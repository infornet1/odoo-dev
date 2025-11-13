#!/usr/bin/env python3
"""
Phase 6: Update Liquidation Formulas
=====================================

Updates 4 critical liquidation formulas to use new historical tracking fields:

1. LIQUID_INTERESES: Change interest rate 3% → 13%
2. LIQUID_ANTIGUEDAD: Use ueipab_original_hire_date, subtract previous liquidation
3. LIQUID_VACACIONES: Calculate from ueipab_vacation_paid_until
4. LIQUID_BONO_VACACIONAL: Calculate from ueipab_vacation_paid_until, 14 days for 5+ years
"""

print("=" * 80)
print("PHASE 6: UPDATE LIQUIDATION FORMULAS")
print("=" * 80)

# Formula updates
FORMULA_UPDATES = {
    'LIQUID_INTERESES': {
        'name': 'Interest on Prestaciones',
        'code': '''# Interest on accumulated prestaciones - UPDATED 2025-11-12
# Annual rate: 13% (confirmed from spreadsheet analysis)
# Period: Sep 2023 - Jul 2025 showed 24.47% over 22 months = 13.3% annually

service_months = LIQUID_SERVICE_MONTHS or 0.0
prestaciones = LIQUID_PRESTACIONES or 0.0

# Average balance (prestaciones accrue over time)
average_balance = prestaciones * 0.5

# UPDATED: Annual interest rate = 13% (not 3%!)
annual_rate = 0.13

# Interest for period worked
interest_fraction = service_months / 12.0
result = average_balance * annual_rate * interest_fraction
'''
    },

    'LIQUID_ANTIGUEDAD': {
        'name': 'Seniority Payment (Antigüedad)',
        'code': '''# Antiguedad with historical tracking - UPDATED 2025-11-12
# Uses ueipab_original_hire_date for continuity
# Subtracts ueipab_previous_liquidation_date period if set

antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY or 0.0
end_date = payslip.date_to

# Use original hire date if available, otherwise contract start
if contract.ueipab_original_hire_date:
    start_date = contract.ueipab_original_hire_date
else:
    start_date = contract.date_start

# Calculate total months from original hire to liquidation
total_days = (end_date - start_date).days
total_months = total_days / 30.0

# Subtract already-paid period if previous liquidation exists
if contract.ueipab_previous_liquidation_date:
    paid_days = (contract.ueipab_previous_liquidation_date - start_date).days
    paid_months = paid_days / 30.0
    net_months = total_months - paid_months
else:
    net_months = total_months

# Antiguedad: 2 days per month after first 3 months
if net_months < 3:
    antiguedad_days = 0.0
else:
    antiguedad_days = net_months * 2

result = antiguedad_days * antiguedad_daily

# Example (Virginia Verde):
# Total: Oct 2019 - Jul 2025 = 71 months
# Paid: Oct 2019 - Jul 2023 = 46 months
# Net: 25 months × 2 days = 50 days antiguedad
'''
    },

    'LIQUID_VACACIONES': {
        'name': 'Vacation Payment',
        'code': '''# Vacation with Aug 1 tracking - UPDATED 2025-11-12
# Calculates only vacation accrued AFTER ueipab_vacation_paid_until

daily_salary = LIQUID_DAILY_SALARY or 0.0
end_date = payslip.date_to

# Use vacation paid until date if available
if contract.ueipab_vacation_paid_until:
    # Start from day after last payment
    from datetime import timedelta
    start_date = contract.ueipab_vacation_paid_until + timedelta(days=1)
else:
    # No previous payment: calculate from contract start
    start_date = contract.date_start

# Calculate months in period
days_in_period = (end_date - start_date).days
months_in_period = days_in_period / 30.0

# 15 days vacation per year
vacation_days = (months_in_period / 12.0) * 15.0

result = vacation_days * daily_salary

# Example: Aug 2, 2024 - Jul 31, 2025 = 364 days ≈ 12 months = 15 days
'''
    },

    'LIQUID_BONO_VACACIONAL': {
        'name': 'Vacation Bonus',
        'code': '''# Bono Vacacional with seniority tracking - UPDATED 2025-11-12
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

# Calculate period to pay
if contract.ueipab_vacation_paid_until:
    from datetime import timedelta
    period_start = contract.ueipab_vacation_paid_until + timedelta(days=1)
else:
    period_start = contract.date_start

period_days = (end_date - period_start).days
period_years = period_days / 365.0

# Apply rate to period
bono_days = period_years * annual_bono_days

result = bono_days * daily_salary

# Example (Virginia Verde, 5.92 years total):
# Rate: 14 days/year (≥ 5 years)
# Period: Aug 2, 2024 - Jul 31, 2025 = 1 year
# Bono: 1 × 14 = 14 days
'''
    }
}

print("\nUpdating 4 liquidation formulas...")
print("-" * 80)

updated_count = 0
for rule_code, rule_data in FORMULA_UPDATES.items():
    rule = env['hr.salary.rule'].search([('code', '=', rule_code)], limit=1)

    if rule:
        rule.amount_python_compute = rule_data['code']
        print(f"✅ {rule_code}: {rule_data['name']}")
        updated_count += 1
    else:
        print(f"❌ {rule_code}: NOT FOUND")

# Commit changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Updated: {updated_count} formulas")
print(f"   Expected: 4 formulas")

print("\n" + "=" * 80)
print("WHAT WAS UPDATED")
print("=" * 80)
print("\n1. LIQUID_INTERESES:")
print("   - Interest rate: 3% → 13% (from spreadsheet analysis)")
print("\n2. LIQUID_ANTIGUEDAD:")
print("   - Uses ueipab_original_hire_date for total seniority")
print("   - Subtracts ueipab_previous_liquidation_date period")
print("   - Example: Virginia Verde gets 25 months (not 71)")
print("\n3. LIQUID_VACACIONES:")
print("   - Calculates from ueipab_vacation_paid_until (Aug 1, 2024)")
print("   - Only pays for Aug 2, 2024 - Jul 31, 2025 period")
print("\n4. LIQUID_BONO_VACACIONAL:")
print("   - Uses total seniority for rate (14 days for 5+ years)")
print("   - Calculates period from ueipab_vacation_paid_until")

print("\n" + "=" * 80)
print("✅ PHASE 6 COMPLETE!")
print("=" * 80)
print("\nAll liquidation formulas updated to use historical tracking!")
print("Ready for testing with Gabriel España and Virginia Verde.")
print("=" * 80)
