#!/usr/bin/env python3
"""
Absence Notification Processor — soporte@ FreeScout mailbox.

Processes student absence/sick notifications from multiple channels:
  • Email  → parent emails soporte@ directly
  • WA/TG  → parent tells Glenda → Glenda creates FS conversation

Every 10 min (weekdays 06:00–17:00 VET):
  1. Find unprocessed absence conversations in soporte@ inbox
  2. Claude extracts: student, grade, level, section, reason, teacher
  3. FreeScout API: assign to Josefina + auto-reply to parent + internal note
  4. Odoo XML-RPC: email alert (Josefina + CC director + subdirector + soporte@)
  5. Odoo XML-RPC: OdooBot DM → Josefina (immediate action checklist)
  6. 24h follow-up: re-ping Josefina if conversation still open

Usage:
  python3 scripts/absence_processor.py           # live
  python3 scripts/absence_processor.py --dry-run # no writes

Cron: /etc/cron.d/absence_processor
  */10 10-21 * * 1-5 root /usr/bin/python3 /opt/odoo-dev/scripts/absence_processor.py \
    >> /var/log/absence_processor.log 2>&1
  # 10:00-21:00 UTC = 06:00-17:00 VET
"""

import json
import os
import re
import sys
import xmlrpc.client
from datetime import datetime, timezone, timedelta

import pymysql
import requests

# ── Config ────────────────────────────────────────────────────────────────────

FS_CONFIG   = json.load(open('/opt/odoo-dev/config/freescout_api.json'))
FS_API_URL  = FS_CONFIG['api_url']
FS_API_KEY  = FS_CONFIG['api_key']
FS_MAILBOX_SOPORTE = 3   # soporte@ueipab.edu.ve
FS_USER_JOSEFINA   = 8   # Josefina Rodriguez (Freescout user_id)
FS_ADMIN_USER      = 1   # Admin (for API byUser)

MYSQL = dict(host='localhost', db='free297', user='free297',
             password='1gczp1S@3!', cursorclass=pymysql.cursors.DictCursor)

ODOO = {
    'url':     'https://odoo.ueipab.edu.ve',
    'db':      'DB_UEIPAB',
    'user':    'tdv.devs@gmail.com',
    'api_key': '6e65cfeb1762f224f675b8d26c1dfe0c',
}

ANTHROPIC_CONFIG = json.load(open('/opt/odoo-dev/config/anthropic_api.json'))
CLAUDE_API_KEY   = ANTHROPIC_CONFIG['api']['api_key']
CLAUDE_MODEL     = ANTHROPIC_CONFIG['model']['default']

STATE_FILE = '/opt/odoo-dev/scripts/absence_processor_state.json'
PROCESSED_TAG = '[AUSENCIA]'

# Staff emails
JOSEFINA_EMAIL = 'josefina.rodriguez@ueipab.edu.ve'
JOSEFINA_ODOO_PARTNER_ID = 2558  # for OdooBot DM
ARCIDES_EMAIL  = 'arcides.arzola@ueipab.edu.ve'
NORKA_EMAIL    = 'norka.larosa@ueipab.edu.ve'    # Media General / Bachillerato
DAVID_EMAIL    = 'david.hernandez@ueipab.edu.ve'  # Preescolar / Inicial / Primaria
SOPORTE_EMAIL  = 'soporte@ueipab.edu.ve'          # CEO oversight CC on every email
FROM_EMAIL     = 'Colegio Andrés Bello <soporte@ueipab.edu.ve>'
FS_BASE_URL    = 'https://freescout.ueipab.edu.ve'

# Keyword patterns for initial classification (fast, no AI)
ABSENCE_KEYWORDS = re.compile(
    r'ausencia|reposo|inasistencia|enferm|malestar|fiebre|dolor|'
    r'médico|medico|cita|incapacidad|no asistir|no asistirá|'
    r'no va a ir|no podrá asistir|no podra asistir|aviso de ausencia|'
    r'notificacion de ausencia|notificación de ausencia',
    re.IGNORECASE
)

