#!/usr/bin/env python3
"""
Encuesta Institucional — Plan de Contingencia Académica (Modelo Bimodal)
========================================================================
Survey email sender for the bimodal contingency plan consultation.

RECIPIENTS (authoritative): the Customers tab of the Google Sheet
    1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA
  • col C (Status) == 'ACTIVE'      → the active-family filter (house rule)
  • col J (Email)                   → the address(es) we blast (';'/','-separated ok)
  • col B (Name) / col L (Phone)    → display name + WA phone
Each sheet email is matched to a res.partner (email index, then name fallback);
unmatched rows are skipped (an ACK needs a partner_id).

Service ac: votacion@ueipab.edu.ve  (the SAME voting account used by the
            2026-2027 budget vote). Used for From / CC / Reply-To and every
            mailto in this survey's artifacts.
Vote gate : notice_key 'contingencia_academica_2026'; deadline 2026-07-01 lives
            in the controller's _VOTE_DEADLINES — voting allowed through all of
            Jul 1 (gate is "today > deadline" → closed).
Maps      : SÍ → /partner-ack/<token>/si → state 'continuing'
            NO → /partner-ack/<token>/no → state 'leaving'

TARGET ENVIRONMENT: TESTING (db 'testing', container 'odoo-dev-web').

ARCHITECTURE — hybrid two-stage (the Google Sheet needs google libs + creds,
which live on the HOST, not inside the Odoo container):
  • Stage 1 runs on the HOST (python3 …): reads the sheet, then re-invokes this
    same file inside the container's odoo shell, passing recipients via an env var.
  • Stage 2 runs INSIDE the container (odoo shell provides `env`): matches each
    recipient email to a partner and creates the ACK + queues the mail.mail.

USAGE (run on the HOST):
    python3 scripts/send_contingencia_vote_email.py             # DRY RUN (default)
    python3 scripts/send_contingencia_vote_email.py --test      # CEO preview (dry)
    python3 scripts/send_contingencia_vote_email.py --test --live  # real CEO send
    python3 scripts/send_contingencia_vote_email.py --live      # FULL send (sheet)

Modes:
    (none)         → DRY RUN: read sheet, match partners, report. NO writes.
    --test         → CEO only (gustavo.perdomo@ueipab.edu.ve), dry.
    --live         → create ACK + queue mail for every ACTIVE sheet recipient.
    --test --live  → real CEO send (preview one live email to the CEO).

Safe to re-run — skips partners who already voted (state != pending) or whose
email is already in an outgoing/sent mail.mail with this subject.
"""

import os
import sys
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger('contingencia_vote')

# ── Constants ────────────────────────────────────────────────────────────────
NOTICE_KEY   = 'contingencia_academica_2026'
NOTICE_LABEL = 'Plan de Contingencia Académica — Modelo Bimodal'

SUBJECT = 'Encuesta Institucional — Plan de Contingencia Académica (Modelo Bimodal)'

# votacion@ — the same voting account used by the 2026-2027 budget vote.
SENDER_NAME = 'Colegio Andrés Bello'
SENDER_ADDR = 'votacion@ueipab.edu.ve'
EMAIL_FROM  = f'{SENDER_NAME} <{SENDER_ADDR}>'
EMAIL_CC    = SENDER_ADDR
REPLY_TO    = SENDER_ADDR

LOGO_URL = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'

CEO_NAME  = 'Gustavo Perdomo'
CEO_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'

# Host-stage (sheet) config
SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
CREDS_PATH     = '/opt/odoo-dev/config/google_sheets_credentials.json'
RECIPIENTS_ENV = 'CONT_RECIPIENTS_JSON'   # host → container hand-off

# Target environment — TARGET_ENV=production switches the container + db.
# DEFAULT is testing (never prod by accident). The PROD container is only
# reachable from the prod host (10.124.0.3); run the host stage there (it needs
# google libs + creds) or hand off the recipients JSON from a host that has them.
_ENV = os.environ.get('TARGET_ENV', 'testing').strip().lower()
if _ENV in ('prod', 'production', 'db_ueipab'):
    CONTAINER, TARGET_DB = 'ueipab17', 'DB_UEIPAB'
else:
    CONTAINER, TARGET_DB = 'odoo-dev-web', 'testing'

