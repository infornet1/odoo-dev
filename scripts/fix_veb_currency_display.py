#!/usr/bin/env python3
"""
Fix Prestaciones Interest Report to properly display VEB currency.

Issues to fix:
1. Exchange rate lookup returning 1.0 for VEB
2. Values not being converted to VEB
3. Template hardcoding "$" symbol

Solution:
- Use Odoo's built-in _convert() method for currency conversion
- Return actual exchange rate for display in "Tasa del Mes" column
- Pass currency symbol to template for dynamic display
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("FIXING VEB CURRENCY DISPLAY IN PRESTACIONES INTEREST REPORT")
print("=" * 80)

# Get the report model
report_model = env['ir.model'].search([
    ('model', '=', 'report.ueipab_payroll_enhancements.prestaciones_interest')
], limit=1)

if not report_model:
    print("\n❌ Report model not found!")
    sys.exit(1)

print(f"\n✅ Found report model: {report_model.name}")

# The fix needs to be applied to the Python code file directly
# We'll update the _get_exchange_rate and _generate_monthly_breakdown methods

print("\n" + "=" * 80)
print("FIX REQUIREMENTS:")
print("=" * 80)

print("""
The following changes need to be made to:
/opt/odoo-dev/addons/ueipab_payroll_enhancements/models/prestaciones_interest_report.py

1. Update _get_exchange_rate() method:
   - Use Odoo's currency conversion to get actual rate
   - Return company_rate field value for display

2. Update _generate_monthly_breakdown() method:
   - Convert all monetary values to selected currency
   - Add currency symbol to monthly_data

3. Update _get_report_values() method:
   - Pass currency symbol to template context

These changes will allow the report to:
- Display values in VEB when selected
- Show correct exchange rates in "Tasa del Mes" column
- Use correct currency symbol (Bs. for VEB, $ for USD)
""")

# Test current behavior
print("\n" + "=" * 80)
print("TESTING CURRENT CONVERSION")
print("=" * 80)

usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("❌ VEB currency not found in system")
    sys.exit(1)

print(f"\nCurrencies:")
print(f"  USD: {usd.name} (Symbol: {usd.symbol})")
print(f"  VEB: {veb.name} (Symbol: {veb.symbol})")

# Test conversion
from datetime import date
test_amount = 672.27  # Prestaciones from SLIP/568
test_date = date(2025, 11, 14)

converted = usd._convert(
    from_amount=test_amount,
    to_currency=veb,
    company=env.company,
    date=test_date
)

print(f"\nConversion Test:")
print(f"  ${test_amount:.2f} USD → {converted:,.2f} {veb.symbol}")

# Get the rate for display
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', test_date)
], limit=1, order='name desc')

if rate_record:
    display_rate = rate_record.company_rate
    print(f"  Exchange Rate: {display_rate:.2f} VEB/USD")
    print(f"  Rate Date: {rate_record.name}")

print("\n✅ Currency conversion logic verified - ready to apply fix")
