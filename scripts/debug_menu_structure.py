#!/usr/bin/env python3
"""
Debug Menu Structure
====================

Check the exact menu hierarchy and parent references.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("DEBUGGING MENU STRUCTURE")
print("="*80)
print()

Menu = env['ir.ui.menu']

# Find Payroll root menu
payroll_root = Menu.search([('name', 'ilike', 'Payroll')], limit=5)
print("PAYROLL ROOT MENUS:")
for menu in payroll_root:
    print(f"  - {menu.name} (ID: {menu.id}, Parent: {menu.parent_id.name if menu.parent_id else 'ROOT'})")
print()

# Find Reports submenu under Payroll
reports_menu = Menu.search([('name', '=', 'Reports')])
print("ALL 'Reports' MENUS:")
for menu in reports_menu:
    parent_name = menu.parent_id.name if menu.parent_id else 'ROOT'
    print(f"  - Reports (ID: {menu.id}, Parent: {parent_name})")

    # Show children
    children = Menu.search([('parent_id', '=', menu.id)])
    if children:
        print(f"    Children:")
        for child in children:
            print(f"      • {child.name} (ID: {child.id}, Seq: {child.sequence})")
print()

# Check our specific menu
our_menu = Menu.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)
if our_menu:
    print("OUR MENU DETAILS:")
    print(f"  Name: {our_menu.name}")
    print(f"  ID: {our_menu.id}")
    print(f"  Parent ID: {our_menu.parent_id.id if our_menu.parent_id else 'None'}")
    print(f"  Parent Name: {our_menu.parent_id.name if our_menu.parent_id else 'ROOT'}")
    print(f"  Parent Complete Name: {our_menu.parent_id.complete_name if our_menu.parent_id else 'N/A'}")
    print(f"  Sequence: {our_menu.sequence}")
    print(f"  Active: {our_menu.active}")
    print(f"  Action: {our_menu.action}")
    print(f"  Groups: {[(g.id, g.name) for g in our_menu.groups_id]}")
    print()

# Check the menu_payroll_reports reference
try:
    ref_menu = env.ref('ueipab_payroll_enhancements.menu_payroll_reports')
    print("MENU REFERENCE 'menu_payroll_reports':")
    print(f"  ID: {ref_menu.id}")
    print(f"  Name: {ref_menu.name}")
    print(f"  Parent: {ref_menu.parent_id.name if ref_menu.parent_id else 'ROOT'}")
    print()
except Exception as e:
    print(f"ERROR finding menu reference: {e}")
    print()

print("="*80)
print("RECOMMENDED FIX:")
print("="*80)
print("The menu might be pointing to wrong parent.")
print("Check: Is 'Reports' menu under correct Payroll root?")
print()