# ── Mode resolution (env vars, read by both stages) ──────────────────────────
def _flag(name):
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')

LIVE = _flag('LIVE')
TEST = _flag('TEST')
ENSURE_PARTNERS = _flag('ENSURE_PARTNERS')   # auto-create a partner for unmatched col-J emails

# Background-style batched delivery: send BATCH_SIZE mails, pause BATCH_PAUSE
# seconds, fresh SMTP connection per batch (avoids Gmail rate-limit/idle-socket).
def _int_env(name, default):
    try:
        return max(1, int(os.environ.get(name, '').strip() or default))
    except ValueError:
        return default

BATCH_SIZE  = _int_env('BATCH_SIZE', 10)     # default groups of 10
BATCH_PAUSE = _int_env('BATCH_PAUSE', 20)    # seconds between batches


# ── HTML builder (shared) ────────────────────────────────────────────────────
def _build_html(partner_name, si_url, no_url, is_test=False):
    test_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '&#9888;&#65039; PRUEBA DE REVISI&Oacute;N &mdash; Los botones funcionan, '
        'pero este voto no cuenta para el resultado final.</div>'
    ) if is_test else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Encuesta Institucional &mdash; Plan de Contingencia Acad&eacute;mica</title>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
{test_banner}
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:28px 12px;">
<table cellpadding="0" cellspacing="0" width="600"
       style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 28px rgba(0,0,0,0.11);">

  <!-- HEADER -->
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
          &#128499;&#65039; ENCUESTA INSTITUCIONAL
        </span>
      </div>
    </td>
  </tr>

  <!-- GREETING -->
  <tr>
    <td style="padding:28px 32px 6px;">
      <p style="margin:0 0 12px;color:#1a2c5b;font-size:15px;line-height:1.6;">
        Estimado(a) <strong>{partner_name}</strong>,
      </p>
      <h2 style="margin:0 0 10px;color:#1a2c5b;font-size:17px;line-height:1.35;">
        Activaci&oacute;n del Plan de Contingencia Acad&eacute;mica (Modelo Bimodal)
      </h2>
    </td>
  </tr>

  <!-- CONTEXTO Y JUSTIFICACIÓN -->
  <tr>
    <td style="padding:6px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border-left:4px solid #f0a500;
                    border-radius:0 8px 8px 0;">
        <tr>
          <td style="padding:16px 18px;">
            <p style="margin:0 0 10px;font-size:11px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:0.5px;">
              Contexto y Justificaci&oacute;n
            </p>
            <p style="margin:0 0 12px;color:#444;font-size:14px;line-height:1.7;">
              Respetando fielmente las directrices emitidas por las autoridades
              gubernamentales orientadas a salvaguardar la integridad de nuestra
              comunidad estudiantil, es de car&aacute;cter prioritario mantener a
              los alumnos resguardados en sus hogares.
            </p>
            <p style="margin:0;color:#444;font-size:14px;line-height:1.7;">
              Ante este escenario, la instituci&oacute;n plantea el uso de medios
              tecnol&oacute;gicos como un canal seguro, eficiente y viable para
              evitar la interrupci&oacute;n del a&ntilde;o escolar. A solicitud de
              diversos representantes de la comunidad educativa, se eval&uacute;a la
              activaci&oacute;n del Plan de Contingencia Acad&eacute;mica bajo el
              modelo bimodal, utilizando exclusivamente las herramientas de
              <strong>Google Classroom</strong> y <strong>Google Meet</strong>.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- NOTA 50% + 1 -->
  <tr>
    <td style="padding:10px 32px 4px;">
      <p style="margin:0;color:#666;font-size:13px;line-height:1.6;font-style:italic;">
        Con base en el principio de decisi&oacute;n democr&aacute;tica, le
        solicitamos fijar su postura ante la siguiente consulta.
        (Nota: Esta medida se activar&aacute; de manera inmediata &uacute;nicamente
        al alcanzar el <strong>50% + 1</strong> de aprobaci&oacute;n del total de la
        plantilla).
      </p>
    </td>
  </tr>

  <!-- PREGUNTA -->
  <tr>
    <td style="padding:18px 32px 8px;text-align:center;">
      <p style="margin:0 0 6px;font-size:11px;color:#888;font-weight:bold;
                text-transform:uppercase;letter-spacing:0.5px;">
        Pregunta de la Encuesta
      </p>
      <p style="margin:0;color:#1a2c5b;font-size:16px;font-weight:bold;line-height:1.5;">
        &iquest;Est&aacute; usted de acuerdo con la activaci&oacute;n del Plan de
        Contingencia Acad&eacute;mica bajo el modelo bimodal (utilizando Google
        Classroom y Google Meet), como canal seguro de aprendizaje desde el hogar?
      </p>
    </td>
  </tr>

  <!-- OPCIÓN SÍ -->
  <tr>
    <td style="padding:18px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#e8f5e9;border:2px solid #2e7d32;border-radius:12px;">
        <tr>
          <td style="padding:18px 18px 16px;text-align:center;">
            <a href="{si_url}"
               style="display:block;background:#2e7d32;color:#fff;font-size:16px;
                      font-weight:bold;text-decoration:none;padding:15px 8px;
                      border-radius:8px;">
              &#9989; S&Iacute; ESTOY DE ACUERDO
            </a>
            <p style="margin:12px 0 0;font-size:13px;color:#1b5e20;line-height:1.6;">
              Autorizo la activaci&oacute;n del plan bimodal y me comprometo a
              implementar las herramientas tecnol&oacute;gicas institucionales.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- OPCIÓN NO -->
  <tr>
    <td style="padding:6px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f4f5f7;border:2px solid #9aa3ad;border-radius:12px;">
        <tr>
          <td style="padding:18px 18px 16px;text-align:center;">
            <a href="{no_url}"
               style="display:block;background:#5f6b7a;color:#fff;font-size:16px;
                      font-weight:bold;text-decoration:none;padding:15px 8px;
                      border-radius:8px;">
              &#10060; NO ESTOY DE ACUERDO
            </a>
            <p style="margin:12px 0 0;font-size:13px;color:#444;line-height:1.6;">
              Prefiero mantener el esquema actual y esperar nuevas disposiciones de
              las autoridades.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- DEADLINE -->
  <tr>
    <td style="padding:18px 32px 8px;text-align:center;">
      <p style="margin:0;font-size:13px;color:#555;">
        Vote antes del <strong>01 de julio de 2026</strong>.
        Puede consultar a Glenda cualquier duda sobre esta encuesta.
      </p>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#f8f9fa;border-top:1px solid #e0e0e0;
               padding:18px 32px;text-align:center;">
      <p style="margin:0 0 6px;font-size:12px;color:#888;">
        &iquest;Preguntas? Estamos para ayudarle:
      </p>
      <p style="margin:0;font-size:13px;color:#555;">
        &#9993;&#65039; <a href="mailto:votacion@ueipab.edu.ve"
           style="color:#1a2c5b;">votacion@ueipab.edu.ve</a>
        &nbsp;|&nbsp;
        &#128172; <a href="https://wa.me/584148321989"
           style="color:#1a2c5b;">Glenda WhatsApp</a>
        &nbsp;|&nbsp;
        &#128241; <a href="https://t.me/GlendaUeipabBot"
           style="color:#1a2c5b;">Glenda Telegram</a>
      </p>
      <p style="margin:8px 0 0;font-size:10px;color:#bbb;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo; &mdash; El Tigre,
        Estado Anzo&aacute;tegui
      </p>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — HOST: read the Customers sheet, then hand off to the container
