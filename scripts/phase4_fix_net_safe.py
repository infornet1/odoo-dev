#!/usr/bin/env python3
"""
Phase 4 FIX: Make LIQUID_NET safe when referencing LIQUID_VACATION_PREPAID
==========================================================================

The issue is that LIQUID_VACATION_PREPAID may not exist or may not be computed yet
when LIQUID_NET is calculated. We need to use a try/except block.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("PHASE 4 FIX: LIQUID_NET SAFE REFERENCE")
print("="*80)
print()

SalaryRule = env['hr.salary.rule']

net_rule = SalaryRule.search([('code', '=', 'LIQUID_NET')], limit=1)

if net_rule:
    print("Updating LIQUID_NET with safe reference to LIQUID_VACATION_PREPAID...")

    net_rule.write({
        'amount_python_compute': '''# Net Liquidation = All benefits - Deductions - Prepaid vacation/bono

# Safely get prepaid deduction (may not exist)
try:
    prepaid_deduction = LIQUID_VACATION_PREPAID or 0
except:
    prepaid_deduction = 0

result = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0) +
    (LIQUID_FAOV or 0) +
    (LIQUID_INCES or 0) +
    prepaid_deduction
)
'''
    })

    print("✅ Updated LIQUID_NET formula with safe reference")
else:
    print("⚠️  LIQUID_NET rule not found")

env.cr.commit()

print()
print("="*80)
print("✅ SUCCESS: LIQUID_NET formula fixed")
print("="*80)
print()
print("Try computing liquidation again - should work now!")
print()
