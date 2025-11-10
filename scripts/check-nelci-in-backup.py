#!/usr/bin/env python3
"""Check if NELCI was in the backup and if she was updated"""
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
print("NELCI BRITO - CONTRACT UPDATE CHECK")
print("=" * 80)

# Check current contract
print("\n📋 CURRENT CONTRACT (hr_contract):")
cur.execute("""
SELECT
    e.name,
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus,
    c.write_date,
    e.department_id
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO'
AND c.state = 'open'
ORDER BY c.date_start DESC
LIMIT 1;
""")

current = cur.fetchone()
if current:
    print(f"Employee: {current[0]}")
    print(f"wage:                 ${current[1]:.2f}")
    print(f"ueipab_salary_base:   ${current[2]:.2f}")
    print(f"ueipab_bonus_regular: ${current[3]:.2f}")
    print(f"ueipab_extra_bonus:   ${current[4]:.2f}")
    print(f"Last updated:         {current[5]}")
    print(f"Department ID:        {current[6]}")

# Check backup table
print("\n📦 BACKUP (contract_salary_backup_20251110_182441):")
cur.execute("""
SELECT
    employee_name,
    old_wage,
    old_salary_base,
    old_bonus_regular,
    old_extra_bonus,
    new_wage,
    new_salary_base,
    new_bonus_regular,
    new_extra_bonus,
    backup_date
FROM contract_salary_backup_20251110_182441
WHERE employee_name LIKE '%NELCI%';
""")

backup = cur.fetchone()
if backup:
    print(f"Employee: {backup[0]}")
    print(f"\nOLD VALUES:")
    print(f"  wage:                 ${backup[1]:.2f}")
    print(f"  ueipab_salary_base:   ${backup[2]:.2f}")
    print(f"  ueipab_bonus_regular: ${backup[3]:.2f}")
    print(f"  ueipab_extra_bonus:   ${backup[4]:.2f}")
    print(f"\nNEW VALUES:")
    print(f"  wage:                 ${backup[5]:.2f}")
    print(f"  ueipab_salary_base:   ${backup[6]:.2f}")
    print(f"  ueipab_bonus_regular: ${backup[7]:.2f}")
    print(f"  ueipab_extra_bonus:   ${backup[8]:.2f}")
    print(f"\nBackup date: {backup[9]}")

    print("\n🔍 ANALYSIS:")
    if current and backup:
        if abs(current[1] - backup[5]) < 0.01:
            print("✓ Current wage matches NEW backup wage")
            print("✓ NELCI was successfully updated")
        elif abs(current[1] - backup[1]) < 0.01:
            print("✗ Current wage matches OLD backup wage")
            print("✗ NELCI was NOT updated (or rollback occurred)")
        else:
            print("⚠️  Current wage doesn't match either old or new backup")
            print(f"  Current: ${current[1]:.2f}")
            print(f"  Old:     ${backup[1]:.2f}")
            print(f"  New:     ${backup[5]:.2f}")
else:
    print("⚠️  NELCI BRITO NOT FOUND in backup table!")
    print("⚠️  This means she was NOT included in the update!")

    if current and current[6] is not None:
        print(f"\n  Reason: department_id = {current[6]} (only NULL departments updated)")
    else:
        print(f"\n  Reason: Contract not found or other issue")

print("\n" + "=" * 80)

cur.close()
conn.close()
