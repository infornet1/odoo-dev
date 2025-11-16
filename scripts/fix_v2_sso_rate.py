#!/usr/bin/env python3
"""
Fix V2 SSO Rate: 4.0% → 4.5%

Business Requirement:
- SSO should be 4.5% monthly basis
- For bi-weekly (15 days): 4.5% ÷ 2 = 2.25%
- Formula should use: (monthly_salary × 0.045) × (period_days / 30.0)

Current Issue:
- V2 uses 0.04 (4.0%) instead of 0.045 (4.5%)

Expected Impact:
- Rafael Perez net will change from $195.84 to $195.54
- Then need to verify against spreadsheet $195.70
"""

print("=" * 80)
print("FIX V2 SSO RATE: 4.0% → 4.5%")
print("=" * 80)

# Find the SSO deduction rule
rule = env['hr.salary.rule'].search([('code', '=', 'VE_SSO_DED_V2')], limit=1)

if not rule:
    print("\n❌ ERROR: VE_SSO_DED_V2 rule not found")
    exit(1)

print(f"\n📋 Rule Found: {rule.name} (ID: {rule.id})")
print(f"   Code: {rule.code}")
print(f"   Sequence: {rule.sequence}")

print(f"\n📊 CURRENT FORMULA:")
print("-" * 80)
print(rule.amount_python_compute)
print("-" * 80)

# New formula with 4.5% rate
new_formula = """monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.045
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))"""

print(f"\n📊 NEW FORMULA (4.5% rate):")
print("-" * 80)
print(new_formula)
print("-" * 80)

# Update the rule
print(f"\n🔧 Updating rule...")
rule.write({
    'amount_python_compute': new_formula,
    'name': 'VE_SSO_DED_V2 - SSO 4.5%'  # Update name to reflect correct rate
})

print(f"✅ Rule updated successfully!")

# Verify the update
rule.invalidate_cache()
updated_rule = env['hr.salary.rule'].browse(rule.id)

print(f"\n✅ VERIFICATION:")
print(f"   Name: {updated_rule.name}")
print(f"   Formula contains '0.045': {'0.045' in updated_rule.amount_python_compute}")

print(f"\n📊 UPDATED FORMULA:")
print("-" * 80)
print(updated_rule.amount_python_compute)
print("-" * 80)

print(f"\n" + "=" * 80)
print("SSO RATE FIX COMPLETE")
print("=" * 80)

print(f"\n📊 EXPECTED IMPACT (Rafael Perez - 15 days):")
print(f"   Monthly Salary: $119.09")
print(f"   OLD SSO (4.0%): ($119.09 × 0.04) × (15/30) = $2.38")
print(f"   NEW SSO (4.5%): ($119.09 × 0.045) × (15/30) = $2.68")
print(f"   Difference: $0.30 more deduction")
print(f"\n   Old Net: $195.84")
print(f"   New Net: $195.84 - $0.30 = $195.54")
print(f"   Spreadsheet: $195.70")
print(f"   Remaining diff: $0.16 (to investigate)")

print("\n✅ Next step: Regenerate Rafael Perez V2 payslip to test")
print("\n" + "=" * 80)
