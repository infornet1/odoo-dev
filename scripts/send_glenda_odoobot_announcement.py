"""
Send staff announcement email: OdooBot is now powered by Glenda.
Run: docker exec -i odoo-dev-web /usr/bin/odoo shell -d DB_UEIPAB --no-http < scripts/send_glenda_odoobot_announcement.py
"""

import logging
_logger = logging.getLogger(__name__)

DRY_RUN = True   # Set to False to actually send

# ── Email content ─────────────────────────────────────────────────────────────

SUBJECT = "Glenda ya está en Odoo — tu asistente virtual ahora también responde en el chat interno"

BODY_HTML = """
<div style="font-family: Arial, sans-serif; max-width: 640px; margin: 0 auto; background: #f0f4fa; padding: 24px;">

  <!-- Header -->
  <div style="background: #1a2c5b; border-radius: 10px 10px 0 0; padding: 32px 36px 24px; text-align: center;">
    <div style="font-size: 42px; margin-bottom: 8px;">🤖</div>
    <h1 style="color: #ffffff; font-size: 22px; margin: 0 0 6px;">¡Glenda ya está en Odoo!</h1>
    <p style="color: #a8c4e0; font-size: 14px; margin: 0;">
      Tu asistente virtual ahora responde en el chat interno del sistema
    </p>
  </div>

  <!-- Body card -->
  <div style="background: #ffffff; padding: 32px 36px; border-left: 4px solid #2471a3; border-right: 4px solid #2471a3;">

    <p style="color: #1a2c5b; font-size: 15px; line-height: 1.6;">
      Hola equipo,
    </p>
    <p style="color: #333; font-size: 15px; line-height: 1.6;">
      A partir de hoy, <strong style="color: #1a2c5b;">Glenda</strong> — la misma asistente de inteligencia artificial que atiende a los representantes por WhatsApp — está disponible directamente dentro de <strong>Odoo Discuss</strong>, conectada al <strong>OdooBot</strong>.
    </p>
    <p style="color: #333; font-size: 15px; line-height: 1.6;">
      Esto significa que puedes consultarle tarifas, políticas, costos de inscripción y cualquier información institucional sin salir del sistema — desde tu computadora, en tiempo real.
    </p>

    <!-- How to use -->
    <div style="background: #f0f4fa; border-radius: 8px; padding: 20px 24px; margin: 24px 0;">
      <h2 style="color: #1a2c5b; font-size: 16px; margin: 0 0 16px;">¿Cómo usarlo? Solo 3 pasos</h2>
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="width: 36px; vertical-align: top; padding: 6px 12px 6px 0;">
            <div style="background: #1a2c5b; color: #fff; border-radius: 50%; width: 28px; height: 28px; text-align: center; line-height: 28px; font-size: 13px; font-weight: bold;">1</div>
          </td>
          <td style="vertical-align: top; padding: 6px 0; color: #333; font-size: 14px;">
            Abre <strong>Odoo</strong> → haz clic en el ícono de <strong>Discuss</strong> (burbuja de chat) en el menú superior.
          </td>
        </tr>
        <tr>
          <td style="width: 36px; vertical-align: top; padding: 6px 12px 6px 0;">
            <div style="background: #1a2c5b; color: #fff; border-radius: 50%; width: 28px; height: 28px; text-align: center; line-height: 28px; font-size: 13px; font-weight: bold;">2</div>
          </td>
          <td style="vertical-align: top; padding: 6px 0; color: #333; font-size: 14px;">
            En la barra lateral izquierda, busca <strong>OdooBot</strong> y haz clic para abrir el chat privado.
          </td>
        </tr>
        <tr>
          <td style="width: 36px; vertical-align: top; padding: 6px 12px 6px 0;">
            <div style="background: #1a2c5b; color: #fff; border-radius: 50%; width: 28px; height: 28px; text-align: center; line-height: 28px; font-size: 13px; font-weight: bold;">3</div>
          </td>
          <td style="vertical-align: top; padding: 6px 0; color: #333; font-size: 14px;">
            <strong>¡Escríbele!</strong> Glenda responderá en segundos con información precisa y actualizada.
          </td>
        </tr>
      </table>
    </div>

    <!-- What she knows -->
    <h2 style="color: #1a2c5b; font-size: 16px; margin: 28px 0 16px;">¿Qué puede responderle?</h2>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
      <tr>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #2471a3; font-weight: bold; width: 50%;">💰 Tarifas 2026-2027</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #333;">Mensualidades, inscripción promo ($187,51), pronto pago</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #2471a3; font-weight: bold;">👨‍👩‍👧‍👦 Descuentos por hermanos</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #333;">1er hijo 5% · 2do 8% · 3ro+ 11% · cotizaciones multi-alumno</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #2471a3; font-weight: bold;">📋 Costos anuales</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #333;">Seguro $30,58 · Guía inglés $25 · Olimpiadas $10 · Enciclopedia $36</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #2471a3; font-weight: bold;">🏦 Medios de pago</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #333;">Cuentas bancarias, Zelle, Binance, Cashea, Mercantil portal</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #2471a3; font-weight: bold;">📜 Políticas institucionales</td>
        <td style="padding: 8px 12px; border-bottom: 1px solid #e8eef5; color: #333;">PDVSA, mora, inscripción anticipada, requisitos</td>
      </tr>
      <tr>
        <td style="padding: 8px 12px; color: #2471a3; font-weight: bold;">🏫 Información general</td>
        <td style="padding: 8px 12px; color: #333;">Autoridades, aliados, tasa BCV, horarios de contacto</td>
      </tr>
    </table>

    <!-- Chat example -->
    <div style="background: #f0f4fa; border-radius: 8px; padding: 20px 24px; margin: 28px 0;">
      <p style="color: #1a2c5b; font-size: 13px; font-weight: bold; margin: 0 0 14px; text-transform: uppercase; letter-spacing: 0.5px;">Ejemplo de conversación</p>
      <!-- User bubble -->
      <div style="text-align: right; margin-bottom: 10px;">
        <span style="display: inline-block; background: #2471a3; color: #fff; border-radius: 16px 16px 4px 16px; padding: 8px 14px; font-size: 13px; max-width: 80%;">
          ¿Cuánto cuesta la inscripción para 2 hijos el próximo año?
        </span>
      </div>
      <!-- Glenda bubble -->
      <div style="text-align: left; margin-bottom: 10px;">
        <span style="display: inline-block; background: #ffffff; color: #333; border: 1px solid #d0dce8; border-radius: 16px 16px 16px 4px; padding: 8px 14px; font-size: 13px; max-width: 85%;">
          ¡Hola! Hay una <strong>promoción vigente</strong> hasta el 31 de julio:<br><br>
          • Inscripción promo: <strong>$187,51</strong> × 2 = $375,02<br>
          • Mensualidad sep: 1er hijo $207,94 · 2do $201,37<br>
          • Costos anuales: $101,58 × 2 = $203,16<br>
          • <strong>Total primer mes: $987,49</strong><br><br>
          Requisito: período 2025-2026 completamente saldado. ¿Deseas la cotización completa?
        </span>
      </div>
    </div>

    <!-- Note -->
    <div style="border-left: 3px solid #2471a3; padding: 12px 16px; background: #f8fafd; border-radius: 0 6px 6px 0; margin-top: 8px;">
      <p style="margin: 0; font-size: 13px; color: #555; line-height: 1.5;">
        <strong style="color: #1a2c5b;">Nota:</strong> Esta integración es exclusiva para el equipo interno con acceso a Odoo. Glenda responde en segundos con la misma información actualizada que usa en WhatsApp. En caso de error, OdooBot responde con su comportamiento habitual.
      </p>
    </div>
  </div>

  <!-- Footer -->
  <div style="background: #1a2c5b; border-radius: 0 0 10px 10px; padding: 20px 36px; text-align: center;">
    <p style="color: #a8c4e0; font-size: 12px; margin: 0 0 4px;">Instituto Privado Andrés Bello — Sistema de Gestión Interno</p>
    <p style="color: #6a90b5; font-size: 11px; margin: 0;">¿Dudas técnicas? soporte@ueipab.edu.ve</p>
  </div>

</div>
"""

