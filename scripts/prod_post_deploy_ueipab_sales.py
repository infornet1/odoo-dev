# -*- coding: utf-8 -*-
"""Phase 7 post-deploy config + verification for ueipab_sales in PRODUCTION.

Run AFTER: module copy, `-i ueipab_sales -u ueipab_ai_agent`, container restart,
and setup_ueipab_sales_catalog.py (see UEIPAB_SALES_QUOTATION_PLAN.md §11).

DRY_RUN by default — pass --live to apply changes.

Applies (--live):
  1. res.company id=1: portal_confirmation_pay = False  (no payment provider)
  2. ir.config_parameter ueipab_sales.suppress_ai_quote_emails = True (explicit)
  3. S00001 (Gustavo's wizard test quotation): cancel + delete
  4. Smoke test: create_ai_quote(partner=7, n_students=2) → expect $973.20
     → then cancel + delete the smoke order

Always (read-only verification):
  - module versions, product/template counts, fields_get, report binding,
    outgoing-mail count snapshot
"""
import json
import sys
import xmlrpc.client

LIVE = '--live' in sys.argv

cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
URL, DB, USER, KEY = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, USER, KEY, {})
models = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object')


def kw(model, method, args=None, kwargs=None):
    return models.execute_kw(DB, uid, KEY, model, method, args or [], kwargs or {})


print('=== MODE:', 'LIVE' if LIVE else 'DRY_RUN', '===')

# ── 1. Config changes ────────────────────────────────────────────────────────
company = kw('res.company', 'read', [[1]], {'fields': ['portal_confirmation_pay']})[0]
print('portal_confirmation_pay (before):', company['portal_confirmation_pay'])
if LIVE and company['portal_confirmation_pay']:
    kw('res.company', 'write', [[1], {'portal_confirmation_pay': False}])
    print('  → set False')

suppress = kw('ir.config_parameter', 'get_param', ['ueipab_sales.suppress_ai_quote_emails'])
print('suppress_ai_quote_emails (before):', suppress)
if LIVE:
    kw('ir.config_parameter', 'set_param', ['ueipab_sales.suppress_ai_quote_emails', 'True'])
    print('  → set True')

# ── 2. Delete S00001 test quotation ─────────────────────────────────────────
s1 = kw('sale.order', 'search_read', [[['name', '=', 'S00001']]],
        {'fields': ['state', 'partner_id', 'invoice_ids']})
if s1:
    print('S00001:', s1[0]['state'], s1[0]['partner_id'], 'invoices:', s1[0]['invoice_ids'])
    if LIVE:
        oid = [s1[0]['id']]
        kw('sale.order', 'action_cancel', [oid])
        kw('sale.order', 'unlink', [oid])
        print('  → cancelled + deleted')
else:
    print('S00001: not found (already removed)')

# ── 3. Verification (read-only) ──────────────────────────────────────────────
print('\n=== VERIFICATION ===')
mods = kw('ir.module.module', 'search_read',
          [[['name', 'in', ['ueipab_sales', 'ueipab_ai_agent']]]],
          {'fields': ['name', 'state', 'latest_version']})
for x in mods:
    print('MOD %-18s %-10s %s' % (x['name'], x['state'], x['latest_version']))

n_prod = kw('product.template', 'search_count', [[['default_code', 'like', '2627']]])
n_tpl = kw('sale.order.template', 'search_count', [[]])
print('products *2627*: %d (expect 17) | quotation templates: %d (expect 12)' % (n_prod, n_tpl))

f = kw('sale.order', 'fields_get', [['is_glenda_quote', 'quote_channel']], {'attributes': ['string']})
fl = kw('sale.order.line', 'fields_get', [['ueipab_payment_due_date']], {'attributes': ['string']})
print('sale.order fields:', sorted(f.keys()), '| line field:', sorted(fl.keys()))

rep = kw('ir.actions.report', 'search_read',
         [[['report_name', '=', 'ueipab_sales.quotation_agreement']]],
         {'fields': ['name', 'binding_model_id', 'binding_type']})
print('report binding:', rep)

# ── 4. Smoke test (LIVE only) ────────────────────────────────────────────────
if LIVE:
    print('\n=== SMOKE TEST: create_ai_quote(7, 2) ===')
    q = kw('sale.order', 'create_ai_quote', [7, 2], {'channel': 'manual'})
    print('quote:', q['name'], 'total:', q['amount_total'], '(expect 973.2)',
          'llamado:', q['llamado_code'], 'validity:', q['validity_date'])
    assert abs(q['amount_total'] - 973.20) < 0.01, 'TOTAL MISMATCH'
    out_mails = kw('mail.mail', 'search_count', [[['state', '=', 'outgoing']]])
    print('outgoing mails after quote:', out_mails)
    kw('sale.order', 'action_cancel', [[q['order_id']]])
    kw('sale.order', 'unlink', [[q['order_id']]])
    print('smoke order cancelled + deleted ✓')

print('\nDONE.')
