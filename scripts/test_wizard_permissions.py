#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Wizard Permissions

Check if current user can access liquidacion.breakdown.wizard
"""

# Get current user
print(f"Current user: {env.user.name} (ID: {env.user.id})")
print(f"User groups: {[g.name for g in env.user.groups_id]}")

# Check if user has payroll access
payroll_user = env.ref('hr_payroll_community.group_hr_payroll_community_user', raise_if_not_found=False)
payroll_manager = env.ref('hr_payroll_community.group_hr_payroll_community_manager', raise_if_not_found=False)

if payroll_user:
    print(f"\nPayroll User Group (ID: {payroll_user.id}): {env.user in payroll_user.users}")
if payroll_manager:
    print(f"Payroll Manager Group (ID: {payroll_manager.id}): {env.user in payroll_manager.users}")

# Try to create wizard
print("\n=== Testing Wizard Creation ===")
try:
    # Find SLIP/795
    payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)
    usd = env.ref('base.USD')

    wizard = env['liquidacion.breakdown.wizard'].create({
        'payslip_ids': [(6, 0, [payslip.id])],
        'currency_id': usd.id,
    })

    print(f"✅ Wizard created successfully (ID: {wizard.id})")
    print(f"   Payslip count: {wizard.payslip_count}")
    print(f"   Currency: {wizard.currency_id.name}")

    # Try to call action_print_pdf
    print("\n=== Testing PDF Action ===")
    try:
        result = wizard.action_print_pdf()
        print(f"✅ PDF action returned successfully")
        print(f"   Result type: {result.get('type')}")
        print(f"   Report name: {result.get('report_name')}")
    except Exception as e:
        print(f"❌ PDF action failed: {e}")

except Exception as e:
    print(f"❌ Wizard creation failed: {e}")
    import traceback
    traceback.print_exc()

# Check access rules
print("\n=== Checking Access Rules ===")
access_rules = env['ir.model.access'].search([
    ('model_id.model', '=', 'liquidacion.breakdown.wizard')
])

if access_rules:
    for rule in access_rules:
        print(f"   {rule.name}")
        print(f"      Group: {rule.group_id.name if rule.group_id else 'All Users'}")
        print(f"      Read: {rule.perm_read}, Write: {rule.perm_write}, Create: {rule.perm_create}, Delete: {rule.perm_unlink}")
else:
    print("   ❌ NO ACCESS RULES FOUND!")

print("\n=== Test Complete ===")
