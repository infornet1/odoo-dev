#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze SLIP/802 Interest Calculation Discrepancy

This script compares how the two reports calculate "Intereses sobre Prestaciones"
for Virginia Verde's liquidation payslip (SLIP/802).
"""

import sys

# Find payslip SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if not payslip:
    print("ERROR: SLIP/802 not found")
    sys.exit(1)

print("=" * 80)
print("SLIP/802 - VIRGINIA VERDE - Interest Analysis")
print("=" * 80)
print(f"Employee: {payslip.employee_id.name}")
print(f"Payslip: {payslip.number}")
print(f"Date: {payslip.date_from} to {payslip.date_to}")
print(f"Structure: {payslip.struct_id.name} ({payslip.struct_id.code})")
print()

# Get key values from payslip
def get_line(code):
    line = payslip.line_ids.filtered(lambda l: l.code == code)
    return line.total if line else 0.0

# Get V2 values (since SLIP/802 uses V2 structure)
service_months = get_line('LIQUID_SERVICE_MONTHS_V2')
daily_salary = get_line('LIQUID_DAILY_SALARY_V2')
integral_daily = get_line('LIQUID_INTEGRAL_DAILY_V2')
prestaciones = get_line('LIQUID_PRESTACIONES_V2')
intereses = get_line('LIQUID_INTERESES_V2')

print("KEY VALUES FROM PAYSLIP (USD):")
print("-" * 80)
print(f"Service Months: {service_months:.2f}")
print(f"Daily Salary (base for deductions): ${daily_salary:.2f}")
print(f"Integral Daily Salary: ${integral_daily:.2f}")
print(f"Prestaciones Sociales Total: ${prestaciones:.2f}")
print(f"Intereses sobre Prestaciones: ${intereses:.2f}")
print()

# Get currency and exchange rates
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("ERROR: VEB currency not found in system")
    sys.exit(1)

# Get automatic rate for payslip date_to
automatic_rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', payslip.date_to)
], limit=1, order='name desc')

automatic_rate = automatic_rate_record.company_rate if automatic_rate_record and hasattr(automatic_rate_record, 'company_rate') else 0.0
print(f"AUTOMATIC EXCHANGE RATE (for {payslip.date_to}):")
print(f"  Rate: {automatic_rate:.4f} VEB/USD")
print(f"  Date: {automatic_rate_record.name if automatic_rate_record else 'N/A'}")
print()

# Calculate interest in VEB using automatic rate
intereses_veb_auto = intereses * automatic_rate
print(f"INTERESES IN VEB (Automatic Rate):")
print(f"  ${intereses:.2f} × {automatic_rate:.4f} = Bs. {intereses_veb_auto:,.2f}")
print()

# Get Nov 17 rate (if user overrides)
from datetime import date
nov_17_date = date(2025, 11, 17)
nov_17_rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', nov_17_date)
], limit=1, order='name desc')
nov_17_rate = nov_17_rate_record.company_rate if nov_17_rate_record and hasattr(nov_17_rate_record, 'company_rate') else 0.0

intereses_veb_nov17 = intereses * nov_17_rate
print(f"INTERESES IN VEB (Nov 17 Override Rate):")
print(f"  Rate: {nov_17_rate:.4f} VEB/USD")
print(f"  ${intereses:.2f} × {nov_17_rate:.4f} = Bs. {intereses_veb_nov17:,.2f}")
print()

print("=" * 80)
print("RELACIÓN REPORT CALCULATION (Line 225-233)")
print("=" * 80)
print("Formula: 13% anual sobre saldo promedio de prestaciones")
print(f"Calculation: Prestaciones × 50% × 13% × (months/12)")
print(f"           = ${prestaciones:.2f} × 0.50 × 0.13 × ({service_months:.2f}/12)")
print(f"           = ${intereses:.2f} USD")
print()
print("When VEB selected with Nov 17 override:")
print(f"  Bs. {intereses_veb_nov17:,.2f}")
print()

print("=" * 80)
print("PRESTACIONES INTEREST REPORT CALCULATION")
print("=" * 80)
print("Current Logic (prestaciones_interest_report.py:110-174):")
print("  1. Distributes total interest across ALL months proportionally")
print(f"  2. Interest per month = ${intereses:.2f} / {service_months:.2f} = ${intereses/service_months:.4f}")
print("  3. For EACH month, converts that month's interest using THAT month's rate")
print("  4. Accumulates converted amounts across all months")
print()
print("Example for first 3 months:")

# Simulate first 3 months
contract = payslip.contract_id
start_date = contract.date_start
current_date = start_date
interest_per_month = intereses / service_months
accumulated_veb = 0.0

for month_num in range(1, 4):
    # Get rate for this month
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', current_date)
    ], limit=1, order='name desc')

    if not rate_record:
        rate_record = env['res.currency.rate'].search([
            ('currency_id', '=', veb.id)
        ], limit=1, order='name asc')

    month_rate = rate_record.company_rate if rate_record and hasattr(rate_record, 'company_rate') else 0.0
    month_interest_veb = interest_per_month * month_rate
    accumulated_veb += month_interest_veb

    print(f"  Month {month_num} ({current_date.strftime('%b-%y')}): ${interest_per_month:.4f} × {month_rate:.4f} = Bs. {month_interest_veb:.4f}")

    from dateutil.relativedelta import relativedelta
    current_date = current_date + relativedelta(months=1)

print(f"  ... (continues for all {service_months:.0f} months)")
print()

print("=" * 80)
print("THE ISSUE")
print("=" * 80)
print("⚠️  RELACIÓN REPORT:")
print(f"    - Converts TOTAL interest once: ${intereses:.2f} × {nov_17_rate:.4f} = Bs. {intereses_veb_nov17:,.2f}")
print("    - Uses SINGLE rate (from wizard override or payslip date)")
print()
print("⚠️  PRESTACIONES INTEREST REPORT:")
print("    - Converts interest MONTH-BY-MONTH using historical rates")
print("    - Each month uses ITS OWN historical rate from the past")
print("    - NO override capability currently")
print()
print("📊 RESULT:")
print("    - The two reports will show DIFFERENT VEB amounts")
print("    - Employee sees inconsistency between reports")
print("    - This violates the requirement: 'zero inconsistency calcs'")
print()

print("=" * 80)
print("RECOMMENDED SOLUTION")
print("=" * 80)
print("✅ Add same exchange rate override to Prestaciones Interest Report:")
print("    1. Add 'use_custom_rate' field to wizard")
print("    2. Add 'custom_exchange_rate' field to wizard")
print("    3. Add 'rate_date' field to wizard")
print("    4. Pass these to report model via data dict")
print("    5. Use SINGLE rate for ALL month conversions (matching Relación logic)")
print()
print("📝 This ensures:")
print("    - Both reports use SAME exchange rate")
print("    - Both reports show SAME VEB amounts")
print("    - Zero inconsistency for employee")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
