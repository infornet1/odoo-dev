#!/usr/bin/env python3
"""
Check currency settings on SLIP/569 (ALEJANDRA LOPEZ in NOVIEMBRE15-1)
READONLY - no modifications
"""

# Find SLIP/569
payslip = env['hr.payslip'].search([('number', '=', 'SLIP/569')], limit=1)

if not payslip:
    print("❌ SLIP/569 not found")
    exit()

print(f"📊 SLIP/569 (ALEJANDRA LOPEZ) - NOVIEMBRE15-1")
print(f"=" * 60)

# Check contract
print(f"\n💼 CONTRACT:")
print(f"   Wage: ${payslip.contract_id.wage:,.2f}")
print(f"   Currency: {payslip.contract_id.currency_id.name if hasattr(payslip.contract_id, 'currency_id') and payslip.contract_id.currency_id else 'Not set'}")

# Check company currency
print(f"\n🏢 COMPANY:")
print(f"   Currency: {payslip.company_id.currency_id.name} ({payslip.company_id.currency_id.symbol})")

# Check if payslip has currency field
if hasattr(payslip, 'currency_id') and payslip.currency_id:
    print(f"\n💵 PAYSLIP CURRENCY:")
    print(f"   Currency: {payslip.currency_id.name} ({payslip.currency_id.symbol})")
else:
    print(f"\n💵 PAYSLIP CURRENCY: Not set (uses company currency)")

# Expected values if contract wage is $324.91
expected_salary_70 = payslip.contract_id.wage * 0.70
actual_salary = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')[0].total

print(f"\n🔍 ANALYSIS:")
print(f"   Expected VE_SALARY_70 (70% of wage): ${expected_salary_70:,.2f}")
print(f"   Actual VE_SALARY_70:                 ${actual_salary:,.2f}")
print(f"   Multiplier:                          {actual_salary / expected_salary_70:.2f}x")

# Check VEB exchange rate
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
if veb:
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', payslip.date_to)
    ], limit=1, order='name desc')
    if rate_record:
        veb_rate = rate_record.company_rate
        print(f"   VEB Exchange Rate:                   {veb_rate:.2f} VEB/USD")
        print(f"   Expected if converted from VEB:      ${actual_salary / veb_rate:,.2f}")

print(f"\n⚠️  ISSUE DETECTED:")
if actual_salary / expected_salary_70 > 100:
    print(f"   Payslip values are ~{actual_salary / expected_salary_70:.0f}x larger than expected!")
    print(f"   This suggests VEB values were stored in the USD amount field.")
    print(f"   The payslip was likely computed with wrong currency settings.")

