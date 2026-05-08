#!/usr/bin/env python3
"""
Setup: Bono Día de las Madres 2026 - Salary Structure

Creates:
  - Salary structure: BONO_MADRES
  - Earnings rule:    BONO_MADRES  (reads from ir.config_parameter)
  - NET rule:         BONO_MADRES_NET  (with PAY1 accounting)
  - ir.config_parameter: payroll.bono_madres_2026 = "12.50"

Run:
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/setup_bono_madres.py
"""

BONUS_AMOUNT_USD = "12.50"  # Default — HR changes via Settings → Technical → Parameters → System Parameters → payroll.bono_madres_2026

print("=" * 70)
print("SETUP: Bono Día de las Madres 2026")
print("=" * 70)

# ── 1. Set ir.config_parameter (HR edits this to change the bonus amount) ─
param = env['ir.config_parameter'].sudo()
if not param.get_param('payroll.bono_madres_2026'):
    param.set_param('payroll.bono_madres_2026', BONUS_AMOUNT_USD)
    print(f"\n✅ ir.config_parameter created: payroll.bono_madres_2026 = {BONUS_AMOUNT_USD}")
else:
    print(f"\n✅ ir.config_parameter already exists: payroll.bono_madres_2026 = {param.get_param('payroll.bono_madres_2026')}")

# ── 2. Resolve journal PAY1 ───────────────────────────────────────────────
journal = env['account.journal'].search([('code', '=', 'PAY1')], limit=1)
if not journal:
    print("❌ Journal PAY1 not found — aborting")
    raise SystemExit(1)
print(f"✅ Journal PAY1 found: id={journal.id}")

# ── 3. Salary structure ───────────────────────────────────────────────────
Structure = env['hr.payroll.structure']
base_struct = Structure.search([('code', '=', 'BASE')], limit=1)
existing = Structure.search([('code', '=', 'BONO_MADRES')], limit=1)
if existing:
    print(f"⚠️  Structure BONO_MADRES already exists (id={existing.id}) — skipping create")
    struct = existing
else:
    struct = Structure.create({
        'name': 'Bono Día de las Madres',
        'code': 'BONO_MADRES',
        'parent_id': False,  # No parent — flat bonus, BASE aggregators would pollute payslip lines
    })
    print(f"✅ Salary structure created: BONO_MADRES (id={struct.id})")

# ── 4. Salary rule categories ─────────────────────────────────────────────
cat_basic = env['hr.salary.rule.category'].search([('code', '=', 'BASIC')], limit=1)
cat_net   = env['hr.salary.rule.category'].search([('code', '=', 'NET')],   limit=1)
if not cat_basic or not cat_net:
    print("❌ Could not find BASIC or NET salary rule categories — aborting")
    raise SystemExit(1)
print(f"✅ Categories: BASIC id={cat_basic.id}, NET id={cat_net.id}")

# ── 5. Resolve debit/credit accounts for NET accounting ───────────────────
acc_debit  = env['account.account'].search([('code', '=', '5.1.01.10.001')], limit=1)
acc_credit = env['account.account'].search([('code', '=', '1.1.01.02.001')], limit=1)
if not acc_debit or not acc_credit:
    print(f"⚠️  Accounting accounts not found (debit={bool(acc_debit)}, credit={bool(acc_credit)})")
    print("   NET rule will be created without account config — set manually in Odoo UI")

# ── 6. Earnings rule: BONO_MADRES ─────────────────────────────────────────
Rule = env['hr.salary.rule']
# Rules link to structure via many2many (hr_structure_salary_rule_rel)
existing_earn = Rule.search([('code', '=', 'BONO_MADRES')], limit=1)
if existing_earn:
    print(f"⚠️  Rule BONO_MADRES already exists (id={existing_earn.id})")
    earn_rule = existing_earn
    if struct not in earn_rule.struct_ids:
        struct.write({'rule_ids': [(4, earn_rule.id)]})
        print("   → Linked existing rule to BONO_MADRES structure")
else:
    earn_rule = Rule.create({
        'name': 'Bono Día de las Madres',
        'code': 'BONO_MADRES',
        'sequence': 10,
        'category_id': cat_basic.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': (
            "result = float(payslip.env['ir.config_parameter'].sudo()"
            ".get_param('payroll.bono_madres_2026', '12.50'))"
        ),
        'appears_on_payslip': True,
    })
    struct.write({'rule_ids': [(4, earn_rule.id)]})
    print(f"✅ Earnings rule created and linked: BONO_MADRES (id={earn_rule.id})")

# ── 7. NET rule: BONO_MADRES_NET ──────────────────────────────────────────
existing_net = Rule.search([('code', '=', 'BONO_MADRES_NET')], limit=1)
if existing_net:
    print(f"⚠️  Rule BONO_MADRES_NET already exists (id={existing_net.id})")
    net_rule = existing_net
    if struct not in net_rule.struct_ids:
        struct.write({'rule_ids': [(4, net_rule.id)]})
        print("   → Linked existing NET rule to BONO_MADRES structure")
else:
    net_rule = Rule.create({
        'name': 'Net Bono Día de las Madres',
        'code': 'BONO_MADRES_NET',
        'sequence': 200,
        'category_id': cat_net.id,
        'condition_select': 'none',
        'amount_select': 'code',
        'amount_python_compute': 'result = BONO_MADRES',
        'appears_on_payslip': True,
        'account_debit_id': acc_debit.id if acc_debit else False,
        'account_credit_id': acc_credit.id if acc_credit else False,
    })
    struct.write({'rule_ids': [(4, net_rule.id)]})
    print(f"✅ NET rule created and linked: BONO_MADRES_NET (id={net_rule.id})")

# ── 8. Commit ─────────────────────────────────────────────────────────────
env.cr.commit()
print("\n✅ Transaction committed")

# ── 9. Verification ───────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)
struct_check = env['hr.payroll.structure'].search([('code', '=', 'BONO_MADRES')], limit=1)
rules_check  = struct_check.rule_ids
print(f"\nStructure : {struct_check.name} (code={struct_check.code}, id={struct_check.id})")
for r in rules_check.sorted('sequence'):
    acc_d = r.account_debit_id.code if r.account_debit_id else 'none'
    acc_c = r.account_credit_id.code if r.account_credit_id else 'none'
    print(f"  Rule [{r.sequence:3d}] {r.code:<25} debit={acc_d}  credit={acc_c}")

print("\n✅ Setup complete.")
print("\nNext steps:")
print("  1. docker restart odoo-dev-web  (to reload module with new template)")
print("  2. In Odoo: Payroll > Batches > New batch")
print("     - Set structure = 'Bono Día de las Madres'")
print("     - Generate payslips > Compute > Confirm")
print("     - Send emails with template 'Bono Día de las Madres - Entrega Especial'")
print("  3. Adjust BONUS_AMOUNT_USD in this script (or edit ir.config_parameter")
print("     directly) before changing the amount.")
