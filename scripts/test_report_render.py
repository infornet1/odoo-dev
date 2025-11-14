#!/usr/bin/env python3
"""
Test Report PDF Rendering
==========================

Actually try to render the PDF and catch any errors.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("TESTING PDF RENDERING")
print("="*80)
print()

# Find a liquidation payslip
Payslip = env['hr.payslip']
payslip = Payslip.search([
    ('struct_id.name', '=', 'Liquidación Venezolana'),
    ('state', 'in', ['draft', 'done'])
], limit=1)

if not payslip:
    print("❌ No liquidation payslips found!")
    import sys
    sys.exit(1)

print(f"✅ Testing with: {payslip.number} - {payslip.employee_id.name}")
print()

# Get the report action
Report = env['ir.actions.report']
report = Report.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

if not report:
    print("❌ Report action not found!")
    import sys
    sys.exit(1)

print(f"✅ Report action found: {report.name}")
print(f"   Report Name: {report.report_name}")
print()

# Prepare data
Currency = env['res.currency']
usd = Currency.search([('name', '=', 'USD')], limit=1)

data = {
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
}

# Try to render the PDF
print("Attempting to render PDF...")
print()

try:
    pdf_content, report_format = report._render_qweb_pdf(
        report.report_name,
        res_ids=[payslip.id],
        data=data
    )

    pdf_size = len(pdf_content) if pdf_content else 0
    print(f"✅ PDF generated successfully!")
    print(f"   Size: {pdf_size:,} bytes")

    if pdf_size < 1000:
        print(f"   ⚠️  PDF is suspiciously small (< 1KB) - might be blank")
    else:
        print(f"   ✅ PDF size looks reasonable")

except Exception as e:
    print(f"❌ ERROR rendering PDF: {e}")
    import traceback
    traceback.print_exc()
    print()

    # Try to render HTML to see the error
    print()
    print("Attempting to render HTML to see template errors...")
    print()
    try:
        html_content, html_format = report._render_qweb_html(
            report.report_name,
            res_ids=[payslip.id],
            data=data
        )
        html_size = len(html_content) if html_content else 0
        print(f"✅ HTML rendered: {html_size:,} bytes")

        # Show first 500 chars of HTML
        if html_content:
            html_str = html_content.decode('utf-8') if isinstance(html_content, bytes) else str(html_content)
            print()
            print("HTML Preview (first 500 chars):")
            print("-" * 80)
            print(html_str[:500])
            print("-" * 80)
    except Exception as e2:
        print(f"❌ ERROR rendering HTML: {e2}")
        import traceback
        traceback.print_exc()

print()
print("="*80)
