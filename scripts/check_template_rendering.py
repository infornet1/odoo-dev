#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Template Rendering Issue

The reports calculate correctly but may not be displaying properly in PDF.
Let's check what data is being passed to the template.
"""

import sys

# Find payslip SLIP/803
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/803')], limit=1)

if not payslip:
    print("ERROR: SLIP/803 not found")
    sys.exit(1)

print("=" * 80)
print("CHECK: TEMPLATE RENDERING FOR SLIP/803")
print("=" * 80)
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Test data
data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

# Get report models
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']

print("RELACIÓN DE LIQUIDACIÓN REPORT DATA:")
print("=" * 80)
relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_veb)
relacion_report = relacion_result['reports'][0]

print()
print("Currency Symbol:")
print(f"  currency: {relacion_report.get('currency', 'N/A')}")
print(f"  currency.symbol: {relacion_report['currency'].symbol if 'currency' in relacion_report else 'N/A'}")
print()

print("Amounts:")
print(f"  total_benefits: {relacion_report.get('total_benefits', 0)}")
print(f"  total_deductions: {relacion_report.get('total_deductions', 0)}")
print(f"  net_amount: {relacion_report.get('net_amount', 0)}")
print()

print("Benefits (first 3):")
benefits = relacion_report.get('benefits', [])
for i, benefit in enumerate(benefits[:3]):
    print(f"  {i+1}. {benefit['name']}")
    print(f"     amount: {benefit.get('amount', 'MISSING')}")
    print(f"     amount_formatted: {benefit.get('amount_formatted', 'MISSING')}")
print()

print("Employee Info:")
print(f"  employee_name: {relacion_report.get('employee_name', 'MISSING')}")
print(f"  employee_vat: {relacion_report.get('employee_vat', 'MISSING')}")
print()

print("=" * 80)
print("ACUERDO FINIQUITO REPORT DATA:")
print("=" * 80)
finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_veb)
finiquito_report = finiquito_result['reports'][0]

print()
print("Currency Symbol:")
print(f"  currency: {finiquito_report.get('currency', 'N/A')}")
if 'currency' in finiquito_report:
    print(f"  currency.symbol: {finiquito_report['currency'].symbol}")
print()

print("Amount:")
print(f"  net_amount: {finiquito_report.get('net_amount', 'MISSING')}")
print()

print("Employee Info:")
print(f"  employee: {finiquito_report.get('employee', 'MISSING')}")
if 'employee' in finiquito_report:
    print(f"  employee.name: {finiquito_report['employee'].name}")
print()

print("Dates:")
print(f"  date_start_str: {finiquito_report.get('date_start_str', 'MISSING')}")
print(f"  date_to_str: {finiquito_report.get('date_to_str', 'MISSING')}")
print()

print("=" * 80)
print("POTENTIAL ISSUES TO CHECK IN PDF:")
print("=" * 80)
print()

print("1. Currency Symbol Display:")
print(f"   VEB symbol: '{veb.symbol}'")
print(f"   Is it showing in PDF? Check if 'Bs.' appears")
print()

print("2. Amount Formatting:")
print(f"   Sample amount: {relacion_report.get('net_amount', 0)}")
print(f"   Formatted: {relacion_report.get('net_amount', 0):,.2f}")
print(f"   Check if PDF shows: 'Bs. 158,294.80'")
print()

print("3. Template Variables:")
print("   Check if template uses:")
print("   - report['net_amount'] or report.get('net_amount')")
print("   - benefit['amount_formatted'] or benefit['amount']")
print()

print("4. Conditional Display:")
print("   Check for invisible conditions like:")
print("   - t-if=\"report.get('net_amount') > 0\"")
print("   - invisible=\"net_amount == 0\"")
print()

# Check if amounts might be getting filtered out
if relacion_report.get('net_amount', 0) > 0:
    print("✅ Net amount is > 0, should display")
else:
    print("⚠️  Net amount is 0 or missing!")

print()
print("=" * 80)
print("Analysis complete!")
print("=" * 80)
