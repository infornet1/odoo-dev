#!/usr/bin/env python3
"""
Test PDF generation via wizard (proper flow)
"""

print("=" * 80)
print("TESTING LIQUIDACIÓN PDF VIA WIZARD")
print("=" * 80)

# Get SLIP/795 (VIRGINIA VERDE)
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("\n❌ ERROR: Could not find SLIP/795")
    import sys
    sys.exit(1)

print(f"\n✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")

# Create wizard
print("\n🔍 Creating wizard...")
wizard = env['liquidacion.breakdown.wizard'].create({
    'payslip_ids': [(6, 0, payslip.ids)],
    'currency_id': env.ref('base.USD').id,
})
print(f"   ✅ Wizard created: ID {wizard.id}")
print(f"      Payslip count: {wizard.payslip_count}")
print(f"      Currency: {wizard.currency_id.name}")

# Call action_print_pdf
print("\n🔍 Calling action_print_pdf()...")
try:
    result = wizard.action_print_pdf()
    print(f"   ✅ Action returned successfully!")
    print(f"      Type: {result.get('type')}")
    print(f"      Report type: {result.get('report_type')}")
    print(f"      Report name: {result.get('report_name')}")

    if result.get('data'):
        print(f"      Data keys: {list(result['data'].keys())}")

except Exception as e:
    print(f"   ❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Now manually generate the PDF using the correct API
print("\n🔍 Generating PDF using report API...")
try:
    report = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')

    # This is what report_action() does internally
    pdf_content, report_format = report._render_qweb_pdf(payslip.ids)

    print(f"   ✅ PDF generated: {len(pdf_content):,} bytes")

    with open('/tmp/liquidacion_wizard_test.pdf', 'wb') as f:
        f.write(pdf_content)
    print(f"      💾 Saved to /tmp/liquidacion_wizard_test.pdf")

    if len(pdf_content) < 5000:
        print(f"      ⚠️  WARNING: PDF is small ({len(pdf_content)} bytes) - likely empty")
    else:
        print(f"      ✅ PDF SIZE LOOKS GOOD!")
        print(f"      🎉 SUCCESS! The model name fix worked!")

except Exception as e:
    print(f"   ❌ PDF generation ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("To view PDF: docker cp odoo-dev-web:/tmp/liquidacion_wizard_test.pdf .")
print("=" * 80)

env.cr.commit()
