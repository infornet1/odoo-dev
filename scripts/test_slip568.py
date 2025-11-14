#!/usr/bin/env python3
"""
Test SLIP/568 Specifically
===========================

Check if SLIP/568 exists and test report generation with it.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("TESTING SLIP/568")
print("="*80)
print()

# Find SLIP/568
Payslip = env['hr.payslip']
slip568 = Payslip.search([('number', '=', 'SLIP/568')], limit=1)

if not slip568:
    print("❌ SLIP/568 not found!")
    print()
    print("Available liquidation slips:")
    all_slips = Payslip.search([
        ('struct_id.name', '=', 'Liquidación Venezolana'),
        ('state', 'in', ['draft', 'done'])
    ], limit=10)
    for slip in all_slips:
        print(f"   - {slip.number} - {slip.employee_id.name}")
    import sys
    sys.exit(1)

print(f"✅ SLIP/568 found!")
print(f"   Employee: {slip568.employee_id.name}")
print(f"   State: {slip568.state}")
print(f"   Structure: {slip568.struct_id.name}")
print(f"   Date: {slip568.date_from} to {slip568.date_to}")
print(f"   Contract: {slip568.contract_id.name if slip568.contract_id else 'None'}")
print()

# Check if it has prestaciones data
print("Checking salary rule lines...")
prestaciones_line = slip568.line_ids.filtered(lambda l: l.code == 'LIQUID_PRESTACIONES')
interest_line = slip568.line_ids.filtered(lambda l: l.code == 'LIQUID_INTERESES')

if prestaciones_line:
    print(f"   ✅ LIQUID_PRESTACIONES: ${prestaciones_line.total:,.2f}")
else:
    print(f"   ❌ LIQUID_PRESTACIONES: Not found!")

if interest_line:
    print(f"   ✅ LIQUID_INTERESES: ${interest_line.total:,.2f}")
else:
    print(f"   ❌ LIQUID_INTERESES: Not found!")

print()

# Now simulate EXACT wizard call
print("Simulating wizard call for SLIP/568...")
print()

Wizard = env['prestaciones.interest.wizard']
Currency = env['res.currency']
usd = Currency.search([('name', '=', 'USD')], limit=1)

# Create wizard exactly as UI does
wizard = Wizard.create({
    'payslip_ids': [(6, 0, [slip568.id])],
    'currency_id': usd.id,
})

print(f"Wizard created: ID={wizard.id}")
print(f"   Payslips: {wizard.payslip_ids.ids}")
print(f"   Currency: {wizard.currency_id.name}")
print()

# Call the action
print("Calling wizard.action_print_report()...")
action = wizard.action_print_report()

print(f"Action returned:")
print(f"   Type: {action.get('type')}")
print(f"   Report: {action.get('report_name')}")
print(f"   Data: {action.get('data')}")
print(f"   Context: {action.get('context')}")
print()

# Now manually render using the exact same approach Odoo web client would
print("Rendering PDF as web client would...")
Report = env['ir.actions.report']
report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

docids = [slip568.id]
data = action.get('data', {})

print(f"Calling _get_report_values(docids={docids}, data={data})...")
report_values = report_model._get_report_values(docids=docids, data=data)

print(f"Report values returned:")
print(f"   docs: {report_values.get('docs')}")
print(f"   currency: {report_values.get('currency').name if report_values.get('currency') else 'None'}")
print(f"   get_report_data function: {report_values.get('get_report_data')}")
print()

if report_values.get('docs'):
    for doc in report_values['docs']:
        print(f"Testing get_report_data for {doc.number}...")
        report_data = report_values['get_report_data'](doc)
        print(f"   Monthly data rows: {len(report_data.get('monthly_data', []))}")
        print(f"   Totals: {report_data.get('totals')}")

print()
print("="*80)
