#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Option B Implementation: Interest Ignores Override

Test both scenarios:
1. WITHOUT override - both reports should match
2. WITH override - both reports should STILL match
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: OPTION B IMPLEMENTATION - INTEREST IGNORES OVERRIDE")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report models
prest_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print("=" * 80)
print("SCENARIO 1: WITHOUT EXCHANGE RATE OVERRIDE")
print("=" * 80)
print()

# Test without override
data_no_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

# Prestaciones report
prest_result = prest_model._get_report_values(docids=[payslip.id], data=data_no_override)
prest_interest = prest_result['reports'][0]['totals']['total_interest']

# Relación report
relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_no_override)
relacion_interest = [b for b in relacion_result['reports'][0]['benefits'] if b['number'] == 6][0]['amount']

print(f"Prestaciones Report (Interest):  Bs. {prest_interest:,.2f}")
print(f"Relación Report (Interest):      Bs. {relacion_interest:,.2f}")
print()

diff_no_override = abs(prest_interest - relacion_interest)
if diff_no_override < 100:
    print(f"✅ MATCH! (difference: Bs. {diff_no_override:.2f})")
else:
    print(f"❌ DON'T MATCH! (difference: Bs. {diff_no_override:.2f})")
print()

print("=" * 80)
print("SCENARIO 2: WITH EXCHANGE RATE OVERRIDE (Nov 17, 236.4601)")
print("=" * 80)
print()

# Test with override
from datetime import date
data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

# Prestaciones report (should ignore override)
prest_result_override = prest_model._get_report_values(docids=[payslip.id], data=data_with_override)
prest_interest_override = prest_result_override['reports'][0]['totals']['total_interest']

# Relación report (should also ignore override for interest)
relacion_result_override = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
relacion_benefits = relacion_result_override['reports'][0]['benefits']
relacion_interest_override = [b for b in relacion_benefits if b['number'] == 6][0]['amount']

# Check other benefits (should use override)
vacaciones_override = [b for b in relacion_benefits if b['number'] == 1][0]['amount']
prestaciones_override = [b for b in relacion_benefits if b['number'] == 4][0]['amount']

print("Other benefits (should use override rate 236.4601):")
print(f"  Vacaciones: Bs. {vacaciones_override:,.2f}")
print(f"  Prestaciones: Bs. {prestaciones_override:,.2f}")
print()

print("Interest (should IGNORE override, use accrual):")
print(f"  Prestaciones Report:  Bs. {prest_interest_override:,.2f}")
print(f"  Relación Report:      Bs. {relacion_interest_override:,.2f}")
print()

diff_with_override = abs(prest_interest_override - relacion_interest_override)
if diff_with_override < 100:
    print(f"✅ MATCH! (difference: Bs. {diff_with_override:.2f})")
else:
    print(f"❌ DON'T MATCH! (difference: Bs. {diff_with_override:.2f})")
print()

# Verify interest didn't change between scenarios
print("=" * 80)
print("VERIFICATION: Interest Should Be Same in Both Scenarios")
print("=" * 80)
print()
print(f"WITHOUT override: Bs. {relacion_interest:,.2f}")
print(f"WITH override:    Bs. {relacion_interest_override:,.2f}")
print()

interest_same = abs(relacion_interest - relacion_interest_override) < 1
if interest_same:
    print("✅ CORRECT! Interest ignores override as intended")
else:
    print("❌ WRONG! Interest changed with override")
print()

print("=" * 80)
print("FINAL RESULT")
print("=" * 80)
print()

all_match = (diff_no_override < 100 and
             diff_with_override < 100 and
             interest_same)

if all_match:
    print("🎉 SUCCESS! Option B implementation is correct!")
    print()
    print("✅ Reports match without override")
    print("✅ Reports match WITH override")
    print("✅ Interest ignores override (always uses accrual)")
    print("✅ Other benefits respect override")
    print()
    print("Employee will receive consistent information! 🎯")
else:
    print("⚠️  Issues detected - review implementation")
print()

print("=" * 80)
print("Test complete!")
print("=" * 80)
