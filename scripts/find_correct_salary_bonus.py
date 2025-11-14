#!/usr/bin/env python3
"""
Find which payslip line fields sum to $143.65 (Salary) and $181.25 (Bonus)
for ALEJANDRA LOPEZ in NOVIEMBRE15-1
"""

# Find ALEJANDRA LOPEZ in NOVIEMBRE15-1
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

print(f"👤 {payslip.employee_id.name} - {payslip.number}")
print(f"   Contract Wage: ${payslip.contract_id.wage:,.2f}")
print(f"   Expected: Salary $143.65 + Bonus $181.25 = $324.90")

print(f"\n💰 ALL PAYSLIP LINES:")
print(f"{'Rule Code':<25} | {'Total':>15} | {'Rate':>8} | {'Quantity':>10} | {'Amount':>15}")
print("=" * 100)

for line in payslip.line_ids.sorted(lambda l: l.sequence):
    if line.total != 0 or line.amount != 0:
        print(f"{line.salary_rule_id.code:<25} | ${line.total:>14,.2f} | {line.rate:>7.2f}% | {line.quantity:>10,.2f} | ${line.amount:>14,.2f}")

# Check if there are 'amount' or 'quantity' fields that have the USD values
print(f"\n🔍 CHECKING 'AMOUNT' FIELD (might contain original USD values):")
print(f"{'Rule Code':<25} | {'Amount (USD?)':>15}")
print("=" * 50)

salary_amount_sum = 0.0
bonus_amount_sum = 0.0

for line in payslip.line_ids:
    if line.salary_rule_id.code == 'VE_SALARY_70' and line.amount != 0:
        print(f"{line.salary_rule_id.code:<25} | ${line.amount:>14,.2f}")
        salary_amount_sum += line.amount
    elif line.amount > 0 and line.salary_rule_id.code not in ('VE_NET', 'VE_SALARY_70', 'VE_GROSS'):
        print(f"{line.salary_rule_id.code:<25} | ${line.amount:>14,.2f}")
        bonus_amount_sum += line.amount

print(f"\n📊 SUMS USING 'AMOUNT' FIELD:")
print(f"   Salary (VE_SALARY_70 amount):  ${salary_amount_sum:,.2f}")
print(f"   Bonus (others amount):         ${bonus_amount_sum:,.2f}")
print(f"   Total:                         ${salary_amount_sum + bonus_amount_sum:,.2f}")

print(f"\n🎯 MATCH CHECK:")
print(f"   Salary: ${salary_amount_sum:,.2f} vs $143.65 - {'✅ MATCH!' if abs(salary_amount_sum - 143.65) < 1 else '❌'}")
print(f"   Bonus:  ${bonus_amount_sum:,.2f} vs $181.25 - {'✅ MATCH!' if abs(bonus_amount_sum - 181.25) < 1 else '❌'}")

