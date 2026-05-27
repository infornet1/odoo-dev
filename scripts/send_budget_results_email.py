#!/usr/bin/env python3
"""
Resultados Consulta Presupuestaria 2026-2027 — Email Blast
===========================================================
Sends the official voting-results announcement to all parents in the
Customers sheet (col J = email).

FROM:     soporte@ueipab.edu.ve
REPLY-TO: pagos@ueipab.edu.ve
SOURCE:   Google Sheets 1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA — Customers!A2:M

Usage:
    python3 scripts/send_budget_results_email.py            # dry-run (no sends)
    python3 scripts/send_budget_results_email.py --preview  # CEO preview only
    python3 scripts/send_budget_results_email.py --live     # full blast
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
SUBJECT        = '✅ Resultados Consulta Presupuestaria 2026-2027 — Instituto Andrés Bello'

RESULTS_DOC    = ('https://docs.google.com/document/d/'
                  '1GSGzXLxGaaMvYtbyJuGki5KFodmpoy5OyHk0fm4e2fg/edit?usp=sharing')

CEO_EMAIL      = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME       = 'Gustavo Perdomo'

MAIL_QUEUE_CRON_ID = 3   # "Mail: Email Queue Manager"
SEND_DELAY         = 0.1  # seconds between mail.mail creates

# Extra institutional recipients always included in the blast (not in Customers sheet)
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
    """Return list of {name, email} for all rows with an email in col J."""
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
        # Handle semicolon-separated addresses — take the first valid one
        primary = next((e.strip() for e in email.replace(',', ';').split(';') if e.strip()), '')
        if not primary:
            continue
        key = primary.lower()
        if key in seen_emails:
            log.debug("SKIP duplicate: %s", primary)
            continue
        seen_emails.add(key)
        recipients.append({'name': name or primary, 'email': primary})

    log.info("Sheet: %d unique recipient emails loaded", len(recipients))
    return recipients


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(recipient_name: str, is_preview: bool = False) -> str:
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
<title>Resultados Consulta Presupuestaria 2026-2027</title>
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
      <img src="{LOGO_URL}" alt="Colegio Andr&eacute;s Bello" width="80" height="80"
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
          📊 RESULTADOS — CONSULTA PRESUPUESTARIA 2026-2027
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ SUCCESS BANNER ══ -->
  <tr>
    <td style="background:#eafaf1;border-bottom:3px solid #27ae60;
               padding:16px 32px;text-align:center;">
      <p style="margin:0;font-size:16px;font-weight:bold;color:#1e8449;">
        ✅ &iexcl;Votaci&oacute;n completada con &eacute;xito!
      </p>
    </td>
  </tr>

  <!-- ══ GREETING ══ -->
  <tr>
    <td style="padding:28px 32px 10px;">
      <p style="margin:0 0 10px;color:#1a2c5b;font-size:15px;line-height:1.6;">
        Estimad@s <strong>{recipient_name}</strong>,
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Queremos informarles que ha finalizado con &eacute;xito nuestro proceso de
        votaci&oacute;n para la nueva estructura de costos del pr&oacute;ximo
        per&iacute;odo escolar. Gracias a ustedes, alcanzamos una
        <strong>participaci&oacute;n del 64%</strong>, cumpliendo con el
        qu&oacute;rum requerido.
      </p>
    </td>
  </tr>

  <!-- ══ RESULT BOX ══ -->
  <tr>
    <td style="padding:16px 32px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:linear-gradient(135deg,#eafaf1 0%,#d5f5e3 100%);
                    border:2px solid #27ae60;border-radius:12px;">
        <tr>
          <td style="padding:22px 24px;text-align:center;">
            <div style="font-size:13px;font-weight:bold;color:#1e8449;
                        text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">
              Opci&oacute;n Seleccionada por la Mayor&iacute;a
            </div>
            <div style="font-size:32px;font-weight:bold;color:#1a2c5b;line-height:1.1;">
              📊 Opci&oacute;n N&uacute;m. 1
            </div>
            <div style="margin-top:10px;font-size:13px;color:#555;">
              Mensualidad <strong>$218,88</strong> &bull;
              Pronto pago <strong>$207,93</strong>
              <br/>(vigente desde el 1 de septiembre de 2026)
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ STATS BAR ══ -->
  <tr>
    <td style="padding:0 32px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f0f4fa;border-radius:10px;">
        <tr>
          <td width="50%" style="text-align:center;padding:14px 8px;">
            <div style="font-size:28px;font-weight:bold;color:#1a2c5b;">64%</div>
            <div style="font-size:11px;color:#666;margin-top:3px;">
              Participaci&oacute;n de Representantes
            </div>
          </td>
          <td width="50%" style="text-align:center;padding:14px 8px;
              border-left:1px solid #dde;">
            <div style="font-size:28px;font-weight:bold;color:#27ae60;">✅</div>
            <div style="font-size:11px;color:#666;margin-top:3px;">
              Qu&oacute;rum Requerido Alcanzado
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ BODY ══ -->
  <tr>
    <td style="padding:0 32px 20px;">
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Para conocer todos los detalles de los resultados, los montos aprobados
        y nuestra promoci&oacute;n especial de inscripci&oacute;n, los invitamos
        a leer el comunicado oficial:
      </p>
    </td>
  </tr>

  <!-- ══ CTA BUTTON ══ -->
  <tr>
    <td style="padding:0 32px 28px;text-align:center;">
      <a href="{RESULTS_DOC}"
         style="display:inline-block;background:linear-gradient(135deg,#1a2c5b,#2471a3);
                color:#fff;text-decoration:none;font-size:15px;font-weight:bold;
                padding:14px 36px;border-radius:30px;
                box-shadow:0 4px 14px rgba(26,44,91,0.35);">
        🔗 Ver Comunicado Oficial
      </a>
    </td>
  </tr>

  <!-- ══ EARLY-BIRD REMINDER ══ -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border-left:4px solid #f0a500;
                    border-radius:0 8px 8px 0;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 6px;font-size:11px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:0.5px;">
              🎁 Promoci&oacute;n Especial de Inscripci&oacute;n Anticipada
            </p>
            <p style="margin:0;font-size:13px;color:#444;line-height:1.65;">
              Hasta el <strong>31 de julio de 2026</strong>: inscripci&oacute;n
              <strong>$187,51</strong> &bull; mensualidad de septiembre
              <strong>$197,38</strong>.<br/>
              Para iniciar su inscripci&oacute;n o consultar su estado de cuenta,
              escriba a
              <a href="mailto:pagos@ueipab.edu.ve"
                 style="color:#1a2c5b;font-weight:bold;">pagos@ueipab.edu.ve</a>
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ CLOSING ══ -->
  <tr>
    <td style="padding:0 32px 28px;">
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Agradecemos su valiosa participaci&oacute;n y compromiso con nuestra
        comunidad educativa 🤝.
      </p>
      <p style="margin:14px 0 0;color:#1a2c5b;font-size:14px;font-weight:bold;text-align:center;">
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
        'subject':        SUBJECT,
        'email_from':     EMAIL_FROM,
        'reply_to':       REPLY_TO,
        'email_to':       to_email,
        'body_html':      html,
        'state':          'outgoing',
        'auto_delete':    True,
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
    parser = argparse.ArgumentParser(description='Budget results email blast')
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
        # Single preview send to CEO
        html = _build_html('padres y representantes', is_preview=True)
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
        html = _build_html('padres y representantes')
        _create_mail(models, db, uid, key, r['email'], r['name'], html, dry_run)
        sent += 1
        if not dry_run:
            time.sleep(SEND_DELAY)

    log.info("Done — sent: %d | skipped (no email): %d", sent, skipped)

    if args.live and sent > 0:
        _trigger_mail_queue(models, db, uid, key)


if __name__ == '__main__':
    main()
