#!/usr/bin/env python3
"""
VERIFICATION: Check if 70/30 split of deduction_base is the correct logic
NO DATABASE MODIFICATIONS
"""

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

# Check ALEJANDRA LOPEZ and RAFAEL PEREZ
test_employees = ['ALEJANDRA LOPEZ', 'RAFAEL PEREZ', 'ANDRES MORALES']

print("=" * 90)
print("VERIFICATION: 70/30 Split of Deduction Base")
print("=" * 90)

print(f"\n{'Employee':<25} | {'Deduction Base':>15} | {'Salary (70%)':>15} | {'Bonus (30%)':>15} | {'Total':>15}")
print("-" * 90)

for emp_name in test_employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)
    
    if payslip:
        deduction_base = payslip.contract_id.ueipab_deduction_base or 0.0
        salary_70 = deduction_base * 0.70
        bonus_30 = deduction_base * 0.30
        total = salary_70 + bonus_30
        
        print(f"{emp_name:<25} | ${deduction_base:>14,.2f} | ${salary_70:>14,.2f} | ${bonus_30:>14,.2f} | ${total:>14,.2f}")

print("-" * 90)

# Show current calculation vs new calculation for RAFAEL
print(f"\n📊 RAFAEL PEREZ - Current vs Proposed:")
rafael = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'RAFAEL PEREZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if rafael:
    wage = rafael.contract_id.wage
    deduction_base = rafael.contract_id.ueipab_deduction_base
    
    # Current method
    salary_current = deduction_base
    bonus_current = wage - deduction_base
    
    # Proposed method (70/30 split)
    salary_proposed = deduction_base * 0.70
    bonus_proposed = deduction_base * 0.30
    
    print(f"\n   {'Method':<20} | {'Salary':>15} | {'Bonus':>15} | {'Total':>15}")
    print("   " + "-" * 70)
    print(f"   {'Current (100%/diff)':<20} | ${salary_current:>14,.2f} | ${bonus_current:>14,.2f} | ${salary_current + bonus_current:>14,.2f}")
    print(f"   {'Proposed (70/30)':<20} | ${salary_proposed:>14,.2f} | ${bonus_proposed:>14,.2f} | ${salary_proposed + bonus_proposed:>14,.2f}")
    
    print(f"\n   ⚠️  NOTE: Proposed total (${salary_proposed + bonus_proposed:.2f}) != Contract wage (${wage:.2f})")
    print(f"   The 70/30 split only covers deduction_base, not full wage")

print("\n" + "=" * 90)
print("🤔 QUESTION: Should Bonus also include (wage - deduction_base)?")
print("=" * 90)
print(f"\n   Option A: Salary = 70% deduction_base, Bonus = 30% deduction_base")
print(f"             Total = deduction_base only (${deduction_base:.2f})")
print(f"\n   Option B: Salary = 70% deduction_base, Bonus = 30% deduction_base + (wage - deduction_base)")
print(f"             Total = wage (${wage:.2f})")

if rafael:
    option_b_salary = deduction_base * 0.70
    option_b_bonus = (deduction_base * 0.30) + (wage - deduction_base)
    
    print(f"\n   Rafael with Option B:")
    print(f"      Salary: ${option_b_salary:.2f}")
    print(f"      Bonus:  ${option_b_bonus:.2f} (${deduction_base * 0.30:.2f} + ${wage - deduction_base:.2f})")
    print(f"      Total:  ${option_b_salary + option_b_bonus:.2f}")

print("\n" + "=" * 90)