DRY_RUN = '--dry-run' in sys.argv


# ── State management ──────────────────────────────────────────────────────────

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {'processed': {}, 'followup_pending': {}}


def save_state(state):
    if not DRY_RUN:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)


# ── FreeScout helpers ─────────────────────────────────────────────────────────

def fs_headers():
    return {'X-FreeScout-API-Key': FS_API_KEY, 'Content-Type': 'application/json'}


def fs_get_conversation(conv_id):
    r = requests.get(f'{FS_API_URL}/conversations/{conv_id}', headers=fs_headers(), timeout=15)
    return r.json() if r.ok else {}


def fs_assign(conv_id, user_id):
    r = requests.put(f'{FS_API_URL}/conversations/{conv_id}',
                     json={'assignTo': user_id, 'byUser': FS_ADMIN_USER},
                     headers=fs_headers(), timeout=15)
    return r.status_code in (200, 204)


def fs_reply(conv_id, html_body):
    """Send a reply visible to the customer."""
    r = requests.post(f'{FS_API_URL}/conversations/{conv_id}/threads',
                      json={'type': 'reply', 'text': html_body, 'user': FS_ADMIN_USER},
                      headers=fs_headers(), timeout=15)
    return r.status_code == 201


def fs_note(conv_id, html_body):
    """Add an internal note (not visible to customer)."""
    r = requests.post(f'{FS_API_URL}/conversations/{conv_id}/threads',
                      json={'type': 'note', 'text': html_body, 'user': FS_ADMIN_USER},
                      headers=fs_headers(), timeout=15)
    return r.status_code == 201


def fs_create_conversation(subject, body_html, customer_email, customer_name=''):
    """Create a new conversation in soporte@ (used by Glenda WA/TG channel)."""
    payload = {
        'type':      1,
        'mailboxId': FS_MAILBOX_SOPORTE,
        'subject':   subject,
        'status':    'active',
        'customer':  {'email': customer_email, 'firstName': customer_name},
        'threads':   [{'type': 'customer', 'text': body_html}],
    }
    r = requests.post(f'{FS_API_URL}/conversations', json=payload,
                      headers=fs_headers(), timeout=15)
    if r.ok:
        return r.json().get('id')
    return None


# ── MySQL helpers ─────────────────────────────────────────────────────────────

