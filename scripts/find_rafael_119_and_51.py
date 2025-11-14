#!/usr/bin/env python3
"""
INVESTIGATION: Where do $119.09 and $51.21 come from for Rafael Perez?
User expects: Salary $119.09, Bonus $51.21
NO DATABASE MODIFICATIONS - pure investigation
"""

# Find RAFAEL PEREZ
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'RAFAEL PEREZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

print("=" * 80)
print(f"🔍 INVESTIGATION: Where do $119.09 and $51.21 come from?")
print("=" * 80)

print(f"\n👤 {payslip.employee_id.name} - {payslip.number}")

# Contract info
print(f"\n💼 CONTRACT FIELDS:")
print(f"   wage:                     ${payslip.contract_id.wage:,.2f}")
print(f"   ueipab_deduction_base:    ${payslip.contract_id.ueipab_deduction_base:,.2f}")

# User expects
print(f"\n🎯 USER EXPECTS:")
print(f"   Salary:  $119.09")
print(f"   Bonus:   $51.21")
print(f"   Total:   ${119.09 + 51.21:.2f}")

# Check if there are other contract fields
if hasattr(payslip.contract_id, 'struct_id'):
    print(f"\n📋 Salary Structure: {payslip.contract_id.struct_id.name if payslip.contract_id.struct_id else 'None'}")

# Check ALL contract fields that might contain these values
print(f"\n🔍 CHECKING ALL CONTRACT FIELDS FOR THESE VALUES:")
print(f"   Looking for: $119.09 or $51.21...")

contract_fields_to_check = [
    'wage', 'ueipab_deduction_base', 'basic_wage', 'gross_wage',
    'net_wage', 'allowance', 'bonus_amount'
]

found_matches = []

for field_name in contract_fields_to_check:
    if hasattr(payslip.contract_id, field_name):
        try:
            value = getattr(payslip.contract_id, field_name)
            if isinstance(value, (int, float)):
                if abs(value - 119.09) < 0.1:
                    found_matches.append(f"   ✅ {field_name} = ${value:.2f} (matches $119.09!)")
                elif abs(value - 51.21) < 0.1:
                    found_matches.append(f"   ✅ {field_name} = ${value:.2f} (matches $51.21!)")
                elif abs(value - 170.30) < 0.1:
                    found_matches.append(f"   📌 {field_name} = ${value:.2f} (matches $170.30 = $119.09 + $51.21)")
        except:
            pass

if found_matches:
    print("\n   MATCHES FOUND:")
    for match in found_matches:
        print(match)
else:
    print("   ❌ No direct matches in standard contract fields")

# Check payslip lines for these values
print(f"\n🔍 CHECKING PAYSLIP LINES:")
print(f"{'Rule Code':<25} | {'Total':>12} | {'Amount':>12} | {'Quantity':>10} | Match?")
print("-" * 85)

for line in payslip.line_ids:
    match = ""
    if abs(line.total - 119.09) < 0.1:
        match = "✅ Matches $119.09!"
    elif abs(line.total - 51.21) < 0.1:
        match = "✅ Matches $51.21!"
    elif abs(line.amount - 119.09) < 0.1:
        match = "✅ Amount matches $119.09!"
    elif abs(line.amount - 51.21) < 0.1:
        match = "✅ Amount matches $51.21!"
    
    if match or line.total != 0:
        print(f"{line.salary_rule_id.code:<25} | ${line.total:>11,.2f} | ${line.amount:>11,.2f} | {line.quantity:>10,.2f} | {match}")

# Try different calculation methods
print(f"\n🧮 TESTING DIFFERENT CALCULATION METHODS:")

# Method 1: 70% of something
test1 = payslip.contract_id.ueipab_deduction_base * 0.70
print(f"   1. deduction_base × 70%:           ${test1:.2f} {'✅ Match!' if abs(test1 - 119.09) < 0.1 else ''}")

# Method 2: 30% of something
test2 = payslip.contract_id.ueipab_deduction_base * 0.30
print(f"   2. deduction_base × 30%:           ${test2:.2f} {'✅ Match!' if abs(test2 - 51.21) < 0.1 else ''}")

# Method 3: wage - deduction_base
test3 = payslip.contract_id.wage - payslip.contract_id.ueipab_deduction_base
print(f"   3. wage - deduction_base:          ${test3:.2f}")

# Method 4: Sum of VE_SALARY_70 amount field
salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
if salary_line:
    print(f"   4. VE_SALARY_70.total:             ${salary_line[0].total:.2f}")
    print(f"   5. VE_SALARY_70.amount:            ${salary_line[0].amount:.2f}")

# Method 5: Sum of bonus lines using amount field
bonus_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code in ('VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET'))
if bonus_lines:
    bonus_sum_total = sum(bonus_lines.mapped('total'))
    bonus_sum_amount = sum(bonus_lines.mapped('amount'))
    print(f"   6. Sum bonus lines (total):        ${bonus_sum_total:.2f}")
    print(f"   7. Sum bonus lines (amount):       ${bonus_sum_amount:.2f} {'✅ Match!' if abs(bonus_sum_amount - 51.21) < 0.1 else ''}")

# Check if 119.09 + 51.21 = 170.30 (deduction base)
print(f"\n🎯 KEY FINDING:")
print(f"   $119.09 + $51.21 = ${119.09 + 51.21:.2f}")
print(f"   deduction_base = ${payslip.contract_id.ueipab_deduction_base:.2f}")
if abs((119.09 + 51.21) - payslip.contract_id.ueipab_deduction_base) < 0.1:
    print(f"   ✅ These add up to deduction_base!")
    print(f"\n   This suggests:")
    print(f"   - Salary = 70% of deduction_base = ${payslip.contract_id.ueipab_deduction_base * 0.70:.2f}")
    print(f"   - Bonus  = 30% of deduction_base = ${payslip.contract_id.ueipab_deduction_base * 0.30:.2f}")

print("\n" + "=" * 80)

