#!/usr/bin/env python3
"""
Phase 3: Create V2 Salary Structure
Creates "Salarios Venezuela UEIPAB V2" with 11 salary rules
"""

# First delete any existing V2 structure (for clean testing)
existing = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')])
if existing:
    existing.unlink()
    print(f"Deleted existing V2 structure")

# Create all salary rules first (without struct_id)
rules = []

# Rule 1: VE_SALARY_V2
rule1 = env['hr.salary.rule'].create({
    'name': 'VE_SALARY_V2 - Salary V2 (Deductible)',
    'code': 'VE_SALARY_V2',
    'category_id': env.ref('hr_payroll_community.ALW').id,
    'sequence': 1,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
period_days = (payslip.date_to - payslip.date_from).days + 1
result = monthly_salary * (period_days / 30.0)''',
})
rules.append(rule1.id)
print(f"✅ Created Rule 1: {rule1.code}")

# Rule 2: VE_EXTRABONUS_V2
rule2 = env['hr.salary.rule'].create({
    'name': 'VE_EXTRABONUS_V2 - Extra Bonus V2',
    'code': 'VE_EXTRABONUS_V2',
    'category_id': env.ref('hr_payroll_community.ALW').id,
    'sequence': 2,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_extrabonus = contract.ueipab_extrabonus_v2 or 0.0
period_days = (payslip.date_to - payslip.date_from).days + 1
result = monthly_extrabonus * (period_days / 30.0)''',
})
rules.append(rule2.id)
print(f"✅ Created Rule 2: {rule2.code}")

# Rule 3: VE_BONUS_V2
rule3 = env['hr.salary.rule'].create({
    'name': 'VE_BONUS_V2 - Bonus V2',
    'code': 'VE_BONUS_V2',
    'category_id': env.ref('hr_payroll_community.ALW').id,
    'sequence': 3,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_bonus = contract.ueipab_bonus_v2 or 0.0
period_days = (payslip.date_to - payslip.date_from).days + 1
result = monthly_bonus * (period_days / 30.0)''',
})
rules.append(rule3.id)
print(f"✅ Created Rule 3: {rule3.code}")

# Rule 4: VE_CESTA_TICKET_V2
rule4 = env['hr.salary.rule'].create({
    'name': 'VE_CESTA_TICKET_V2 - Cesta Ticket',
    'code': 'VE_CESTA_TICKET_V2',
    'category_id': env.ref('hr_payroll_community.ALW').id,
    'sequence': 4,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_cesta = contract.cesta_ticket_usd or 0.0
period_days = (payslip.date_to - payslip.date_from).days + 1
result = monthly_cesta * (period_days / 30.0)''',
})
rules.append(rule4.id)
print(f"✅ Created Rule 4: {rule4.code}")

# Rule 5: VE_GROSS_V2
rule5 = env['hr.salary.rule'].create({
    'name': 'VE_GROSS_V2 - Total Gross',
    'code': 'VE_GROSS_V2',
    'category_id': env.ref('hr_payroll_community.GROSS').id,
    'sequence': 5,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''result = VE_SALARY_V2 + VE_EXTRABONUS_V2 + VE_BONUS_V2 + VE_CESTA_TICKET_V2''',
})
rules.append(rule5.id)
print(f"✅ Created Rule 5: {rule5.code}")

# Rule 6: VE_SSO_DED_V2
rule6 = env['hr.salary.rule'].create({
    'name': 'VE_SSO_DED_V2 - SSO 4%',
    'code': 'VE_SSO_DED_V2',
    'category_id': env.ref('hr_payroll_community.DED').id,
    'sequence': 101,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.04
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))''',
})
rules.append(rule6.id)
print(f"✅ Created Rule 6: {rule6.code}")

