#!/usr/bin/env python3
"""
Fix Odoo payroll formulas to match spreadsheet EXACTLY

Spreadsheet Formula: Column Y = (Salary ÷ 2) - MONTHLY Deductions

Key Changes:
1. Remove Cesta Ticket from bi-weekly gross (set to 0)
2. DOUBLE all deduction rates (to apply full monthly amount in bi-weekly payslip)
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

# New formulas with DOUBLED rates to match spreadsheet
FORMULAS = {
    'VE_SSO_DED': {
        'formula': """# Venezuelan SSO: 4.5% on K (Basic Salary) ONLY
# DOUBLED from 2.25% to apply FULL MONTHLY deduction in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.045)""",
        'old_rate': '2.25%',
        'new_rate': '4.5%'
    },

    'VE_FAOV_DED': {
        'formula': """# Venezuelan FAOV: 1% on K (Basic Salary) ONLY
# DOUBLED from 0.5% to apply FULL MONTHLY deduction in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.01)""",
        'old_rate': '0.5%',
        'new_rate': '1%'
    },

    'VE_PARO_DED': {
        'formula': """# Venezuelan PARO: 0.25% on K (Basic Salary) ONLY
# DOUBLED from 0.125% to apply FULL MONTHLY deduction in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.0025)""",
        'old_rate': '0.125%',
        'new_rate': '0.25%'
    },

    'VE_ARI_DED': {
        'formula': """# Venezuelan ARI: 1% on K (Basic Salary) ONLY
# DOUBLED from 0.5% to apply FULL MONTHLY deduction in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.01)""",
        'old_rate': '0.5%',
        'new_rate': '1%'
    },

    'VE_CESTA_TICKET': {
        'formula': """# Venezuelan Cesta Ticket: SET TO ZERO
# Spreadsheet does NOT include cesta in bi-weekly gross
# Column Y = (K+L+M)/2 - Monthly Deductions (NO CESTA)
result = 0.0""",
        'old_rate': '$40/month ($20 bi-weekly)',
        'new_rate': '$0 (excluded from bi-weekly)'
    }
}

