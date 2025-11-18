#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Formula Display Improvement (v1.21.0)

Verify the new interest formula display in Relación report.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("TEST: FORMULA DISPLAY IMPROVEMENT v1.21.0")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report model
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Test with VEB and Nov 17 override
from datetime import date
data_with_override = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': True,
    'custom_exchange_rate': 236.4601,
    'rate_date': None,
}

# Generate report
result = relacion_model._get_report_values(docids=[payslip.id], data=data_with_override)
report_data = result['reports'][0]

# Find interest benefit
interest_benefit = [b for b in report_data['benefits'] if b['number'] == 6][0]

print("INTEREST BENEFIT DISPLAY:")
print("-" * 80)
print(f"Number:      {interest_benefit['number']}")
print(f"Name:        {interest_benefit['name']}")
print(f"Formula:     {interest_benefit['formula']}")
print(f"Calculation: {interest_benefit['calculation']}")
print(f"Detail:      {interest_benefit['detail']}")
print(f"Amount:      Bs. {interest_benefit['amount']:,.2f}")
print()

# Verify new formula
expected_calc_start = "Acumulación mensual"
expected_detail = 'Ver reporte "Prestaciones Soc. Intereses"'

print("=" * 80)
print("VERIFICATION")
print("=" * 80)

calc_ok = interest_benefit['calculation'].startswith(expected_calc_start)
detail_ok = interest_benefit['detail'] == expected_detail

print(f"✅ Calculation starts with '{expected_calc_start}': {calc_ok}")
print(f"✅ Detail references Prestaciones report: {detail_ok}")

# Check no misleading numbers
no_misleading = 'Bs.' not in interest_benefit['calculation'] or 'Ver reporte' in interest_benefit['calculation']
print(f"✅ No misleading arithmetic formula: {no_misleading}")

print()

if calc_ok and detail_ok and no_misleading:
    print("🎉 SUCCESS! Formula display improvement working correctly!")
    print()
    print("Expected PDF display:")
    print("-" * 80)
    print("6  Intereses sobre Prestaciones")
    print("   13% anual sobre saldo promedio de prestaciones")
    print(f"   {interest_benefit['calculation']}")
    print()
    print(f"   {interest_benefit['detail']:<50} Bs. {interest_benefit['amount']:>12,.2f}")
    print()
else:
    print("⚠️  Issues detected - review implementation")

print()
print("=" * 80)
print("Test complete!")
print("=" * 80)
