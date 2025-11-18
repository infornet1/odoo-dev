#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Prestaciones Report Fix

Verify both reports now show identical interest amounts.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: PRESTACIONES REPORT FIX v1.22.0")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report models
prest_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Test data (VEB, no override)
data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

print("=" * 80)
print("SCENARIO 1: VEB CURRENCY (NO OVERRIDE)")
print("=" * 80)
print()

# Generate both reports
prest_result = prest_model._get_report_values(docids=[payslip.id], data=data_veb)
prest_interest = prest_result['reports'][0]['totals']['total_interest']

relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_veb)
relacion_interest = [b for b in relacion_result['reports'][0]['benefits'] if b['number'] == 6][0]['amount']

print(f"Prestaciones Report Interest: Bs. {prest_interest:,.2f}")
print(f"Relación Report Interest:     Bs. {relacion_interest:,.2f}")
print()

diff_no_override = abs(prest_interest - relacion_interest)
if diff_no_override < 1:
    print(f"✅ PERFECT MATCH! (difference: Bs. {diff_no_override:.2f})")
else:
    print(f"❌ MISMATCH! (difference: Bs. {diff_no_override:.2f})")
print()

# Show sample monthly breakdown
print("Sample Monthly Breakdown (Prestaciones):")
print("-" * 80)
monthly_data = prest_result['reports'][0]['monthly_data']
print(f"{'Month':<15} {'Interest':<15}")
print("-" * 80)
for i, month_data in enumerate(monthly_data[:3]):  # First 3 months
    print(f"{month_data['month_name']:<15} Bs. {month_data['month_interest']:>10,.2f}")
print("...")
for i, month_data in enumerate(monthly_data[-3:]):  # Last 3 months
    print(f"{month_data['month_name']:<15} Bs. {month_data['month_interest']:>10,.2f}")
print("-" * 80)
print(f"Total: Bs. {prest_interest:,.2f}")
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
relacion_interest_override = [b for b in relacion_result_override['reports'][0]['benefits'] if b['number'] == 6][0]['amount']

print("Interest (should IGNORE override, use accrual):")
print(f"  Prestaciones Report:  Bs. {prest_interest_override:,.2f}")
print(f"  Relación Report:      Bs. {relacion_interest_override:,.2f}")
print()

diff_with_override = abs(prest_interest_override - relacion_interest_override)
if diff_with_override < 1:
    print(f"✅ MATCH! (difference: Bs. {diff_with_override:.2f})")
else:
    print(f"❌ DON'T MATCH! (difference: Bs. {diff_with_override:.2f})")
print()

# Verify interest didn't change between scenarios
print("=" * 80)
print("VERIFICATION: Interest Should Be Same in Both Scenarios")
print("=" * 80)
print()
print(f"WITHOUT override: Bs. {prest_interest:,.2f}")
print(f"WITH override:    Bs. {prest_interest_override:,.2f}")
print()

interest_same = abs(prest_interest - prest_interest_override) < 1
if interest_same:
    print("✅ CORRECT! Interest ignores override as intended")
else:
    print("❌ WRONG! Interest changed with override")
print()

print("=" * 80)
print("FINAL RESULT")
print("=" * 80)
print()

all_match = (diff_no_override < 1 and
             diff_with_override < 1 and
             interest_same)

if all_match:
    print("🎉 SUCCESS! Prestaciones report fix is working correctly!")
    print()
    print("✅ Reports match without override")
    print("✅ Reports match WITH override")
    print("✅ Interest ignores override (always uses accrual)")
    print("✅ Both reports show IDENTICAL amounts")
    print()
    print("Employee will receive consistent information! 🎯")
    print()
    print(f"Expected amount on both reports: Bs. {prest_interest:,.2f}")
else:
    print("⚠️  Issues detected - review implementation")
print()

print("=" * 80)
print("Test complete!")
print("=" * 80)
