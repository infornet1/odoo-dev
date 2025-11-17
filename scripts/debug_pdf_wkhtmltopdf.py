#!/usr/bin/env python3
"""
Debug wkhtmltopdf PDF generation issue
Compare working Prestaciones vs broken Liquidación
"""

print("=" * 80)
print("WKHTMLTOPDF PDF GENERATION DEBUG")
print("=" * 80)

# Get a liquidation payslip (SLIP/795 - VIRGINIA VERDE)
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("\n❌ ERROR: Could not find SLIP/795 (VIRGINIA VERDE)")
    import sys
    sys.exit(1)

print(f"\n✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")

# Get both report actions
liquidacion_report = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
prestaciones_report = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')

print(f"\n📄 Liquidación Report:")
print(f"   - ID: {liquidacion_report.id}")
print(f"   - Name: {liquidacion_report.name}")
print(f"   - Model: {liquidacion_report.model}")
print(f"   - Report Name: {liquidacion_report.report_name}")
print(f"   - Report Type: {liquidacion_report.report_type}")
print(f"   - Paperformat: {liquidacion_report.paperformat_id.name if liquidacion_report.paperformat_id else 'None'}")

print(f"\n📄 Prestaciones Report:")
print(f"   - ID: {prestaciones_report.id}")
print(f"   - Name: {prestaciones_report.name}")
print(f"   - Model: {prestaciones_report.model}")
print(f"   - Report Name: {prestaciones_report.report_name}")
print(f"   - Report Type: {prestaciones_report.report_type}")
print(f"   - Paperformat: {prestaciones_report.paperformat_id.name if prestaciones_report.paperformat_id else 'None'}")

# Check if templates exist
print("\n📋 Template Check:")

try:
    liq_template = env.ref('ueipab_payroll_enhancements.liquidacion_breakdown_report')
    print(f"   ✅ Liquidación template exists (ID: {liq_template.id})")
    print(f"      Type: {liq_template.type}")
    print(f"      Key: {liq_template.key}")
except Exception as e:
    print(f"   ❌ Liquidación template ERROR: {e}")

try:
    prest_template = env.ref('ueipab_payroll_enhancements.prestaciones_interest')
    print(f"   ✅ Prestaciones template exists (ID: {prest_template.id})")
    print(f"      Type: {prest_template.type}")
    print(f"      Key: {prest_template.key}")
except Exception as e:
    print(f"   ❌ Prestaciones template ERROR: {e}")

# Try to render HTML for both
print("\n🔍 Testing HTML Rendering:")

try:
    # Liquidación HTML
    liq_html = env['ir.qweb']._render(
        'ueipab_payroll_enhancements.liquidacion_breakdown_report',
        {
            'docs': payslip,
            'doc_ids': payslip.ids,
            'doc_model': 'hr.payslip',
            'data': {
                'payslip_ids': payslip.ids,
                'currency_id': env.ref('base.USD').id,
            },
            'currency': env.ref('base.USD'),
            'reports': env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']._get_liquidacion_data(payslip.ids, env.ref('base.USD')),
        }
    )
    liq_html_str = liq_html.decode('utf-8') if isinstance(liq_html, bytes) else str(liq_html)
    print(f"   ✅ Liquidación HTML: {len(liq_html_str):,} bytes")
    print(f"      Contains 'VIRGINIA VERDE': {'VIRGINIA VERDE' in liq_html_str}")
    print(f"      Contains 'RELACIÓN': {'RELACIÓN' in liq_html_str or 'RELACION' in liq_html_str}")

    # Save to file for inspection
    with open('/tmp/liquidacion_debug.html', 'w', encoding='utf-8') as f:
        f.write(liq_html_str)
    print(f"      💾 Saved to /tmp/liquidacion_debug.html")

except Exception as e:
    print(f"   ❌ Liquidación HTML ERROR: {e}")
    import traceback
    traceback.print_exc()

# Now try PDF generation using Odoo's internal method
print("\n🖨️  Testing PDF Generation:")

try:
    # Test Liquidación PDF
    pdf_content, pdf_type = liquidacion_report._render_qweb_pdf(
        payslip.ids,
        data={
            'payslip_ids': payslip.ids,
            'currency_id': env.ref('base.USD').id,
        }
    )

    print(f"   📄 Liquidación PDF: {len(pdf_content):,} bytes")

    # Save PDF
    with open('/tmp/liquidacion_debug.pdf', 'wb') as f:
        f.write(pdf_content)
    print(f"      💾 Saved to /tmp/liquidacion_debug.pdf")

    # Check PDF content structure
    if len(pdf_content) < 5000:
        print(f"      ⚠️  PDF is suspiciously small ({len(pdf_content)} bytes)")
        # Show first 500 characters in hex to see PDF structure
        import binascii
        print(f"      First 200 bytes (hex): {binascii.hexlify(pdf_content[:200])}")
    else:
        print(f"      ✅ PDF size looks reasonable")

except Exception as e:
    print(f"   ❌ Liquidación PDF ERROR: {e}")
    import traceback
    traceback.print_exc()

# Compare with Prestaciones (working report)
try:
    # Get prestaciones data from the report model
    prest_data = env['report.ueipab_payroll_enhancements.prestaciones_interest']._get_report_values(
        payslip.ids,
        data={
            'payslip_ids': payslip.ids,
            'currency_id': env.ref('base.USD').id,
        }
    )

    prest_html = env['ir.qweb']._render(
        'ueipab_payroll_enhancements.prestaciones_interest',
        prest_data
    )
    prest_html_str = prest_html.decode('utf-8') if isinstance(prest_html, bytes) else str(prest_html)
    print(f"\n   ✅ Prestaciones HTML: {len(prest_html_str):,} bytes")

    # Try Prestaciones PDF
    prest_pdf, prest_type = prestaciones_report._render_qweb_pdf(
        payslip.ids,
        data={
            'payslip_ids': payslip.ids,
            'currency_id': env.ref('base.USD').id,
        }
    )
    print(f"   ✅ Prestaciones PDF: {len(prest_pdf):,} bytes")

    with open('/tmp/prestaciones_debug.pdf', 'wb') as f:
        f.write(prest_pdf)
    print(f"      💾 Saved to /tmp/prestaciones_debug.pdf")

except Exception as e:
    print(f"   ❌ Prestaciones comparison ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Debug files saved:")
print("  - /tmp/liquidacion_debug.html")
print("  - /tmp/liquidacion_debug.pdf")
print("  - /tmp/prestaciones_debug.pdf")
print("\nTo view PDFs: docker cp odoo-dev-web:/tmp/liquidacion_debug.pdf .")
print("=" * 80)

env.cr.commit()
