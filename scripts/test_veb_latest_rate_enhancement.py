#!/usr/bin/env python3
"""
Test VEB latest rate enhancement for Relación de Liquidación report.

Usage: docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http < scripts/test_veb_latest_rate_enhancement.py
"""

# Get SLIP/854
slip = env['hr.payslip'].search([('number', '=', 'SLIP/854')], limit=1)
if not slip:
    print("❌ SLIP/854 not found")
    exit()

print(f"=== TESTING VEB LATEST RATE ENHANCEMENT ===\n")
print(f"Payslip: {slip.number}")
print(f"Date To: {slip.date_to}")

# Get VEB currency
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
if not veb:
    print("❌ VEB currency not found")
    exit()

# Get automatic rate for payslip date (old behavior)
rate_record_payslip = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', slip.date_to)
], limit=1, order='name desc')

payslip_date_rate = rate_record_payslip.company_rate if rate_record_payslip else 0.0
print(f"\n📊 Rate at payslip date ({slip.date_to}): {payslip_date_rate:.4f}")
print(f"   Rate record date: {rate_record_payslip.name if rate_record_payslip else 'N/A'}")

# Get latest available rate (new behavior)
rate_record_latest = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id)
], limit=1, order='name desc')

latest_rate = rate_record_latest.company_rate if rate_record_latest else 0.0
print(f"\n📈 Latest available rate: {latest_rate:.4f}")
print(f"   Rate record date: {rate_record_latest.name if rate_record_latest else 'N/A'}")

if latest_rate > payslip_date_rate:
    diff_pct = ((latest_rate - payslip_date_rate) / payslip_date_rate) * 100
    print(f"   📊 Difference: +{diff_pct:.2f}%")

# Test the report model
report = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print(f"\n=== TEST 1: AUTO (LATEST RATE - NEW BEHAVIOR) ===")
data1 = {
    'currency_id': veb.id,
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None
}
result1 = report._get_report_values([slip.id], data=data1)
r1 = result1['reports'][0]  # Access reports list, not docs
print(f"exchange_rate: {r1['exchange_rate']}")
print(f"rate_source: {r1['rate_source']}")
print(f"Expected: {latest_rate:.4f} and 'Tasa del {rate_record_latest.name.strftime('%d/%m/%Y')}'")

print(f"\n=== TEST 2: CUSTOM RATE 300.0 ===")
data2 = {
    'currency_id': veb.id,
    'use_custom_rate': True,
    'custom_exchange_rate': 300.0,
    'rate_date': None
}
result2 = report._get_report_values([slip.id], data=data2)
r2 = result2['reports'][0]
print(f"exchange_rate: {r2['exchange_rate']}")
print(f"rate_source: {r2['rate_source']}")
print(f"Expected: 300.0000 and 'Tasa del {slip.date_to.strftime('%d/%m/%Y')}'")

print(f"\n=== TEST 3: RATE DATE 2025-11-17 ===")
from datetime import date
rate_date_test = date(2025, 11, 17)
data3 = {
    'currency_id': veb.id,
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': rate_date_test
}
result3 = report._get_report_values([slip.id], data=data3)
r3 = result3['reports'][0]
print(f"exchange_rate: {r3['exchange_rate']}")
print(f"rate_source: {r3['rate_source']}")

# Get expected rate for Nov 17
rate_record_nov17 = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', rate_date_test)
], limit=1, order='name desc')
expected_nov17 = rate_record_nov17.company_rate if rate_record_nov17 else 0.0
print(f"Expected: {expected_nov17:.4f} and 'Tasa del {rate_record_nov17.name.strftime('%d/%m/%Y')}'")

print(f"\n=== VALIDATION ===")
test1_pass = abs(r1['exchange_rate'] - latest_rate) < 0.01 and rate_record_latest.name.strftime('%d/%m/%Y') in r1['rate_source']
test2_pass = abs(r2['exchange_rate'] - 300.0) < 0.01 and slip.date_to.strftime('%d/%m/%Y') in r2['rate_source']
test3_pass = abs(r3['exchange_rate'] - expected_nov17) < 0.01 and rate_record_nov17.name.strftime('%d/%m/%Y') in r3['rate_source']

print(f"Test 1 (Auto - Latest): {'✅ PASS' if test1_pass else '❌ FAIL'}")
print(f"Test 2 (Custom Rate): {'✅ PASS' if test2_pass else '❌ FAIL'}")
print(f"Test 3 (Rate Date): {'✅ PASS' if test3_pass else '❌ FAIL'}")

if test1_pass and test2_pass and test3_pass:
    print(f"\n🎉 ALL TESTS PASSED!")
else:
    print(f"\n⚠️ SOME TESTS FAILED - Review output above")

print(f"\n=== TEST COMPLETE ===")
