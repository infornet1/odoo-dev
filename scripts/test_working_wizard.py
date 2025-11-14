#!/usr/bin/env python3
"""
Test the WORKING Payroll Disbursement wizard to see what it returns.
"""

import sys

env = globals().get('env')
if not env:
    print("ERROR: Must run via odoo shell")
    sys.exit(1)

print("="*80)
print("TESTING WORKING DISBURSEMENT WIZARD")
print("="*80)

# Find a batch with payslips
batch = env['hr.payslip.run'].search([('state', '!=', 'close')], limit=1)
if not batch:
    print("No batches found")
    sys.exit(1)

print(f"\n✅ Found batch: {batch.name} (ID: {batch.id})")

# Create disbursement wizard
wizard = env['payroll.disbursement.wizard'].create({
    'filter_type': 'batch',
    'batch_id': batch.id,
})

print(f"\n✅ Wizard created:")
print(f"   Filter type: {wizard.filter_type}")
print(f"   Batch: {wizard.batch_id.name}")
print(f"   Payslip count: {wizard.payslip_count}")

# Get the payslips this wizard will use
payslips = wizard._get_filtered_payslips()
print(f"   Payslip IDs: {payslips.ids[:5]}...")  # First 5

# Call action_print_report
print(f"\n" + "="*80)
print("CALLING wizard.action_print_report()")
print("="*80)

result = wizard.action_print_report()

print(f"\n✅ Returned:")
print(f"   Type: {type(result)}")
print(f"   Keys: {list(result.keys())}")

for key, value in result.items():
    if key == 'data' and isinstance(value, dict):
        print(f"\n   {key}:")
        for k, v in value.items():
            if k == 'payslip_ids':
                print(f"     {k}: [{len(v)} IDs]")
            else:
                print(f"     {k}: {v}")
    else:
        print(f"   {key}: {value}")
