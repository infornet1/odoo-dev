#!/usr/bin/env python3
"""
SNAPSHOT: Capture payslip data BEFORE generating USD report
This will save current values to compare after report generation
"""

import json

# Find NOVIEMBRE15-2 batch
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15-2 batch not found")
    print("\n📋 Available batches:")
    batches = env['hr.payslip.run'].search([], order='id desc', limit=10)
    for b in batches:
        print(f"   - {b.name} (ID: {b.id})")
    exit()

payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print("=" * 80)
print(f"📸 SNAPSHOT: NOVIEMBRE15-2 BEFORE USD REPORT")
print("=" * 80)
print(f"\nBatch: {batch.name} (ID: {batch.id})")
print(f"Payslips: {len(payslips)}")

# Capture all payslip data
snapshot = {}

print(f"\n{'Employee':<25} | {'Contract':>12} | {'VE_NET':>15} | {'VE_SALARY_70':>15}")
print("=" * 80)

for payslip in payslips.sorted(lambda p: p.employee_id.name):
    wage = payslip.contract_id.wage
    
    # Get key payslip line values
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    
    net_value = net_line[0].total if net_line else 0.0
    salary_value = salary_line[0].total if salary_line else 0.0
    
    # Store snapshot
    snapshot[payslip.id] = {
        'number': payslip.number,
        'employee': payslip.employee_id.name,
        'wage': wage,
        'net': net_value,
        'salary': salary_value,
    }
    
    print(f"{payslip.employee_id.name[:24]:<25} | ${wage:>11,.2f} | ${net_value:>14,.2f} | ${salary_value:>14,.2f}")

# Save snapshot to file
snapshot_file = '/tmp/noviembre15_2_before_usd.json'
with open(snapshot_file, 'w') as f:
    json.dump(snapshot, f, indent=2)

print(f"\n✅ Snapshot saved to: {snapshot_file}")
print(f"\n📊 SUMMARY:")
print(f"   Total payslips captured: {len(snapshot)}")
print(f"   All values are in USD (contract wage range: ${min(p['wage'] for p in snapshot.values()):.2f} - ${max(p['wage'] for p in snapshot.values()):.2f})")

# Check if any values look corrupted already
corrupted = [p for p in snapshot.values() if p['net'] > p['wage'] * 10]
if corrupted:
    print(f"\n⚠️  WARNING: {len(corrupted)} payslips already look corrupted!")
    for p in corrupted[:5]:
        print(f"   - {p['employee']}: NET ${p['net']:,.2f} vs Wage ${p['wage']:,.2f}")
else:
    print(f"\n✅ All payslips look clean (NET values reasonable)")

print(f"\n👉 NOW: Generate the USD report in Odoo UI")
print(f"👉 THEN: Run monitor_after_usd_report.py to check for changes")

