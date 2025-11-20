#!/usr/bin/env python3
"""
Fix VE_SSO_DED_V2: Implement Bs 1300 Monthly Ceiling with Bi-weekly Exchange Rate

Business Requirement (from Accounting Team - 2025-11-20):
- SSO deduction should be 4.5% monthly basis ✅ (already correct in formula)
- Apply CEILING of Bs 1300 monthly per employee (maximum SSO calculation base)
- Use bi-weekly exchange rate from payslip for Bs to USD conversion
- Update rule name to reflect correct 4.5% rate

Implementation Details:
1. Name: "VE_SSO_DED_V2 - SSO 4%" → "VE_SSO_DED_V2 - SSO 4.5%"
2. Formula: Add Bs 1300 ceiling logic with bi-weekly exchange rate
3. Exchange Rate: Use payslip.exchange_rate_used (set bi-weekly on batch)
4. Fallback Rate: 236.4601 VES/USD (realistic current rate, only if payslip rate missing)

Calculation Logic:
- Convert Bs 1300 ceiling to USD using bi-weekly exchange rate
- Compare employee's salary with ceiling
- Use LOWER amount as SSO calculation base
- Employees earning > Bs 1300 → SSO capped at Bs 1300
- Employees earning < Bs 1300 → SSO on actual salary

Example (with exchange rate 236.46 VES/USD):
- Bs 1300 ÷ 236.46 = ~$5.50 USD ceiling
- Employee earning $119/month → SSO base = $5.50 (ceiling applied)
- Employee earning $3/month → SSO base = $3.00 (actual salary used)
"""

print("=" * 80)
print("FIX VE_SSO_DED_V2: IMPLEMENT Bs 1300 MONTHLY CEILING")
print("=" * 80)

# Find the SSO deduction rule
rule = env['hr.salary.rule'].search([('code', '=', 'VE_SSO_DED_V2')], limit=1)

if not rule:
    print("\n❌ ERROR: VE_SSO_DED_V2 rule not found")
    exit(1)

print(f"\n📋 Rule Found: {rule.name} (ID: {rule.id})")
print(f"   Code: {rule.code}")
print(f"   Sequence: {rule.sequence}")

print(f"\n📊 CURRENT CONFIGURATION:")
print("-" * 80)
print(f"Name: {rule.name}")
print(f"\nFormula:")
print(rule.amount_python_compute)
print("-" * 80)

# New formula with Bs 1300 ceiling and bi-weekly exchange rate
new_formula = """# Venezuela SSO monthly ceiling in Bolivares
sso_ceiling_bs = 1300.0

# Use the bi-weekly exchange rate already captured on this payslip
# Fallback to 236.4601 (recent rate) if rate is missing
exchange_rate = payslip.exchange_rate_used or 236.4601

# Convert Bs 1300 ceiling to USD using bi-weekly rate
sso_ceiling_usd = sso_ceiling_bs / exchange_rate

# Get employee's monthly salary in USD
employee_salary_usd = contract.ueipab_salary_v2 or 0.0

# Apply ceiling: use lower of employee salary or Bs 1300 (in USD)
sso_base = min(employee_salary_usd, sso_ceiling_usd)

# Calculate monthly deduction at 4.5%
monthly_deduction = sso_base * 0.045

# Prorate for actual payslip period
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))"""

new_name = 'VE_SSO_DED_V2 - SSO 4.5%'

print(f"\n📊 NEW CONFIGURATION:")
print("-" * 80)
print(f"Name: {new_name}")
print(f"\nFormula:")
print(new_formula)
print("-" * 80)

# Update the rule
print(f"\n🔧 Updating rule...")
rule.write({
    'name': new_name,
    'amount_python_compute': new_formula,
})

print(f"✅ Rule updated successfully!")

# Verify the update
rule.invalidate_cache()
updated_rule = env['hr.salary.rule'].browse(rule.id)

print(f"\n✅ VERIFICATION:")
print(f"   Name: {updated_rule.name}")
print(f"   Formula contains 'sso_ceiling_bs = 1300.0': {'sso_ceiling_bs = 1300.0' in updated_rule.amount_python_compute}")
print(f"   Formula contains 'exchange_rate': {'exchange_rate' in updated_rule.amount_python_compute}")
print(f"   Formula contains 'min(': {'min(' in updated_rule.amount_python_compute}")
print(f"   Formula contains '0.045': {'0.045' in updated_rule.amount_python_compute}")

print(f"\n📊 UPDATED FORMULA:")
print("-" * 80)
print(updated_rule.amount_python_compute)
print("-" * 80)

print(f"\n" + "=" * 80)
print("SSO Bs 1300 CEILING IMPLEMENTATION COMPLETE")
print("=" * 80)

print(f"\n📊 CALCULATION EXAMPLES (with exchange rate 236.46 VES/USD):")
print(f"\nBs 1300 ÷ 236.46 = $5.50 USD ceiling")
print(f"\nEmployee A - Earning $119/month:")
print(f"   SSO Base: min($119, $5.50) = $5.50 (ceiling applied)")
print(f"   Monthly SSO: $5.50 × 4.5% = $0.25")
print(f"   Bi-weekly SSO (15 days): $0.25 × (15/30) = $0.12")
print(f"\nEmployee B - Earning $3/month:")
print(f"   SSO Base: min($3, $5.50) = $3.00 (actual salary used)")
print(f"   Monthly SSO: $3.00 × 4.5% = $0.14")
print(f"   Bi-weekly SSO (15 days): $0.14 × (15/30) = $0.07")

print("\n📋 IMPORTANT NOTES:")
print("   • Bs 1300 ceiling is hardcoded in formula")
print("   • Bi-weekly exchange rate comes from payslip.exchange_rate_used")
print("   • Fallback rate: 236.4601 VES/USD (only if payslip rate is missing)")
print("   • Employees earning > Bs 1300/month will have SSO capped")
print("   • Employees earning < Bs 1300/month will have SSO on actual salary")
print("   • Existing payslips are NOT affected - only new payslips after this change")

print("\n✅ Next step: Generate test payslips to verify the ceiling is working correctly")
print("\n" + "=" * 80)
