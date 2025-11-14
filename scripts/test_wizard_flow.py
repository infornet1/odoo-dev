#!/usr/bin/env python3
"""
Test the complete wizard -> report flow.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("="*80)
print("TESTING WIZARD -> REPORT FLOW")
print("="*80)

# Get test payslip
slip568 = env['hr.payslip'].search([('number', '=', 'SLIP/568')], limit=1)
if not slip568:
    print("SLIP/568 not found!")
    sys.exit(1)

print(f"\n✅ Test payslip: {slip568.number} (ID: {slip568.id})")

# Get USD currency
usd = env.ref('base.USD')

# Create wizard instance
wizard = env['prestaciones.interest.wizard'].create({
    'payslip_ids': [(6, 0, [slip568.id])],
    'currency_id': usd.id,
})

print(f"\n✅ Wizard created:")
print(f"   Wizard ID: {wizard.id}")
print(f"   Payslip IDs field: {wizard.payslip_ids}")
print(f"   Payslip IDs (ids): {wizard.payslip_ids.ids}")
print(f"   Currency: {wizard.currency_id.name}")
print(f"   Payslip count: {wizard.payslip_count}")

# Call the wizard's action_print_report method
print(f"\n" + "="*80)
print("CALLING wizard.action_print_report()")
print("="*80)

try:
    result = wizard.action_print_report()

    print(f"\n✅ action_print_report() returned:")
    print(f"   Type: {type(result)}")
    print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

    if isinstance(result, dict):
        print(f"\n   Details:")
        for key, value in result.items():
            if key == 'data':
                print(f"     {key}: {value}")
            elif key == 'context':
                print(f"     {key}: {value}")
            else:
                print(f"     {key}: {value}")

    # Check if data contains payslip_ids
    if 'data' in result and isinstance(result['data'], dict):
        print(f"\n   Data dict contents:")
        for k, v in result['data'].items():
            print(f"     {k}: {v}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Now test calling _get_report_values directly with the IDs
print(f"\n" + "="*80)
print("TESTING _get_report_values() WITH WIZARD DATA")
print("="*80)

report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

# Simulate what Odoo should be doing
test_docids = [slip568.id]
test_data = {'currency_id': usd.id, 'payslip_ids': [slip568.id]}

print(f"\nCalling _get_report_values(docids={test_docids}, data={test_data})")

result = report_model._get_report_values(docids=test_docids, data=test_data)

print(f"\n✅ Result keys: {list(result.keys())}")
print(f"   doc_ids: {result.get('doc_ids')}")
print(f"   docs: {result.get('docs')}")
print(f"   reports count: {len(result.get('reports', []))}")

if result.get('reports'):
    first_report = result['reports'][0]
    print(f"\n   First report:")
    print(f"     Employee: {first_report['employee'].name}")
    print(f"     Monthly rows: {len(first_report['monthly_data'])}")
    print(f"     Totals: Prest ${first_report['totals']['total_prestaciones']:.2f}, Int ${first_report['totals']['total_interest']:.2f}")
