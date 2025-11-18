#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze USD Display and Accounting Journal Entry Implications

This script investigates:
1. How interest looks when USD is selected for display
2. What amount gets posted to journal entries
3. Accounting implications of accrual-based vs single-rate approach
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("USD DISPLAY AND ACCOUNTING ANALYSIS")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get key values
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

service_months = get_line('LIQUID_SERVICE_MONTHS_V2')
intereses_usd = get_line('LIQUID_INTERESES_V2')
interest_per_month = intereses_usd / service_months if service_months > 0 else 0.0

print("=" * 80)
print("QUESTION 1: USD DISPLAY BEHAVIOR")
print("=" * 80)
print()
print("When user selects USD currency for report display:")
print()
print(f"Total Interest from Payslip: ${intereses_usd:.2f} USD")
print(f"Interest per Month: ${interest_per_month:.4f} USD")
print()
print("Both reports should display:")
print(f"  Prestaciones Soc. Intereses Report: Total = ${intereses_usd:.2f}")
print(f"  Relación de Liquidación Report: Intereses item = ${intereses_usd:.2f}")
print()
print("✅ In USD mode:")
print("   - NO exchange rate conversion needed")
print("   - Both reports show same USD amount")
print("   - Simple and consistent")
print()

print("=" * 80)
print("QUESTION 2: JOURNAL ENTRY POSTING")
print("=" * 80)
print()

# Check current journal entry
if hasattr(payslip, 'move_id') and payslip.move_id:
    print(f"Current Journal Entry: {payslip.move_id.name}")
    print(f"Posting Date: {payslip.move_id.date}")
    print(f"State: {payslip.move_id.state}")
    print()

    # Find interest line
    interest_lines = payslip.move_id.line_ids.filtered(
        lambda l: 'Intereses' in l.name or 'INTERESES' in l.name.upper()
    )

    if interest_lines:
        print("Current Interest Journal Entry Line:")
        print("-" * 80)
        for line in interest_lines:
            print(f"  Account: {line.account_id.code} - {line.account_id.name}")
            print(f"  Debit: ${line.debit:.2f} USD")
            print(f"  Credit: ${line.credit:.2f} USD")
            print(f"  Label: {line.name}")
            print(f"  Currency: {line.currency_id.name if line.currency_id else 'Company currency'}")

            # Check if there's amount_currency (multi-currency)
            if hasattr(line, 'amount_currency') and line.amount_currency:
                print(f"  Amount Currency: {line.amount_currency:.2f}")
            print()
    else:
        print("⚠️  No interest line found in journal entry")
        print()

    # Show company currency
    company = env.company
    print(f"Company Currency: {company.currency_id.name}")
    print()

print("=" * 80)
print("ACCOUNTING SCENARIOS ANALYSIS")
print("=" * 80)
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get exchange rates
end_date = payslip.date_to
end_rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', end_date)
], limit=1, order='name desc')
end_rate = end_rate_record.company_rate if end_rate_record and hasattr(end_rate_record, 'company_rate') else 0.0

print("SCENARIO A: Current Implementation (Single Rate)")
print("-" * 80)
print("Journal Entry Posts:")
print(f"  Date: {end_date}")
print(f"  Amount: ${intereses_usd:.2f} USD")
print(f"  Exchange Rate (if converted to VEB): {end_rate:.4f}")
print(f"  VEB Equivalent: Bs. {intereses_usd * end_rate:,.2f}")
print()
print("Accounting Entry:")
print(f"  Dr. 5.1.01.10.011 Intereses prestaciones soc.     ${intereses_usd:.2f}")
print(f"  Cr. 2.1.01.10.004 Provisión intereses prestaciones ${intereses_usd:.2f}")
print()
print("If company uses VEB functional currency:")
print(f"  VEB amount posted: Bs. {intereses_usd * end_rate:,.2f}")
print(f"  (Converted at liquidation date rate: {end_rate:.4f})")
print()

print("=" * 80)
print("SCENARIO B: Accrual-Based Approach (Option 3)")
print("-" * 80)
print()

# Calculate month-by-month accrual in VEB
contract = payslip.contract_id
start_date = contract.date_start
current_date = start_date
month_num = 0
accumulated_interest_veb = 0.0

print("Monthly Accruals (if posted monthly):")
print(f"{'Month':<10} {'Int USD':<12} {'Rate':<10} {'Int VEB':<15} {'Accum VEB':<15}")
print("-" * 70)

while current_date <= end_date:
    month_num += 1

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
    month_interest_veb = interest_per_month * month_rate
    accumulated_interest_veb += month_interest_veb

    month_name = current_date.strftime("%b-%y")

    if month_num <= 3 or month_num >= (service_months - 2):
        print(f"{month_name:<10} ${interest_per_month:>10.4f} {month_rate:>9.4f} "
              f"Bs.{month_interest_veb:>12.2f} Bs.{accumulated_interest_veb:>12,.2f}")
    elif month_num == 4:
        print("...")

    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

