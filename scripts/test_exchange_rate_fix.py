#!/usr/bin/env python3
"""Test exchange rate override fix - SLIP/802"""

from datetime import date

print("="*80)
print("TEST EXCHANGE RATE OVERRIDE FIX")
print("="*80)

# Get models
Wizard = env['liquidacion.breakdown.wizard']
Payslip = env['hr.payslip']
Currency = env['res.currency']

# Find SLIP/802 (VIRGINIA VERDE)
payslip = Payslip.search([
    ('name', '=', 'Liquidación Venezolana V2 of VIRGINIA VERDE for 31jul-2025')
], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    exit(1)

print(f"Payslip: {payslip.name}")
print(f"Employee: {payslip.employee_id.name}")
print(f"Date To: {payslip.date_to}")

# Get VEB currency
veb = Currency.search([('name', '=', 'VEB')], limit=1)
usd = env.ref('base.USD')

print("\n" + "="*80)
print("TEST 1: DEFAULT BEHAVIOR (No override)")
print("="*80)

wizard1 = Wizard.create({
    'payslip_ids': [(6, 0, [payslip.id])],
    'currency_id': veb.id,
    'rate_date': False,
    'use_custom_rate': False,
})

print(f"Wizard: rate_date={wizard1.rate_date}, use_custom_rate={wizard1.use_custom_rate}")

# Get report data
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
data1 = {
    'wizard_id': wizard1.id,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

report_data1 = report_model._generate_breakdown(payslip, veb, data1)

print(f"\n✅ Exchange Rate: {report_data1['exchange_rate']:.4f} VEB/USD")
print(f"   Rate Source: {report_data1['rate_source']}")
print(f"   Net Amount (VEB): {report_data1['net_amount']:,.2f}")

# Get the default USD amount for comparison
report_data_usd = report_model._generate_breakdown(payslip, usd, None)
print(f"   Net Amount (USD): {report_data_usd['net_amount']:,.2f}")

print("\n" + "="*80)
print("TEST 2: CUSTOM DATE (Nov 17, 2025)")
print("="*80)

wizard2 = Wizard.create({
    'payslip_ids': [(6, 0, [payslip.id])],
    'currency_id': veb.id,
    'rate_date': '2025-11-17',
    'use_custom_rate': False,
})

print(f"Wizard: rate_date={wizard2.rate_date}, use_custom_rate={wizard2.use_custom_rate}")

data2 = {
    'wizard_id': wizard2.id,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': wizard2.rate_date,  # This is a date object from wizard
}

report_data2 = report_model._generate_breakdown(payslip, veb, data2)

print(f"\n✅ Exchange Rate: {report_data2['exchange_rate']:.4f} VEB/USD")
print(f"   Rate Source: {report_data2['rate_source']}")
print(f"   Net Amount (VEB): {report_data2['net_amount']:,.2f}")

# Expected rate for Nov 17
CurrencyRate = env['res.currency.rate']
expected_rate = CurrencyRate.search([
    ('currency_id', '=', veb.id),
    ('name', '<=', date(2025, 11, 17))
], limit=1, order='name desc')

if expected_rate:
    expected_rate_value = expected_rate.company_rate if hasattr(expected_rate, 'company_rate') else (1.0 / expected_rate.rate)
    print(f"   Expected Rate: {expected_rate_value:.4f} VEB/USD (from {expected_rate.name})")

    # Calculate expected VEB amount
    expected_veb = report_data_usd['net_amount'] * expected_rate_value
    print(f"   Expected VEB Amount: {expected_veb:,.2f}")

    # Verify
    if abs(report_data2['exchange_rate'] - expected_rate_value) < 0.0001:
        print("\n   ✅ RATE MATCH!")
    else:
        print(f"\n   ❌ RATE MISMATCH! Got {report_data2['exchange_rate']:.4f}, expected {expected_rate_value:.4f}")

    if abs(report_data2['net_amount'] - expected_veb) < 1.0:
        print("   ✅ AMOUNT MATCH!")
    else:
        print(f"   ❌ AMOUNT MISMATCH! Got {report_data2['net_amount']:,.2f}, expected {expected_veb:,.2f}")

print("\n" + "="*80)
print("TEST 3: CUSTOM RATE (300.0000)")
print("="*80)

wizard3 = Wizard.create({
    'payslip_ids': [(6, 0, [payslip.id])],
    'currency_id': veb.id,
    'use_custom_rate': True,
    'custom_exchange_rate': 300.0000,
})

print(f"Wizard: custom_exchange_rate={wizard3.custom_exchange_rate}, use_custom_rate={wizard3.use_custom_rate}")

data3 = {
    'wizard_id': wizard3.id,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 300.0000,
    'rate_date': None,
}

report_data3 = report_model._generate_breakdown(payslip, veb, data3)

print(f"\n✅ Exchange Rate: {report_data3['exchange_rate']:.4f} VEB/USD")
print(f"   Rate Source: {report_data3['rate_source']}")
print(f"   Net Amount (VEB): {report_data3['net_amount']:,.2f}")

expected_custom_veb = report_data_usd['net_amount'] * 300.0
print(f"   Expected VEB Amount: {expected_custom_veb:,.2f}")

if abs(report_data3['exchange_rate'] - 300.0) < 0.0001:
    print("\n   ✅ RATE MATCH!")
else:
    print(f"\n   ❌ RATE MISMATCH! Got {report_data3['exchange_rate']:.4f}, expected 300.0000")

if abs(report_data3['net_amount'] - expected_custom_veb) < 1.0:
    print("   ✅ AMOUNT MATCH!")
else:
    print(f"   ❌ AMOUNT MISMATCH! Got {report_data3['net_amount']:,.2f}, expected {expected_custom_veb:,.2f}")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Default (Jul 31):  {report_data1['exchange_rate']:>10.4f} VEB/USD → {report_data1['net_amount']:>15,.2f} VEB")
print(f"Custom Date (Nov 17): {report_data2['exchange_rate']:>10.4f} VEB/USD → {report_data2['net_amount']:>15,.2f} VEB")
print(f"Custom Rate (300):    {report_data3['exchange_rate']:>10.4f} VEB/USD → {report_data3['net_amount']:>15,.2f} VEB")
print(f"Original (USD):                        → {report_data_usd['net_amount']:>15,.2f} USD")
print("="*80)
