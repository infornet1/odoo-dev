#!/usr/bin/env python3
"""
Check Prestaciones Interest Report Menu
========================================

Verify menu item and wizard are properly loaded.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CHECKING PRESTACIONES INTEREST REPORT MENU")
print("="*80)
print()

# Check wizard action
Action = env['ir.actions.act_window']
action = Action.search([('res_model', '=', 'prestaciones.interest.wizard')], limit=1)

if action:
    print(f"✅ Wizard Action found (ID: {action.id})")
    print(f"   Name: {action.name}")
    print(f"   Model: {action.res_model}")
    print()
else:
    print("❌ Wizard action NOT found!")
    print()

# Check menu item
Menu = env['ir.ui.menu']
menu = Menu.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

if menu:
    print(f"✅ Menu item found (ID: {menu.id})")
    print(f"   Name: {menu.name}")
    print(f"   Parent: {menu.parent_id.name if menu.parent_id else 'N/A'}")
    print(f"   Action: {menu.action}")
    print(f"   Sequence: {menu.sequence}")
    print(f"   Groups: {[g.name for g in menu.groups_id]}")
    print()
else:
    print("❌ Menu item NOT found!")
    print()
    print("Searching for all payroll report menus...")
    all_menus = Menu.search([('parent_id.name', '=', 'Reports')])
    for m in all_menus:
        print(f"   - {m.name} (ID: {m.id})")
    print()

# Check wizard model
try:
    wizard_model = env['prestaciones.interest.wizard']
    print(f"✅ Wizard model loaded: {wizard_model._name}")
except Exception as e:
    print(f"❌ Wizard model ERROR: {e}")

print()

# Check report model
try:
    report_model = env['report.ueipab_payroll.prestaciones_interest']
    print(f"✅ Report model loaded: {report_model._name}")
except Exception as e:
    print(f"❌ Report model ERROR: {e}")

print()
print("="*80)
print("TROUBLESHOOTING STEPS:")
print("="*80)
print("1. Hard reload browser (Ctrl+Shift+R)")
print("2. Clear browser cache")
print("3. Log out and log back in")
print("4. Check user has group: 'Payroll / User'")
print()
