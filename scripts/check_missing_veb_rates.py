#!/usr/bin/env python3
"""
Check what VEB rates are missing in testing database.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("CHECKING VEB RATES IN TESTING DATABASE")
print("=" * 80)

veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("❌ VEB currency not found")
    sys.exit(1)

# Get all VEB rates
all_rates = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], order='name desc')

print(f"\n📊 Total VEB rates in testing: {len(all_rates)}")

if all_rates:
    earliest = all_rates[-1]
    latest = all_rates[0]

    print(f"\n   Earliest: {earliest.name}")
    print(f"   Latest: {latest.name}")

    # Show last 10 rates
    print(f"\n📅 Last 10 VEB rates:")
    for rate in all_rates[:10]:
        print(f"   {rate.name}: rate={rate.rate:.6f}, company_rate={rate.company_rate:.2f}")

print(f"\n💡 Production has 622 records, testing has {len(all_rates)} records")
print(f"   Missing: {622 - len(all_rates)} records")
