#!/usr/bin/env python3
"""Check NELCI BRITO SLIP/239 vs expected values"""
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
print("NELCI BRITO - SLIP/239 ANALYSIS")
print("=" * 80)

# Get contract values
print("\n📋 CURRENT CONTRACT:")
cur.execute("""
SELECT
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO'
AND c.state = 'open'
ORDER BY c.date_start DESC
LIMIT 1;
""")

contract = cur.fetchone()
if contract:
    print(f"wage:                 ${contract[0]:.2f}")
    print(f"ueipab_salary_base:   ${contract[1]:.2f}")
    print(f"ueipab_bonus_regular: ${contract[2]:.2f}")
    print(f"ueipab_extra_bonus:   ${contract[3]:.2f}")

# Get payslip details
print("\n📄 PAYSLIP SLIP/239:")
cur.execute("""
SELECT
    p.number,
    p.name,
    p.date_from,
    p.date_to,
    p.state,
    p.struct_id
FROM hr_payslip p
JOIN hr_employee e ON e.id = p.employee_id
WHERE p.number = 'SLIP/239'
AND e.name = 'NELCI BRITO';
""")

payslip = cur.fetchone()
if payslip:
    print(f"Number: {payslip[0]}")
    print(f"Name: {payslip[1]}")
    print(f"Period: {payslip[2]} to {payslip[3]}")
    print(f"State: {payslip[4]}")
    print(f"Structure ID: {payslip[5]}")

    # Get structure name
    cur.execute("SELECT name FROM hr_payroll_structure WHERE id = %s;", (payslip[5],))
    struct = cur.fetchone()
    if struct:
        print(f"Structure: {struct[0]}")

# Get payslip lines
print("\n📊 PAYSLIP LINES:")
cur.execute("""
SELECT
    pl.name,
    pl.code,
    pl.total,
    pl.quantity,
    pl.rate,
    pl.amount
FROM hr_payslip p
JOIN hr_payslip_line pl ON pl.slip_id = p.id
JOIN hr_employee e ON e.id = p.employee_id
WHERE p.number = 'SLIP/239'
AND e.name = 'NELCI BRITO'
ORDER BY pl.sequence, pl.id;
""")

lines = cur.fetchall()
gross = 0
deductions = 0
net = 0

print(f"\n{'Line Name':<50} {'Code':<20} {'Total':>12} {'Qty':>8} {'Rate':>10}")
print("-" * 110)

for line in lines:
    line_name = line[0]
    if isinstance(line_name, dict):
        line_name = line_name.get('en_US', str(line_name))

    code = line[1]
    total = float(line[2]) if line[2] else 0.0
    qty = float(line[3]) if line[3] else 0.0
    rate = float(line[4]) if line[4] else 0.0
    amount = float(line[5]) if line[5] else 0.0

    print(f"{line_name:<50} {code:<20} ${total:>11.2f} {qty:>8.2f} ${rate:>9.2f}")

    # Track totals
    if code in ['VE_SALARY_70', 'VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET']:
        gross += total
    elif code in ['VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED']:
        deductions += total
    elif code == 'VE_NET':
        net = total

print("-" * 110)
print(f"{'GROSS:':<50} {'':20} ${gross:>11.2f}")
print(f"{'DEDUCTIONS:':<50} {'':20} ${deductions:>11.2f}")
print(f"{'NET:':<50} {'':20} ${net:>11.2f}")

# Compare to expected
print("\n" + "=" * 80)
print("COMPARISON TO SPREADSHEET")
print("=" * 80)

expected_k_15 = contract[1] * 0.5  # K × 50%
expected_m_15 = contract[2] * 0.5  # M × 50%
expected_l_15 = contract[3] * 0.5  # L × 50%
expected_cesta = 20.00

expected_gross = expected_k_15 + expected_m_15 + expected_l_15 + expected_cesta
spreadsheet_net = 153.91

print(f"\n📊 EXPECTED CALCULATION (15 days):")
print(f"  K × 50%:  ${contract[1]:.2f} × 0.5 = ${expected_k_15:.2f}")
print(f"  M × 50%:  ${contract[2]:.2f} × 0.5 = ${expected_m_15:.2f}")
print(f"  L × 50%:  ${contract[3]:.2f} × 0.5 = ${expected_l_15:.2f}")
print(f"  Cesta:                       ${expected_cesta:.2f}")
print(f"  ────────────────────────────────────────")
print(f"  GROSS:                       ${expected_gross:.2f}")

print(f"\n📄 ACTUAL PAYSLIP:")
print(f"  GROSS:  ${gross:.2f}")
print(f"  NET:    ${net:.2f}")

print(f"\n📊 SPREADSHEET:")
print(f"  Column Y (Bi-weekly NET): ${spreadsheet_net:.2f}")

print(f"\n🔍 DIFFERENCES:")
gross_diff = gross - expected_gross
net_diff = net - spreadsheet_net
print(f"  Gross difference:  ${gross_diff:+.2f}")
print(f"  NET difference:    ${net_diff:+.2f}")

if abs(gross_diff) > 0.01:
    print(f"\n⚠️  GROSS doesn't match expected!")
    print(f"  Expected: ${expected_gross:.2f}")
    print(f"  Actual:   ${gross:.2f}")

if abs(net_diff) > 5.0:
    print(f"\n❌ NET is more than $5 off from spreadsheet!")
    print(f"  Expected (Column Y): ${spreadsheet_net:.2f}")
    print(f"  Actual (Payslip):    ${net:.2f}")
elif abs(net_diff) > 1.0:
    print(f"\n⚠️  NET is slightly off (within $5)")
    print(f"  Difference: ${abs(net_diff):.2f}")
    print(f"  This could be due to rounding or deduction rate differences")
else:
    print(f"\n✓ NET matches spreadsheet (within $1)!")

# Check what the salary rules are actually using
print("\n" + "=" * 80)
print("SALARY RULE ANALYSIS")
print("=" * 80)

cur.execute("""
SELECT
    sr.code,
    sr.name,
    sr.amount_python_compute
FROM hr_salary_rule sr
JOIN hr_payroll_structure_rule_rel rel ON rel.rule_id = sr.id
WHERE rel.struct_id = %s
AND sr.code IN ('VE_SALARY_70', 'VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET')
ORDER BY sr.sequence;
""", (payslip[5],))

rules = cur.fetchall()
print("\nSalary rules for this payslip structure:")
for rule in rules:
    code = rule[0]
    name = rule[1]
    if isinstance(name, dict):
        name = name.get('en_US', str(name))
    formula = rule[2]
    print(f"\n{code} - {name}:")
    print(f"  Formula: {formula[:200]}..." if len(formula) > 200 else f"  Formula: {formula}")

print("\n" + "=" * 80)

cur.close()
conn.close()
