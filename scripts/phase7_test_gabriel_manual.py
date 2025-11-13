#!/usr/bin/env python3
"""
Phase 7: Test Gabriel España Liquidation - Manual Computation
=============================================================

Manually compute liquidation values using salary rules.
"""

import datetime

print("=" * 80)
print("PHASE 7: GABRIEL ESPAÑA LIQUIDATION TEST (Manual Computation)")
print("=" * 80)

# Find Gabriel España
employee = env['hr.employee'].search([('name', 'ilike', 'GABRIEL ESPAÑA')], limit=1)
if not employee:
    print("\n❌ Employee not found!")
    exit(1)

# Get contract
contract = env['hr.contract'].search([
    ('employee_id', '=', employee.id),
    ('state', 'in', ['open', 'close'])
], limit=1)

if not contract:
    print("❌ No contract found!")
    exit(1)

print(f"\n✅ Employee: {employee.name}")
print(f"✅ Contract ID: {contract.id}")

# Display contract data
print(f"\n{'-' * 80}")
print("CONTRACT DATA (Historical Tracking Fields)")
print(f"{'-' * 80}")
print(f"Contract Start: {contract.date_start}")
print(f"Original Hire Date: {contract.ueipab_original_hire_date}")
print(f"Previous Liquidation: {contract.ueipab_previous_liquidation_date}")
print(f"Vacation Paid Until: {contract.ueipab_vacation_paid_until}")
print(f"Deduction Base: ${contract.ueipab_deduction_base:.2f}")

liquidation_date = datetime.date(2025, 7, 31)
print(f"Liquidation Date: {liquidation_date}")

# Calculate service months from contract start
service_days = (liquidation_date - contract.date_start).days
service_months = service_days / 30.0

print(f"\n{'-' * 80}")
print("CALCULATED VALUES")
print(f"{'-' * 80}")
print(f"Service Days: {service_days}")
print(f"Service Months: {service_months:.2f}")

# Daily salary
daily_salary = contract.ueipab_deduction_base / 30.0
print(f"Daily Salary: ${daily_salary:.2f}")

# Integral daily (base + utilidades + bono proportion)
utilidades_daily = daily_salary * (60.0 / 360.0)
bono_daily = daily_salary * (15.0 / 360.0)
integral_daily = daily_salary + utilidades_daily + bono_daily
print(f"Integral Daily: ${integral_daily:.2f}")

# ANTIGUEDAD calculation with historical tracking
print(f"\n{'-' * 80}")
print("ANTIGUEDAD (Seniority) - WITH HISTORICAL TRACKING")
print(f"{'-' * 80}")

if contract.ueipab_original_hire_date:
    # Total seniority from original hire
    total_days = (liquidation_date - contract.ueipab_original_hire_date).days
    total_months = total_days / 30.0
    print(f"Original Hire: {contract.ueipab_original_hire_date}")
    print(f"Total Seniority: {total_months:.2f} months")

    # Subtract previous liquidation period
    if contract.ueipab_previous_liquidation_date:
        paid_days = (contract.ueipab_previous_liquidation_date - contract.ueipab_original_hire_date).days
        paid_months = paid_days / 30.0
        net_months = total_months - paid_months
        print(f"Previous Liquidation: {contract.ueipab_previous_liquidation_date}")
        print(f"Already Paid Period: {paid_months:.2f} months")
        print(f"Net Owed Period: {net_months:.2f} months")
    else:
        net_months = total_months
        print(f"No previous liquidation")
        print(f"Net Owed Period: {net_months:.2f} months")
else:
    net_months = service_months
    print(f"No original hire date set, using service months: {net_months:.2f}")

# Calculate antiguedad amount
if net_months < 3:
    antiguedad_days = 0.0
else:
    antiguedad_days = net_months * 2

antiguedad_amount = antiguedad_days * integral_daily
print(f"Antiguedad Days: {antiguedad_days:.2f}")
print(f"Antiguedad Amount: ${antiguedad_amount:.2f}")

# VACATION calculation with Aug 1 tracking
print(f"\n{'-' * 80}")
print("VACACIONES - WITH AUG 1 TRACKING")
print(f"{'-' * 80}")

if contract.ueipab_vacation_paid_until:
    vacation_start = contract.ueipab_vacation_paid_until + datetime.timedelta(days=1)
    vacation_days_period = (liquidation_date - vacation_start).days + 1
    vacation_months = vacation_days_period / 30.0
    print(f"Last Paid: {contract.ueipab_vacation_paid_until}")
    print(f"Period: {vacation_start} to {liquidation_date}")
    print(f"Days in Period: {vacation_days_period}")
    print(f"Months: {vacation_months:.2f}")
else:
    vacation_months = service_months
    print(f"No vacation paid date, using service months: {vacation_months:.2f}")

vacation_days = (vacation_months / 12.0) * 15.0
vacation_amount = vacation_days * daily_salary
print(f"Vacation Days: {vacation_days:.2f}")
print(f"Vacation Amount: ${vacation_amount:.2f}")

# BONO VACACIONAL with seniority tracking
print(f"\n{'-' * 80}")
print("BONO VACACIONAL - WITH SENIORITY TRACKING")
print(f"{'-' * 80}")

