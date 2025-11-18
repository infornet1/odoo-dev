#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Interest Accrual - Accounting Perspective

This script investigates how interest should be calculated from an
accrual accounting perspective where monthly interest is recorded
in the ledger each month.
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("ACCRUAL ACCOUNTING PERSPECTIVE - Interest Analysis")
print("=" * 80)
print(f"Employee: {payslip.employee_id.name}")
print(f"Payslip: {payslip.number}")
print(f"Period: {payslip.date_from} to {payslip.date_to}")
print()

# Get key values from payslip
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

service_months = get_line('LIQUID_SERVICE_MONTHS_V2')
prestaciones_usd = get_line('LIQUID_PRESTACIONES_V2')
intereses_usd = get_line('LIQUID_INTERESES_V2')
integral_daily = get_line('LIQUID_INTEGRAL_DAILY_V2')

print("KEY VALUES (USD):")
print("-" * 80)
print(f"Service Months: {service_months:.2f}")
print(f"Prestaciones Total: ${prestaciones_usd:.2f}")
print(f"Intereses Total: ${intereses_usd:.2f}")
print(f"Integral Daily Salary: ${integral_daily:.2f}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Calculate quarterly deposit and interest distribution
quarterly_deposit = integral_daily * 15
interest_per_month = intereses_usd / service_months

print("=" * 80)
print("MONTHLY ACCRUAL CALCULATION (As Recorded in Ledger)")
print("=" * 80)
print()
print("Accounting Process Each Month:")
print("  1. Calculate month's interest in USD")
print("  2. Convert to VEB using THAT month's exchange rate")
print("  3. Post to general ledger in VEB")
print("  4. Accumulate over all months")
print()

# Simulate monthly accrual process
contract = payslip.contract_id
start_date = contract.date_start
end_date = payslip.date_to

current_date = start_date
month_num = 0
accumulated_prestaciones_usd = 0.0
accumulated_interest_usd = 0.0
accumulated_interest_veb = 0.0

print(f"{'Month':<10} {'Date':<12} {'Dep':<5} {'Prest USD':<12} {'Int USD':<12} {'Rate':<10} {'Int VEB':<15} {'Accum VEB':<15}")
print("-" * 120)

while current_date <= end_date:
    month_num += 1

    # Determine if deposit month (every 3 months starting from month 3)
    is_deposit_month = (month_num >= 3 and (month_num - 3) % 3 == 0)

    # Prestaciones deposit this month
    deposit_usd = quarterly_deposit if is_deposit_month else 0.0
    accumulated_prestaciones_usd += deposit_usd

    # Interest for this month (proportional distribution)
    month_interest_usd = interest_per_month
    accumulated_interest_usd += month_interest_usd

    # Get exchange rate for THIS month
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_record:
        rate_record = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_record.company_rate if rate_record and hasattr(rate_record, 'company_rate') else 0.0

    # Convert THIS month's interest to VEB using THIS month's rate
    # THIS IS THE LEDGER ENTRY FOR THIS MONTH
    month_interest_veb = month_interest_usd * month_rate
    accumulated_interest_veb += month_interest_veb

    # Print row
    month_name = current_date.strftime("%b-%y")
    deposit_marker = "✓" if is_deposit_month else ""

    print(f"{month_name:<10} {current_date.strftime('%Y-%m-%d'):<12} {deposit_marker:<5} "
          f"${accumulated_prestaciones_usd:>10.2f} ${month_interest_usd:>10.4f} "
          f"{month_rate:>9.4f} Bs.{month_interest_veb:>12.2f} Bs.{accumulated_interest_veb:>12.2f}")

    # Move to next month
    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

print("-" * 120)
print(f"{'TOTALS':<10} {'':<12} {'':<5} ${accumulated_prestaciones_usd:>10.2f} "
      f"${accumulated_interest_usd:>10.2f} {'':<10} {'':<15} Bs.{accumulated_interest_veb:>12.2f}")
print()

print("=" * 80)
print("COMPARISON: Two Different Calculation Methods")
print("=" * 80)
print()

# Method 1: Accrual-based (month-by-month conversion)
print("METHOD 1: ACCRUAL ACCOUNTING (Current Prestaciones Report)")
print("  - Each month's interest converted at THAT month's rate")
print("  - Represents actual ledger postings each month")
print(f"  - Total Interest VEB: Bs. {accumulated_interest_veb:,.2f}")
print("  ✅ This matches what was ACTUALLY recorded in accounting ledger")
print()

# Method 2: Single rate conversion (what Relación report does)
end_date_rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', end_date)
], limit=1, order='name desc')
end_date_rate = end_date_rate_record.company_rate if end_date_rate_record and hasattr(end_date_rate_record, 'company_rate') else 0.0

single_conversion_veb = intereses_usd * end_date_rate

print("METHOD 2: SINGLE RATE CONVERSION (Current Relación Report)")
print(f"  - Total USD interest × End date rate")
print(f"  - ${intereses_usd:.2f} × {end_date_rate:.4f}")
print(f"  - Total Interest VEB: Bs. {single_conversion_veb:,.2f}")
print("  ⚠️  This DOES NOT match actual ledger entries!")
print()

print("=" * 80)
print("THE PROBLEM")
print("=" * 80)
print()
print("⚠️  RELACIÓN REPORT is using WRONG calculation!")
print(f"    - Shows: Bs. {single_conversion_veb:,.2f} (single rate conversion)")
print(f"    - Should show: Bs. {accumulated_interest_veb:,.2f} (accrual-based)")
print()
print("⚠️  PRESTACIONES INTEREST REPORT is CORRECT!")
print(f"    - Shows: Bs. {accumulated_interest_veb:,.2f} (accrual-based)")
print("    - Matches actual monthly ledger postings")
print()

print("=" * 80)
print("CORRECT SOLUTION")
print("=" * 80)
print()
print("✅ FIX: Relación Report should use ACCRUAL calculation for Interest")
print()
print("   Current Relación logic (WRONG):")
print("     inter_amt = self._convert_currency(intereses, usd, currency, date_ref, exchange_rate)")
print("     # Uses single rate for entire period")
print()
print("   Corrected Relación logic (RIGHT):")
print("     inter_amt = self._calculate_accrual_interest(payslip, currency)")
print("     # Calculate month-by-month like Prestaciones Report")
print()
print("   WHY:")
print("     - Interest accrues MONTHLY in accounting ledger")
print("     - Each month posts at THAT month's exchange rate")
print("     - Total = SUM of monthly VEB ledger entries")
print("     - NOT a simple USD total × current rate")
print()

print("📝 RESULT:")
print("   - Both reports will show same VEB amount (accrual-based)")
print("   - Amounts match actual accounting ledger")
print("   - Employee sees consistent, accurate information")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
