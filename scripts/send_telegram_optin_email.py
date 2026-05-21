#!/usr/bin/env python3
"""
send_telegram_optin_email.py
-----------------------------
Personalized Telegram opt-in campaign for UEIPAB Representante parents.

Each parent receives a unique deep-link t.me/GlendaUeipabBot?start=FAM_{token}
that, when clicked, permanently links their Telegram account to their school
contact — enabling Telegram-first blasts for future campaigns (no WA anti-spam).

Sources:
  - Google Sheets Customers tab (ACTIVE rows) — name, email, col J
  - Odoo production: partner.communication.ack (notice_key=budget_consulta_2026_2027)
    token used as FAM_ payload

Usage:
    python3 scripts/send_telegram_optin_email.py            # dry-run
    python3 scripts/send_telegram_optin_email.py --test     # CEO preview only
    python3 scripts/send_telegram_optin_email.py --live     # send to all active parents
"""

import json
import logging
import re
import sys
import time
import unicodedata
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)

TEST_ONLY  = '--test' in sys.argv
DRY_RUN    = '--live' not in sys.argv and not TEST_ONLY

TEST_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'
SHEET_ID   = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'

LOGO_URL    = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
BANNER_URL  = 'https://dev.ueipab.edu.ve/flyers/glenda_banner.png'
TELEGRAM_BOT = 'https://t.me/GlendaUeipabBot'
NOTICE_KEY   = 'budget_consulta_2026_2027'

PROD_CFG = '/opt/odoo-dev/config/production.json'
GSHEET_CREDS = '/opt/odoo-dev/config/google_sheets_credentials.json'
LAST_GRADE = '5to. Año'  # single-student families in this grade are excluded


# ── Odoo connection ────────────────────────────────────────────────────────────

def connect_odoo():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    url, db, user, key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
    uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, db, uid, key, url


def load_pdvsa_leaver_emails(models, db, uid, key):
    """Return lowercase email set of PDVSA parents who voted Opción B (no continuará)."""
    rows = models.execute_kw(db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', 'pdvsa_continuacion_2026_2027'], ['state', '=', 'leaving']]],
        {'fields': ['partner_name', 'partner_email'], 'limit': 100})
    emails = set()
    for r in rows:
        for em in (r.get('partner_email') or '').lower().split(';'):
            em = em.strip()
            if em:
                emails.add(em)
    log.info('PDVSA leavers: %d parents, %d emails to exclude', len(rows), len(emails))
    return emails


def load_ack_tokens(models, db, uid, key):
    """Return dict: email.lower() → token for all budget vote ACK records."""
    acks = models.execute_kw(db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', NOTICE_KEY]]],
        {'fields': ['partner_email', 'token', 'partner_name'], 'limit': 0})
    token_map = {}
    for a in acks:
        if not a.get('token'):
            continue
        for em in (a['partner_email'] or '').lower().split(';'):
            em = em.strip()
            if em:
                token_map[em] = {'token': a['token'], 'name': a['partner_name']}
    log.info('ACK tokens loaded: %d email keys', len(token_map))
    return token_map


# ── Google Sheet ───────────────────────────────────────────────────────────────

def load_akdemia_exclusions(svc):
    """Return set of parent names (uppercase) whose ALL Akdemia students are LAST_GRADE.
    Source: Akdemia2526 tab (authoritative enrollment). Matching by last-name tokens + phone.
    """
    ak = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Akdemia2526!A3:P').execute().get('values', [])
    ak_students = []
    for row in ak[1:]:
        r     = (row + [''] * 16)[:16]
        grade = r[0].strip()
        nombre = r[2].strip()
        apell  = r[4].strip()
        phone  = re.sub(r'\D', '', r[3])[-10:] if r[3] else ''
        if grade and nombre:
            ak_students.append({'grade': grade, 'tok': _tok(apell), 'phone': phone})

    cu = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Customers!A2:M').execute().get('values', [])
    excluded = set()
    for row in cu[1:]:
        r      = (row + [''] * 13)[:13]
        name   = r[1].strip()
        status = r[2].strip().upper()
        phone1 = re.sub(r'\D', '', r[10])[-10:] if r[10] else ''
        phone2 = re.sub(r'\D', '', r[11])[-10:] if r[11] else ''
        if not name or status != 'ACTIVE':
            continue
        pt     = {w for w in _tok(name) if len(w) >= 4}
        phones = {phone1, phone2} - {''}
        matched = [s for s in ak_students
                   if (phones & {s['phone']}) or (pt & s['tok'])]
        if matched and all(s['grade'] == LAST_GRADE for s in matched):
            excluded.add(name.upper())

    log.info('Akdemia: %d %s-only families excluded', len(excluded), LAST_GRADE)
    return excluded


