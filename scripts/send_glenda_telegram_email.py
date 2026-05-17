#!/usr/bin/env python3
"""
Send Glenda Telegram Introduction Email — UEIPAB

Reads Active + Pipeline customers from the Customers spreadsheet,
builds a branded HTML email introducing Glenda on Telegram, and sends
via Odoo XML-RPC mail.mail.

Usage:
    python3 scripts/send_glenda_telegram_email.py            # dry-run (print recipients)
    python3 scripts/send_glenda_telegram_email.py --test     # send only to CEO email
    python3 scripts/send_glenda_telegram_email.py --live     # send to all 184 customers

Author: Claude Code
Date: 2026-05-17
"""

import json
import sys
import time
import xmlrpc.client
sys.path.insert(0, '/var/www/dev/odoo_api_bridge')

# ============================================================================
# Configuration
# ============================================================================

TEST_ONLY = '--test' in sys.argv
DRY_RUN   = '--live' not in sys.argv and not TEST_ONLY

TEST_EMAIL   = 'gustavo.perdomo@ueipab.edu.ve'
SHEET_ID     = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
LOGO_URL     = 'https://dev.ueipab.edu.ve/flyers/ueipab_logo.png'
BANNER_URL   = 'https://dev.ueipab.edu.ve/flyers/glenda_banner.png'   # upload when ready
TELEGRAM_URL = 'https://t.me/GlendaUeipabBot'
WA_NUMBER    = '+58 414-8321989'

ODOO = {
    'url':     'https://odoo.ueipab.edu.ve',
    'db':      'DB_UEIPAB',
    'user':    'tdv.devs@gmail.com',
    'api_key': '6e65cfeb1762f224f675b8d26c1dfe0c',
}

# ============================================================================
# HTML Email Template
# ============================================================================

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>¡Bienvenida, Glenda!</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">

<!-- Wrapper -->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f4f8;">
<tr><td align="center" style="padding:24px 12px;">

