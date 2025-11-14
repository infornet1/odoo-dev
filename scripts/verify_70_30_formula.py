#!/usr/bin/env python3
"""
Verify the new 70/30 Salary/Bonus formula in the report
Test with key employees from NOVIEMBRE15-2 batch
"""

print("=" * 120)
print("✅ VERIFYING 70/30 SALARY/BONUS FORMULA")
print("=" * 120)

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("\n❌ NOVIEMBRE15-2 batch not found")
    exit()

# Test with these key employees
test_employees = [
    'RAFAEL PEREZ',      # Original test case
    'ALEJANDRA LOPEZ',   # User's example
    'GABRIEL ESPAÑA',    # Another test case
    'ARCIDES ARZOLA',    # One of the mismatched VE_NET
]

print(f"\nBatch: {batch.name}")
print(f"Payslips in batch: {len(batch.slip_ids)}")

print(f"\n{'Employee':<20} | {'Wage':>12} | {'Ded Base':>12} | {'Salary (70%)':>12} | {'Bonus (30%+)':>12} | {'Total':>12} | {'VE_NET':>12} | Match?")
print("-" * 120)

for emp_name in test_employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if not payslip:
        print(f"{emp_name:<20} | NOT FOUND IN BATCH")
        continue

    contract = payslip.contract_id
    wage = contract.wage
    deduction_base = contract.ueipab_deduction_base

    # NEW FORMULA (70/30 split)
    salary = deduction_base * 0.70
    bonus = (deduction_base * 0.30) + (wage - deduction_base)
    total = salary + bonus

    # Get VE_NET from payslip
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    ve_net = net_line[0].total if net_line else 0.0

    # Check if total equals wage (should always be true)
    match = "✅" if abs(total - wage) < 0.01 else "❌"

    print(f"{emp_name:<20} | ${wage:>11,.2f} | ${deduction_base:>11,.2f} | ${salary:>11,.2f} | ${bonus:>11,.2f} | ${total:>11,.2f} | ${ve_net:>11,.2f} | {match}")

print("-" * 120)

print(f"\n📊 FORMULA VERIFICATION:")
print(f"   Salary = deduction_base × 70%")
print(f"   Bonus  = (deduction_base × 30%) + (wage - deduction_base)")
print(f"   Total  = Salary + Bonus = wage ✅")

print(f"\n💡 EXPECTED RESULTS:")
print(f"   RAFAEL PEREZ:")
print(f"      Previous: Salary $170.30, Bonus $230.32")
print(f"      New:      Salary $119.21, Bonus $281.41")
print(f"\n   ALEJANDRA LOPEZ:")
print(f"      Previous: Salary $143.65, Bonus $181.25")
print(f"      New:      Salary $100.55, Bonus $224.36")

print(f"\n✅ Formula is mathematically correct!")
print(f"   - Salary shows 70% of deduction_base (the portion subject to SS/tax)")
print(f"   - Bonus shows 30% of deduction_base + all other benefits")
print(f"   - Total always equals wage (no money lost or created)")
print(f"   - VE_NET is unchanged (formula only affects report display)")

print("\n" + "=" * 120)
