#!/usr/bin/env python3
"""
Test Liquidación report without header/footer
"""

print("=" * 80)
print("TESTING LIQUIDACIÓN REPORT - NO HEADER/FOOTER")
print("=" * 80)

# Get SLIP/795
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("\n❌ ERROR: Could not find SLIP/795")
    import sys
    sys.exit(1)

print(f"\n✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")

# Get report model
report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']

# Generate report data
data = {
    'payslip_ids': payslip.ids,
    'currency_id': env.ref('base.USD').id,
}

print("\n🔍 Generating report data...")
report_values = report_model._get_report_values(payslip.ids, data=data)
print(f"   ✅ Report data generated")
print(f"      Reports: {len(report_values.get('reports', []))}")
print(f"      Currency: {report_values.get('currency').name}")

# Render HTML
print("\n🔍 Rendering HTML template...")
try:
    html = env['ir.qweb']._render(
        'ueipab_payroll_enhancements.liquidacion_breakdown_report',
        report_values
    )
    html_str = html.decode('utf-8') if isinstance(html, bytes) else str(html)
    print(f"   ✅ HTML rendered: {len(html_str):,} bytes")

    # Check for header/footer markers
    has_external_layout = 'web.external_layout' in html_str
    has_header_class = 'header' in html_str and 'company_logo' in html_str
    has_footer_class = 'footer' in html_str and 'page number' in html_str.lower()

    print(f"\n   🔍 Header/Footer Detection:")
    print(f"      external_layout template: {'❌ FOUND (bad)' if has_external_layout else '✅ NOT FOUND (good)'}")
    print(f"      Company header elements: {'❌ FOUND (bad)' if has_header_class else '✅ NOT FOUND (good)'}")
    print(f"      Footer elements: {'❌ FOUND (bad)' if has_footer_class else '✅ NOT FOUND (good)'}")

    # Check for our content
    has_title = 'RELACIÓN DE LIQUIDACIÓN' in html_str
    has_employee = 'VIRGINIA VERDE' in html_str
    has_declaration = 'El suscrito trabajador' in html_str
    has_signatures = 'Firma del Trabajador' in html_str

    print(f"\n   🔍 Content Verification:")
    print(f"      Report title: {'✅' if has_title else '❌'}")
    print(f"      Employee name: {'✅' if has_employee else '❌'}")
    print(f"      Declaration text: {'✅' if has_declaration else '❌'}")
    print(f"      Signatures section: {'✅' if has_signatures else '❌'}")

    # Save HTML
    with open('/tmp/liquidacion_no_header.html', 'w', encoding='utf-8') as f:
        f.write(html_str)
    print(f"\n   💾 Saved HTML to: /tmp/liquidacion_no_header.html")

    # Check HTML structure
    has_html_container = 'html_container' in html_str
    print(f"\n   🔍 Structure Check:")
    print(f"      html_container: {'✅' if has_html_container else '❌'}")

except Exception as e:
    print(f"   ❌ HTML render ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test via wizard (proper flow)
print("\n🔍 Testing via Wizard...")
try:
    wizard = env['liquidacion.breakdown.wizard'].create({
        'payslip_ids': [(6, 0, payslip.ids)],
        'currency_id': env.ref('base.USD').id,
    })

    action = wizard.action_print_pdf()
    print(f"   ✅ Wizard action successful")
    print(f"      Action type: {action['type']}")
    print(f"      Report name: {action['report_name']}")

except Exception as e:
    print(f"   ❌ Wizard ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Expected results:")
print("  ✅ HTML renders without errors")
print("  ✅ NO external_layout found")
print("  ✅ NO company header/footer elements")
print("  ✅ Report content present (title, employee, declaration, signatures)")
print("  ✅ Wizard flow works")
print("\nTo view HTML: docker cp odoo-dev-web:/tmp/liquidacion_no_header.html .")
print("=" * 80)

env.cr.commit()
