# -*- coding: utf-8 -*-
"""
Fix advance payment email template calculation and batch template assignment.

Issue 2: Template 44 "Payslip Email - Advance Payment - Employee Delivery"
  double-applies the advance percentage.
  - net_wage is ALREADY reduced by advance % via salary rules
  - Template was computing advance_amt = net_wage * (advance_pct/100) → double-reduction
  - Fix: advance_amt = net_wage (already correct), full_salary = net_wage * (100/advance_pct)

Issue 1 (production only): Batch MARZO31-G3-50 has standard template assigned.
  Fix: set email_template_id to the advance payment template.
"""
import sys

DRY_RUN = '--live' not in sys.argv
TARGET_BATCH_NAME = 'MARZO31-G3-50'

print(f"=== Advance Payment Template Fix ===")
print(f"DRY_RUN: {DRY_RUN}")
print()

# ── Fix 2: Template body ──────────────────────────────────────────────────────

template = env['mail.template'].search([
    ('name', '=', 'Payslip Email - Advance Payment - Employee Delivery'),
    ('model_id.model', '=', 'hr.payslip'),
], limit=1)

if not template:
    print("ERROR: Template 'Payslip Email - Advance Payment - Employee Delivery' not found.")
else:
    print(f"Found template id={template.id}: {template.name}")

    OLD_SET = '<t t-set="advance_amt" t-value="(object.net_wage or 0.0) * (advance_pct / 100.0)"/>'
    NEW_SET = (
        '<t t-set="full_salary" t-value="(object.net_wage or 0.0) '
        '* (100.0 / (advance_pct if advance_pct else 100.0))"/>\n'
        '            '
        '<t t-set="advance_amt" t-value="object.net_wage or 0.0"/>'
    )
    OLD_TOTAL = "'{:,.2f}'.format((object.net_wage or 0.0) * exchange_rate)"
    NEW_TOTAL = "'{:,.2f}'.format(full_salary * exchange_rate)"

    # Must iterate explicit language keys stored in the JSONB field.
    # In Odoo 17, body_html is stored as {"en_US": "...", "es_VE": "..."}.
    # Writing with lang=False updates a neutral fallback that Python reads but
    # does NOT update the en_US key used by the UI — so each key must be fixed
    # explicitly using with_context(lang=<key>).
    for lang in ['en_US', 'es_VE']:
        tpl_ctx = template.with_context(lang=lang)
        body = str(tpl_ctx.body_html or '')
        if not body:
            print(f"  [{lang}] Empty body, skipping.")
            continue

        changed = False
        if OLD_SET in body:
            body = body.replace(OLD_SET, NEW_SET)
            changed = True
            print(f"  [{lang}] Fixed advance_amt t-set (removed double %).")
        else:
            print(f"  [{lang}] advance_amt t-set already fixed or not found.")

        if OLD_TOTAL in body:
            count = body.count(OLD_TOTAL)
            body = body.replace(OLD_TOTAL, NEW_TOTAL)
            changed = True
            print(f"  [{lang}] Fixed {count} occurrence(s) of net_wage → full_salary in totals.")
        else:
            print(f"  [{lang}] net_wage totals already fixed or not found.")

        if changed and not DRY_RUN:
            tpl_ctx.write({'body_html': body})
            print(f"  [{lang}] Written to DB.")
        elif changed:
            print(f"  [{lang}] DRY RUN — no write.")

# ── Fix 1: Batch template assignment ─────────────────────────────────────────

print()
batch = env['hr.payslip.run'].search([('name', '=', TARGET_BATCH_NAME)], limit=1)

if not batch:
    print(f"Batch '{TARGET_BATCH_NAME}' not found — skipping Fix 1 (may already be corrected).")
else:
    current_tpl = batch.email_template_id
    print(f"Batch id={batch.id} '{batch.name}': current template = {current_tpl.id} '{current_tpl.name}'")

    if template and current_tpl.id != template.id:
        if not DRY_RUN:
            batch.write({'email_template_id': template.id})
            print(f"  Updated to template id={template.id}.")
        else:
            print(f"  DRY RUN — would update to template id={template.id}.")
    else:
        print(f"  Template already correct, no change needed.")

if not DRY_RUN:
    env.cr.commit()
    print("\nCommitted.")
else:
    print("\nDRY RUN complete — re-run with --live to apply.")
