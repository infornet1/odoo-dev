#!/usr/bin/env python3
"""
Fix Liquidation Salary Rule Formulas
=====================================
This script fixes the hardcoded liquidation salary rule formulas to use
dynamic calculations based on contract.ueipab_deduction_base field.

Author: Claude Code
Date: 2025-11-12
Test Case: Gabriel España (Contract 106, SLIP/553)
"""

# Liquidation formula definitions based on Venezuelan Labor Law (LOTTT)
# Using contract.ueipab_deduction_base ($151.56) as base salary

LIQUIDATION_FORMULAS = {
    'LIQUID_SERVICE_MONTHS': {
        'name': 'Service Months for Liquidation',
        'code': '''# Calculate service months from contract start to termination
from dateutil.relativedelta import relativedelta

# Get dates
start_date = contract.date_start
end_date = payslip.date_to

# Calculate difference
delta = relativedelta(end_date, start_date)
months = delta.years * 12 + delta.months
days_fraction = delta.days / 30.0

result = months + days_fraction

# Example: Sept 1, 2024 to July 31, 2025 = 10.97 months
'''
    },

    'LIQUID_DAILY_SALARY': {
        'name': 'Daily Salary Base for Liquidation',
        'code': '''# Daily salary based on deduction base (not total wage)
# Uses "original K" base that excludes bonuses/allowances
base_salary = contract.ueipab_deduction_base or 0.0
result = base_salary / 30.0

# Example: $151.56 / 30 = $5.05/day
'''
    },

    'LIQUID_INTEGRAL_DAILY': {
        'name': 'Integral Daily Salary',
        'code': '''# Venezuelan "Salario Integral" per LOTTT Article 104
# Includes base + proportional benefits (utilidades + bono vacacional)
base_daily = (contract.ueipab_deduction_base or 0.0) / 30.0

# Utilidades proportion: 60 days per year / 360 days
utilidades_daily = base_daily * (60.0 / 360.0)

# Bono Vacacional proportion: 15 days per year / 360 days
bono_vac_daily = base_daily * (15.0 / 360.0)

# Integral = Base + Benefits
result = base_daily + utilidades_daily + bono_vac_daily

# Example: $5.05 + $0.84 + $0.21 = $6.10/day integral
'''
    },

    'LIQUID_ANTIGUEDAD_DAILY': {
        'name': 'Antiguedad Daily Rate',
        'code': '''# Same as integral daily salary for antiguedad calculations
base_daily = (contract.ueipab_deduction_base or 0.0) / 30.0
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily
'''
    },

    'LIQUID_VACACIONES': {
        'name': 'Vacation Payment',
        'code': '''# Calculate unused vacation days
# Venezuelan law: 15 days per year after first year
# For first year: proportional (15 days * months / 12)

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

if service_months < 12:
    # First year: proportional
    vacation_days = (service_months / 12.0) * 15.0
else:
    # After first year: 15 days per year
    years = service_months / 12.0
    vacation_days = years * 15.0

# Check if employee has taken vacation (would need vacation records)
# For now, calculate maximum owed
result = vacation_days * daily_salary

# Example: 10.97 months → 13.71 days × $5.05 = $69.24
'''
    },

    'LIQUID_BONO_VACACIONAL': {
        'name': 'Vacation Bonus',
        'code': '''# Venezuelan vacation bonus: 7-14 days depending on seniority
# First year: 7 days minimum, proportional
service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

if service_months < 12:
    # First year: proportional (7 days minimum)
    bonus_days = (service_months / 12.0) * 7.0
else:
    # After first year: 7 days minimum
    # Up to 14 days for 5+ years of service
    years = service_months / 12.0
    if years >= 5:
        bonus_days = 14.0
    else:
        bonus_days = 7.0 + (years * 1.4)  # Progressive increase

result = bonus_days * daily_salary

# Example: 10.97 months → 6.40 days × $5.05 = $32.32
'''
    },

    'LIQUID_UTILIDADES': {
        'name': 'Profit Sharing (Utilidades)',
        'code': '''# Venezuelan profit sharing: 15-120 days per year
# Minimum 15 days if company has profits
# Maximum 4 months salary (120 days)
# For liquidation: proportional to months worked in fiscal year

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

# Calculate proportional to fiscal year (assume minimum 15 days annual)
if service_months < 12:
    utilidades_days = (service_months / 12.0) * 15.0
else:
    # Full year minimum
    utilidades_days = 15.0

result = utilidades_days * daily_salary

# Example: 10.97 months → 13.71 days × $5.05 = $69.24
'''
    },

    'LIQUID_PRESTACIONES': {
        'name': 'Severance Benefits (Prestaciones Sociales)',
        'code': '''# Venezuelan severance per LOTTT Article 141
# First 3 months: 5 days per month
# After 3 months: 2 additional days per month
# Calculated on integral salary

service_months = LIQUID_SERVICE_MONTHS or 0.0
integral_daily = LIQUID_INTEGRAL_DAILY or 0.0

if service_months <= 3:
    # First 3 months: 5 days per month
    prestaciones_days = service_months * 5
else:
    # First 3 months at 5 days/month
    first_period = 3 * 5  # 15 days
    # Remaining months at 2 days/month
    remaining_months = service_months - 3
    second_period = remaining_months * 2
    prestaciones_days = first_period + second_period

result = prestaciones_days * integral_daily

# Example: 10.97 months
# First 3 months: 3 × 5 = 15 days
# Remaining 7.97 months: 7.97 × 2 = 15.94 days
# Total: 30.94 days × $6.10 = $188.73
'''
    },

    'LIQUID_ANTIGUEDAD': {
        'name': 'Seniority Payment (Antigüedad)',
        'code': '''# Venezuelan seniority benefit per LOTTT Article 108
# After 3 months: 2 days per month of service
# Calculated on integral salary

service_months = LIQUID_SERVICE_MONTHS or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY or 0.0

if service_months < 3:
    # No antiguedad for first 3 months
    antiguedad_days = 0.0
else:
    # 2 days per month for all months worked
    antiguedad_days = service_months * 2

result = antiguedad_days * antiguedad_daily

# Example: 10.97 months × 2 days = 21.94 days × $6.10 = $133.83
'''
    },

    'LIQUID_INTERESES': {
        'name': 'Interest on Prestaciones',
        'code': '''# Venezuelan interest on accumulated prestaciones
# Annual rate as determined by Central Bank (typically 2-3%)
# Calculated monthly on accumulated balance

service_months = LIQUID_SERVICE_MONTHS or 0.0
prestaciones = LIQUID_PRESTACIONES or 0.0

# Estimate average balance (prestaciones accrue over time)
# Simple approximation: 50% of final prestaciones for average balance
average_balance = prestaciones * 0.5

# Annual interest rate (approximate, should be parameterized)
annual_rate = 0.03  # 3% per year

# Interest for period worked
interest_fraction = service_months / 12.0
result = average_balance * annual_rate * interest_fraction

# Example: $188.73 avg balance × 3% × 0.914 years = $5.17
'''
    },

    'LIQUID_FAOV': {
        'name': 'FAOV Deduction (1%)',
        'code': '''# FAOV deduction on liquidation gross
# 1% of total liquidation benefits (excluding this deduction)

gross_liquidation = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0)
)

result = -1 * (gross_liquidation * 0.01)

# Example: $498.53 gross × 1% = -$4.99
'''
    },

    'LIQUID_INCES': {
        'name': 'INCES Deduction (0.5%)',
        'code': '''# INCES deduction on liquidation gross
# 0.5% of total liquidation benefits

gross_liquidation = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0)
)

result = -1 * (gross_liquidation * 0.005)

# Example: $498.53 gross × 0.5% = -$2.49
'''
    },

    'LIQUID_NET': {
        'name': 'Net Liquidation',
        'code': '''# Net liquidation = All benefits - Deductions
result = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0) +
    (LIQUID_FAOV or 0) +
    (LIQUID_INCES or 0)
)

# Example: $69.24 + $32.32 + $69.24 + $188.73 + $133.83 + $5.17 - $4.99 - $2.49 = $491.05
'''
    },
}


