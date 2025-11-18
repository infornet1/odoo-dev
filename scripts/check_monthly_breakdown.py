#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Monthly Breakdown from Prestaciones Report

Let's see exactly what monthly_data is being generated.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("CHECK MONTHLY BREAKDOWN FROM PRESTACIONES REPORT")
print("=" * 80)
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report model
prest_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

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

# Generate report
result = prest_model._get_report_values(docids=[payslip.id], data=data_veb)
report_data = result['reports'][0]

print(f"Total Interest from Report: Bs. {report_data['totals']['total_interest']:,.2f}")
print()

print("MONTHLY BREAKDOWN:")
print("-" * 80)
print(f"{'Month':<15} {'Interest VEB':<15} {'Accum Interest':<15}")
print("-" * 80)

total_from_monthly = 0.0
for month_data in report_data['monthly_data']:
    month_name = month_data['month_name']
    month_interest = month_data['month_interest']
    accum_interest = month_data['accumulated_interest']

    total_from_monthly += month_interest

    print(f"{month_name:<15} Bs.{month_interest:>12,.2f} Bs.{accum_interest:>12,.2f}")

print("-" * 80)
print(f"Sum of monthly interest: Bs. {total_from_monthly:,.2f}")
print(f"Report total_interest:   Bs. {report_data['totals']['total_interest']:,.2f}")
print(f"Last accumulated value:  Bs. {report_data['monthly_data'][-1]['accumulated_interest']:,.2f}")
print()

print("Number of months in breakdown: ", len(report_data['monthly_data']))
print()

if abs(total_from_monthly - report_data['totals']['total_interest']) > 1:
    print("⚠️  MISMATCH! Sum of monthly ≠ Total")
    print(f"   Difference: Bs. {abs(total_from_monthly - report_data['totals']['total_interest']):,.2f}")
else:
    print("✅ Monthly sum matches total")

print()

if abs(report_data['monthly_data'][-1]['accumulated_interest'] - report_data['totals']['total_interest']) > 1:
    print("⚠️  MISMATCH! Last accumulated ≠ Total")
    print(f"   Last accumulated: Bs. {report_data['monthly_data'][-1]['accumulated_interest']:,.2f}")
    print(f"   Report total:     Bs. {report_data['totals']['total_interest']:,.2f}")
    print(f"   Difference:       Bs. {abs(report_data['monthly_data'][-1]['accumulated_interest'] - report_data['totals']['total_interest']):,.2f}")
    print()
    print("🔍 ROOT CAUSE: The totals calculation is OVERRIDING the accumulated value!")
else:
    print("✅ Last accumulated matches total")

print()
print("=" * 80)
print("Analysis complete!")
print("=" * 80)
