#!/usr/bin/env python3
"""Verify salary rule formulas were updated"""

PayrollStructure = env['hr.payroll.structure']

structure = PayrollStructure.search([('code', '=', 'LIQUID_VE_V2')], limit=1)
rules = structure.rule_ids

codes = ['LIQUID_VACACIONES_V2', 'LIQUID_BONO_VACACIONAL_V2', 'LIQUID_VACATION_PREPAID_V2']

print("="*80)
print("VERIFY FORMULA UPDATES")
print("="*80)

for code in codes:
    rule = rules.filtered(lambda r: r.code == code)
    if rule:
        formula = rule.amount_python_compute or ''
        lines = formula.split('\n')
        print(f"\n{code}:")
        print(f"  Lines: {len(lines)}")
        print(f"  First line: {lines[0][:80]}")
        print(f"  Uses 'vacation_paid_until': {'vacation_paid_until' in formula}")
        print(f"  Uses 'ueipab_vacation_prepaid_amount': {'ueipab_vacation_prepaid_amount' in formula}")
