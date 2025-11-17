#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add current user to Payroll Officer group

This fixes the permission error for Liquidación Breakdown report
"""

# Get payroll groups
payroll_user = env.ref('hr_payroll_community.group_hr_payroll_community_user')
payroll_manager = env.ref('hr_payroll_community.group_hr_payroll_community_manager')

print("=== Available Payroll Groups ===")
print(f"1. {payroll_user.full_name} (ID: {payroll_user.id})")
print(f"2. {payroll_manager.full_name} (ID: {payroll_manager.id})")

# Find the admin user (ID 2 is typically the main admin)
admin_user = env['res.users'].browse(2)

if not admin_user.exists():
    print("\n❌ User ID 2 not found, trying to find admin user...")
    admin_user = env['res.users'].search([('login', '=', 'admin')], limit=1)

if not admin_user.exists():
    print("❌ Admin user not found!")
else:
    print(f"\n=== Current User ===")
    print(f"Name: {admin_user.name}")
    print(f"Login: {admin_user.login}")
    print(f"ID: {admin_user.id}")

    # Check current groups
    has_payroll_user = payroll_user in admin_user.groups_id
    has_payroll_manager = payroll_manager in admin_user.groups_id

    print(f"\nCurrent Payroll Access:")
    print(f"  Payroll/Officer: {has_payroll_user}")
    print(f"  Payroll/Manager: {has_payroll_manager}")

    if not has_payroll_user:
        print(f"\n=== Adding user to Payroll/Officer group ===")
        admin_user.write({
            'groups_id': [(4, payroll_user.id)]
        })
        env.cr.commit()
        print("✅ User added to Payroll/Officer group successfully!")
    else:
        print("\n✅ User already in Payroll/Officer group")

    if not has_payroll_manager:
        print(f"\n=== Adding user to Payroll/Manager group ===")
        admin_user.write({
            'groups_id': [(4, payroll_manager.id)]
        })
        env.cr.commit()
        print("✅ User added to Payroll/Manager group successfully!")
    else:
        print("\n✅ User already in Payroll/Manager group")

print("\n=== Complete ===")
print("Please log out and log back in for changes to take effect.")
print("Then try accessing: Payroll > Reports > Relación de Liquidación")