# ══════════════════════════════════════════════════════════════════════════════
def _load_spreadsheet_recipients():
    """ACTIVE Customers-tab rows → [{name, email, phone}].

    Layout (verified): row 1 is a junk 'Tasa BCV' row, row 2 is the real header
    (Name/Status/Email/Phone). Reading 'Customers!A2:M' then dropping the first
    returned row lands us on the first real customer — matches the budget vote.
    Columns: B(1)=Name, C(2)=Status, J(9)=Email, L(11)=Phone.
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute().get('values', [])
    data = rows[1:]  # drop the real header row

    recips, skipped_no_email = [], 0
    for row in data:
        r = (row + [''] * 13)[:13]
        name   = r[1].strip()
        status = r[2].strip().upper()
        email  = r[9].strip()
        phone  = r[11].strip()
        if not name or status != 'ACTIVE':
            continue
        if not email:
            skipped_no_email += 1
            log.info("  (no col-J email, skipped — handle via WA separately): %s", name)
            continue
        recips.append({'name': name, 'email': email, 'phone': phone})

    log.info("Sheet: %d ACTIVE recipient(s) with a col-J email "
             "(%d ACTIVE rows had no email).", len(recips), skipped_no_email)
    return recips


def _run_host_stage():
    import argparse
    import subprocess

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Actually create ACKs + queue mail')
    parser.add_argument('--test', action='store_true', help='CEO only (gustavo.perdomo@)')
    args = parser.parse_args()

    if args.test:
        mode = 'LIVE + TEST (real CEO send)' if args.live else 'TEST (CEO preview, dry)'
        recipients = [{'name': CEO_NAME, 'email': CEO_EMAIL, 'phone': ''}]
    else:
        mode = 'LIVE (full send — Customers sheet ACTIVE)' if args.live else 'DRY RUN (no writes)'
        recipients = _load_spreadsheet_recipients()

    log.info("=" * 72)
    log.info("ENCUESTA — PLAN DE CONTINGENCIA ACADÉMICA (BIMODAL) — %s", mode)
    log.info("recipients=%d → handing off to %s (db=%s)",
             len(recipients), CONTAINER, TARGET_DB)
    log.info("=" * 72)

    if TARGET_DB == 'DB_UEIPAB' and args.live and not args.test:
        log.warning("⚠️  PRODUCTION full send to DB_UEIPAB — this emails real parents.")
        ans = input("Type 'BLAST PROD' to proceed: ").strip()
        if ans != 'BLAST PROD':
            log.info("aborted."); return 1

    if not recipients:
        log.warning("No recipients — nothing to do.")
        return 0

    # Hand off to Stage 2 inside the container. The container has no google libs,
    # so we pass the already-read recipient list via an env var and pipe THIS file
    # into the container's odoo shell (where `env` is defined → Stage 2 runs).
    child_env = [
        '-e', 'LIVE=true' if args.live else 'LIVE=',
        '-e', 'TEST=true' if args.test else 'TEST=',
        '-e', 'ENSURE_PARTNERS=true' if ENSURE_PARTNERS else 'ENSURE_PARTNERS=',
        '-e', f'BATCH_SIZE={BATCH_SIZE}',
        '-e', f'BATCH_PAUSE={BATCH_PAUSE}',
        '-e', f'{RECIPIENTS_ENV}=' + json.dumps(recipients, ensure_ascii=False),
    ]
    cmd = ['docker', 'exec', '-i', *child_env, CONTAINER,
           '/usr/bin/odoo', 'shell', '-d', TARGET_DB, '--no-http']
    with open(os.path.abspath(__file__), 'rb') as fh:
        proc = subprocess.run(cmd, stdin=fh)
    return proc.returncode


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — CONTAINER (odoo shell): match partners, create ACK, queue mail
# ══════════════════════════════════════════════════════════════════════════════
def _build_email_index():
    idx = {}
    for p in env['res.partner'].sudo().search(  # noqa: F821
            [('active', '=', True), ('email', '!=', False)]):
        for a in (p.email or '').replace(';', ',').split(','):
            a = a.strip().lower()
            if a:
                idx.setdefault(a, p.id)
    return idx


def _match_partner(rec, email_index):
    """Resolve a sheet recipient to (partner, send_to_addr) or (None, None)."""
    Partner = env['res.partner'].sudo()  # noqa: F821
    first_addr = None
    for a in (rec['email'] or '').replace(';', ',').split(','):
        a = a.strip()
        if not a:
            continue
        first_addr = first_addr or a
        pid = email_index.get(a.lower())
        if pid:
            return Partner.browse(pid), a
    hit = Partner.search([('name', 'ilike', rec['name']), ('active', '=', True)], limit=1)
    if hit:
        log.warning("  email not matched — found by name: %s (id=%d)", hit.name, hit.id)
        return hit, (first_addr or hit.email or '')
    return None, None


def _already_queued_addrs():
    """Lowercased set of addresses already in an outgoing/sent mail.mail for this
    subject — idempotency guard mirroring the budget script."""
    import re
    addrs = set()
    mails = env['mail.mail'].sudo().search([  # noqa: F821
        ('subject', 'ilike', SUBJECT),
        ('state', 'in', ['outgoing', 'sent']),
    ], limit=2000)
    for m in mails:
        for a in re.findall(r'[\w.+\-]+@[\w.\-]+', m.email_to or ''):
            addrs.add(a.lower())
    if addrs:
        log.info("Idempotency guard: %d address(es) already queued/sent — will skip",
                 len(addrs))
    return addrs


def _resolve_targets():
    """Yield (name, send_addr, phone, partner) tuples.

    Primary path: recipients handed in from the host (Customers sheet, col J),
    each matched to a partner. Fallback (manual in-container run with no hand-off):
    the ACTIVE Representante tag-25 ORM query.
    """
    raw = os.environ.get(RECIPIENTS_ENV, '').strip()
    if raw:
        recips = json.loads(raw)
        log.info("Recipients from Customers sheet (host hand-off): %d", len(recips))
        email_index = _build_email_index()
        targets, unmatched, created = [], 0, 0
        for rec in recips:
            partner, addr = _match_partner(rec, email_index)
            if not partner:
                addr = next((a.strip() for a in (rec.get('email') or '')
                             .replace(';', ',').split(',') if a.strip()), '')
                # ENSURE_PARTNERS: give every ACTIVE col-J email a ballot by
                # creating a minimal partner when none exists. Opt-in (off by
                # default) so we never silently spawn duplicates — run a DRY
                # first to see the unmatched count, then enable if wanted.
                if ENSURE_PARTNERS and addr:
                    if LIVE:
                        partner = env['res.partner'].sudo().create({  # noqa: F821
                            'name':  rec.get('name') or addr,
                            'email': addr,
                        })
                        created += 1
                        log.info("  CREATED partner for %s <%s> (id=%d)",
                                 rec.get('name'), addr, partner.id)
                    else:
                        created += 1
                        log.info("  WOULD CREATE partner for %s <%s>",
                                 rec.get('name'), addr)
                        continue   # dry: no partner to attach, skip the target
                else:
                    unmatched += 1
                    log.warning("  UNMATCHED — no partner for %s <%s>%s",
                                rec.get('name'), rec.get('email'),
                                '' if ENSURE_PARTNERS else ' (set ENSURE_PARTNERS=true to auto-create)')
                    continue
            phone = rec.get('phone') or partner.mobile or partner.phone or ''
            targets.append((rec.get('name') or partner.name, addr, phone, partner))
        if created:
            log.info("ENSURE_PARTNERS: %d partner(s) %s.", created,
                     'created' if LIVE else 'would be created')
        if unmatched:
            log.warning("%d sheet recipient(s) had no Odoo partner — skipped.", unmatched)
        return targets

    # Fallback: ORM tag-25 (manual container run, no sheet hand-off)
    log.info("No host hand-off — falling back to ORM tag-25 (Representante) query.")
    REPRESENTANTE_TAG_ID = 25
    partners = env['res.partner'].sudo().search([  # noqa: F821
        ('active', '=', True),
        ('email', '!=', False),
        ('category_id', 'in', [REPRESENTANTE_TAG_ID]),
    ])
    return [(p.name or 'Representante', p.email, p.mobile or p.phone or '', p)
            for p in partners]


def _run_container_stage():
    if LIVE and TEST:
        mode = 'LIVE + TEST (real CEO send)'
    elif TEST:
        mode = 'TEST (CEO preview, no writes)'
    elif LIVE:
        mode = 'LIVE (full send)'
    else:
        mode = 'DRY RUN (no writes)'

    log.info("-" * 72)
    log.info("[container] %s  db=%s  notice_key=%s", mode,
             env.cr.dbname, NOTICE_KEY)  # noqa: F821
    log.info("-" * 72)

    base = env['ir.config_parameter'].sudo().get_param('web.base.url')  # noqa: F821
    log.info("web.base.url = %s", base)

    targets = _resolve_targets()
    if not targets:
        log.warning("No targets resolved — nothing to do.")
        return

    Ack  = env['partner.communication.ack'].sudo()   # noqa: F821
    Mail = env['mail.mail'].sudo()                    # noqa: F821
    already = _already_queued_addrs() if LIVE else set()

    queued = skipped = 0
    wrote = False
    created_mails = []

    for name, send_addr, phone, partner in targets:
        email = CEO_EMAIL if TEST else (send_addr or '')
        if not email:
            log.warning("  SKIP %s — no email", name)
            skipped += 1
            continue

        ack = Ack.search([
            ('notice_key', '=', NOTICE_KEY),
            ('partner_id', '=', partner.id),
        ], limit=1)

        if ack and ack.state != 'pending':
            log.info("  SKIP %s — already voted (%s)", name, ack.state)
            skipped += 1
            continue

        addrs = {a.strip().lower()
                 for a in (email or '').replace(';', ',').split(',') if a.strip()}
        if already & addrs:
            log.info("  SKIP %s — email already in mail queue", name)
            skipped += 1
            continue

        if not LIVE:
            log.info("  DRY  %s <%s>%s", name, email,
                     ' [existing ACK reused]' if ack else '')
            continue

        # ── LIVE writes ──────────────────────────────────────────────────────
        if not ack:
            ack = Ack.create({
                'notice_key':    NOTICE_KEY,
                'notice_label':  NOTICE_LABEL,
                'partner_id':    partner.id,
                'partner_name':  name,
                'partner_email': email,
                'partner_phone': phone,
            })
        else:
            updates = {}
            if phone and not ack.partner_phone:
                updates['partner_phone'] = phone
            if not ack.partner_email:
                updates['partner_email'] = email
            if updates:
                ack.write(updates)

        token  = ack.token
        si_url = f"{base}/partner-ack/{token}/si"
        no_url = f"{base}/partner-ack/{token}/no"
        html   = _build_html(name, si_url, no_url, is_test=TEST)

        vals = {
            'subject':    SUBJECT,
            'email_from': EMAIL_FROM,
            'email_to':   f'{name} <{email}>',
            'reply_to':   REPLY_TO,
            'body_html':  html,
            'state':      'outgoing',
        }
        if not TEST:                      # don't CC votacion@ on test previews
            vals['email_cc'] = EMAIL_CC
        created_mails.append(Mail.create(vals))
        wrote = True
        queued += 1
        log.info("  QUEUED %s <%s>", name, email)

    # Persist the queued mails (state='outgoing') before sending, so a crash
    # mid-blast never loses them — Odoo's mail cron would drain any remainder.
    if wrote:
        env.cr.commit()  # noqa: F821
        log.info("Committed %d queued mail(s).", queued)

    # ── Send in background-style BATCHES of BATCH_SIZE with a pause + a fresh
    #    SMTP connection per batch (mitigates Gmail rate-limit / idle-socket
    #    SSLEOFError seen on large blasts). Each batch commits independently.
    if LIVE and created_mails:
        import time
        total = len(created_mails)
        sent_ok = 0
        for i in range(0, total, BATCH_SIZE):
            batch = created_mails[i:i + BATCH_SIZE]
            n = (i // BATCH_SIZE) + 1
            try:
                # raise_exception=False → one bad address won't abort the batch;
                # a fresh send() opens its own SMTP connection per batch.
                env['mail.mail'].browse([m.id for m in batch]).send(  # noqa: F821
                    raise_exception=False)
                sent_ok += len(batch)
                log.info("  batch %d: sent %d (%d/%d total)",
                         n, len(batch), min(i + BATCH_SIZE, total), total)
            except Exception as exc:
                log.warning("  batch %d send error (left outgoing for cron): %s", n, exc)
            env.cr.commit()  # noqa: F821
            if i + BATCH_SIZE < total:
                time.sleep(BATCH_PAUSE)
        log.info("Batched send done: %d/%d sent (BATCH_SIZE=%d, pause=%ss).",
                 sent_ok, total, BATCH_SIZE, BATCH_PAUSE)

    log.info("-" * 72)
    log.info("QUEUED: %d  |  SKIPPED: %d  |  mode=%s", queued, skipped, mode)
    log.info("-" * 72)


# ── Stage dispatch ───────────────────────────────────────────────────────────
try:
    env  # noqa: F821  (defined only under `odoo shell`)
    _IN_SHELL = True
except NameError:
    _IN_SHELL = False

if _IN_SHELL:
    _run_container_stage()
else:
    sys.exit(_run_host_stage())
