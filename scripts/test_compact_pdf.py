#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test compact payslip PDF generation"""

import odoo
from odoo import api, SUPERUSER_ID

# Get registry
registry = odoo.registry('testing')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find SLIP/953
    payslip = env['hr.payslip'].search([('number', '=', 'SLIP/953')], limit=1)

    if not payslip:
        print("ERROR: SLIP/953 not found")
        exit(1)

    print(f"Found payslip: {payslip.number}")
    print(f"Employee: {payslip.employee_id.name}")
    print(f"Date: {payslip.date_from} to {payslip.date_to}")

    # Create wizard
    wizard = env['payslip.compact.wizard'].create({
        'payslip_ids': [(6, 0, [payslip.id])],
        'currency_id': env['res.currency'].search([('name', '=', 'USD')], limit=1).id,
    })

    print(f"\nWizard created with {wizard.payslip_count} payslip(s)")
    print(f"Currency: {wizard.currency_id.name}")

    # Generate report
    try:
        action = wizard.action_generate_report()
        print(f"\n✓ Report action generated successfully!")
        print(f"Action type: {action.get('type')}")
        print(f"Report name: {action.get('report_name')}")

        # Now actually render the PDF to check content
        report = env.ref('ueipab_payroll_enhancements.action_report_payslip_compact')
        pdf_data, _ = report._render_qweb_pdf(payslip.ids, data={
            'payslip_ids': payslip.ids,
            'currency_id': wizard.currency_id.id,
            'use_custom_rate': False,
            'custom_exchange_rate': False,
            'rate_date': False,
        })

        print(f"\n✓ PDF rendered successfully!")
        print(f"PDF size: {len(pdf_data)} bytes")

        if len(pdf_data) > 5000:
            print("✓ PDF appears to have content (>5KB)")
        else:
            print("⚠ WARNING: PDF may be blank (<5KB)")

    except Exception as e:
        print(f"\n✗ ERROR generating report:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
