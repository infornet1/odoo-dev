#!/usr/bin/env python3
"""
Test PDF generation after model name fix
"""

print("=" * 80)
print("TESTING LIQUIDACIÓN BREAKDOWN PDF - AFTER FIX")
print("=" * 80)

# Get SLIP/795 (VIRGINIA VERDE)
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if not payslip:
    print("\n❌ ERROR: Could not find SLIP/795")
    import sys
    sys.exit(1)

print(f"\n✅ Found payslip: {payslip.number} - {payslip.employee_id.name}")

# Test 1: Check if report model exists
print("\n🔍 Test 1: Verifying Report Model Registration")
try:
    report_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
    print("   ✅ Report model exists!")
except Exception as e:
    print(f"   ❌ Report model ERROR: {e}")

# Test 2: Get report action
print("\n🔍 Test 2: Getting Report Action")
try:
    report_action = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
    print(f"   ✅ Report action found: {report_action.name}")
    print(f"      Report name: {report_action.report_name}")
    print(f"      Model: {report_action.model}")
except Exception as e:
    print(f"   ❌ Report action ERROR: {e}")

# Test 3: Get report data from model
print("\n🔍 Test 3: Generating Report Data")
try:
    data = {
        'payslip_ids': payslip.ids,
        'currency_id': env.ref('base.USD').id,
    }

    report_values = report_model._get_report_values(payslip.ids, data=data)

    print(f"   ✅ Report data generated!")
    print(f"      Reports count: {len(report_values.get('reports', []))}")
    print(f"      Currency: {report_values.get('currency').name}")

    if report_values.get('reports'):
        first_report = report_values['reports'][0]
        print(f"      Employee: {first_report.get('employee').name}")
        print(f"      Benefits count: {len(first_report.get('benefits', []))}")
        print(f"      Deductions count: {len(first_report.get('deductions', []))}")

except Exception as e:
    print(f"   ❌ Report data ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Render HTML
print("\n🔍 Test 4: Rendering HTML Template")
try:
    html = env['ir.qweb']._render(
        'ueipab_payroll_enhancements.liquidacion_breakdown_report',
        report_values
    )
    html_str = html.decode('utf-8') if isinstance(html, bytes) else str(html)
    print(f"   ✅ HTML rendered: {len(html_str):,} bytes")
    print(f"      Contains 'VIRGINIA VERDE': {'VIRGINIA VERDE' in html_str}")
    print(f"      Contains 'RELACIÓN': {'RELACIÓN' in html_str or 'RELACION' in html_str}")

    with open('/tmp/liquidacion_fixed.html', 'w', encoding='utf-8') as f:
        f.write(html_str)
    print(f"      💾 Saved to /tmp/liquidacion_fixed.html")

except Exception as e:
    print(f"   ❌ HTML render ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Generate PDF
print("\n🔍 Test 5: Generating PDF (The Moment of Truth!)")
try:
    pdf_content, pdf_type = report_action._render_qweb_pdf(payslip.ids, data=data)

    print(f"   📄 PDF Generated: {len(pdf_content):,} bytes")

    with open('/tmp/liquidacion_fixed.pdf', 'wb') as f:
        f.write(pdf_content)
    print(f"      💾 Saved to /tmp/liquidacion_fixed.pdf")

    # Check PDF size
    if len(pdf_content) < 5000:
        print(f"      ⚠️  WARNING: PDF is small ({len(pdf_content)} bytes)")
        print(f"      This might indicate an empty PDF (previous issue)")
    else:
        print(f"      ✅ PDF SIZE LOOKS GOOD! ({len(pdf_content):,} bytes)")
        print(f"      🎉 SUCCESS! The PDF should contain actual content!")

except Exception as e:
    print(f"   ❌ PDF generation ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Test wizard flow
print("\n🔍 Test 6: Testing Wizard Flow (Complete Integration)")
try:
    wizard = env['liquidacion.breakdown.wizard'].create({
        'payslip_ids': [(6, 0, payslip.ids)],
        'currency_id': env.ref('base.USD').id,
    })
    print(f"   ✅ Wizard created: {wizard.id}")

    # Generate report via wizard
    result = wizard.action_print_report()
    print(f"   ✅ Wizard action result: {result.get('type')}")
    print(f"      Report name: {result.get('report_name')}")

except Exception as e:
    print(f"   ❌ Wizard flow ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("Files saved:")
print("  - /tmp/liquidacion_fixed.html")
print("  - /tmp/liquidacion_fixed.pdf")
print("\nTo view PDF:")
print("  docker cp odoo-dev-web:/tmp/liquidacion_fixed.pdf .")
print("  open liquidacion_fixed.pdf  # or xdg-open on Linux")
print("=" * 80)

env.cr.commit()
