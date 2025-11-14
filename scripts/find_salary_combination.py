#!/usr/bin/env python3
"""
Find which combination of 'amount' fields gives Salary $143.65 and Bonus $181.25
"""

# Find ALEJANDRA LOPEZ
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

print(f"🎯 TARGET: Salary $143.65 + Bonus $181.25 = $324.90")
print(f"   Contract Wage: ${payslip.contract_id.wage:,.2f}\n")

# Get all positive earnings using 'amount' field
earnings = {}
for line in payslip.line_ids:
    if line.amount > 0 and line.salary_rule_id.code not in ('VE_NET', 'VE_GROSS', 'VE_TOTAL_DED'):
        earnings[line.salary_rule_id.code] = line.amount
        print(f"   {line.salary_rule_id.code:<20} = ${line.amount:>8.2f}")

print(f"\n🧮 TESTING COMBINATIONS:")

# Test 1: VE_SALARY_70 alone
test1_salary = earnings.get('VE_SALARY_70', 0)
test1_bonus = sum(v for k, v in earnings.items() if k != 'VE_SALARY_70')
print(f"\n1. Salary=VE_SALARY_70 only:")
print(f"   Salary: ${test1_salary:.2f}")
print(f"   Bonus:  ${test1_bonus:.2f}")
print(f"   Total:  ${test1_salary + test1_bonus:.2f}")

# Test 2: VE_SALARY_70 + VE_BONUS_25
test2_salary = earnings.get('VE_SALARY_70', 0) + earnings.get('VE_BONUS_25', 0)
test2_bonus = earnings.get('VE_EXTRA_5', 0) + earnings.get('VE_CESTA_TICKET', 0)
print(f"\n2. Salary=VE_SALARY_70+VE_BONUS_25:")
print(f"   Salary: ${test2_salary:.2f}")
print(f"   Bonus:  ${test2_bonus:.2f}")
print(f"   Total:  ${test2_salary + test2_bonus:.2f}")

# Test 3: VE_SALARY_70 + VE_BONUS_25 + VE_EXTRA_5
test3_salary = earnings.get('VE_SALARY_70', 0) + earnings.get('VE_BONUS_25', 0) + earnings.get('VE_EXTRA_5', 0)
test3_bonus = earnings.get('VE_CESTA_TICKET', 0)
print(f"\n3. Salary=VE_SALARY_70+VE_BONUS_25+VE_EXTRA_5:")
print(f"   Salary: ${test3_salary:.2f} ← {'✅ MATCH!' if abs(test3_salary - 143.65) < 1 else '❌'}")
print(f"   Bonus:  ${test3_bonus:.2f}")
print(f"   Total:  ${test3_salary + test3_bonus:.2f}")

# Check contract breakdown
if payslip.contract_id.ueipab_deduction_base:
    print(f"\n📋 CONTRACT BREAKDOWN:")
    print(f"   Total Wage:        ${payslip.contract_id.wage:.2f}")
    print(f"   Deduction Base:    ${payslip.contract_id.ueipab_deduction_base:.2f}")
    print(f"   Bonuses/Benefits:  ${payslip.contract_id.wage - payslip.contract_id.ueipab_deduction_base:.2f}")

