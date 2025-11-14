#!/usr/bin/env python3
"""
Test Payroll Disbursement Detail Report enhancements:
1. Salary/Bonus split
2. Exchange rate display in header
"""

# Get NOVIEMBRE15 batch
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15 batch not found")
    exit()

# Get Alejandra Lopez payslip
payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'ALEJANDRA LOPEZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if not payslip:
    print("❌ Alejandra Lopez payslip not found")
    exit()

print(f"📊 Testing with: {payslip.employee_id.name}")
print(f"   Batch: {batch.name}")
print(f"   Period: {payslip.date_from} to {payslip.date_to}")

# Calculate salary and bonus
salary_lines = payslip.line_ids.filtered(lambda l: l.total > 0 and l.salary_rule_id.code == 'VE_SALARY_70')
bonus_lines = payslip.line_ids.filtered(lambda l: l.total > 0 and l.salary_rule_id.code not in ('VE_NET', 'VE_SALARY_70'))

salary_amount = sum(salary_lines.mapped('total'))
bonus_amount = sum(bonus_lines.mapped('total'))

print(f"\n💰 Salary/Bonus Breakdown:")
print(f"   Salary (VE_SALARY_70): ${salary_amount:,.2f}")
print(f"   Bonus (all others):    ${bonus_amount:,.2f}")
print(f"   TOTAL:                 ${salary_amount + bonus_amount:,.2f}")

# Test report with VEB currency
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("\n❌ VEB currency not found")
    exit()

# Get exchange rate
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', payslip.date_to)
], limit=1, order='name desc')

if rate_record:
    print(f"\n💱 Exchange Rate Info:")
    print(f"   Date: {rate_record.name}")
    print(f"   Rate: {rate_record.company_rate:,.2f} VEB/USD")
    print(f"   Expected display: @ {rate_record.company_rate:.2f} VEB/USD")
else:
    print("\n⚠️  No exchange rate found")

# Test report model
report_model = env['report.ueipab_payroll_enhancements.disbursement_detail_doc']

data_veb = {
    'batch_name': batch.name,
    'currency_id': veb.id,
    'currency_name': veb.name,
    'payslip_ids': [payslip.id],
    'employee_count': 1,
    'payslip_count': 1,
}

print("\n🧪 Testing VEB Report Generation...")
try:
    report_values = report_model._get_report_values(
        docids=[payslip.id],
        data=data_veb
    )
    
    print("✅ Report generated successfully")
    print(f"   Currency: {report_values['currency'].name} ({report_values['currency'].symbol})")
    
    # Verify converted amounts
    if report_values['docs']:
        test_payslip = report_values['docs'][0]
        
        # Get salary line (converted to VEB)
        salary_line_veb = test_payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
        if salary_line_veb:
            veb_salary = salary_line_veb[0].total
            print(f"   Salary (VEB): Bs.{veb_salary:,.2f}")
            
        # Calculate expected
        if rate_record:
            expected_salary_veb = salary_amount * rate_record.company_rate
            expected_bonus_veb = bonus_amount * rate_record.company_rate
            print(f"   Expected Salary: Bs.{expected_salary_veb:,.2f}")
            print(f"   Expected Bonus: Bs.{expected_bonus_veb:,.2f}")

except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