def fetch_inbox_convs():
    """Return active/unassigned absence convs in soporte@ not yet tagged [AUSENCIA]."""
    conn = pymysql.connect(**MYSQL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT c.id, c.number, c.subject, c.created_at, c.user_id,
                       cu.first_name, cu.last_name,
                       e.email as customer_email,
                       t.body
                FROM conversations c
                LEFT JOIN customers cu ON cu.id = c.customer_id
                LEFT JOIN emails e ON e.customer_id = cu.id AND e.type = 'customer'
                LEFT JOIN threads t ON t.conversation_id = c.id AND t.type = 1 AND t.state = 2
                WHERE c.mailbox_id = %s
                  AND c.status = 1
                  AND c.subject NOT LIKE %s
                ORDER BY c.created_at ASC
            """, (FS_MAILBOX_SOPORTE, f'{PROCESSED_TAG}%'))
            return cur.fetchall()
    finally:
        conn.close()


def strip_html(html):
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    return ' '.join(text.split())


# ── Claude extraction ─────────────────────────────────────────────────────────

def extract_absence_info(subject, body_text):
    """Use Claude Haiku to extract structured info from subject + body."""
    prompt = f"""Analiza este mensaje de un representante escolar en Venezuela.

ASUNTO: {subject}
CUERPO: {body_text[:800]}

Extrae la información y responde SOLO con JSON válido (sin markdown, sin explicaciones):
{{
  "is_absence": true/false,
  "student_name": "nombre completo o null",
  "grade_raw": "texto original del grado (ej: '3er año sección A', '4to grado', 'preescolar')",
  "level": "preescolar" | "primaria" | "media" | "bachillerato" | "unknown",
  "section": "A/B/C o null",
  "reason": "motivo breve",
  "return_date": "fecha si se menciona o null",
  "teacher_mentioned": "nombre del docente si se menciona o null"
}}

Notas: "año" = Media General/Bachillerato. "grado" = Primaria. "preescolar/inicial/kinder" = Preescolar."""

    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key':         CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type':      'application/json',
            },
            json={
                'model':      CLAUDE_MODEL,
                'max_tokens': 300,
                'messages':   [{'role': 'user', 'content': prompt}],
            },
            timeout=20,
        )
        text = r.json()['content'][0]['text'].strip()
        # Strip markdown fences if present
        text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE).strip()
        return json.loads(text)
    except Exception as e:
        print(f'  [WARN] Claude extraction failed: {e}')
        # Fail safe: if extraction fails, do NOT process — avoid false positives
        return {'is_absence': False}


# ── CC routing ────────────────────────────────────────────────────────────────

def get_cc_emails(level, teacher_email=None):
    """Return list of CC addresses based on student level."""
    cc = [SOPORTE_EMAIL, ARCIDES_EMAIL]  # Director + soporte@ always
    if level in ('media', 'bachillerato'):
        cc.append(NORKA_EMAIL)
    elif level in ('preescolar', 'primaria'):
        cc.append(DAVID_EMAIL)
    else:
        cc += [NORKA_EMAIL, DAVID_EMAIL]  # ambiguous → both subdirectors
    if teacher_email and teacher_email not in cc:
        cc.append(teacher_email)
    return list(dict.fromkeys(cc))  # deduplicate, preserve order


def find_teacher_email(teacher_name):
    """Look up teacher's work email in Odoo hr.employee."""
    if not teacher_name:
        return None
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
        uid = common.authenticate(ODOO['db'], ODOO['user'], ODOO['api_key'], {})
        models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")
        # Try name search
        parts = teacher_name.strip().split()
        domain = [['active', '=', True]]
        for part in parts[:2]:  # first two name parts
            domain.append(['name', 'ilike', part])
        emps = models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                                 'hr.employee', 'search_read', [domain],
                                 {'fields': ['name', 'work_email'], 'limit': 1})
        return emps[0]['work_email'] if emps and emps[0]['work_email'] else None
    except Exception:
        return None


# ── Odoo email ────────────────────────────────────────────────────────────────

