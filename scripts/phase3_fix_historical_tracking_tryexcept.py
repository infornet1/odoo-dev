#!/usr/bin/env python3
"""
Phase 3 FIX v2: Historical Tracking with Try/Except (Most Compatible)
=====================================================================

Using try/except blocks which are definitely allowed in safe_eval

Author: Claude Code
Date: 2025-11-13
"""

LIQUIDATION_FORMULAS_PHASE3_TRYEXCEPT = {

    'LIQUID_VACACIONES': {
        'name': 'Vacation Payment - With Historical Tracking (Try/Except)',
        'code': '''# Vacaciones: 15 days per year with vacation paid until tracking
# Uses try/except to safely access historical tracking fields

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

# Try to get vacation paid until field safely
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Calculate only unpaid period (from last payment to liquidation)
    days_from_last_payment = (payslip.date_to - vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    vacation_days = (months_in_period / 12.0) * 15.0
else:
    # No tracking, calculate proportionally for full service
    vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary
'''
    },

    'LIQUID_BONO_VACACIONAL': {
        'name': 'Vacation Bonus - With Historical Tracking (Try/Except)',
        'code': '''# Bono Vacacional: 15 days minimum with historical tracking
# Uses try/except to safely access historical tracking fields

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual bonus days based on total seniority
if total_seniority_years >= 16:
    annual_bonus_days = 30.0  # Maximum
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year
    annual_bonus_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_bonus_days = 15.0  # Minimum

# Try to get vacation paid until for period calculation
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Calculate only unpaid period
    days_from_last_payment = (payslip.date_to - vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    bonus_days = (months_in_period / 12.0) * annual_bonus_days
else:
    # No tracking, calculate proportionally for full service
    bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary
'''
    },

    'LIQUID_ANTIGUEDAD': {
        'name': 'Seniority Payment (Antigüedad) - With Historical Tracking (Try/Except)',
        'code': '''# Antigüedad: 2 days per month with historical tracking support
# Uses try/except to safely access historical tracking fields

service_months = LIQUID_SERVICE_MONTHS or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY or 0.0

# Threshold: 1 month + 1 day = approximately 1.03 months
if service_months < 1.03:
    antiguedad_days = 0.0
else:
    # Try to get historical tracking fields safely
    try:
        original_hire = contract.ueipab_original_hire_date
        if not original_hire:
            original_hire = False
    except:
        original_hire = False

    try:
        previous_liquidation = contract.ueipab_previous_liquidation_date
        if not previous_liquidation:
            previous_liquidation = False
    except:
        previous_liquidation = False

    if original_hire:
        # Calculate total seniority from original hire date
        total_days = (payslip.date_to - original_hire).days
        total_months = total_days / 30.0

        if previous_liquidation:
            # Subtract already-paid antiguedad period
            paid_days = (previous_liquidation - original_hire).days
            paid_months = paid_days / 30.0

            # Net antiguedad owed = Total - Already paid
            net_months = total_months - paid_months
            antiguedad_days = net_months * 2
        else:
            # No previous liquidation, calculate for total seniority
            antiguedad_days = total_months * 2
    else:
        # No historical tracking, use standard calculation
        antiguedad_days = service_months * 2

result = antiguedad_days * antiguedad_daily
'''
    },
}

# Main execution
print("="*80)
print("PHASE 3 FIX v2: HISTORICAL TRACKING (TRY/EXCEPT)")
print("="*80)
print()
print("Using try/except blocks for maximum safe_eval compatibility")
print("Database: testing")
print()

SalaryRule = env['hr.salary.rule']

updated_count = 0

for rule_code, rule_data in LIQUIDATION_FORMULAS_PHASE3_TRYEXCEPT.items():
    rule = SalaryRule.search([('code', '=', rule_code)], limit=1)

    if not rule:
        print(f"⚠️  {rule_code}: Not found - skipping")
        continue

    rule.write({
        'amount_python_compute': rule_data['code']
    })

    print(f"✅ {rule_code}: {rule_data['name']}")
    updated_count += 1

env.cr.commit()

print()
print("="*80)
print(f"✅ SUCCESS: Updated {updated_count} salary rules")
print("="*80)
print()
print("Try computing liquidation in UI now - should work!")
print()
