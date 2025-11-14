#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements Module
===========================================

Upgrades the module to v1.7.0 with Prestaciones Interest Report

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("UPGRADING ueipab_payroll_enhancements MODULE")
print("="*80)
print()

Module = env['ir.module.module']

# Find module
module = Module.search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)

if not module:
    print("❌ Module not found!")
else:
    print(f"✅ Module found (ID: {module.id})")
    print(f"   Name: {module.name}")
    print(f"   State: {module.state}")
    print(f"   Version: {module.latest_version}")
    print()

    if module.state != 'installed':
        print("⚠️  Module not installed. Installing...")
        module.button_immediate_install()
        print("✅ Module installed")
    else:
        print("📦 Upgrading module...")
        module.button_immediate_upgrade()
        print("✅ Module upgraded")

    # Refresh module info
    module = Module.search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)
    print()
    print(f"Updated state: {module.state}")
    print(f"Updated version: {module.latest_version}")

print()
print("="*80)
print("✅ SUCCESS: Module upgrade complete")
print("="*80)
print()
print("NEW FEATURES AVAILABLE:")
print("  • Prestaciones Soc. Intereses report")
print("  • Navigate to: Payroll → Reports → Prestaciones Soc. Intereses")
print("  • Select liquidation payslips and currency (USD/VEB)")
print("  • Generate monthly interest breakdown report")
print()
