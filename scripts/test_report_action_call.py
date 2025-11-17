#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test report action call - the way wizard would call it
"""

# Find SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("❌ SLIP/795 not found!")
else:
    print(f"✅ Found payslip: {payslip.number}")
    print(f"   ID: {payslip.id}")
    print(f"   Employee: {payslip.employee_id.name}")

    # Get USD
    usd = env.ref('base.USD')

    # Get report action
    report_action = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
    print(f"\n✅ Report action found: {report_action.name}")
    print(f"   Report name: {report_action.report_name}")

    # Prepare data (exactly as wizard does)
    data = {
        'wizard_id': None,
        'currency_id': usd.id,
        'currency_name': 'USD',
        'payslip_ids': [payslip.id],
    }

    print(f"\n=== Calling report_action (as wizard does) ===")
    print(f"Data: {data}")

    try:
        # Call report_action exactly as wizard does
        # This is the KEY LINE - how wizard calls the report
        result = report_action.report_action(payslip, data=data)

        print(f"\n✅ Report action called successfully")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")

    except Exception as e:
        print(f"\n❌ Error calling report_action: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Test Complete ===")
