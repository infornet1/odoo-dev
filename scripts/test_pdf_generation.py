#!/usr/bin/env python3
"""
Test actual PDF generation from report.
"""

import sys
import base64

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("="*80)
print("TESTING PDF GENERATION")
print("="*80)

# Get test payslip
slip568 = env['hr.payslip'].search([('number', '=', 'SLIP/568')], limit=1)
print(f"\n✅ Payslip: {slip568.number} (ID: {slip568.id})")

# Get report action
report_action = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')
print(f"✅ Report action: {report_action.name}")

# Get USD
usd = env.ref('base.USD')

# Prepare data (same as wizard)
data = {
    'currency_id': usd.id,
    'payslip_ids': [slip568.id],
}

print(f"\n" + "="*80)
print("GENERATING PDF...")
print("="*80)

try:
    # Use _render_qweb_pdf with correct Odoo 17 signature
    pdf_content, output_format = report_action._render_qweb_pdf(
        report_ref='ueipab_payroll_enhancements.prestaciones_interest',
        res_ids=[slip568.id],
        data=data
    )

    print(f"\n✅ PDF Generated!")
    print(f"   Format: {output_format}")
    print(f"   Size: {len(pdf_content)} bytes")

    if len(pdf_content) > 0:
        print(f"   First 100 bytes: {pdf_content[:100]}")

        # Save to file
        output_path = '/opt/odoo-dev/prestaciones_test.pdf'
        with open(output_path, 'wb') as f:
            f.write(pdf_content)
        print(f"\n✅ PDF saved to: {output_path}")
        print(f"   You can download and view it to see if data is there")
    else:
        print(f"\n❌ PDF is EMPTY!")

except Exception as e:
    print(f"\n❌ ERROR generating PDF: {e}")
    import traceback
    traceback.print_exc()
