#!/usr/bin/env python3
"""Check what the deduction rules are calculating from"""
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
print("DEDUCTION RULE FORMULAS ANALYSIS")
print("=" * 80)

# Get deduction rules
cur.execute("""
SELECT
    sr.code,
    sr.name,
    sr.amount_python_compute,
    sr.amount_percentage,
    sr.amount_percentage_base
FROM hr_salary_rule sr
WHERE sr.code IN ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED', 'VE_INCES_DED')
ORDER BY sr.code;
""")

rules = cur.fetchall()

print("\n📋 DEDUCTION RULES:")
for rule in rules:
    code = rule[0]
    name = rule[1]
    if isinstance(name, dict):
        name = name.get('en_US', str(name))
    formula = rule[2]
    percentage = rule[3]
    base = rule[4]

    print(f"\n{code}: {name}")
    print(f"  Percentage: {percentage}")
    print(f"  Base: {base}")
    print(f"  Formula:")
    # Print formula with indentation
    if formula:
        for line in formula.split('\n'):
            print(f"    {line}")

# Check NELCI's actual payslip calculation
print("\n" + "=" * 80)
print("NELCI SLIP/239 - ACTUAL DEDUCTION CALCULATION")
print("=" * 80)

cur.execute("""
SELECT
    pl.code,
    pl.name,
    pl.total,
    pl.quantity,
    pl.rate,
    pl.amount
FROM hr_payslip p
JOIN hr_payslip_line pl ON pl.slip_id = p.id
JOIN hr_employee e ON e.id = p.employee_id
WHERE p.number = 'SLIP/239'
AND e.name = 'NELCI BRITO'
AND pl.code IN ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED', 'VE_INCES_DED', 'VE_SALARY_70')
ORDER BY pl.sequence;
""")

lines = cur.fetchall()

print("\n📊 PAYSLIP LINE DETAILS:")
print(f"{'Code':<15} {'Total':>12} {'Quantity':>10} {'Rate':>10} {'Amount':>12}")
print("-" * 65)

for line in lines:
    code = line[0]
    total = float(line[1]) if line[1] else 0.0
    qty = float(line[2]) if line[2] else 0.0
    rate = float(line[3]) if line[3] else 0.0
    amount = float(line[4]) if line[4] else 0.0

    print(f"{code:<15} ${total:>11.2f} {qty:>10.2f} ${rate:>9.2f} ${amount:>11.2f}")

# Manual calculation
print("\n" + "=" * 80)
print("EXPECTED DEDUCTIONS (based on spreadsheet)")
print("=" * 80)

k = 140.36  # Basic salary
biweekly_k = k * 0.5  # 15 days

print(f"\nBasic Salary (K): ${k:.2f}")
print(f"Bi-weekly (15 days): ${biweekly_k:.2f}")

print("\nMonthly deductions from spreadsheet:")
print(f"  IVSS 4.5%/2 = 2.25%:  ${k * 0.0225:.2f}")
print(f"  FAOV 1%:              ${k * 0.01:.2f}")
print(f"  INCES 0.25%:          ${k * 0.0025:.2f}")
print(f"  ARI:                  ${k * 0.005:.2f}  (estimated)")

print("\nBi-weekly deductions (÷2):")
print(f"  IVSS:   ${k * 0.0225 / 2:.2f}")
print(f"  FAOV:   ${k * 0.01 / 2:.2f}")
print(f"  INCES:  ${k * 0.0025 / 2:.2f}")
print(f"  ARI:    ${k * 0.005 / 2:.2f}")
print(f"  ─────────────────────")
total_expected = (k * 0.0225 / 2) + (k * 0.01 / 2) + (k * 0.0025 / 2) + (k * 0.005 / 2)
print(f"  TOTAL:  ${total_expected:.2f}")

print(f"\nOdoo actual deductions: $9.32")
print(f"Expected deductions:    ${total_expected:.2f}")
print(f"Difference:             ${9.32 - total_expected:.2f}")

print("\n" + "=" * 80)
print("HYPOTHESIS: Odoo is applying deductions to wrong base")
print("=" * 80)

# Test different bases
gross_with_cesta = 178.65
gross_without_cesta = 158.65
k_biweekly = 70.18

print("\nIf deductions are on GROSS WITH CESTA ($178.65):")
print(f"  4% SSO:   ${gross_with_cesta * 0.04:.2f}")
print(f"  1% FAOV:  ${gross_with_cesta * 0.01:.2f}")
print(f"  0.5% Paro: ${gross_with_cesta * 0.005:.2f}")
print(f"  3% ARI:   ${gross_with_cesta * 0.03:.2f}")
print(f"  Total:    ${(gross_with_cesta * 0.04) + (gross_with_cesta * 0.01) + (gross_with_cesta * 0.005) + (gross_with_cesta * 0.03):.2f}")

print("\nIf deductions are on K ONLY ($70.18):")
print(f"  4% SSO:   ${k_biweekly * 0.04:.2f}")
print(f"  1% FAOV:  ${k_biweekly * 0.01:.2f}")
print(f"  0.5% Paro: ${k_biweekly * 0.005:.2f}")
print(f"  3% ARI:   ${k_biweekly * 0.03:.2f}")
print(f"  Total:    ${(k_biweekly * 0.04) + (k_biweekly * 0.01) + (k_biweekly * 0.005) + (k_biweekly * 0.03):.2f}")

sso_actual = 3.57
expected_on_k = k_biweekly * 0.04
print(f"\n🔍 SSO Deduction Analysis:")
print(f"  Actual: ${sso_actual:.2f}")
print(f"  If 4% on K ($70.18): ${expected_on_k:.2f}")
print(f"  Matches? {abs(sso_actual - expected_on_k) < 0.01}")

# Try to reverse engineer what base is being used
if sso_actual > 0:
    base_used = sso_actual / 0.04
    print(f"\n  Reverse calculation: ${sso_actual:.2f} ÷ 4% = ${base_used:.2f}")
    print(f"  This suggests SSO is being applied to: ${base_used:.2f}")

print("\n" + "=" * 80)

cur.close()
conn.close()
