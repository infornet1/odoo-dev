#!/usr/bin/env python3
"""
Configure journal entries for Venezuelan payroll structure

Set NET salary to post to liability account (payable) instead of bank:
- Dr. 5.1.01.10.001 (Nómina expense)
- Cr. 2.1.01.01.002 (Payable liability)

This ensures NET salary is recorded as payable until disbursed from bank.
"""
import psycopg2
from datetime import datetime

db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo8069'
}

# Target accounts (verified to exist)
DEBIT_ACCOUNT_ID = 1009   # 5.1.01.10.001 - Nómina (Docentes)
CREDIT_ACCOUNT_ID = 1125  # 2.1.01.01.002 - Cuentas por pagar nómina

def main():
    print("=" * 80)
    print("CONFIGURE PAYROLL JOURNAL ENTRIES")
    print("=" * 80)
    print("\nTarget Configuration:")
    print(f"  Dr. 5.1.01.10.001 (ID: {DEBIT_ACCOUNT_ID}) - Nómina expense")
    print(f"  Cr. 2.1.01.01.002 (ID: {CREDIT_ACCOUNT_ID}) - Payable liability")
    print("=" * 80)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    try:
        # Create backup table
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"salary_rule_accounts_backup_{backup_timestamp}"

        print(f"\n📦 Creating backup: {backup_table}")
        cur.execute(f"""
            CREATE TABLE {backup_table} AS
            SELECT *
            FROM hr_salary_rule
            WHERE code = 'VE_NET';
        """)

        cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
        backup_count = cur.fetchone()[0]
        print(f"✓ Backed up {backup_count} rule(s)")

        # Show current configuration
        print("\n" + "=" * 80)
        print("CURRENT CONFIGURATION (BEFORE)")
        print("=" * 80)

        cur.execute("""
            SELECT
                sr.id,
                sr.code,
                sr.name,
                sr.account_debit_id,
                sr.account_credit_id
            FROM hr_salary_rule sr
            WHERE sr.code = 'VE_NET';
        """)

        net_rule = cur.fetchone()

        if net_rule:
            rule_id = net_rule[0]
            print(f"\nRule: {net_rule[1]}")
            name = net_rule[2]
            if isinstance(name, dict):
                name = name.get('en_US', str(name))
            print(f"Name: {name}")
            print(f"Debit Account ID: {net_rule[3]}")
            print(f"Credit Account ID: {net_rule[4]}")

            # Get account details if they exist
            if net_rule[3]:
                cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[3],))
                debit_acct = cur.fetchone()
                if debit_acct:
                    debit_name = debit_acct[1]
                    if isinstance(debit_name, dict):
                        debit_name = debit_name.get('en_US', str(debit_name))
                    print(f"  Current Debit: {debit_acct[0]} - {debit_name}")
            else:
                print(f"  Current Debit: None ❌")

            if net_rule[4]:
                cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[4],))
                credit_acct = cur.fetchone()
                if credit_acct:
                    credit_name = credit_acct[1]
                    if isinstance(credit_name, dict):
                        credit_name = credit_name.get('en_US', str(credit_name))
                    print(f"  Current Credit: {credit_acct[0]} - {credit_name}")
            else:
                print(f"  Current Credit: None ❌")
        else:
            print("\n⚠️  VE_NET rule not found!")
            cur.close()
            conn.close()
            return

        # Verify target accounts exist
        print("\n" + "=" * 80)
        print("VERIFYING TARGET ACCOUNTS")
        print("=" * 80)

        cur.execute("SELECT id, code, name, account_type FROM account_account WHERE id = %s;", (DEBIT_ACCOUNT_ID,))
        debit_acct = cur.fetchone()
        if debit_acct:
            debit_name = debit_acct[2]
            if isinstance(debit_name, dict):
                debit_name = debit_name.get('en_US', str(debit_name))
            print(f"\n✓ Debit Account Found:")
            print(f"  ID: {debit_acct[0]}")
            print(f"  Code: {debit_acct[1]}")
            print(f"  Name: {debit_name}")
            print(f"  Type: {debit_acct[3]}")
        else:
            print(f"\n❌ Debit account {DEBIT_ACCOUNT_ID} not found!")
            cur.close()
            conn.close()
            return

        cur.execute("SELECT id, code, name, account_type FROM account_account WHERE id = %s;", (CREDIT_ACCOUNT_ID,))
        credit_acct = cur.fetchone()
        if credit_acct:
            credit_name = credit_acct[2]
            if isinstance(credit_name, dict):
                credit_name = credit_name.get('en_US', str(credit_name))
            print(f"\n✓ Credit Account Found:")
            print(f"  ID: {credit_acct[0]}")
            print(f"  Code: {credit_acct[1]}")
            print(f"  Name: {credit_name}")
            print(f"  Type: {credit_acct[3]}")
        else:
            print(f"\n❌ Credit account {CREDIT_ACCOUNT_ID} not found!")
            cur.close()
            conn.close()
            return

        # Update VE_NET rule
        print("\n" + "=" * 80)
        print("UPDATING VE_NET RULE")
        print("=" * 80)

        cur.execute("""
            UPDATE hr_salary_rule
            SET
                account_debit_id = %s,
                account_credit_id = %s
            WHERE code = 'VE_NET';
        """, (DEBIT_ACCOUNT_ID, CREDIT_ACCOUNT_ID))

        if cur.rowcount > 0:
            print(f"\n✓ Updated VE_NET rule")
            print(f"  Debit: {DEBIT_ACCOUNT_ID} (5.1.01.10.001)")
            print(f"  Credit: {CREDIT_ACCOUNT_ID} (2.1.01.01.002)")
        else:
            print(f"\n⚠️  VE_NET rule not updated (no rows affected)")

        # Verify update
        print("\n" + "=" * 80)
        print("UPDATED CONFIGURATION (AFTER)")
        print("=" * 80)

        cur.execute("""
            SELECT
                sr.id,
                sr.code,
                sr.name,
                sr.account_debit_id,
                sr.account_credit_id
            FROM hr_salary_rule sr
            WHERE sr.code = 'VE_NET';
        """)

        net_rule = cur.fetchone()

        if net_rule:
            print(f"\nRule: {net_rule[1]}")
            name = net_rule[2]
            if isinstance(name, dict):
                name = name.get('en_US', str(name))
            print(f"Name: {name}")

            # Get debit account details
            if net_rule[3]:
                cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[3],))
                debit_acct = cur.fetchone()
                if debit_acct:
                    debit_name = debit_acct[1]
                    if isinstance(debit_name, dict):
                        debit_name = debit_name.get('en_US', str(debit_name))
                    print(f"  Debit: {debit_acct[0]} - {debit_name} ✓")

            # Get credit account details
            if net_rule[4]:
                cur.execute("SELECT code, name FROM account_account WHERE id = %s;", (net_rule[4],))
                credit_acct = cur.fetchone()
                if credit_acct:
                    credit_name = credit_acct[1]
                    if isinstance(credit_name, dict):
                        credit_name = credit_name.get('en_US', str(credit_name))
                    print(f"  Credit: {credit_acct[0]} - {credit_name} ✓")

        # Show impact
        print("\n" + "=" * 80)
        print("JOURNAL ENTRY IMPACT")
        print("=" * 80)
        print("\nWhen payslips are posted, NET salary will be recorded as:")
        print(f"  Dr. 5.1.01.10.001 - Nómina (Docentes)           [Expense]")
        print(f"  Cr. 2.1.01.01.002 - Cuentas por pagar nómina    [Liability]")
        print("\nThis keeps NET as PAYABLE until disbursed from bank.")
        print("When payment is made, create separate journal entry:")
        print(f"  Dr. 2.1.01.01.002 - Cuentas por pagar nómina")
        print(f"  Cr. 1.1.01.02.001 - Banco Venezuela")

        # Ask for confirmation
        print("\n" + "=" * 80)
        print("REVIEW CHANGES ABOVE")
        print("=" * 80)
        print(f"\nBackup table: {backup_table}")
        print(f"Updated rule: VE_NET")
        print("\n⚠️  WARNING: This changes how NET salary is posted!")
        print("⚠️  Make sure this matches your accounting policy!")

        response = input("\nCommit these changes? (yes/no): ")

        if response.lower() == 'yes':
            conn.commit()
            print("\n✓ Changes committed!")
            print("\n" + "=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print("1. Recompute all November 2025 draft payslips")
            print("2. Post a test payslip to verify journal entries")
            print("3. Check journal entry shows correct Dr./Cr. accounts")
            print("4. When ready to pay, create payment journal entry:")
            print("   Dr. 2.1.01.01.002 (Payable)")
            print("   Cr. 1.1.01.02.001 (Bank)")
            print("\n" + "=" * 80)
            print("ROLLBACK INSTRUCTIONS (if needed)")
            print("=" * 80)
            print(f"""
UPDATE hr_salary_rule r SET
    account_debit_id = b.account_debit_id,
    account_credit_id = b.account_credit_id
FROM {backup_table} b
WHERE r.id = b.id;
            """)
        else:
            conn.rollback()
            print("\n✗ Changes rolled back - no changes made")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
