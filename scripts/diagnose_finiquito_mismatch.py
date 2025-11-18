#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose Finiquito Report Mismatch

Compare net amount in Finiquito vs Relación report.

Finiquito shows: Bs. 300,621.18
Need to find what Relación shows and why they differ.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("DIAGNOSE: FINIQUITO VS RELACIÓN NET AMOUNT MISMATCH")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report models
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Test with VEB, no override first
data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

print("=" * 80)
print("SCENARIO 1: VEB CURRENCY (NO OVERRIDE)")
print("=" * 80)
print()

# Generate Relación report
relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_veb)
relacion_report = relacion_result['reports'][0]

# Get all amounts from Relación
total_benefits = relacion_report['total_benefits']
total_deductions = relacion_report['total_deductions']
net_amount_relacion = relacion_report['net_amount']

print("RELACIÓN DE LIQUIDACIÓN REPORT:")
print("-" * 80)
print(f"Total Benefits:   Bs. {total_benefits:,.2f}")
print(f"Total Deductions: Bs. {total_deductions:,.2f}")
print(f"NET AMOUNT:       Bs. {net_amount_relacion:,.2f}")
print()

# Show breakdown
print("Benefits Breakdown:")
for benefit in relacion_report['benefits']:
    print(f"  {benefit['number']}. {benefit['name']:<35} Bs. {benefit['amount']:>12,.2f}")
print()

print("Deductions Breakdown:")
for deduction in relacion_report['deductions']:
    print(f"  {deduction['name']:<35} Bs. {deduction['amount']:>12,.2f}")
print()

# Generate Finiquito report
print("=" * 80)
print("FINIQUITO REPORT")
print("=" * 80)
print()

finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_veb)
finiquito_report = finiquito_result['reports'][0]

# Check what's in the finiquito report
print("Finiquito Report Data:")
print("-" * 80)
if 'total_benefits' in finiquito_report:
    print(f"Total Benefits:   Bs. {finiquito_report['total_benefits']:,.2f}")
if 'total_deductions' in finiquito_report:
    print(f"Total Deductions: Bs. {finiquito_report['total_deductions']:,.2f}")
if 'net_amount' in finiquito_report:
    print(f"NET AMOUNT:       Bs. {finiquito_report['net_amount']:,.2f}")
print()

# Check if finiquito has the raw amounts
if 'liquidacion_total' in finiquito_report:
    print(f"Liquidación Total: Bs. {finiquito_report['liquidacion_total']:,.2f}")
if 'net_to_receive' in finiquito_report:
    print(f"Net to Receive:    Bs. {finiquito_report['net_to_receive']:,.2f}")
if 'amount_formatted' in finiquito_report:
    print(f"Amount Formatted:  {finiquito_report['amount_formatted']}")
print()

# Compare
print("=" * 80)
print("COMPARISON")
print("=" * 80)
print()

# Try to find the net amount from finiquito
finiquito_net = None
if 'net_amount' in finiquito_report:
    finiquito_net = finiquito_report['net_amount']
elif 'net_to_receive' in finiquito_report:
    finiquito_net = finiquito_report['net_to_receive']
elif 'liquidacion_total' in finiquito_report:
    finiquito_net = finiquito_report['liquidacion_total']

if finiquito_net is not None:
    print(f"Relación Net:  Bs. {net_amount_relacion:,.2f}")
    print(f"Finiquito Net: Bs. {finiquito_net:,.2f}")
    print(f"Difference:    Bs. {abs(net_amount_relacion - finiquito_net):,.2f}")
    print()

    if abs(net_amount_relacion - finiquito_net) < 1:
        print("✅ MATCH!")
    else:
        print("❌ MISMATCH!")
        print()
        print("Investigating root cause...")
else:
    print("⚠️  Cannot find net amount in Finiquito report")
    print("Available fields:")
    for key in finiquito_report.keys():
        print(f"  - {key}")

print()

# Now test with Nov 17 override (user mentioned Bs. 300,621.18)
print("=" * 80)
print("SCENARIO 2: WITH EXCHANGE RATE OVERRIDE (Nov 17, 236.4601)")
print("=" * 80)
print()

data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

# Generate both reports with override
relacion_result_override = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
relacion_report_override = relacion_result_override['reports'][0]

finiquito_result_override = finiquito_model._get_report_values(docids=[payslip.id], data=data_with_override)
finiquito_report_override = finiquito_result_override['reports'][0]

print("RELACIÓN REPORT (with override):")
print("-" * 80)
print(f"Total Benefits:   Bs. {relacion_report_override['total_benefits']:,.2f}")
print(f"Total Deductions: Bs. {relacion_report_override['total_deductions']:,.2f}")
print(f"NET AMOUNT:       Bs. {relacion_report_override['net_amount']:,.2f}")
print()

print("FINIQUITO REPORT (with override):")
print("-" * 80)

# Try to extract net amount
finiquito_net_override = None
if 'net_amount' in finiquito_report_override:
    finiquito_net_override = finiquito_report_override['net_amount']
    print(f"NET AMOUNT:       Bs. {finiquito_net_override:,.2f}")
elif 'net_to_receive' in finiquito_report_override:
    finiquito_net_override = finiquito_report_override['net_to_receive']
    print(f"Net to Receive:   Bs. {finiquito_net_override:,.2f}")
elif 'liquidacion_total' in finiquito_report_override:
    finiquito_net_override = finiquito_report_override['liquidacion_total']
    print(f"Liquidación Total: Bs. {finiquito_net_override:,.2f}")
print()

# Check if Bs. 300,621.18 appears anywhere
if finiquito_net_override and abs(finiquito_net_override - 300621.18) < 1:
    print("✅ FOUND! Finiquito shows Bs. 300,621.18 with override")
    print()
    print(f"But Relación shows: Bs. {relacion_report_override['net_amount']:,.2f}")
    print(f"Difference:         Bs. {abs(relacion_report_override['net_amount'] - 300621.18):,.2f}")
elif abs(relacion_report_override['net_amount'] - 300621.18) < 1:
    print("✅ Relación shows Bs. 300,621.18")
    if finiquito_net_override:
        print(f"But Finiquito shows: Bs. {finiquito_net_override:,.2f}")
        print(f"Difference:          Bs. {abs(finiquito_net_override - 300621.18):,.2f}")

print()
print("=" * 80)
print("ROOT CAUSE INVESTIGATION")
print("=" * 80)
print()

# Let's check the finiquito model code to understand what it's calculating
print("Checking Finiquito report fields available:")
print("-" * 80)
for key, value in finiquito_report_override.items():
    if isinstance(value, (int, float)):
        print(f"  {key}: Bs. {value:,.2f}" if value > 100 else f"  {key}: {value}")
    elif isinstance(value, str) and len(value) < 100:
        print(f"  {key}: {value}")

print()
print("=" * 80)
print("Analysis complete!")
print("=" * 80)
