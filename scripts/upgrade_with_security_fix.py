#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements Module - Security Access Rules Fix
=======================================================================

Add missing security access rules for prestaciones.interest.wizard.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("UPGRADING ueipab_payroll_enhancements - SECURITY FIX")
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

    print("🔄 Upgrading module with security access rules...")
    module.button_immediate_upgrade()

    print("✅ Module upgraded successfully!")
    print()

    # Verify access rules are loaded
    Access = env['ir.model.access']
    access_user = Access.search([
        ('model_id.model', '=', 'prestaciones.interest.wizard'),
        ('group_id.name', '=', 'User')
    ], limit=1)

    access_manager = Access.search([
        ('model_id.model', '=', 'prestaciones.interest.wizard'),
        ('group_id.name', '=', 'Manager')
    ], limit=1)

    if access_user and access_manager:
        print(f"✅ Security Access Rules verified:")
        print(f"   User access (ID: {access_user.id}): {access_user.name}")
        print(f"   Manager access (ID: {access_manager.id}): {access_manager.name}")
    else:
        print("⚠️  Access rules not found after upgrade!")
        if not access_user:
            print("   Missing: User access rule")
        if not access_manager:
            print("   Missing: Manager access rule")

    print()

    # Verify the wizard action and menu
    Action = env['ir.actions.act_window']
    action = Action.search([('res_model', '=', 'prestaciones.interest.wizard')], limit=1)

    Menu = env['ir.ui.menu']
    menu = Menu.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

    if action and menu:
        print(f"✅ Wizard Action (ID: {action.id}): {action.name}")
        print(f"✅ Menu Item (ID: {menu.id}): {menu.name}")
        print(f"   Parent: {menu.parent_id.name if menu.parent_id else 'N/A'}")
        print(f"   Action: {menu.action}")
    else:
        print("⚠️  Action or Menu not found!")

    print()

print("="*80)
print("FINAL STEP:")
print("="*80)
print("1. Hard reload browser (Ctrl+Shift+R)")
print("2. Check Payroll → Reports → Prestaciones Soc. Intereses")
print("3. Menu should NOW be visible!")
print()
