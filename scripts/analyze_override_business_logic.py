#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Exchange Rate Override Business Logic

Should interest calculation be excluded from exchange rate override?
Let's examine the implications.
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("BUSINESS LOGIC ANALYSIS: EXCHANGE RATE OVERRIDE")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get payslip values
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

vacaciones = get_line('LIQUID_VACACIONES_V2')
bono_vacacional = get_line('LIQUID_BONO_VACACIONAL_V2')
utilidades = get_line('LIQUID_UTILIDADES_V2')
prestaciones = get_line('LIQUID_PRESTACIONES_V2')
antiguedad = get_line('LIQUID_ANTIGUEDAD_V2')
intereses = get_line('LIQUID_INTERESES_V2')
service_months = get_line('LIQUID_SERVICE_MONTHS_V2')

print("LIQUIDATION BENEFITS (USD):")
print("-" * 80)
print(f"1. Vacaciones:                   ${vacaciones:.2f}")
print(f"2. Bono Vacacional:              ${bono_vacacional:.2f}")
print(f"3. Utilidades:                   ${utilidades:.2f}")
print(f"4. Prestaciones Sociales:        ${prestaciones:.2f}")
print(f"5. Antigüedad:                   ${antiguedad:.2f}")
print(f"6. Intereses sobre Prestaciones: ${intereses:.2f}")
print(f"   Service Period: {service_months:.2f} months")
print()

# Exchange rates
end_date = payslip.date_to
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', end_date)
], limit=1, order='name desc')
automatic_rate = rate_record.company_rate if rate_record and hasattr(rate_record, 'company_rate') else 0.0

nov_17_rate = 236.4601  # The override rate being used

print("EXCHANGE RATES:")
print("-" * 80)
print(f"Automatic (July 31, 2025):  {automatic_rate:.4f} VEB/USD")
print(f"Override (Nov 17, 2025):     {nov_17_rate:.4f} VEB/USD")
print(f"Difference: +{((nov_17_rate/automatic_rate - 1) * 100):.1f}%")
print()

print("=" * 80)
print("SCENARIO A: ALL BENEFITS USE OVERRIDE RATE (Current Implementation)")
print("=" * 80)
print()

print("All benefits converted at Nov 17 rate (236.4601):")
print("-" * 80)
vac_override = vacaciones * nov_17_rate
bono_override = bono_vacacional * nov_17_rate
util_override = utilidades * nov_17_rate
prest_override = prestaciones * nov_17_rate
antig_override = antiguedad * nov_17_rate
inter_override = intereses * nov_17_rate

print(f"1. Vacaciones:                   Bs. {vac_override:,.2f}")
print(f"2. Bono Vacacional:              Bs. {bono_override:,.2f}")
print(f"3. Utilidades:                   Bs. {util_override:,.2f}")
print(f"4. Prestaciones Sociales:        Bs. {prest_override:,.2f}")
print(f"5. Antigüedad:                   Bs. {antig_override:,.2f}")
print(f"6. Intereses sobre Prestaciones: Bs. {inter_override:,.2f}")
total_override = vac_override + bono_override + util_override + prest_override + antig_override + inter_override
print(f"   TOTAL:                        Bs. {total_override:,.2f}")
print()

print("Business Logic:")
print("  ✅ Consistent: All benefits use same rate")
print("  ✅ Simple: Easy to understand and verify")
print("  ✅ Use Case: Employee payment delayed to Nov 17, ALL amounts paid at Nov 17 rate")
print("  ⚠️  Issue: Interest doesn't reflect monthly accrual reality")
print()

print("=" * 80)
print("SCENARIO B: INTEREST USES ACCRUAL, OTHERS USE OVERRIDE (Proposed)")
print("=" * 80)
print()

# Calculate accrual-based interest
contract = payslip.contract_id
start_date = contract.date_start
interest_per_month = intereses / service_months

accumulated_interest_veb = 0.0
current_date = start_date

while current_date <= end_date:
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
    accumulated_interest_veb += month_interest_veb

    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

inter_accrual = accumulated_interest_veb

