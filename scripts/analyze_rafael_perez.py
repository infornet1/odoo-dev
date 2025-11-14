#!/usr/bin/env python3
"""
DIAGNOSIS: Analyze RAFAEL PEREZ payslip to understand extra bonus calculation
NO DATABASE MODIFICATIONS - pure analysis
"""

# Find RAFAEL PEREZ in NOVIEMBRE15-2
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'RAFAEL PEREZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if not payslip:
    print("❌ RAFAEL PEREZ not found in NOVIEMBRE15-2")
    exit()

print("=" * 80)
print(f"🔍 DIAGNOSIS: {payslip.employee_id.name} ({payslip.number})")
print("=" * 80)

# Contract info
print(f"\n💼 CONTRACT:")
print(f"   Total Wage:        ${payslip.contract_id.wage:,.2f}")
print(f"   Deduction Base:    ${payslip.contract_id.ueipab_deduction_base:,.2f}")
print(f"   Difference:        ${payslip.contract_id.wage - payslip.contract_id.ueipab_deduction_base:,.2f}")

# Current report calculation (using contract fields)
salary_report = payslip.contract_id.ueipab_deduction_base or 0.0
bonus_report = (payslip.contract_id.wage or 0.0) - (payslip.contract_id.ueipab_deduction_base or 0.0)

print(f"\n📊 CURRENT REPORT CALCULATION (contract fields):")
print(f"   Salary (deduction_base):      ${salary_report:,.2f}")
print(f"   Bonus (wage - deduction_base): ${bonus_report:,.2f}")
print(f"   Total:                         ${salary_report + bonus_report:,.2f}")

# Show ALL payslip lines
print(f"\n💰 ALL PAYSLIP LINES (from database):")
print(f"{'Rule Code':<25} | {'Category':<15} | {'Total (USD)':>15} | Type")
print("=" * 80)

earnings_total = 0.0
deductions_total = 0.0

for line in payslip.line_ids.sorted(lambda l: l.sequence):
    if line.total != 0:
        line_type = "📈 Earning" if line.total > 0 else "📉 Deduction"
        category = line.category_id.name if line.category_id else "N/A"
        print(f"{line.salary_rule_id.code:<25} | {category:<15} | ${line.total:>14,.2f} | {line_type}")
        
        if line.total > 0 and line.salary_rule_id.code not in ('VE_GROSS', 'VE_NET'):
            earnings_total += line.total
        elif line.total < 0:
            deductions_total += abs(line.total)

# Check if there are extra earning lines beyond standard
standard_earnings = ['VE_SALARY_70', 'VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET']
extra_earnings = []

print(f"\n🔍 EARNINGS BREAKDOWN:")
print(f"{'Rule Code':<25} | {'Amount (USD)':>15} | Category")
print("-" * 80)

for line in payslip.line_ids.filtered(lambda l: l.total > 0 and l.salary_rule_id.code not in ('VE_GROSS', 'VE_NET')):
    is_standard = line.salary_rule_id.code in standard_earnings
    category = "Standard" if is_standard else "⭐ EXTRA"
    
    if not is_standard:
        extra_earnings.append({
            'code': line.salary_rule_id.code,
            'name': line.salary_rule_id.name,
            'amount': line.total,
        })
    
    print(f"{line.salary_rule_id.code:<25} | ${line.total:>14,.2f} | {category}")

print("-" * 80)
print(f"{'TOTAL EARNINGS (excl GROSS/NET)':<25} | ${earnings_total:>14,.2f}")

if extra_earnings:
    print(f"\n⭐ EXTRA EARNINGS DETECTED:")
    print(f"   Count: {len(extra_earnings)}")
    for extra in extra_earnings:
        print(f"   - {extra['code']}: {extra['name']} = ${extra['amount']:,.2f}")
    
    extra_total = sum(e['amount'] for e in extra_earnings)
    print(f"\n   Total Extra Earnings: ${extra_total:,.2f}")
    
    print(f"\n🤔 ISSUE IDENTIFIED:")
    print(f"   Current report uses contract.wage - contract.ueipab_deduction_base")
    print(f"   This gives: ${bonus_report:,.2f}")
    print(f"\n   But actual earnings in payslip include extra lines:")
    
    # Calculate what bonus SHOULD be based on payslip lines
    salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    salary_from_line = salary_line[0].total if salary_line else 0.0
    
    bonus_from_lines = earnings_total - salary_from_line
    
    print(f"   - Salary (VE_SALARY_70):     ${salary_from_line:,.2f}")
    print(f"   - Bonus (all other earnings): ${bonus_from_lines:,.2f}")
    print(f"   - Total:                      ${earnings_total:,.2f}")
    
    print(f"\n   Difference in Bonus calculation:")
    print(f"   Contract method:  ${bonus_report:,.2f}")
    print(f"   Payslip method:   ${bonus_from_lines:,.2f}")
    print(f"   Gap:              ${abs(bonus_report - bonus_from_lines):,.2f}")

else:
    print(f"\n✅ No extra earnings detected - standard structure only")

# Compare with ALEJANDRA LOPEZ for reference
alejandra = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if alejandra:
    print(f"\n📊 COMPARISON WITH ALEJANDRA LOPEZ (standard case):")
    print(f"\n{'Field':<30} | {'RAFAEL PEREZ':>15} | {'ALEJANDRA LOPEZ':>15}")
    print("-" * 70)
    print(f"{'Contract Wage':<30} | ${payslip.contract_id.wage:>14,.2f} | ${alejandra.contract_id.wage:>14,.2f}")
    print(f"{'Deduction Base':<30} | ${payslip.contract_id.ueipab_deduction_base:>14,.2f} | ${alejandra.contract_id.ueipab_deduction_base:>14,.2f}")
    print(f"{'Total Earnings (from lines)':<30} | ${earnings_total:>14,.2f} | ${sum(l.total for l in alejandra.line_ids if l.total > 0 and l.salary_rule_id.code not in ('VE_GROSS', 'VE_NET')):>14,.2f}")

print("\n" + "=" * 80)
print("📋 DIAGNOSIS COMPLETE")
print("=" * 80)

