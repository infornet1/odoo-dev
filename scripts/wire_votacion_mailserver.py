# -*- coding: utf-8 -*-
"""
wire_votacion_mailserver.py
─────────────────────────────
Create/update a dedicated outgoing **ir.mail_server** so that mail with
From=**votacion@ueipab.edu.ve** (the SAME voting account used by the 2026-2027
budget vote) routes through an authenticated Gmail SMTP, while every other
From-address keeps using the default server.

This is for the survey:
    notice_key   = 'contingencia_academica_2026'
    notice_label = 'Plan de Contingencia Académica — Modelo Bimodal'
    voting window: opens 2026-06-29, CLOSES 2026-07-01 (48h)

Dedicated server config (idempotent — keyed on smtp_user):
    name            'Votación (votacion@ueipab.edu.ve)'
    smtp_host       smtp.gmail.com
    smtp_port       587
    smtp_encryption starttls
    smtp_user       votacion@ueipab.edu.ve
    from_filter     votacion@ueipab.edu.ve   (only From=votacion@ uses this server)
    sequence        5

The SMTP app password is read ONLY from env **VOTACION_SMTP_PASS** (never
hardcoded). Without it, --live still RUNS but SKIPS creating/updating the server
(no point creating a server that cannot authenticate). A clear warning is printed.

⚠ TARGET = TESTING ONLY (db 'testing', container 'odoo-dev-web'). This script does
NOT read config/production.json and does NOT touch production. It runs under the
Odoo shell `env` injected by `odoo shell -d testing`.

The dedicated ir.mail_server is BUILT here but the actual survey send still goes
through the DEFAULT mail server with votacion@ as From/CC/Reply-To headers until
DNS (DMARC/SPF/DKIM) for votacion@ is aligned and prod wiring is approved.

LIVE flag:
    DRY by default. Pass --live (argv) OR set env LIVE=true to apply.
    (odoo shell does not always forward argv cleanly, hence the env fallback.)

Invocation (TESTING):
    # DRY-RUN (no writes):
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/wire_votacion_mailserver.py

    # LIVE (creates/updates the dedicated server; needs the Gmail app password):
    docker exec -e LIVE=true -e VOTACION_SMTP_PASS='xxxxxxxxxxxxxxxx' -i \
        odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
        < /opt/odoo-dev/scripts/wire_votacion_mailserver.py
"""
import os
import sys

# LIVE from argv OR env (odoo shell may swallow argv) ------------------------
LIVE = ('--live' in sys.argv) or (os.environ.get('LIVE', '').strip().lower()
                                  in ('1', 'true', 'yes', 'on'))

VOT = 'votacion@ueipab.edu.ve'  # same voting account as the budget vote

MAIL_SERVER = {
    'name': 'Votación (votacion@ueipab.edu.ve)',
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_encryption': 'starttls',
    'smtp_user': VOT,
    'from_filter': VOT,
    'sequence': 5,
}

# `env` is injected by `odoo shell`. Guard so a stray `python3` run fails loudly.
try:
    env  # noqa: F821
except NameError:
    sys.exit('ERROR: no Odoo `env` in scope. Run under:\n'
             '  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing '
             '--no-http < scripts/wire_votacion_mailserver.py')

DB = env.cr.dbname  # noqa: F821
if DB != 'testing':
    sys.exit('ERROR: refusing to run — connected DB is %r, expected '
             "'testing'. This script is testing-only." % DB)

print('=== wire_votacion_mailserver [%s] → db=%s ==='
      % ('LIVE' if LIVE else 'DRY-RUN', DB))
print('    survey: contingencia_academica_2026  (account: %s)\n' % VOT)

# Dedicated outgoing mail server ---------------------------------------------
print('— Dedicated outgoing mail server (from_filter=%s) —' % VOT)
smtp_pass = os.environ.get('VOTACION_SMTP_PASS', '').strip()

MailServer = env['ir.mail_server']  # noqa: F821
existing = MailServer.search([('smtp_user', '=', VOT)], limit=1)
server_id = existing.id if existing else None

if not smtp_pass:
    print('  ⚠ VOTACION_SMTP_PASS not set — SKIPPING mail-server create/update.')
    print('    (A server without a working app password cannot authenticate to')
    print('     Gmail, so we do not create/modify it. Provide the env var to apply.)')
    if existing:
        print('  (an existing server id=%s is present and was left untouched)'
              % existing.id)
else:
    vals = dict(MAIL_SERVER, smtp_pass=smtp_pass)
    if not LIVE:
        print('  would %s ir.mail_server %s'
              % ('update' if existing else 'create', existing.id if existing else ''))
    elif existing:
        existing.write(vals)
        server_id = existing.id
        print('  updated ir.mail_server id=%s' % server_id)
    else:
        rec = MailServer.create(vals)
        server_id = rec.id
        print('  created ir.mail_server id=%s' % server_id)

# Verification (read-only) ---------------------------------------------------
print('\n— Verification —')
srv = MailServer.search_read(
    [('smtp_user', '=', VOT)],
    ['id', 'name', 'smtp_host', 'smtp_port', 'smtp_encryption', 'from_filter',
     'sequence'])
print('  mail server:', srv[0] if srv else '(none)')

# Commit (odoo shell does not auto-commit) -----------------------------------
if LIVE:
    env.cr.commit()  # noqa: F821
    print('\n  committed.')

# Final notice ---------------------------------------------------------------
print('\n=== %s complete ===' % ('LIVE' if LIVE else 'DRY-RUN'))
print('  final mail server id: %s' % (server_id if server_id else '(none — not created)'))
print('  ⚠ DMARC/SPF/DKIM for %s MUST align before any EXTERNAL send.' % VOT)
print('  ⚠ TESTING-ONLY: this dedicated server stays inactive for real sends')
print('    until creds + prod wiring are approved. For now the survey sends')
print('    through the DEFAULT mail server with %s as From/CC/Reply-To.' % VOT)
if not LIVE:
    print('\n  Re-run with LIVE=true (and VOTACION_SMTP_PASS set) to apply.')