print("Benefits 1-5 use override, Interest uses accrual:")
print("-" * 80)
print(f"1. Vacaciones:                   Bs. {vac_override:,.2f} (override)")
print(f"2. Bono Vacacional:              Bs. {bono_override:,.2f} (override)")
print(f"3. Utilidades:                   Bs. {util_override:,.2f} (override)")
print(f"4. Prestaciones Sociales:        Bs. {prest_override:,.2f} (override)")
print(f"5. Antigüedad:                   Bs. {antig_override:,.2f} (override)")
print(f"6. Intereses sobre Prestaciones: Bs. {inter_accrual:,.2f} (accrual)")
total_mixed = vac_override + bono_override + util_override + prest_override + antig_override + inter_accrual
print(f"   TOTAL:                        Bs. {total_mixed:,.2f}")
print()

print("Business Logic:")
print("  ✅ Accurate: Interest reflects monthly accrual accounting")
print("  ✅ Realistic: Interest accumulated over time at historical rates")
print("  ⚠️  Inconsistent: Not all benefits use same rate")
print("  ⚠️  Complex: Harder to verify (why is one different?)")
print()

print("=" * 80)
print("COMPARISON")
print("=" * 80)
print()
print(f"Scenario A (All Override):  Total = Bs. {total_override:,.2f}")
print(f"Scenario B (Mixed):         Total = Bs. {total_mixed:,.2f}")
print(f"Difference:                        Bs. {abs(total_override - total_mixed):,.2f}")
print()
print(f"Interest difference:")
print(f"  Override:  Bs. {inter_override:,.2f}")
print(f"  Accrual:   Bs. {inter_accrual:,.2f}")
print(f"  Diff:      Bs. {abs(inter_override - inter_accrual):,.2f} ({abs(inter_override/inter_accrual - 1)*100:.1f}% difference)")
print()

print("=" * 80)
print("ACCOUNTING PERSPECTIVE")
print("=" * 80)
print()

print("Question: When is the journal entry posted?")
print("  Answer: At liquidation time (July 31, 2025)")
print()
print("Question: What amount is posted to ledger?")
company = env.company
print(f"  Company currency: {company.currency_id.name}")
if company.currency_id.name == 'USD':
    print(f"  Amount posted: ${intereses:.2f} USD (always the same)")
    print("  ✅ Override rate doesn't affect accounting!")
print()

print("Question: When does employee receive payment?")
print("  Liquidation date: July 31, 2025")
print("  Actual payment:   November 17, 2025 (delayed)")
print("  Override reason:  Use Nov 17 rate for actual payment")
print()

print("=" * 80)
print("THE BUSINESS QUESTION")
print("=" * 80)
print()
print("WHY use Nov 17 override rate?")
print()
print("Option 1: CASH FLOW REALITY")
print("  - Employee receives money on Nov 17")
print("  - ALL benefits should use Nov 17 rate")
print("  - Interest is just another benefit")
print("  ✅ Makes sense: Everything paid at same time = same rate")
print()
print("Option 2: ACCRUAL ACCOUNTING ACCURACY")
print("  - Interest accrued monthly over 23 months")
print("  - Each month's interest has its own economic value")
print("  - Payment date doesn't change accrual history")
print("  ✅ Makes sense: Interest is fundamentally different")
print()

print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()
print("🤔 The choice depends on business intent:")
print()
print("KEEP CURRENT (All Override):")
print("  - If override represents PAYMENT DATE")
print("  - Employee receives ALL benefits on Nov 17")
print("  - Simple, consistent, easy to explain")
print("  - Interest treated like any other benefit")
print()
print("CHANGE TO PROPOSED (Interest Accrual):")
print("  - If override represents DISPLAY PREFERENCE")
print("  - Interest is different from other benefits (accrues over time)")
print("  - More accounting-accurate")
print("  - Matches Prestaciones Interest Report")
print()
print("SUGGESTED APPROACH:")
print("  1. Ask business: 'Why do you need override rate?'")
print("  2. If answer is 'delayed payment' → Keep current (all override)")
print("  3. If answer is 'display accuracy' → Change to accrual for interest")
print()
print("MY RECOMMENDATION:")
print("  Keep CURRENT implementation (all override)")
print("  Reason: When payment is delayed, ALL amounts paid at same rate")
print("  This is simpler and more consistent for employee understanding")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
