# -*- coding: utf-8 -*-
"""
wire_enrollment_inscripcion.py
──────────────────────────────
Wire the enrollment funnel to send from the dedicated admissions inbox
**inscripcion@ueipab.edu.ve** instead of soporte@ (avoids support-queue
congestion from the S0 blast). Idempotent. DRY by default; --live to apply.

Sets these ir.config_parameter (read by enrollment_journey._enroll_addr):
    enrollment.notify_from   = "Colegio Andrés Bello - Inscripción <inscripcion@…>"
    enrollment.reply_to      = inscripcion@ueipab.edu.ve
    enrollment.contact       = inscripcion@ueipab.edu.ve     (mailto links in bodies)
    enrollment.escalation_to = inscripcion@ueipab.edu.ve     (revision requests)
  (enrollment.internal_to stays unset → default pagos@; enrollment.blast_cc stays
   unset → default '' = NO CC on the blast.)

And creates/updates a dedicated outgoing mail server so only From=inscripcion@
mail routes through it (from_filter), authenticated as that account:
    smtp.gmail.com:587 STARTTLS, user inscripcion@, from_filter inscripcion@

The SMTP app password is read from env **INSCRIPCION_SMTP_PASS** (never hardcoded
here). Without it, --live still sets the params but skips the mail-server step.

Usage:
    python3 scripts/wire_enrollment_inscripcion.py                      # DRY (prod)
    INSCRIPCION_SMTP_PASS='xxxx' python3 scripts/wire_enrollment_inscripcion.py --live
    (prod creds come from config/production.json)
"""
import json
import os
import sys
import xmlrpc.client

LIVE = '--live' in sys.argv

INS = 'inscripcion@ueipab.edu.ve'
FROM_DISPLAY = 'Colegio Andrés Bello - Inscripción <%s>' % INS

PARAMS = {
    'enrollment.notify_from':   FROM_DISPLAY,
    'enrollment.reply_to':      INS,
    'enrollment.contact':       INS,
    'enrollment.escalation_to': INS,
}

MAIL_SERVER = {
    'name': 'Inscripciones (inscripcion@ueipab.edu.ve)',
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_encryption': 'starttls',
    'smtp_user': INS,
    'from_filter': INS,
    'sequence': 5,
}

cfg = json.load(open('config/production.json'))['production']['xmlrpc']
URL, DB, USER, KEY = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, USER, KEY, {})
if not uid:
    sys.exit('ERROR: XML-RPC authentication failed')
models = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)


def kw(model, method, a=None, k=None):
    return models.execute_kw(DB, uid, KEY, model, method, a or [], k or {})


print('=== wire_enrollment_inscripcion [%s] → %s (%s) ===\n'
      % ('LIVE' if LIVE else 'DRY-RUN', URL, DB))

# 1) config parameters
print('— Config parameters —')
for k, v in PARAMS.items():
    print('  set %-28s = %s' % (k, v))
    if LIVE:
        kw('ir.config_parameter', 'set_param', [k, v])

# 2) dedicated mail server
print('\n— Dedicated outgoing mail server (from_filter=%s) —' % INS)
smtp_pass = os.environ.get('INSCRIPCION_SMTP_PASS', '').strip()
if not smtp_pass:
    print('  ⚠ INSCRIPCION_SMTP_PASS not set — skipping mail-server create/update.')
else:
    existing = kw('ir.mail_server', 'search', [[['smtp_user', '=', INS]]])
    vals = dict(MAIL_SERVER, smtp_pass=smtp_pass)
    if not LIVE:
        print('  would %s ir.mail_server %s' % ('update' if existing else 'create', existing or ''))
    elif existing:
        kw('ir.mail_server', 'write', [existing, vals])
        print('  updated ir.mail_server id=%s' % existing)
    else:
        sid = kw('ir.mail_server', 'create', [vals])
        print('  created ir.mail_server id=%s' % sid)

# 3) verification (read-only)
print('\n— Verification —')
for k in list(PARAMS) + ['enrollment.internal_to', 'enrollment.blast_cc']:
    print('  %-28s = %r' % (k, kw('ir.config_parameter', 'get_param', [k])))
srv = kw('ir.mail_server', 'search_read', [[['smtp_user', '=', INS]]],
         {'fields': ['name', 'smtp_host', 'smtp_port', 'smtp_encryption', 'from_filter']})
print('  mail server:', srv[0] if srv else '(none)')

print('\n=== %s complete ===' % ('LIVE' if LIVE else 'DRY-RUN'))
if not LIVE:
    print('Re-run with --live (and INSCRIPCION_SMTP_PASS set) to apply.')
