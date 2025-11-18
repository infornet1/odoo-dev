#!/usr/bin/env python3
"""
Check Exchange Rate for SLIP/802 VIRGINIA VERDE
Purpose: Identify what exchange rate the Relación de Liquidación report uses
"""

from datetime import datetime

print("="*80)
print("CHECK EXCHANGE RATE - SLIP/802 VIRGINIA VERDE")
print("="*80)

# Find SLIP/802
Payslip = env['hr.payslip']
payslip = Payslip.search([('name', '=', 'SLIP/802')], limit=1)

if not payslip:
    # Try to find by employee name and recent date
    Employee = env['hr.employee']
    virginia = Employee.search([('name', 'ilike', 'VIRGINIA VERDE')], limit=1)
    if virginia:
        payslip = Payslip.search([
            ('employee_id', '=', virginia.id)
        ], limit=1, order='id desc')

if not payslip:
    print("❌ SLIP/802 not found!")
    exit(1)

print(f"\nPayslip: {payslip.name}")
print(f"Employee: {payslip.employee_id.name}")
print(f"Period: {payslip.date_from} to {payslip.date_to}")
print(f"Structure: {payslip.struct_id.name}")
print(f"State: {payslip.state}")

# Get the reference date (date_to)
date_ref = payslip.date_to
print(f"\nReference Date (date_to): {date_ref}")

# Get VEB currency
CurrencyRate = env['res.currency.rate']
Currency = env['res.currency']

veb_currency = Currency.search([('name', '=', 'VEB')], limit=1)
if not veb_currency:
    print("❌ VEB currency not found!")
    exit(1)

print(f"\nVEB Currency ID: {veb_currency.id}")

# Find the exchange rate using the SAME logic as the report
# Line 283-296 in liquidacion_breakdown_report.py
print("\n" + "="*80)
print("EXCHANGE RATE LOOKUP (Report Logic)")
print("="*80)

# Search for rate <= date_ref, ordered by date descending (most recent first)
rate_record = CurrencyRate.search([
    ('currency_id', '=', veb_currency.id),
    ('name', '<=', date_ref)
], limit=1, order='name desc')

if rate_record:
    print(f"\n✅ Found rate record:")
    print(f"   ID: {rate_record.id}")
    print(f"   Date: {rate_record.name}")
    print(f"   Rate (inverse): {rate_record.rate}")

    # Check for company_rate
    if hasattr(rate_record, 'company_rate'):
        print(f"   Company Rate: {rate_record.company_rate}")
        exchange_rate = rate_record.company_rate
        print(f"\n   📊 EXCHANGE RATE USED: {exchange_rate:.4f} VEB/USD")
    elif rate_record.rate > 0:
        exchange_rate = 1.0 / rate_record.rate
        print(f"\n   📊 EXCHANGE RATE USED (calculated): {exchange_rate:.4f} VEB/USD")
    else:
        exchange_rate = 1.0
        print(f"\n   ⚠️  Invalid rate, using default: 1.0")
else:
    print("\n❌ No rate found for date <= {date_ref}")

    # Fallback: search for earliest rate
    rate_record = CurrencyRate.search([
        ('currency_id', '=', veb_currency.id)
    ], limit=1, order='name asc')

    if rate_record:
        print(f"\n   Using EARLIEST rate as fallback:")
        print(f"   Date: {rate_record.name}")
        if hasattr(rate_record, 'company_rate'):
            exchange_rate = rate_record.company_rate
            print(f"   📊 EXCHANGE RATE USED: {exchange_rate:.4f} VEB/USD")
        elif rate_record.rate > 0:
            exchange_rate = 1.0 / rate_record.rate
            print(f"   📊 EXCHANGE RATE USED (calculated): {exchange_rate:.4f} VEB/USD")
    else:
        exchange_rate = 1.0
        print(f"   ⚠️  No VEB rates found, using default: 1.0")

# Show recent VEB rates for context
print("\n" + "="*80)
print("RECENT VEB RATES (Last 5)")
print("="*80)

recent_rates = CurrencyRate.search([
    ('currency_id', '=', veb_currency.id)
], limit=5, order='name desc')

for r in recent_rates:
    if hasattr(r, 'company_rate'):
        display_rate = r.company_rate
    elif r.rate > 0:
        display_rate = 1.0 / r.rate
    else:
        display_rate = 0.0

    print(f"   {r.name}: {display_rate:.4f} VEB/USD")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Payslip: {payslip.name}")
print(f"Date To: {date_ref}")
print(f"Exchange Rate Used: {exchange_rate:.4f} VEB/USD")
print("="*80)
