#!/usr/bin/env python3
"""Test rate date lookup with Nov 17, 2025"""

from datetime import datetime, date

print("="*80)
print("TEST RATE DATE LOOKUP - Nov 17, 2025")
print("="*80)

# Get VEB currency
Currency = env['res.currency']
CurrencyRate = env['res.currency.rate']

veb = Currency.search([('name', '=', 'VEB')], limit=1)
if not veb:
    print("ERROR: VEB currency not found")
    exit(1)

print(f"VEB Currency ID: {veb.id}")

# Test with Nov 17, 2025
test_date = date(2025, 11, 17)
print(f"\nLooking up rate for: {test_date} (Nov 17, 2025)")

# Same logic as report
rate_record = CurrencyRate.search([
    ('currency_id', '=', veb.id),
    ('name', '<=', test_date)
], limit=1, order='name desc')

if rate_record:
    print(f"\n✅ Found rate record:")
    print(f"   ID: {rate_record.id}")
    print(f"   Date: {rate_record.name}")
    print(f"   Rate (inverse): {rate_record.rate}")
    
    if hasattr(rate_record, 'company_rate'):
        print(f"   Company Rate: {rate_record.company_rate}")
        exchange_rate = rate_record.company_rate
    elif rate_record.rate > 0:
        exchange_rate = 1.0 / rate_record.rate
    else:
        exchange_rate = 1.0
        
    print(f"\n   📊 EXCHANGE RATE: {exchange_rate:.4f} VEB/USD")
else:
    print("\n❌ No rate found!")

# Show all recent rates
print("\n" + "="*80)
print("RECENT VEB RATES (Last 10)")
print("="*80)

recent = CurrencyRate.search([
    ('currency_id', '=', veb.id)
], limit=10, order='name desc')

for r in recent:
    if hasattr(r, 'company_rate'):
        rate = r.company_rate
    elif r.rate > 0:
        rate = 1.0 / r.rate
    else:
        rate = 0.0
    
    indicator = " ← SELECTED" if r.id == rate_record.id else ""
    print(f"   {r.name}: {rate:.4f} VEB/USD{indicator}")

print("="*80)
