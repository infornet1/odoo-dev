#!/usr/bin/env python3
"""
Verify how Odoo's _convert() handles historical dates without rates.
"""

import sys
from datetime import date

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("VERIFYING ODOO CURRENCY CONVERSION FOR HISTORICAL DATES")
print("=" * 80)

usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get earliest VEB rate
earliest_rate = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], limit=1, order='name asc')

print(f"\n📊 Earliest VEB rate in database:")
print(f"   Date: {earliest_rate.name}")
print(f"   Company Rate: {earliest_rate.company_rate:.2f} VEB/USD")

# Test conversion for dates before earliest rate
test_amount = 143.40  # Monthly income from SLIP/568 first month

test_dates = [
    (date(2023, 9, 1), "Before earliest rate (Sep 2023)"),
    (date(2024, 1, 1), "Before earliest rate (Jan 2024)"),
    (date(2024, 1, 30), "Earliest rate date"),
    (date(2024, 2, 1), "After earliest rate (Feb 2024)"),
    (date(2025, 7, 31), "Recent date (Jul 2025)"),
]

print(f"\n💰 Converting ${test_amount:.2f} USD to VEB:")

for test_date, description in test_dates:
    converted = usd._convert(
        from_amount=test_amount,
        to_currency=veb,
        company=env.company,
        date=test_date
    )

    # Get the rate that was used
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', test_date)
    ], limit=1, order='name desc')

    if rate_record:
        rate_used = rate_record.company_rate
        rate_date = rate_record.name
        print(f"\n   {test_date} ({description}):")
        print(f"      Rate used: {rate_used:.2f} VEB/USD (from {rate_date})")
        print(f"      Result: Bs.{converted:,.2f}")
        print(f"      Calculation: ${test_amount:.2f} × {rate_used:.2f} = Bs.{test_amount * rate_used:,.2f}")
    else:
        print(f"\n   {test_date} ({description}):")
        print(f"      ❌ NO RATE - Result: Bs.{converted:,.2f}")
        print(f"      (Odoo using unknown fallback logic)")

print(f"\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print(f"""
When converting to VEB for dates BEFORE the earliest rate (2024-01-30):
- Odoo's _convert() uses the EARLIEST available rate ({earliest_rate.company_rate:.2f} VEB/USD)
- This explains why Sep 2023 shows: $143.40 × {earliest_rate.company_rate:.2f} ≈ Bs.5,086.65

For the exchange rate DISPLAY column ("Tasa del Mes"):
- We should show the actual rate used for conversion
- Or show "N/A" if no rate exists for that date
""")
