"""
Glenda Telegram Announcement — Internal Staff
=============================================
Sends a personalised invitation email to each active employee, introducing
Glenda on Telegram with a direct deep-link button (t.me/GlendaUeipabBot?start=EMP_{id}).

Usage (testing):
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < scripts/send_glenda_telegram_announcement.py

Usage (production):
  docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http \
    < scripts/send_glenda_telegram_announcement.py

Controls:
  DRY_RUN    = True   → prints recipient list, no emails sent
  TEST_EMAIL = '...'  → send to one address only (set DRY_RUN=False)
"""

import logging
_logger = logging.getLogger(__name__)

# ── Controls ─────────────────────────────────────────────────────────────────
DRY_RUN    = True
TEST_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'   # set '' to send to all employees

BOT_USERNAME = 'GlendaUeipabBot'
FROM_EMAIL   = 'Glenda — Colegio Andrés Bello <soporte@ueipab.edu.ve>'
REPLY_TO     = 'recursoshumanos@ueipab.edu.ve'
SUBJECT      = '📱 Glenda ya está en Telegram — respuestas instantáneas desde cualquier dispositivo'
# ─────────────────────────────────────────────────────────────────────────────


def build_body(employee_name, bot_link):
    """Return the full HTML body for a given employee."""
    first = employee_name.split()[0].title()

    # ── Comparison table rows ────────────────────────────────────────────────
    cmp_rows = [
        ('⚡ Velocidad de respuesta', 'Hasta 5 min (ciclo de revisión)', '<b>Instantánea</b> (webhook en tiempo real)'),
        ('🕐 Disponibilidad', '24/7 para usuarios WA', '<b>24/7, sin restricciones de ventana</b>'),
        ('💻 Desde PC / escritorio', 'Solo móvil', '<b>Telegram Web + app desktop</b>'),
        ('📷 Enviar fotos de recibos', 'Sí', 'Sí'),
        ('💬 Conversaciones largas', 'Ventana 24h (puede cortarse)', '<b>Sin límite de tiempo</b>'),
        ('💰 Costo para el colegio', 'Créditos MassivaMóvil', '<b>Gratis</b>'),
    ]
    cmp_html = ''
    for i, (feature, wa, tg) in enumerate(cmp_rows):
        bg = '#f8fafd' if i % 2 == 0 else '#ffffff'
        cmp_html += (
            f'<tr style="background:{bg};">'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#1a2c5b;font-weight:600;font-size:13px;">{feature}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#666;font-size:13px;">{wa}</td>'
            f'<td style="padding:9px 12px;border-bottom:1px solid #e0e8f0;color:#1a7a4a;font-size:13px;">{tg}</td>'
            f'</tr>'
        )

    # ── Step boxes ───────────────────────────────────────────────────────────
    steps_html = ''
    steps = [
        ('Toca el botón azul', 'Abre directamente el chat de Glenda en Telegram — ya estarás identificado/a automáticamente.'),
        ('Espera el mensaje de bienvenida', 'Glenda te saludará por tu nombre y confirmará que te reconoció en el sistema.'),
        ('¡Pregunta lo que necesites!', 'Tarifas, inscripciones, medios de pago, políticas — todo al instante.'),
    ]
    for n, (title, desc) in enumerate(steps, 1):
        steps_html += (
            f'<tr>'
            f'<td style="width:36px;vertical-align:top;padding:8px 14px 8px 0;">'
            f'<div style="background:#1a2c5b;color:#fff;border-radius:50%;width:30px;height:30px;'
            f'text-align:center;line-height:30px;font-size:14px;font-weight:bold;">{n}</div>'
            f'</td>'
            f'<td style="vertical-align:top;padding:8px 0;">'
            f'<p style="margin:0 0 2px;font-size:14px;font-weight:700;color:#1a2c5b;">{title}</p>'
            f'<p style="margin:0;font-size:13px;color:#555;line-height:1.5;">{desc}</p>'
            f'</td>'
            f'</tr>'
        )

    return f"""
<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;background:#f0f4fa;padding:24px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
              border-radius:12px 12px 0 0;padding:32px 36px 28px;text-align:center;">
    <div style="font-size:48px;margin-bottom:12px;">📱</div>
    <h1 style="color:#ffffff;font-size:22px;margin:0 0 8px;font-weight:700;">
      Glenda llegó a Telegram
    </h1>
    <p style="color:#a8c4e0;font-size:14px;margin:0;">
      Tu asistente virtual — ahora más rápida, desde cualquier dispositivo
    </p>
  </div>

  <!-- Body card -->
  <div style="background:#ffffff;padding:32px 36px;
              border-left:4px solid #2471a3;border-right:4px solid #2471a3;">

    <p style="color:#1a2c5b;font-size:15px;line-height:1.6;margin:0 0 16px;">
      Hola, <strong>{first}</strong>,
    </p>
    <p style="color:#444;font-size:15px;line-height:1.6;margin:0 0 24px;">
      Glenda — la misma asistente que ya conoces por <strong>WhatsApp</strong> y por el
      <strong>chat interno de Odoo</strong> — ahora está disponible en
      <strong style="color:#2471a3;">Telegram</strong>.
      Responde al instante, funciona desde el PC y no tiene límites de tiempo de conversación.
    </p>

    <!-- CTA Button -->
    <div style="text-align:center;margin:28px 0;">
      <a href="{bot_link}"
         style="display:inline-block;background:#2471a3;color:#ffffff;
                font-size:16px;font-weight:700;padding:14px 36px;
                border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
        💬 Abrir Glenda en Telegram
      </a>
      <p style="color:#888;font-size:12px;margin:10px 0 0;">
        Este enlace es personal — al abrirlo quedarás identificado/a automáticamente
      </p>
    </div>

    <hr style="border:none;border-top:1px solid #e8eef5;margin:28px 0;">

    <!-- Comparison table -->
    <h2 style="color:#1a2c5b;font-size:16px;margin:0 0 16px;">
      ¿Por qué Telegram vs WhatsApp?
    </h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#1a2c5b;">
          <th style="padding:9px 12px;color:#fff;text-align:left;border-radius:6px 0 0 0;font-weight:600;">Característica</th>
          <th style="padding:9px 12px;color:#a8c4e0;text-align:left;font-weight:600;">WhatsApp</th>
          <th style="padding:9px 12px;color:#7dd9a8;text-align:left;border-radius:0 6px 0 0;font-weight:600;">Telegram ✨</th>
        </tr>
      </thead>
      <tbody>
        {cmp_html}
      </tbody>
    </table>

    <hr style="border:none;border-top:1px solid #e8eef5;margin:28px 0;">

    <!-- Steps -->
    <h2 style="color:#1a2c5b;font-size:16px;margin:0 0 18px;">Cómo empezar — 3 pasos</h2>
    <table style="width:100%;border-collapse:collapse;">{steps_html}</table>

    <hr style="border:none;border-top:1px solid #e8eef5;margin:28px 0;">

    <!-- Three channels -->
    <h2 style="color:#1a2c5b;font-size:16px;margin:0 0 14px;">Glenda en tres canales</h2>
    <table style="width:100%;border-collapse:collapse;">
      <tr>
        <td style="width:33%;padding:12px;text-align:center;vertical-align:top;">
          <div style="font-size:28px;">💬</div>
          <p style="color:#1a2c5b;font-size:13px;font-weight:700;margin:6px 0 4px;">WhatsApp</p>
          <p style="color:#666;font-size:12px;margin:0;line-height:1.4;">Ideal para representantes y contacto externo</p>
        </td>
        <td style="width:33%;padding:12px;text-align:center;vertical-align:top;
                   border-left:1px solid #e8eef5;border-right:1px solid #e8eef5;">
          <div style="font-size:28px;">📱</div>
          <p style="color:#2471a3;font-size:13px;font-weight:700;margin:6px 0 4px;">Telegram ← Nuevo</p>
          <p style="color:#666;font-size:12px;margin:0;line-height:1.4;">Más rápido, desde cualquier dispositivo, sin límites</p>
        </td>
        <td style="width:33%;padding:12px;text-align:center;vertical-align:top;">
          <div style="font-size:28px;">🤖</div>
          <p style="color:#1a2c5b;font-size:13px;font-weight:700;margin:6px 0 4px;">OdooBot (Discuss)</p>
          <p style="color:#666;font-size:12px;margin:0;line-height:1.4;">Consultas rápidas mientras trabajas en Odoo</p>
        </td>
      </tr>
    </table>

    <!-- Note box -->
    <div style="border-left:3px solid #2471a3;padding:12px 16px;
                background:#f0f6ff;border-radius:0 6px 6px 0;margin-top:24px;">
      <p style="margin:0;font-size:13px;color:#444;line-height:1.6;">
        <strong style="color:#1a2c5b;">Nota:</strong>
        El enlace de este correo es personal y único para ti.
        Si Telegram no está instalado, descárgalo gratis en
        <a href="https://telegram.org" style="color:#2471a3;">telegram.org</a>.
        ¿Dudas técnicas? Escríbenos a
        <a href="mailto:soporte@ueipab.edu.ve" style="color:#2471a3;">soporte@ueipab.edu.ve</a>
      </p>
    </div>
  </div>

  <!-- Footer -->
  <div style="background:#1a2c5b;border-radius:0 0 12px 12px;padding:18px 36px;text-align:center;">
    <p style="color:#a8c4e0;font-size:12px;margin:0 0 4px;">
      Instituto Privado Andrés Bello — Sistema de Gestión Interno
    </p>
    <p style="color:#6a90b5;font-size:11px;margin:0;">
      © 2026 Colegio Andrés Bello, El Tigre, Anzoátegui, Venezuela
    </p>
  </div>

</div>
"""


