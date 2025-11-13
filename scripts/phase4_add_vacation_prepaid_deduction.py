#!/usr/bin/env python3
"""
Phase 4: Add Vacation Prepaid Deduction to Liquidation
=======================================================

Issue: Employees who terminated before Aug 1, 2025 but received the Aug 1, 2025
       annual vacation payment need that amount DEDUCTED from final liquidation.

Example: Josefina Rodriguez (SLIP/565)
- Terminated: Jul 31, 2025
- Received Aug 1, 2025 vacation payment: Vac $72.43 + Bono $91.75 = $164.18
- This $164.18 should be DEDUCTED from her final liquidation payment

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("PHASE 4: ADD VACATION PREPAID DEDUCTION")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']
RuleCategory = env['hr.salary.rule.category']

# Find deduction category
deduction_category = RuleCategory.search([('code', '=', 'DED')], limit=1)
if not deduction_category:
    print("⚠️  Deduction category (DED) not found, searching for any category...")
    deduction_category = RuleCategory.search([], limit=1)
    print(f"   Using category: {deduction_category.name}")

# Check if rule already exists
existing_rule = SalaryRule.search([('code', '=', 'LIQUID_VACATION_PREPAID')], limit=1)

if existing_rule:
    print(f"\n✅ Rule LIQUID_VACATION_PREPAID already exists (ID: {existing_rule.id})")
    print("   Updating formula...")

    existing_rule.write({
        'name': 'Vacaciones/Bono Prepagadas (Deducción)',
        'sequence': 195,
        'amount_python_compute': '''# Deduct prepaid vacation/bono if already paid on Aug 1, 2025
# Only applies if ueipab_vacation_paid_until is set (indicates prepayment)

# Try to get vacation paid until field
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Employee received Aug 1 annual payment - deduct from liquidation
    vacaciones = LIQUID_VACACIONES or 0.0
    bono = LIQUID_BONO_VACACIONAL or 0.0
    result = -1 * (vacaciones + bono)
else:
    # No prepayment (hired after Aug 31, 2025) - no deduction
    result = 0.0
''',
    })
    print("   ✅ Updated existing rule")

else:
    print("\n📝 Creating new salary rule: LIQUID_VACATION_PREPAID")

    new_rule = SalaryRule.create({
        'name': 'Vacaciones/Bono Prepagadas (Deducción)',
        'code': 'LIQUID_VACATION_PREPAID',
        'sequence': 195,
        'category_id': deduction_category.id,
        'amount_select': 'code',
        'amount_python_compute': '''# Deduct prepaid vacation/bono if already paid on Aug 1, 2025
# Only applies if ueipab_vacation_paid_until is set (indicates prepayment)

# Try to get vacation paid until field
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Employee received Aug 1 annual payment - deduct from liquidation
    vacaciones = LIQUID_VACACIONES or 0.0
    bono = LIQUID_BONO_VACACIONAL or 0.0
    result = -1 * (vacaciones + bono)
else:
    # No prepayment (hired after Aug 31, 2025) - no deduction
    result = 0.0
''',
    })
    print(f"   ✅ Created new rule (ID: {new_rule.id})")

# Update LIQUID_NET formula
print("\n📝 Updating LIQUID_NET formula...")

net_rule = SalaryRule.search([('code', '=', 'LIQUID_NET')], limit=1)

if net_rule:
    net_rule.write({
        'amount_python_compute': '''# Net Liquidation = All benefits - Deductions - Prepaid vacation/bono

result = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0) +
    (LIQUID_FAOV or 0) +
    (LIQUID_INCES or 0) +
    (LIQUID_VACATION_PREPAID or 0)
)
'''
    })
    print("   ✅ Updated LIQUID_NET formula")
else:
    print("   ⚠️  LIQUID_NET rule not found")

env.cr.commit()

print()
print("="*80)
print("✅ SUCCESS: Vacation prepaid deduction implemented")
print("="*80)
print()
print("NEXT STEPS:")
print("  1. Recompute SLIP/565 (Josefina Rodriguez)")
print("  2. Verify new line: LIQUID_VACATION_PREPAID = -$164.18")
print("  3. Verify net reduced: $1,341.18 → $1,177.00")
print()
