#!/usr/bin/env python3
"""
Check for VEB exchange rate tables and data.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("CHECKING FOR VEB EXCHANGE RATE TABLES")
print("=" * 80)

# Check ir.model for any currency rate models
models = env['ir.model'].search([('model', 'ilike', 'currency')])
print(f"\n📊 Currency-related models:")
for model in models:
    print(f"   - {model.model}: {model.name}")

# Check for res.currency.rate model
rate_model = env['ir.model'].search([('model', '=', 'res.currency.rate')], limit=1)
if rate_model:
    print(f"\n✅ Found: {rate_model.model}")

    # Get VEB currency
    veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
    if veb:
        print(f"   VEB currency ID: {veb.id}")

        # Check for VEB rates
        rates = env['res.currency.rate'].search([('currency_id', '=', veb.id)], limit=5, order='name desc')
        print(f"   Recent VEB rates found: {len(rates)}")
        for rate in rates:
            print(f"      {rate.name}: rate={rate.rate:.6f}, inverse={rate.inverse_company_rate:.2f}")
    else:
        print("   ❌ VEB currency not found")

# Check for USD currency
usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
if usd:
    print(f"\n💵 USD currency ID: {usd.id}")
    print(f"   Symbol: {usd.symbol}")
    usd_rates = env['res.currency.rate'].search([('currency_id', '=', usd.id)], limit=5, order='name desc')
    print(f"   Recent USD rates found: {len(usd_rates)}")
    for rate in usd_rates:
        print(f"      {rate.name}: rate={rate.rate:.6f}")

# Check for any custom VEB rate models
custom_models = env['ir.model'].search([('model', 'ilike', 'veb')])
print(f"\n🔍 VEB-specific models:")
if custom_models:
    for model in custom_models:
        print(f"   - {model.model}: {model.name}")
else:
    print("   No custom VEB models found")

print("\n" + "=" * 80)
print("Testing currency conversion")
print("=" * 80)

if veb and usd:
    # Test conversion from USD to VEB
    from datetime import date
    test_amount = 100.0
    test_date = date(2025, 11, 14)

    print(f"\nTest: Convert ${test_amount} USD to VEB on {test_date}")

    # Get rate for specific date
    veb_rate = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', test_date)
    ], limit=1, order='name desc')

    if veb_rate:
        print(f"   VEB rate found: {veb_rate.name} = {veb_rate.inverse_company_rate:.2f} VEB/USD")
        converted = test_amount * veb_rate.inverse_company_rate
        print(f"   Result: ${test_amount} USD = {converted:,.2f} VEB")
    else:
        print(f"   ❌ No VEB rate found for {test_date}")
