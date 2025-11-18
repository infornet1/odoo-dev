#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug the conversion bug in Prestaciones Interest Report
"""

import sys

# Find payslip
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)
if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

print("=" * 80)
print("DEBUGGING CONVERSION LOGIC")
print("=" * 80)
print()

# Test the _convert_currency method
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

intereses_usd = get_line('LIQUID_INTERESES_V2')
end_date = payslip.date_to

print(f"Interest Total (USD): ${intereses_usd:.2f}")
print(f"End Date: {end_date}")
print()

# Get exchange rate for end_date
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', end_date)
], limit=1, order='name desc')

if rate_record:
    print(f"Exchange Rate Record:")
    print(f"  Date: {rate_record.name}")
    print(f"  company_rate: {rate_record.company_rate:.4f}")
    print(f"  rate field: {rate_record.rate:.8f}")
    print()

# Test Odoo's _convert method
print("Testing Odoo's usd._convert() method:")
converted = usd._convert(
    from_amount=intereses_usd,
    to_currency=veb,
    company=env.company,
    date=end_date
)
print(f"  ${intereses_usd:.2f} USD → Bs. {converted:,.2f} VEB")
print(f"  Implied rate: {converted / intereses_usd:.4f}")
print()

# Manual calculation
manual_calc = intereses_usd * rate_record.company_rate
print(f"Manual calculation (USD × company_rate):")
print(f"  ${intereses_usd:.2f} × {rate_record.company_rate:.4f} = Bs. {manual_calc:,.2f}")
print()

print("=" * 80)
print("THE ISSUE")
print("=" * 80)
print()
print("Odoo's _convert() uses the 'rate' field, NOT 'company_rate'!")
print(f"  rate field = {rate_record.rate:.8f}")
print(f"  conversion formula: USD / rate = VEB")
print(f"  ${intereses_usd:.2f} / {rate_record.rate:.8f} = Bs. {intereses_usd / rate_record.rate:,.2f}")
print()
print("But 'company_rate' is the VEB/USD rate we expect:")
print(f"  company_rate = {rate_record.company_rate:.4f}")
print(f"  ${intereses_usd:.2f} × {rate_record.company_rate:.4f} = Bs. {manual_calc:,.2f}")
print()

print("Relationship:")
print(f"  company_rate = 1 / rate")
print(f"  {rate_record.company_rate:.4f} ≈ 1 / {rate_record.rate:.8f}")
print(f"  {1.0 / rate_record.rate:.4f} (verified)")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
