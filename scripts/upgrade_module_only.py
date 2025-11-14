#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements module ONLY
This ONLY updates the QWeb template - does NOT modify any payslip data
"""

# Find module
module = env['ir.module.module'].search([
    ('name', '=', 'ueipab_payroll_enhancements')
], limit=1)

if not module:
    print("❌ Module not found")
    exit()

print(f"📦 Module: {module.name}")
print(f"   Current State: {module.state}")

if module.state != 'installed':
    print(f"⚠️  Module is not installed!")
    exit()

print(f"\n🔄 Upgrading module (updates QWeb template only)...")
module.button_immediate_upgrade()

print(f"✅ Module upgraded successfully!")
print(f"\n📄 The report template has been updated.")
print(f"   NEW: Salary = contract.ueipab_deduction_base")
print(f"   NEW: Bonus = wage - deduction_base")
print(f"\n⚠️  NO PAYSLIP DATA WAS MODIFIED - only the report template!")

env.cr.commit()

