#!/usr/bin/env python3
"""
Check User Groups
==================

Check what groups the user has.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("CHECKING USER GROUPS")
print("="*80)
print()

User = env['res.users']

# Find user
user = User.search([('login', '=', 'gustavo.perdomo@ueipab.edu.ve')], limit=1)

if not user:
    print("❌ User not found!")
else:
    print(f"✅ User found: {user.name} ({user.login})")
    print(f"   ID: {user.id}")
    print(f"   Active: {user.active}")
    print()

    print("USER GROUPS:")
    for group in user.groups_id:
        print(f"  • {group.full_name} (ID: {group.id})")
    print()

    # Check for Payroll groups specifically
    payroll_groups = user.groups_id.filtered(lambda g: 'Payroll' in g.full_name or 'payroll' in g.full_name)
    if payroll_groups:
        print("PAYROLL GROUPS:")
        for group in payroll_groups:
            print(f"  • {group.full_name} (ID: {group.id})")
    else:
        print("⚠️  NO PAYROLL GROUPS FOUND!")
        print()
        print("USER NEEDS: 'Payroll / Officer' group (ID: 76)")
        print()

        # Try to add the group
        officer_group = env['res.groups'].browse(76)
        if officer_group:
            print(f"Adding group: {officer_group.full_name}")
            user.write({'groups_id': [(4, 76)]})
            env.cr.commit()
            print("✅ Group added! Please log out and log back in.")
        else:
            print("❌ Could not find Officer group")

print()
print("="*80)
