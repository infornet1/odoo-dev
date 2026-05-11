#!/usr/bin/env python3
"""
Send the Glenda Calibration Programme testing guide email
to the 19 enrolled employees with verified personal WA numbers.

Usage:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/send_calibration_programme_email.py

    # Production:
    # Run from the production container referencing DB_UEIPAB

DRY_RUN = True  →  prints emails, does NOT create mail.mail records
"""

DRY_RUN = False          # set False to actually queue emails
TARGET_ENV = 'production'  # 'testing' | 'production'
PILOT_ONLY = False         # True = send only to PILOT_EMAIL; False = send to all 19
ALREADY_SENT = {'gustavo.perdomo@ueipab.edu.ve'}  # skip pilot recipient

# ──────────────────────────────────────────────────────────────────────────────

NOTICE_KEY   = 'glenda_calibracion_v1'
GLENDA_WA    = '+58 414 8321989'
FROM_EMAIL   = 'Recursos Humanos UEIPAB <recursoshumanos@ueipab.edu.ve>'
CC_EMAIL     = 'recursoshumanos@ueipab.edu.ve'
PILOT_EMAIL  = 'gustavo.perdomo@ueipab.edu.ve'
BONUS_DEADLINE = 'viernes 30 de mayo de 2026'

BONUS_CONV_MIN = 3
BONUS_FB_MIN   = 1

TESTING_SCENARIOS = [
    ("1", "Saludo y presentación",
     "Escríbele hola a Glenda y observa cómo se presenta e identifica tu consulta."),
    ("2", "Tasa BCV",
     "Pregunta: <em>«¿Cuál es la tasa BCV de hoy?»</em> o <em>«¿Cuánto son $100 en bolívares?»</em>"),
    ("3", "Consulta de asistencia",
     "Pregunta sobre tu reporte de asistencia quincenal o cómo registrar una corrección."),
    ("4", "Información institucional",
     "Pregunta sobre inscripciones, mensualidades, horarios o cursos extracurriculares."),
    ("5", "Pregunta difícil",
     "Hazle una pregunta que creas que no sabe contestar y observa cómo responde."),
    ("6", "Sugerencia de mejora",
     "Dile a Glenda: <em>«Tengo una sugerencia»</em> y cuéntale qué cambiarías o mejorarías."),
    ("7", "Escenario de representante",
     "Actúa como si fueras un padre/madre buscando información de inscripción y evalúa la experiencia."),
]


