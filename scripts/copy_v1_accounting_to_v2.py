#!/usr/bin/env python3
"""
Copy V1 Accounting Configuration to V2 Salary Rules

This script copies payroll accounting settings from V1 (UEIPAB_VE) to V2 (VE_PAYROLL_V2).
Enables V2 payslips to generate journal entries using same GL accounts as V1.

Migration Mapping:
------------------
VE_SSO_DED    → VE_SSO_DED_V2
VE_FAOV_DED   → VE_FAOV_DED_V2
VE_PARO_DED   → VE_PARO_DED_V2
VE_ARI_DED    → VE_ARI_DED_V2 (use same accounts as other deductions)
VE_NET        → VE_NET_V2

Earnings rules remain blank (matching V1 pattern).
"""

print("=" * 80)
print("COPY V1 ACCOUNTING TO V2 SALARY RULES")
print("=" * 80)

# Find V1 and V2 structures
v1_struct = env['hr.payroll.structure'].search([('code', '=', 'UEIPAB_VE')], limit=1)
v2_struct = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)

if not v1_struct:
    print("\n❌ ERROR: V1 structure (UEIPAB_VE) not found")
    exit(1)

if not v2_struct:
    print("\n❌ ERROR: V2 structure (VE_PAYROLL_V2) not found")
    exit(1)

print(f"\n✅ V1 Structure: {v1_struct.name} (ID: {v1_struct.id})")
print(f"✅ V2 Structure: {v2_struct.name} (ID: {v2_struct.id})")

# Get reference accounts from V1 SSO rule
v1_sso = v1_struct.rule_ids.filtered(lambda r: r.code == 'VE_SSO_DED')

if not v1_sso:
    print("\n❌ ERROR: V1 VE_SSO_DED rule not found")
    exit(1)

if not v1_sso.account_debit_id or not v1_sso.account_credit_id:
    print("\n❌ ERROR: V1 VE_SSO_DED has no accounting configured")
    exit(1)

ref_debit = v1_sso.account_debit_id
ref_credit = v1_sso.account_credit_id

print(f"\n📊 Reference Accounts (from V1 VE_SSO_DED):")
print(f"   Debit:  {ref_debit.code} - {ref_debit.name}")
print(f"   Credit: {ref_credit.code} - {ref_credit.name}")

# Define mapping
mappings = [
    ('VE_SSO_DED', 'VE_SSO_DED_V2', 'SSO 4.5%'),
    ('VE_FAOV_DED', 'VE_FAOV_DED_V2', 'FAOV 1%'),
    ('VE_PARO_DED', 'VE_PARO_DED_V2', 'PARO 0.5%'),
    ('VE_ARI_DED', 'VE_ARI_DED_V2', 'ARI Variable %'),
    ('VE_NET', 'VE_NET_V2', 'Net Salary'),
]

print("\n" + "=" * 80)
print("APPLYING ACCOUNTING CONFIGURATION TO V2 RULES")
print("=" * 80)

updates = []

for v1_code, v2_code, description in mappings:
    print(f"\n📝 {v2_code} ({description}):")

    # Get V1 rule (for reference)
    v1_rule = v1_struct.rule_ids.filtered(lambda r: r.code == v1_code)

    # Get V2 rule
    v2_rule = v2_struct.rule_ids.filtered(lambda r: r.code == v2_code)

    if not v2_rule:
        print(f"   ❌ V2 rule not found: {v2_code}")
        continue

    # Determine accounts to use
    if v1_rule and v1_rule.account_debit_id and v1_rule.account_credit_id:
        # Copy from V1 rule
        debit_account = v1_rule.account_debit_id
        credit_account = v1_rule.account_credit_id
        print(f"   ✅ Copying from V1 {v1_code}")
    else:
        # Use reference accounts (for VE_ARI_DED which has no V1 config)
        debit_account = ref_debit
        credit_account = ref_credit
        print(f"   ⚠️  V1 rule has no accounting, using reference accounts")

    # Check current V2 configuration
    current_debit = v2_rule.account_debit_id
    current_credit = v2_rule.account_credit_id

    if current_debit or current_credit:
        print(f"   ⚠️  V2 already has accounting configured:")
        if current_debit:
            print(f"      Current Debit:  {current_debit.code}")
        if current_credit:
            print(f"      Current Credit: {current_credit.code}")

    # Update V2 rule
    v2_rule.write({
        'account_debit_id': debit_account.id,
        'account_credit_id': credit_account.id,
    })

    print(f"   ✅ Debit:  {debit_account.code} - {debit_account.name}")
    print(f"   ✅ Credit: {credit_account.code} - {credit_account.name}")

    updates.append({
        'v2_rule': v2_rule,
        'debit': debit_account,
        'credit': credit_account,
    })

# Commit changes
env.cr.commit()

print("\n" + "=" * 80)
print("✅ ACCOUNTING CONFIGURATION APPLIED SUCCESSFULLY")
print("=" * 80)

print(f"\n📊 Summary: {len(updates)} V2 rules configured")

# Verify configuration
print("\n" + "=" * 80)
print("VERIFICATION - V2 RULES WITH ACCOUNTING")
print("=" * 80)

print(f"\n{'V2 Rule Code':<25} {'Debit Account':<30} {'Credit Account':<30}")
print("-" * 90)

for update in updates:
    rule = update['v2_rule']
    debit = update['debit']
    credit = update['credit']
    print(f"{rule.code:<25} {debit.code:<30} {credit.code:<30}")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)

print("""
✅ V2 payroll accounting is now configured!

To test:
1. Create a V2 payslip via Odoo UI
2. Select employee with V2 contract (Rafael Perez)
3. Compute payslip
4. Confirm payslip (state = Done)
5. Check journal entry created (should appear in Accounting)

Expected Journal Entry:
- Debit  5.1.01.10.001 (Nómina): Total of all deductions + net
- Credit 2.1.01.01.002 (Cuentas por pagar): Total of all deductions + net

NOTE: Earnings rules (VE_SALARY_V2, VE_BONUS_V2, etc.) have NO accounting
      configured, matching V1 pattern. Only deductions and NET create journal
      entries.
""")

print("=" * 80)
