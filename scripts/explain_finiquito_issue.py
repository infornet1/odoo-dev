#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explain Finiquito Issue - Exchange Rate Override Not Applied

The Finiquito report is NOT respecting the exchange rate override.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("FINIQUITO ISSUE: EXCHANGE RATE OVERRIDE NOT APPLIED")
print("=" * 80)
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

print("THE PROBLEM:")
print("-" * 80)
print("When user generates Finiquito with exchange rate override (Nov 17):")
print("  - Relación Report: Bs. 300,621.18 ✅ (uses override)")
print("  - Finiquito Report: Bs. 158,294.80 ❌ (ignores override)")
print()

print("=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)
print()

print("LOCATION: finiquito_report.py lines 42-51")
print("-" * 80)
print()

print("CURRENT CODE (WRONG):")
print("""
# Convert to selected currency if needed (payslip uses company currency)
payslip_currency = payslip.company_id.currency_id
if currency != payslip_currency:
    # Get exchange rate for payslip date
    rate_date = payslip.date_to or payslip.date_from
    net_amount = payslip_currency._convert(
        net_amount,
        currency,
        payslip.company_id,
        rate_date                           # ❌ Uses automatic rate (Jul 31)
    )
""")
print()

print("THE ISSUE:")
print("-" * 80)
print("1. Finiquito uses Odoo's _convert() with rate_date = payslip.date_to")
print("2. This ALWAYS uses the automatic rate for July 31, 2025")
print("3. It IGNORES the wizard's use_custom_rate and custom_exchange_rate")
print("4. The 'data' parameter contains the override info, but it's NOT used!")
print()

# Show the data parameter
data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

print("WIZARD DATA AVAILABLE (but ignored):")
print("-" * 80)
print(f"  use_custom_rate: {data_with_override['use_custom_rate']}")
print(f"  custom_exchange_rate: {data_with_override['custom_exchange_rate']}")
print()

# Get the net amount in USD
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

net_usd = get_line('LIQUID_NET_V2') or get_line('LIQUID_NET')
net_usd = abs(net_usd)

print("CALCULATION COMPARISON:")
print("-" * 80)
print(f"Net Amount (USD): ${net_usd:.2f}")
print()

# Get automatic rate for July 31
rate_rec = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', payslip.date_to)
], limit=1, order='name desc')
automatic_rate = rate_rec.company_rate if rate_rec and hasattr(rate_rec, 'company_rate') else 0.0

print(f"Automatic rate (Jul 31): {automatic_rate:.4f}")
print(f"Finiquito calculates: ${net_usd:.2f} × {automatic_rate:.4f} = Bs. {net_usd * automatic_rate:,.2f}")
print()

# With override
override_rate = 236.4601
print(f"Override rate (Nov 17): {override_rate:.4f}")
print(f"Should calculate: ${net_usd:.2f} × {override_rate:.4f} = Bs. {net_usd * override_rate:,.2f}")
print()

print(f"Difference: Bs. {abs((net_usd * override_rate) - (net_usd * automatic_rate)):,.2f}")
print()

print("=" * 80)
print("THE FIX NEEDED")
print("=" * 80)
print()

print("Finiquito needs to use the SAME logic as Relación report:")
print()
print("1. Check if data contains 'use_custom_rate' and it's True")
print("2. If yes, use 'custom_exchange_rate' from data")
print("3. If no, use automatic rate for payslip.date_to")
print()

print("PROPOSED CODE:")
print("-" * 80)
print("""
# Convert to selected currency if needed
payslip_currency = payslip.company_id.currency_id
if currency != payslip_currency:
    rate_date = payslip.date_to or payslip.date_from

    # Check for custom exchange rate override (SAME AS RELACIÓN REPORT)
    if data and data.get('use_custom_rate') and data.get('custom_exchange_rate'):
        # Use custom override rate
        exchange_rate = data.get('custom_exchange_rate')
        net_amount = net_amount * exchange_rate
    else:
        # Use automatic rate for payslip date
        net_amount = payslip_currency._convert(
            net_amount,
            currency,
            payslip.company_id,
            rate_date
        )
""")
print()

print("=" * 80)
print("EXPECTED RESULT AFTER FIX")
print("=" * 80)
print()

print("WITHOUT override:")
print(f"  Finiquito: Bs. {net_usd * automatic_rate:,.2f} ✅")
print(f"  Relación:  Bs. 158,294.80 ✅")
print(f"  MATCH!")
print()

print("WITH override (Nov 17, 236.4601):")
print(f"  Finiquito: Bs. {net_usd * override_rate:,.2f} ✅")
print(f"  Relación:  Bs. 300,621.18 ✅")
print(f"  MATCH!")
print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print()

print("ISSUE:")
print("  Finiquito report ignores exchange rate override from wizard")
print()

print("ROOT CAUSE:")
print("  Lines 42-51 in finiquito_report.py use payslip_currency._convert()")
print("  which ALWAYS uses automatic rate, ignoring wizard data")
print()

print("FIX:")
print("  Add check for data['use_custom_rate'] and data['custom_exchange_rate']")
print("  Use direct multiplication when override is enabled")
print("  Same pattern as Relación report")
print()

print("IMPACT:")
print("  Employee receives consistent information across all reports")
print("  No confusion about final amount to claim")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
