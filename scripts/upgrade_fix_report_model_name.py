#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements - Fix Report Model Name
============================================================

Fix report model _name to match report action.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("UPGRADING ueipab_payroll_enhancements - FIX REPORT MODEL NAME")
print("="*80)
print()

Module = env['ir.module.module']

module = Module.search([('name', '=', 'ueipab_payroll_enhancements')], limit=1)

if not module:
    print("❌ Module 'ueipab_payroll_enhancements' not found!")
else:
    print(f"📦 Module: {module.name}")
    print(f"   Version: {module.installed_version}")
    print()

    print("🔄 Upgrading module...")
    module.button_immediate_upgrade()

    print("✅ Module upgraded successfully!")
    print()

    # Verify the report model exists
    try:
        report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
        print(f"✅ Report Model found: {report_model._name}")
        print(f"   Description: {report_model._description}")
    except Exception as e:
        print(f"❌ Report Model ERROR: {e}")

    print()

    # Verify the report action
    Report = env['ir.actions.report']
    report = Report.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

    if report:
        print(f"✅ Report Action (ID: {report.id})")
        print(f"   Name: {report.name}")
        print(f"   Report Name: {report.report_name}")

        # Check if they match
        expected_model = f"report.{report.report_name}"
        try:
            test_model = env[expected_model]
            print(f"   ✅ Model '{expected_model}' EXISTS!")
        except Exception as e:
            print(f"   ❌ Model '{expected_model}' NOT FOUND!")

    print()

print("="*80)
print("READY TO TEST:")
print("="*80)
print("1. Refresh browser page")
print("2. Select a liquidation payslip")
print("3. Generate report")
print("4. PDF should now show data!")
print()
