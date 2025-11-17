#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Save HTML output to inspect what's being generated
"""

# Find SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("❌ SLIP/795 not found!")
else:
    print(f"✅ Found payslip: {payslip.number}")

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

    print(f"\n=== Rendering Template ===")
    try:
        qweb = env['ir.qweb']

        # Render template
        html = qweb._render('ueipab_payroll_enhancements.liquidacion_breakdown_report', values)

        # Save HTML to file
        with open('/tmp/test_liquidacion.html', 'wb') as f:
            f.write(html if isinstance(html, bytes) else html.encode('utf-8'))

        print(f"✅ HTML saved to: /tmp/test_liquidacion.html")
        print(f"   Size: {len(html)} bytes")

        # Show snippet of HTML around the benefits table
        html_str = html.decode('utf-8') if isinstance(html, bytes) else html

        # Find PRESTACIONES section
        prest_idx = html_str.find('PRESTACIONES SOCIALES')
        if prest_idx > 0:
            snippet = html_str[prest_idx:prest_idx+2000]
            print(f"\n=== PRESTACIONES Section (first 2000 chars) ===")
            print(snippet)
        else:
            print("\n❌ PRESTACIONES section not found in HTML!")

    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Done ===")
