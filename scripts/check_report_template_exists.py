#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if report template exists and how data is passed
"""

print("=== Checking Report Template ===")

# Find template
template_key = 'ueipab_payroll_enhancements.liquidacion_breakdown_report'
template = env['ir.ui.view'].search([('key', '=', template_key)], limit=1)

if template:
    print(f"✅ Template found: {template.name}")
    print(f"   ID: {template.id}")
    print(f"   Key: {template.key}")
    print(f"   Type: {template.type}")
else:
    print(f"❌ Template NOT found with key: {template_key}")
    # Try searching by name
    template = env['ir.ui.view'].search([('name', 'ilike', 'liquidacion_breakdown')], limit=1)
    if template:
        print(f"   Found by name: {template.name} (key: {template.key})")

print("\n=== Checking Report Action ===")
report_action = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
print(f"✅ Report action: {report_action.name}")
print(f"   report_name: {report_action.report_name}")
print(f"   report_file: {report_action.report_file}")
print(f"   report_type: {report_action.report_type}")

print("\n=== Checking Report Model ===")
report_model_name = 'report.ueipab_payroll_enhancements.liquidacion_breakdown'
if report_model_name in env:
    report_model = env[report_model_name]
    print(f"✅ Report model exists: {report_model_name}")

    # Test _get_report_values
    payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)
    usd = env.ref('base.USD')

    data = {
        'wizard_id': None,
        'currency_id': usd.id,
        'currency_name': 'USD',
        'payslip_ids': [payslip.id],
    }

    print(f"\n   Testing _get_report_values...")
    values = report_model._get_report_values(docids=[payslip.id], data=data)
    print(f"   ✅ Returned keys: {list(values.keys())}")
    print(f"   reports count: {len(values.get('reports', []))}")
    print(f"   docs count: {len(values.get('docs', []))}")
    print(f"   currency: {values.get('currency')}")
else:
    print(f"❌ Report model NOT found: {report_model_name}")

print("\n=== Test Complete ===")
