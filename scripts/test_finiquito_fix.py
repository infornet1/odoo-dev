#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Finiquito Exchange Rate Override Fix

Verify Finiquito now respects exchange rate override.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: FINIQUITO EXCHANGE RATE OVERRIDE FIX v1.23.0")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report models
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print("=" * 80)
print("SCENARIO 1: VEB CURRENCY (NO OVERRIDE)")
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

# Generate both reports
finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_no_override)
finiquito_net = finiquito_result['reports'][0]['net_amount']

relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_no_override)
relacion_net = relacion_result['reports'][0]['net_amount']

print(f"Finiquito Net Amount: Bs. {finiquito_net:,.2f}")
print(f"Relación Net Amount:  Bs. {relacion_net:,.2f}")
print()

diff_no_override = abs(finiquito_net - relacion_net)
if diff_no_override < 1:
    print(f"✅ PERFECT MATCH! (difference: Bs. {diff_no_override:.2f})")
else:
    print(f"❌ MISMATCH! (difference: Bs. {diff_no_override:.2f})")
print()

print("=" * 80)
print("SCENARIO 2: WITH EXCHANGE RATE OVERRIDE (Nov 17, 236.4601)")
print("=" * 80)
print()

# Test with override
data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

# Generate both reports with override
finiquito_result_override = finiquito_model._get_report_values(docids=[payslip.id], data=data_with_override)
finiquito_net_override = finiquito_result_override['reports'][0]['net_amount']

relacion_result_override = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
relacion_net_override = relacion_result_override['reports'][0]['net_amount']

print("Net amounts (should use Nov 17 override rate):")
print(f"  Finiquito: Bs. {finiquito_net_override:,.2f}")
print(f"  Relación:  Bs. {relacion_net_override:,.2f}")
print()

diff_with_override = abs(finiquito_net_override - relacion_net_override)
if diff_with_override < 1:
    print(f"✅ MATCH! (difference: Bs. {diff_with_override:.2f})")
else:
    print(f"❌ DON'T MATCH! (difference: Bs. {diff_with_override:.2f})")
print()

# Verify amounts changed with override
print("=" * 80)
print("VERIFICATION: Amounts Should Increase with Override")
print("=" * 80)
print()

print(f"WITHOUT override: Bs. {finiquito_net:,.2f}")
print(f"WITH override:    Bs. {finiquito_net_override:,.2f}")
print(f"Increase:         Bs. {finiquito_net_override - finiquito_net:,.2f} ({((finiquito_net_override/finiquito_net - 1) * 100):.1f}%)")
print()

amounts_increased = finiquito_net_override > finiquito_net
if amounts_increased:
    print("✅ CORRECT! Amounts increased with override")
else:
    print("❌ WRONG! Amounts didn't increase")
print()

# Verify expected amount
print("=" * 80)
print("VERIFY EXPECTED AMOUNT")
print("=" * 80)
print()

expected_with_override = 300621.18
if abs(finiquito_net_override - expected_with_override) < 1:
    print(f"✅ PERFECT! Finiquito shows expected Bs. {expected_with_override:,.2f}")
else:
    print(f"Finiquito shows: Bs. {finiquito_net_override:,.2f}")
    print(f"Expected:        Bs. {expected_with_override:,.2f}")
    print(f"Difference:      Bs. {abs(finiquito_net_override - expected_with_override):,.2f}")
print()

print("=" * 80)
print("FINAL RESULT")
print("=" * 80)
print()

all_pass = (diff_no_override < 1 and
            diff_with_override < 1 and
            amounts_increased and
            abs(finiquito_net_override - expected_with_override) < 1)

if all_pass:
    print("🎉 SUCCESS! Finiquito exchange rate override fix is working!")
    print()
    print("✅ Reports match without override")
    print("✅ Reports match WITH override")
    print("✅ Amounts correctly increase with override")
    print("✅ Shows expected amount Bs. 300,621.18")
    print()
    print("Employee will receive consistent information across all reports! 🎯")
    print()
    print("Summary:")
    print(f"  WITHOUT override: Bs. {finiquito_net:,.2f}")
    print(f"  WITH override:    Bs. {finiquito_net_override:,.2f}")
    print(f"  Increase:         +{((finiquito_net_override/finiquito_net - 1) * 100):.1f}%")
else:
    print("⚠️  Issues detected - review implementation")
print()

print("=" * 80)
print("Test complete!")
print("=" * 80)
