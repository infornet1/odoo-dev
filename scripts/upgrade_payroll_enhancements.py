#!/usr/bin/env python3
"""
Upgrade ueipab_payroll_enhancements module to load email templates

This script upgrades the module to version 1.26.0 which includes:
- Regular payslip email template
- AGUINALDOS email template
"""

import odoorpc

# Connect to Odoo
print("Connecting to Odoo...")
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('testing', 'finanzas@ueipab.edu.ve', 'Changeit2')

print("✅ Connected to Odoo (testing database)")

# Get module
Module = odoo.env['ir.module.module']
module = Module.search([('name', '=', 'ueipab_payroll_enhancements')])

if not module:
    print("❌ Module 'ueipab_payroll_enhancements' not found")
    exit(1)

module_id = module[0]
module_data = Module.read(module_id, ['name', 'state', 'latest_version'])

print(f"\n📦 Module: {module_data['name']}")
print(f"   State: {module_data['state']}")
print(f"   Version: {module_data['latest_version']}")

# Upgrade module
print("\n🔧 Upgrading module...")
Module.button_immediate_upgrade([module_id])

print("\n✅ Module upgraded successfully!")

# Verify email templates were created
print("\n📧 Verifying email templates...")
Template = odoo.env['mail.template']

templates = Template.search([
    ('name', 'in', [
        'Payslip Email - Employee Delivery',
        'Aguinaldos Email - Christmas Bonus Delivery'
    ])
])

if templates:
    template_data = Template.read(templates, ['name', 'model_id', 'subject'])
    print(f"\n✅ Found {len(template_data)} email templates:")
    for template in template_data:
        print(f"   - {template['name']}")
        print(f"     Model: {template['model_id'][1]}")
        print(f"     Subject: {template['subject'][:60]}...")
else:
    print("\n⚠️  No email templates found (may need to check module data files)")

print("\n" + "=" * 80)
print("UPGRADE COMPLETE")
print("=" * 80)
