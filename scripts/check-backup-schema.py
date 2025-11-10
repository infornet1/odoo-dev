#!/usr/bin/env python3
"""Check backup table schema and NELCI's status"""
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
print("BACKUP TABLE ANALYSIS")
print("=" * 80)

# Get backup table schema
print("\n📋 BACKUP TABLE SCHEMA:")
cur.execute("""
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'contract_salary_backup_20251110_182441'
ORDER BY ordinal_position;
""")

for row in cur.fetchall():
    print(f"  {row[0]:<30} {row[1]}")

# Count records in backup
print("\n📊 BACKUP TABLE COUNTS:")
cur.execute("SELECT COUNT(*) FROM contract_salary_backup_20251110_182441;")
count = cur.fetchone()[0]
print(f"  Total records in backup: {count}")

# Check if NELCI is in backup (join with employee to get name)
cur.execute("""
SELECT b.*, e.name
FROM contract_salary_backup_20251110_182441 b
JOIN hr_employee e ON e.id = b.employee_id
WHERE e.name LIKE '%NELCI%'
LIMIT 1;
""")
nelci_backup = cur.fetchone()
if nelci_backup:
    print(f"\n✓ NELCI found in backup: {nelci_backup[-1]}")
else:
    print(f"\n✗ NELCI NOT found in backup")

# Check all employees with department_id set
print("\n🔍 EMPLOYEES WITH department_id SET (excluded from update):")
cur.execute("""
SELECT e.name, e.department_id, c.wage, c.ueipab_salary_base
FROM hr_employee e
JOIN hr_contract c ON c.employee_id = e.id
WHERE e.department_id IS NOT NULL
AND c.state = 'open'
ORDER BY e.name;
""")

excluded = cur.fetchall()
if excluded:
    print(f"\nFound {len(excluded)} employees with department_id (NOT updated):")
    for row in excluded:
        print(f"  - {row[0]:<30} Dept: {row[1]:>3}  wage: ${row[2]:>10.2f}")
else:
    print("  None")

# Check employees without department_id
print("\n✓ EMPLOYEES WITHOUT department_id (included in update):")
cur.execute("""
SELECT e.name, c.wage, c.ueipab_salary_base
FROM hr_employee e
JOIN hr_contract c ON c.employee_id = e.id
WHERE e.department_id IS NULL
AND c.state = 'open'
ORDER BY e.name
LIMIT 10;
""")

included = cur.fetchall()
print(f"\nShowing first 10 of employees without department_id:")
for row in included:
    print(f"  - {row[0]:<30} wage: ${row[1]:>10.2f}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("NELCI BRITO was EXCLUDED from the update because she has department_id = 54")
print("Our script only updated employees WHERE department_id IS NULL")
print("\nTo fix NELCI's contract, you need to either:")
print("1. Remove her department_id and run the sync script again")
print("2. Manually update her contract")
print("3. Modify the sync script to include employees with department_id")
print("=" * 80)

cur.close()
conn.close()
