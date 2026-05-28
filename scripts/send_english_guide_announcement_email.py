#!/usr/bin/env python3
"""
Comunicado Importante: Ajuste en Guías de Inglés 2026-2027 — Email Blast
=========================================================================
Sends the official English-guide cost-adjustment announcement to all parents
in the Customers sheet (col J = email, col C = ACTIVE/PIPELINE).

FROM:     soporte@ueipab.edu.ve
REPLY-TO: pagos@ueipab.edu.ve
SOURCE:   Google Sheets 1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA — Customers!A2:M

Usage:
    python3 scripts/send_english_guide_announcement_email.py            # dry-run
    python3 scripts/send_english_guide_announcement_email.py --preview  # CEO only
    python3 scripts/send_english_guide_announcement_email.py --live     # full blast
"""

import argparse
import json
import logging
import sys
import time
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
CREDS_PATH     = '/opt/odoo-dev/config/google_sheets_credentials.json'
PROD_CFG       = '/opt/odoo-dev/config/production.json'

ODOO_URL       = 'https://odoo.ueipab.edu.ve'
LOGO_URL       = f'{ODOO_URL}/web/image/res.company/1/logo'

EMAIL_FROM     = 'Instituto Andrés Bello <soporte@ueipab.edu.ve>'
REPLY_TO       = 'pagos@ueipab.edu.ve'
SUBJECT        = '📢 Comunicado Importante: Ajuste en Guías de Inglés 2026-2027 — Instituto Andrés Bello'

ANNOUNCEMENT_DOC = 'https://docs.google.com/document/d/1LeeTB-7vk8BWSl9NH_JHZoXSiq3mvtSKpmAgWUh0r-0/edit?usp=sharing'

CEO_EMAIL      = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME       = 'Gustavo Perdomo'

MAIL_QUEUE_CRON_ID = 3
SEND_DELAY         = 0.1

# Addresses with confirmed hard-bounce DSNs in Freescout — skip to avoid noise
SKIP_EMAILS = {
    'eledeher@gmail.com',    # DAMIRIS HEREDIA — bouncing as of 2026-05-28 (conv #46552)
    'olysamg@gmail.com',     # EMIRO GONZALEZ  — failing since 2026-05-17 (conv #44815)
}

EXTRA_RECIPIENTS = [
    {'name': 'Docentes Primaria',     'email': 'docentesprimaria@ueipab.edu.ve'},
    {'name': 'Docentes Secundaria',   'email': 'docentesecundaria@ueipab.edu.ve'},
    {'name': 'Académico',             'email': 'academico@ueipab.edu.ve'},
    {'name': 'Administración',        'email': 'administracion@ueipab.edu.ve'},
    {'name': 'Jesús Rengel',          'email': 'jesus.rengel@ueipab.edu.ve'},
    {'name': 'Yelitza Chirinos',      'email': 'yelitza.chirinos@ueipab.edu.ve'},
]


# ── Config + XML-RPC ───────────────────────────────────────────────────────────

def _load_prod_cfg():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    return cfg['url'], cfg['db'], cfg['user'], cfg['api_key']


def _connect():
    url, db, user, key = _load_prod_cfg()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, key, {})
    if not uid:
        raise RuntimeError('XML-RPC authentication failed')
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, db, uid, key


def call(models, db, uid, key, model, method, args=None, kw=None):
    return models.execute_kw(db, uid, key, model, method,
                             args or [[]], kw or {})


# ── Google Sheets reader ───────────────────────────────────────────────────────

