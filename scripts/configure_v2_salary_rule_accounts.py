#!/usr/bin/env python3
"""
Configure accounting for V2 salary rules
Based on patterns from PAYROLL_ACCOUNTING_FIX.md and V2_PAYROLL_IMPLEMENTATION.md

V2 Payroll Rules:    Debit 5.1.01.10.001 / Credit 2.1.01.01.002
V2 Liquidation Rules: Debit 5.1.01.10.010 / Credit 2.1.01.10.005
"""

print("=" * 80)
print("CONFIGURING V2 SALARY RULE ACCOUNTING")
print("=" * 80)

# Get account objects
AccountAccount = env['account.account']
SalaryRule = env['hr.salary.rule']

# Find accounts
payroll_expense = AccountAccount.search([('code', '=', '5.1.01.10.001')], limit=1)
transition_payable = AccountAccount.search([('code', '=', '2.1.01.01.002')], limit=1)
liquidation_expense = AccountAccount.search([('code', '=', '5.1.01.10.010')], limit=1)
liquidation_payable = AccountAccount.search([('code', '=', '2.1.01.10.005')], limit=1)

print(f"\nAccounts found:")
print(f"  Payroll Expense:       {payroll_expense.code} - {payroll_expense.name} (ID: {payroll_expense.id})")
print(f"  Transition Payable:    {transition_payable.code} - {transition_payable.name} (ID: {transition_payable.id})")
print(f"  Liquidation Expense:   {liquidation_expense.code} - {liquidation_expense.name} (ID: {liquidation_expense.id})")
print(f"  Liquidation Payable:   {liquidation_payable.code} - {liquidation_payable.name} (ID: {liquidation_payable.id})")

# Configuration mapping
# NOTE: Only deductions and NET should post to accounting
# Individual earnings (SALARY, BONUS, etc.) and summary totals (GROSS, TOTAL_DED) should NOT post
rule_configs = {
    # V2 Payroll Deductions (these should post)
    'VE_SSO_DED_V2': {
        'debit': payroll_expense.id,
        'credit': transition_payable.id,
        'type': 'deduction'
    },
    'VE_FAOV_DED_V2': {
        'debit': payroll_expense.id,
        'credit': transition_payable.id,
        'type': 'deduction'
    },
    'VE_PARO_DED_V2': {
        'debit': payroll_expense.id,
        'credit': transition_payable.id,
        'type': 'deduction'
    },
    'VE_ARI_DED_V2': {
        'debit': payroll_expense.id,
        'credit': transition_payable.id,
        'type': 'deduction'
    },
    'VE_NET_V2': {
        'debit': payroll_expense.id,
        'credit': transition_payable.id,
        'type': 'net'
    },

    # V2 Liquidation Rules (Liquidation expense)
    'LIQUID_SERVICE_MONTHS_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
    'LIQUID_DAILY_SALARY_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
    'LIQUID_INTEGRAL_DAILY_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
    'LIQUID_ANTIGUEDAD_DAILY_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
    'LIQUID_VACATION_PREPAID_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
    'LIQUID_NET_V2': {
        'debit': liquidation_expense.id,
        'credit': liquidation_payable.id,
        'type': 'liquidation'
    },
}

print(f"\n" + "=" * 80)
print("APPLYING CONFIGURATION")
print("=" * 80)

configured_count = 0
for rule_code, config in rule_configs.items():
    rule = SalaryRule.search([('code', '=', rule_code)], limit=1)
    if rule:
        rule.write({
            'account_debit_id': config['debit'],
            'account_credit_id': config['credit']
        })

        debit_acc = AccountAccount.browse(config['debit'])
        credit_acc = AccountAccount.browse(config['credit'])

        print(f"\n✅ [{rule_code}] {rule.name}")
        print(f"   Type: {config['type'].upper()}")
        print(f"   Debit:  {debit_acc.code} - {debit_acc.name}")
        print(f"   Credit: {credit_acc.code} - {credit_acc.name}")
        configured_count += 1
    else:
        print(f"\n❌ [{rule_code}] NOT FOUND")

print(f"\n" + "=" * 80)
print(f"SUMMARY: {configured_count}/{len(rule_configs)} rules configured")
print("=" * 80)

# COMMIT CHANGES TO DATABASE
print("\nCommitting changes to database...")
env.cr.commit()
print("✅ Changes committed successfully")

# Verify configuration
print(f"\n" + "=" * 80)
print("VERIFICATION - All V2 Rules Status")
print("=" * 80)

all_v2_rules = SalaryRule.search([
    '|', ('code', 'like', '_V2'),
    ('code', 'like', 'LIQUID_%')
])

print(f"\nTotal V2 rules: {len(all_v2_rules)}")
print(f"\nConfiguration status:")

configured = []
missing = []

for rule in all_v2_rules:
    if rule.account_debit_id and rule.account_credit_id:
        configured.append(rule)
    else:
        missing.append(rule)

print(f"\n✅ WITH accounting: {len(configured)} rules")
for rule in configured:
    print(f"   [{rule.code}] {rule.name}")
    print(f"      Dr: {rule.account_debit_id.code} | Cr: {rule.account_credit_id.code}")

if missing:
    print(f"\n⚠️  WITHOUT accounting: {len(missing)} rules")
    for rule in missing:
        print(f"   [{rule.code}] {rule.name}")

print(f"\n" + "=" * 80)
