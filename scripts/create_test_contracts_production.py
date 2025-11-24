# -*- coding: utf-8 -*-
"""
Create Test Contracts in Production
====================================
Creates 5 test contracts using V2 salary structure and fields.

Usage: Run via Odoo shell in production container
  docker exec -i ueipab17 odoo shell -d DB_UEIPAB --no-http < script.py

Author: Technical Team
Date: 2025-11-24
"""
from datetime import date

print("="*80)
print("CREATING TEST CONTRACTS IN PRODUCTION")
print("="*80)

# Get models
Employee = env['hr.employee']
Contract = env['hr.contract']
Structure = env['hr.payroll.structure']

# Get VE_PAYROLL_V2 structure
ve_payroll = Structure.search([('code', '=', 'VE_PAYROLL_V2')], limit=1)
if not ve_payroll:
    print("❌ ERROR: VE_PAYROLL_V2 structure not found!")
    raise Exception("VE_PAYROLL_V2 structure not found")

print(f"✅ Found structure: {ve_payroll.name} (ID: {ve_payroll.id})")

# Test contract data from testing database
# 5 employees with valid VAT IDs
TEST_CONTRACTS = [
    {
        'vat': 'V8478634',  # ARCIDES ARZOLA
        'date_start': '2023-09-01',
        'ueipab_salary_v2': 285.39,
        'ueipab_bonus_v2': 249.52,
        'ueipab_extrabonus_v2': 0.0,
        'cesta_ticket_usd': 40.0,
        'ueipab_ari_withholding_rate': 1.0,
        'ueipab_original_hire_date': '2022-08-01',
    },
    {
        'vat': 'V17870047',  # AUDREY GARCIA
        'date_start': '2023-09-01',
        'ueipab_salary_v2': 107.65,
        'ueipab_bonus_v2': 122.74,
        'ueipab_extrabonus_v2': 0.0,
        'cesta_ticket_usd': 40.0,
        'ueipab_ari_withholding_rate': 0.0,
        'ueipab_original_hire_date': '2009-09-01',
    },
    {
        'vat': 'V29807160',  # CAMILA ROSSATO
        'date_start': '2023-09-11',
        'ueipab_salary_v2': 163.42,
        'ueipab_bonus_v2': 135.66,
        'ueipab_extrabonus_v2': 0.0,
        'cesta_ticket_usd': 40.0,
        'ueipab_ari_withholding_rate': 1.0,
        'ueipab_original_hire_date': '2023-09-11',
    },
    {
        'vat': 'V13753290',  # DIXIA BELLORIN
        'date_start': '2023-09-01',
        'ueipab_salary_v2': 127.66,
        'ueipab_bonus_v2': 139.67,
        'ueipab_extrabonus_v2': 0.0,
        'cesta_ticket_usd': 40.0,
        'ueipab_ari_withholding_rate': 0.0,
        'ueipab_original_hire_date': '2012-09-01',
    },
    {
        'vat': 'V30712714',  # ALEJANDRA LOPEZ
        'date_start': '2023-09-11',
        'ueipab_salary_v2': 146.19,
        'ueipab_bonus_v2': 198.83,
        'ueipab_extrabonus_v2': 42.58,
        'cesta_ticket_usd': 40.0,
        'ueipab_ari_withholding_rate': 1.0,
        'ueipab_original_hire_date': '2023-09-11',
    },
]

print(f"\n[Creating {len(TEST_CONTRACTS)} test contracts...]")

created_count = 0
skipped_count = 0

for data in TEST_CONTRACTS:
    # Find employee by VAT
    emp = Employee.search([('identification_id', '=', data['vat'])], limit=1)
    if not emp:
        print(f"  ❌ Employee not found: {data['vat']}")
        continue

    print(f"\n  Processing: {emp.name} ({data['vat']})...")

    # Check if contract already exists
    existing = Contract.search([
        ('employee_id', '=', emp.id),
        ('state', '=', 'open')
    ])
    if existing:
        print(f"    ⚠️  Contract already exists (ID: {existing.id})")
        skipped_count += 1
        continue

    # Parse dates
    date_start = date.fromisoformat(data['date_start'])
    original_hire = date.fromisoformat(data['ueipab_original_hire_date']) if data['ueipab_original_hire_date'] else None

    # Calculate wage (total compensation)
    wage = (
        data['ueipab_salary_v2'] +
        data['ueipab_bonus_v2'] +
        data['ueipab_extrabonus_v2'] +
        data['cesta_ticket_usd']
    )

    # Create contract
    contract_vals = {
        'name': f'Contrato - {emp.name}',
        'employee_id': emp.id,
        'date_start': date_start,
        'structure_type_id': ve_payroll.id,
        'wage': wage,
        'state': 'open',
        # V2 fields
        'ueipab_salary_v2': data['ueipab_salary_v2'],
        'ueipab_bonus_v2': data['ueipab_bonus_v2'],
        'ueipab_extrabonus_v2': data['ueipab_extrabonus_v2'],
        'cesta_ticket_usd': data['cesta_ticket_usd'],
        'ueipab_ari_withholding_rate': data['ueipab_ari_withholding_rate'],
    }

    # Add original hire date if available
    if original_hire:
        contract_vals['ueipab_original_hire_date'] = original_hire

    contract = Contract.create(contract_vals)
    print(f"    ✅ Created contract: ID {contract.id}")
    print(f"       Wage: ${wage:.2f}")
    print(f"       Structure: {ve_payroll.code}")
    created_count += 1

env.cr.commit()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"✅ Contracts created: {created_count}")
print(f"⚠️  Contracts skipped (existing): {skipped_count}")

# Verify contracts
print("\n" + "="*80)
print("VERIFICATION - Open Contracts with VE_PAYROLL_V2")
print("="*80)

contracts = Contract.search([
    ('state', '=', 'open'),
    ('structure_type_id', '=', ve_payroll.id)
])

for c in contracts:
    print(f"\n  {c.employee_id.name} (ID: {c.id})")
    print(f"    Wage: ${c.wage:.2f}")
    print(f"    ueipab_salary_v2: ${c.ueipab_salary_v2:.2f}" if c.ueipab_salary_v2 else "    ueipab_salary_v2: $0.00")
    print(f"    ueipab_bonus_v2: ${c.ueipab_bonus_v2:.2f}" if c.ueipab_bonus_v2 else "    ueipab_bonus_v2: $0.00")

print("\n" + "="*80)
print("✅ TEST CONTRACT CREATION COMPLETE!")
print("="*80)
print("\nNext step: Create a test payslip batch and generate payslips")
