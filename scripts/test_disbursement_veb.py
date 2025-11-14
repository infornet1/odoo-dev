#!/usr/bin/env python3
"""
Test Payroll Disbursement Detail Report with VEB currency conversion
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
], limit=1)  # Test with just first payslip

print(f"   Payslips found: {len(payslips)}")

if not payslips:
    print("❌ No payslips in batch")
    exit()

# Get currencies
usd = env.ref('base.USD')
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

if not veb:
    print("❌ VEB currency not found")
    exit()

print(f"\n💵 USD: {usd.name} ({usd.symbol})")
print(f"💵 VEB: {veb.name} ({veb.symbol})")

# Get test payslip
test_payslip = payslips[0]
print(f"\n👤 Test Employee: {test_payslip.employee_id.name}")
print(f"   Payslip period: {test_payslip.date_from} to {test_payslip.date_to}")

# Get NET amount in USD (original)
net_line = test_payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
if net_line:
    usd_net = net_line[0].total
    print(f"   Net (USD): ${usd_net:,.2f}")
else:
    print("❌ No NET line found")
    exit()

# Get exchange rate for payslip date
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', test_payslip.date_to)
], limit=1, order='name desc')

if rate_record:
    # Odoo stores inverse rate (VEB per USD)
    veb_per_usd = 1 / rate_record.rate
    print(f"   Exchange rate date: {rate_record.name}")
    print(f"   Exchange rate: 1 USD = {veb_per_usd:,.2f} VEB")
    expected_veb = usd_net * veb_per_usd
    print(f"   Expected Net (VEB): Bs.{expected_veb:,.2f}")
else:
    print("⚠️  No exchange rate found for payslip date")

# Test report model with VEB currency
report_model = env['report.ueipab_payroll_enhancements.disbursement_detail_doc']

data_veb = {
    'batch_name': batch.name,
    'currency_id': veb.id,
    'currency_name': veb.name,
    'payslip_ids': payslips.ids,
    'employee_count': len(payslips.mapped('employee_id')),
    'payslip_count': len(payslips),
}

print("\n🧪 Testing VEB Report Generation...")
try:
    report_values_veb = report_model._get_report_values(
        docids=payslips.ids,
        data=data_veb
    )
    
    print("✅ VEB report generated successfully")
    print(f"   Currency: {report_values_veb['currency'].name} ({report_values_veb['currency'].symbol})")
    print(f"   Payslips: {len(report_values_veb['docs'])}")
    
    # Check first payslip values (should be converted to VEB)
    if report_values_veb['docs']:
        first_payslip = report_values_veb['docs'][0]
        print(f"   Employee: {first_payslip.employee_id.name}")
        
        # Get NET amount (should now be in VEB)
        net_line_veb = first_payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
        if net_line_veb:
            actual_veb = net_line_veb[0].total
            print(f"   Actual Net (VEB): Bs.{actual_veb:,.2f}")
            
            # Verify conversion
            if rate_record:
                diff = abs(actual_veb - expected_veb)
                if diff < 1.0:  # Allow small rounding difference
                    print(f"   ✅ Conversion correct! (diff: Bs.{diff:.2f})")
                else:
                    print(f"   ⚠️  Conversion mismatch! (diff: Bs.{diff:.2f})")
    
except Exception as e:
    print(f"❌ Error generating VEB report: {str(e)}")
    import traceback
    traceback.print_exc()

