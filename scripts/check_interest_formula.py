#!/usr/bin/env python3
"""
Check Current LIQUID_INTERESES Formula
=======================================

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CURRENT LIQUID_INTERESES FORMULA")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']

interest_rule = SalaryRule.search([('code', '=', 'LIQUID_INTERESES')], limit=1)

if not interest_rule:
    print("❌ LIQUID_INTERESES rule not found!")
else:
    print(f"✅ Rule found (ID: {interest_rule.id})")
    print(f"   Name: {interest_rule.name}")
    print(f"   Sequence: {interest_rule.sequence}")
    print()
    print("Current Formula:")
    print("-" * 80)
    print(interest_rule.amount_python_compute)
    print("-" * 80)
    print()

print("="*80)
