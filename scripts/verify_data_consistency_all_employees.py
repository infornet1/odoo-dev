#!/usr/bin/env python3
"""
Data Consistency Verification - ALL Employees
Compares V1 payslips (NOVIEMBRE15-2) with current V2 contract values
to identify which employees had contract changes after the batch was paid.

CRITICAL: This identifies data consistency issues before V2 production use.
"""

from datetime import date

print("=" * 80)
print("DATA CONSISTENCY VERIFICATION - ALL EMPLOYEES")
print("=" * 80)

# Find NOVIEMBRE15-2 batch
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("\n❌ ERROR: NOVIEMBRE15-2 batch not found")
    exit(1)

print(f"\n📋 Reference Batch: {batch.name}")
print(f"   Date: {batch.date_start} to {batch.date_end}")

# Calculate period days
date_from = batch.date_start
date_to = batch.date_end
period_days = (date_to - date_from).days + 1
proration = period_days / 30.0

print(f"   Period Days: {period_days}")
print(f"   Proration: {proration:.4f}")

# Get all active contracts with V2 fields
contracts = env['hr.contract'].search([
    ('state', '=', 'open'),
    ('ueipab_salary_v2', '>', 0)
])

print(f"\n📊 Total Active Contracts with V2 Fields: {len(contracts)}")

# Classification buckets
perfect_match = []
minor_diff = []
significant_diff = []
no_v1_payslip = []

print("\n" + "=" * 80)
print("PROCESSING ALL EMPLOYEES...")
print("=" * 80)

for contract in contracts:
    employee = contract.employee_id

    # Find V1 payslip from NOVIEMBRE15-2
    v1_payslip = env['hr.payslip'].search([
        ('payslip_run_id', '=', batch.id),
        ('employee_id', '=', employee.id)
    ], limit=1)

    if not v1_payslip:
        no_v1_payslip.append({
            'name': employee.name,
            'contract_id': contract.id,
        })
        continue

    # Get V1 values
    v1_gross_line = v1_payslip.line_ids.filtered(lambda l: l.code == 'VE_GROSS')
    v1_gross = v1_gross_line.total if v1_gross_line else 0.0

    v1_net_line = v1_payslip.line_ids.filtered(lambda l: l.code == 'VE_NET')
    v1_net = v1_net_line.total if v1_net_line else 0.0

    # Calculate V2 gross (prorated)
    salary_v2 = contract.ueipab_salary_v2 or 0.0
    extrabonus_v2 = contract.ueipab_extrabonus_v2 or 0.0
    bonus_v2 = contract.ueipab_bonus_v2 or 0.0
    cesta_ticket = contract.cesta_ticket_usd or 0.0

    v2_gross = (salary_v2 + extrabonus_v2 + bonus_v2 + cesta_ticket) * proration

    # Calculate difference
    diff_gross = v2_gross - v1_gross
    diff_pct = (diff_gross / v1_gross * 100) if v1_gross > 0 else 0.0

    # Classify
    employee_data = {
        'name': employee.name,
        'contract_id': contract.id,
        'payslip_id': v1_payslip.id,
        'v1_gross': v1_gross,
        'v2_gross': v2_gross,
        'diff_gross': diff_gross,
        'diff_pct': diff_pct,
        'v1_net': v1_net,
        'salary_v2': salary_v2,
        'extrabonus_v2': extrabonus_v2,
        'bonus_v2': bonus_v2,
        'cesta_ticket': cesta_ticket,
    }

    if abs(diff_gross) < 0.50:
        perfect_match.append(employee_data)
    elif abs(diff_gross) < 5.00:
        minor_diff.append(employee_data)
    else:
        significant_diff.append(employee_data)

# Print results
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)

total_processed = len(perfect_match) + len(minor_diff) + len(significant_diff)
print(f"\n📊 Total Employees Processed: {total_processed}")
print(f"   ✅ Perfect Match (<$0.50 diff):    {len(perfect_match):>3} ({100*len(perfect_match)/total_processed:.1f}%)")
print(f"   ⚠️  Minor Difference (<$5 diff):    {len(minor_diff):>3} ({100*len(minor_diff)/total_processed:.1f}%)")
print(f"   🔴 Significant Difference (>=$5):  {len(significant_diff):>3} ({100*len(significant_diff)/total_processed:.1f}%)")
print(f"   ❌ No V1 Payslip Found:            {len(no_v1_payslip):>3}")

