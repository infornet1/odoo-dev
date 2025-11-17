#!/usr/bin/env python3
"""
Check a regular bi-weekly payslip (not Aguinaldos) for Cesta Ticket
"""

print("=" * 80)
print("CHECKING REGULAR BI-WEEKLY PAYSLIP FOR CESTA TICKET")
print("=" * 80)

# Find a regular bi-weekly payslip (not Aguinaldos or Liquidacion)
regular_payslip = env['hr.payslip'].search([
    ('state', '=', 'done'),
    ('name', 'not ilike', 'aguinaldo'),
    ('name', 'not ilike', 'liquidacion'),
], order='date_to desc', limit=1)

if regular_payslip:
    print(f"\nPayslip: {regular_payslip.name}")
    print(f"Employee: {regular_payslip.employee_id.name}")
    print(f"Period: {regular_payslip.date_from} to {regular_payslip.date_to}")
    print(f"Structure: {regular_payslip.struct_id.name}")

    print("\n" + "-" * 80)
    print("PAYSLIP LINES:")
    print("-" * 80)

    for line in regular_payslip.line_ids.sorted('sequence'):
        category = line.category_id.code if line.category_id else 'N/A'
        print(f"{line.sequence:3d}. [{category:6s}] {line.code:20s} {line.name:45s} ${line.total:>10.2f}")

    # Check if Cesta Ticket appears
    cesta_line = regular_payslip.line_ids.filtered(lambda l: l.code == 'VE_CESTA_TICKET')

    print("\n" + "=" * 80)
    if cesta_line:
        print(f"✅ FOUND: VE_CESTA_TICKET = ${cesta_line.total:.2f}")
        print(f"   Formula used: {cesta_line.salary_rule_id.amount_python_compute[:200]}")
    else:
        print("⚠️  VE_CESTA_TICKET rule exists but didn't appear in this payslip")
        print("   Possible reasons:")
        print("   - Rule not linked to this payslip's structure")
        print("   - Contract cesta_ticket_usd is zero")
        print("   - Rule has condition that evaluated to False")
else:
    print("\n⚠️  No regular payslip found in database")

print("\n" + "=" * 80)

# Also check the VE_CESTA_TICKET rule details
cesta_rule = env['hr.salary.rule'].search([('code', '=', 'VE_CESTA_TICKET')], limit=1)

if cesta_rule:
    print("VE_CESTA_TICKET RULE DETAILS:")
    print("=" * 80)
    print(f"Name: {cesta_rule.name}")
    print(f"Code: {cesta_rule.code}")
    print(f"Sequence: {cesta_rule.sequence}")
    print(f"Category: {cesta_rule.category_id.code} - {cesta_rule.category_id.name}")
    print(f"Appears on Payslip: {cesta_rule.appears_on_payslip}")
    print(f"\nCondition: {cesta_rule.condition_select}")
    if cesta_rule.condition_python:
        print(f"Python Condition:\n{cesta_rule.condition_python}")

    print(f"\nFormula:")
    print(cesta_rule.amount_python_compute)

    print(f"\nLinked to structures:")
    for struct in cesta_rule.struct_id:
        print(f"  - {struct.name}")
