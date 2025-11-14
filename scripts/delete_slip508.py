#!/usr/bin/env python3
"""
Delete corrupted SLIP/508 payslip
"""

# Find SLIP/508
slip508 = env['hr.payslip'].search([('id', '=', 508)], limit=1)

if not slip508:
    print("❌ SLIP/508 not found")
    exit()

print(f"🗑️  Deleting corrupted payslip: {slip508.number}")
print(f"   Employee: {slip508.employee_id.name}")
print(f"   State: {slip508.state}")
print(f"   VE_SALARY_70: ${slip508.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')[0].total:,.2f} (CORRUPTED)")

# Delete the payslip (cascades to hr_payslip_line)
slip508.unlink()

print("✅ SLIP/508 deleted successfully")

# Verify deletion
verify = env['hr.payslip'].search([('id', '=', 508)], limit=1)
if not verify:
    print("✅ Verified: SLIP/508 no longer exists in database")
else:
    print("❌ ERROR: SLIP/508 still exists!")

env.cr.commit()
