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

# control_asistencias credentials (same as sync_control_asistencia.py)
CA_MYSQL = dict(
    host='localhost', port=3306,
    user='control_asist', password='y3deTsi92HrQgj0wgvVx',
    database='control_asistencias', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

# Grade text → control_asistencias id_grado
# Ordered longest-match first to avoid "1er" matching "primer nivel de preescolar 1er grupo"
_GRADE_PATTERNS = [
    # Maternales / Preescolar (id_grado 1-3)
    (r'(primer|1er?).{0,15}(nivel|grupo).{0,15}(maternal|preescolar|kinder|inicial)', 1),
    (r'(segundo|2do?).{0,15}(nivel|grupo).{0,15}(maternal|preescolar|kinder|inicial)', 2),
    (r'(tercer|3er?).{0,15}(nivel|grupo).{0,15}(maternal|preescolar|kinder|inicial)', 3),
    (r'preescolar|maternal|inicial|kinder', 1),   # unspecified preescolar → nivel 1 (fallback)
    # Primaria (id_grado 4-9)
    (r'(primer|1er?)\s*(grado)',    4),
    (r'(segundo|2do?)\s*(grado)',   5),
    (r'(tercer|3er?)\s*(grado)',    6),
    (r'(cuarto|4to?)\s*(grado)',    7),
    (r'(quinto|5to?)\s*(grado)',    8),
    (r'(sexto|6to?)\s*(grado)',     9),
    # Secundaria / Media / Bachillerato (id_grado 10-14)
    (r'(primer|1er?)\s*(a[ñn]o)',  10),
    (r'(segundo|2do?)\s*(a[ñn]o)', 11),
    (r'(tercer|3er?)\s*(a[ñn]o)',  12),
    (r'(cuarto|4to?)\s*(a[ñn]o)',  13),
    (r'(quinto|5to?)\s*(a[ñn]o)',  14),
]

_GRADE_NAMES = {
    1: 'Nivel 1 maternal', 2: 'Nivel 2 maternal', 3: 'Nivel 3 maternal',
    4: '1er grado', 5: '2do grado', 6: '3er grado',
    7: '4to grado', 8: '5to grado', 9: '6to grado',
    10: '1er año', 11: '2do año', 12: '3er año',
    13: '4to año', 14: '5to año',
}

# Max teachers to CC directly when section IS specified (all are relevant)
# When section is NOT specified, we never CC teachers — subdirector coordinates
MAX_TEACHERS_TO_CC = 12


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
                       (SELECT t.body FROM threads t
                        WHERE t.conversation_id = c.id AND t.type = 1 AND t.state = 2
                        ORDER BY t.id ASC LIMIT 1) as body
                FROM conversations c
                LEFT JOIN customers cu ON cu.id = c.customer_id
                LEFT JOIN emails e ON e.customer_id = cu.id
                WHERE c.mailbox_id = %s
                  AND c.status = 1
                  AND c.subject NOT LIKE %s
                GROUP BY c.id
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


def normalize_grade_to_id(grade_raw):
    """Map Claude's grade_raw text to control_asistencias id_grado. Returns None if unrecognised."""
    if not grade_raw:
        return None
    text = grade_raw.lower()
    for pattern, grade_id in _GRADE_PATTERNS:
        if re.search(pattern, text):
            return grade_id
    return None


def extract_section_letter(grade_raw):
    """Extract section letter from grade text, e.g. '3er año Sec A' → 'A'."""
    if not grade_raw:
        return None
    m = re.search(r'secc?i[oó]n\s*([A-Za-z])|sec\.?\s+([A-Za-z])\b|\bsec\.?\s*([A-Za-z])',
                  grade_raw, re.IGNORECASE)
    if m:
        return (m.group(1) or m.group(2) or m.group(3)).upper()
    return None


def lookup_teachers_from_ca(grade_raw, section=None, named_teacher=None):
    """Query control_asistencias for teachers assigned to the given grade/section.

    Returns:
        dict with:
          grade_id       — matched id_grado or None
          grade_name     — human-readable grade name
          section        — section letter used for lookup
          cc_teachers    — [(name, email)] to add to email CC
          all_teachers   — [(name, email)] all teachers for this grade (for note reference)
          logic          — short explanation of what was done
    """
    result = {
        'grade_id': None, 'grade_name': '—', 'section': section,
        'cc_teachers': [], 'all_teachers': [], 'logic': '',
    }

    grade_id = normalize_grade_to_id(grade_raw)
    result['grade_id'] = grade_id
    result['grade_name'] = _GRADE_NAMES.get(grade_id, grade_raw) if grade_id else grade_raw

    # Try to extract section from grade_raw if not already passed in
    if not section:
        section = extract_section_letter(grade_raw)
        result['section'] = section

    if not grade_id:
        result['logic'] = f'Grade "{grade_raw}" not mapped to id_grado — no teacher lookup'
        return result

    try:
        conn = pymysql.connect(**CA_MYSQL)
        try:
            with conn.cursor() as cur:
                # All teachers for this grade (for reference in the internal note)
                cur.execute("""
                    SELECT DISTINCT
                        CONCAT(u.nombre, ' ', u.apellido) AS name,
                        u.email,
                        s.nombre_seccion
                    FROM profesor_seccion ps
                    JOIN usuario u ON u.id_usuario = ps.id_profesor
                    JOIN seccion s ON s.id_seccion = ps.id_seccion
                    WHERE s.id_grado = %s
                      AND u.activo = 1
                      AND u.email IS NOT NULL AND u.email != ''
                    ORDER BY s.nombre_seccion, u.nombre
                """, (grade_id,))
                all_rows = cur.fetchall()
                result['all_teachers'] = [(r['name'], r['email']) for r in all_rows]

                if section:
                    # Section-specific teachers → CC them directly
                    cur.execute("""
                        SELECT DISTINCT
                            CONCAT(u.nombre, ' ', u.apellido) AS name,
                            u.email
                        FROM profesor_seccion ps
                        JOIN usuario u ON u.id_usuario = ps.id_profesor
                        JOIN seccion s ON s.id_seccion = ps.id_seccion
                        WHERE s.id_grado = %s
                          AND LOWER(s.nombre_seccion) LIKE %s
                          AND u.activo = 1
                          AND u.email IS NOT NULL AND u.email != ''
                        ORDER BY u.nombre
                    """, (grade_id, f'%{section.lower()}%'))
                    sec_rows = cur.fetchall()
                    result['cc_teachers'] = [(r['name'], r['email']) for r in sec_rows]
                    result['logic'] = (
                        f'Section {section} specified → {len(result["cc_teachers"])} teachers CC\'d directly'
                    )
                else:
                    # No section → do not CC teachers; subdirector coordinates
                    # (listing all_teachers in the note is enough)
                    result['cc_teachers'] = []
                    result['logic'] = (
                        f'No section specified → {len(result["all_teachers"])} teachers for '
                        f'{result["grade_name"]} listed in note; subdirector coordinates'
                    )
        finally:
            conn.close()

    except Exception as e:
        result['logic'] = f'control_asistencias lookup failed: {e}'

    # If a specific teacher was named by the parent, always add them
    if named_teacher:
        named_email = find_teacher_email(named_teacher)
        if named_email and (named_teacher, named_email) not in result['cc_teachers']:
            result['cc_teachers'].insert(0, (named_teacher, named_email))
            result['logic'] += f'; named teacher ({named_teacher}) added'

    return result


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

def send_alert_email(info, conv_id, conv_number, parent_name, cc_emails, teacher_lookup=None):
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

    # Teacher section for email body
    teacher_section_html = ''
    if teacher_lookup:
        cc_t  = teacher_lookup.get('cc_teachers', [])
        all_t = teacher_lookup.get('all_teachers', [])
        if cc_t:
            rows = ''.join(
                f'<tr style="background:{"#f8fafd" if i%2==0 else "#fff"};">'
                f'<td style="padding:6px 10px;font-size:12px;">{n}</td>'
                f'<td style="padding:6px 10px;font-size:12px;color:#555;">{e}</td>'
                f'</tr>'
                for i, (n, e) in enumerate(cc_t)
            )
            teacher_section_html = f"""
    <div style="margin-top:16px;">
      <p style="font-weight:700;color:#1a2c5b;margin:0 0 8px;font-size:13px;">
        👩‍🏫 Docentes de {grade}{section} notificados (CC en este correo):
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <tr style="background:#1a2c5b;color:#fff;">
          <th style="padding:5px 10px;text-align:left;">Docente</th>
          <th style="padding:5px 10px;text-align:left;">Correo</th>
        </tr>
        {rows}
      </table>
    </div>"""
        elif all_t:
            names = ', '.join(n for n, _ in all_t[:6])
            more  = f' y {len(all_t)-6} más' if len(all_t) > 6 else ''
            teacher_section_html = f"""
    <div style="margin-top:16px;padding:10px 14px;background:#f5f5f5;border-radius:6px;">
      <p style="margin:0;font-size:12px;color:#555;">
        <strong>Docentes de {grade}:</strong> {names}{more}<br/>
        <em>Sección no especificada — coordinar notificación vía {subdirector}</em>
      </p>
    </div>"""

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

    {teacher_section_html}

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

def notify_josefina_discuss(info, conv_id, conv_number, teacher_lookup=None, is_followup=False):
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

    # Teacher line for DM
    teacher_dm_line = ''
    if teacher_lookup:
        cc_t = teacher_lookup.get('cc_teachers', [])
        all_t = teacher_lookup.get('all_teachers', [])
        if cc_t:
            names = ', '.join(n.split()[0].title() for n, _ in cc_t[:4])
            more  = f' +{len(cc_t)-4}' if len(cc_t) > 4 else ''
            teacher_dm_line = f'👩‍🏫 Docentes CC\'d: {names}{more}<br/>'
        elif all_t:
            teacher_dm_line = f'👩‍🏫 {len(all_t)} docentes en {teacher_lookup.get("grade_name","?")} — coordinar vía {subdirector}<br/>'

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
            f'{teacher_dm_line}'
            f'<br/>'
            f'Coordinar con: <strong>{subdirector}</strong><br/>'
            f'<br/>'
            f'☐ Confirmar con {subdirector} actividades/evaluaciones perdidas<br/>'
            f'☐ Verificar plan de recuperación con docentes del aula<br/>'
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

def build_internal_note(info, subdirector, teacher_lookup=None):
    student  = info.get('student_name') or '—'
    grade    = info.get('grade_raw') or '—'
    section  = f" Sec. {info['section']}" if info.get('section') else ''
    reason   = info.get('reason') or '—'
    ret_date = info.get('return_date') or 'No indicada'
    teacher  = info.get('teacher_mentioned') or 'No mencionado'

    # Teacher section from control_asistencias
    teacher_html = ''
    if teacher_lookup:
        all_t = teacher_lookup.get('all_teachers', [])
        cc_t  = teacher_lookup.get('cc_teachers', [])
        logic = teacher_lookup.get('logic', '')
        sec_used = teacher_lookup.get('section')

        if cc_t:
            rows = ''.join(
                f'<tr><td style="padding:3px 8px;">✉️ CC enviado</td>'
                f'<td style="padding:3px 8px;">{n}</td>'
                f'<td style="padding:3px 8px;color:#555;">{e}</td></tr>'
                for n, e in cc_t
            )
            teacher_html = (
                f'<p style="margin-top:12px;"><strong>Docentes de {grade}{section} '
                f'notificados (CC en email):</strong></p>'
                f'<table style="font-size:12px;border-collapse:collapse;">{rows}</table>'
            )
        elif all_t:
            rows = ''.join(
                f'<tr><td style="padding:3px 8px;color:#888;">—</td>'
                f'<td style="padding:3px 8px;">{n}</td>'
                f'<td style="padding:3px 8px;color:#555;">{e}</td></tr>'
                for n, e in all_t
            )
            teacher_html = (
                f'<p style="margin-top:12px;"><strong>Docentes de {grade} '
                f'(sección no especificada — coordinar vía {subdirector}):</strong></p>'
                f'<table style="font-size:12px;border-collapse:collapse;">{rows}</table>'
                f'<p style="font-size:11px;color:#888;">ℹ️ {logic}</p>'
            )

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
  {teacher_html}
  <p style="margin-top:14px;"><strong>Acción requerida — coordinar con {subdirector}:</strong></p>
  <p>
    ☐ Confirmar con {subdirector} el manejo de actividades/evaluaciones del período<br/>
    ☐ Verificar que los docentes del aula tengan el plan de recuperación<br/>
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

    # Phase 2: Teacher lookup from control_asistencias
    section_from_claude = info.get('section')
    teacher_lookup = lookup_teachers_from_ca(
        grade_raw=info.get('grade_raw', ''),
        section=section_from_claude,
        named_teacher=info.get('teacher_mentioned'),
    )
    print(f'  Teachers: {teacher_lookup["logic"]}')
    if teacher_lookup['cc_teachers']:
        for name, email in teacher_lookup['cc_teachers']:
            print(f'    CC teacher: {name} <{email}>')

    # Find teacher email if mentioned (legacy path, merged into lookup above)
    teacher_email = None  # handled by teacher_lookup now

    # CC list: soporte@ + director + subdirector + section teachers (if section known)
    cc_emails = get_cc_emails(level, teacher_email)
    for _, t_email in teacher_lookup.get('cc_teachers', []):
        if t_email and t_email not in cc_emails:
            cc_emails.append(t_email)

    if DRY_RUN:
        print(f'  [DRY RUN] Would:')
        print(f'    → assign to Josefina in FreeScout')
        print(f'    → reply to parent ({parent_email})')
        print(f'    → internal note (with teacher list)')
        print(f'    → email: josefina CC {", ".join(cc_emails)}')
        print(f'    → OdooBot DM to Josefina')
        state['processed'][str(conv_id)] = {'at': datetime.now().isoformat(), 'dry_run': True}
        return True

    # 1. Assign to Josefina
    ok = fs_assign(conv_id, FS_USER_JOSEFINA)
    print(f'  Assign → Josefina: {"✓" if ok else "✗"}')

    # 2. Auto-reply to parent
    ok = fs_reply(conv_id, build_parent_reply(info))
    print(f'  Reply  → parent:   {"✓" if ok else "✗"}')

    # 3. Internal note for Josefina (includes teacher list)
    ok = fs_note(conv_id, build_internal_note(info, subdirector, teacher_lookup))
    print(f'  Note   → internal: {"✓" if ok else "✗"}')

    # 4. Alert email (Josefina + CC director + subdirector + teachers + soporte@)
    ok = send_alert_email(info, conv_id, conv_number, parent_name, cc_emails, teacher_lookup)
    print(f'  Email  → alert:    {"✓" if ok else "✗"}  CC: {", ".join(cc_emails)}')

    # 5. OdooBot DM → Josefina
    ok = notify_josefina_discuss(info, conv_id, conv_number, teacher_lookup)
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
