#!/usr/bin/env python3
"""
Upgrade ueipab_hr_contract module to add new field
Date: 2025-11-17
"""

print("="*80)
print("UPGRADE MODULE: ueipab_hr_contract")
print("="*80)

Module = env['ir.module.module']

# Find the module
module = Module.search([('name', '=', 'ueipab_hr_contract')], limit=1)

if module:
    print(f"Module: {module.name}")
    print(f"Current state: {module.state}")
    print(f"Current version: {module.latest_version}")

    # Mark for upgrade
    module.button_immediate_upgrade()

    print("\n✅ Module upgraded successfully!")
    print("\nNew field added:")
    print("- ueipab_vacation_prepaid_amount (Monetary)")
else:
    print("❌ Module not found!")

print("="*80)
