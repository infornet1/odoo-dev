#!/usr/bin/env python3
"""
Fix BONO_MADRES salary rule to read amount from ir.config_parameter.
HR changes the value at: Settings → Technical → Parameters → System Parameters
Key: payroll.bono_madres_2026

Run:
  docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/fix_bono_madres_rule.py
"""

PARAM_KEY = 'payroll.bono_madres_2026'
DEFAULT_AMOUNT = '12.50'

# Ensure the parameter exists with a default value
param = env['ir.config_parameter'].sudo()
if not param.get_param(PARAM_KEY):
    param.set_param(PARAM_KEY, DEFAULT_AMOUNT)
    print(f"✅ Created ir.config_parameter: {PARAM_KEY} = {DEFAULT_AMOUNT}")
else:
    print(f"✅ ir.config_parameter already exists: {PARAM_KEY} = {param.get_param(PARAM_KEY)}")

# Update the salary rule formula
rule = env['hr.salary.rule'].search([('code', '=', 'BONO_MADRES')], limit=1)
if not rule:
    print("❌ Rule BONO_MADRES not found")
    raise SystemExit(1)

formula = (
    "result = float(payslip.env['ir.config_parameter'].sudo()"
    f".get_param('{PARAM_KEY}', '{DEFAULT_AMOUNT}'))"
)
rule.write({'amount_python_compute': formula})
env.cr.commit()

print(f"✅ BONO_MADRES formula updated (id={rule.id})")
print(f"   Formula: {formula}")
print(f"\nTo change the bonus amount:")
print(f"  Settings → Technical → Parameters → System Parameters")
print(f"  Search: {PARAM_KEY}  →  edit Value field")
