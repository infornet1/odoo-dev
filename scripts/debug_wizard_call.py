#!/usr/bin/env python3
"""
Debug Wizard Report Call
=========================

Simulate what happens when user clicks the button in the wizard.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("DEBUGGING WIZARD REPORT CALL")
print("="*80)
print()

# Create a wizard instance like the UI does
Wizard = env['prestaciones.interest.wizard']
Currency = env['res.currency']
Payslip = env['hr.payslip']

# Find a payslip
payslip = Payslip.search([
    ('struct_id.name', '=', 'Liquidación Venezolana'),
    ('state', 'in', ['draft', 'done'])
], limit=1)

usd = Currency.search([('name', '=', 'USD')], limit=1)

print(f"Creating wizard with payslip: {payslip.number}")
print(f"Currency: {usd.name}")
print()

# Create wizard instance
wizard = Wizard.create({
    'payslip_ids': [(6, 0, [payslip.id])],
    'currency_id': usd.id,
})

print(f"✅ Wizard created (ID: {wizard.id})")
print(f"   Payslip IDs: {wizard.payslip_ids.ids}")
print(f"   Payslip count: {wizard.payslip_count}")
print(f"   Currency: {wizard.currency_id.name}")
print()

# Call action_print_report like the button does
print("Calling wizard.action_print_report()...")
print()

try:
    result = wizard.action_print_report()

    print("✅ Method returned:")
    print(f"   Type: {type(result)}")
    print(f"   Keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    print()

    if isinstance(result, dict):
        for key, value in result.items():
            if key == 'data':
                print(f"   {key}:")
                for dk, dv in value.items():
                    print(f"      {dk}: {dv}")
            else:
                print(f"   {key}: {value}")

    print()

    # Now try to actually render using the same approach
    if isinstance(result, dict) and result.get('type') == 'ir.actions.report':
        print("Attempting to render PDF using wizard's return value...")

        Report = env['ir.actions.report']
        report = Report.browse(result.get('id'))

        if report:
            data = result.get('data', {})
            docids = result.get('context', {}).get('active_ids', [])

            print(f"   Report: {report.name}")
            print(f"   Data passed: {data}")
            print(f"   Doc IDs: {docids}")
            print()

            # Try rendering
            pdf_content, _ = report._render_qweb_pdf(
                report.report_name,
                res_ids=docids,
                data=data
            )

            print(f"✅ PDF rendered: {len(pdf_content):,} bytes")

            if len(pdf_content) < 1000:
                print("   ⚠️  PDF is too small - likely blank!")
            else:
                print("   ✅ PDF size looks good!")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*80)
