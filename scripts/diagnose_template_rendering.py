#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose template rendering issues
"""

print("=== Checking Template Structure ===")

# Check if template exists
template = env['ir.ui.view'].search([('key', '=', 'ueipab_payroll_enhancements.liquidacion_breakdown_report')])

if not template:
    print("❌ Template not found by key, searching by name...")
    template = env['ir.ui.view'].search([('name', 'ilike', 'liquidacion_breakdown_report')])

if template:
    print(f"✅ Template found (ID: {template.id})")
    print(f"   Name: {template.name}")
    print(f"   Key: {template.key}")
    print(f"   Type: {template.type}")
    print(f"   Active: {template.active}")

    # Show first 500 chars of arch
    arch = template.arch_db or template.arch
    print(f"\n=== Template Structure (first 500 chars) ===")
    print(arch[:500] if arch else "No arch found")
else:
    print("❌ Template not found!")

# Find SLIP/795
print("\n=== Testing Report Data Generation ===")
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if payslip:
    print(f"✅ Payslip found: {payslip.number}")

    # Get report model
    report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown']

    # Get USD
    usd = env.ref('base.USD')

    # Prepare data
    data = {
        'wizard_id': None,
        'currency_id': usd.id,
        'currency_name': 'USD',
        'payslip_ids': [payslip.id],
    }

    # Get report values
    values = report_model._get_report_values(docids=[payslip.id], data=data)

    print(f"\n=== Report Values ===")
    print(f"Keys in values dict: {list(values.keys())}")
    print(f"Reports count: {len(values.get('reports', []))}")

    if values.get('reports'):
        r = values['reports'][0]
        print(f"\n=== First Report Data ===")
        print(f"Keys in report dict: {list(r.keys())}")
        print(f"Employee: {r.get('employee')}")
        print(f"Contract: {r.get('contract')}")
        print(f"Currency: {r.get('currency')}")

    # Try to render template
    print(f"\n=== Testing Template Rendering ===")
    try:
        qweb = env['ir.qweb']

        # Try to render with the values
        html = qweb._render('ueipab_payroll_enhancements.liquidacion_breakdown_report', values)

        print(f"✅ Template rendered successfully!")
        print(f"   HTML length: {len(html)} bytes")
        print(f"   First 500 chars of HTML:")
        print(html[:500].decode('utf-8') if isinstance(html, bytes) else html[:500])

    except Exception as e:
        print(f"❌ Template rendering failed: {e}")
        import traceback
        traceback.print_exc()

else:
    print("❌ Payslip SLIP/795 not found!")

print("\n=== Diagnostic Complete ===")
