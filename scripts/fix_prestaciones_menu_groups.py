#!/usr/bin/env python3
"""
Fix Prestaciones Menu Groups
==============================

Remove restrictive group and use same as other reports.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("FIXING PRESTACIONES MENU GROUPS")
print("="*80)
print()

Menu = env['ir.ui.menu']

# Get other report menus to see what groups they use
disbursement_menu = Menu.search([('name', '=', 'Payroll Disbursement Detail')], limit=1)
our_menu = Menu.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

if disbursement_menu:
    print(f"Payroll Disbursement Detail groups: {[(g.id, g.full_name) for g in disbursement_menu.groups_id]}")
    print()

if our_menu:
    print(f"Prestaciones Soc. Intereses groups (BEFORE): {[(g.id, g.full_name) for g in our_menu.groups_id]}")

    # Copy groups from disbursement menu (which works)
    if disbursement_menu.groups_id:
        our_menu.write({'groups_id': [(6, 0, disbursement_menu.groups_id.ids)]})
        print(f"✅ Updated to use same groups as Disbursement Detail")
    else:
        # No groups = visible to all payroll users
        our_menu.write({'groups_id': [(5, 0, 0)]})
        print(f"✅ Removed all group restrictions (visible to all payroll users)")

    our_menu = Menu.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)
    print(f"Prestaciones Soc. Intereses groups (AFTER): {[(g.id, g.full_name) for g in our_menu.groups_id]}")

env.cr.commit()

print()
print("="*80)
print("✅ SUCCESS: Menu groups fixed")
print("="*80)
print()
print("Please refresh your browser (Ctrl+F5) and check Payroll → Reports menu")
print()
