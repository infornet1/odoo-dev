#!/usr/bin/env python3
"""
GENERATED SCRIPT: Phase 1+3 Contract Date Updates
=================================================

Auto-generated from spreadsheet data.
Updates contract.date_start and ueipab_original_hire_date based on:
- Pre-Sep 2023 hires: date_start = 2023-09-01
- Post-Sep 2023 hires: date_start = actual hire date
- ALL: ueipab_original_hire_date = actual hire date
"""

import datetime

print("=" * 80)
print("PHASE 1+3: CONTRACT DATE UPDATES (Generated Script)")
print("=" * 80)

COMPANY_LIABILITY_START = datetime.date(2023, 9, 1)

# Employee hire dates from spreadsheet (44 employees)
EMPLOYEE_HIRE_DATES = {
    'ARCIDES ARZOLA': datetime.date(2022, 8, 1),
    'NORKA LA ROSA': datetime.date(2022, 9, 1),
    'DAVID HERNANDEZ': datetime.date(2022, 10, 17),
    'MIRIAN HERNANDEZ': datetime.date(2020, 1, 23),
    'JOSEFINA RODRIGUEZ': datetime.date(2020, 8, 1),
    'NELCI BRITO': datetime.date(1985, 9, 11),
    'JESSICA BOLIVAR': datetime.date(2016, 1, 11),
    'LORENA REYES': datetime.date(2022, 8, 1),
    'GABRIEL ESPAÑA': datetime.date(2022, 7, 27),
    'SERGIO MANEIRO': datetime.date(2019, 9, 10),
    'ANDRES MORALES': datetime.date(2023, 10, 2),
    'PABLO NAVARRO': datetime.date(2022, 10, 24),
    'MARIELA PRADO': datetime.date(2017, 9, 1),
    'ZARETH FARIAS': datetime.date(2015, 9, 1),
    'MAGYELYS MATA': datetime.date(2003, 9, 1),
    'TERESA MARIN': datetime.date(2006, 10, 5),
    'HEYDI RON': datetime.date(2010, 3, 28),
    'YUDELIS BRITO': datetime.date(2006, 9, 1),
    'DIXIA BELLORIN': datetime.date(2012, 9, 1),
    'GABRIELA URAY': datetime.date(2022, 10, 4),
    'YARITZA BRUCES': datetime.date(2019, 9, 2),
    'ELIS MEJIAS': datetime.date(2006, 9, 1),
    'VIRGINIA VERDE': datetime.date(2019, 10, 1),
    'LEIDYMAR ARAY': datetime.date(2021, 4, 21),
    'LUISA ELENA ABREU': datetime.date(2019, 2, 1),
    'AUDREY GARCIA': datetime.date(2009, 9, 1),
    'RAFAEL PEREZ': datetime.date(2022, 11, 7),
    'ISMARY ARCILA': datetime.date(2023, 9, 20),
    'FLORMAR HERNANDEZ': datetime.date(2023, 9, 26),
    'GLADYS BRITO CALZADILLA': datetime.date(2020, 9, 4),
    'STEFANY ROMERO': datetime.date(2023, 9, 11),
    'CAMILA ROSSATO': datetime.date(2023, 9, 11),
    'RAMON BELLO': datetime.date(2023, 9, 11),
    'MARIA NIETO': datetime.date(2024, 9, 2),
    'JOSE HERNANDEZ': datetime.date(2022, 11, 18),
    'NIDYA LIRA': datetime.date(2022, 9, 5),
    'EMILIO ISEA': datetime.date(2023, 10, 2),
    'ALEJANDRA LOPEZ': datetime.date(2020, 9, 1),
    'GIOVANNI VEZZA': datetime.date(2024, 9, 2),
    'MARIA FIGUERA': datetime.date(2024, 9, 9),
    'DANIEL BONGIANNI': datetime.date(2025, 7, 22),
    'ROBERT QUIJADA': datetime.date(2025, 9, 1),
    'JESUS DI CESARE': datetime.date(2025, 10, 1),
    'LUIS RODRIGUEZ': datetime.date(2025, 10, 15),
}

print(f"\n📊 Loaded {len(EMPLOYEE_HIRE_DATES)} employees from spreadsheet")

# Get all active contracts
contracts = env['hr.contract'].search([('state', 'in', ['open', 'close'])])
print(f"Found {len(contracts)} active contracts in Odoo\n")

print("-" * 80)
print(f"{'Employee':<35} {'Orig Hire':<12} {'Contract Start':<15} {'Status':<12}")
print("-" * 80)

updated_count = 0
not_found_count = 0

for contract in contracts:
    employee_name = contract.employee_id.name.upper() if contract.employee_id else "UNKNOWN"

    if employee_name not in EMPLOYEE_HIRE_DATES:
        print(f"{employee_name:<35} {'N/A':<12} {'-':<15} ⚠️  NOT IN SHEET")
        not_found_count += 1
        continue

    original_hire_date = EMPLOYEE_HIRE_DATES[employee_name]

    # Determine contract start date
    if original_hire_date < COMPANY_LIABILITY_START:
        new_contract_start = COMPANY_LIABILITY_START
        status = "Pre-2023"
    else:
        new_contract_start = original_hire_date
        status = "Post-2023"

    # Update fields
    contract.date_start = new_contract_start
    contract.ueipab_original_hire_date = original_hire_date

    print(f"{employee_name:<35} {original_hire_date} {new_contract_start} {status:<12}")
    updated_count += 1

# Commit changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Updated: {updated_count}")
print(f"   ⚠️  Not in sheet: {not_found_count}")
print(f"   Total contracts: {len(contracts)}")

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

pre_count = env['hr.contract'].search_count([
    ('date_start', '=', '2023-09-01'),
    ('state', 'in', ['open', 'close'])
])

post_count = env['hr.contract'].search_count([
    ('date_start', '>', '2023-09-01'),
    ('state', 'in', ['open', 'close'])
])

with_original = env['hr.contract'].search_count([
    ('ueipab_original_hire_date', '!=', False),
    ('state', 'in', ['open', 'close'])
])

print(f"\n✅ Pre-2023 hires (date_start = Sep 1, 2023): {pre_count}")
print(f"✅ Post-2023 hires (date_start > Sep 1, 2023): {post_count}")
print(f"✅ With original hire date set: {with_original}")

print("\n" + "=" * 80)
print("✅ PHASE 1+3 COMPLETE!")
print("=" * 80)