def update_liquidation_formulas():
    """
    Update liquidation salary rule formulas in the database

    This function should be run via Odoo shell:
        docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http < fix_liquidation_formulas.py
    """
    print("="*80)
    print("FIXING LIQUIDATION SALARY RULE FORMULAS")
    print("="*80)
    print()

    # Get liquidation structure
    liquid_struct = env['hr.payroll.structure'].search([
        ('name', '=', 'Liquidación Venezolana')
    ], limit=1)

    if not liquid_struct:
        print("ERROR: Liquidation structure 'Liquidación Venezolana' not found!")
        return

    print(f"Found structure: {liquid_struct.name} (ID: {liquid_struct.id})")
    print()

    # Update each rule
    updated_count = 0
    for rule_code, formula_data in LIQUIDATION_FORMULAS.items():
        rule = env['hr.salary.rule'].search([
            ('code', '=', rule_code)
        ], limit=1)

        if rule:
            print(f"Updating: {rule_code} - {rule.name}")
            rule.write({
                'amount_python_compute': formula_data['code']
            })
            updated_count += 1
            print(f"  ✓ Updated")
        else:
            print(f"WARNING: Rule {rule_code} not found in database")
        print()

    # IMPORTANT: Commit the changes to database
    env.cr.commit()
    print("✓ Changes committed to database")

    print("="*80)
    print(f"COMPLETED: Updated {updated_count} salary rules")
    print("="*80)
    print()

    # Test with Gabriel España
    print("Testing with Gabriel España...")
    employee = env['hr.employee'].search([
        ('name', 'ilike', 'GABRIEL'),
        ('name', 'ilike', 'ESPAÑA')
    ], limit=1)

    if employee:
        print(f"Employee: {employee.name}")
        contract = env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open')
        ], limit=1)

        if contract:
            print(f"Contract: {contract.name}")
            print(f"  ueipab_deduction_base: ${contract.ueipab_deduction_base:.2f}")
            print(f"  Expected daily salary: ${contract.ueipab_deduction_base / 30:.2f}")
            print()
            print("To test: Recompute SLIP/553 and verify calculations")


if __name__ == '__main__':
    # This will be executed when run via Odoo shell
    update_liquidation_formulas()
