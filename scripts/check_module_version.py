#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check module version and upgrade status
"""

# Check module
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)

if not module:
    print("ERROR: Module not found")
else:
    print("=" * 80)
    print("MODULE STATUS")
    print("=" * 80)
    print(f"Name: {module.name}")
    print(f"State: {module.state}")
    print(f"Installed Version: {module.installed_version}")
    print(f"Latest Version: {module.latest_version}")
    print()

    if module.state == 'installed':
        print("✅ Module is installed")
    else:
        print(f"⚠️  Module state: {module.state}")

    print()
    print("To upgrade the module to v1.20.0:")
    print("  1. Go to Apps menu")
    print("  2. Remove 'Apps' filter")
    print("  3. Search for 'ueipab_payroll_enhancements'")
    print("  4. Click 'Upgrade' button")
    print()
    print("OR run upgrade via shell:")
    print("  module.button_immediate_upgrade()")
