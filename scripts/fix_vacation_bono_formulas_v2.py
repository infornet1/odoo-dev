#!/usr/bin/env python3
"""
Fix Vacation & Bono Vacacional V2 Formula Bug
Date: 2025-11-17
Purpose: Fix double deduction bug where NET was incorrectly $0.00

CHANGES:
1. LIQUID_VACACIONES_V2: Calculate for FULL period (remove vacation_paid_until logic)
2. LIQUID_BONO_VACACIONAL_V2: Calculate for FULL period (preserve progressive rate)
3. LIQUID_VACATION_PREPAID_V2: Deduct ACTUAL prepaid amount from contract field

Expected Results:
- YOSMARI: NET $15.01 (was $0.00)
- VIRGINIA: NET $27.26 (was $0.00)
"""

print("="*80)
print("VACATION & BONO VACACIONAL V2 FORMULA FIX")
print("="*80)

# Get V2 structure
PayrollStructure = env['hr.payroll.structure']
structure = PayrollStructure.search([('code', '=', 'LIQUID_VE_V2')], limit=1)

if not structure:
    print("ERROR: LIQUID_VE_V2 structure not found!")
    exit(1)

print(f"Structure: {structure.name} (ID: {structure.id})")
print("="*80)

# Define the 3 new formulas
formulas = {
    'LIQUID_VACACIONES_V2': '''# Vacaciones: 15 days per year - Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Calculate for FULL liquidation period (no exclusions)
vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary''',

    'LIQUID_BONO_VACACIONAL_V2': '''# Bono Vacacional: Progressive rate based on seniority
# Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments
# ⚠️ CRITICAL: Uses ueipab_original_hire_date for progressive seniority bonus!

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

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

# Calculate for FULL liquidation period (no exclusions)
bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary''',

    'LIQUID_VACATION_PREPAID_V2': '''# Deduct prepaid vacation/bono amount from contract field
# This represents the actual dollar amount paid in advance (e.g., Aug 1 payments)
# CHANGED: Uses new ueipab_vacation_prepaid_amount field

# Try to get prepaid amount from contract field
try:
    prepaid_amount = contract.ueipab_vacation_prepaid_amount
    if not prepaid_amount:
        prepaid_amount = 0.0
except:
    prepaid_amount = 0.0

if prepaid_amount > 0:
    # Deduct the actual prepaid amount
    result = -1 * prepaid_amount
else:
    # No prepayment - no deduction
    result = 0.0'''
}

# Update each rule
SalaryRule = env['hr.salary.rule']
rules = structure.rule_ids

for code, new_formula in formulas.items():
    rule = rules.filtered(lambda r: r.code == code)

    if not rule:
        print(f"\n❌ ERROR: Rule {code} not found!")
        continue

    # Get old formula for comparison
    old_formula = rule.amount_python_compute or ''
    old_lines = len(old_formula.split('\n'))
    new_lines = len(new_formula.split('\n'))

    print(f"\n{'='*80}")
    print(f"Updating: {code}")
    print(f"{'='*80}")
    print(f"Name: {rule.name}")
    print(f"Old formula: {old_lines} lines")
    print(f"New formula: {new_lines} lines")
    print(f"Reduction: {old_lines - new_lines} lines ({100 * (old_lines - new_lines) / old_lines:.1f}%)")

    # Update the rule
    rule.write({'amount_python_compute': new_formula})
    env.cr.commit()  # Commit the change

    print(f"✅ Updated successfully!")

print("\n" + "="*80)
print("FIX COMPLETE!")
print("="*80)
print("\nSummary:")
print("- LIQUID_VACACIONES_V2: Calculate FULL period")
print("- LIQUID_BONO_VACACIONAL_V2: Calculate FULL period (preserve progressive rate)")
print("- LIQUID_VACATION_PREPAID_V2: Deduct ACTUAL prepaid amount")
print("\nNext Steps:")
print("1. Update contracts:")
print("   - YOSMARI: ueipab_vacation_prepaid_amount = $88.98")
print("   - VIRGINIA: ueipab_vacation_prepaid_amount = $256.82")
print("2. Test liquidations:")
print("   - YOSMARI: Expected NET $15.01")
print("   - VIRGINIA: Expected NET $27.26")
print("="*80)
