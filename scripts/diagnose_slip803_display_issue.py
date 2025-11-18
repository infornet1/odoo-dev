#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose SLIP/803 Display Issue

Check why Relación and Finiquito reports are not displaying amounts.
"""

import sys

# Find payslip SLIP/803
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/803')], limit=1)

if not payslip:
    print("ERROR: SLIP/803 not found")
    sys.exit(1)

print("=" * 80)
print("DIAGNOSE: SLIP/803 AMOUNT DISPLAY ISSUE")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print(f"State: {payslip.state}")
print(f"Date From: {payslip.date_from}")
print(f"Date To: {payslip.date_to}")
print()

# Check payslip lines
print("=" * 80)
print("PAYSLIP SALARY RULES")
print("=" * 80)
print()

# Get all lines
all_lines = payslip.line_ids.sorted(key=lambda l: l.sequence)

if not all_lines:
    print("⚠️  NO SALARY RULES FOUND!")
    print("Payslip may not be computed yet.")
else:
    print(f"Found {len(all_lines)} salary rules:")
    print()
    print(f"{'Code':<30} {'Name':<40} {'Total':>15}")
    print("-" * 85)
    for line in all_lines:
        print(f"{line.code:<30} {line.name:<40} ${line.total:>14.2f}")

print()

# Check for liquidation-specific codes
print("=" * 80)
print("LIQUIDATION CODES (V1 and V2)")
print("=" * 80)
print()

liquidation_codes = [
    'LIQUID_NET',
    'LIQUID_NET_V2',
    'LIQUID_VACACIONES',
    'LIQUID_VACACIONES_V2',
    'LIQUID_BONO_VACACIONAL',
    'LIQUID_BONO_VACACIONAL_V2',
    'LIQUID_UTILIDADES',
    'LIQUID_UTILIDADES_V2',
    'LIQUID_PRESTACIONES',
    'LIQUID_PRESTACIONES_V2',
    'LIQUID_ANTIGUEDAD',
    'LIQUID_ANTIGUEDAD_V2',
    'LIQUID_INTERESES',
    'LIQUID_INTERESES_V2',
]

found_liquidation = False
for code in liquidation_codes:
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    if line:
        found_liquidation = True
        print(f"✅ {code:<30} ${line[0].total:.2f}")
    else:
        print(f"❌ {code:<30} (not found)")

print()

if not found_liquidation:
    print("⚠️  NO LIQUIDATION CODES FOUND!")
    print("This may not be a liquidation payslip.")
    print()
    print("Check:")
    print("  1. Is this payslip using a liquidation structure?")
    print("  2. Has the payslip been computed?")
    print("  3. Are the salary rules correctly configured?")

print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Try to generate both reports
print("=" * 80)
print("ATTEMPT TO GENERATE REPORTS")
print("=" * 80)
print()

# Test data
data_veb = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

# Get report models
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
finiquito_model = env['report.ueipab_payroll_enhancements.finiquito_report']

print("Testing Relación de Liquidación report...")
print("-" * 80)
try:
    relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_veb)
    relacion_report = relacion_result['reports'][0]

    print(f"Total Benefits:   Bs. {relacion_report.get('total_benefits', 0):,.2f}")
    print(f"Total Deductions: Bs. {relacion_report.get('total_deductions', 0):,.2f}")
    print(f"Net Amount:       Bs. {relacion_report.get('net_amount', 0):,.2f}")
    print()

    if relacion_report.get('net_amount', 0) == 0:
        print("⚠️  NET AMOUNT IS ZERO!")
        print()
        print("Checking benefits breakdown:")
        benefits = relacion_report.get('benefits', [])
        if benefits:
            for benefit in benefits:
                print(f"  {benefit['number']}. {benefit['name']:<35} Bs. {benefit['amount']:,.2f}")
        else:
            print("  No benefits found in report")
        print()
        print("Checking deductions breakdown:")
        deductions = relacion_report.get('deductions', [])
        if deductions:
            for deduction in deductions:
                print(f"  {deduction['name']:<35} Bs. {deduction['amount']:,.2f}")
        else:
            print("  No deductions found in report")
    else:
        print("✅ Report generated successfully with amounts")

except Exception as e:
    print(f"❌ ERROR generating Relación report: {str(e)}")

print()

print("Testing Acuerdo Finiquito Laboral report...")
print("-" * 80)
try:
    finiquito_result = finiquito_model._get_report_values(docids=[payslip.id], data=data_veb)
    finiquito_report = finiquito_result['reports'][0]

    print(f"Net Amount: Bs. {finiquito_report.get('net_amount', 0):,.2f}")
    print()

    if finiquito_report.get('net_amount', 0) == 0:
        print("⚠️  NET AMOUNT IS ZERO!")
    else:
        print("✅ Report generated successfully with amount")

except Exception as e:
    print(f"❌ ERROR generating Finiquito report: {str(e)}")

print()

# Check contract
print("=" * 80)
print("CONTRACT INFORMATION")
print("=" * 80)
print()

contract = payslip.contract_id
if contract:
    print(f"Contract: {contract.name}")
    print(f"Employee: {contract.employee_id.name}")
    print(f"Date Start: {contract.date_start}")
    print(f"Salary Structure: {contract.structure_type_id.name if contract.structure_type_id else 'None'}")
    print()

    # Check for V2 fields
    if hasattr(contract, 'ueipab_salary_v2'):
        print(f"V2 Salary: ${contract.ueipab_salary_v2:.2f}")
    if hasattr(contract, 'ueipab_original_hire_date'):
        print(f"Original Hire Date: {contract.ueipab_original_hire_date}")
else:
    print("⚠️  NO CONTRACT FOUND!")

print()

print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

if not all_lines:
    print("ISSUE: Payslip has no computed salary rules")
    print("FIX: Compute the payslip first")
    print("  1. Go to payslip in Odoo")
    print("  2. Click 'Compute Sheet' button")
    print("  3. Verify salary rules appear")
    print("  4. Try generating reports again")
elif not found_liquidation:
    print("ISSUE: Payslip is not a liquidation payslip")
    print("FIX: Ensure correct salary structure")
    print("  1. Check payslip structure is LIQUID_VE or LIQUID_VE_V2")
    print("  2. Verify liquidation rules are active")
    print("  3. Recompute if needed")
else:
    print("Payslip appears to have liquidation rules.")
    print("Need to investigate why reports show zero amounts.")

print()
print("=" * 80)
print("Analysis complete!")
print("=" * 80)
