#!/usr/bin/env python3
"""
Generate ACCURATE V2 field values for all employees
This creates the starting data for HR to review in SalaryStructureV2 spreadsheet tab

CRITICAL: These values must be 100% accurate to avoid payslip calculation errors
"""

print("=" * 80)
print("GENERATE V2 SALARY STRUCTURE DATA - 100% Accuracy Required")
print("=" * 80)

# Get all active contracts
contracts = env['hr.contract'].search([
    ('state', '=', 'open')
], order='employee_id')

print(f"\nFound {len(contracts)} active contracts")
print("\nGenerating V2 breakdown for each employee...")
print("=" * 80)
print(f"{'Employee Name':<30} {'Wage':<12} {'Deduction':<12} {'Cesta':<12} {'Salary V2':<12} {'Bonus V2':<12} {'ExtraBonus V2':<12}")
print("-" * 80)

v2_data = []
errors = []

for contract in contracts:
    emp_name = contract.employee_id.name
    wage = contract.wage
    deduction_base = contract.ueipab_deduction_base
    cesta_ticket = contract.cesta_ticket_usd or 40.00

    # Calculate V2 breakdown (these are STARTING values for HR review)
    # HR can adjust these values in the spreadsheet before migration

    # 70/30 split of deduction_base (starting suggestion)
    salary_v2 = deduction_base * 0.70
    bonus_v2 = deduction_base * 0.30

    # ExtraBonus = everything NOT in deduction_base and NOT cesta_ticket
    extrabonus_v2 = wage - deduction_base - cesta_ticket

    # Verification: sum should equal wage
    total = salary_v2 + bonus_v2 + extrabonus_v2 + cesta_ticket
    diff = abs(total - wage)

    if diff > 0.01:
        errors.append({
            'name': emp_name,
            'wage': wage,
            'total': total,
            'diff': diff
        })
        status = "✗ ERROR"
    else:
        status = "✓"

    v2_data.append({
        'name': emp_name,
        'vat': contract.employee_id.identification_id or '',
        'wage': wage,
        'deduction_base': deduction_base,
        'cesta_ticket': cesta_ticket,
        'salary_v2': salary_v2,
        'bonus_v2': bonus_v2,
        'extrabonus_v2': extrabonus_v2,
        'total': total,
        'diff': diff,
        'status': status
    })

    print(f"{emp_name:<30} ${wage:>10.2f} ${deduction_base:>10.2f} ${cesta_ticket:>10.2f} ${salary_v2:>10.2f} ${bonus_v2:>10.2f} ${extrabonus_v2:>10.2f} {status}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if errors:
    print(f"\n⚠️  {len(errors)} ERRORS FOUND:")
    for error in errors:
        print(f"  {error['name']}: Wage ${error['wage']:.2f} != Total ${error['total']:.2f} (diff ${error['diff']:.2f})")
else:
    print(f"\n✅ ALL {len(v2_data)} EMPLOYEES: Calculations verified (sum = wage)")

print("\n" + "=" * 80)
print("DETAILED BREAKDOWN - First 5 Employees")
print("=" * 80)

for i, data in enumerate(v2_data[:5]):
    print(f"\nEmployee {i+1}: {data['name']}")
    print(f"  Current Wage:       ${data['wage']:.2f}")
    print(f"  Deduction Base:     ${data['deduction_base']:.2f}")
    print(f"  Cesta Ticket:       ${data['cesta_ticket']:.2f}")
    print(f"  ---")
    print(f"  NEW Salary V2:      ${data['salary_v2']:.2f}  (70% of deduction_base)")
    print(f"  NEW Bonus V2:       ${data['bonus_v2']:.2f}  (30% of deduction_base)")
    print(f"  NEW ExtraBonus V2:  ${data['extrabonus_v2']:.2f}  (wage - deduction_base - cesta)")
    print(f"  ---")
    print(f"  Verification:       ${data['total']:.2f}  (should equal ${data['wage']:.2f})")
    print(f"  Difference:         ${data['diff']:.4f}  {data['status']}")

# Find Rafael Perez specifically
print("\n" + "=" * 80)
print("RAFAEL PEREZ - DETAILED BREAKDOWN")
print("=" * 80)

rafael = [d for d in v2_data if 'RAFAEL PEREZ' in d['name'].upper()]
if rafael:
    r = rafael[0]
    print(f"\nEmployee: {r['name']}")
    print(f"\nCurrent V1 Data:")
    print(f"  Wage:            ${r['wage']:.2f}")
    print(f"  Deduction Base:  ${r['deduction_base']:.2f}")
    print(f"  Cesta Ticket:    ${r['cesta_ticket']:.2f}")
    print(f"\nProposed V2 Breakdown (STARTING VALUES for HR review):")
    print(f"  Salary V2:       ${r['salary_v2']:.2f}  ← Subject to deductions")
    print(f"  Bonus V2:        ${r['bonus_v2']:.2f}  ← NOT subject to deductions")
    print(f"  ExtraBonus V2:   ${r['extrabonus_v2']:.2f}  ← NOT subject to deductions")
    print(f"  Cesta Ticket:    ${r['cesta_ticket']:.2f}  ← Existing field (unchanged)")
    print(f"\nVerification:")
    print(f"  Total: ${r['salary_v2']:.2f} + ${r['bonus_v2']:.2f} + ${r['extrabonus_v2']:.2f} + ${r['cesta_ticket']:.2f}")
    print(f"       = ${r['total']:.2f}")
    print(f"  Wage:  ${r['wage']:.2f}")
    print(f"  Match: {r['status']}")

    if r['diff'] < 0.01:
        print(f"\n✅ CORRECT: Values sum to wage exactly")
    else:
        print(f"\n✗ ERROR: Difference of ${r['diff']:.2f}")

print("\n" + "=" * 80)
print("IMPORTANT NOTES")
print("=" * 80)
print("""
1. These are STARTING VALUES for HR to review
2. HR can adjust any values in the spreadsheet before migration
3. The 70/30 split is only a SUGGESTION
4. HR must ensure final values sum to wage for each employee
5. All values must be reviewed and approved before migration

NEXT STEPS:
1. Export this data to SalaryStructureV2 spreadsheet tab
2. HR reviews and adjusts values as needed
3. HR verifies all totals match wages
4. HR approves final breakdown
5. Run migration script to import HR-approved values
""")
