#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnose what compact report receives"""

import odoo
from odoo import api, SUPERUSER_ID
import json

# Get registry
registry = odoo.registry('testing')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Find SLIP/953
    payslip = env['hr.payslip'].search([('number', '=', 'SLIP/953')], limit=1)

    if not payslip:
        print("ERROR: SLIP/953 not found")
        exit(1)

    print(f"=== PAYSLIP INFO ===")
    print(f"Number: {payslip.number}")
    print(f"Employee: {payslip.employee_id.name}")
    print(f"Date From: {payslip.date_from}")
    print(f"Date To: {payslip.date_to}")
    print()

    # Prepare data like wizard does
    usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
    data = {
        'payslip_ids': [payslip.id],
        'currency_id': usd.id,
        'use_custom_rate': False,
        'custom_exchange_rate': 0.0,
        'rate_date': False,
    }

    print(f"=== WIZARD DATA ===")
    print(json.dumps(data, indent=2))
    print()

    # Get report model
    report_model = env['report.ueipab_payroll_enhancements.report_payslip_compact']

    print(f"=== CALLING _get_report_values ===")
    print(f"docids: {[payslip.id]}")
    print(f"data: {data}")
    print()

    # Call _get_report_values
    try:
        result = report_model._get_report_values(docids=[payslip.id], data=data)

        print(f"=== REPORT RESULT ===")
        print(f"Keys in result: {list(result.keys())}")
        print()

        print(f"doc_ids: {result.get('doc_ids')}")
        print(f"doc_model: {result.get('doc_model')}")
        print(f"docs: {result.get('docs')}")
        print(f"currency: {result.get('currency')}")
        print()

        print(f"Number of reports: {len(result.get('reports', []))}")

        if result.get('reports'):
            print()
            print(f"=== FIRST REPORT STRUCTURE ===")
            report = result['reports'][0]
            print(f"Report keys: {list(report.keys())}")
            print()
            print(f"payslip: {report.get('payslip')}")
            print(f"employee: {report.get('employee')}")
            print(f"salary_formatted: {report.get('salary_formatted')}")
            print(f"earnings count: {len(report.get('earnings', []))}")
            print(f"deductions count: {len(report.get('deductions', []))}")

            if report.get('earnings'):
                print()
                print(f"=== FIRST EARNING ===")
                print(json.dumps(report['earnings'][0], indent=2, default=str))

        print("\n✓ Report data generated successfully!")

    except Exception as e:
        print(f"\n✗ ERROR in _get_report_values:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