def _tok(n):
    n2 = unicodedata.normalize('NFD', n.lower())
    n2 = ''.join(c for c in n2 if unicodedata.category(c) != 'Mn')
    return set(re.sub(r'[^a-z ]', '', n2).split())


def load_sheet_recipients(svc, pdvsa_leaver_emails=None):
    """Load ACTIVE parents — email from col J.
    Excludes: (1) Akdemia 5to. Año only families, (2) PDVSA Opción B leavers.
    """
    akdemia_excl = load_akdemia_exclusions(svc)
    pdvsa_excl   = pdvsa_leaver_emails or set()

    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Customers!A2:M').execute().get('values', [])
    data = rows[1:]

    recipients = []
    skipped_ak = skipped_pdvsa = 0
    for row in data:
        r          = (row + [''] * 13)[:13]
        name       = r[1].strip()
        status     = r[2].strip().upper()
        emails_raw = r[9].strip()   # col J
        if not name or status != 'ACTIVE':
            continue
        emails = [e.strip().lower() for e in emails_raw.split(';') if e.strip()]
        if name.upper() in akdemia_excl:
            log.info('[SKIP-5TO] %s — all Akdemia students in %s', name, LAST_GRADE)
            skipped_ak += 1
            continue
        if pdvsa_excl and any(e in pdvsa_excl for e in emails):
            log.info('[SKIP-PDVSA] %s — voted No continuará', name)
            skipped_pdvsa += 1
            continue
        if emails:
            recipients.append({'name': name, 'emails': emails, 'primary_email': emails[0]})

    log.info('Sheet: %d ACTIVE recipients (excl. %d 5to-Año, %d PDVSA-leaver)',
             len(recipients), skipped_ak, skipped_pdvsa)
    return recipients


# ── HTML template ──────────────────────────────────────────────────────────────

