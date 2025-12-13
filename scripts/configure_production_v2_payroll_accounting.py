#!/usr/bin/env python3
"""
Configure V2 Payroll Accounting for Production (DB_UEIPAB)

This script configures accounting for the VE_PAYROLL_V2 salary structure.
It must be run in the Odoo shell on the PRODUCTION database.

IMPORTANT: This script modifies PRODUCTION data. Review carefully before running.

Run with:
    docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http < configure_production_v2_payroll_accounting.py

Accounting Configuration:
    Debit:  5.1.01.10.001 (Nómina - Expense)
    Credit: 2.1.01.01.002 (Cuentas por pagar nómina - Liability)

Rules to configure:
    - VE_SSO_DED_V2 (SSO 4%)
    - VE_PARO_DED_V2 (PARO 0.5%)
    - VE_FAOV_DED_V2 (FAOV 1%)
    - VE_ARI_DED_V2 (ARI Variable %)
    - VE_OTHER_DED_V2 (Otras Deducciones)
    - VE_NET_V2 (Net Salary)

Date: 2025-12-13
Author: Claude Code
"""

print("=" * 80)
print("CONFIGURE V2 PAYROLL ACCOUNTING - PRODUCTION")
print("=" * 80)
print("\n⚠️  WARNING: This script modifies PRODUCTION database!")
print("=" * 80)

# Step 1: Verify we're on the right database
db_name = env.cr.dbname
print(f"\n📊 Connected to database: {db_name}")

if db_name != 'DB_UEIPAB':
    print(f"\n❌ ERROR: Expected DB_UEIPAB but connected to {db_name}")
    print("   Aborting to prevent accidental changes to wrong database.")
    exit(1)

print("✅ Confirmed: Connected to production database")

# Step 2: Find or create the credit account
print("\n" + "=" * 80)
print("STEP 1: VERIFY/CREATE ACCOUNTS")
print("=" * 80)

AccountAccount = env['account.account']

# Debit account (should exist)
debit_account = AccountAccount.search([('code', '=', '5.1.01.10.001')], limit=1)
if not debit_account:
    print("\n❌ ERROR: Debit account 5.1.01.10.001 not found!")
    print("   This account should already exist in production.")
    exit(1)

print(f"\n✅ Debit Account: {debit_account.code} (ID: {debit_account.id})")

# Credit account (may need to be created)
credit_account = AccountAccount.search([('code', '=', '2.1.01.01.002')], limit=1)

if not credit_account:
    print("\n⚠️  Credit account 2.1.01.01.002 not found. Creating...")

    # Find account type for Payables
    account_type = 'liability_payable'

    # Find a reference account to copy settings from
    ref_account = AccountAccount.search([('code', '=', '2.1.01.01.001')], limit=1)

    if not ref_account:
        ref_account = AccountAccount.search([('code', 'like', '2.1.01%')], limit=1)

    credit_account = AccountAccount.create({
        'code': '2.1.01.01.002',
        'name': 'Cuentas por pagar nómina de personal',
        'account_type': account_type,
        'reconcile': True,
        'company_id': ref_account.company_id.id if ref_account else 1,
    })

    env.cr.commit()
    print(f"   ✅ Created account: {credit_account.code} (ID: {credit_account.id})")
else:
    print(f"\n✅ Credit Account: {credit_account.code} (ID: {credit_account.id})")

# Step 3: Find V2 Payroll Structure
print("\n" + "=" * 80)
print("STEP 2: FIND V2 SALARY STRUCTURE")
print("=" * 80)

v2_struct = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)

if not v2_struct:
    print("\n❌ ERROR: VE_PAYROLL_V2 structure not found!")
    exit(1)

print(f"\n✅ Found: {v2_struct.name} (ID: {v2_struct.id})")
print(f"   Rules in structure: {len(v2_struct.rule_ids)}")

# Step 4: Configure accounting for deduction and net rules
print("\n" + "=" * 80)
print("STEP 3: CONFIGURE SALARY RULE ACCOUNTING")
print("=" * 80)

# Rules that need accounting (deductions + NET)
rules_to_configure = [
    'VE_SSO_DED_V2',
    'VE_PARO_DED_V2',
    'VE_FAOV_DED_V2',
    'VE_ARI_DED_V2',
    'VE_OTHER_DED_V2',
    'VE_NET_V2',
]

configured_count = 0
skipped_count = 0

for rule_code in rules_to_configure:
    rule = v2_struct.rule_ids.filtered(lambda r: r.code == rule_code)

    if not rule:
        # Try finding by code globally (may not be linked to structure yet)
        rule = env['hr.salary.rule'].search([('code', '=', rule_code)], limit=1)

    if not rule:
        print(f"\n⚠️  {rule_code}: NOT FOUND - skipping")
        skipped_count += 1
        continue

    # Check current config
    current_debit = rule.account_debit_id.code if rule.account_debit_id else None
    current_credit = rule.account_credit_id.code if rule.account_credit_id else None

    if current_debit == debit_account.code and current_credit == credit_account.code:
        print(f"\n✅ {rule_code}: Already configured correctly")
        continue

    # Update accounting
    rule.write({
        'account_debit_id': debit_account.id,
        'account_credit_id': credit_account.id,
    })

    print(f"\n✅ {rule_code}: Configured")
    print(f"   Debit:  {debit_account.code}")
    print(f"   Credit: {credit_account.code}")
    configured_count += 1

# Commit changes
env.cr.commit()

# Step 5: Verification
print("\n" + "=" * 80)
print("STEP 4: VERIFICATION")
print("=" * 80)

print(f"\n{'Rule Code':<22} {'Debit':<18} {'Credit':<18} {'Status'}")
print("-" * 75)

all_ok = True
for rule_code in rules_to_configure:
    rule = env['hr.salary.rule'].search([('code', '=', rule_code)], limit=1)

    if rule:
        debit = rule.account_debit_id.code if rule.account_debit_id else "NOT SET"
        credit = rule.account_credit_id.code if rule.account_credit_id else "NOT SET"

        if debit == '5.1.01.10.001' and credit == '2.1.01.01.002':
            status = "✅ OK"
        else:
            status = "❌ ISSUE"
            all_ok = False
    else:
        debit = "N/A"
        credit = "N/A"
        status = "⚠️ NOT FOUND"
        all_ok = False

    print(f"{rule_code:<22} {debit:<18} {credit:<18} {status}")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"\n📊 Results:")
print(f"   Rules configured: {configured_count}")
print(f"   Rules skipped:    {skipped_count}")
print(f"   Verification:     {'✅ ALL OK' if all_ok else '❌ ISSUES FOUND'}")

if all_ok:
    print(f"\n✅ V2 Payroll accounting configuration COMPLETE!")
    print(f"\n📝 Next steps:")
    print(f"   1. Test by creating a V2 payslip and confirming it")
    print(f"   2. Verify journal entry is created with correct accounts")
else:
    print(f"\n⚠️  Some issues found. Please review above output.")

print("\n" + "=" * 80)
