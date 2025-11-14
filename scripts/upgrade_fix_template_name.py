#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements - Fix Template Name
========================================================

Fix report_name to use correct module prefix.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("UPGRADING ueipab_payroll_enhancements - FIX TEMPLATE NAME")
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

    # Verify the report action
    Report = env['ir.actions.report']
    report = Report.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

    if report:
        print(f"✅ Report Action verified (ID: {report.id})")
        print(f"   Name: {report.name}")
        print(f"   Report Name: {report.report_name}")
        print(f"   Report File: {report.report_file}")

        if report.report_name == 'ueipab_payroll_enhancements.prestaciones_interest':
            print("   ✅ Template name is CORRECT!")
        else:
            print(f"   ❌ Template name is WRONG: {report.report_name}")
    else:
        print("⚠️  Report action not found!")

    print()

print("="*80)
print("READY TO TEST:")
print("="*80)
print("1. Go to Payroll → Reports → Prestaciones Soc. Intereses")
print("2. Select a liquidation payslip")
print("3. Click 'Generate Report'")
print("4. PDF should generate successfully!")
print()
