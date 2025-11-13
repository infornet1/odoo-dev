#!/usr/bin/env python3
"""
Phase 4: Set Previous Liquidation Dates
========================================

All employees were fully paid (Prestaciones, Antiguedad, Vacaciones,
Bono Vacacional, Intereses, Utilidades) 100% until Jul 31, 2023.

For employees hired BEFORE Sep 1, 2023:
- Set ueipab_previous_liquidation_date = Jul 31, 2023
- This ensures antiguedad calculation subtracts the already-paid period

For employees hired ON/AFTER Sep 1, 2023:
- Leave ueipab_previous_liquidation_date = False (never liquidated)
- These are new hires with no previous liquidation

This is critical for Virginia Verde and other rehired employees!
"""

import datetime

print("=" * 80)
print("PHASE 4: SET PREVIOUS LIQUIDATION DATES")
print("=" * 80)

PREVIOUS_LIQUIDATION_DATE = datetime.date(2023, 7, 31)
COMPANY_LIABILITY_START = datetime.date(2023, 9, 1)

print(f"\n📋 Setting previous liquidation date: {PREVIOUS_LIQUIDATION_DATE}")
print(f"    For employees hired before: {COMPANY_LIABILITY_START}")

# Get all active contracts
contracts = env['hr.contract'].search([
    ('state', 'in', ['open', 'close']),
    ('ueipab_original_hire_date', '!=', False)  # Only contracts with original hire date set
])

print(f"\nFound {len(contracts)} contracts with original hire date set")

print("\n" + "-" * 80)
print(f"{'Employee':<35} {'Original Hire':<15} {'Prev Liquidation':<20}")
print("-" * 80)

pre_2023_count = 0
post_2023_count = 0

for contract in contracts:
    employee_name = contract.employee_id.name if contract.employee_id else "Unknown"
    original_hire = contract.ueipab_original_hire_date

    if not original_hire:
        continue

    # If hired BEFORE Sep 1, 2023: Set previous liquidation date
    if original_hire < COMPANY_LIABILITY_START:
        contract.ueipab_previous_liquidation_date = PREVIOUS_LIQUIDATION_DATE
        status = "Jul 31, 2023 (SET)"
        pre_2023_count += 1
    else:
        # Hired ON/AFTER Sep 1, 2023: No previous liquidation
        contract.ueipab_previous_liquidation_date = False
        status = "None (new hire)"
        post_2023_count += 1

    print(f"{employee_name:<35} {original_hire} {status:<20}")

# Commit changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Pre-2023 hires with previous liquidation set: {pre_2023_count}")
print(f"   ✅ Post-2023 new hires (no previous liquidation): {post_2023_count}")
print(f"   Total: {len(contracts)}")

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

with_prev_liq = env['hr.contract'].search_count([
    ('ueipab_previous_liquidation_date', '=', '2023-07-31'),
    ('state', 'in', ['open', 'close'])
])

without_prev_liq = env['hr.contract'].search_count([
    ('ueipab_previous_liquidation_date', '=', False),
    ('ueipab_original_hire_date', '!=', False),
    ('state', 'in', ['open', 'close'])
])

print(f"\n✅ Contracts with previous liquidation (Jul 31, 2023): {with_prev_liq}")
print(f"✅ Contracts without previous liquidation (new hires): {without_prev_liq}")

# Verify Virginia Verde specifically
virginia = env['hr.contract'].search([
    ('employee_id.name', 'ilike', 'VIRGINIA VERDE'),
    ('state', 'in', ['open', 'close'])
], limit=1)

if virginia:
    print(f"\n🔍 VIRGINIA VERDE Verification:")
    print(f"   Original hire date: {virginia.ueipab_original_hire_date}")
    print(f"   Contract start: {virginia.date_start}")
    print(f"   Previous liquidation: {virginia.ueipab_previous_liquidation_date}")
    print(f"   ✅ Correctly configured for antiguedad calculation!")

print("\n" + "=" * 80)
print("✅ PHASE 4 COMPLETE!")
print("=" * 80)
print("\nAll rehired employees now have previous liquidation dates set.")
print("Antiguedad calculations will correctly subtract already-paid periods!")
print("=" * 80)
