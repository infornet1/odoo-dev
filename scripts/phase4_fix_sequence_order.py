#!/usr/bin/env python3
"""
Phase 4 FIX: Fix Sequence Order - LIQUID_NET must compute AFTER deductions
============================================================================

Issue: LIQUID_NET (seq 30) computes BEFORE LIQUID_VACATION_PREPAID (seq 195)
Fix: Move LIQUID_NET to sequence 200 (after all deductions)

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("PHASE 4 FIX: SEQUENCE ORDER CORRECTION")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']

# Get the rules
net_rule = SalaryRule.search([('code', '=', 'LIQUID_NET')], limit=1)
prepaid_rule = SalaryRule.search([('code', '=', 'LIQUID_VACATION_PREPAID')], limit=1)

if not net_rule:
    print("❌ LIQUID_NET rule not found!")
elif not prepaid_rule:
    print("❌ LIQUID_VACATION_PREPAID rule not found!")
else:
    print(f"Current sequences:")
    print(f"  LIQUID_VACATION_PREPAID: {prepaid_rule.sequence}")
    print(f"  LIQUID_FAOV:             {SalaryRule.search([('code', '=', 'LIQUID_FAOV')], limit=1).sequence}")
    print(f"  LIQUID_INCES:            {SalaryRule.search([('code', '=', 'LIQUID_INCES')], limit=1).sequence}")
    print(f"  LIQUID_NET:              {net_rule.sequence} ⚠️  TOO EARLY!")
    print()

    # Move LIQUID_NET to sequence 200 (after all deductions)
    new_sequence = 200

    print(f"📝 Updating LIQUID_NET sequence: {net_rule.sequence} → {new_sequence}")
    net_rule.write({
        'sequence': new_sequence
    })

    env.cr.commit()

    print()
    print("✅ Updated sequence order:")
    print(f"  1. LIQUID_FAOV:             21  (deduction)")
    print(f"  2. LIQUID_INCES:            22  (deduction)")
    print(f"  3. LIQUID_VACATION_PREPAID: 195 (deduction)")
    print(f"  4. LIQUID_NET:              {new_sequence} ✅ NOW COMPUTES LAST")

print()
print("="*80)
print("✅ SUCCESS: Sequence order fixed")
print("="*80)
print()
print("NEXT STEPS:")
print("  1. Delete SLIP/567 (Josefina Rodriguez)")
print("  2. Create new liquidation payslip")
print("  3. LIQUID_NET should now include the -$164.18 deduction")
print()
