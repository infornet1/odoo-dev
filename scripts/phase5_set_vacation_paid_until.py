#!/usr/bin/env python3
"""
Phase 5: Set Vacation Paid Until Dates
=======================================

All employees received Vacaciones and Bono Vacacional payments on Aug 1, 2024
for the period Sep 1, 2023 - Jul 31, 2024 (fiscal year 2023-2024).

Set ueipab_vacation_paid_until = Aug 1, 2024 for all employees.

This ensures liquidation calculations only include vacation accrued AFTER
Aug 1, 2024 (i.e., Aug 2, 2024 to liquidation date).

Exception: Employees hired AFTER Aug 1, 2024 should not have this set,
as they never received an Aug 1 payment.
"""

import datetime

print("=" * 80)
print("PHASE 5: SET VACATION PAID UNTIL DATES")
print("=" * 80)

VACATION_PAYMENT_DATE = datetime.date(2024, 8, 1)

print(f"\n📋 Setting vacation paid until: {VACATION_PAYMENT_DATE}")
print(f"    For employees hired before or on: {VACATION_PAYMENT_DATE}")

# Get all active contracts with original hire date set
contracts = env['hr.contract'].search([
    ('state', 'in', ['open', 'close']),
    ('ueipab_original_hire_date', '!=', False)
])

print(f"\nFound {len(contracts)} contracts with original hire date set")

print("\n" + "-" * 80)
print(f"{'Employee':<35} {'Hire Date':<15} {'Vacation Paid Until':<20}")
print("-" * 80)

eligible_count = 0
too_new_count = 0

for contract in contracts:
    employee_name = contract.employee_id.name if contract.employee_id else "Unknown"
    hire_date = contract.ueipab_original_hire_date

    if not hire_date:
        continue

    # If hired ON or BEFORE Aug 1, 2024: Set vacation paid until
    if hire_date <= VACATION_PAYMENT_DATE:
        contract.ueipab_vacation_paid_until = VACATION_PAYMENT_DATE
        status = "Aug 1, 2024 (SET)"
        eligible_count += 1
    else:
        # Hired AFTER Aug 1, 2024: No vacation payment received yet
        contract.ueipab_vacation_paid_until = False
        status = "None (too new)"
        too_new_count += 1

    print(f"{employee_name:<35} {hire_date} {status:<20}")

# Commit changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Employees with vacation paid until Aug 1, 2024: {eligible_count}")
print(f"   ⚠️  Employees hired after Aug 1, 2024 (no payment): {too_new_count}")
print(f"   Total: {len(contracts)}")

# Verification
print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

with_vacation_paid = env['hr.contract'].search_count([
    ('ueipab_vacation_paid_until', '=', '2024-08-01'),
    ('state', 'in', ['open', 'close'])
])

without_vacation_paid = env['hr.contract'].search_count([
    ('ueipab_vacation_paid_until', '=', False),
    ('ueipab_original_hire_date', '>', '2024-08-01'),
    ('state', 'in', ['open', 'close'])
])

print(f"\n✅ Contracts with vacation paid until Aug 1, 2024: {with_vacation_paid}")
print(f"✅ Contracts without (hired after Aug 1, 2024): {without_vacation_paid}")

# Verify key employees
print(f"\n🔍 KEY EMPLOYEES Verification:")

virginia = env['hr.contract'].search([
    ('employee_id.name', 'ilike', 'VIRGINIA VERDE'),
    ('state', 'in', ['open', 'close'])
], limit=1)

if virginia:
    print(f"\nVirginia Verde:")
    print(f"   Original hire: {virginia.ueipab_original_hire_date}")
    print(f"   Vacation paid until: {virginia.ueipab_vacation_paid_until}")
    print(f"   ✅ Aug 1-Jul 31, 2025 period will be calculated")

gabriel = env['hr.contract'].search([
    ('employee_id.name', 'ilike', 'GABRIEL'),
    ('state', 'in', ['open', 'close'])
], limit=1)

if gabriel:
    print(f"\nGabriel España:")
    print(f"   Original hire: {gabriel.ueipab_original_hire_date}")
    print(f"   Vacation paid until: {gabriel.ueipab_vacation_paid_until}")
    print(f"   ✅ Aug 1-Jul 31, 2025 period will be calculated")

print("\n" + "=" * 80)
print("✅ PHASE 5 COMPLETE!")
print("=" * 80)
print("\nAll eligible employees have vacation paid until date set.")
print("Liquidation will calculate vacation accrued from Aug 2, 2024 forward!")
print("=" * 80)
