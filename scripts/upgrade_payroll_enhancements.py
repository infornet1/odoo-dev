#!/usr/bin/env python3
"""Upgrade ueipab_payroll_enhancements module to v1.19.0"""

print("="*80)
print("UPGRADE MODULE: ueipab_payroll_enhancements")
print("="*80)

Module = env['ir.module.module']

module = Module.search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)

if module:
    print(f"Module: {module.name}")
    print(f"Current state: {module.state}")
    print(f"Current version: {module.latest_version}")

    # Mark for upgrade
    module.button_immediate_upgrade()

    print("\n✅ Module upgraded to v1.19.0!")
    print("\nNew features:")
    print("- Exchange rate override for VEB currency")
    print("- Custom rate entry field")
    print("- Rate date selector for automatic lookup")
else:
    print("❌ Module not found!")

print("="*80)