def build_html(name, deep_link):
    first = name.split()[0].title()
    return f"""\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:24px 12px;">

<table width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px;width:100%;border-radius:14px;overflow:hidden;
              box-shadow:0 4px 24px rgba(0,0,0,0.12);">

  <!-- SCHOOL LOGO HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#0a1628 0%,#1a3a6b 100%);
               padding:28px 32px;text-align:center;">
      <img src="{LOGO_URL}" alt="Colegio Andrés Bello" width="72" height="72"
           style="border-radius:50%;border:3px solid #ffffff;
                  display:block;margin:0 auto 14px;"/>
      <div style="font-size:11px;color:#ffffff;
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;">
        Colegio Andrés Bello — UEIPAB
      </div>
      <div style="font-size:20px;font-weight:800;color:#ffffff;">
        ¡Glenda ya está en Telegram!
      </div>
      <div style="font-size:13px;color:#ffffff;font-weight:600;margin-top:4px;">
        Vincula tu cuenta y recibe todo al instante — gratis
      </div>
    </td>
  </tr>

  <!-- TELEGRAM BANNER -->
  <tr>
    <td style="padding:0;background:#0088cc;">
      <a href="{deep_link}" style="display:block;text-decoration:none;">
        <img src="{BANNER_URL}"
             alt="Glenda en Telegram"
             width="600" style="width:100%;max-width:600px;display:block;border:0;"
             onerror="this.style.display='none'"/>
      </a>
    </td>
  </tr>

  <!-- TELEGRAM STRIP -->
  <tr>
    <td style="background:#0088cc;padding:10px 32px;text-align:center;">
      <p style="margin:0;font-size:14px;font-weight:700;color:#ffffff;letter-spacing:0.3px;">
        ✈️ &nbsp;@GlendaUeipabBot &nbsp;·&nbsp; Disponible 24/7 · Gratis
      </p>
    </td>
  </tr>

  <!-- BODY -->
  <tr>
    <td style="background:#ffffff;padding:36px 40px 28px;">

      <p style="margin:0 0 6px;font-size:22px;font-weight:800;color:#0a1628;">
        Hola, {first} 👋
      </p>
      <p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.7;">
        Glenda, nuestra asistente virtual con <strong>inteligencia artificial</strong>,
        ya está disponible en <strong>Telegram</strong> — y queremos que seas
        de los primeros en vincular tu cuenta para disfrutar de una experiencia
        completamente personalizada.
      </p>

      <!-- ADVANTAGES -->
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#f8faff;border-radius:10px;border:1px solid #e2e8f0;
                    margin-bottom:28px;">
        <tr>
          <td style="padding:24px 28px;">
            <p style="margin:0 0 16px;font-size:13px;font-weight:700;color:#0a1628;
                      text-transform:uppercase;letter-spacing:1px;">
              ¿Por qué vincular tu Telegram con Glenda?
            </p>

            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:8px 0;vertical-align:top;width:32px;
                            font-size:20px;">⚡</td>
                <td style="padding:8px 0;vertical-align:top;">
                  <strong style="color:#0a1628;">Respuestas instantáneas</strong><br/>
                  <span style="font-size:13px;color:#6b7280;">
                    Sin tiempos de espera — Glenda responde en segundos, día y noche.
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;vertical-align:top;font-size:20px;">🎯</td>
                <td style="padding:8px 0;vertical-align:top;">
                  <strong style="color:#0a1628;">Notificaciones personalizadas</strong><br/>
                  <span style="font-size:13px;color:#6b7280;">
                    Recordatorios de pagos, comunicados importantes y novedades
                    enviados directamente a ti — sin saturar tu WhatsApp.
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;vertical-align:top;font-size:20px;">💬</td>
                <td style="padding:8px 0;vertical-align:top;">
                  <strong style="color:#0a1628;">Consultas de saldo e inscripción</strong><br/>
                  <span style="font-size:13px;color:#6b7280;">
                    Pregunta por tu estado de cuenta, opciones de inscripción 2026-2027
                    o cualquier duda — Glenda tiene toda la información.
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;vertical-align:top;font-size:20px;">🔒</td>
                <td style="padding:8px 0;vertical-align:top;">
                  <strong style="color:#0a1628;">Cuenta vinculada = información exacta</strong><br/>
                  <span style="font-size:13px;color:#6b7280;">
                    Al vincular tu cuenta, Glenda te reconoce automáticamente y te
                    brinda información precisa sobre tus hijos y tu familia.
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 0;vertical-align:top;font-size:20px;">🆓</td>
                <td style="padding:8px 0;vertical-align:top;">
                  <strong style="color:#0a1628;">Completamente gratuito</strong><br/>
                  <span style="font-size:13px;color:#6b7280;">
                    Telegram es gratis. Glenda en Telegram es gratis. Sin costo adicional.
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <!-- CTA BUTTON -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
        <tr>
          <td align="center">
            <a href="{deep_link}"
               style="display:inline-block;background:linear-gradient(135deg,#0088cc,#006aaa);
                      color:#ffffff;font-size:16px;font-weight:800;text-decoration:none;
                      padding:16px 48px;border-radius:50px;
                      box-shadow:0 4px 14px rgba(0,136,204,0.4);
                      letter-spacing:0.5px;">
              ✈️ &nbsp;Vincular mi cuenta en Telegram
            </a>
            <p style="margin:10px 0 0;font-size:12px;color:#9ca3af;text-align:center;">
              Un solo clic — abre Telegram y vincula automáticamente
            </p>
          </td>
        </tr>
      </table>

      <!-- HOW IT WORKS -->
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#f0fdf4;border-radius:10px;border:1px solid #bbf7d0;
                    margin-bottom:28px;">
        <tr>
          <td style="padding:20px 24px;">
            <p style="margin:0 0 12px;font-size:13px;font-weight:700;color:#14532d;
                      text-transform:uppercase;letter-spacing:1px;">
              ¿Cómo funciona? — 3 pasos
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:4px 0;font-size:13px;color:#374151;">
                  <span style="font-weight:800;color:#16a34a;">1.</span>
                  Haz clic en el botón azul de arriba
                </td>
              </tr>
              <tr>
                <td style="padding:4px 0;font-size:13px;color:#374151;">
                  <span style="font-weight:800;color:#16a34a;">2.</span>
                  Se abre Telegram — presiona <strong>Iniciar / Start</strong>
                </td>
              </tr>
              <tr>
                <td style="padding:4px 0;font-size:13px;color:#374151;">
                  <span style="font-weight:800;color:#16a34a;">3.</span>
                  ¡Listo! Tu cuenta queda vinculada automáticamente con el colegio
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>

      <!-- WHATSAPP STILL WORKS -->
      <div style="background:#fff8e1;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;
                  padding:14px 18px;margin-bottom:20px;font-size:13px;color:#78350f;">
        <strong>¿No usas Telegram?</strong> No hay problema — Glenda sigue disponible
        en WhatsApp al <strong>+58 414-832-1989</strong> como siempre. Telegram es
        una opción adicional, no un reemplazo.
      </div>

    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#f8fafc;padding:20px 32px;text-align:center;
               border-top:1px solid #e2e8f0;">
      <img src="{LOGO_URL}" alt="UEIPAB" width="40" height="40"
           style="border-radius:50%;margin-bottom:10px;display:block;margin:0 auto 10px;"/>
      <p style="margin:0;font-size:12px;color:#6b7280;">
        Colegio Andrés Bello — UEIPAB &nbsp;·&nbsp;
        <a href="mailto:soporte@ueipab.edu.ve"
           style="color:#0088cc;text-decoration:none;">soporte@ueipab.edu.ve</a>
      </p>
      <p style="margin:6px 0 0;font-size:11px;color:#9ca3af;">
        Este correo fue enviado a {name} como representante registrado del colegio.
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    models, db, uid, key, odoo_url = connect_odoo()
    token_map           = load_ack_tokens(models, db, uid, key)
    pdvsa_leaver_emails = load_pdvsa_leaver_emails(models, db, uid, key)

    creds = Credentials.from_service_account_file(
        GSHEET_CREDS, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc        = build('sheets', 'v4', credentials=creds)
    recipients = load_sheet_recipients(svc, pdvsa_leaver_emails=pdvsa_leaver_emails)

    mode = 'DRY RUN' if DRY_RUN else ('TEST' if TEST_ONLY else 'LIVE')
    log.info('=== %s MODE ===', mode)

    if TEST_ONLY:
        # Send preview to CEO using Gustavo's token
        test_token = token_map.get('gustavo.perdomo@gmail.com', {}).get('token', 'PREVIEW-TOKEN')
        deep_link  = f'{TELEGRAM_BOT}?start=FAM_{test_token}'
        html       = build_html('Gustavo Perdomo', deep_link)
        mail_id = models.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
            'subject':    '[PREVIEW] ¡Vincula tu cuenta de Telegram con Glenda — UEIPAB!',
            'email_from': 'Colegio Andrés Bello <soporte@ueipab.edu.ve>',
            'email_to':   TEST_EMAIL,
            'body_html':  html,
            'state':      'outgoing',
        }]])
        mid = mail_id[0] if isinstance(mail_id, list) else mail_id
        models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
        log.info('Preview sent — mail.mail id=%s to %s | deep_link=%s', mid, TEST_EMAIL, deep_link)
        return

    sent = skipped = 0
    for r in recipients:
        name   = r['name']
        emails = r['emails']

        # Match to ACK token — try each email
        ack = None
        matched_email = None
        for em in emails:
            if em in token_map:
                ack = token_map[em]
                matched_email = em
                break

        if not ack:
            log.warning('[SKIP] %s — no ACK token found (emails: %s)', name, emails)
            skipped += 1
            continue

        deep_link = f'{TELEGRAM_BOT}?start=FAM_{ack["token"]}'
        html      = build_html(name, deep_link)
        subject   = '¡Vincula tu cuenta de Telegram con Glenda — UEIPAB!'

        if DRY_RUN:
            log.info('[DRY] %s | %s | %s', name, matched_email, deep_link)
            sent += 1
            continue

        mail_id = models.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
            'subject':    subject,
            'email_from': 'Colegio Andrés Bello <soporte@ueipab.edu.ve>',
            'email_to':   matched_email,
            'reply_to':   'soporte@ueipab.edu.ve',
            'body_html':  html,
            'state':      'outgoing',
        }]])
        mid = mail_id[0] if isinstance(mail_id, list) else mail_id
        log.info('[SENT] %s | %s | mail=%s | %s', name, matched_email, mid, deep_link)
        sent += 1
        time.sleep(0.3)

    # Trigger mail queue once after all creates
    if not DRY_RUN:
        models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])

    log.info('Done — sent: %d | skipped (no token): %d | mode: %s', sent, skipped, mode)


if __name__ == '__main__':
    main()