def send_alert_email(info, conv_id, conv_number, parent_name, cc_emails):
    """Queue absence alert email via Odoo mail.mail."""
    today = datetime.now().strftime('%d/%m/%Y')
    student  = info.get('student_name') or 'Alumno/a'
    grade    = info.get('grade_raw') or '—'
    reason   = info.get('reason') or '—'
    section  = f" Sec. {info['section']}" if info.get('section') else ''
    teacher  = info.get('teacher_mentioned') or 'No mencionado'
    level    = info.get('level', 'unknown')
    ret_date = info.get('return_date') or 'No indicada'
    conv_url = f'{FS_BASE_URL}/conversations/{conv_id}'

    subdirector = {
        'media': 'Norka La Rosa', 'bachillerato': 'Norka La Rosa',
        'preescolar': 'David Hernández', 'primaria': 'David Hernández',
    }.get(level, 'Norka La Rosa y David Hernández')

    cc_str = ', '.join(cc_emails)
    subject = f'[Ausencia] {student} — {grade}{section} — {today}'

    body = f"""
<div style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;">
  <div style="background:#1a2c5b;padding:20px 28px;border-radius:8px 8px 0 0;">
    <h2 style="color:#fff;margin:0;font-size:18px;">📋 Notificación de Ausencia Escolar</h2>
    <p style="color:#a8c4e0;margin:4px 0 0;font-size:13px;">
      Procesado automáticamente · {today}
    </p>
  </div>

  <div style="background:#fff;padding:24px 28px;border:1px solid #e0e8f0;border-top:none;">
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <tr style="background:#f0f4fa;">
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;width:180px;">Alumno/a</td>
        <td style="padding:8px 12px;color:#222;"><strong>{student}</strong></td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;">Nivel / Año</td>
        <td style="padding:8px 12px;color:#222;">{grade}{section}</td>
      </tr>
      <tr style="background:#f0f4fa;">
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;">Motivo</td>
        <td style="padding:8px 12px;color:#222;">{reason}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;">Fecha retorno</td>
        <td style="padding:8px 12px;color:#222;">{ret_date}</td>
      </tr>
      <tr style="background:#f0f4fa;">
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;">Docente mencionado</td>
        <td style="padding:8px 12px;color:#222;">{teacher}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-weight:700;color:#1a2c5b;">Representante</td>
        <td style="padding:8px 12px;color:#555;">{parent_name}</td>
      </tr>
    </table>

    <div style="background:#fff8e1;border-left:4px solid #f9a825;padding:14px 18px;
                margin:20px 0;border-radius:0 6px 6px 0;">
      <p style="margin:0 0 6px;font-weight:700;color:#1a2c5b;">
        ⚠️ Acción requerida — Josefina Rodríguez
      </p>
      <p style="margin:0;font-size:13px;color:#555;line-height:1.6;">
        Coordinar con <strong>{subdirector}</strong> el manejo de actividades y evaluaciones
        durante la ausencia. Asegurar que el alumno tenga un plan de recuperación al reincorporarse.
      </p>
    </div>

    <p style="text-align:center;margin:20px 0 0;">
      <a href="{conv_url}"
         style="background:#1a2c5b;color:#fff;padding:10px 24px;border-radius:6px;
                text-decoration:none;font-size:13px;font-weight:700;">
        Ver conversación en FreeScout #{conv_number}
      </a>
    </p>
  </div>

  <div style="background:#f5f5f5;padding:12px 28px;border-radius:0 0 8px 8px;
              border:1px solid #e0e8f0;border-top:none;">
    <p style="margin:0;font-size:11px;color:#888;">
      Enviado automáticamente por el sistema de notificaciones del
      Colegio Andrés Bello · CC: {cc_str}
    </p>
  </div>
</div>"""

    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
        uid = common.authenticate(ODOO['db'], ODOO['user'], ODOO['api_key'], {})
        models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")
        models.execute_kw(ODOO['db'], uid, ODOO['api_key'], 'mail.mail', 'create', [{
            'subject':    subject,
            'body_html':  body,
            'email_from': FROM_EMAIL,
            'email_to':   JOSEFINA_EMAIL,
            'email_cc':   ', '.join(cc_emails),
            'state':      'outgoing',
            'auto_delete': True,
        }])
        return True
    except Exception as e:
        print(f'  [ERROR] Email failed: {e}')
        return False


# ── OdooBot DM → Josefina ─────────────────────────────────────────────────────

