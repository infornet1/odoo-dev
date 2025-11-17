#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test report generation end-to-end
"""

# Find SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("ERROR: SLIP/795 not found!")
else:
    print(f"✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")

    # Get USD
    usd = env.ref('base.USD')

    # Create wizard
    wizard = env['liquidacion.breakdown.wizard'].create({
        'payslip_ids': [(6, 0, [payslip.id])],
        'currency_id': usd.id,
    })

    print(f"✅ Wizard created (ID: {wizard.id})")

    # Call PDF action
    result = wizard.action_print_pdf()

    print(f"\n=== PDF Action Result ===")
    print(f"Type: {result.get('type')}")
    print(f"Report Name: {result.get('report_name')}")
    print(f"Data: {result.get('data')}")

    # Try to render the report
    print(f"\n=== Testing Report Rendering ===")
    report_action = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')

    try:
        # Get report data
        report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown']
        data = result.get('data', {})
        report_values = report_model._get_report_values(docids=[payslip.id], data=data)

        print(f"✅ Report values generated:")
        print(f"   Reports count: {len(report_values.get('reports', []))}")
        print(f"   Currency: {report_values.get('currency').name if report_values.get('currency') else 'None'}")

        if report_values.get('reports'):
            r = report_values['reports'][0]
            print(f"   Employee: {r.get('employee').name if r.get('employee') else 'None'}")
            print(f"   Benefits: {len(r.get('benefits', []))}")
            print(f"   Net: ${r.get('net_amount'):.2f}")

    except Exception as e:
        print(f"❌ Report rendering failed: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Test Complete ===")
