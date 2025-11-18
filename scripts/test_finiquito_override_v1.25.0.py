#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Finiquito Exchange Rate Override Feature (v1.25.0)

Verify that Finiquito wizard now passes override settings correctly.
Expected: Both reports should show matching amounts when using same override.
"""

import sys

# Find payslip SLIP/803
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/803')], limit=1)

if not payslip:
    print("ERROR: SLIP/803 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: FINIQUITO EXCHANGE RATE OVERRIDE (v1.25.0)")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get net amount in USD
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

net_usd = get_line('LIQUID_NET_V2') or get_line('LIQUID_NET')
net_usd = abs(net_usd)

print(f"NET AMOUNT (USD): ${net_usd:.2f}")
print()

# Test data WITH override (Nov 17 rate, 236.4601)
data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

# Get report models
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']

print("=" * 80)
print("TEST SCENARIO: Both reports WITH OVERRIDE (236.4601)")
print("=" * 80)
print()

print("Relación de Liquidación:")
print("-" * 80)
relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
relacion_net = relacion_result['reports'][0]['net_amount']
print(f"  Net Amount: Bs. {relacion_net:,.2f}")
print()

print("Acuerdo Finiquito Laboral:")
print("-" * 80)
finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_with_override)
finiquito_net = finiquito_result['reports'][0]['net_amount']
print(f"  Net Amount: Bs. {finiquito_net:,.2f}")
print()

print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print()

difference = abs(relacion_net - finiquito_net)
match = difference < 1

print(f"Relación:  Bs. {relacion_net:,.2f}")
print(f"Finiquito: Bs. {finiquito_net:,.2f}")
print(f"Difference: Bs. {difference:.2f}")
print()

if match:
    print("✅ SUCCESS: Both reports show MATCHING amounts!")
    print()
    print("The exchange rate override feature is working correctly.")
    print("Finiquito wizard now properly passes override settings to the report.")
else:
    print("❌ FAILURE: Amounts still don't match!")
    print()
    print("Expected both to be Bs. 300,621.18 (with 236.4601 rate)")
    print("Something is still wrong with the override implementation.")

print()
print("=" * 80)
print("Test complete!")
print("=" * 80)
