#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test actual PDF generation
"""

# Find SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("❌ SLIP/795 not found!")
else:
    print(f"✅ Found payslip: {payslip.number}")

    # Get report action
    report_action = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
    print(f"✅ Report action found: {report_action.name}")
    print(f"   Report name: {report_action.report_name}")

    # Get currency
    usd = env.ref('base.USD')

    # Prepare data (same as wizard would pass)
    data = {
        'wizard_id': None,
        'currency_id': usd.id,
        'currency_name': 'USD',
        'payslip_ids': [payslip.id],
    }

    print(f"\n=== Attempting PDF Generation ===")
    try:
        # Generate PDF
        pdf_content, report_format = report_action.with_context()._render_qweb_pdf(
            report_action.report_name,
            res_ids=[payslip.id],
            data=data
        )

        print(f"✅ PDF generated successfully!")
        print(f"   PDF size: {len(pdf_content)} bytes")
        print(f"   Format: {report_format}")

        # Save to file for inspection
        with open('/tmp/test_liquidacion.pdf', 'wb') as f:
            f.write(pdf_content)
        print(f"   PDF saved to: /tmp/test_liquidacion.pdf")

    except Exception as e:
        print(f"❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Test Complete ===")
