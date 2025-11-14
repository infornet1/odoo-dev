#!/usr/bin/env python3
"""
Test VEB currency conversion logic.
"""

import sys
from datetime import date

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("TESTING VEB CONVERSION LOGIC")
print("=" * 80)

# Get currencies
usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

print(f"\n💵 USD: {usd.name} (ID: {usd.id}, Symbol: {usd.symbol})")
print(f"💸 VEB: {veb.name} (ID: {veb.id}, Symbol: {veb.symbol})")

# Get latest VEB rate
latest_veb_rate = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], limit=1, order='name desc')

print(f"\n📊 Latest VEB Rate Record:")
print(f"   Date: {latest_veb_rate.name}")
print(f"   rate field: {latest_veb_rate.rate}")
print(f"   inverse_company_rate field: {latest_veb_rate.inverse_company_rate}")
print(f"   company_rate field: {latest_veb_rate.company_rate if hasattr(latest_veb_rate, 'company_rate') else 'N/A'}")

# Calculate proper conversion
print(f"\n🧮 Conversion Calculation:")
if latest_veb_rate.rate > 0:
    veb_per_usd = 1.0 / latest_veb_rate.rate
    print(f"   1 / {latest_veb_rate.rate} = {veb_per_usd:.4f} VEB/USD")

    test_amount = 100.0
    converted = test_amount * veb_per_usd
    print(f"\n   Test: ${test_amount:.2f} USD = {converted:,.2f} VEB")
else:
    print("   ❌ Rate is 0, cannot convert")

# Try using Odoo's built-in conversion
print(f"\n🔄 Using Odoo's _convert method:")
test_amount = 100.0
test_date = date(2025, 11, 14)

try:
    # Convert from USD to VEB
    converted = usd._convert(
        from_amount=test_amount,
        to_currency=veb,
        company=env.company,
        date=test_date
    )
    print(f"   ${test_amount:.2f} USD → {converted:,.2f} VEB")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Check rate interpretation
print(f"\n📖 Rate Interpretation:")
print(f"   If rate = {latest_veb_rate.rate:.6f}")
print(f"   This means: 1 VEB = {latest_veb_rate.rate:.6f} USD")
print(f"   Therefore: 1 USD = {1.0/latest_veb_rate.rate if latest_veb_rate.rate > 0 else 'ERROR':.2f} VEB")
