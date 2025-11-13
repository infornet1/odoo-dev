#!/usr/bin/env python3
"""
Check Salary Rule Sequences - Verify computation order
=======================================================

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CHECKING SALARY RULE SEQUENCES")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']

# Get liquidation structure
Structure = env['hr.payroll.structure']
liquidation_struct = Structure.search([
    ('name', '=', 'Liquidación Venezolana')
], limit=1)

if not liquidation_struct:
    print("❌ Liquidación Venezolana structure not found!")
else:
    print(f"✅ Structure: {liquidation_struct.name} (ID: {liquidation_struct.id})")
    print()
    print("All rules in structure (ordered by sequence):")
    print("-" * 80)

    rules = liquidation_struct.rule_ids.sorted(lambda r: r.sequence)

    for rule in rules:
        marker = ""
        if rule.code == 'LIQUID_VACATION_PREPAID':
            marker = " ⭐ PREPAID DEDUCTION"
        elif rule.code == 'LIQUID_NET':
            marker = " ⭐ NET CALCULATION"

        print(f"{rule.sequence:4d}  {rule.code:30s} {rule.name}{marker}")

    print("-" * 80)
    print()

    # Check specific rules
    prepaid_rule = SalaryRule.search([('code', '=', 'LIQUID_VACATION_PREPAID')], limit=1)
    net_rule = SalaryRule.search([('code', '=', 'LIQUID_NET')], limit=1)

    if prepaid_rule and net_rule:
        print(f"LIQUID_VACATION_PREPAID sequence: {prepaid_rule.sequence}")
        print(f"LIQUID_NET sequence: {net_rule.sequence}")
        print()

        if prepaid_rule.sequence < net_rule.sequence:
            print("✅ CORRECT ORDER: LIQUID_VACATION_PREPAID ({}) computes BEFORE LIQUID_NET ({})".format(
                prepaid_rule.sequence, net_rule.sequence))
        else:
            print("❌ WRONG ORDER: LIQUID_NET ({}) computes BEFORE LIQUID_VACATION_PREPAID ({})".format(
                net_rule.sequence, prepaid_rule.sequence))
            print()
            print("⚠️  This is the problem! LIQUID_NET needs higher sequence number.")
            print("   Fix: Update LIQUID_NET sequence to a number > {}".format(prepaid_rule.sequence))

print()
print("="*80)
