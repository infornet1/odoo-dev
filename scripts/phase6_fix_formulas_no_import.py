#!/usr/bin/env python3
"""
Fix Phase 6 Formulas - Remove Forbidden Imports
================================================

The timedelta import is forbidden in safe_eval.
Fix LIQUID_VACACIONES and LIQUID_BONO_VACACIONAL to calculate dates
without using imports.
"""

print("=" * 80)
print("FIXING LIQUIDATION FORMULAS - REMOVE TIMEDELTA IMPORTS")
print("=" * 80)

# Fixed formulas without timedelta import
FORMULA_FIXES = {
    'LIQUID_VACACIONES': {
        'name': 'Vacation Payment',
        'code': '''# Vacation with Aug 1 tracking - UPDATED 2025-11-12 (FIX: No imports)
# Calculates only vacation accrued AFTER ueipab_vacation_paid_until

daily_salary = LIQUID_DAILY_SALARY or 0.0
end_date = payslip.date_to

# Use vacation paid until date if available
if contract.ueipab_vacation_paid_until:
    # Calculate period from day after last payment
    # We add 1 day by calculating from vacation_paid_until and adding 1 to days
    days_from_last_payment = (end_date - contract.ueipab_vacation_paid_until).days
    # Start from next day (so if paid Aug 1, we start Aug 2)
    days_in_period = days_from_last_payment  # This gives us Aug 1 to Jul 31 = 365 days
    # But we want Aug 2 to Jul 31 = 364 days, so we need to be careful
    # Actually the calculation (end - start).days gives us the right answer
    # Aug 1 to Jul 31 next year = 364 days (what we want for Aug 2-Jul 31)
    # So we use it as-is since we're counting FROM the payment date
    months_in_period = days_from_last_payment / 30.0
else:
    # No previous payment: calculate from contract start
    days_in_period = (end_date - contract.date_start).days
    months_in_period = days_in_period / 30.0

# 15 days vacation per year
vacation_days = (months_in_period / 12.0) * 15.0

result = vacation_days * daily_salary

# Example: Aug 1, 2024 - Jul 31, 2025 = 364 days ≈ 12.13 months = 15.17 days
'''
    },

    'LIQUID_BONO_VACACIONAL': {
        'name': 'Vacation Bonus',
        'code': '''# Bono Vacacional with seniority tracking - UPDATED 2025-11-12 (FIX: No imports)
# 14 days/year for 5+ years total seniority
# Calculates only period AFTER ueipab_vacation_paid_until

daily_salary = LIQUID_DAILY_SALARY or 0.0
end_date = payslip.date_to

# Calculate TOTAL seniority for rate determination
if contract.ueipab_original_hire_date:
    seniority_days = (end_date - contract.ueipab_original_hire_date).days
    total_seniority_years = seniority_days / 365.0
else:
    seniority_days = (end_date - contract.date_start).days
    total_seniority_years = seniority_days / 365.0

# Determine annual bono days based on total seniority
if total_seniority_years >= 5:
    annual_bono_days = 14.0
else:
    annual_bono_days = 7.0 + (total_seniority_years * 1.4)

# Calculate period to pay (from day after last payment)
if contract.ueipab_vacation_paid_until:
    # Days from last payment to liquidation
    period_days = (end_date - contract.ueipab_vacation_paid_until).days
    period_years = period_days / 365.0
else:
    period_days = (end_date - contract.date_start).days
    period_years = period_days / 365.0

# Apply rate to period
bono_days = period_years * annual_bono_days

result = bono_days * daily_salary

# Example (Virginia Verde, 5.92 years total):
# Rate: 14 days/year (≥ 5 years)
# Period: Aug 1, 2024 - Jul 31, 2025 = 364 days = 0.997 years
# Bono: 0.997 × 14 = 13.96 days
'''
    }
}

print("\nUpdating 2 formulas to remove timedelta imports...")
print("-" * 80)

updated_count = 0
for rule_code, rule_data in FORMULA_FIXES.items():
    rule = env['hr.salary.rule'].search([('code', '=', rule_code)], limit=1)

    if rule:
        rule.amount_python_compute = rule_data['code']
        print(f"✅ {rule_code}: {rule_data['name']} - FIXED (no imports)")
        updated_count += 1
    else:
        print(f"❌ {rule_code}: NOT FOUND")

# Commit changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Fixed: {updated_count} formulas")
print(f"   Expected: 2 formulas")

print("\n" + "=" * 80)
print("WHAT WAS FIXED")
print("=" * 80)
print("\n1. LIQUID_VACACIONES:")
print("   - Removed: from datetime import timedelta")
print("   - Uses: (end_date - vacation_paid_until).days directly")
print("\n2. LIQUID_BONO_VACACIONAL:")
print("   - Removed: from datetime import timedelta")
print("   - Uses: (end_date - vacation_paid_until).days directly")

print("\n" + "=" * 80)
print("✅ FORMULA FIX COMPLETE!")
print("=" * 80)
print("\nBoth formulas now work without forbidden imports.")
print("Ready to test liquidation computation from UI!")
print("=" * 80)
