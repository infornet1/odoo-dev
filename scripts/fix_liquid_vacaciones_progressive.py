#!/usr/bin/env python3
"""
Fix LIQUID_VACACIONES_V2: Update to Progressive Calculation

Business Requirement (External Reviewer - 2025-11-20):
- Vacation calculation should use progressive rate (15 + 1 per year, max 30)
- Must match the same logic as LIQUID_BONO_VACACIONAL_V2
- LOTTT Article 190 compliance: employees earn 1 additional day per year

Current Issue:
- LIQUID_VACACIONES_V2 uses flat 15 days/year
- LIQUID_BONO_VACACIONAL_V2 uses progressive rate
- Inconsistency causes underpayment for employees with > 1 year service

Impact Example (5 years of service):
- Current: 5 years × 15 days = 75 days
- Correct: 5 years × 19 days* = 95 days (*15 + 4 additional)
- Underpayment: 20 days

Changes:
1. Update LIQUID_VACACIONES_V2 formula
2. Align with LIQUID_BONO_VACACIONAL_V2 progressive logic
3. Use ueipab_original_hire_date for seniority calculation
4. Progressive rate: 15 + (seniority - 1) up to max 30 days
"""

print("=" * 80)
print("FIX LIQUID_VACACIONES_V2: PROGRESSIVE RATE CALCULATION")
print("=" * 80)

# Find the Liquidación Venezolana V2 structure
struct = env['hr.payroll.structure'].search([('code', '=', 'LIQUID_VE_V2')], limit=1)

if not struct:
    print("\n❌ ERROR: Liquidación Venezolana V2 structure not found")
    print("   Please ensure LIQUID_VE_V2 structure exists")
    exit(1)

print(f"\n✅ Structure Found: {struct.name} (ID: {struct.id})")

# Find the LIQUID_VACACIONES_V2 rule
vac_rule = env['hr.salary.rule'].search([('code', '=', 'LIQUID_VACACIONES_V2')], limit=1)

if not vac_rule:
    print("\n❌ ERROR: LIQUID_VACACIONES_V2 rule not found")
    exit(1)

print(f"\n📋 Rule Found: {vac_rule.name} (ID: {vac_rule.id})")
print(f"   Code: {vac_rule.code}")
print(f"   Sequence: {vac_rule.sequence}")

print(f"\n📊 CURRENT FORMULA:")
print("-" * 80)
print(vac_rule.amount_python_compute)
print("-" * 80)

# New progressive formula (matches Bono Vacacional logic)
new_formula = """# Vacaciones: Progressive rate based on seniority (LOTTT Article 190)
# Aligned with LIQUID_BONO_VACACIONAL_V2 logic
# Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments
# Progressive: 15 days + 1 additional per year (max 30 days at 16+ years)

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
    # Calculate total seniority for progressive rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual vacation days based on total seniority (PROGRESSIVE)
if total_seniority_years >= 16:
    annual_vacation_days = 30.0  # Maximum per LOTTT
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year (Year 1=15, Year 2=16, Year 3=17, etc.)
    annual_vacation_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_vacation_days = 15.0  # Minimum

# Calculate for FULL liquidation period (no exclusions)
vacation_days = (service_months / 12.0) * annual_vacation_days

result = vacation_days * daily_salary"""

print(f"\n📊 NEW FORMULA (PROGRESSIVE):")
print("-" * 80)
print(new_formula)
print("-" * 80)

# Update the rule
print(f"\n🔧 Updating rule...")
vac_rule.write({
    'amount_python_compute': new_formula,
})
env.cr.commit()

print(f"✅ Rule updated successfully!")

# Verify the update
vac_rule.invalidate_cache()
updated_rule = env['hr.salary.rule'].browse(vac_rule.id)

print(f"\n✅ VERIFICATION:")
print(f"   Formula contains 'Progressive': {'Progressive' in updated_rule.amount_python_compute}")
print(f"   Formula contains 'total_seniority_years': {'total_seniority_years' in updated_rule.amount_python_compute}")
print(f"   Formula contains '15.0 + (total_seniority_years - 1)': {'15.0 + (total_seniority_years - 1)' in updated_rule.amount_python_compute}")
print(f"   Formula contains 'annual_vacation_days': {'annual_vacation_days' in updated_rule.amount_python_compute}")

print(f"\n📊 UPDATED FORMULA:")
print("-" * 80)
print(updated_rule.amount_python_compute)
print("-" * 80)

print(f"\n" + "=" * 80)
print("LIQUID_VACACIONES_V2 PROGRESSIVE UPDATE COMPLETE")
print("=" * 80)

print(f"\n📊 IMPACT EXAMPLES:")
print(f"\nEmployee with 1 year seniority:")
print(f"   Annual rate: 15 days (base year)")
print(f"   1 year × 15 days = 15 days")

print(f"\nEmployee with 5 years seniority:")
print(f"   Annual rate: 19 days (15 + 4 additional)")
print(f"   OLD: 5 years × 15 days = 75 days")
print(f"   NEW: 5 years × 19 days = 95 days")
print(f"   Difference: +20 days (26% increase)")

print(f"\nEmployee with 10 years seniority:")
print(f"   Annual rate: 24 days (15 + 9 additional)")
print(f"   OLD: 10 years × 15 days = 150 days")
print(f"   NEW: 10 years × 24 days = 240 days")
print(f"   Difference: +90 days (60% increase)")

print(f"\nEmployee with 16+ years seniority:")
print(f"   Annual rate: 30 days (maximum)")
print(f"   OLD: 16 years × 15 days = 240 days")
print(f"   NEW: 16 years × 30 days = 480 days")
print(f"   Difference: +240 days (100% increase)")

print("\n📋 IMPORTANT NOTES:")
print("   • Now matches LIQUID_BONO_VACACIONAL_V2 logic (consistency)")
print("   • Uses ueipab_original_hire_date for total seniority calculation")
print("   • Progressive: 15 + 1 per year (max 30 at 16+ years)")
print("   • LOTTT Article 190 compliant")
print("   • Existing payslips are NOT affected - only new liquidations")
print("   • Prepaid vacation deduction logic remains unchanged")

print("\n✅ Next step: Generate test liquidation payslips to verify calculations")
print("\n" + "=" * 80)
