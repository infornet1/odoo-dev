#!/usr/bin/env python3
"""
Phase 1: Fix Contract Dates (Sep 2024 → Sep 2023)
==================================================

CRITICAL FIX: All employee contracts incorrectly show date_start = Sep 1, 2024
This causes 12-month underpayment on ALL liquidations.

Fix: Update all contracts to date_start = Sep 1, 2023 (company liability start)

Database: ueipab (development)
Module: Direct database update via Odoo ORM
"""

import datetime

print("=" * 80)
print("PHASE 1: FIX CONTRACT DATES (Sep 2024 → Sep 2023)")
print("=" * 80)
print("\n⚠️  CRITICAL FIX: Correcting 12-month underpayment issue")
print("    All liquidations currently missing 1 year of service\n")

# Find all contracts with Sep 1, 2024 start date
contracts_to_fix = env['hr.contract'].search([('date_start', '=', '2024-09-01')])

print(f"Found {len(contracts_to_fix)} contracts with date_start = 2024-09-01")

if len(contracts_to_fix) == 0:
    print("\n✅ No contracts need fixing - all dates already correct")
    print("=" * 80)
else:
    print("\n" + "-" * 80)
    print(f"{'Employee':<35} {'Current Date':<15} {'New Date':<15}")
    print("-" * 80)

    for contract in contracts_to_fix:
        employee_name = contract.employee_id.name if contract.employee_id else "Unknown"
        print(f"{employee_name:<35} {contract.date_start} → 2023-09-01")

    print("\n" + "=" * 80)
    print("UPDATING CONTRACT DATES...")
    print("=" * 80)

    # Update all contracts
    updated_count = 0
    for contract in contracts_to_fix:
        contract.date_start = datetime.date(2023, 9, 1)
        updated_count += 1

    # Commit changes
    env.cr.commit()

    print(f"\n✅ Successfully updated {updated_count} contracts")

    # Verify the update
    print("\nVerifying changes...")
    verification = env['hr.contract'].search([('date_start', '=', '2023-09-01')])
    print(f"✅ Verification: {len(verification)} contracts now have date_start = 2023-09-01")

    # Check if any contracts still have the old date
    old_date_check = env['hr.contract'].search([('date_start', '=', '2024-09-01')])
    if len(old_date_check) == 0:
        print(f"✅ Verification: 0 contracts remain with old date - SUCCESS!")
    else:
        print(f"⚠️  Warning: {len(old_date_check)} contracts still have old date")

    print("\n" + "=" * 80)
    print("PHASE 1 COMPLETE ✅")
    print("=" * 80)
    print("\nAll employee contracts now correctly show:")
    print("  Company liability start: September 1, 2023")
    print("\n✅ This fixes the 12-month underpayment issue!")
    print("=" * 80)
