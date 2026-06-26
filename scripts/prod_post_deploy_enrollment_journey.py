# -*- coding: utf-8 -*-
"""Post-deploy config + verification for ueipab_enrollment_journey in PRODUCTION.

Run AFTER scripts/deploy_enrollment_journey_prod.sh (module copy + install +
restart). DRY_RUN by default — pass --live to apply config changes.

Applies (--live):
  1. ir.config_parameter akdemia.api_key       ← env AKDEMIA_API_KEY (required to set)
  2. ir.config_parameter akdemia.base_url       = https://api-staging.akdemia.com
  3. ir.config_parameter akdemia.min_cache_guardians = 50
  4. ir.config_parameter enrollment.report_url  = REPORT_URL (edit constant below — B1 decision)

Always (read-only verification):
  - module installed_version + dependency ueipab_sales state
  - web.base.url value (journey/contract/QR links depend on it)
  - enrollment.journey/.student/.withdrawal fields_get sanity
  - demo-journey count (fresh prod should be 0)
  - contract sequence present
  - group_enrollment_support present + outgoing mail server configured
"""
import json
import os
import sys
import xmlrpc.client

LIVE = '--live' in sys.argv
ALLOW_DEV_REPORT = '--allow-dev-report' in sys.argv   # opt-in to ship a dev-hosted report URL to prod

# ── B1 decision: where the public Annual Report is served. Until moved to a
#    prod host, the dev URL works (page is live there). Edit before --live, or
#    set env ENROLLMENT_REPORT_URL.
REPORT_URL = os.environ.get('ENROLLMENT_REPORT_URL',
                            'https://dev.ueipab.edu.ve/reporte-anual-2025-2026/')
# Akdemia API is the same endpoint for both envs (confirmed) — staging host is intentional.
AKDEMIA_BASE_URL = os.environ.get('AKDEMIA_BASE_URL', 'https://api-staging.akdemia.com')

cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
URL, DB, USER, KEY = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, USER, KEY, {})
models = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)


def kw(model, method, args=None, kwargs=None):
    return models.execute_kw(DB, uid, KEY, model, method, args or [], kwargs or {})


def set_param(key, val):
    print('  set %s = %s' % (key, (val[:12] + '…') if key.endswith('api_key') and val else val))
    if LIVE:
        kw('ir.config_parameter', 'set_param', [key, val])


print('=== MODE:', 'LIVE' if LIVE else 'DRY_RUN', '===\n')

# ── Guard: don't silently ship a dev-hosted report URL to PRODUCTION ─────────
if LIVE and 'dev.ueipab.edu.ve' in REPORT_URL and not ALLOW_DEV_REPORT:
    print('REFUSING --live: enrollment.report_url still points at dev.ueipab.edu.ve\n'
          '  → set ENROLLMENT_REPORT_URL to the prod public URL, OR pass --allow-dev-report\n'
          '    to intentionally keep parents pointed at the dev-hosted report (interim).')
    sys.exit(2)
if LIVE:
    print('About to write to PRODUCTION:')
    print('  enrollment.report_url =', REPORT_URL)
    print('  akdemia.base_url      =', AKDEMIA_BASE_URL)
    print()

# ── 1. Config params ─────────────────────────────────────────────────────────
print('— Config parameters —')
api_key = os.environ.get('AKDEMIA_API_KEY', '').strip()
if api_key:
    set_param('akdemia.api_key', api_key)
else:
    print('  ⚠ AKDEMIA_API_KEY env not set — skipping akdemia.api_key '
          '(import button will UserError until set)')
set_param('akdemia.base_url', AKDEMIA_BASE_URL)
set_param('akdemia.min_cache_guardians', '50')
set_param('enrollment.report_url', REPORT_URL)

# ── 2. Read-only verification ────────────────────────────────────────────────
print('\n— Verification (read-only) —')
for name in ('ueipab_enrollment_journey', 'ueipab_sales'):
    r = kw('ir.module.module', 'search_read',
           [[['name', '=', name]]], {'fields': ['state', 'installed_version']})
    print('  module %-26s %s' % (name, r[0] if r else 'NOT FOUND'))

wbu = kw('ir.config_parameter', 'get_param', ['web.base.url'])
print('  web.base.url:', wbu, '(journey/contract/QR links use this)')

for model in ('enrollment.journey', 'enrollment.journey.student', 'enrollment.withdrawal'):
    try:
        f = kw(model, 'fields_get', [], {'attributes': ['type']})
        print('  model %-28s ✓ (%d fields)' % (model, len(f)))
    except Exception as e:
        print('  model %-28s ✗ %s' % (model, e))

jcount = kw('enrollment.journey', 'search_count', [[]])
print('  enrollment.journey records:', jcount, '(fresh prod expected 0 — no demo data)')

seq = kw('ir.sequence', 'search_count', [[['code', '=', 'enrollment.contract']]])
print('  contract sequence present:', bool(seq))

# Check the group by its technical xml_id (name is a translatable label).
grp = kw('ir.model.data', 'search_count',
         [[['module', '=', 'ueipab_enrollment_journey'],
           ['name', '=', 'group_enrollment_support'],
           ['model', '=', 'res.groups']]])
print('  group_enrollment_support present:', bool(grp))

mailsrv = kw('ir.mail_server', 'search_count', [[]])
print('  outgoing mail servers configured:', mailsrv, '(S0/withdrawal emails need >=1)')

print('\n=== %s complete ===' % ('LIVE' if LIVE else 'DRY_RUN'))
if not LIVE:
    print('Re-run with --live to apply config params. Set AKDEMIA_API_KEY first.')