print("-" * 70)
print(f"{'TOTAL':<10} ${intereses_usd:>10.2f} {'':<10} {'':<15} Bs.{accumulated_interest_veb:>12,.2f}")
print()

print("IF Posted Monthly (23 journal entries):")
print("  Each month would post:")
print(f"    Dr. 5.1.01.10.011 Intereses prestaciones ${interest_per_month:.2f}")
print(f"    Cr. 2.1.01.10.004 Provisión intereses     ${interest_per_month:.2f}")
print("  Each converted at that month's rate")
print(f"  Total VEB in ledger: Bs. {accumulated_interest_veb:,.2f}")
print()

print("IF Posted Once at Liquidation (1 journal entry):")
print("  Option A - Post USD amount:")
print(f"    Dr. 5.1.01.10.011 Intereses prestaciones ${intereses_usd:.2f}")
print(f"    Cr. 2.1.01.10.004 Provisión intereses     ${intereses_usd:.2f}")
print(f"    VEB equivalent at liquidation rate: Bs. {intereses_usd * end_rate:,.2f}")
print()
print("  Option B - Post accrued VEB amount:")
print(f"    Dr. 5.1.01.10.011 Intereses prestaciones Bs. {accumulated_interest_veb:,.2f}")
print(f"    Cr. 2.1.01.10.004 Provisión intereses     Bs. {accumulated_interest_veb:,.2f}")
print(f"    USD equivalent: ${accumulated_interest_veb / end_rate:.2f}")
print()

print("=" * 80)
print("THE FUNDAMENTAL QUESTION")
print("=" * 80)
print()
print("❓ What is the company's functional currency?")
print()
company_currency = env.company.currency_id
print(f"   Current Setting: {company_currency.name}")
print()

if company_currency.name == 'USD':
    print("✅ Company uses USD as functional currency")
    print()
    print("   Implications:")
    print("   - All journal entries post in USD")
    print("   - VEB is just a DISPLAY currency for reports")
    print("   - Ledger amount: ${:.2f} (no matter which VEB rate used)".format(intereses_usd))
    print("   - Accrual calculation only affects REPORT DISPLAY in VEB")
    print()
    print("   Journal Entry (always the same in ledger):")
    print("     Dr. 5.1.01.10.011  ${:.2f}".format(intereses_usd))
    print("     Cr. 2.1.01.10.004  ${:.2f}".format(intereses_usd))
    print()
    print("   Report Display Options:")
    print("     USD: ${:.2f}".format(intereses_usd))
    print("     VEB (single rate): Bs. {:,.2f}".format(intereses_usd * end_rate))
    print("     VEB (accrual): Bs. {:,.2f}".format(accumulated_interest_veb))
    print()
    print("   ⭐ RECOMMENDATION:")
    print("      - Ledger posts in USD (no change needed)")
    print("      - Reports offer VEB display for convenience")
    print("      - Accrual-based VEB is more economically accurate")
    print()

elif company_currency.name == 'VEB':
    print("✅ Company uses VEB as functional currency")
    print()
    print("   Implications:")
    print("   - All journal entries post in VEB")
    print("   - Must decide which VEB amount to post:")
    print()
    print("     Option 1: Single rate at liquidation")
    print("       Amount: Bs. {:,.2f}".format(intereses_usd * end_rate))
    print("       Simpler, but economically less accurate")
    print()
    print("     Option 2: Accrual-based total")
    print("       Amount: Bs. {:,.2f}".format(accumulated_interest_veb))
    print("       More accurate, reflects economic reality")
    print()
    print("   ⭐ RECOMMENDATION:")
    print("      - Use accrual-based amount for posting")
    print("      - Matches monthly accrual concept")
    print("      - Reports will match ledger exactly")
    print()

print("=" * 80)
print("FINAL RECOMMENDATIONS")
print("=" * 80)
print()
print("1. USD DISPLAY (both reports):")
print(f"   ✅ Always show: ${intereses_usd:.2f}")
print("   No conversion needed, simple and consistent")
print()
print("2. VEB DISPLAY (both reports):")
print("   ✅ Default: Use accrual-based calculation")
print(f"   Shows: Bs. {accumulated_interest_veb:,.2f}")
print("   More economically accurate than single rate")
print()
print("3. JOURNAL ENTRY:")
if company_currency.name == 'USD':
    print(f"   ✅ Post in USD: ${intereses_usd:.2f}")
    print("   (Current implementation is correct)")
elif company_currency.name == 'VEB':
    print(f"   ⚠️  Currently posts: Bs. {intereses_usd * end_rate:,.2f} (single rate)")
    print(f"   ⭐ Should consider: Bs. {accumulated_interest_veb:,.2f} (accrual-based)")
print()
print("4. REPORTS vs LEDGER:")
print("   - Reports are for EMPLOYEE INFORMATION (can show accrual)")
print("   - Ledger is for COMPANY ACCOUNTING (follows company policy)")
print("   - These don't have to match if USD is functional currency")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
