#!/usr/bin/env python3
"""
Diagnose custom exchange rate display issue in Relación de Liquidación report.

Usage: docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http < scripts/diagnose_custom_rate_issue.py
"""

# Get SLIP/854
slip = env['hr.payslip'].search([('number', '=', 'SLIP/854')], limit=1)
if not slip:
    print("❌ SLIP/854 not found")
    exit()

print(f"=== DIAGNOSING CUSTOM RATE ISSUE ===\n")
print(f"Payslip: {slip.number}")
print(f"Date To: {slip.date_to}")

# Get VEB currency
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)

if not veb:
    print("❌ VEB currency not found")
    exit()

# Get automatic rate for payslip date
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', slip.date_to)
], limit=1, order='name desc')

auto_rate = rate_record.company_rate if rate_record else 0.0
print(f"\nAutomatic VEB rate for {slip.date_to}: {auto_rate:.4f}")
print(f"Rate record date: {rate_record.name if rate_record else 'N/A'}")

# Test the report model directly
report = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print(f"\n=== TEST 1: NO CUSTOM RATE ===")
data1 = {
    'currency': veb.name,
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None
}
result1 = report._get_report_values(slip.id, data=data1)
print(f"exchange_rate: {result1.get('exchange_rate')}")
print(f"rate_source: {result1.get('rate_source')}")

print(f"\n=== TEST 2: CUSTOM RATE 300.0 ===")
data2 = {
    'currency': veb.name,
    'use_custom_rate': True,
    'custom_exchange_rate': 300.0,
    'rate_date': None
}
result2 = report._get_report_values(slip.id, data=data2)
print(f"exchange_rate: {result2.get('exchange_rate')}")
print(f"rate_source: {result2.get('rate_source')}")

print(f"\n=== TEST 3: RATE DATE 2025-11-17 ===")
data3 = {
    'currency': veb.name,
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': '2025-11-17'
}
result3 = report._get_report_values(slip.id, data=data3)
print(f"exchange_rate: {result3.get('exchange_rate')}")
print(f"rate_source: {result3.get('rate_source')}")

# Check if there's an issue with data passing
print(f"\n=== CHECKING DATA PARAMETER HANDLING ===")
print(f"Test 2 input data:")
for key, value in data2.items():
    print(f"  {key}: {value} (type: {type(value).__name__})")

# Manually call _get_exchange_rate
print(f"\n=== MANUAL _GET_EXCHANGE_RATE CALL ===")
manual_rate = report._get_exchange_rate(slip.date_to, veb, custom_rate=300.0, custom_date=None)
print(f"Result with custom_rate=300.0: {manual_rate}")

print(f"\n=== DIAGNOSIS COMPLETE ===")
