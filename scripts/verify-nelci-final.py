#!/usr/bin/env python3
"""Verify NELCI's contract is now correct"""
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
print("NELCI BRITO - FINAL CONTRACT VERIFICATION")
print("=" * 80)

# Get current contract
cur.execute("""
SELECT
    e.name,
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus,
    c.write_date
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO'
AND c.state = 'open'
ORDER BY c.date_start DESC
LIMIT 1;
""")

current = cur.fetchone()

print("\n✅ UPDATED CONTRACT:")
print(f"Employee: {current[0]}")
print(f"wage:                 ${current[1]:.2f}")
print(f"ueipab_salary_base:   ${current[2]:.2f}")
print(f"ueipab_bonus_regular: ${current[3]:.2f}")
print(f"ueipab_extra_bonus:   ${current[4]:.2f}")
print(f"Last updated:         {current[5]}")

# Expected from spreadsheet
expected_wage = 317.29
expected_k = 140.36
expected_m = 176.93
expected_l = 0.00

print("\n📊 SPREADSHEET VALUES:")
print(f"K+L+M (GROSS):        ${expected_wage:.2f}")
print(f"K (Basic Salary):     ${expected_k:.2f}")
print(f"M (Major Bonus):      ${expected_m:.2f}")
print(f"L (Other Bonus):      ${expected_l:.2f}")

print("\n🔍 VERIFICATION:")
wage_match = abs(float(current[1]) - expected_wage) < 0.01
k_match = abs(float(current[2]) - expected_k) < 0.01
m_match = abs(float(current[3]) - expected_m) < 0.01
l_match = abs(float(current[4]) - expected_l) < 0.01

if wage_match and k_match and m_match and l_match:
    print("✓ ALL VALUES MATCH SPREADSHEET!")
    print("\n📋 EXPECTED PAYSLIP CALCULATION (15 days = 50%):")
    print(f"  K × 50%:  ${expected_k * 0.5:.2f}")
    print(f"  M × 50%:  ${expected_m * 0.5:.2f}")
    print(f"  L × 50%:  ${expected_l * 0.5:.2f}")
    print(f"  Cesta:    $20.00 (fixed)")
    print(f"  ────────────────────────")
    gross_15 = (expected_k + expected_m + expected_l) * 0.5 + 20.0
    print(f"  GROSS:    ${gross_15:.2f}")

    # Approximate deductions (need to verify exact rates)
    deductions = expected_k * 0.5 * 0.0625  # ~6.25% on K only
    print(f"  Deductions (~6.25% on K): ${deductions:.2f}")
    net_15 = gross_15 - deductions
    print(f"  NET:      ${net_15:.2f}")

    print(f"\n📊 SPREADSHEET Column Y (bi-weekly): $153.91")
    print(f"   Calculated NET:                    ${net_15:.2f}")
    print(f"   Difference:                        ${abs(net_15 - 153.91):.2f}")

    if abs(net_15 - 153.91) < 5.0:
        print("\n✓ Close match! Difference likely due to exact deduction rates.")
    else:
        print("\n⚠️  Still a difference - may need to verify deduction calculations.")
else:
    print("✗ VALUES DO NOT MATCH!")
    if not wage_match:
        print(f"  wage: Expected ${expected_wage:.2f}, Got ${float(current[1]):.2f}")
    if not k_match:
        print(f"  K: Expected ${expected_k:.2f}, Got ${float(current[2]):.2f}")
    if not m_match:
        print(f"  M: Expected ${expected_m:.2f}, Got ${float(current[3]):.2f}")
    if not l_match:
        print(f"  L: Expected ${expected_l:.2f}, Got ${float(current[4]):.2f}")

print("\n" + "=" * 80)
print("NEXT STEP: Recompute SLIP/238 in Odoo UI")
print("=" * 80)
print("1. Go to Payroll > Payslips")
print("2. Open SLIP/238 (NELCI BRITO)")
print("3. Click 'Compute Sheet' button")
print("4. Verify NET matches spreadsheet Column Y ($153.91)")
print("=" * 80)

cur.close()
conn.close()
