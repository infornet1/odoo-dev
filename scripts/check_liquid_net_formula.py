#!/usr/bin/env python3
"""
Check LIQUID_NET Formula - Verify prepaid deduction is included
================================================================

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CHECKING LIQUID_NET FORMULA")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']

# Find LIQUID_NET rule
net_rule = SalaryRule.search([('code', '=', 'LIQUID_NET')], limit=1)

if not net_rule:
    print("❌ LIQUID_NET rule not found!")
else:
    print(f"✅ LIQUID_NET rule found (ID: {net_rule.id})")
    print(f"   Name: {net_rule.name}")
    print(f"   Sequence: {net_rule.sequence}")
    print()
    print("Current Formula:")
    print("-" * 80)
    print(net_rule.amount_python_compute)
    print("-" * 80)
    print()

    # Check if formula includes LIQUID_VACATION_PREPAID
    if 'LIQUID_VACATION_PREPAID' in net_rule.amount_python_compute:
        print("✅ Formula INCLUDES LIQUID_VACATION_PREPAID reference")
    else:
        print("❌ Formula DOES NOT INCLUDE LIQUID_VACATION_PREPAID reference")
        print()
        print("⚠️  This is the problem! LIQUID_NET needs to include the prepaid deduction.")

print()
print("="*80)
