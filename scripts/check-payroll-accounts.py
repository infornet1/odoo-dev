#!/usr/bin/env python3
"""Check current payroll journal entry configuration"""
import psycopg2

db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo8069'
}

conn = psycopg2.connect(**db_config)
cur = conn.cursor()

print("=" * 80)
print("PAYROLL JOURNAL ENTRY CONFIGURATION")
print("=" * 80)

# Get the Venezuelan payroll structure
print("\n📋 PAYROLL STRUCTURE:")
cur.execute("""
SELECT id, name, code
FROM hr_payroll_structure
WHERE code = 'UEIPAB_VE';
""")

struct = cur.fetchone()
if struct:
    struct_id = struct[0]
    struct_name = struct[1]
    if isinstance(struct_name, dict):
        struct_name = struct_name.get('en_US', str(struct_name))

    print(f"ID: {struct_id}")
    print(f"Name: {struct_name}")
    print(f"Code: {struct[2]}")
else:
    print("⚠️  UEIPAB_VE structure not found!")
    cur.close()
    conn.close()
    exit(1)

# Check salary rules and their accounts
print("\n" + "=" * 80)
print("SALARY RULES AND THEIR ACCOUNTS")
print("=" * 80)

cur.execute("""
SELECT
    sr.code,
    sr.name,
    sr.category_id,
    sc.code as category_code,
    sc.name as category_name,
    sr.account_debit_id,
    sr.account_credit_id
FROM hr_salary_rule sr
JOIN hr_salary_rule_category sc ON sc.id = sr.category_id
WHERE sr.code LIKE 'VE_%'
ORDER BY sr.sequence;
""")

rules = cur.fetchall()

print(f"\n{'Code':<20} {'Category':<15} {'Debit Account':<20} {'Credit Account':<20}")
print("-" * 80)

for rule in rules:
    code = rule[0]
    category_code = rule[3]
    debit_acct = rule[5]
    credit_acct = rule[6]

    print(f"{code:<20} {category_code:<15} {str(debit_acct):<20} {str(credit_acct):<20}")

# Check account details
print("\n" + "=" * 80)
print("ACCOUNT DETAILS")
print("=" * 80)

# Get all accounts used in payroll
cur.execute("""
SELECT DISTINCT account_id
FROM (
    SELECT account_debit_id as account_id FROM hr_salary_rule WHERE account_debit_id IS NOT NULL
    UNION
    SELECT account_credit_id as account_id FROM hr_salary_rule WHERE account_credit_id IS NOT NULL
) accounts;
""")

account_ids = [row[0] for row in cur.fetchall()]

if account_ids:
    placeholders = ','.join(['%s'] * len(account_ids))
    cur.execute(f"""
    SELECT id, code, name, account_type
    FROM account_account
    WHERE id IN ({placeholders});
    """, account_ids)

    accounts = cur.fetchall()

    print(f"\n{'ID':<10} {'Code':<20} {'Name':<40} {'Type':<20}")
    print("-" * 100)

    for acct in accounts:
        acct_id = acct[0]
        code = acct[1]
        name = acct[2]
        if isinstance(name, dict):
            name = name.get('en_US', str(name))
        acct_type = acct[3]
        print(f"{acct_id:<10} {code:<20} {name:<40} {acct_type:<20}")

# Check if desired accounts exist
print("\n" + "=" * 80)
print("CHECKING DESIRED ACCOUNTS")
print("=" * 80)

desired_accounts = ['5.1.01.10.001', '2.1.01.01.002']

for acct_code in desired_accounts:
    cur.execute("""
    SELECT id, code, name, account_type
    FROM account_account
    WHERE code = %s;
    """, (acct_code,))

    acct = cur.fetchone()
    if acct:
        name = acct[2]
        if isinstance(name, dict):
            name = name.get('en_US', str(name))
        print(f"\n✓ {acct_code}: {name}")
        print(f"  ID: {acct[0]}")
        print(f"  Type: {acct[3]}")
    else:
        print(f"\n✗ {acct_code}: NOT FOUND")

# Check NET salary rule
print("\n" + "=" * 80)
print("NET SALARY RULE CONFIGURATION")
print("=" * 80)

cur.execute("""
SELECT
    sr.id,
    sr.code,
    sr.name,
    sr.account_debit_id,
    sr.account_credit_id,
    sc.code as category_code
FROM hr_salary_rule sr
JOIN hr_salary_rule_category sc ON sc.id = sr.category_id
WHERE sr.code = 'VE_NET';
""")

net_rule = cur.fetchone()

if net_rule:
    print(f"\nRule: {net_rule[1]}")
    name = net_rule[2]
    if isinstance(name, dict):
        name = name.get('en_US', str(name))
    print(f"Name: {name}")
    print(f"Category: {net_rule[5]}")
    print(f"Debit Account ID: {net_rule[3]}")
    print(f"Credit Account ID: {net_rule[4]}")

    if net_rule[3]:
        cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[3],))
        debit_acct = cur.fetchone()
        if debit_acct:
            debit_name = debit_acct[1]
            if isinstance(debit_name, dict):
                debit_name = debit_name.get('en_US', str(debit_name))
            print(f"  Debit: {debit_acct[0]} - {debit_name}")

    if net_rule[4]:
        cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[4],))
        credit_acct = cur.fetchone()
        if credit_acct:
            credit_name = credit_acct[1]
            if isinstance(credit_name, dict):
                credit_name = credit_name.get('en_US', str(credit_name))
            print(f"  Credit: {credit_acct[0]} - {credit_name}")
else:
    print("\n⚠️  VE_NET rule not found!")

print("\n" + "=" * 80)

cur.close()
conn.close()
