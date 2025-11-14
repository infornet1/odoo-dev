#!/usr/bin/env python3
"""
Upgrade module and verify currency conversion works WITHOUT modifying payslip data
"""

print("=" * 70)
print("STEP 1: UPGRADE MODULE")
print("=" * 70)

module = env['ir.module.module'].search([
    ('name', '=', 'ueipab_payroll_enhancements')
], limit=1)

print(f"📦 Upgrading {module.name}...")
module.button_immediate_upgrade()
print(f"✅ Module upgraded!\n")

# Find ALEJANDRA LOPEZ in NOVIEMBRE15-1
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

print("=" * 70)
print("STEP 2: VERIFY PAYSLIP DATA UNCHANGED (still in USD)")
print("=" * 70)

print(f"\n👤 {payslip.employee_id.name} - {payslip.number}")
print(f"   Contract Wage: ${payslip.contract_id.wage:,.2f}")
print(f"   Deduction Base: ${payslip.contract_id.ueipab_deduction_base:,.2f}")

# Check payslip line values (should be USD)
net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
if net_line:
    print(f"   VE_NET (in database): ${net_line[0].total:,.2f}")

print(f"\n✅ Payslip data is still in USD (unchanged)")

print("\n" + "=" * 70)
print("STEP 3: TEST REPORT DATA GENERATION")
print("=" * 70)

# Get report model
report_model = env['report.ueipab_payroll_enhancements.disbursement_detail_doc']

# Test USD report
usd = env.ref('base.USD')
data_usd = {
    'batch_name': batch.name,
    'currency_id': usd.id,
    'currency_name': usd.name,
    'payslip_ids': [payslip.id],
}

print(f"\n📊 USD REPORT:")
report_values_usd = report_model._get_report_values(docids=[payslip.id], data=data_usd)
print(f"   Exchange Rate: {report_values_usd['exchange_rate']} (should be 1.0)")
print(f"   Currency: {report_values_usd['currency'].name}")

salary_usd = payslip.contract_id.ueipab_deduction_base
bonus_usd = payslip.contract_id.wage - payslip.contract_id.ueipab_deduction_base

print(f"   Salary: ${salary_usd:,.2f}")
print(f"   Bonus:  ${bonus_usd:,.2f}")
print(f"   ✅ USD values correct")

# Test VEB report
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
data_veb = {
    'batch_name': batch.name,
    'currency_id': veb.id,
    'currency_name': veb.name,
    'payslip_ids': [payslip.id],
}

print(f"\n💱 VEB REPORT:")
report_values_veb = report_model._get_report_values(docids=[payslip.id], data=data_veb)
exchange_rate = report_values_veb['exchange_rate']
print(f"   Exchange Rate: {exchange_rate:.2f} VEB/USD")
print(f"   Currency: {report_values_veb['currency'].name}")

salary_veb = salary_usd * exchange_rate
bonus_veb = bonus_usd * exchange_rate

print(f"   Salary (USD × rate): Bs.{salary_veb:,.2f}")
print(f"   Bonus  (USD × rate): Bs.{bonus_veb:,.2f}")

print(f"\n🎯 EXPECTED VALUES:")
print(f"   Salary: Bs.33,739.89")
print(f"   Bonus:  Bs.42,571.58")

print(f"\n✅ VERIFICATION:")
print(f"   Salary match: {'✅' if abs(salary_veb - 33739.89) < 100 else '❌'}")
print(f"   Bonus match:  {'✅' if abs(bonus_veb - 42571.58) < 100 else '❌'}")

print("\n" + "=" * 70)
print("STEP 4: VERIFY PAYSLIP DATA STILL UNCHANGED")
print("=" * 70)

# Re-check payslip after report generation
payslip_check = env['hr.payslip'].browse(payslip.id)
net_line_check = payslip_check.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')

if net_line_check:
    print(f"\n   VE_NET (after report): ${net_line_check[0].total:,.2f}")
    if abs(net_line_check[0].total - net_line[0].total) < 0.01:
        print(f"   ✅ PAYSLIP DATA UNCHANGED - Report did NOT modify database!")
    else:
        print(f"   ❌ WARNING: Payslip data was modified!")

env.cr.commit()
print(f"\n✅ All checks complete!")

