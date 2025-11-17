#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Liquidación Breakdown Report

Tests report generation for SLIP/795 (VIRGINIA VERDE)
"""

# Find SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("ERROR: SLIP/795 not found!")
else:
    print(f"✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")
    print(f"   Structure: {payslip.struct_id.name} ({payslip.struct_id.code})")
    print(f"   State: {payslip.state}")

    # Test report model directly
    print("\n=== Testing Report Model ===")
    report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown']

    # Get USD currency
    usd = env.ref('base.USD')

    # Prepare data dict (same as wizard would pass)
    data = {
        'wizard_id': None,
        'currency_id': usd.id,
        'currency_name': 'USD',
        'payslip_ids': [payslip.id],
    }

    print(f"Data dict: {data}")

    # Call _get_report_values
    try:
        result = report_model._get_report_values(docids=[payslip.id], data=data)

        print(f"\n✅ Report generated successfully!")
        print(f"   Doc IDs: {result.get('doc_ids')}")
        print(f"   Currency: {result.get('currency').name if result.get('currency') else 'None'}")
        print(f"   Reports count: {len(result.get('reports', []))}")

        if result.get('reports'):
            report = result['reports'][0]
            print(f"\n=== Report Data ===")
            print(f"   Employee: {report.get('employee').name if report.get('employee') else 'None'}")
            print(f"   Service months: {report.get('service_months_total')}")
            print(f"   Daily salary: ${report.get('daily_salary'):.2f}")
            print(f"   Benefits count: {len(report.get('benefits', []))}")
            print(f"   Deductions count: {len(report.get('deductions', []))}")
            print(f"   Total benefits: ${report.get('total_benefits'):.2f}")
            print(f"   Total deductions: ${report.get('total_deductions'):.2f}")
            print(f"   Net amount: ${report.get('net_amount'):.2f}")

            # Show first benefit
            if report.get('benefits'):
                b = report['benefits'][0]
                print(f"\n=== First Benefit (Sample) ===")
                print(f"   {b.get('number')}. {b.get('name')}")
                print(f"   Formula: {b.get('formula')}")
                print(f"   Calculation: {b.get('calculation')}")
                print(f"   Amount: ${b.get('amount'):.2f}")
        else:
            print("❌ No report data generated!")

    except Exception as e:
        print(f"❌ ERROR generating report: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Test Complete ===")
