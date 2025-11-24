# -*- coding: utf-8 -*-
"""
Create Test Payslips in Production
===================================
Creates a test batch and generates payslips for the 5 test employees.

Usage: Run via Odoo shell in production container
  docker exec -i ueipab17 odoo shell -d DB_UEIPAB --no-http < script.py

Author: Technical Team
Date: 2025-11-24
"""
from datetime import date

print("="*80)
print("CREATING TEST PAYSLIP BATCH IN PRODUCTION")
print("="*80)

# Get models
PayslipRun = env['hr.payslip.run']
Payslip = env['hr.payslip']
Contract = env['hr.contract']
Structure = env['hr.payroll.structure']

# Get VE_PAYROLL_V2 structure
ve_payroll = Structure.search([('code', '=', 'VE_PAYROLL_V2')], limit=1)
if not ve_payroll:
    print("❌ ERROR: VE_PAYROLL_V2 structure not found!")
    raise Exception("VE_PAYROLL_V2 structure not found")

print(f"✅ Found structure: {ve_payroll.name} (ID: {ve_payroll.id})")

# Create batch for November 2025 (1st-15th)
batch_name = "TEST_PAYROLL_V2_2025_11_01-15"
date_start = date(2025, 11, 1)
date_end = date(2025, 11, 15)

# Check if batch already exists
existing_batch = PayslipRun.search([('name', '=', batch_name)], limit=1)
if existing_batch:
    print(f"\n⚠️  Batch already exists: {batch_name} (ID: {existing_batch.id})")
    batch = existing_batch
else:
    batch = PayslipRun.create({
        'name': batch_name,
        'date_start': date_start,
        'date_end': date_end,
    })
    print(f"\n✅ Created batch: {batch_name} (ID: {batch.id})")

# Get contracts with VE_PAYROLL_V2
contracts = Contract.search([
    ('state', '=', 'open'),
    ('structure_type_id', '=', ve_payroll.id)
])

print(f"\n[Generating payslips for {len(contracts)} employees...]")

created_count = 0
skipped_count = 0

for contract in contracts:
    emp = contract.employee_id

    # Check if payslip already exists for this employee in this batch
    existing_slip = Payslip.search([
        ('employee_id', '=', emp.id),
        ('payslip_run_id', '=', batch.id)
    ])
    if existing_slip:
        print(f"\n  ⚠️  Payslip already exists for {emp.name}")
        skipped_count += 1
        continue

    print(f"\n  Processing: {emp.name}...")

    # Create payslip
    payslip = Payslip.create({
        'name': f'SLIP/{emp.name}/{batch_name}',
        'employee_id': emp.id,
        'contract_id': contract.id,
        'struct_id': ve_payroll.id,
        'date_from': date_start,
        'date_to': date_end,
        'payslip_run_id': batch.id,
    })

    print(f"    ✅ Created payslip: {payslip.name} (ID: {payslip.id})")

    # Compute payslip
    try:
        payslip.compute_sheet()
        print(f"    ✅ Computed payslip")

        # Show key lines
        for line in payslip.line_ids.filtered(lambda l: l.code in ('VE_SALARY_V2', 'VE_GROSS_V2', 'VE_NET_V2')):
            print(f"       {line.code}: ${line.total:.2f}")

        created_count += 1
    except Exception as e:
        print(f"    ❌ Error computing: {str(e)}")

env.cr.commit()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"✅ Payslips created and computed: {created_count}")
print(f"⚠️  Payslips skipped (existing): {skipped_count}")
print(f"📊 Batch: {batch.name} (ID: {batch.id})")

# Show batch totals
print("\n" + "="*80)
print("BATCH DETAILS")
print("="*80)

# Reload batch to get updated data
batch = PayslipRun.browse(batch.id)
print(f"\n  Batch: {batch.name}")
print(f"  Period: {batch.date_start} to {batch.date_end}")
print(f"  Payslips: {len(batch.slip_ids)}")

print("\n  Employee Payslips:")
for slip in batch.slip_ids:
    net_line = slip.line_ids.filtered(lambda l: l.code == 'VE_NET_V2')
    net_amount = net_line[0].total if net_line else 0.0
    gross_line = slip.line_ids.filtered(lambda l: l.code == 'VE_GROSS_V2')
    gross_amount = gross_line[0].total if gross_line else 0.0
    print(f"    {slip.employee_id.name}")
    print(f"      Gross: ${gross_amount:.2f}, Net: ${net_amount:.2f}")

print("\n" + "="*80)
print("✅ TEST PAYSLIP GENERATION COMPLETE!")
print("="*80)
print("\nNext steps:")
print("1. Review payslips in Odoo UI")
print("2. Validate calculations match testing database")
print("3. Confirm payslips if correct")