<!-- Card -->
<table width="600" cellpadding="0" cellspacing="0" border="0"
       style="max-width:600px;width:100%;border-radius:12px;overflow:hidden;
              box-shadow:0 4px 24px rgba(0,0,0,0.12);">

  <!-- BANNER HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#0a1628 0%,#0d2045 50%,#0a1628 100%);
               padding:0;text-align:center;">
      <!-- Try image banner first; if not available, styled header shows -->
      <a href="{telegram_url}" style="display:block;text-decoration:none;">
        <img src="{banner_url}" alt="¡Bienvenida, Agente AI Glenda!" width="600"
             style="width:100%;max-width:600px;display:block;border:0;"
             onerror="this.style.display='none'">
      </a>
      <!-- Fallback header (shows if image fails) -->
      <div style="padding:32px 24px 24px;">
        <img src="{logo_url}" alt="Colegio Andrés Bello" width="80" height="80"
             style="border-radius:50%;border:3px solid #C8A951;margin-bottom:16px;display:block;margin-left:auto;margin-right:auto;">
        <p style="margin:0 0 4px;font-size:13px;color:#C8A951;letter-spacing:3px;
                  text-transform:uppercase;font-weight:600;">UNA NUEVA ERA COMIENZA EN</p>
        <h1 style="margin:0 0 8px;font-size:32px;font-weight:900;color:#ffffff;
                   letter-spacing:1px;">Andrés Bello</h1>
        <p style="margin:0;font-size:22px;color:#C8A951;font-weight:700;">
          ¡Bienvenida, Agente AI <span style="color:#ffffff;">GLENDA</span>!
        </p>
        <p style="margin:16px 0 0;font-size:12px;color:#8ba4c8;letter-spacing:1px;">
          Impulsando el futuro con Ciencia, Tecnología, Ingeniería, Arte y Matemáticas
        </p>
      </div>
    </td>
  </tr>

  <!-- INTRO -->
  <tr>
    <td style="background:#ffffff;padding:36px 40px 28px;">
      <p style="margin:0 0 8px;font-size:22px;font-weight:800;color:#0a1628;">
        🚀 ¡El Colegio Andrés Bello se renueva!
      </p>
      <p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.7;">
        Estimado representante,<br><br>
        Nos complace presentarles a <strong>Glenda</strong>, nuestra asistente virtual con
        <strong>inteligencia artificial</strong>, ahora disponible en Telegram — más rápida,
        disponible las 24 horas y sin límites de tiempo de respuesta.
      </p>

      <!-- CAPABILITIES -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background:#f8faff;border-radius:10px;border:1px solid #e2e8f0;
                    margin-bottom:28px;">
        <tr>
          <td style="padding:24px 28px;">
            <p style="margin:0 0 16px;font-size:14px;font-weight:700;color:#0a1628;
                      text-transform:uppercase;letter-spacing:1px;">
              ¿Qué puede hacer Glenda por usted?
            </p>
            {capabilities}
          </td>
        </tr>
      </table>

      <!-- WA vs TG comparison -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">
        <tr>
          <td width="48%" style="background:#e8f5e9;border-radius:8px;padding:16px 20px;
                                  vertical-align:top;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#2e7d32;">
              📱 WhatsApp
            </p>
            <p style="margin:0;font-size:13px;color:#374151;line-height:1.5;">
              Glenda ya atiende por WhatsApp al {wa_number}
            </p>
          </td>
          <td width="4%">&nbsp;</td>
          <td width="48%" style="background:#e3f2fd;border-radius:8px;padding:16px 20px;
                                  vertical-align:top;">
            <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#0d47a1;">
              ✈️ Telegram — ¡Recomendado!
            </p>
            <p style="margin:0;font-size:13px;color:#374151;line-height:1.5;">
              ⚡ Más rápida · Sin límites de tiempo · Respuestas al instante
            </p>
          </td>
        </tr>
      </table>

      <!-- CTA BUTTON -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:32px;">
        <tr>
          <td align="center">
            <a href="{telegram_url}"
               style="display:inline-block;background:linear-gradient(135deg,#0088cc,#006699);
                      color:#ffffff;text-decoration:none;font-size:17px;font-weight:700;
                      padding:16px 48px;border-radius:50px;
                      box-shadow:0 4px 15px rgba(0,136,204,0.35);letter-spacing:0.5px;">
              📲 Activar Glenda en Telegram
            </a>
            <p style="margin:12px 0 0;font-size:13px;color:#6b7280;">
              Haz clic, escribe <strong>"Hola"</strong> y comienza. ¡Así de sencillo!
            </p>
            <p style="margin:8px 0 0;font-size:12px;color:#9ca3af;">
              {telegram_url}
            </p>
          </td>
        </tr>
      </table>

      <!-- BETA WARNING -->
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="background:#fff8e1;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                     padding:16px 20px;">
            <p style="margin:0;font-size:13px;color:#78350f;line-height:1.6;">
              <strong>🚨 Período de adaptación:</strong> Glenda está en etapa de aprendizaje.
              Es posible que durante la conversación se presenten algunas situaciones o
              problemas técnicos. Si esto ocurre, por favor repórtelo inmediatamente a
              <a href="mailto:soporte@ueipab.edu.ve"
                 style="color:#b45309;font-weight:700;">soporte@ueipab.edu.ve</a>
              — su retroalimentación nos ayuda a mejorar.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#0a1628;padding:28px 40px;text-align:center;">
      <img src="{logo_url}" alt="Colegio Andrés Bello" width="48" height="48"
           style="border-radius:50%;border:2px solid #C8A951;margin-bottom:12px;
                  display:block;margin-left:auto;margin-right:auto;">
      <p style="margin:0 0 4px;font-size:14px;font-weight:700;color:#C8A951;">
        Equipo Colegio Andrés Bello 🎓
      </p>
      <p style="margin:0 0 12px;font-size:12px;color:#8ba4c8;">
        Instituto Privado Andrés Bello · El Tigre, Venezuela
      </p>
      <p style="margin:0;font-size:11px;color:#4b6080;">
        <a href="mailto:soporte@ueipab.edu.ve"
           style="color:#4b6080;text-decoration:none;">soporte@ueipab.edu.ve</a>
        &nbsp;·&nbsp;
        <a href="https://t.me/GlendaUeipabBot"
           style="color:#4b6080;text-decoration:none;">@GlendaUeipabBot</a>
      </p>
    </td>
  </tr>

</table>
<!-- End Card -->

</td></tr>
</table>
<!-- End Wrapper -->

