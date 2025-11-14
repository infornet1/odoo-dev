#!/usr/bin/env python3
"""
Verify new Salary/Bonus calculation using contract fields
READONLY - no modifications
"""

# Find ALEJANDRA LOPEZ in NOVIEMBRE15-1
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

print(f"✅ {payslip.employee_id.name} - {payslip.number}")
print(f"=" * 60)

# New calculation method (using contract fields)
salary_new = payslip.contract_id.ueipab_deduction_base or 0.0
bonus_new = (payslip.contract_id.wage or 0.0) - (payslip.contract_id.ueipab_deduction_base or 0.0)

print(f"\n📊 NEW CALCULATION (using contract fields):")
print(f"   Salary (contract.ueipab_deduction_base): ${salary_new:,.2f}")
print(f"   Bonus  (wage - deduction_base):          ${bonus_new:,.2f}")
print(f"   Total:                                   ${salary_new + bonus_new:,.2f}")

print(f"\n🎯 USER EXPECTED VALUES:")
print(f"   Salary:  $143.65")
print(f"   Bonus:   $181.25")
print(f"   Total:   $324.90")

print(f"\n✅ MATCH CHECK:")
print(f"   Salary: ${salary_new:,.2f} vs $143.65 - {'✅ PERFECT MATCH!' if abs(salary_new - 143.65) < 0.01 else '❌'}")
print(f"   Bonus:  ${bonus_new:,.2f} vs $181.25 - {'✅ MATCH!' if abs(bonus_new - 181.25) < 0.01 else '❌'}")
print(f"   Total:  ${salary_new + bonus_new:,.2f} vs ${payslip.contract_id.wage:,.2f} (wage) - {'✅' if abs((salary_new + bonus_new) - payslip.contract_id.wage) < 0.01 else '❌'}")

# Check VEB conversion
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
if veb:
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', payslip.date_to)
    ], limit=1, order='name desc')
    if rate_record:
        veb_rate = rate_record.company_rate
        salary_veb = salary_new * veb_rate
        bonus_veb = bonus_new * veb_rate
        
        print(f"\n💱 VEB CONVERSION (@ {veb_rate:.2f} VEB/USD):")
        print(f"   Salary: Bs.{salary_veb:,.2f}")
        print(f"   Bonus:  Bs.{bonus_veb:,.2f}")
        print(f"   Total:  Bs.{salary_veb + bonus_veb:,.2f}")
        
        print(f"\n🎯 USER REPORTED VEB VALUES:")
        print(f"   Salary: Bs.33,739.89")
        print(f"   Bonus:  Bs.42,571.58")
        
        print(f"\n✅ VEB MATCH CHECK:")
        print(f"   Salary: Bs.{salary_veb:,.2f} vs Bs.33,739.89 - {'✅ MATCH!' if abs(salary_veb - 33739.89) < 1 else '❌'}")
        print(f"   Bonus:  Bs.{bonus_veb:,.2f} vs Bs.42,571.58 - {'✅ MATCH!' if abs(bonus_veb - 42571.58) < 1 else '❌'}")

