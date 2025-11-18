#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug monthly accumulation in Prestaciones Interest Report
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)
if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

service_months = get_line('LIQUID_SERVICE_MONTHS_V2')
intereses_usd = get_line('LIQUID_INTERESES_V2')
interest_per_month = intereses_usd / service_months

contract = payslip.contract_id
start_date = contract.date_start
end_date = payslip.date_to

print("=" * 80)
print("DEBUGGING MONTHLY ACCUMULATION")
print("=" * 80)
print()
print(f"Total Interest (USD): ${intereses_usd:.2f}")
print(f"Service Months: {service_months:.2f}")
print(f"Interest per month (USD): ${interest_per_month:.4f}")
print()

# Simulate the loop
current_date = start_date
month_num = 0
accumulated_interest_usd = 0.0

print("SIMULATING MONTHLY LOOP:")
print("=" * 80)
print(f"{'#':<3} {'Month':<10} {'Month Int':<12} {'Accum USD':<12} {'Rate':<10} {'Accum VEB':<15}")
print("-" * 80)

while current_date <= end_date:
    month_num += 1

    # Monthly interest (USD)
    month_interest_usd = interest_per_month
    accumulated_interest_usd += month_interest_usd

    # Get rate for this month
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_record:
        rate_record = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_record.company_rate if rate_record and hasattr(rate_record, 'company_rate') else 0.0

    # Convert accumulated USD to VEB using THIS month's rate
    # THIS IS THE BUG: Should accumulate VEB, not re-convert USD total
    accumulated_veb_wrong = usd._convert(
        from_amount=accumulated_interest_usd,
        to_currency=veb,
        company=env.company,
        date=current_date
    )

    month_name = current_date.strftime("%b-%y")

    print(f"{month_num:<3} {month_name:<10} ${month_interest_usd:>10.4f} ${accumulated_interest_usd:>10.2f} "
          f"{month_rate:>9.4f} Bs.{accumulated_veb_wrong:>12,.2f}")

    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

print()
print("=" * 80)
print("THE BUG EXPLAINED")
print("=" * 80)
print()
print("Current code (WRONG approach):")
print("  accumulated_interest = 0.0  # USD")
print("  for each month:")
print("    accumulated_interest += month_interest  # Add USD")
print("    accumulated_veb = convert(accumulated_interest, current_month_rate)  # ❌ WRONG!")
print()
print("Why this is wrong:")
print("  - Each month re-converts the TOTAL accumulated USD using THAT month's rate")
print("  - Earlier months' interest gets converted multiple times with different rates")
print("  - This is NOT accrual accounting!")
print()
print("Correct approach (accrual accounting):")
print("  accumulated_interest_veb = 0.0  # VEB")
print("  for each month:")
print("    month_interest_usd = interest_per_month")
print("    month_interest_veb = convert(month_interest_usd, current_month_rate)")
print("    accumulated_interest_veb += month_interest_veb  # Add VEB")
print()
print("This way:")
print("  - Each month's interest is converted ONCE at its own rate")
print("  - VEB amounts accumulate properly")
print("  - Matches accrual accounting principles")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
