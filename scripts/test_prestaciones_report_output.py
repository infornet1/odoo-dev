#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Prestaciones Interest Report - Verify Actual Output

This script simulates the actual report generation to see what VEB amounts
are currently being calculated and displayed.
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("TESTING ACTUAL PRESTACIONES INTEREST REPORT OUTPUT")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("ERROR: VEB currency not found")
    sys.exit(1)

# Instantiate the report model
report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

# Simulate data dict from wizard (VEB currency selected)
data = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
}

print("Calling report model's _get_report_values()...")
print()

# Call the actual report method
report_values = report_model._get_report_values(docids=[payslip.id], data=data)

print("=" * 80)
print("REPORT OUTPUT - MAIN VALUES")
print("=" * 80)
print()

# Extract report data
reports = report_values.get('reports', [])
if reports:
    report_data = reports[0]

    print(f"Employee: {report_data['employee'].name}")
    print(f"Currency: {report_data['currency'].name} ({report_data['currency'].symbol})")
    print()

    # Get monthly data
    monthly_data = report_data.get('monthly_data', [])
    totals = report_data.get('totals', {})

    print(f"Number of months: {len(monthly_data)}")
    print()

    print("=" * 80)
    print("MONTHLY BREAKDOWN (First 5 months)")
    print("=" * 80)
    print()
    print(f"{'Month':<10} {'Income':<15} {'Deposit':<15} {'Accum Prest':<15} {'Month Int':<15} {'Accum Int':<15}")
    print("-" * 90)

    for i, month in enumerate(monthly_data[:5]):
        print(f"{month['month_name']:<10} "
              f"Bs.{month['monthly_income']:>11,.2f} "
              f"Bs.{month['deposit_amount']:>11,.2f} "
              f"Bs.{month['accumulated_prestaciones']:>11,.2f} "
              f"Bs.{month['month_interest']:>11,.2f} "
              f"Bs.{month['accumulated_interest']:>11,.2f}")

    if len(monthly_data) > 5:
        print(f"... ({len(monthly_data) - 5} more months)")
    print()

    print("=" * 80)
    print("LAST 5 MONTHS")
    print("=" * 80)
    print()
    print(f"{'Month':<10} {'Income':<15} {'Deposit':<15} {'Accum Prest':<15} {'Month Int':<15} {'Accum Int':<15}")
    print("-" * 90)

    for month in monthly_data[-5:]:
        print(f"{month['month_name']:<10} "
              f"Bs.{month['monthly_income']:>11,.2f} "
              f"Bs.{month['deposit_amount']:>11,.2f} "
              f"Bs.{month['accumulated_prestaciones']:>11,.2f} "
              f"Bs.{month['month_interest']:>11,.2f} "
              f"Bs.{month['accumulated_interest']:>11,.2f}")
    print()

    print("=" * 80)
    print("FINAL TOTALS (FROM REPORT)")
    print("=" * 80)
    print()
    print(f"Total Days Deposited: {totals.get('total_days', 0):.1f}")
    print(f"Total Prestaciones: Bs. {totals.get('total_prestaciones', 0):,.2f}")
    print(f"Total Interest: Bs. {totals.get('total_interest', 0):,.2f}")
    print(f"Total Advance: Bs. {totals.get('total_advance', 0):,.2f}")
    print()

    # Get the final accumulated interest from last month
    if monthly_data:
        final_accum = monthly_data[-1]['accumulated_interest']
        print("=" * 80)
        print("VERIFICATION")
        print("=" * 80)
        print()
        print(f"Last month accumulated interest: Bs. {final_accum:,.2f}")
        print(f"Totals 'total_interest' field: Bs. {totals.get('total_interest', 0):,.2f}")
        print()

        if abs(final_accum - totals.get('total_interest', 0)) < 0.01:
            print("✅ VALUES MATCH!")
        else:
            print("⚠️  VALUES DON'T MATCH!")
        print()

    print("=" * 80)
    print("COMPARISON WITH OUR MANUAL CALCULATION")
    print("=" * 80)
    print()
    print(f"Report shows total interest: Bs. {totals.get('total_interest', 0):,.2f}")
    print(f"Our manual calc expected: Bs. 4,224.84")
    print()

    diff = totals.get('total_interest', 0) - 4224.84
    if abs(diff) < 0.01:
        print("✅ REPORT MATCHES OUR CALCULATION!")
    else:
        print(f"⚠️  DIFFERENCE: Bs. {diff:,.2f}")
        print()
        print("Possible reasons for difference:")
        print("  1. Different rounding in conversion logic")
        print("  2. Different date range interpretation")
        print("  3. Different rate lookup logic")
    print()

else:
    print("ERROR: No report data generated")
    print()

print("=" * 80)
print("Test complete!")
print("=" * 80)
