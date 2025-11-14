#!/usr/bin/env python3
"""
Test Payroll Disbursement Detail Report with USD currency
"""

# Get first available payslip batch
batch = env['hr.payslip.run'].search([], limit=1, order='id desc')

if not batch:
    print("❌ No payslip batches found")
    exit()

print(f"📊 Testing with batch: {batch.name}")
print(f"   Batch ID: {batch.id}")

# Get payslips from batch
payslips = env['hr.payslip'].search([
    ('payslip_run_id', '=', batch.id),
    ('state', '!=', 'cancel')
])

print(f"   Payslips found: {len(payslips)}")

if not payslips:
    print("❌ No payslips in batch")
    exit()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

print(f"\n💵 USD: {usd.name} ({usd.symbol})")
if veb:
    print(f"💵 VEB: {veb.name} ({veb.symbol})")
else:
    print("⚠️  VEB currency not found")

# Test report model with USD currency
report_model = env['report.ueipab_payroll_enhancements.disbursement_detail_doc']

data_usd = {
    'batch_name': batch.name,
    'currency_id': usd.id,
    'currency_name': usd.name,
    'payslip_ids': payslips.ids,
    'employee_count': len(payslips.mapped('employee_id')),
    'payslip_count': len(payslips),
}

print("\n🧪 Testing USD Report Generation...")
try:
    report_values_usd = report_model._get_report_values(
        docids=payslips.ids,
        data=data_usd
    )
    
    print("✅ USD report generated successfully")
    print(f"   Currency: {report_values_usd['currency'].name} ({report_values_usd['currency'].symbol})")
    print(f"   Payslips: {len(report_values_usd['docs'])}")
    
    # Check first payslip values
    if report_values_usd['docs']:
        first_payslip = report_values_usd['docs'][0]
        print(f"   First employee: {first_payslip.employee_id.name}")
        
        # Get NET amount
        net_line = first_payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
        if net_line:
            print(f"   Net amount: ${net_line[0].total:,.2f}")
    
except Exception as e:
    print(f"❌ Error generating USD report: {str(e)}")
    import traceback
    traceback.print_exc()