</body>
</html>
"""

CAPABILITIES_ROWS = [
    ("💳", "Consultas sobre <strong>pagos y mensualidades</strong>"),
    ("📋", "<strong>Inscripciones</strong> y proceso de matrícula"),
    ("📅", "<strong>Actividades</strong> escolares y eventos"),
    ("🏥", "<strong>Ausencias</strong> de sus hijos por cualquier razón"),
    ("🤝", "Solicitar <strong>reunión con profesor o Director</strong>"),
    ("💳", "Pagos con <strong>Cashea</strong> y otros métodos"),
    ("🔍", "Información general del colegio y más…"),
    ("⏰", "Disponible <strong>24 horas, 7 días a la semana</strong>"),
]

def build_capabilities_html():
    rows = []
    for icon, text in CAPABILITIES_ROWS:
        rows.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin-bottom:10px;">'
            f'<tr>'
            f'<td width="32" style="vertical-align:top;padding-top:1px;">'
            f'<span style="font-size:18px;">{icon}</span></td>'
            f'<td style="vertical-align:top;font-size:14px;color:#374151;line-height:1.5;">✅ {text}</td>'
            f'</tr></table>'
        )
    return '\n'.join(rows)


def build_html(recipient_name='Representante'):
    first = recipient_name.split()[0].title() if recipient_name else 'Representante'
    intro = HTML_TEMPLATE.replace(
        'Estimado representante,',
        f'Estimado/a <strong>{first}</strong>,'
    )
    return intro.format(
        banner_url=BANNER_URL,
        logo_url=LOGO_URL,
        telegram_url=TELEGRAM_URL,
        wa_number=WA_NUMBER,
        capabilities=build_capabilities_html(),
    )


# ============================================================================
# Spreadsheet — read recipients
# ============================================================================

def get_recipients():
    import gspread
    gc = gspread.service_account(
        filename='/var/www/dev/odoo_api_bridge/gsheet_credentials.json')
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet('Customers')
    rows = ws.get_all_values()

    recipients = []
    seen_emails = set()
    for row in rows[2:]:  # skip BCV row + header row
        if len(row) < 10:
            continue
        name   = row[1].strip()
        status = row[2].strip().upper()
        emails = row[9].strip()
        if status not in ('ACTIVE', 'PIPELINE') or not emails:
            continue
        for email in emails.split(';'):
            email = email.strip().lower()
            if email and '@' in email and email not in seen_emails:
                seen_emails.add(email)
                recipients.append({'name': name, 'email': email, 'status': status})
    return recipients


# ============================================================================
# Odoo XML-RPC — send mail.mail
# ============================================================================

def connect_odoo():
    common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
    uid    = common.authenticate(ODOO['db'], ODOO['user'], ODOO['api_key'], {})
    models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")
    return uid, models


def send_email(uid, models, to_email, to_name, html_body):
    # Create with state='outgoing' — Odoo mail queue sends automatically.
    # Do NOT call mail.mail.send() via XML-RPC — it returns None (unmarshalable).
    mail_id = models.execute_kw(
        ODOO['db'], uid, ODOO['api_key'],
        'mail.mail', 'create', [{
            'subject':     '🤖 ¡Bienvenida Glenda, tu Agente AI en Telegram! — Colegio Andrés Bello',
            'email_from':  'Colegio Andrés Bello <soporte@ueipab.edu.ve>',
            'email_to':    f'{to_name} <{to_email}>',
            'body_html':   html_body,
            'state':       'outgoing',
            'auto_delete': True,
        }]
    )
    return mail_id


# ============================================================================
# Main
# ============================================================================

def main():
    mode = 'LIVE' if not DRY_RUN else ('TEST' if TEST_ONLY else 'DRY RUN')
    print(f"Glenda Telegram Email Announcement — {mode}")
    print("=" * 60)

    recipients = get_recipients()
    total_unique_emails = len(recipients)

    if TEST_ONLY or DRY_RUN:
        # Always show first 10
        print(f"Total recipients: {total_unique_emails} unique emails")
        for r in recipients[:10]:
            print(f"  [{r['status']}] {r['name']:<35} {r['email']}")
        if total_unique_emails > 10:
            print(f"  ... ({total_unique_emails - 10} more)")

    if DRY_RUN and not TEST_ONLY:
        print("\nDRY RUN — no emails sent. Use --test (CEO only) or --live (all).")
        return

    uid, models = connect_odoo()
    print(f"\nConnected to Odoo uid={uid}")

    if TEST_ONLY:
        # Single test to CEO
        html = build_html('Gustavo Perdomo')
        if not DRY_RUN:
            mid = send_email(uid, models, TEST_EMAIL, 'Gustavo Perdomo', html)
            print(f"\n✅ Test email sent to {TEST_EMAIL} (mail.mail id={mid})")
        else:
            print(f"\nDRY RUN: would send test to {TEST_EMAIL}")
        return

    # Full send
    sent = errors = 0
    for r in recipients:
        try:
            html = build_html(r['name'])
            send_email(uid, models, r['email'], r['name'], html)
            print(f"  ✓ {r['email']}")
            sent += 1
            time.sleep(0.8)   # gentle throttle — ~75/min
        except Exception as e:
            print(f"  ✗ {r['email']} — {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"Done. Sent: {sent} | Errors: {errors} | Total: {total_unique_emails}")


if __name__ == '__main__':
    main()
