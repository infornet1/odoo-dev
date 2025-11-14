#!/usr/bin/env python3
"""
SNAPSHOT: Capture payslip data BEFORE generating VEB report
Critical check to ensure VEB report doesn't modify database
"""

import json

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print("=" * 80)
print(f"📸 SNAPSHOT: NOVIEMBRE15-2 BEFORE VEB REPORT")
print("=" * 80)
print(f"\nBatch: {batch.name} (ID: {batch.id})")
print(f"Payslips: {len(payslips)}")

# Focus on ALEJANDRA LOPEZ for detailed tracking
alejandra = payslips.filtered(lambda p: 'ALEJANDRA' in p.employee_id.name.upper())

if alejandra:
    print(f"\n🎯 FOCUS: {alejandra[0].employee_id.name} (for detailed tracking)")
    print(f"   Payslip: {alejandra[0].number}")
    print(f"   Contract Wage: ${alejandra[0].contract_id.wage:,.2f}")
    print(f"   Deduction Base: ${alejandra[0].contract_id.ueipab_deduction_base:,.2f}")
    
    # Get all important line values
    for code in ['VE_SALARY_70', 'VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET', 'VE_GROSS', 'VE_NET']:
        line = alejandra[0].line_ids.filtered(lambda l: l.salary_rule_id.code == code)
        if line:
            print(f"   {code:<20}: ${line[0].total:>14,.2f}")

# Capture snapshot for all payslips
snapshot = {}

print(f"\n{'Employee':<25} | {'VE_NET (USD)':>15} | {'VE_GROSS (USD)':>15}")
print("=" * 80)

for payslip in payslips.sorted(lambda p: p.employee_id.name):
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    gross_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
    salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    
    net_value = net_line[0].total if net_line else 0.0
    gross_value = gross_line[0].total if gross_line else 0.0
    salary_value = salary_line[0].total if salary_line else 0.0
    
    snapshot[payslip.id] = {
        'number': payslip.number,
        'employee': payslip.employee_id.name,
        'wage': payslip.contract_id.wage,
        'deduction_base': payslip.contract_id.ueipab_deduction_base,
        'net': net_value,
        'gross': gross_value,
        'salary': salary_value,
    }
    
    # Show first 5 employees
    if len([p for p in snapshot.values()]) <= 5:
        print(f"{payslip.employee_id.name[:24]:<25} | ${net_value:>14,.2f} | ${gross_value:>14,.2f}")

print(f"   ... and {len(payslips) - 5} more")

# Save snapshot
snapshot_file = '/tmp/noviembre15_2_before_veb.json'
with open(snapshot_file, 'w') as f:
    json.dump(snapshot, f, indent=2)

print(f"\n✅ Snapshot saved to: {snapshot_file}")

# Get VEB exchange rate for reference
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)
if veb:
    rate_record = env['res.currency.rate'].search([
        ('currency_id', '=', veb.id),
        ('name', '<=', max(payslips.mapped('date_to')))
    ], limit=1, order='name desc')
    if rate_record:
        print(f"\n💱 VEB Exchange Rate: {rate_record.company_rate:.2f} VEB/USD")
        
        if alejandra:
            net_usd = snapshot[alejandra[0].id]['net']
            expected_veb = net_usd * rate_record.company_rate
            print(f"\n🎯 EXPECTED VEB VALUES (for Alejandra Lopez):")
            print(f"   NET USD:           ${net_usd:,.2f}")
            print(f"   Expected NET VEB:  Bs.{expected_veb:,.2f}")
            print(f"   (Should display in report, NOT stored in database)")

print("\n" + "=" * 80)
print("⚠️  CRITICAL: All values above are in USD")
print("   They MUST remain unchanged after VEB report generation!")
print("=" * 80)

print(f"\n👉 NOW: Generate VEB report in Odoo UI")
print(f"   - Select NOVIEMBRE15-2 batch")
print(f"   - Currency: VEB")
print(f"   - Generate Report")
print(f"\n👉 THEN: Run monitor_after_veb_report.py to verify NO database changes")

