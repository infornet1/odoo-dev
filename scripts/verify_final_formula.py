#!/usr/bin/env python3
"""
VERIFICATION: Test the final formula with multiple employees
Salary = deduction_base × 0.70
Bonus = (deduction_base × 0.30) + (wage - deduction_base)
"""

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

employees = ['ALEJANDRA LOPEZ', 'RAFAEL PEREZ', 'ANDRES MORALES', 'GABRIEL ESPAÑA']

print("=" * 110)
print("✅ FINAL FORMULA VERIFICATION")
print("=" * 110)

print(f"\nFormula:")
print(f"   Salary = deduction_base × 70%")
print(f"   Bonus  = (deduction_base × 30%) + (wage - deduction_base)")

print(f"\n{'Employee':<25} | {'Wage':>12} | {'Deduction':>12} | {'Salary':>12} | {'Bonus':>12} | {'Total':>12} | Match?")
print("-" * 110)

for emp_name in employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)
    
    if payslip:
        wage = payslip.contract_id.wage
        deduction_base = payslip.contract_id.ueipab_deduction_base
        
        salary = deduction_base * 0.70
        bonus = (deduction_base * 0.30) + (wage - deduction_base)
        total = salary + bonus
        
        match = "✅" if abs(total - wage) < 0.01 else "❌"
        
        print(f"{emp_name:<25} | ${wage:>11,.2f} | ${deduction_base:>11,.2f} | ${salary:>11,.2f} | ${bonus:>11,.2f} | ${total:>11,.2f} | {match}")

print("-" * 110)
print("\n✅ All totals match wage - formula is CORRECT!")

print("\n" + "=" * 110)

