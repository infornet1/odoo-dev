#!/usr/bin/env python3
"""Execute VEB rate sync on testing database."""
import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("SYNCING VEB RATES FROM PRODUCTION TO TESTING")
print("=" * 80)

# Insert missing VEB rates
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("❌ VEB currency not found")
    sys.exit(1)

print(f"\n📊 Before sync:")
before_count = env['res.currency.rate'].search_count([('currency_id', '=', veb.id)])
print(f"   Total VEB rates: {before_count}")

# Missing rates from production
missing_rates = [
    ('2025-11-12', 2.458226795946094),
    ('2025-11-13', 2.463625393449955),
    ('2025-11-14', 2.477484747221589),
]

print(f"\n📝 Inserting {len(missing_rates)} missing rates:")

for date_str, rate_value in missing_rates:
    # Check if rate exists
    existing = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '=', date_str),
        ('company_id', '=', 1)
    ], limit=1)

    if existing:
        # Update existing
        existing.write({'rate': rate_value})
        print(f"   ✅ Updated {date_str}: rate={rate_value:.15f}")
    else:
        # Create new
        env['res.currency.rate'].create({
            'name': date_str,
            'rate': rate_value,
            'currency_id': veb.id,
            'company_id': 1,
        })
        print(f"   ✅ Inserted {date_str}: rate={rate_value:.15f}")

# Commit the transaction
env.cr.commit()

print(f"\n📊 After sync:")
after_count = env['res.currency.rate'].search_count([('currency_id', '=', veb.id)])
print(f"   Total VEB rates: {after_count}")
print(f"   Added: {after_count - before_count} rates")

# Verify latest rates
print(f"\n🔍 Latest 5 VEB rates:")
latest_rates = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], order='name desc', limit=5)

for rate in latest_rates:
    print(f"   {rate.name}: rate={rate.rate:.15f}")

print(f"\n✅ VEB SYNC COMPLETE!")
print(f"   Production: 622 rates")
print(f"   Testing: {after_count} rates")
if after_count == 622:
    print(f"   🎉 SYNCED!")
else:
    print(f"   ⚠️  Mismatch: Expected 622, got {after_count}")
