#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify what the PDF is actually generating for SLIP/802
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("VERIFY ACTUAL PDF GENERATION - SLIP/802")
print("=" * 80)
print()

# Get VEB currency
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Simulate EXACT wizard call as user would do
wizard_data = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

print("Calling report model with VEB currency...")
print()

# Get the report model
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Generate report (same as PDF generation)
report_values = report_model._get_report_values(docids=[payslip.id], data=wizard_data)

# Get the report data
report_data = report_values['reports'][0]

# Find interest benefit (#6)
benefits = report_data['benefits']
interest_benefit = None
for benefit in benefits:
    if benefit['number'] == 6:
        interest_benefit = benefit
        break

if not interest_benefit:
    print("ERROR: Interest benefit not found!")
    sys.exit(1)

print("=" * 80)
print("BENEFIT #6 DATA (What PDF will show)")
print("=" * 80)
print()
print(f"Number: {interest_benefit['number']}")
print(f"Name: {interest_benefit['name']}")
print(f"Formula: {interest_benefit['formula']}")
print(f"Calculation: {interest_benefit['calculation']}")
print(f"Detail: {interest_benefit['detail']}")
print(f"Amount (raw): {interest_benefit['amount']}")
print(f"Amount (formatted): {interest_benefit['amount_formatted']}")
print()

print("=" * 80)
print("WHAT THE PDF TEMPLATE WILL RENDER")
print("=" * 80)
print()
print("Line 1 (Name): " + interest_benefit['name'])
print("Line 2 (Formula): " + interest_benefit['formula'])
print("Line 3 (Calculation): " + interest_benefit['calculation'])
print(f"Amount Column: Bs. {interest_benefit['amount_formatted']}")
print()

# Also check the currency symbol
currency = report_data['currency']
print(f"Currency: {currency.name} ({currency.symbol})")
print()

# Check if there's any other value that could be 20,209.12
print("=" * 80)
print("CHECKING FOR Bs. 20,209.12 IN REPORT DATA")
print("=" * 80)
print()

# Check all benefits
print("All benefit amounts:")
for b in benefits:
    print(f"  {b['number']}. {b['name']}: Bs. {b['amount_formatted']}")
print()

# Check totals
print(f"Total Benefits: Bs. {report_data['total_benefits_formatted']}")
print(f"Total Deductions: Bs. {report_data['total_deductions_formatted']}")
print(f"Net Amount: Bs. {report_data['net_amount_formatted']}")
print()

# Search for 20209 in all values
print("Searching for any value close to 20,209...")
found_20209 = False
for b in benefits:
    if abs(b['amount'] - 20209.12) < 1:
        print(f"  FOUND in benefit {b['number']}: {b['name']} = {b['amount']:.2f}")
        found_20209 = True

if not found_20209:
    print("  NOT FOUND in any benefit amounts")
print()

# Calculate what 162,206.90 × 50% × 13% × (23.30/12) would be
manual_calc = 162206.90 * 0.50 * 0.13 * (23.30 / 12)
print(f"Manual calculation of formula shown: {manual_calc:.2f}")
print()

print("=" * 80)
print("DIAGNOSIS")
print("=" * 80)
print()

if abs(interest_benefit['amount'] - 4224.84) < 100:
    print("✅ Python code is returning CORRECT value: Bs. 4,224.84")
    print()
    print("But you're seeing: Bs. 20,209.12")
    print()
    print("Possible causes:")
    print("  1. Module not upgraded in Odoo (still using old code)")
    print("  2. Different report being viewed (cached/old PDF file)")
    print("  3. Python code changed but Odoo server not restarted")
    print()
else:
    print(f"❌ Python code is returning WRONG value: Bs. {interest_benefit['amount']:.2f}")
    print()
    print("This means _calculate_accrued_interest() is NOT working")
    print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
