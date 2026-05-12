#!/usr/bin/env python3
"""
Send a group status report for the Glenda Calibration Programme.

Queries production for current conv/feedback counts per enrolled tester,
builds an HTML status table in Spanish, and queues one email.

Usage:
    docker exec -i odoo-prod-web /usr/bin/odoo shell -d DB_UEIPAB --no-http \
        < /opt/odoo-dev/scripts/send_calibration_status_report.py

    # Or run directly (reads from /root/.odoo_agent_env_prod via XML-RPC):
    source /root/.odoo_agent_env_prod && python3 scripts/send_calibration_status_report.py
"""

DRY_RUN       = False
NOTICE_KEY    = 'glenda_calibracion_v1'
SKILL_ID      = 6          # ai.agent.skill id for general_inquiry in production
BONUS_DEADLINE = 'viernes 30 de mayo de 2026'
BONUS_MIN_CONVS = 3
BONUS_MIN_FB    = 1
FROM_EMAIL    = 'Recursos Humanos UEIPAB <recursoshumanos@ueipab.edu.ve>'
TO_EMAIL      = 'recursoshumanos@ueipab.edu.ve'   # change to distribution list if needed
SUBJECT       = 'Programa Calibración Glenda — Reporte de Avance'

import re
import os
import sys
import xmlrpc.client
from collections import defaultdict
from datetime import datetime, timezone, timedelta

# ── Connection ─────────────────────────────────────────────────────────────────

def get_connection():
    url = os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve')
    db  = os.environ.get('ODOO_DB',  'DB_UEIPAB')
    user = os.environ.get('ODOO_USER', 'tdv.devs@gmail.com')
    pw   = os.environ.get('ODOO_PASSWORD', '')
    if not pw:
        print("ERROR: ODOO_PASSWORD not set. Source /root/.odoo_agent_env_prod first.")
        sys.exit(1)
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, pw, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    def call(model, method, domain=None, fields=None, **kw):
        kwargs = {}
        if fields: kwargs['fields'] = fields
        kwargs.update(kw)
        return models.execute_kw(db, uid, pw, model, method, [domain or []], kwargs)
    return call

# ── Data fetch ─────────────────────────────────────────────────────────────────

def fetch_data(call):
    acks = call('hr.notice.acknowledgment', 'search_read',
        [('notice_key','=', NOTICE_KEY), ('state','=','acknowledged')],
        fields=['employee_id','wa_number','ack_date'])

    tester_map = {}
    for a in acks:
        wa = a.get('wa_number') or ''
        digits = re.sub(r'\D','',wa)
        emp_name = a['employee_id'][1] if a['employee_id'] else '?'
        emp_id   = a['employee_id'][0] if a['employee_id'] else None
        if digits and len(digits) >= 9:
            tester_map[digits[-9:]] = {'emp_name': emp_name, 'emp_id': emp_id, 'wa_number': wa}

    convs = call('ai.agent.conversation', 'search_read',
        [('skill_id','=', SKILL_ID)],
        fields=['id','phone','state','create_date'])

    tester_convs = defaultdict(int)
    for c in convs:
        digits = re.sub(r'\D','', c.get('phone') or '')
        if len(digits) >= 9 and digits[-9:] in tester_map:
            tester_convs[digits[-9:]] += 1

    feedbacks = call('ai.agent.feedback', 'search_read',
        [],
        fields=['employee_id','wa_number','category','suggestion','date','state'])

    feedback_by_emp = defaultdict(list)
    for fb in feedbacks:
        emp_id = fb['employee_id'][0] if fb['employee_id'] else None
        if emp_id:
            feedback_by_emp[emp_id].append(fb)

    rows = []
    for key9, info in tester_map.items():
        n_convs = tester_convs.get(key9, 0)
        n_fb    = len(feedback_by_emp.get(info['emp_id'], []))
        eligible = n_convs >= BONUS_MIN_CONVS and n_fb >= BONUS_MIN_FB
        rows.append({
            'name':    info['emp_name'],
            'wa':      info['wa_number'],
            'n_convs': n_convs,
            'n_fb':    n_fb,
            'eligible': eligible,
        })

    rows.sort(key=lambda x: (-x['n_convs'], -x['n_fb'], x['name']))
    return rows, feedbacks


