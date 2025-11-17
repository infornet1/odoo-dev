#!/usr/bin/env python3
"""
Investigate how Cesta Ticket is currently handled in V1 system
"""

print("=" * 80)
print("CESTA TICKET INVESTIGATION - V1 System")
print("=" * 80)

# Check contract field usage
print("\n[1] Checking contract field 'cesta_ticket_usd'...")
contracts = env['hr.contract'].search([('state', '=', 'open')], limit=5)

print(f"\nFound {len(contracts)} active contracts (showing first 5):")
for contract in contracts:
    print(f"\n  Employee: {contract.employee_id.name}")
    print(f"  - Wage: ${contract.wage:.2f}")
    print(f"  - Cesta Ticket USD: ${contract.cesta_ticket_usd:.2f}")
    print(f"  - Deduction Base: ${contract.ueipab_deduction_base:.2f}")

# Check if cesta_ticket_usd is used in any salary rules
print("\n" + "=" * 80)
print("[2] Checking salary rules that reference 'cesta_ticket'...")

ve_structure = env['hr.payroll.structure'].search([
    ('name', 'ilike', 'venezuela')
], limit=1)

if ve_structure:
    print(f"\nVenezuelan Structure: {ve_structure.name}")
    print(f"Rules in structure: {len(ve_structure.rule_ids)}")

    cesta_rules = []
    for rule in ve_structure.rule_ids:
        if 'cesta' in rule.code.lower() or 'cesta' in (rule.amount_python_compute or '').lower():
            cesta_rules.append(rule)
            print(f"\n  Rule: {rule.code} - {rule.name}")
            print(f"  Sequence: {rule.sequence}")
            print(f"  Formula: {rule.amount_python_compute[:200] if rule.amount_python_compute else 'N/A'}")

    if not cesta_rules:
        print("\n  ⚠️  No salary rules found that reference 'cesta_ticket'")
        print("  This means cesta_ticket_usd field exists but is NOT being used in payroll!")

# Check recent payslips to see if cesta appears
print("\n" + "=" * 80)
print("[3] Checking recent payslips for Cesta Ticket line items...")

recent_payslip = env['hr.payslip'].search([
    ('state', '=', 'done')
], order='date_to desc', limit=1)

if recent_payslip:
    print(f"\nMost recent payslip: {recent_payslip.name} ({recent_payslip.employee_id.name})")
    print(f"Date: {recent_payslip.date_from} to {recent_payslip.date_to}")
    print(f"\nPayslip lines containing 'cesta' or 'ticket':")

    cesta_lines = recent_payslip.line_ids.filtered(
        lambda l: 'cesta' in l.name.lower() or 'ticket' in l.name.lower()
    )

    if cesta_lines:
        for line in cesta_lines:
            print(f"  - {line.code}: {line.name} = ${line.total:.2f}")
    else:
        print("  ⚠️  No Cesta Ticket line found in payslip!")
        print("\n  All payslip lines:")
        for line in recent_payslip.line_ids.sorted('sequence'):
            print(f"    {line.sequence:3d}. {line.code:20s} {line.name:40s} ${line.total:>10.2f}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n1. The 'cesta_ticket_usd' field EXISTS in hr.contract")
print("2. It has a default value of $40.00")
print("3. Need to determine if it's actively used in V1 payroll calculations")
print("\n" + "=" * 80)
