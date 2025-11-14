#!/usr/bin/env python3
"""
Test Prestaciones Interest Report with VEB currency.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("TESTING PRESTACIONES INTEREST REPORT WITH VEB CURRENCY")
print("=" * 80)

# Upgrade module to apply changes
print("\n📦 Upgrading module...")
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)
if module:
    print(f"   Current version: {module.latest_version}")
    print(f"   State: {module.state}")

    if module.state == 'installed':
        print("   Upgrading module...")
        module.button_immediate_upgrade()
        print("   ✅ Module upgraded")
    else:
        print(f"   ⚠️  Module state is {module.state}, not upgrading")

# Get test data
print("\n📋 Getting test data...")
slip568 = env['hr.payslip'].search([('number', '=', 'SLIP/568')], limit=1)
if not slip568:
    print("❌ SLIP/568 not found")
    sys.exit(1)

print(f"   Payslip: {slip568.number} - {slip568.employee_id.name}")

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

print(f"   USD Symbol: {usd.symbol}")
print(f"   VEB Symbol: {veb.symbol}")

# Get report model
report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

# Test 1: Generate report in USD
print("\n" + "=" * 80)
print("TEST 1: REPORT IN USD")
print("=" * 80)

data_usd = {
    'currency_id': usd.id,
    'payslip_ids': [slip568.id],
}

report_values_usd = report_model._get_report_values(docids=[slip568.id], data=data_usd)

print(f"\n✅ Report generated with {len(report_values_usd['reports'])} report(s)")
report_usd = report_values_usd['reports'][0]
print(f"   Currency: {report_usd['currency'].name} ({report_usd['currency'].symbol})")
print(f"   Monthly rows: {len(report_usd['monthly_data'])}")

# Check first month values
first_month_usd = report_usd['monthly_data'][0]
print(f"\n   First month ({first_month_usd['month_name']}):")
print(f"      Monthly Income: {first_month_usd['monthly_income']:.2f}")
print(f"      Integral Salary: {first_month_usd['integral_salary']:.2f}")
print(f"      Exchange Rate: {first_month_usd['exchange_rate']:.2f}")

# Check totals
totals_usd = report_usd['totals']
print(f"\n   Totals:")
print(f"      Prestaciones: {totals_usd['total_prestaciones']:.2f}")
print(f"      Interest: {totals_usd['total_interest']:.2f}")

# Test 2: Generate report in VEB
print("\n" + "=" * 80)
print("TEST 2: REPORT IN VEB")
print("=" * 80)

data_veb = {
    'currency_id': veb.id,
    'payslip_ids': [slip568.id],
}

report_values_veb = report_model._get_report_values(docids=[slip568.id], data=data_veb)

print(f"\n✅ Report generated with {len(report_values_veb['reports'])} report(s)")
report_veb = report_values_veb['reports'][0]
print(f"   Currency: {report_veb['currency'].name} ({report_veb['currency'].symbol})")
print(f"   Monthly rows: {len(report_veb['monthly_data'])}")

# Check first month values
first_month_veb = report_veb['monthly_data'][0]
print(f"\n   First month ({first_month_veb['month_name']}):")
print(f"      Monthly Income: {first_month_veb['monthly_income']:,.2f}")
print(f"      Integral Salary: {first_month_veb['integral_salary']:,.2f}")
print(f"      Exchange Rate: {first_month_veb['exchange_rate']:.2f}")

# Check totals
totals_veb = report_veb['totals']
print(f"\n   Totals:")
print(f"      Prestaciones: {totals_veb['total_prestaciones']:,.2f}")
print(f"      Interest: {totals_veb['total_interest']:,.2f}")

# Verify conversion
print("\n" + "=" * 80)
print("VERIFICATION: USD vs VEB CONVERSION")
print("=" * 80)

print(f"\n   First Month Monthly Income:")
print(f"      USD: ${first_month_usd['monthly_income']:.2f}")
print(f"      VEB: {veb.symbol}{first_month_veb['monthly_income']:,.2f}")
print(f"      Exchange Rate: {first_month_veb['exchange_rate']:.2f} VEB/USD")

expected_veb = first_month_usd['monthly_income'] * first_month_veb['exchange_rate']
print(f"      Expected VEB: ${first_month_usd['monthly_income']:.2f} × {first_month_veb['exchange_rate']:.2f} = {veb.symbol}{expected_veb:,.2f}")

if abs(first_month_veb['monthly_income'] - expected_veb) < 1.0:
    print(f"      ✅ CONVERSION CORRECT!")
else:
    print(f"      ❌ CONVERSION MISMATCH: Got {first_month_veb['monthly_income']:,.2f}, expected {expected_veb:,.2f}")

print(f"\n   Totals Prestaciones:")
print(f"      USD: ${totals_usd['total_prestaciones']:.2f}")
print(f"      VEB: {veb.symbol}{totals_veb['total_prestaciones']:,.2f}")

print("\n✅ VEB currency conversion testing complete!")
