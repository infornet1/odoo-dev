#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Accounting Ledger for Monthly Interest Postings

Verify if monthly interest accruals are actually posted to the general ledger.
"""

import sys

print("=" * 80)
print("CHECKING GENERAL LEDGER FOR INTEREST ACCRUAL ENTRIES")
print("=" * 80)
print()

# Search for account moves related to prestaciones interest
# Common account patterns: interest expense, accrued interest, etc.

# Check if there are any journal entries with "interes" or "prestaciones" in reference
print("Searching for journal entries with 'interes' or 'prestaciones' keywords...")
print()

interest_moves = env['account.move'].search([
    '|',
    ('ref', 'ilike', 'interes'),
    ('ref', 'ilike', 'prestacion')
], limit=50, order='date desc')

print(f"Found {len(interest_moves)} journal entries with related keywords")
print()

if interest_moves:
    print("Recent entries:")
    print("-" * 80)
    for move in interest_moves[:10]:
        print(f"Date: {move.date} | Ref: {move.ref or 'N/A'} | Journal: {move.journal_id.name}")
    print()

# Check for specific account codes that might hold prestaciones interest
print("Checking common liability accounts for prestaciones...")
print()

# Search for accounts with "prestacion" in name
prestacion_accounts = env['account.account'].search([
    ('name', 'ilike', 'prestacion')
])

print(f"Found {len(prestacion_accounts)} accounts with 'prestacion' in name:")
for acc in prestacion_accounts:
    print(f"  - {acc.code} | {acc.name}")
print()

# Search for accounts with "interes" in name
interes_accounts = env['account.account'].search([
    ('name', 'ilike', 'interes')
])

print(f"Found {len(interes_accounts)} accounts with 'interes' in name:")
for acc in interes_accounts[:10]:
    print(f"  - {acc.code} | {acc.name}")
print()

print("=" * 80)
print("CHECKING PAYSLIP ACCOUNTING INTEGRATION")
print("=" * 80)
print()

# Find SLIP/802
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/802')], limit=1)

if payslip:
    print(f"Payslip: {payslip.number}")
    print(f"State: {payslip.state}")

    # Check if payslip has accounting entries
    if hasattr(payslip, 'move_id') and payslip.move_id:
        print(f"Accounting Entry: {payslip.move_id.name}")
        print(f"Entry Date: {payslip.move_id.date}")
        print(f"Entry State: {payslip.move_id.state}")
        print()
        print("Journal Entry Lines:")
        print("-" * 80)
        for line in payslip.move_id.line_ids:
            print(f"  Account: {line.account_id.code} - {line.account_id.name}")
            print(f"  Debit: {line.debit:.2f} | Credit: {line.credit:.2f}")
            print(f"  Label: {line.name}")
            print()
    else:
        print("⚠️  No accounting entry found for this payslip")
        print("   Payslip may not be integrated with accounting module")
print()

print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()
print("QUESTION: Are monthly interest accruals posted to ledger?")
print()
print("Scenario 1: YES - Monthly accruals ARE posted")
print("  - Each month, interest is calculated and posted in VEB")
print("  - Prestaciones Interest Report shows SUM of these ledger entries")
print("  - Relación Report MUST use same accrual calculation")
print("  ✅ Both reports match ledger reality")
print()
print("Scenario 2: NO - Monthly accruals are NOT posted")
print("  - Interest is only calculated/posted at liquidation time")
print("  - Prestaciones Interest Report is just informational breakdown")
print("  - Exchange rate strategy depends on company policy:")
print("    Option A: Use month-by-month rates (theoretical accrual)")
print("    Option B: Use single rate at liquidation time (actual posting)")
print()
print("📝 RECOMMENDATION:")
print("   Check with accounting team:")
print("   1. Is interest accrued monthly in the ledger?")
print("   2. What exchange rates are used for monthly accruals?")
print("   3. Should liquidation report match monthly ledger totals?")
print()

print("=" * 80)
print("Analysis complete!")
print("=" * 80)
