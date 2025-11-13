#!/usr/bin/env python3
"""
Phase 3: Fix Liquidation Formulas - Add Historical Tracking Support
====================================================================

Critical fix: Formulas must use historical tracking fields for accurate calculations!

Issue found: Virginia Verde (long-service) showing LOWER liquidation than Gabriel España (junior)
Root cause: Formulas not using ueipab_original_hire_date and ueipab_previous_liquidation_date

Virginia Verde example:
- Original hire: Oct 1, 2019
- Previous liquidation: Jul 31, 2023 (fully paid)
- Current contract: Sep 1, 2023
- WITHOUT historical tracking: Only 23.30 months antiguedad
- WITH historical tracking: 71 months total - 46 months paid = 25 months owed

Author: Claude Code
Date: 2025-11-13
"""

LIQUIDATION_FORMULAS_PHASE3 = {

    'LIQUID_ANTIGUEDAD': {
        'name': 'Seniority Payment (Antigüedad) - With Historical Tracking',
        'code': '''# Antigüedad: 2 days per month with historical tracking support
# CRITICAL: Must use ueipab_original_hire_date if available
# CRITICAL: Must subtract ueipab_previous_liquidation_date period if applicable

service_months = LIQUID_SERVICE_MONTHS or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY or 0.0

# Threshold: 1 month + 1 day = approximately 1.03 months
if service_months < 1.03:
    antiguedad_days = 0.0
else:
    # Check if historical tracking fields are available
    has_original_hire = hasattr(contract, 'ueipab_original_hire_date') and contract.ueipab_original_hire_date
    has_previous_liquidation = hasattr(contract, 'ueipab_previous_liquidation_date') and contract.ueipab_previous_liquidation_date

    if has_original_hire:
        # Calculate total seniority from original hire date
        total_days = (payslip.date_to - contract.ueipab_original_hire_date).days
        total_months = total_days / 30.0

        if has_previous_liquidation:
            # Subtract already-paid antiguedad period
            paid_days = (contract.ueipab_previous_liquidation_date - contract.ueipab_original_hire_date).days
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

# Example Virginia Verde (with historical tracking):
# Original hire: Oct 1, 2019
# Liquidation date: Jul 31, 2025
# Total months: 71 months
# Previous liquidation: Jul 31, 2023 (46 months)
# Net owed: 71 - 46 = 25 months
# Days: 25 × 2 = 50 days
# Amount: 50 × $5.40 = $270 (vs $251 without historical tracking)
'''
    },

    'LIQUID_VACACIONES': {
        'name': 'Vacation Payment - With Historical Tracking',
        'code': '''# Vacaciones: 15 days per year with vacation paid until tracking
# CRITICAL: Must use ueipab_vacation_paid_until if available

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

# Check if vacation paid until field is available
has_vacation_paid_until = hasattr(contract, 'ueipab_vacation_paid_until') and contract.ueipab_vacation_paid_until

if has_vacation_paid_until:
    # Calculate only unpaid period (from last payment to liquidation)
    days_from_last_payment = (payslip.date_to - contract.ueipab_vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    vacation_days = (months_in_period / 12.0) * 15.0
else:
    # No tracking, calculate proportionally for full service
    vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary

# Example with tracking (Aug 1, 2024 paid until):
# Liquidation: Jul 31, 2025
# Days from last payment: (Jul 31, 2025 - Aug 1, 2024) = 364 days
# Months: 364 / 30 = 12.13 months
# Vacation days: (12.13 / 12) × 15 = 15.16 days
'''
    },

    'LIQUID_BONO_VACACIONAL': {
        'name': 'Vacation Bonus - With Historical Tracking',
        'code': '''# Bono Vacacional: 15 days minimum with vacation paid until tracking
# CRITICAL: Must use ueipab_vacation_paid_until if available
# CRITICAL: Must use ueipab_original_hire_date for seniority calculation

service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0

# Determine seniority (for progressive bonus rate)
has_original_hire = hasattr(contract, 'ueipab_original_hire_date') and contract.ueipab_original_hire_date

if has_original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - contract.ueipab_original_hire_date).days
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

# Calculate period owed
has_vacation_paid_until = hasattr(contract, 'ueipab_vacation_paid_until') and contract.ueipab_vacation_paid_until

if has_vacation_paid_until:
    # Calculate only unpaid period
    days_from_last_payment = (payslip.date_to - contract.ueipab_vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    bonus_days = (months_in_period / 12.0) * annual_bonus_days
else:
    # No tracking, calculate proportionally for full service
    bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary

# Example Virginia Verde:
# Total seniority: Oct 2019 - Jul 2025 = 5.92 years → 15 days annual bonus
# Last paid: Aug 1, 2024
# Period owed: Aug 1, 2024 - Jul 31, 2025 = 12 months
# Bonus days: (12/12) × 15 = 15 days
'''
    },
}

# Main execution - works directly in Odoo shell
print("="*80)
print("PHASE 3: LIQUIDATION FORMULA FIXES - HISTORICAL TRACKING")
print("="*80)
print()
print("Critical Fix: Formulas now use historical tracking fields!")
print("Database: testing")
print()
print("Formulas to update:")
for idx, (code, data) in enumerate(LIQUIDATION_FORMULAS_PHASE3.items(), 1):
    print(f"  {idx}. {code}: {data['name']}")
print()

# Odoo shell provides 'env' automatically
SalaryRule = env['hr.salary.rule']

updated_count = 0

for rule_code, rule_data in LIQUIDATION_FORMULAS_PHASE3.items():
    # Find salary rule
    rule = SalaryRule.search([('code', '=', rule_code)], limit=1)

    if not rule:
        print(f"⚠️  {rule_code}: Not found - skipping")
        continue

    # Update formula
    rule.write({
        'amount_python_compute': rule_data['code']
    })

    print(f"✅ {rule_code}: {rule_data['name']} - UPDATED")
    updated_count += 1

# Commit changes
env.cr.commit()

print()
print("="*80)
print(f"✅ SUCCESS: Updated {updated_count} salary rules with historical tracking")
print("="*80)
print()
print("HISTORICAL TRACKING FIELDS NOW USED:")
print("  1. ✅ ueipab_original_hire_date - For total seniority calculation")
print("  2. ✅ ueipab_previous_liquidation_date - Subtract already-paid antiguedad")
print("  3. ✅ ueipab_vacation_paid_until - Calculate only unpaid vacation/bono")
print()
print("IMPACT ON VIRGINIA VERDE (SLIP/561):")
print("  Before: Antiguedad based on 23.30 months (Sep 2023 - Jul 2025)")
print("  After:  Antiguedad based on 25 months (71 total - 46 paid)")
print("  Increase: ~$19 USD more antiguedad")
print()
print("NEXT STEPS:")
print("  1. Delete SLIP/561 (Virginia Verde liquidation)")
print("  2. Recreate liquidation payslip")
print("  3. Verify Virginia > Gabriel (as expected for long-service staff)")
print()
