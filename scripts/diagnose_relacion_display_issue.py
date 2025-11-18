#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose Relación Report Display Issue

The report shows Bs. 20,209.12 for interest instead of expected Bs. 4,224.84.
Let's trace through the calculation.
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("DIAGNOSE: RELACIÓN REPORT SHOWING Bs. 20,209.12")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get payslip values
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

prestaciones_usd = get_line('LIQUID_PRESTACIONES_V2')
intereses_usd = get_line('LIQUID_INTERESES_V2')
service_months = get_line('LIQUID_SERVICE_MONTHS_V2')

print("KEY VALUES FROM PAYSLIP:")
print("-" * 80)
print(f"Prestaciones Sociales: ${prestaciones_usd:.2f} USD")
print(f"Intereses sobre Prestaciones: ${intereses_usd:.2f} USD")
print(f"Service Months: {service_months:.2f}")
print()

# Get exchange rate at end date
end_date = payslip.date_to
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', end_date)
], limit=1, order='name desc')
end_rate = rate_record.company_rate if rate_record and hasattr(rate_record, 'company_rate') else 0.0

print(f"Exchange Rate at {end_date}: {end_rate:.4f} VEB/USD")
print()

# Calculate what formula display shows
prestaciones_veb_simple = prestaciones_usd * end_rate
formula_result = prestaciones_veb_simple * 0.50 * 0.13 * (service_months / 12)

print("=" * 80)
print("FORMULA DISPLAY CALCULATION")
print("=" * 80)
print()
print("What the report SHOWS in formula:")
print(f"  Prestaciones VEB: Bs. {prestaciones_veb_simple:,.2f}")
print(f"  Formula: {prestaciones_veb_simple:,.2f} × 50% × 13% × ({service_months:.2f}/12)")
print(f"  Result: Bs. {formula_result:,.2f}")
print()

# Now test what _calculate_accrued_interest returns
print("=" * 80)
print("CALLING _calculate_accrued_interest() METHOD")
print("=" * 80)
print()

relacion_report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Simulate wizard data (VEB, no override)
data = {
    'wizard_id': 1,
    'currency_id': veb.id,
    'currency_name': 'VEB',
    'payslip_ids': [payslip.id],
    'use_custom_rate': False,
    'custom_exchange_rate': None,
    'rate_date': None,
}

# Call the method directly
accrued_interest = relacion_report_model._calculate_accrued_interest(payslip, veb, data)

print(f"_calculate_accrued_interest() returned: Bs. {accrued_interest:,.2f}")
print()

# Now generate full report
print("=" * 80)
print("FULL REPORT GENERATION")
print("=" * 80)
print()

result = relacion_report_model._get_report_values(docids=[payslip.id], data=data)
report_data = result['reports'][0]

# Find interest benefit
interest_benefit = [b for b in report_data['benefits'] if b['number'] == 6][0]

print("Interest Benefit Data:")
print(f"  Name: {interest_benefit['name']}")
print(f"  Formula: {interest_benefit['formula']}")
print(f"  Calculation: {interest_benefit['calculation']}")
print(f"  Amount: {interest_benefit['amount']:,.2f}")
print(f"  Amount Formatted: {interest_benefit['amount_formatted']}")
print()

print("=" * 80)
print("THE ISSUE")
print("=" * 80)
print()

if abs(interest_benefit['amount'] - accrued_interest) > 1:
    print("⚠️  PROBLEM FOUND!")
    print(f"  _calculate_accrued_interest() returns: Bs. {accrued_interest:,.2f}")
    print(f"  But benefit['amount'] shows: Bs. {interest_benefit['amount']:,.2f}")
    print()
    print("Possible causes:")
    print("  1. inter_amt variable not using _calculate_accrued_interest() result")
    print("  2. Variable reassignment happening after calculation")
    print("  3. Different code path for formula display vs amount")
    print()
else:
    print("✅ _calculate_accrued_interest() is being used correctly")
    print()
    print("The issue is in the DISPLAY FORMULA:")
    print(f"  prestaciones_display: Bs. {prestaciones_veb_simple:,.2f} (single rate conversion)")
    print("  This is only for display in the 'calculation' field")
    print("  The actual 'amount' field is correct: Bs. {interest_benefit['amount']:,.2f}")
    print()

# Check prestaciones_display calculation
print("=" * 80)
print("CHECKING prestaciones_display VARIABLE")
print("=" * 80)
print()

print("Looking at line 174 in liquidacion_breakdown_report.py:")
print("  prestaciones_display = self._convert_currency(prestaciones, usd, currency, date_ref, exchange_rate)")
print()
print("This converts prestaciones using SINGLE exchange rate:")
print(f"  ${prestaciones_usd:.2f} × {end_rate:.4f} = Bs. {prestaciones_usd * end_rate:,.2f}")
print()
print("But this is used in the FORMULA DISPLAY, not the actual calculation!")
print()

print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
print()
print("EXPECTED: Benefit amount should be Bs. 4,224.84 (accrual-based)")
print(f"ACTUAL:   Benefit amount is Bs. {interest_benefit['amount']:,.2f}")
print()

if abs(interest_benefit['amount'] - 4224.84) < 100:
    print("✅ Actual calculation is CORRECT (accrual-based)")
    print()
    print("The display formula is just showing REFERENCE values,")
    print("not the actual calculation method.")
else:
    print("❌ Actual calculation is WRONG")
    print()
    print("Need to investigate why _calculate_accrued_interest() isn't working")

print()
print("=" * 80)
print("Analysis complete!")
print("=" * 80)
