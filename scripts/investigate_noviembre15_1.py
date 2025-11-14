#!/usr/bin/env python3
"""
READONLY investigation of NOVIEMBRE15-1 batch and ALEJANDRA LOPEZ payslip
NO DATABASE MODIFICATIONS!
"""

# Find NOVIEMBRE15-1 batch
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15-1 batch not found")
    print("\n📋 Available batches:")
    batches = env['hr.payslip.run'].search([], order='id desc', limit=10)
    for b in batches:
        print(f"   - {b.name} (ID: {b.id})")
    exit()

print(f"✅ Found batch: {batch.name} (ID: {batch.id})")

# Find ALEJANDRA LOPEZ in this batch
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if not payslip:
    print("❌ ALEJANDRA LOPEZ not found in NOVIEMBRE15-1")
    exit()

print(f"\n👤 Employee: {payslip.employee_id.name}")
print(f"   Payslip: {payslip.number}")
print(f"   State: {payslip.state}")
print(f"   Period: {payslip.date_from} to {payslip.date_to}")

# Get contract wage
if payslip.contract_id:
    print(f"   Contract Wage: ${payslip.contract_id.wage:,.2f}")

print(f"\n💰 PAYSLIP LINE BREAKDOWN:")
print(f"{'Rule Code':<20} | {'Amount':>12}")
print("=" * 35)

# Show ALL lines ordered by sequence
for line in payslip.line_ids.sorted(lambda l: l.sequence):
    if line.total != 0:
        print(f"{line.salary_rule_id.code:<20} | ${line.total:>11,.2f}")

# Calculate Salary (VE_SALARY_70)
salary_lines = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
salary_amount = sum(salary_lines.mapped('total')) if salary_lines else 0.0

# Calculate Bonus (excluding VE_NET, VE_SALARY_70, VE_GROSS)
bonus_lines = payslip.line_ids.filtered(lambda l: l.total > 0 and l.salary_rule_id.code not in ('VE_NET', 'VE_SALARY_70', 'VE_GROSS'))
bonus_amount = sum(bonus_lines.mapped('total'))

# Get GROSS
gross_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
gross_amount = gross_line[0].total if gross_line else 0.0

# Get NET
net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
net_amount = net_line[0].total if net_line else 0.0

print(f"\n📊 CALCULATED VALUES (per report template logic):")
print(f"   Salary (VE_SALARY_70):        ${salary_amount:,.2f}")
print(f"   Bonus (all others):           ${bonus_amount:,.2f}")
print(f"   Salary + Bonus =              ${salary_amount + bonus_amount:,.2f}")
print(f"   GROSS (from payslip):         ${gross_amount:,.2f}")
print(f"   NET (from payslip):           ${net_amount:,.2f}")

print(f"\n🎯 USER EXPECTED VALUES:")
print(f"   Salary:  $143.65")
print(f"   Bonus:   $181.25")
print(f"   Total:   $324.90")

print(f"\n🔍 COMPARISON:")
print(f"   Salary match: ${salary_amount:,.2f} vs $143.65 - {'✅' if abs(salary_amount - 143.65) < 1 else '❌ MISMATCH'}")
print(f"   Bonus match:  ${bonus_amount:,.2f} vs $181.25 - {'✅' if abs(bonus_amount - 181.25) < 1 else '❌ MISMATCH'}")

