#!/usr/bin/env python3
"""
Compare Prestaciones (working) vs Liquidación (broken) report database records
"""

print("=" * 80)
print("COMPARING REPORT DATABASE RECORDS")
print("=" * 80)

# Get both reports
liq_report = env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
prest_report = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')

print("\n📊 LIQUIDACIÓN BREAKDOWN REPORT:")
print(f"   ID: {liq_report.id}")
print(f"   Name: {liq_report.name}")
print(f"   Model: {liq_report.model}")
print(f"   Report Name: {liq_report.report_name}")
print(f"   Report File: {liq_report.report_file}")
print(f"   Report Type: {liq_report.report_type}")
print(f"   Paperformat: {liq_report.paperformat_id.name if liq_report.paperformat_id else None}")
print(f"   Binding Model: {liq_report.binding_model_id.model if liq_report.binding_model_id else None}")
print(f"   Binding Type: {liq_report.binding_type}")
print(f"   Print Report Name: {liq_report.print_report_name}")

print("\n📊 PRESTACIONES INTEREST REPORT:")
print(f"   ID: {prest_report.id}")
print(f"   Name: {prest_report.name}")
print(f"   Model: {prest_report.model}")
print(f"   Report Name: {prest_report.report_name}")
print(f"   Report File: {prest_report.report_file}")
print(f"   Report Type: {prest_report.report_type}")
print(f"   Paperformat: {prest_report.paperformat_id.name if prest_report.paperformat_id else None}")
print(f"   Binding Model: {prest_report.binding_model_id.model if prest_report.binding_model_id else None}")
print(f"   Binding Type: {prest_report.binding_type}")
print(f"   Print Report Name: {prest_report.print_report_name}")

# Check if report models exist
print("\n🔍 CHECKING REPORT MODELS:")
try:
    liq_model = env['report.ueipab_payroll_enhancements.liquidacion_breakdown_report']
    print(f"   ✅ Liquidación model exists: {liq_model._name}")
except Exception as e:
    print(f"   ❌ Liquidación model ERROR: {e}")

try:
    prest_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
    print(f"   ✅ Prestaciones model exists: {prest_model._name}")
except Exception as e:
    print(f"   ❌ Prestaciones model ERROR: {e}")

# Check templates
print("\n🔍 CHECKING TEMPLATES:")
try:
    liq_template = env.ref('ueipab_payroll_enhancements.liquidacion_breakdown_report')
    print(f"   ✅ Liquidación template: {liq_template.key}")
except Exception as e:
    print(f"   ❌ Liquidación template ERROR: {e}")

try:
    prest_template = env.ref('ueipab_payroll_enhancements.prestaciones_interest')
    print(f"   ✅ Prestaciones template: {prest_template.key}")
except Exception as e:
    print(f"   ❌ Prestaciones template ERROR: {e}")

# Test actual PDF generation via web UI simulation
print("\n🔍 SIMULATING WEB UI REPORT GENERATION:")

payslip = env['hr.payslip'].search([('number', '=', 'SLIP/795')], limit=1)

if payslip:
    # Test Prestaciones (working)
    print("\n   Testing Prestaciones (should work)...")
    try:
        wizard_prest = env['prestaciones.interest.wizard'].create({
            'payslip_ids': [(6, 0, payslip.ids)],
            'currency_id': env.ref('base.USD').id,
        })
        action_prest = wizard_prest.action_print_report()
        print(f"      ✅ Prestaciones action returned: {action_prest['type']}")

        # Try to render it
        prest_report_obj = env['ir.actions.report']._get_report_from_name('ueipab_payroll_enhancements.prestaciones_interest')
        print(f"      ✅ Got report object: {prest_report_obj.name}")

    except Exception as e:
        print(f"      ❌ Prestaciones ERROR: {e}")

    # Test Liquidación (broken?)
    print("\n   Testing Liquidación...")
    try:
        wizard_liq = env['liquidacion.breakdown.wizard'].create({
            'payslip_ids': [(6, 0, payslip.ids)],
            'currency_id': env.ref('base.USD').id,
        })
        action_liq = wizard_liq.action_print_report()
        print(f"      ✅ Liquidación action returned: {action_liq['type']}")

        # Try to render it
        liq_report_obj = env['ir.actions.report']._get_report_from_name('ueipab_payroll_enhancements.liquidacion_breakdown_report')
        print(f"      ✅ Got report object: {liq_report_obj.name}")

    except Exception as e:
        print(f"      ❌ Liquidación ERROR: {e}")

print("\n" + "=" * 80)

env.cr.commit()