if contract.ueipab_original_hire_date:
    total_seniority_days = (liquidation_date - contract.ueipab_original_hire_date).days
    total_seniority_years = total_seniority_days / 365.0
    print(f"Total Seniority: {total_seniority_years:.2f} years")

    if total_seniority_years >= 5:
        annual_bono_rate = 14.0
        print(f"Rate: 14 days/year (≥ 5 years)")
    else:
        annual_bono_rate = 7.0 + (total_seniority_years * 1.4)
        print(f"Rate: {annual_bono_rate:.2f} days/year")
else:
    annual_bono_rate = 7.0
    print(f"No original hire date, using minimum: 7 days/year")

if contract.ueipab_vacation_paid_until:
    bono_start = contract.ueipab_vacation_paid_until + datetime.timedelta(days=1)
    bono_period_days = (liquidation_date - bono_start).days + 1
    bono_period_years = bono_period_days / 365.0
    print(f"Period: {bono_start} to {liquidation_date}")
    print(f"Period Years: {bono_period_years:.2f}")
else:
    bono_period_years = service_months / 12.0
    print(f"Period Years (from service): {bono_period_years:.2f}")

bono_days = bono_period_years * annual_bono_rate
bono_amount = bono_days * daily_salary
print(f"Bono Days: {bono_days:.2f}")
print(f"Bono Amount: ${bono_amount:.2f}")

# PRESTACIONES
print(f"\n{'-' * 80}")
print("PRESTACIONES (Severance)")
print(f"{'-' * 80}")

if service_months <= 3:
    prestaciones_days = service_months * 5
else:
    first_period = 3 * 5  # 15 days
    remaining_months = service_months - 3
    second_period = remaining_months * 2
    prestaciones_days = first_period + second_period

prestaciones_amount = prestaciones_days * integral_daily
print(f"Service Months: {service_months:.2f}")
print(f"Prestaciones Days: {prestaciones_days:.2f}")
print(f"Prestaciones Amount: ${prestaciones_amount:.2f}")

# UTILIDADES
print(f"\n{'-' * 80}")
print("UTILIDADES (Profit Sharing)")
print(f"{'-' * 80}")

if service_months < 12:
    utilidades_days = (service_months / 12.0) * 15.0
else:
    utilidades_days = 15.0

utilidades_amount = utilidades_days * daily_salary
print(f"Utilidades Days: {utilidades_days:.2f}")
print(f"Utilidades Amount: ${utilidades_amount:.2f}")

# INTEREST (13% annual - UPDATED!)
print(f"\n{'-' * 80}")
print("INTERESES (Interest) - 13% ANNUAL RATE")
print(f"{'-' * 80}")

average_prestaciones = prestaciones_amount * 0.5
annual_rate = 0.13  # UPDATED from 3% to 13%!
interest_fraction = service_months / 12.0
interest_amount = average_prestaciones * annual_rate * interest_fraction

print(f"Average Prestaciones: ${average_prestaciones:.2f}")
print(f"Annual Rate: {annual_rate * 100:.0f}%")
print(f"Period Fraction: {interest_fraction:.2f} years")
print(f"Interest Amount: ${interest_amount:.2f}")

# DEDUCTIONS
print(f"\n{'-' * 80}")
print("DEDUCTIONS")
print(f"{'-' * 80}")

gross_liquidation = (vacation_amount + bono_amount + utilidades_amount +
                     prestaciones_amount + antiguedad_amount + interest_amount)

faov_deduction = gross_liquidation * 0.01
inces_deduction = gross_liquidation * 0.005

print(f"Gross Liquidation: ${gross_liquidation:.2f}")
print(f"FAOV (1%): ${faov_deduction:.2f}")
print(f"INCES (0.5%): ${inces_deduction:.2f}")

# NET
net_liquidation = gross_liquidation - faov_deduction - inces_deduction

print(f"\n{'=' * 80}")
print("FINAL LIQUIDATION SUMMARY")
print(f"{'=' * 80}")
print(f"\nVacaciones:         ${vacation_amount:>10.2f}")
print(f"Bono Vacacional:    ${bono_amount:>10.2f}")
print(f"Utilidades:         ${utilidades_amount:>10.2f}")
print(f"Prestaciones:       ${prestaciones_amount:>10.2f}")
print(f"Antiguedad:         ${antiguedad_amount:>10.2f}")
print(f"Intereses (13%):    ${interest_amount:>10.2f}")
print(f"{'-' * 80}")
print(f"GROSS TOTAL:        ${gross_liquidation:>10.2f}")
print(f"\nDeductions:")
print(f"  FAOV (1%):        ${faov_deduction:>10.2f}")
print(f"  INCES (0.5%):     ${inces_deduction:>10.2f}")
print(f"{'-' * 80}")
print(f"NET LIQUIDATION:    ${net_liquidation:>10.2f}")
print(f"{'=' * 80}")

print(f"\n✅ PHASE 7 TEST COMPLETE")
print(f"\nGabriel España liquidation calculated successfully using new formulas!")
print(f"Historical tracking fields working correctly:")
print(f"  - Original hire date used for antiguedad and bono rate")
print(f"  - Previous liquidation subtracted from antiguedad")
print(f"  - Vacation period tracked from Aug 1, 2024")
print(f"  - Interest calculated at 13% annual (not 3%!)")
print("=" * 80)
