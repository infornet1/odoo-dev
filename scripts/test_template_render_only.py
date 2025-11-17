#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test template rendering ONLY (not PDF conversion)
"""

# Get report model
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown']

# Find payslip
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)
usd = env.ref('base.USD')

data = {
    'wizard_id': None,
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
}

# Get report values (what template will receive)
values = report_model._get_report_values(docids=[payslip.id], data=data)

print("=== Report Values Prepared ===")
print(f"Keys: {list(values.keys())}")
print(f"Reports: {len(values.get('reports', []))}")
print(f"Docs: {len(values.get('docs', []))}")

# Try to render template with these values
print("\n=== Rendering Template ===")
try:
    qweb = env['ir.qweb']
    html = qweb._render('ueipab_payroll_enhancements.liquidacion_breakdown_report', values)

    print(f"✅ Template rendered!")
    print(f"   HTML size: {len(html)} bytes")

    # Save HTML
    with open('/tmp/template_render_test.html', 'wb') as f:
        f.write(html if isinstance(html, bytes) else html.encode('utf-8'))

    print(f"   Saved to: /tmp/template_render_test.html")

    # Show snippet
    html_str = html.decode('utf-8') if isinstance(html, bytes) else html
    if 'DEBUG REPORT' in html_str:
        idx = html_str.find('DEBUG REPORT')
        snippet = html_str[idx:idx+500]
        print(f"\n=== Template Content ===")
        print(snippet)
    else:
        print(f"\n⚠️ 'DEBUG REPORT' not found in HTML")
        print(f"First 500 chars:")
        print(html_str[:500])

except Exception as e:
    print(f"❌ Template rendering failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Done ===")