def _load_recipients():
    """Return list of {name, email} for ACTIVE/PIPELINE rows with an email in col J."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    result = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute()

    rows = result.get('values', [])[1:]  # skip header row
    seen_emails = set()
    recipients = []
    VALID_STATUSES = {'ACTIVE', 'PIPELINE'}

    for row in rows:
        r = (row + [''] * 13)[:13]
        name   = r[1].strip()          # col B
        status = r[2].strip().upper()  # col C
        email  = r[9].strip()          # col J

        if status not in VALID_STATUSES:
            log.debug("SKIP (%s): %s", status or 'no status', name)
            continue
        if not email:
            continue
        primary = next((e.strip() for e in email.replace(',', ';').split(';') if e.strip()), '')
        if not primary:
            continue
        key_e = primary.lower()
        if key_e in seen_emails:
            log.debug("SKIP duplicate: %s", primary)
            continue
        seen_emails.add(key_e)
        recipients.append({'name': name or primary, 'email': primary})

    log.info("Sheet: %d unique recipient emails loaded", len(recipients))
    return recipients


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(is_preview: bool = False) -> str:
    preview_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '⚠️ VISTA PREVIA — Este correo es solo para revisión. '
        'No ha sido enviado a los representantes.</div>'
    ) if is_preview else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Comunicado: Ajuste en Guías de Inglés 2026-2027</title>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
{preview_banner}
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:28px 12px;">
<table cellpadding="0" cellspacing="0" width="600"
       style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 28px rgba(0,0,0,0.11);">

  <!-- ══ HEADER ══ -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:36px 32px 30px;text-align:center;">
      <img src="{LOGO_URL}" alt="Instituto Andr&eacute;s Bello" width="80" height="80"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 14px;"/>
      <h1 style="margin:0;color:#fff;font-size:21px;font-weight:bold;line-height:1.3;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </h1>
      <p style="margin:5px 0 16px;color:rgba(255,255,255,0.8);font-size:13px;">
        El Tigre, Estado Anzo&aacute;tegui
      </p>
      <div style="display:inline-block;background:rgba(255,255,255,0.18);
                  border:1px solid rgba(255,255,255,0.4);border-radius:20px;
                  padding:7px 22px;">
        <span style="color:#fff;font-size:14px;font-weight:bold;">
          📢 COMUNICADO IMPORTANTE — GU&Iacute;AS DE INGL&Eacute;S 2026-2027
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ GREETING ══ -->
  <tr>
    <td style="padding:28px 32px 16px;">
      <p style="margin:0 0 14px;color:#1a2c5b;font-size:15px;line-height:1.6;">
        Estimados padres y representantes del Instituto Privado Andr&eacute;s Bello,
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Les informamos que hemos emitido un <strong>comunicado oficial</strong>
        referente a un ajuste en el costo de las <strong>gu&iacute;as de ingl&eacute;s</strong>
        para el periodo 2026-2027, debido a cambios notificados por nuestra
        consultora aliada <strong>MoA</strong>.
      </p>
    </td>
  </tr>

  <!-- ══ INFO CARD ══ -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border-left:4px solid #f0a500;
                    border-radius:0 8px 8px 0;">
        <tr>
          <td style="padding:16px 20px;">
            <p style="margin:0 0 6px;font-size:11px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:0.5px;">
              📅 Fechas l&iacute;mite y tarifa promocional
            </p>
            <p style="margin:0;font-size:13px;color:#444;line-height:1.65;">
              Para conocer los <strong>motivos de esta medida</strong> y las
              <strong>fechas l&iacute;mite</strong> para aprovechar la tarifa
              promocional, les invitamos a leer el documento completo a trav&eacute;s
              del enlace a continuaci&oacute;n.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ CTA BUTTON ══ -->
  <tr>
    <td style="padding:0 32px 28px;text-align:center;">
      <a href="{ANNOUNCEMENT_DOC}"
         style="display:inline-block;background:linear-gradient(135deg,#1a2c5b,#2471a3);
                color:#fff;text-decoration:none;font-size:15px;font-weight:bold;
                padding:14px 36px;border-radius:30px;
                box-shadow:0 4px 14px rgba(26,44,91,0.35);">
        🔗 Ver Comunicado Oficial
      </a>
    </td>
  </tr>

  <!-- ══ CLOSING ══ -->
  <tr>
    <td style="padding:0 32px 28px;">
      <p style="margin:0 0 12px;color:#444;font-size:14px;line-height:1.75;">
        Agradecemos de antemano su comprensi&oacute;n y apoyo continuo. 🤝
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Cualquier duda, estamos a su disposici&oacute;n:
        <a href="mailto:pagos@ueipab.edu.ve"
           style="color:#1a2c5b;font-weight:bold;">pagos@ueipab.edu.ve</a> ✉️
      </p>
      <p style="margin:20px 0 0;color:#1a2c5b;font-size:14px;font-weight:bold;text-align:center;">
        Atentamente,<br/>
        <span style="font-weight:normal;color:#555;">La Administraci&oacute;n</span><br/>
        <span style="font-weight:normal;color:#555;font-size:13px;">
          Instituto Privado Andr&eacute;s Bello
        </span>
      </p>
    </td>
  </tr>

  <!-- ══ FOOTER ══ -->
  <tr>
    <td style="background:#f0f4fa;padding:16px 32px;text-align:center;
               border-top:1px solid #dde;">
      <p style="margin:0;font-size:11px;color:#999;line-height:1.6;">
        Instituto Privado Andr&eacute;s Bello &bull; El Tigre, Edo. Anzo&aacute;tegui
        &bull; RIF J-08008617-1<br/>
        Consultas: <a href="mailto:soporte@ueipab.edu.ve"
                      style="color:#2471a3;">soporte@ueipab.edu.ve</a>
        &bull; Pagos: <a href="mailto:pagos@ueipab.edu.ve"
                         style="color:#2471a3;">pagos@ueipab.edu.ve</a>
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Send helpers ───────────────────────────────────────────────────────────────

def _create_mail(models, db, uid, key, to_email, to_name, html, dry_run):
    if dry_run:
        log.info("DRY-RUN → would send to: %s <%s>", to_name, to_email)
        return None
    mail_id = call(models, db, uid, key, 'mail.mail', 'create', [[{
        'subject':     SUBJECT,
        'email_from':  EMAIL_FROM,
        'reply_to':    REPLY_TO,
        'email_to':    to_email,
        'body_html':   html,
        'state':       'outgoing',
        'auto_delete': True,
    }]])
    log.info("Queued → %s <%s> (mail.mail id=%s)", to_name, to_email, mail_id)
    return mail_id


def _trigger_mail_queue(models, db, uid, key):
    log.info("Triggering mail queue cron (id=%d)…", MAIL_QUEUE_CRON_ID)
    call(models, db, uid, key, 'ir.cron', 'method_direct_trigger',
         [[MAIL_QUEUE_CRON_ID]])
    log.info("Mail queue triggered.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='English guide announcement email blast')
    parser.add_argument('--preview', action='store_true',
                        help='Send only to CEO for review')
    parser.add_argument('--live', action='store_true',
                        help='Send to all recipients from Customers sheet')
    args = parser.parse_args()

    dry_run = not (args.preview or args.live)
    if dry_run:
        log.info("DRY-RUN mode — no emails will be sent. Use --preview or --live.")

    models, db, uid, key = _connect()
    log.info("Connected to Odoo (%s / %s)", ODOO_URL, db)

    if args.preview:
        html = _build_html(is_preview=True)
        _create_mail(models, db, uid, key, CEO_EMAIL, CEO_NAME, html, dry_run=False)
        _trigger_mail_queue(models, db, uid, key)
        log.info("Preview sent to %s", CEO_EMAIL)
        return

    # Full blast or dry-run
    recipients = _load_recipients() + EXTRA_RECIPIENTS
    log.info("Recipients to process: %d (%d sheet + %d extra)",
             len(recipients), len(recipients) - len(EXTRA_RECIPIENTS), len(EXTRA_RECIPIENTS))

    sent = skipped = 0
    for r in recipients:
        if not r['email']:
            skipped += 1
            continue
        if r['email'].lower() in SKIP_EMAILS:
            log.info("SKIP (bounce): %s <%s>", r['name'], r['email'])
            skipped += 1
            continue
        html = _build_html(is_preview=False)
        _create_mail(models, db, uid, key, r['email'], r['name'], html, dry_run)
        sent += 1
        if not dry_run:
            time.sleep(SEND_DELAY)

    log.info("Done — sent: %d | skipped: %d", sent, skipped)

    if args.live and sent > 0:
        _trigger_mail_queue(models, db, uid, key)


if __name__ == '__main__':
    main()