CATEGORY_ES = {
    'flujo':       'Flujo',
    'respuesta':   'Respuesta',
    'idioma':      'Idioma',
    'asistencia':  'Asistencia',
    'conocimiento':'Conocimiento',
    'tecnico':     'Técnico',
    'otro':        'Otro',
}

# ── HTML builder ───────────────────────────────────────────────────────────────

def build_html(rows, feedbacks, report_date):
    bonus_count    = sum(1 for r in rows if r['eligible'])
    started_count  = sum(1 for r in rows if r['n_convs'] > 0)
    total          = len(rows)
    total_feedback = len(feedbacks)

    # ── Status rows ──────────────────────────────────────────────────────────
    def status_cell(r):
        if r['eligible']:
            return ('<td style="padding:10px 14px;border-bottom:1px solid #e0e8f4;'
                    'text-align:center;background:#eafaf1;">'
                    '<span style="color:#1e8449;font-weight:bold;">✓ ELEGIBLE</span></td>')
        conv_ok = r['n_convs'] >= BONUS_MIN_CONVS
        fb_ok   = r['n_fb'] >= BONUS_MIN_FB
        missing = []
        if not conv_ok: missing.append(f"+{BONUS_MIN_CONVS - r['n_convs']} conv.")
        if not fb_ok:   missing.append('+1 sugerencia')
        color = '#7d6608' if r['n_convs'] > 0 else '#922b21'
        label = ' / '.join(missing) if missing else 'En progreso'
        return (f'<td style="padding:10px 14px;border-bottom:1px solid #e0e8f4;'
                f'text-align:center;color:{color};font-size:12px;">{label}</td>')

    def conv_cell(n):
        color = '#1e8449' if n >= BONUS_MIN_CONVS else ('#7d6608' if n > 0 else '#922b21')
        return (f'<td style="padding:10px 14px;border-bottom:1px solid #e0e8f4;'
                f'text-align:center;color:{color};font-weight:bold;">{n}</td>')

    def fb_cell(n):
        color = '#1e8449' if n >= BONUS_MIN_FB else ('#7d6608' if n > 0 else '#922b21')
        return (f'<td style="padding:10px 14px;border-bottom:1px solid #e0e8f4;'
                f'text-align:center;color:{color};font-weight:bold;">{n}</td>')

    table_rows = ''
    for i, r in enumerate(rows):
        bg = '#ffffff' if i % 2 == 0 else '#f8fbff'
        first = r['name'].split()[0].capitalize()
        table_rows += f"""
        <tr style="background:{bg};">
          <td style="padding:10px 14px;border-bottom:1px solid #e0e8f4;">{first}</td>
          {conv_cell(r['n_convs'])}
          {fb_cell(r['n_fb'])}
          {status_cell(r)}
        </tr>"""

    # ── Feedback section ─────────────────────────────────────────────────────
    if feedbacks:
        fb_rows = ''
        for fb in sorted(feedbacks, key=lambda x: x.get('date') or '', reverse=True):
            emp = fb['employee_id'][1].split()[0].capitalize() if fb['employee_id'] else '?'
            cat = CATEGORY_ES.get(fb.get('category',''), 'Otro')
            sug = fb.get('suggestion','')
            dt  = (fb.get('date') or '')[:10]
            fb_rows += f"""
            <tr>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e8f4;
                         color:#1a2c5b;font-weight:bold;white-space:nowrap;">{emp}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e8f4;
                         color:#2471a3;white-space:nowrap;">{cat}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e8f4;">{sug}</td>
              <td style="padding:9px 12px;border-bottom:1px solid #e0e8f4;
                         color:#7f8c8d;white-space:nowrap;font-size:11px;">{dt}</td>
            </tr>"""

        feedback_block = f"""
    <p style="margin-top:28px;"><strong>Sugerencias recibidas ({total_feedback})</strong></p>
    <table style="width:100%;border-collapse:collapse;background:#ffffff;
                  border-radius:6px;overflow:hidden;font-size:13px;">
      <tr style="background:#e8f4fb;">
        <th style="padding:10px 12px;text-align:left;color:#1a2c5b;">Empleado/a</th>
        <th style="padding:10px 12px;text-align:left;color:#1a2c5b;">Categoría</th>
        <th style="padding:10px 12px;text-align:left;color:#1a2c5b;">Sugerencia</th>
        <th style="padding:10px 12px;text-align:left;color:#1a2c5b;">Fecha</th>
      </tr>
      {fb_rows}
    </table>"""
    else:
        feedback_block = """
    <div style="background:#fff8e1;border-left:4px solid #f39c12;
                padding:12px 16px;margin-top:20px;border-radius:0 6px 6px 0;font-size:13px;">
      <strong>Sin sugerencias aún.</strong> Recuerda decirle a Glenda:
      <em>«Tengo una sugerencia: [tu idea]»</em>
    </div>"""

    # ── KPI chips ────────────────────────────────────────────────────────────
    def chip(value, label, color):
        return (f'<div style="display:inline-block;background:{color};color:#fff;'
                f'padding:14px 22px;border-radius:8px;text-align:center;margin:6px;">'
                f'<div style="font-size:26px;font-weight:bold;">{value}</div>'
                f'<div style="font-size:11px;margin-top:4px;">{label}</div></div>')

    chips = (
        chip(bonus_count, 'Elegibles bono', '#1e8449') +
        chip(started_count, 'Han iniciado', '#2471a3') +
        chip(total - started_count, 'Sin iniciar', '#922b21') +
        chip(total_feedback, 'Sugerencias', '#7d6608')
    )

    return f"""
<div style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;color:#1a2c5b;">

  <!-- Header -->
  <div style="background:#1a2c5b;padding:24px 30px;">
    <h2 style="color:#ffffff;margin:0;font-size:18px;">
      Programa de Calibración · Glenda IA — Reporte de Avance
    </h2>
    <p style="color:#a0b4d0;margin:6px 0 0;font-size:13px;">
      Fecha del reporte: {report_date} &nbsp;|&nbsp; Plazo final: {BONUS_DEADLINE}
    </p>
  </div>

  <!-- Body -->
  <div style="padding:28px 30px;background:#f0f4fa;">

    <p>Estimado equipo,</p>
    <p>A continuación encontrarán el estado actual del <strong>Programa de Calibración de Glenda</strong>.
    Les compartimos el avance de cada participante y las sugerencias recibidas hasta la fecha.</p>

    <!-- KPI chips -->
    <div style="text-align:center;margin:20px 0;">
      {chips}
    </div>

    <!-- Bonus reminder -->
    <div style="background:#fff8e1;border-left:4px solid #f39c12;
                padding:14px 18px;margin:16px 0;border-radius:0 6px 6px 0;font-size:13px;">
      <strong>🎁 Criterio de bono:</strong>
      Realizar al menos <strong>{BONUS_MIN_CONVS} conversaciones</strong> con Glenda
      y enviar al menos <strong>{BONUS_MIN_FB} sugerencia</strong> antes del
      <strong>{BONUS_DEADLINE}</strong>.
    </div>

    <!-- Progress table -->
    <p style="margin-top:24px;"><strong>Estado por participante</strong></p>
    <table style="width:100%;border-collapse:collapse;background:#ffffff;
                  border-radius:6px;overflow:hidden;font-size:13px;">
      <tr style="background:#2471a3;">
        <th style="padding:10px 14px;text-align:left;color:#fff;">Participante</th>
        <th style="padding:10px 14px;text-align:center;color:#fff;">Conversaciones</th>
        <th style="padding:10px 14px;text-align:center;color:#fff;">Sugerencias</th>
        <th style="padding:10px 14px;text-align:center;color:#fff;">Estado</th>
      </tr>
      {table_rows}
    </table>
    <p style="font-size:11px;color:#7f8c8d;margin-top:6px;">
      Meta: {BONUS_MIN_CONVS} conversaciones + {BONUS_MIN_FB} sugerencia &nbsp;·&nbsp;
      <span style="color:#1e8449;">Verde</span> = alcanzado &nbsp;·&nbsp;
      <span style="color:#7d6608;">Ámbar</span> = en progreso &nbsp;·&nbsp;
      <span style="color:#922b21;">Rojo</span> = sin iniciar / pendiente
    </p>

    {feedback_block}

    <!-- Tip -->
    <div style="background:#e8f4fb;border-left:4px solid #2471a3;
                padding:14px 18px;margin-top:24px;border-radius:0 6px 6px 0;font-size:13px;">
      <strong>¿Cómo enviar una sugerencia?</strong><br/>
      Escríbele a Glenda: <em>«Tengo una sugerencia: [tu idea]»</em><br/>
      Glenda la registrará automáticamente en el sistema.
    </div>

    <p style="margin-top:24px;">Gracias por su participación y aportes.<br/>
    <strong>Recursos Humanos · UEIPAB</strong></p>
  </div>

  <!-- Footer -->
  <div style="background:#1a2c5b;padding:12px 30px;text-align:center;">
    <span style="color:#a0b4d0;font-size:11px;">
      Instituto Privado Andrés Bello · El Tigre, Venezuela · ueipab.edu.ve
    </span>
  </div>

</div>
"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    call = get_connection()
    rows, feedbacks = fetch_data(call)

    vet = datetime.now(timezone(timedelta(hours=-4)))
    report_date = vet.strftime('%d/%m/%Y')

    bonus_count = sum(1 for r in rows if r['eligible'])
    started     = sum(1 for r in rows if r['n_convs'] > 0)
    subject_full = f"{SUBJECT} — {started}/{len(rows)} iniciados · {bonus_count} elegibles"

    body = build_html(rows, feedbacks, report_date)

    print(f"Report date : {report_date}")
    print(f"Subject     : {subject_full}")
    print(f"To          : {TO_EMAIL}")
    print(f"DRY_RUN     : {DRY_RUN}")
    print(f"Rows        : {len(rows)} testers")
    print(f"Feedback    : {len(feedbacks)} suggestions")

    if DRY_RUN:
        print("\n[DRY RUN] Email not sent.")
        return

    # This block runs inside Odoo shell context (env is pre-defined)
    # OR via XML-RPC create below
    try:
        # Odoo shell mode
        mail = env['mail.mail'].sudo().create({   # noqa: F821
            'subject':    subject_full,
            'email_from': FROM_EMAIL,
            'email_to':   TO_EMAIL,
            'body_html':  body,
            'state':      'outgoing',
        })
        env.cr.commit()  # noqa: F821
        print(f"\nQueued mail.mail id={mail.id}")
        env['mail.mail'].sudo().search([('state','=','outgoing')]).send()  # noqa: F821
        env.cr.commit()  # noqa: F821
        print("Mail queue flushed.")
    except NameError:
        # Standalone XML-RPC mode
        call_rpc = get_connection()
        mail_id = call_rpc('mail.mail', 'create', [], {
            'subject':    subject_full,
            'email_from': FROM_EMAIL,
            'email_to':   TO_EMAIL,
            'body_html':  body,
            'state':      'outgoing',
        })
        print(f"\nQueued mail.mail id={mail_id} via XML-RPC")
        outgoing = call_rpc('mail.mail', 'search', [('state','=','outgoing')])
        call_rpc('mail.mail', 'send', outgoing)
        print("Mail queue flushed.")


main()