def main():
    print("=" * 80)
    print("FIX ODOO PAYROLL TO MATCH SPREADSHEET EXACTLY")
    print("=" * 80)
    print("\nSpreadsheet Formula: Column Y = (Salary ÷ 2) - MONTHLY Deductions")
    print("\nChanges:")
    print("1. DOUBLE all deduction rates (to apply full monthly amount)")
    print("2. Set Cesta Ticket to $0 (not included in spreadsheet bi-weekly)")
    print("=" * 80)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    try:
        # Create backup table
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"payroll_rules_backup_{backup_timestamp}"

        print(f"\n📦 Creating backup: {backup_table}")
        cur.execute(f"""
            CREATE TABLE {backup_table} AS
            SELECT *
            FROM hr_salary_rule
            WHERE code IN ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED', 'VE_CESTA_TICKET');
        """)

        cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
        backup_count = cur.fetchone()[0]
        print(f"✓ Backed up {backup_count} rules")

        # Show current formulas
        print("\n" + "=" * 80)
        print("CURRENT RULES (BEFORE FIX)")
        print("=" * 80)

        for code in FORMULAS.keys():
            cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = %s;", (code,))
            result = cur.fetchone()
            if result:
                name = result[0]
                if isinstance(name, dict):
                    name = name.get('en_US', str(name))
                print(f"\n{code} - {name}")
                print(f"  Old rate: {FORMULAS[code]['old_rate']}")

        # Update formulas
        print("\n" + "=" * 80)
        print("UPDATING RULES")
        print("=" * 80)

        updated_count = 0
        for code, config in FORMULAS.items():
            cur.execute("""
                UPDATE hr_salary_rule
                SET amount_python_compute = %s
                WHERE code = %s;
            """, (config['formula'], code))

            if cur.rowcount > 0:
                print(f"✓ Updated {code}: {config['old_rate']} → {config['new_rate']}")
                updated_count += 1
            else:
                print(f"⚠️  {code} not found")

        # Verify updates
        print("\n" + "=" * 80)
        print("UPDATED FORMULAS (AFTER FIX)")
        print("=" * 80)

        for code in FORMULAS.keys():
            cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = %s;", (code,))
            result = cur.fetchone()
            if result:
                name = result[0]
                if isinstance(name, dict):
                    name = name.get('en_US', str(name))
                formula = result[1]
                print(f"\n{code} - {name}:")
                for line in formula.split('\n'):
                    print(f"  {line}")

        # Show expected impact on NELCI
        print("\n" + "=" * 80)
        print("EXPECTED IMPACT ON NELCI BRITO (15 days)")
        print("=" * 80)

        k_biweekly = 70.18
        m_biweekly = 88.47
        l_biweekly = 0.00

        print(f"\n📊 GROSS (Salary ÷ 2):")
        print(f"  K × 50%: ${k_biweekly:>10.2f}")
        print(f"  M × 50%: ${m_biweekly:>10.2f}")
        print(f"  L × 50%: ${l_biweekly:>10.2f}")
        print(f"  Cesta:   ${'0.00':>10}")
        print(f"  ───────────────────────")
        gross = k_biweekly + m_biweekly + l_biweekly
        print(f"  TOTAL:   ${gross:>10.2f}")

        print(f"\n📉 DEDUCTIONS (MONTHLY rates on bi-weekly K):")
        sso = k_biweekly * 0.045
        faov = k_biweekly * 0.01
        paro = k_biweekly * 0.0025
        ari = k_biweekly * 0.01
        print(f"  SSO 4.5%:  ${sso:>10.2f}")
        print(f"  FAOV 1%:   ${faov:>10.2f}")
        print(f"  Paro 0.25%: ${paro:>10.2f}")
        print(f"  ARI 1%:    ${ari:>10.2f}")
        print(f"  ───────────────────────")
        total_ded = sso + faov + paro + ari
        print(f"  TOTAL:     ${total_ded:>10.2f}")

        print(f"\n💰 NET:")
        net = gross - total_ded
        print(f"  ${gross:.2f} - ${total_ded:.2f} = ${net:.2f}")

        print(f"\n📊 SPREADSHEET:")
        print(f"  Column Y: $153.91")
        print(f"  Our calc: ${net:.2f}")
        print(f"  Difference: ${abs(net - 153.91):.2f}")

        if abs(net - 153.91) < 0.50:
            print(f"\n✓ PERFECT MATCH!")
        elif abs(net - 153.91) < 2.0:
            print(f"\n✓ Very close (within $2)")
        else:
            print(f"\n⚠️  Still ${abs(net - 153.91):.2f} off")
            print(f"   May need INCES rule (0.25%): ${k_biweekly * 0.0025:.2f}")

        # Ask for confirmation
        print("\n" + "=" * 80)
        print("REVIEW CHANGES ABOVE")
        print("=" * 80)
        print(f"\nBackup table: {backup_table}")
        print(f"Updated rules: {updated_count}")
        print("\n⚠️  WARNING: This changes deduction rates and removes cesta!")
        print("⚠️  Make sure this matches your payroll policy!")

        response = input("\nCommit these changes? (yes/no): ")

        if response.lower() == 'yes':
            conn.commit()
            print("\n✓ Changes committed!")
            print("\n" + "=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print("1. Recompute SLIP/239 (NELCI BRITO) in Odoo UI")
            print("2. Verify NET is now exactly $153.91")
            print("3. If still off, create VE_INCES_DED rule with 0.25% rate")
            print("4. Recompute all November 2025 payslips")
            print("\n" + "=" * 80)
            print("ROLLBACK INSTRUCTIONS (if needed)")
            print("=" * 80)
            print(f"""
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
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
