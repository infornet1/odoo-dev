#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements Module - Fixed Wizard Action
=================================================================

Fix missing view_id reference in wizard action.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("UPGRADING ueipab_payroll_enhancements MODULE (v1.7.0 - Fix wizard action)")
print("="*80)
print()

Module = env['ir.module.module']

module = Module.search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)

if not module:
    print("❌ Module 'ueipab_payroll_enhancements' not found!")
else:
    print(f"📦 Module: {module.name}")
    print(f"   State: {module.state}")
    print(f"   Version: {module.installed_version}")
    print()

    print("🔄 Upgrading module...")
    module.button_immediate_upgrade()

    print("✅ Module upgraded successfully!")
    print()

    # Verify the action is now properly loaded
    Action = env['ir.actions.act_window']
    action = Action.search([('res_model', '=', 'prestaciones.interest.wizard')], limit=1)

    if action:
        print(f"✅ Wizard Action verified (ID: {action.id})")
        print(f"   Name: {action.name}")
        print(f"   View ID: {action.view_id.name if action.view_id else 'NOT SET'}")
    else:
        print("⚠️  Wizard action not found after upgrade!")

    print()

print("="*80)
print("NEXT STEPS:")
print("="*80)
print("1. Hard reload browser (Ctrl+Shift+R)")
print("2. Check Payroll → Reports menu")
print()
