#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upgrade ueipab_payroll_enhancements module to v1.9.0

New in v1.9.0:
- Relación de Liquidación report with formula breakdown
- PDF and XLSX export functionality
- Currency selector (USD/VEB)
- V1 and V2 liquidation structure support
"""

import odoo
from odoo import api, SUPERUSER_ID

# Get environment
env = api.Environment(odoo.cli.server.odoo.registry('testing'), SUPERUSER_ID, {})

# Find module
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])

if not module:
    print("ERROR: Module 'ueipab_payroll_enhancements' not found!")
    exit(1)

print(f"Current module state: {module.state}")
print(f"Current module version: {module.latest_version}")

# Upgrade module
if module.state == 'installed':
    print("\nUpgrading module...")
    module.button_immediate_upgrade()
    env.cr.commit()
    print("✅ Module upgraded successfully!")
    print(f"New version: {module.latest_version}")
else:
    print(f"ERROR: Module is in '{module.state}' state, expected 'installed'")
    exit(1)

# Verify new components exist
print("\n=== Verification ===")

# Check wizard model
wizard_model = env['ir.model'].search([('model', '=', 'liquidacion.breakdown.wizard')])
if wizard_model:
    print("✅ Wizard model 'liquidacion.breakdown.wizard' found")
else:
    print("❌ Wizard model 'liquidacion.breakdown.wizard' NOT found")

# Check report model
report_model = env['ir.model'].search([('model', '=', 'report.ueipab_payroll_enhancements.liquidacion_breakdown')])
if report_model:
    print("✅ Report model 'report.ueipab_payroll_enhancements.liquidacion_breakdown' found")
else:
    print("❌ Report model 'report.ueipab_payroll_enhancements.liquidacion_breakdown' NOT found")

# Check report action
report_action = env['ir.actions.report'].search([('name', '=', 'Relación de Liquidación')])
if report_action:
    print(f"✅ Report action 'Relación de Liquidación' found (ID: {report_action.id})")
else:
    print("❌ Report action 'Relación de Liquidación' NOT found")

# Check menu item
menu_item = env['ir.ui.menu'].search([('name', '=', 'Relación de Liquidación')])
if menu_item:
    print(f"✅ Menu item 'Relación de Liquidación' found (ID: {menu_item.id})")
else:
    print("❌ Menu item 'Relación de Liquidación' NOT found")

# Check security access
access_user = env['ir.model.access'].search([('name', '=', 'liquidacion.breakdown.wizard.user')])
access_manager = env['ir.model.access'].search([('name', '=', 'liquidacion.breakdown.wizard.manager')])

if access_user and access_manager:
    print("✅ Security access rules found")
else:
    print("❌ Security access rules NOT found")

print("\n=== Module Upgrade Complete ===")
print("Ready to test 'Relación de Liquidación' report!")
print("\nTest Instructions:")
print("1. Navigate to Payroll > Reports > Relación de Liquidación")
print("2. Select liquidation payslip (e.g., SLIP/797 - DIXIA BELLORIN)")
print("3. Choose currency (USD or VEB)")
print("4. Click 'Generate PDF' or 'Export XLSX'")
print("5. Verify report displays correctly with formulas")