def build_email_body(employee_name, wa_number):
    first = employee_name.split()[0].capitalize()

    scenarios_html = ''.join(
        f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #e0e8f4;
                     font-weight:bold;color:#2471a3;vertical-align:top;
                     white-space:nowrap;">Escenario {num}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e0e8f4;vertical-align:top;">
            <strong>{title}</strong><br/>{desc}
          </td>
        </tr>"""
        for num, title, desc in TESTING_SCENARIOS
    )

    return f"""
<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#1a2c5b;">

  <!-- Header -->
  <div style="background:#1a2c5b;padding:24px 30px;">
    <h2 style="color:#ffffff;margin:0;font-size:18px;">
      Programa de Calibración · Glenda IA — Guía de Pruebas
    </h2>
  </div>

  <!-- Body -->
  <div style="padding:28px 30px;background:#f0f4fa;">
    <p>Estimado/a <strong>{first}</strong>,</p>

    <p>Has sido seleccionado/a para participar en el <strong>Programa de Calibración de Glenda</strong>,
    nuestra Asistente Virtual Institucional con inteligencia artificial. Tu participación es clave para
    afinar las respuestas de Glenda y adaptarla a las necesidades reales de nuestro equipo.</p>

    <p style="margin-top:20px;"><strong>¿Cómo participar?</strong></p>
    <p>Simplemente escríbele a Glenda directamente por WhatsApp al número:</p>

    <div style="text-align:center;margin:20px 0;">
      <span style="background:#2471a3;color:#fff;padding:10px 28px;
                   border-radius:6px;font-size:18px;font-weight:bold;letter-spacing:1px;">
        {GLENDA_WA}
      </span>
    </div>

    <p>Tu número registrado en el programa es <strong>{wa_number}</strong>.
    Glenda te reconocerá automáticamente como evaluador/a.</p>

    <!-- Scenarios table -->
    <p style="margin-top:24px;"><strong>Escenarios de prueba sugeridos:</strong></p>
    <table style="width:100%;border-collapse:collapse;background:#ffffff;
                  border-radius:6px;overflow:hidden;font-size:13px;">
      {scenarios_html}
    </table>

    <!-- Feedback tip -->
    <div style="background:#e8f4fb;border-left:4px solid #2471a3;
                padding:14px 18px;margin:24px 0;border-radius:0 6px 6px 0;">
      <strong>¿Cómo enviar sugerencias?</strong><br/>
      Cuando quieras sugerir una mejora, simplemente dile a Glenda:<br/>
      <em style="color:#1a2c5b;">«Tengo una sugerencia: [tu idea]»</em><br/>
      Glenda registrará tu aporte automáticamente.
    </div>

    <!-- Bonus condition -->
    <div style="background:#fff8e1;border-left:4px solid #f39c12;
                padding:14px 18px;margin:16px 0;border-radius:0 6px 6px 0;">
      <strong>🎁 Bono de participación</strong><br/>
      Para calificar al bono, realiza al menos <strong>{BONUS_CONV_MIN} conversaciones de prueba</strong>
      y envía al menos <strong>{BONUS_FB_MIN} sugerencia</strong> a través de Glenda,
      antes del <strong>{BONUS_DEADLINE}</strong>.
      El equipo de RRHH llevará el seguimiento automáticamente.
    </div>

    <p>Gracias por contribuir a mejorar nuestras herramientas institucionales.
    Cada sugerencia cuenta y será revisada por el equipo de Recursos Humanos.</p>

    <p style="margin-top:24px;">Con aprecio,<br/>
    <strong>Recursos Humanos · UEIPAB</strong><br/>
    <a href="mailto:{CC_EMAIL}" style="color:#2471a3;">{CC_EMAIL}</a></p>
  </div>

  <!-- Footer -->
  <div style="background:#1a2c5b;padding:12px 30px;text-align:center;">
    <span style="color:#a0b4d0;font-size:11px;">
      Instituto Privado Andrés Bello · El Tigre, Venezuela · ueipab.edu.ve
    </span>
  </div>

</div>
"""


# ── Main ──────────────────────────────────────────────────────────────────────

active_db = env['ir.config_parameter'].sudo().get_param('ai_agent.active_db', '')
if TARGET_ENV == 'production' and active_db != 'DB_UEIPAB':
    print(f"ABORT: active_db='{active_db}' — not targeting production. Set TARGET_ENV='testing' or run on prod.")
else:
    acks = env['hr.notice.acknowledgment'].sudo().search([
        ('notice_key', '=', NOTICE_KEY),
        ('state', '=', 'acknowledged'),
        ('wa_number', '!=', False),
        # Exclude YUDELYS BRITO who has the institutional number still
        ('wa_number', '!=', '+58 414 8321963'),
    ])

    print(f"Sending calibration programme email to {len(acks)} enrolled employees")
    print(f"DRY_RUN = {DRY_RUN}\n")

    sent = 0
    skipped = 0
    for ack in sorted(acks, key=lambda a: a.employee_id.name or ''):
        emp = ack.employee_id
        if not emp:
            print(f"  SKIP: ack id={ack.id} has no employee_id")
            skipped += 1
            continue

        email_to = emp.work_email or ''
        if not email_to:
            print(f"  SKIP (no work_email): {emp.name}")
            skipped += 1
            continue

        if PILOT_ONLY and email_to != PILOT_EMAIL:
            skipped += 1
            continue

        if email_to in ALREADY_SENT:
            print(f"  SKIP (already sent): {emp.name}")
            skipped += 1
            continue

        subject = 'Programa Calibración Glenda — Tu guía de pruebas'
        body = build_email_body(emp.name, ack.wa_number)

        if DRY_RUN:
            print(f"  [DRY] → {emp.name:<32} {email_to}  WA:{ack.wa_number}")
        else:
            mail = env['mail.mail'].sudo().create({
                'subject':    subject,
                'email_from': FROM_EMAIL,
                'email_to':   email_to,
                'email_cc':   CC_EMAIL,
                'body_html':  body,
                'state':      'outgoing',
            })
            env.cr.commit()
            print(f"  QUEUED id={mail.id} → {emp.name:<32} {email_to}")
        sent += 1

    print(f"\nDone. Queued={sent if not DRY_RUN else 0} (dry_run previewed={sent if DRY_RUN else 0}) Skipped={skipped}")

    if not DRY_RUN and sent > 0:
        print("Triggering mail queue...")
        env['mail.mail'].sudo().search([('state', '=', 'outgoing')]).send()
        env.cr.commit()
        print("Mail queue flushed.")