# ── Main ─────────────────────────────────────────────────────────────────────

# Fetch active employees with work email
employees = env['hr.employee'].sudo().search([
    ('active', '=', True),
    ('work_email', '!=', False),
    ('work_email', 'not like', 'tdv.devs'),
    ('company_id', '=', 1),
])

label = '[DRY RUN] ' if DRY_RUN else ''
print(f"\n{label}Glenda Telegram Announcement")
print(f"Bot: @{BOT_USERNAME}  |  Employees: {len(employees)}")
print(f"TEST_EMAIL: {TEST_EMAIL or '(all employees)'}\n")

sent = 0
for emp in employees:
    if not emp.work_email:
        continue

    # Generate personalised deep link for this employee
    bot_link = f"https://t.me/{BOT_USERNAME}?start=EMP_{emp.id}"
    recipient = TEST_EMAIL if TEST_EMAIL else emp.work_email

    if DRY_RUN:
        print(f"  {emp.name:<38} {recipient:<40} {bot_link}")
        if TEST_EMAIL:
            break  # only print one row in dry-run test mode
        continue

    body = build_body(emp.name, bot_link)

    mail = env['mail.mail'].sudo().create({
        'subject':    SUBJECT,
        'body_html':  body,
        'email_from': FROM_EMAIL,
        'email_to':   recipient,
        'reply_to':   REPLY_TO,
        'auto_delete': True,
    })
    mail.sudo().send()
    sent += 1
    print(f"  ✓ {emp.name:<38} → {recipient}")

    if TEST_EMAIL:
        break   # send only to the test address

if not DRY_RUN:
    env.cr.commit()
    print(f"\nDone. {sent} email(s) queued.")
else:
    print(f"\n[DRY RUN] No emails sent. Set DRY_RUN = False to send.")
