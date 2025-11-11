#!/usr/bin/env python3
"""
Update VE_ARI_DED salary rule to use employee-specific ARI withholding rate

This fixes the issue where ARI deduction was using a fixed 1% rate for all employees,
when in reality it varies by employee (0.5% or 1%) based on their tax bracket.

The new formula reads the ARI rate from contract.ueipab_ari_withholding_rate field
which is synced from spreadsheet Column AA.
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

# New ARI formula using contract-specific rate
NEW_ARI_FORMULA = """# Venezuelan ARI (Withholding Income Tax): Variable rate on K (Basic Salary) ONLY
# Rate varies by employee (0.5% or 1%) based on tax bracket - stored in contract
# DOUBLED from monthly rate to apply FULL MONTHLY withholding in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment

# Get base salary (K component, bi-weekly)
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0

# Get ARI rate from contract (as decimal: 0.5% = 0.005, 1% = 0.01)
# Default to 0.5% if not set
ari_rate_monthly = (contract.ueipab_ari_withholding_rate / 100.0) if contract.ueipab_ari_withholding_rate else 0.005

# DOUBLE the monthly rate for bi-weekly application
ari_rate_biweekly = ari_rate_monthly * 2

# Calculate deduction
result = -(salary_base * ari_rate_biweekly)"""

def main():
    print("=" * 80)
    print("UPDATE VE_ARI_DED TO USE CONTRACT-SPECIFIC RATE")
    print("=" * 80)
    print("\nThis fixes the Rafael Perez issue ($0.59 difference)")
    print("ARI rate now varies by employee based on tax bracket:")
    print("  - NELCI BRITO: 0.5% (lower bracket)")
    print("  - RAFAEL PEREZ: 1.0% (higher bracket)")
    print("=" * 80)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    try:
        # Create backup table
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"ari_rule_backup_{backup_timestamp}"

        print(f"\n📦 Creating backup: {backup_table}")
        cur.execute(f"""
            CREATE TABLE {backup_table} AS
            SELECT *
            FROM hr_salary_rule
            WHERE code = 'VE_ARI_DED';
        """)

        cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
        backup_count = cur.fetchone()[0]
        print(f"✓ Backed up {backup_count} rule(s)")

        # Show current formula
        print("\n" + "=" * 80)
        print("CURRENT VE_ARI_DED FORMULA (BEFORE)")
        print("=" * 80)

        cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'VE_ARI_DED';")
        result = cur.fetchone()
        if result:
            name = result[0]
            if isinstance(name, dict):
                name = name.get('en_US', str(name))
            formula = result[1]
            print(f"\nRule: VE_ARI_DED - {name}")
            print(f"\nCurrent Formula:")
            for line in formula.split('\n'):
                print(f"  {line}")
        else:
            print("\n⚠️  VE_ARI_DED rule not found!")
            cur.close()
            conn.close()
            return

        # Update formula
        print("\n" + "=" * 80)
        print("UPDATING VE_ARI_DED FORMULA")
        print("=" * 80)

        cur.execute("""
            UPDATE hr_salary_rule
            SET amount_python_compute = %s
            WHERE code = 'VE_ARI_DED';
        """, (NEW_ARI_FORMULA,))

        if cur.rowcount > 0:
            print(f"\n✓ Updated VE_ARI_DED rule")
        else:
            print(f"\n⚠️  VE_ARI_DED rule not updated (no rows affected)")

        # Show new formula
        print("\n" + "=" * 80)
        print("NEW VE_ARI_DED FORMULA (AFTER)")
        print("=" * 80)

        cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'VE_ARI_DED';")
        result = cur.fetchone()
        if result:
            name = result[0]
            if isinstance(name, dict):
                name = name.get('en_US', str(name))
            formula = result[1]
            print(f"\nRule: VE_ARI_DED - {name}")
            print(f"\nNew Formula:")
            for line in formula.split('\n'):
                print(f"  {line}")

        # Show expected impact
        print("\n" + "=" * 80)
        print("EXPECTED IMPACT")
        print("=" * 80)

        print("\n📊 NELCI BRITO (Contract rate: 0.5%):")
        nelci_k_biweekly = 70.18
        nelci_ari_old = nelci_k_biweekly * 0.01
        nelci_ari_new = nelci_k_biweekly * 0.01  # 0.5% * 2 = 1%
        print(f"  K bi-weekly: ${nelci_k_biweekly:.2f}")
        print(f"  Old ARI (fixed 1%): ${nelci_ari_old:.2f}")
        print(f"  New ARI (0.5% × 2): ${nelci_ari_new:.2f}")
        print(f"  Difference: ${abs(nelci_ari_new - nelci_ari_old):.2f}")
        print(f"  NET Impact: $0.00 ✓ (no change for NELCI)")

        print("\n📊 RAFAEL PEREZ (Contract rate: 1.0%):")
        rafael_k_biweekly = 59.55
        rafael_ari_old = rafael_k_biweekly * 0.01
        rafael_ari_new = rafael_k_biweekly * 0.02  # 1.0% * 2 = 2%
        print(f"  K bi-weekly: ${rafael_k_biweekly:.2f}")
        print(f"  Old ARI (fixed 1%): ${rafael_ari_old:.2f}")
        print(f"  New ARI (1.0% × 2): ${rafael_ari_new:.2f}")
        print(f"  Difference: ${abs(rafael_ari_new - rafael_ari_old):.2f}")
        print(f"  NET Impact: -${rafael_ari_new - rafael_ari_old:.2f} (correctly increases deduction)")

        print("\n✓ Rafael Perez NET will now match spreadsheet:")
        rafael_old_net = 196.29
        rafael_new_net = 195.70
        print(f"  Old NET: ${rafael_old_net:.2f}")
        print(f"  New NET: ${rafael_new_net:.2f} (matches spreadsheet)")

        # Ask for confirmation
        print("\n" + "=" * 80)
        print("REVIEW CHANGES ABOVE")
        print("=" * 80)
        print(f"\nBackup table: {backup_table}")
        print(f"Updated rule: VE_ARI_DED")
        print("\n⚠️  WARNING: This changes ARI calculation!")
        print("⚠️  Make sure contract.ueipab_ari_withholding_rate is set for all employees!")

        response = input("\nCommit these changes? (yes/no): ")

        if response.lower() == 'yes':
            conn.commit()
            print("\n✓ Changes committed!")
            print("\n" + "=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print("1. Update module: odoo -d testing -u ueipab_hr_contract")
            print("2. Sync ARI rates from spreadsheet (Column AA)")
            print("3. Recompute RAFAEL PEREZ payslip (SLIP/240)")
            print("4. Verify NET = $195.70 (matches spreadsheet)")
            print("5. Recompute all November 2025 payslips")
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
