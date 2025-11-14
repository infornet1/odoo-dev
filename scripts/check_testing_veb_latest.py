#!/usr/bin/env python3
"""Check latest VEB rates in testing database."""
import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
all_rates = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], order='name desc')

print(f"Total VEB rates in testing: {len(all_rates)}")
print(f"\nLatest 10 VEB rates:")
for rate in all_rates[:10]:
    print(f"  {rate.name}: rate={rate.rate:.15f}")
