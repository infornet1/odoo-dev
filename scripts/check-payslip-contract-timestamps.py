#!/usr/bin/env python3
"""Check when payslip was computed vs when contract was updated"""
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

# Get payslip and contract timestamps
query = """
SELECT
    p.number,
    p.name,
    p.state,
    p.create_date as payslip_created,
    p.write_date as payslip_updated,
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus,
    c.create_date as contract_created,
    c.write_date as contract_updated
FROM hr_payslip p
JOIN hr_employee e ON e.id = p.employee_id
JOIN hr_contract c ON c.employee_id = e.id
WHERE p.number = 'SLIP/238'
AND c.state = 'open'
ORDER BY c.date_start DESC
LIMIT 1;
"""

cur.execute(query)
row = cur.fetchone()

if row:
    print("=" * 80)
    print("TIMESTAMP ANALYSIS - SLIP/238 vs CONTRACT")
    print("=" * 80)
    print(f"\n📄 PAYSLIP: {row[0]}")
    print(f"Employee: {row[1]}")
    print(f"State: {row[2]}")
    print(f"Created:  {row[3]}")
    print(f"Updated:  {row[4]}")

    print(f"\n📋 CONTRACT:")
    print(f"wage:                 ${row[5]:.2f}")
    print(f"ueipab_salary_base:   ${row[6]:.2f}")
    print(f"ueipab_bonus_regular: ${row[7]:.2f}")
    print(f"ueipab_extra_bonus:   ${row[8]:.2f}")
    print(f"Created:              {row[9]}")
    print(f"Updated:              {row[10]}")

    print(f"\n🔍 ANALYSIS:")
    payslip_time = row[4] if row[4] else row[3]
    contract_time = row[10] if row[10] else row[9]

    if payslip_time < contract_time:
        print(f"✓ Payslip was created/updated BEFORE contract update")
        print(f"  Payslip: {payslip_time}")
        print(f"  Contract: {contract_time}")
        print(f"\n  ⚠️  This explains the discrepancy!")
        print(f"  ⚠️  You need to RECOMPUTE this payslip to use new contract values.")
    else:
        print(f"✗ Payslip was created/updated AFTER contract update")
        print(f"  Payslip: {payslip_time}")
        print(f"  Contract: {contract_time}")
        print(f"\n  ⚠️  This suggests the payslip SHOULD have new values")
        print(f"  ⚠️  But wage field shows ${row[5]:.2f} instead of ${row[6] + row[7] + row[8]:.2f}")

    print("\n" + "=" * 80)
else:
    print("⚠️  No data found for SLIP/238")

cur.close()
conn.close()
