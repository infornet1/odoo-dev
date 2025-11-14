#!/usr/bin/env python3
"""
Check VEB exchange rate availability for historical dates.
"""

import sys
from datetime import date

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("CHECKING HISTORICAL VEB EXCHANGE RATES")
print("=" * 80)

veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get all VEB rates
all_rates = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], order='name asc')

print(f"\n📊 Total VEB rates in database: {len(all_rates)}")

if all_rates:
    earliest = all_rates[0]
    latest = all_rates[-1]

    print(f"\n   Earliest rate: {earliest.name} (rate={earliest.rate:.6f}, company_rate={earliest.company_rate:.2f})")
    print(f"   Latest rate: {latest.name} (rate={latest.rate:.6f}, company_rate={latest.company_rate:.2f})")

# Test dates from SLIP/568 (Sep 2023 - Jul 2025)
test_dates = [
    date(2023, 9, 1),   # Contract start
    date(2024, 1, 1),   # Middle
    date(2025, 7, 31),  # Liquidation end
    date(2025, 11, 14), # Today
]

print(f"\n🔍 Testing exchange rate lookup for SLIP/568 dates:")
for test_date in test_dates:
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', test_date)
    ], limit=1, order='name desc')

    if rate_record:
        print(f"\n   {test_date}:")
        print(f"      Found rate from: {rate_record.name}")
        print(f"      Rate: {rate_record.rate:.6f}")
        print(f"      Company rate: {rate_record.company_rate:.2f} VEB/USD")
    else:
        print(f"\n   {test_date}:")
        print(f"      ❌ NO RATE FOUND")

# Test what _get_exchange_rate returns for old dates
print(f"\n" + "=" * 80)
print("TESTING _get_exchange_rate() METHOD")
print("=" * 80)

report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

for test_date in test_dates:
    rate = report_model._get_exchange_rate(test_date, veb)
    print(f"   {test_date}: {rate:.2f} VEB/USD")

print("\n💡 ISSUE: VEB rates only exist from 2025-11-07 onwards")
print("   For historical dates (2023-2025), the method returns the")
print("   oldest available rate, which may not be accurate.")
