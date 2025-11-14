#!/usr/bin/env python3
"""
Save Test PDF to File
======================

Generate PDF and save to /tmp so user can download it.

Author: Claude Code
Date: 2025-11-13
"""

import base64

print("="*80)
print("SAVING TEST PDF")
print("="*80)
print()

# Find a liquidation payslip
Payslip = env['hr.payslip']
payslip = Payslip.search([
    ('struct_id.name', '=', 'Liquidación Venezolana'),
    ('state', 'in', ['draft', 'done'])
], limit=1)

print(f"Testing with: {payslip.number} - {payslip.employee_id.name}")
print()

# Get the report
Report = env['ir.actions.report']
report = Report.search([('name', '=', 'Prestaciones Soc. Intereses')], limit=1)

# Prepare data
Currency = env['res.currency']
usd = Currency.search([('name', '=', 'USD')], limit=1)

data = {
    'currency_id': usd.id,
    'currency_name': 'USD',
    'payslip_ids': [payslip.id],
}

# Generate PDF
print("Generating PDF...")
pdf_content, _ = report._render_qweb_pdf(
    report.report_name,
    res_ids=[payslip.id],
    data=data
)

# Save to file
output_file = '/tmp/prestaciones_test.pdf'
with open(output_file, 'wb') as f:
    f.write(pdf_content)

print(f"✅ PDF saved to: {output_file}")
print(f"   Size: {len(pdf_content):,} bytes")
print()
print("You can download it with:")
print(f"   docker cp odoo-dev-web:{output_file} ./prestaciones_test.pdf")
print()
print("="*80)
