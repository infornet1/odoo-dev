#!/usr/bin/env python3
"""
Delete corrupted SLIP/508 payslip (cancel first, then delete)
"""

# Find SLIP/508
slip508 = env['hr.payslip'].search([('id', '=', 508)], limit=1)

if not slip508:
    print("❌ SLIP/508 not found")
    exit()

print(f"🗑️  Deleting corrupted payslip: {slip508.number}")
print(f"   Employee: {slip508.employee_id.name}")
print(f"   Current State: {slip508.state}")

# Get corrupted value for display
salary_line = slip508.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
if salary_line:
    print(f"   VE_SALARY_70: ${salary_line[0].total:,.2f} (CORRUPTED)")

# Change state to draft so we can delete
print("\n📝 Changing state to draft...")
slip508.write({'state': 'draft'})

# Now delete the payslip
print("🗑️  Deleting payslip...")
slip508.unlink()

print("✅ SLIP/508 deleted successfully")

# Verify deletion
verify = env['hr.payslip'].search([('id', '=', 508)], limit=1)
if not verify:
    print("✅ Verified: SLIP/508 no longer exists in database")
else:
    print("❌ ERROR: SLIP/508 still exists!")

env.cr.commit()
print("\n✅ Changes committed to database")