def notify_josefina_discuss(info, conv_id, conv_number, is_followup=False):
    """Post OdooBot DM to Josefina with action checklist."""
    student  = info.get('student_name') or 'Alumno/a'
    grade    = info.get('grade_raw') or '—'
    reason   = info.get('reason') or '—'
    level    = info.get('level', 'unknown')
    teacher  = info.get('teacher_mentioned') or 'No mencionado'
    conv_url = f'{FS_BASE_URL}/conversations/{conv_id}'

    subdirector = {
        'media': 'Norka La Rosa', 'bachillerato': 'Norka La Rosa',
        'preescolar': 'David Hernández', 'primaria': 'David Hernández',
    }.get(level, 'Norka La Rosa / David Hernández')

    today = datetime.now().strftime('%d/%m/%Y %H:%M')

    if is_followup:
        msg = (
            f'⏰ Recordatorio — Ausencia pendiente de cierre (FS #{conv_number})<br/>'
            f'<br/>'
            f'👤 <strong>{student}</strong> — {grade}<br/>'
            f'📝 {reason}<br/>'
            f'<br/>'
            f'La conversación en FreeScout sigue abierta. '
            f'¿Ya coordinaste con <strong>{subdirector}</strong> el plan de recuperación?<br/>'
            f'<br/>'
            f'🔗 <a href="{conv_url}">Ver en FreeScout #{conv_number}</a>'
        )
    else:
        msg = (
            f'📋 Nueva ausencia escolar — {today}<br/>'
            f'<br/>'
            f'👤 <strong>{student}</strong> — {grade}<br/>'
            f'📝 Motivo: {reason}<br/>'
            f'👩‍🏫 Docente: {teacher}<br/>'
            f'<br/>'
            f'Coordinar con: <strong>{subdirector}</strong><br/>'
            f'<br/>'
            f'☐ Informar a {subdirector} sobre actividades/evaluaciones perdidas<br/>'
            f'☐ Confirmar plan de recuperación con el docente<br/>'
            f'☐ Notificar al representante cuando esté definido<br/>'
            f'☐ Cerrar conversación en FreeScout al completar<br/>'
            f'<br/>'
            f'🔗 <a href="{conv_url}">Ver en FreeScout #{conv_number}</a>'
        )

    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
        uid = common.authenticate(ODOO['db'], ODOO['user'], ODOO['api_key'], {})
        models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")

        # Find OdooBot partner
        bot_ref = models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                                    'ir.model.data', 'search_read',
                                    [[['module', '=', 'base'], ['name', '=', 'partner_root']]],
                                    {'fields': ['res_id'], 'limit': 1})
        if not bot_ref:
            return False
        bot_partner_id = bot_ref[0]['res_id']

        # Find/create Josefina's OdooBot DM channel
        jos_ch = set(models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                                       'discuss.channel', 'search',
                                       [[['channel_type', '=', 'chat'],
                                         ['channel_member_ids.partner_id', '=', JOSEFINA_ODOO_PARTNER_ID]]]))
        bot_ch = set(models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                                       'discuss.channel', 'search',
                                       [[['channel_type', '=', 'chat'],
                                         ['channel_member_ids.partner_id', '=', bot_partner_id]]]))
        shared = jos_ch & bot_ch

        if shared:
            channel_id = min(shared)
        else:
            channel_id = models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                                           'discuss.channel', 'create',
                                           [{'channel_type': 'chat', 'name': ''}])
            models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                               'discuss.channel.member', 'create',
                               [[{'channel_id': channel_id, 'partner_id': JOSEFINA_ODOO_PARTNER_ID},
                                 {'channel_id': channel_id, 'partner_id': bot_partner_id}]])

        models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                          'discuss.channel', 'message_post', [channel_id],
                          {'body': msg, 'message_type': 'comment',
                           'subtype_xmlid': 'mail.mt_comment'})
        return True
    except Exception as e:
        print(f'  [ERROR] OdooBot DM failed: {e}')
        return False


# ── Internal note (FreeScout) ─────────────────────────────────────────────────

