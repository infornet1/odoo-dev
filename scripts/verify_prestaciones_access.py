#!/usr/bin/env python3
"""
Verify Prestaciones Interest Wizard Access Rules
=================================================

Check if access rules are properly loaded.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("VERIFYING ACCESS RULES FOR PRESTACIONES INTEREST WIZARD")
print("="*80)
print()

# Check model exists
Model = env['ir.model']
model = Model.search([('model', '=', 'prestaciones.interest.wizard')], limit=1)

if model:
    print(f"✅ Model found: {model.name} (ID: {model.id})")
    print()
else:
    print("❌ Model not found!")
    print()
    import sys
    sys.exit(1)

# Check access rules
Access = env['ir.model.access']
all_access = Access.search([('model_id', '=', model.id)])

if all_access:
    print(f"✅ Found {len(all_access)} access rule(s):")
    for access in all_access:
        group_name = access.group_id.name if access.group_id else 'All Users'
        print(f"   - {access.name}")
        print(f"     Group: {group_name}")
        print(f"     Read: {access.perm_read}, Write: {access.perm_write}, Create: {access.perm_create}, Delete: {access.perm_unlink}")
        print()
else:
    print("❌ NO ACCESS RULES FOUND!")
    print()

# Check if current user can access the model
User = env['res.users']
current_user = User.browse(1)  # Admin user

print(f"Testing access for admin user (ID: {current_user.id}):")
try:
    env['prestaciones.interest.wizard'].check_access_rights('read')
    print("   ✅ Read access: OK")
except Exception as e:
    print(f"   ❌ Read access: DENIED - {e}")

try:
    env['prestaciones.interest.wizard'].check_access_rights('create')
    print("   ✅ Create access: OK")
except Exception as e:
    print(f"   ❌ Create access: DENIED - {e}")

print()
print("="*80)
