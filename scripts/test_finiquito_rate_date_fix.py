#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Finiquito Rate Date Fix (v1.25.1)

Verify that rate_date parameter now works correctly.
User selected "Rate Date (Auto Lookup)" as 11/17/2025 and expected Bs. 300,621.18
"""

import sys
from datetime import date

# Find payslip SLIP/803
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/803')], limit=1)

if not payslip:
    print("ERROR: SLIP/803 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: FINIQUITO RATE DATE FIX (v1.25.1)")
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

# Check what rate exists for Nov 17, 2025
rate_rec_nov17 = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', date(2025, 11, 17))
], limit=1, order='name desc')

if rate_rec_nov17:
    nov17_rate = rate_rec_nov17.company_rate
    print(f"VEB rate for Nov 17, 2025: {nov17_rate:.4f}")
    print(f"Expected Finiquito amount: ${net_usd:.2f} × {nov17_rate:.4f} = Bs. {net_usd * nov17_rate:,.2f}")
else:
    print("⚠️  No VEB rate found for Nov 17, 2025")
    nov17_rate = 0.0

print()

# Test Finiquito with rate_date = 2025-11-17
print("=" * 80)
print("TEST: Finiquito with rate_date = 2025-11-17")
print("=" * 80)
print()

data_with_rate_date = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,  # NOT using custom rate
    'custom_exchange_rate': None,
    'rate_date': date(2025, 11, 17),  # Using rate date lookup
}

finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']
finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_with_rate_date)
finiquito_net = finiquito_result['reports'][0]['net_amount']

print(f"Finiquito Net Amount: Bs. {finiquito_net:,.2f}")
print()

# Verification
print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print()

expected_amount = net_usd * nov17_rate
difference = abs(finiquito_net - expected_amount)

print(f"Expected: Bs. {expected_amount:,.2f}")
print(f"Actual:   Bs. {finiquito_net:,.2f}")
print(f"Difference: Bs. {difference:.2f}")
print()

if difference < 1:
    print("✅ SUCCESS: Rate date parameter is working correctly!")
    print()
    print(f"Using rate_date=2025-11-17 gives Bs. {finiquito_net:,.2f}")
    print("This matches the expected amount using Nov 17 rate.")
else:
    print("❌ FAILURE: Rate date not working as expected")
    print()
    print("The report may still be using payslip date instead of rate_date")

print()
print("=" * 80)
print("Test complete!")
print("=" * 80)