def build_internal_note(info, subdirector):
    student  = info.get('student_name') or '—'
    grade    = info.get('grade_raw') or '—'
    section  = f" Sec. {info['section']}" if info.get('section') else ''
    reason   = info.get('reason') or '—'
    ret_date = info.get('return_date') or 'No indicada'
    teacher  = info.get('teacher_mentioned') or 'No mencionado'

    return f"""
<div style="font-family:Arial,sans-serif;font-size:13px;">
  <p><strong>📋 Ausencia procesada automáticamente</strong></p>
  <table style="border-collapse:collapse;width:100%;">
    <tr><td style="padding:4px 10px;font-weight:bold;color:#1a2c5b;">Alumno/a</td>
        <td style="padding:4px 10px;">{student}</td></tr>
    <tr style="background:#f5f5f5;"><td style="padding:4px 10px;font-weight:bold;color:#1a2c5b;">Nivel</td>
        <td style="padding:4px 10px;">{grade}{section}</td></tr>
    <tr><td style="padding:4px 10px;font-weight:bold;color:#1a2c5b;">Motivo</td>
        <td style="padding:4px 10px;">{reason}</td></tr>
    <tr style="background:#f5f5f5;"><td style="padding:4px 10px;font-weight:bold;color:#1a2c5b;">Retorno esperado</td>
        <td style="padding:4px 10px;">{ret_date}</td></tr>
    <tr><td style="padding:4px 10px;font-weight:bold;color:#1a2c5b;">Docente mencionado</td>
        <td style="padding:4px 10px;">{teacher}</td></tr>
  </table>
  <p style="margin-top:14px;"><strong>Acción requerida — coordinar con {subdirector}:</strong></p>
  <p>
    ☐ Informar a {subdirector} sobre actividades/evaluaciones en el período de ausencia<br/>
    ☐ Confirmar plan de recuperación con el/la docente del aula<br/>
    ☐ Notificar al representante cuando esté definido el plan<br/>
    ☐ <strong>Cerrar esta conversación al completar el seguimiento</strong>
  </p>
  <p style="font-size:11px;color:#888;margin-top:10px;">
    Procesado por absence_processor.py · Glenda AI Sistema de Ausencias
  </p>
</div>"""


# ── Auto-reply to parent ──────────────────────────────────────────────────────

def build_parent_reply(info):
    student = info.get('student_name') or 'su representado/a'
    return f"""
<div style="font-family:Arial,sans-serif;font-size:14px;color:#333;">
  <p>Estimado/a representante,</p>
  <p>
    Hemos recibido su notificación de ausencia de <strong>{student}</strong>.
    Queda debidamente registrada en nuestro sistema.
  </p>
  <p>
    Coordinaremos con el personal docente y directivo correspondiente para asegurar
    el adecuado manejo de las actividades y evaluaciones durante la ausencia,
    garantizando que <strong>{student}</strong> pueda reincorporarse sin inconvenientes académicos.
  </p>
  <p>Si tiene alguna duda adicional, no dude en contactarnos.</p>
  <p>Saludos cordiales,<br/>
  <strong>Colegio Andrés Bello</strong><br/>
  Coordinación Académica</p>
</div>"""


# ── 24h follow-up check ───────────────────────────────────────────────────────

def check_followup(state):
    """Ping Josefina again if a processed conv is still open after 24h."""
    now = datetime.now(timezone.utc)
    pending = state.get('followup_pending', {})
    to_remove = []

    for conv_id_str, entry in pending.items():
        due = datetime.fromisoformat(entry['due_at'])
        if now < due:
            continue
        conv_id = int(conv_id_str)
        # Check if still open in Freescout
        conv = fs_get_conversation(conv_id)
        status = conv.get('status', 'closed')
        if status == 'active':
            print(f'  Follow-up: conv {conv_id} still open — pinging Josefina')
            if not DRY_RUN:
                notify_josefina_discuss(
                    entry['info'], conv_id, entry['conv_number'], is_followup=True)
        to_remove.append(conv_id_str)

    for k in to_remove:
        del pending[k]


# ── Main processing ───────────────────────────────────────────────────────────

