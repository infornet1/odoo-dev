#!/usr/bin/env python3
"""
Test what variables are available in report context.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

# Get test payslip
slip568 = env['hr.payslip'].search([('number', '=', 'SLIP/568')], limit=1)
if not slip568:
    print("SLIP/568 not found!")
    sys.exit(1)

print("Testing report context variables...")
print(f"Payslip: {slip568.number}")

# Get report and generate
report_action = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')
usd = env.ref('base.USD')

# Call _get_report_values to see what's returned
report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

result = report_model._get_report_values(
    docids=[slip568.id],
    data={'currency_id': usd.id}
)

print("\n" + "="*80)
print("VARIABLES RETURNED BY _get_report_values():")
print("="*80)
for key, value in result.items():
    print(f"\n{key}:")
    if key == 'reports' and isinstance(value, list):
        print(f"  Type: list, Length: {len(value)}")
        if value:
            print(f"  First item keys: {list(value[0].keys())}")
            print(f"  First item employee: {value[0].get('employee')}")
            print(f"  First item monthly_data count: {len(value[0].get('monthly_data', []))}")
    elif key == 'docs':
        print(f"  Type: {type(value)}, Count: {len(value)}")
        print(f"  First doc: {value[0] if value else 'None'}")
    else:
        print(f"  Type: {type(value)}, Value: {value}")

print("\n" + "="*80)
print("CHECKING IF 'reports' IS A PROPER LIST:")
print("="*80)
reports = result.get('reports', [])
print(f"Is list: {isinstance(reports, list)}")
print(f"Length: {len(reports)}")
print(f"Bool value: {bool(reports)}")

if reports:
    print("\nFirst report:")
    first = reports[0]
    print(f"  Type: {type(first)}")
    print(f"  Keys: {first.keys()}")
    print(f"  Employee type: {type(first.get('employee'))}")
    print(f"  Employee name: {first.get('employee').name if first.get('employee') else 'None'}")