# Rule 7: VE_FAOV_DED_V2
rule7 = env['hr.salary.rule'].create({
    'name': 'VE_FAOV_DED_V2 - FAOV 1%',
    'code': 'VE_FAOV_DED_V2',
    'category_id': env.ref('hr_payroll_community.DED').id,
    'sequence': 102,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.01
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))''',
})
rules.append(rule7.id)
print(f"✅ Created Rule 7: {rule7.code}")

# Rule 8: VE_PARO_DED_V2
rule8 = env['hr.salary.rule'].create({
    'name': 'VE_PARO_DED_V2 - PARO 0.5%',
    'code': 'VE_PARO_DED_V2',
    'category_id': env.ref('hr_payroll_community.DED').id,
    'sequence': 103,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
monthly_deduction = monthly_salary * 0.005
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))''',
})
rules.append(rule8.id)
print(f"✅ Created Rule 8: {rule8.code}")

# Rule 9: VE_ARI_DED_V2
rule9 = env['hr.salary.rule'].create({
    'name': 'VE_ARI_DED_V2 - ARI Variable %',
    'code': 'VE_ARI_DED_V2',
    'category_id': env.ref('hr_payroll_community.DED').id,
    'sequence': 104,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''monthly_salary = contract.ueipab_salary_v2 or 0.0
ari_rate = (contract.ueipab_ari_withholding_rate or 0.0) / 100.0
monthly_deduction = monthly_salary * ari_rate
period_days = (payslip.date_to - payslip.date_from).days + 1
result = -(monthly_deduction * (period_days / 30.0))''',
})
rules.append(rule9.id)
print(f"✅ Created Rule 9: {rule9.code}")

# Rule 10: VE_TOTAL_DED_V2
rule10 = env['hr.salary.rule'].create({
    'name': 'VE_TOTAL_DED_V2 - Total Deductions',
    'code': 'VE_TOTAL_DED_V2',
    'category_id': env.ref('hr_payroll_community.DED').id,
    'sequence': 105,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''result = VE_SSO_DED_V2 + VE_FAOV_DED_V2 + VE_PARO_DED_V2 + VE_ARI_DED_V2''',
})
rules.append(rule10.id)
print(f"✅ Created Rule 10: {rule10.code}")

# Rule 11: VE_NET_V2
rule11 = env['hr.salary.rule'].create({
    'name': 'VE_NET_V2 - Net Salary',
    'code': 'VE_NET_V2',
    'category_id': env.ref('hr_payroll_community.NET').id,
    'sequence': 200,
    'appears_on_payslip': True,
    'condition_select': 'none',
    'amount_select': 'code',
    'amount_python_compute': '''result = VE_GROSS_V2 + VE_TOTAL_DED_V2''',
})
rules.append(rule11.id)
print(f"✅ Created Rule 11: {rule11.code}")

# Now create the salary structure with all rules linked
structure = env['hr.payroll.structure'].create({
    'name': 'Salarios Venezuela UEIPAB V2',
    'code': 'VE_PAYROLL_V2',
    'rule_ids': [(6, 0, rules)],  # Link all rules
})

env.cr.commit()

print("\n" + "=" * 80)
print("✅ PHASE 3 COMPLETE: V2 Salary Structure Created Successfully!")
print("=" * 80)
print(f"\nSalary Structure: {structure.name}")
print(f"Code: {structure.code}")
print(f"Structure ID: {structure.id}")
print(f"\nTotal Rules Created: {len(rules)}")
print("\nEarnings Rules (5):")
print("  1. VE_SALARY_V2 - Salary V2 (Deductible)")
print("  2. VE_EXTRABONUS_V2 - Extra Bonus V2")
print("  3. VE_BONUS_V2 - Bonus V2")
print("  4. VE_CESTA_TICKET_V2 - Cesta Ticket")
print("  5. VE_GROSS_V2 - Total Gross")
print("\nDeduction Rules (5):")
print("  6. VE_SSO_DED_V2 - SSO 4%")
print("  7. VE_FAOV_DED_V2 - FAOV 1%")
print("  8. VE_PARO_DED_V2 - PARO 0.5%")
print("  9. VE_ARI_DED_V2 - ARI Variable %")
print("  10. VE_TOTAL_DED_V2 - Total Deductions")
print("\nNet Rule (1):")
print("  11. VE_NET_V2 - Net Salary")
print("\n✅ All deductions apply ONLY to Salary V2")
print("✅ All amounts prorated by actual payslip period (days/30)")
print("✅ CEO Approved: Option A deduction approach with proration")