def process_conversation(conv, state):
    conv_id     = conv['id']
    conv_number = conv.get('number', conv_id)
    subject     = conv.get('subject', '')
    body_html   = conv.get('body', '') or ''
    body_text   = strip_html(body_html)
    first_name  = conv.get('first_name', '') or ''
    last_name   = conv.get('last_name', '') or ''
    parent_name = f'{first_name} {last_name}'.strip() or 'Representante'
    parent_email = conv.get('customer_email', '') or ''

    # Quick keyword pre-filter (avoids Claude API cost on non-absence convs)
    combined = f'{subject} {body_text}'
    if not ABSENCE_KEYWORDS.search(combined):
        return False

    print(f'\n  Conv {conv_id} | {subject[:60]}')
    print(f'  From: {parent_name} <{parent_email}>')

    # Claude extraction
    info = extract_absence_info(subject, body_text)
    if not info.get('is_absence'):
        print(f'  Claude: not an absence → skip')
        return False

    student = info.get('student_name') or '—'
    grade   = info.get('grade_raw') or '—'
    level   = info.get('level', 'unknown')
    print(f'  Student: {student} | Grade: {grade} | Level: {level} | Reason: {info.get("reason")}')

    # Determine subdirector
    subdirector = {
        'media': 'Norka La Rosa', 'bachillerato': 'Norka La Rosa',
        'preescolar': 'David Hernández', 'primaria': 'David Hernández',
    }.get(level, 'Norka La Rosa y David Hernández')

    # Find teacher email if mentioned
    teacher_email = find_teacher_email(info.get('teacher_mentioned'))

    # CC list (always includes soporte@ + director + subdirector)
    cc_emails = get_cc_emails(level, teacher_email)

    if DRY_RUN:
        print(f'  [DRY RUN] Would: assign→Josefina, reply→parent, note, email CC={cc_emails}, OdooBot DM')
        state['processed'][str(conv_id)] = {'at': datetime.now().isoformat(), 'dry_run': True}
        return True

    # 1. Assign to Josefina
    ok = fs_assign(conv_id, FS_USER_JOSEFINA)
    print(f'  Assign → Josefina: {"✓" if ok else "✗"}')

    # 2. Auto-reply to parent
    ok = fs_reply(conv_id, build_parent_reply(info))
    print(f'  Reply  → parent:   {"✓" if ok else "✗"}')

    # 3. Internal note for Josefina
    ok = fs_note(conv_id, build_internal_note(info, subdirector))
    print(f'  Note   → internal: {"✓" if ok else "✗"}')

    # 4. Alert email (Josefina + CC director + subdirector + soporte@)
    ok = send_alert_email(info, conv_id, conv_number, parent_name, cc_emails)
    print(f'  Email  → alert:    {"✓" if ok else "✗"}  CC: {", ".join(cc_emails)}')

    # 5. OdooBot DM → Josefina
    ok = notify_josefina_discuss(info, conv_id, conv_number)
    print(f'  DM     → Josefina: {"✓" if ok else "✗"}')

    # 6. Mark processed (rename subject with [AUSENCIA] prefix via Freescout API)
    requests.put(f'{FS_API_URL}/conversations/{conv_id}',
                 json={'subject': f'{PROCESSED_TAG} {subject}', 'byUser': FS_ADMIN_USER},
                 headers=fs_headers(), timeout=10)

    # 7. Schedule 24h follow-up
    state['processed'][str(conv_id)] = {'at': datetime.now().isoformat()}
    state.setdefault('followup_pending', {})[str(conv_id)] = {
        'due_at': (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        'conv_number': conv_number,
        'info': info,
    }

    return True


def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f'[{ts}] absence_processor starting {"(DRY RUN)" if DRY_RUN else "(LIVE)"}')

    state = load_state()

    # Check 24h follow-ups first
    check_followup(state)

    # Fetch inbox conversations
    convs = fetch_inbox_convs()
    new_convs = [c for c in convs if str(c['id']) not in state.get('processed', {})]
    print(f'Inbox conversations: {len(convs)} total, {len(new_convs)} unprocessed')

    processed = 0
    for conv in new_convs:
        if process_conversation(conv, state):
            processed += 1

    save_state(state)
    print(f'\nDone. {processed} absence(s) processed.')


if __name__ == '__main__':
    main()
