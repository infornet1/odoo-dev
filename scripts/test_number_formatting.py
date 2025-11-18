#!/usr/bin/env python3
"""Test number formatting with thousand separators"""

from datetime import date

print("="*80)
print("TEST NUMBER FORMATTING - Thousand Separators")
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

# Get VEB currency
veb = Currency.search([('name', '=', 'VEB')], limit=1)

print("\n" + "="*80)
print("TEST WITH VEB CURRENCY AND NOV 17 RATE")
print("="*80)

# Get report data
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
data = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': date(2025, 11, 17),
}

report_data = report_model._generate_breakdown(payslip, veb, data)

print(f"\nExchange Rate: {report_data['exchange_rate']:.4f} VEB/USD")
print(f"Rate Source: {report_data['rate_source']}")

print("\n" + "-"*80)
print("BENEFITS (showing formatting)")
print("-"*80)

for benefit in report_data['benefits']:
    # Test Python formatting
    formatted_amount = '{:,.2f}'.format(benefit['amount'])
    print(f"{benefit['number']}. {benefit['name']:30s} {veb.symbol} {formatted_amount:>15s}")

print("-"*80)
print(f"{'TOTAL BENEFITS':>32s} {veb.symbol} {'{:,.2f}'.format(report_data['total_benefits']):>15s}")

print("\n" + "-"*80)
print("DEDUCTIONS (showing formatting)")
print("-"*80)

if report_data['deductions']:
    for deduction in report_data['deductions']:
        formatted_amount = '{:,.2f}'.format(deduction['amount'])
        print(f"{deduction['number']}. {deduction['name']:30s} {veb.symbol} {formatted_amount:>15s}")

    print("-"*80)
    print(f"{'TOTAL DEDUCTIONS':>32s} {veb.symbol} {'{:,.2f}'.format(report_data['total_deductions']):>15s}")
else:
    print("No deductions")

print("\n" + "="*80)
print("NET AMOUNT")
print("="*80)
print(f"{'NETO A RECLAMAR':>32s} {veb.symbol} {'{:,.2f}'.format(report_data['net_amount']):>15s}")

print("\n" + "="*80)
print("FORMATTING VERIFICATION")
print("="*80)

# Verify formatting works correctly
test_values = [
    1200.93,      # Original USD value
    33560.78,     # Example from user
    149528.03,    # Jul 31 VEB
    283972.03,    # Nov 17 VEB
    1234567.89,   # Large number test
]

print("\nNumber formatting test:")
for val in test_values:
    formatted = '{:,.2f}'.format(val)
    print(f"  {val:>12.2f} → {formatted:>15s}")

print("\n✅ All numbers should display with thousand separators (commas)")
print("="*80)
