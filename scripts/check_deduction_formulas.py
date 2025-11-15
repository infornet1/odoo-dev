#!/usr/bin/env python3
"""
DIAGNOSTIC: Check the actual salary rule formulas for SSO, FAOV, PARO, ARI
to see what percentages are coded in the database.
NO DATABASE MODIFICATIONS - pure read-only diagnostic
"""

print("=" * 140)
print("🔍 DIAGNOSTIC: SALARY RULE FORMULAS - DEDUCTION PERCENTAGES")
print("=" * 140)

# The deduction rules we need to check
deduction_rules = ['VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED']

print(f"\n📋 CHECKING DEDUCTION SALARY RULES:")
print(f"   Expected rates:")
print(f"      VE_SSO_DED:   4.00% (Seguro Social Obligatorio)")
print(f"      VE_FAOV_DED:  1.00% (Política Habitacional)")
print(f"      VE_PARO_DED:  0.50% (Paro Forzoso)")
print(f"      VE_ARI_DED:   Progressive tax table")

for rule_code in deduction_rules:
    print(f"\n{'=' * 140}")
    print(f"RULE CODE: {rule_code}")
    print(f"{'=' * 140}")

    rule = env['hr.salary.rule'].search([('code', '=', rule_code)], limit=1)

    if not rule:
        print(f"   ❌ Rule not found in database")
        continue

    print(f"\n   Basic Information:")
    print(f"   {'Field':<30} | Value")
    print(f"   {'-' * 80}")
    print(f"   {'ID':<30} | {rule.id}")
    print(f"   {'Name':<30} | {rule.name}")
    print(f"   {'Code':<30} | {rule.code}")
    print(f"   {'Category':<30} | {rule.category_id.name if rule.category_id else 'N/A'}")
    print(f"   {'Sequence':<30} | {rule.sequence}")
    print(f"   {'Active':<30} | {rule.active}")
    print(f"   {'Amount Type':<30} | {rule.amount_select}")

    if rule.amount_select == 'code':
        print(f"\n   💻 PYTHON CODE FORMULA:")
        print(f"   {'-' * 80}")
        if rule.amount_python_compute:
            # Show the formula with line numbers
            lines = rule.amount_python_compute.split('\n')
            for i, line in enumerate(lines, 1):
                print(f"   {i:3d} | {line}")
        else:
            print(f"   ⚠️  No Python code defined")
    elif rule.amount_select == 'percentage':
        print(f"\n   📊 PERCENTAGE FORMULA:")
        print(f"   {'-' * 80}")
        print(f"   Percentage: {rule.amount_percentage}%")
        print(f"   Based on: {rule.amount_percentage_base}")
    elif rule.amount_select == 'fix':
        print(f"\n   💵 FIXED AMOUNT:")
        print(f"   {'-' * 80}")
        print(f"   Amount: ${rule.amount_fix:,.2f}")

    # Check condition
    if rule.condition_select == 'python':
        print(f"\n   ⚙️  CONDITION (when to apply):")
        print(f"   {'-' * 80}")
        if rule.condition_python:
            lines = rule.condition_python.split('\n')
            for i, line in enumerate(lines, 1):
                print(f"   {i:3d} | {line}")
        else:
            print(f"   Always applied (no condition)")
    elif rule.condition_select == 'range':
        print(f"\n   ⚙️  CONDITION: Range-based")
        print(f"   Min: {rule.condition_range_min}, Max: {rule.condition_range_max}")
    else:
        print(f"\n   ⚙️  CONDITION: {rule.condition_select}")

# Now let's check what these formulas actually calculate for our 4 mismatched employees
print(f"\n{'=' * 140}")
print(f"📊 FORMULA VERIFICATION - Testing with our 4 mismatched employees")
print(f"{'=' * 140}")

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
test_employees = [
    'ARCIDES ARZOLA',
    'Rafael Perez',
    'SERGIO MANEIRO',
    'PABLO NAVARRO',
]

print(f"\n{'Employee':<20} | {'Deduction Base':>15} | {'SSO Actual':>12} | {'SSO 4%':>12} | {'FAOV Actual':>12} | {'FAOV 1%':>12} | {'PARO Actual':>12} | {'PARO 0.5%':>12}")
print(f"{'-' * 140}")

for emp_name in test_employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if not payslip:
        continue

    deduction_base = payslip.contract_id.ueipab_deduction_base

    # Get actual deductions
    sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')
    faov_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_FAOV_DED')
    paro_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_PARO_DED')

    sso_actual = abs(sso_line[0].total) if sso_line else 0.0
    faov_actual = abs(faov_line[0].total) if faov_line else 0.0
    paro_actual = abs(paro_line[0].total) if paro_line else 0.0

    # Calculate what they SHOULD be
    sso_expected = deduction_base * 0.04
    faov_expected = deduction_base * 0.01
    paro_expected = deduction_base * 0.005

    print(f"{emp_name:<20} | ${deduction_base:>14,.2f} | ${sso_actual:>11,.2f} | ${sso_expected:>11,.2f} | ${faov_actual:>11,.2f} | ${faov_expected:>11,.2f} | ${paro_actual:>11,.2f} | ${paro_expected:>11,.2f}")

print(f"\n{'=' * 140}")
print(f"💡 KEY QUESTION:")
print(f"   If the formulas show 4%, 1%, 0.5% - why are actual deductions at ~2.25%, 0.50%, 0.13%?")
print(f"   Possible causes:")
print(f"   1. Formula is applying percentage to WRONG base (not ueipab_deduction_base)")
print(f"   2. Formula has wrong percentage coded (e.g., 0.02 instead of 0.04)")
print(f"   3. Formula has condition that reduces amount for some employees")
print(f"   4. There's a salary rule applying AFTER that reduces these deductions")
print(f"{'=' * 140}")