# ── Recipients: active internal users with valid email, exclude system accounts ──

EXCLUDE_LOGINS = {'tdv.devs@gmail.com', '__system__'}
EXCLUDE_NAMES  = {'Asistencia', 'odoo_api_bridge'}

users = env['res.users'].search([('share', '=', False), ('active', '=', True)])
recipients = []
seen_emails = set()
for u in users:
    email = (u.email or '').strip()
    if not email or '@' not in email:
        continue
    if u.login in EXCLUDE_LOGINS or u.name in EXCLUDE_NAMES:
        continue
    # Gustavo has two emails — use only the primary (first one)
    primary_email = email.split(';')[0].strip()
    if primary_email in seen_emails:
        continue
    seen_emails.add(primary_email)
    recipients.append((u.name, primary_email))

print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}Sending to {len(recipients)} recipients:\n")
for name, email in sorted(recipients, key=lambda x: x[0]):
    print(f"  {name:<35} {email}")

if not DRY_RUN:
    sent = 0
    for name, email in recipients:
        mail = env['mail.mail'].create({
            'subject': SUBJECT,
            'body_html': BODY_HTML,
            'email_from': 'Glenda — Colegio Andrés Bello <soporte@ueipab.edu.ve>',
            'email_to': email,
            'auto_delete': True,
        })
        mail.send()
        sent += 1
        print(f"  ✓ Sent to {name} <{email}>")
    env.cr.commit()
    print(f"\nDone. {sent} emails queued.")
else:
    print(f"\n[DRY RUN] No emails sent. Set DRY_RUN = False to send.")
