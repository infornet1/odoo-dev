#!/usr/bin/env python3
"""Test that formulas show VEB amounts when VEB currency selected"""

from datetime import date

print("="*80)
print("TEST VEB FORMULAS IN CALCULATION DETAILS")
print("="*80)

# Get models
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

# Get currencies
veb = Currency.search([('name', '=', 'VEB')], limit=1)
usd = env.ref('base.USD')

# Get report model
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

print("\n" + "="*80)
print("TEST 1: USD CURRENCY (Original)")
print("="*80)

data_usd = {
    'wizard_id': 1,
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

report_usd = report_model._generate_breakdown(payslip, usd, data_usd)

print("\nVacaciones (USD):")
print(f"  Calculation: {report_usd['benefits'][0]['calculation']}")
print(f"  Detail: {report_usd['benefits'][0]['detail']}")
print(f"  Amount: $ {report_usd['benefits'][0]['amount_formatted']}")

print("\nPrestaciones Sociales (USD):")
print(f"  Calculation: {report_usd['benefits'][3]['calculation']}")
print(f"  Detail: {report_usd['benefits'][3]['detail']}")
print(f"  Amount: $ {report_usd['benefits'][3]['amount_formatted']}")

if report_usd['deductions']:
    print("\nFAOV (USD):")
    print(f"  Calculation: {report_usd['deductions'][0]['calculation']}")
    print(f"  Amount: $ {report_usd['deductions'][0]['amount_formatted']}")

print("\n" + "="*80)
print("TEST 2: VEB CURRENCY with Nov 17 Rate (236.4601)")
print("="*80)

data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': date(2025, 11, 17),
}

report_veb = report_model._generate_breakdown(payslip, veb, data_veb)

print(f"\nExchange Rate: {report_veb['exchange_rate']:.4f} VEB/USD")

print("\nVacaciones (VEB):")
print(f"  Calculation: {report_veb['benefits'][0]['calculation']}")
print(f"  Detail: {report_veb['benefits'][0]['detail']}")
print(f"  Amount: Bs. {report_veb['benefits'][0]['amount_formatted']}")

print("\nPrestaciones Sociales (VEB):")
print(f"  Calculation: {report_veb['benefits'][3]['calculation']}")
print(f"  Detail: {report_veb['benefits'][3]['detail']}")
print(f"  Amount: Bs. {report_veb['benefits'][3]['amount_formatted']}")

if report_veb['deductions']:
    print("\nFAOV (VEB):")
    print(f"  Calculation: {report_veb['deductions'][0]['calculation']}")
    print(f"  Amount: Bs. {report_veb['deductions'][0]['amount_formatted']}")

print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

# Extract daily salary from calculation strings
usd_calc = report_usd['benefits'][0]['calculation']
veb_calc = report_veb['benefits'][0]['calculation']

print(f"\nUSD Calculation: {usd_calc}")
print(f"VEB Calculation: {veb_calc}")

# Check if VEB calculation contains Bs. symbol
if 'Bs.' in veb_calc:
    print("\n✅ VEB formulas correctly show Bs. amounts!")
else:
    print("\n❌ VEB formulas still show USD amounts!")

# Check if amounts are different
usd_amt = report_usd['benefits'][0]['amount']
veb_amt = report_veb['benefits'][0]['amount']
ratio = veb_amt / usd_amt if usd_amt > 0 else 0

print(f"\nAmount ratio (VEB/USD): {ratio:.4f}")
print(f"Expected ratio: ~236.46")

if abs(ratio - 236.4601) < 1.0:
    print("✅ Amounts correctly converted!")
else:
    print(f"❌ Ratio mismatch! Expected ~236.46, got {ratio:.4f}")

print("="*80)
