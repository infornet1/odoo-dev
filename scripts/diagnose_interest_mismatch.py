#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose Interest Mismatch Between Reports

Prestaciones Report: Bs. 4,160.85
Liquidación Report: Bs. 4,224.84
Difference: Bs. 63.99

Let's find out why!
"""

import sys
from dateutil.relativedelta import relativedelta

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("DIAGNOSE: INTEREST AMOUNT MISMATCH")
print("=" * 80)
print(f"Payslip: {payslip.number} - {payslip.employee_id.name}")
print()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get report models
prest_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
relacion_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Test data (VEB, no override)
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
print("GENERATE BOTH REPORTS (VEB, NO OVERRIDE)")
print("=" * 80)
print()

# Generate Prestaciones report
prest_result = prest_model._get_report_values(docids=[payslip.id], data=data_veb)
prest_report = prest_result['reports'][0]
prest_interest = prest_report['totals']['total_interest']

# Generate Relación report
relacion_result = relacion_model._get_report_values(docids=[payslip.id], data=data_veb)
relacion_report = relacion_result['reports'][0]
relacion_interest = [b for b in relacion_report['benefits'] if b['number'] == 6][0]['amount']

print(f"Prestaciones Report Interest: Bs. {prest_interest:,.2f}")
print(f"Relación Report Interest:     Bs. {relacion_interest:,.2f}")
print(f"Difference:                    Bs. {abs(prest_interest - relacion_interest):,.2f}")
print()

# Get payslip data
contract = payslip.contract_id
start_date = contract.date_start
end_date = payslip.date_to

def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

service_months = get_line('LIQUID_SERVICE_MONTHS_V2') or get_line('LIQUID_SERVICE_MONTHS')
intereses_usd = get_line('LIQUID_INTERESES_V2') or get_line('LIQUID_INTERESES')
interest_per_month = intereses_usd / service_months

print("=" * 80)
print("PAYSLIP DATA")
print("=" * 80)
print(f"Service Period: {start_date} to {end_date}")
print(f"Service Months: {service_months:.2f}")
print(f"Total Interest (USD): ${intereses_usd:.2f}")
print(f"Interest per Month: ${interest_per_month:.2f}")
print()

print("=" * 80)
print("ANALYZE: PRESTACIONES REPORT CALCULATION")
print("=" * 80)
print()

# Check Prestaciones report logic
print("Checking monthly breakdown from Prestaciones report:")
print("-" * 80)

accumulated_veb_prest = 0.0
current_date = start_date
month_count = 0

print(f"{'Month':<15} {'Date':<12} {'USD Int':<10} {'Rate':<10} {'VEB Int':<12} {'Accum VEB':<12}")
print("-" * 80)

while current_date <= end_date:
    # Get exchange rate for current month
    rate_rec = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_rec:
        rate_rec = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_rec.company_rate if rate_rec and hasattr(rate_rec, 'company_rate') else 0.0
    month_interest_veb = interest_per_month * month_rate
    accumulated_veb_prest += month_interest_veb

    month_count += 1
    print(f"{current_date.strftime('%b %Y'):<15} {current_date.strftime('%Y-%m-%d'):<12} "
          f"${interest_per_month:<9.2f} {month_rate:<10.4f} "
          f"Bs.{month_interest_veb:<10.2f} Bs.{accumulated_veb_prest:<10.2f}")

    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

print("-" * 80)
print(f"Prestaciones Method Total: Bs. {accumulated_veb_prest:,.2f}")
print(f"Months processed: {month_count}")
print()

print("=" * 80)
print("ANALYZE: RELACIÓN REPORT CALCULATION")
print("=" * 80)
print()

# Check Relación report logic
print("Checking _calculate_accrued_interest() method:")
print("-" * 80)

accumulated_veb_relacion = 0.0
current_date = start_date
month_count_rel = 0

print(f"{'Month':<15} {'Date':<12} {'USD Int':<10} {'Rate':<10} {'VEB Int':<12} {'Accum VEB':<12}")
print("-" * 80)

while current_date <= end_date:
    # Get exchange rate for current month (NO override)
    rate_rec = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_rec:
        rate_rec = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_rec.company_rate if rate_rec and hasattr(rate_rec, 'company_rate') else 0.0
    month_interest_veb = interest_per_month * month_rate
    accumulated_veb_relacion += month_interest_veb

    month_count_rel += 1
    print(f"{current_date.strftime('%b %Y'):<15} {current_date.strftime('%Y-%m-%d'):<12} "
          f"${interest_per_month:<9.2f} {month_rate:<10.4f} "
          f"Bs.{month_interest_veb:<10.2f} Bs.{accumulated_veb_relacion:<10.2f}")

    current_date = current_date + relativedelta(months=1)
    if current_date > end_date:
        break

print("-" * 80)
print(f"Relación Method Total: Bs. {accumulated_veb_relacion:,.2f}")
print(f"Months processed: {month_count_rel}")
print()

print("=" * 80)
print("COMPARISON")
print("=" * 80)
print()

print(f"Prestaciones Report Shows: Bs. {prest_interest:,.2f}")
print(f"Prestaciones Manual Calc:  Bs. {accumulated_veb_prest:,.2f}")
print(f"Match: {abs(prest_interest - accumulated_veb_prest) < 1}")
print()

print(f"Relación Report Shows:     Bs. {relacion_interest:,.2f}")
print(f"Relación Manual Calc:      Bs. {accumulated_veb_relacion:,.2f}")
print(f"Match: {abs(relacion_interest - accumulated_veb_relacion) < 1}")
print()

print(f"Manual Calcs Match Each Other: {abs(accumulated_veb_prest - accumulated_veb_relacion) < 1}")
print()

if abs(accumulated_veb_prest - accumulated_veb_relacion) < 1:
    print("✅ Both methods calculate the SAME way")
    print()
    print("🔍 ROOT CAUSE: Reports show different amounts but logic is identical!")
    print("   The issue is in how the totals are being calculated or displayed.")
    print()
    print("   Checking for potential issues:")
    print("   1. Rounding differences in intermediate calculations")
    print("   2. Different number of months being processed")
    print("   3. Different date ranges being used")
    print("   4. Totals calculation method differences")
else:
    print("⚠️  Methods calculate DIFFERENTLY!")
    print(f"   Difference: Bs. {abs(accumulated_veb_prest - accumulated_veb_relacion):,.2f}")

print()

# Check the actual months being processed
print("=" * 80)
print("DETAILED INVESTIGATION")
print("=" * 80)
print()

# Re-run Prestaciones to see exact breakdown
if hasattr(prest_report, 'monthly_breakdown') and prest_report['monthly_breakdown']:
    print("Prestaciones Report Monthly Breakdown:")
    print("-" * 80)
    total_check = 0.0
    for month_data in prest_report['monthly_breakdown']:
        print(f"{month_data.get('month', 'N/A')}: Bs. {month_data.get('interest_converted', 0):.2f}")
        total_check += month_data.get('interest_converted', 0)
    print(f"Sum of monthly breakdown: Bs. {total_check:.2f}")
    print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
