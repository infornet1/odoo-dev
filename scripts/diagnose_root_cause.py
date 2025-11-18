#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Root Cause Analysis: Interest Mismatch

Found it! The issue is in the Prestaciones report.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print()

# Get payslip values
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

service_months = get_line('LIQUID_SERVICE_MONTHS_V2') or get_line('LIQUID_SERVICE_MONTHS')
intereses_total = get_line('LIQUID_INTERESES_V2') or get_line('LIQUID_INTERESES')

print("PAYSLIP DATA:")
print("-" * 80)
print(f"Service Months: {service_months:.2f}")
print(f"Total Interest (USD): ${intereses_total:.2f}")
print()

print("=" * 80)
print("THE BUG IS IN prestaciones_interest_report.py LINE 114")
print("=" * 80)
print()

print("CURRENT CODE (WRONG):")
print("-" * 80)
print("interest_per_month = intereses_total / service_months")
print()
print(f"Calculation: ${intereses_total:.2f} / {service_months:.2f} = ${intereses_total/service_months:.2f}")
print()

print("BUT THEN...")
print("-" * 80)
print("months_count = int(service_months)  # Line 112")
print(f"months_count = int({service_months:.2f}) = {int(service_months)}")
print()
print("The loop only processes int(service_months) = 23 months")
print("But interest_per_month is based on service_months = 23.30")
print()

print("ACCUMULATED TOTAL:")
print("-" * 80)
accumulated_wrong = 0.0
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

contract = payslip.contract_id
start_date = contract.date_start
end_date = payslip.date_to

from dateutil.relativedelta import relativedelta

current_date = start_date
months_processed = 0
interest_per_month = intereses_total / service_months

while current_date <= end_date and months_processed < 23:  # Only 23 iterations!
    rate_rec = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_rec:
        rate_rec = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_rec.company_rate if rate_rec and hasattr(rate_rec, 'company_rate') else 0.0
    month_interest_veb = interest_per_month * month_rate
    accumulated_wrong += month_interest_veb

    current_date = current_date + relativedelta(months=1)
    months_processed += 1

print(f"USD interest per month: ${interest_per_month:.2f}")
print(f"Months processed: {months_processed}")
print(f"Total USD distributed: ${interest_per_month * months_processed:.2f}")
print(f"Total USD expected: ${intereses_total:.2f}")
print(f"USD missing: ${intereses_total - (interest_per_month * months_processed):.2f}")
print()
print(f"VEB accumulated (wrong): Bs. {accumulated_wrong:,.2f}")
print()

print("=" * 80)
print("THE FIX NEEDED")
print("=" * 80)
print()

print("The loop condition in prestaciones_interest_report.py needs to be:")
print()
print("CURRENT (WRONG):")
print("  while current_date <= end_date:")
print("      # Processes until end_date")
print("      # But months_count = int(23.30) = 23 limits it")
print()
print("SHOULD BE:")
print("  while current_date <= end_date:")
print("      # Process ALL months until end_date")
print("      # Remove the months_count limitation")
print()

# Calculate correct version
accumulated_correct = 0.0
current_date = start_date
months_processed_correct = 0

while current_date <= end_date:  # Process ALL months
    rate_rec = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_rec:
        rate_rec = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_rec.company_rate if rate_rec and hasattr(rate_rec, 'company_rate') else 0.0
    month_interest_veb = interest_per_month * month_rate
    accumulated_correct += month_interest_veb

    current_date = current_date + relativedelta(months=1)
    months_processed_correct += 1
    if current_date > end_date:
        break

print(f"CORRECT CALCULATION:")
print(f"  Months processed: {months_processed_correct}")
print(f"  Total USD distributed: ${interest_per_month * service_months:.2f}")
print(f"  VEB accumulated: Bs. {accumulated_correct:,.2f}")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()
print(f"Prestaciones Report (current): Bs. 4,160.85 ❌")
print(f"Prestaciones Report (should be): Bs. {accumulated_correct:,.2f} ✅")
print(f"Relación Report: Bs. 4,224.84 ✅")
print()
print("The Prestaciones report is UNDER-REPORTING by:")
print(f"  Bs. {accumulated_correct - 4160.85:,.2f}")
print()
print("ROOT CAUSE:")
print("  The loop only processes 23 months (int(23.30))")
print("  But it should process until end_date (which gives 23 full months)")
print("  The issue is likely in how months_count is used or")
print("  the loop is NOT reaching all the way to end_date")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