# Perfect matches
if perfect_match:
    print("\n" + "=" * 80)
    print(f"✅ PERFECT MATCHES - {len(perfect_match)} employees")
    print("=" * 80)
    print(f"{'Employee':<30} {'V1 Gross':>10} {'V2 Gross':>10} {'Diff':>8}")
    print("─" * 80)
    for emp in perfect_match[:10]:  # Show first 10
        print(f"{emp['name']:<30} ${emp['v1_gross']:>9.2f} ${emp['v2_gross']:>9.2f} ${emp['diff_gross']:>7.2f}")
    if len(perfect_match) > 10:
        print(f"... and {len(perfect_match) - 10} more")

# Minor differences
if minor_diff:
    print("\n" + "=" * 80)
    print(f"⚠️  MINOR DIFFERENCES - {len(minor_diff)} employees")
    print("=" * 80)
    print(f"{'Employee':<30} {'V1 Gross':>10} {'V2 Gross':>10} {'Diff':>8} {'%':>7}")
    print("─" * 80)
    for emp in minor_diff:
        print(f"{emp['name']:<30} ${emp['v1_gross']:>9.2f} ${emp['v2_gross']:>9.2f} ${emp['diff_gross']:>7.2f} {emp['diff_pct']:>6.1f}%")

# Significant differences - DETAILED BREAKDOWN
if significant_diff:
    print("\n" + "=" * 80)
    print(f"🔴 SIGNIFICANT DIFFERENCES - {len(significant_diff)} employees")
    print("=" * 80)
    print("\n⚠️  These employees likely had contract changes after NOVIEMBRE15-2 was paid")
    print("   Review carefully before proceeding with V2 testing!\n")

    for emp in significant_diff:
        print("─" * 80)
        print(f"👤 {emp['name']} (Contract ID: {emp['contract_id']}, Payslip: SLIP/{emp['payslip_id']})")
        print(f"\n   V1 PAYSLIP (NOVIEMBRE15-2 - Already Paid):")
        print(f"      Gross:  ${emp['v1_gross']:>8.2f}")
        print(f"      Net:    ${emp['v1_net']:>8.2f}")

        print(f"\n   V2 CONTRACT (Current Spreadsheet Values):")
        print(f"      Salary V2:      ${emp['salary_v2']:>8.2f} × {proration:.4f} = ${emp['salary_v2']*proration:>8.2f}")
        print(f"      ExtraBonus V2:  ${emp['extrabonus_v2']:>8.2f} × {proration:.4f} = ${emp['extrabonus_v2']*proration:>8.2f}")
        print(f"      Bonus V2:       ${emp['bonus_v2']:>8.2f} × {proration:.4f} = ${emp['bonus_v2']*proration:>8.2f}")
        print(f"      Cesta Ticket:   ${emp['cesta_ticket']:>8.2f} × {proration:.4f} = ${emp['cesta_ticket']*proration:>8.2f}")
        print(f"      {'─' * 45}")
        print(f"      V2 Gross:       ${emp['v2_gross']:>8.2f}")

        print(f"\n   📊 COMPARISON:")
        print(f"      V1 vs V2 Difference: ${emp['diff_gross']:>8.2f} ({emp['diff_pct']:>6.1f}%)")
        print(f"      Status: {'⬆️ INCREASE' if emp['diff_gross'] > 0 else '⬇️ DECREASE'}")

# No V1 payslip
if no_v1_payslip:
    print("\n" + "=" * 80)
    print(f"❌ NO V1 PAYSLIP FOUND - {len(no_v1_payslip)} employees")
    print("=" * 80)
    print("   These employees have V2 contracts but no NOVIEMBRE15-2 payslip")
    print("   They may be new hires or were not in the batch\n")
    for emp in no_v1_payslip:
        print(f"   - {emp['name']} (Contract ID: {emp['contract_id']})")

# Final recommendation
print("\n" + "=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)

if significant_diff:
    print(f"\n⚠️  CRITICAL: {len(significant_diff)} employees have SIGNIFICANT differences (>=$5)")
    print("\n   These are likely legitimate contract updates (salary increases, etc.)")
    print("   However, you should verify EACH ONE before proceeding with V2 testing:")
    print("\n   1. Check if they received salary increases after Nov 15")
    print("   2. Verify spreadsheet '15nov2025' tab has correct current values")
    print("   3. Confirm these differences are expected")
    print("\n   ❌ DO NOT proceed with V2 testing until verified!")
else:
    print("\n✅ EXCELLENT: No significant contract changes detected")
    print("   All employees show consistent values between V1 payslips and V2 contracts")
    print("   Safe to proceed with V2 testing!")

if minor_diff:
    print(f"\n⚠️  INFO: {len(minor_diff)} employees have minor differences (<$5)")
    print("   These are likely rounding differences or small adjustments")
    print("   Review recommended but not critical")

print("\n" + "=" * 80)
print("DATA CONSISTENCY CHECK COMPLETE")
print("=" * 80)
