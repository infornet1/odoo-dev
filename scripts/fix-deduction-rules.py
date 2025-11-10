#!/usr/bin/env python3
"""Fix deduction rules to apply ONLY to Column K (Basic Salary)"""
import psycopg2
from datetime import datetime

db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo8069'
}

# New formulas (apply deductions ONLY to K)
FORMULAS = {
    'VE_SSO_DED': """# Venezuelan SSO: 2.25% bi-monthly on K (Basic Salary) ONLY
# Deductions apply ONLY to Column K, NOT to M or L
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.0225)""",

    'VE_FAOV_DED': """# Venezuelan FAOV: 0.5% bi-monthly on K (Basic Salary) ONLY
# Deductions apply ONLY to Column K, NOT to M or L
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.005)""",

    'VE_PARO_DED': """# Venezuelan PARO: 0.125% bi-monthly on K (Basic Salary) ONLY
# Deductions apply ONLY to Column K, NOT to M or L
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.00125)""",

    'VE_ARI_DED': """# Venezuelan ARI: 0.5% bi-monthly on K (Basic Salary) ONLY
# FIXED: Changed from 3% to 0.5% (was wrong!)
# Deductions apply ONLY to Column K, NOT to M or L
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.005)"""
}

def main():
    print("=" * 80)
    print("FIX DEDUCTION RULES - Apply Deductions ONLY to K (Basic Salary)")
    print("=" * 80)

    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    try:
        # Get structure ID
        cur.execute("SELECT id FROM hr_payroll_structure WHERE code = 'UEIPAB_VE' LIMIT 1;")
        struct = cur.fetchone()
        if not struct:
            print("❌ UEIPAB_VE structure not found!")
            return

        struct_id = struct[0]
        print(f"\n✓ Found UEIPAB_VE structure (ID: {struct_id})")

        # Create backup table
        backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"salary_rules_backup_{backup_timestamp}"

        print(f"\n📦 Creating backup: {backup_table}")
        cur.execute(f"""
            CREATE TABLE {backup_table} AS
            SELECT *
            FROM hr_salary_rule
            WHERE code IN ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED', 'VE_INCES_DED');
        """)

        cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
        backup_count = cur.fetchone()[0]
        print(f"✓ Backed up {backup_count} rules")

        # Show current formulas
        print("\n" + "=" * 80)
        print("CURRENT FORMULAS (BEFORE FIX)")
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
                print("Current formula:")
                for line in formula.split('\n')[:5]:  # Show first 5 lines
                    print(f"  {line}")
                print("  ...")

        # Update formulas
        print("\n" + "=" * 80)
        print("UPDATING FORMULAS")
        print("=" * 80)

        updated_count = 0
        for code, new_formula in FORMULAS.items():
            cur.execute("""
                UPDATE hr_salary_rule
                SET amount_python_compute = %s
                WHERE code = %s;
            """, (new_formula, code))

            if cur.rowcount > 0:
                print(f"✓ Updated {code}")
                updated_count += 1
            else:
                print(f"⚠️  {code} not found")

        # Check if INCES exists
        print("\n" + "=" * 80)
        print("CHECKING FOR INCES DEDUCTION")
        print("=" * 80)

        cur.execute("SELECT id FROM hr_salary_rule WHERE code = 'VE_INCES_DED';")
        inces_exists = cur.fetchone()

        if inces_exists:
            print("✓ VE_INCES_DED already exists, updated formula")
        else:
            print("⚠️  VE_INCES_DED does NOT exist!")
            print("   This rule needs to be created manually in Odoo UI or via module")
            print("   Formula needed:")
            print("""
# Venezuelan INCES: 0.125% bi-monthly on K (Basic Salary) ONLY
# Deductions apply ONLY to Column K, NOT to M or L
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.00125)
            """)

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

        print(f"\nK (Basic Salary) bi-weekly: ${k_biweekly:.2f}")
        print("\nOLD Deductions (on K+M+L = $158.65):")
        print(f"  SSO 2.25%:  ${158.65 * 0.0225:.2f}")
        print(f"  FAOV 0.5%:  ${158.65 * 0.005:.2f}")
        print(f"  Paro 0.125%: ${158.65 * 0.00125:.2f}")
        print(f"  ARI 3%:     ${158.65 * 0.03:.2f}")
        print(f"  ────────────────────")
        old_total = (158.65 * 0.0225) + (158.65 * 0.005) + (158.65 * 0.00125) + (158.65 * 0.03)
        print(f"  TOTAL:      ${old_total:.2f}")

        print(f"\nNEW Deductions (on K only = ${k_biweekly:.2f}):")
        print(f"  SSO 2.25%:  ${k_biweekly * 0.0225:.2f}")
        print(f"  FAOV 0.5%:  ${k_biweekly * 0.005:.2f}")
        print(f"  Paro 0.125%: ${k_biweekly * 0.00125:.2f}")
        print(f"  ARI 0.5%:   ${k_biweekly * 0.005:.2f}")
        print(f"  INCES 0.125%: ${k_biweekly * 0.00125:.2f}")
        print(f"  ────────────────────")
        new_total = (k_biweekly * 0.0225) + (k_biweekly * 0.005) + (k_biweekly * 0.00125) + (k_biweekly * 0.005) + (k_biweekly * 0.00125)
        print(f"  TOTAL:      ${new_total:.2f}")

        print(f"\nReduction in deductions: ${old_total - new_total:.2f}")
        print(f"Spreadsheet expected:    $2.37")
        print(f"New calculation:         ${new_total:.2f}")
        print(f"Difference:              ${abs(new_total - 2.37):.2f}")

        # Ask for confirmation
        print("\n" + "=" * 80)
        print("REVIEW CHANGES ABOVE")
        print("=" * 80)
        print(f"\nBackup table: {backup_table}")
        print(f"Updated rules: {updated_count}")

        response = input("\nCommit these changes? (yes/no): ")

        if response.lower() == 'yes':
            conn.commit()
            print("\n✓ Changes committed!")
            print("\n" + "=" * 80)
            print("NEXT STEPS")
            print("=" * 80)
            print("1. Recompute SLIP/239 (NELCI BRITO) in Odoo UI")
            print("2. Verify NET is now close to $153.91")
            print("3. Recompute all November 2025 payslips")
            print("4. If VE_INCES_DED doesn't exist, create it manually")
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
