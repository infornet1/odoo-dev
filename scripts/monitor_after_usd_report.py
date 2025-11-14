#!/usr/bin/env python3
"""
VERIFICATION: Check if payslip data changed AFTER generating USD report
Compares against snapshot taken before report generation
"""

import json
import os

snapshot_file = '/tmp/noviembre15_2_before_usd.json'

if not os.path.exists(snapshot_file):
    print("❌ Snapshot file not found!")
    print("   Run monitor_before_usd_report.py first")
    exit()

# Load snapshot
with open(snapshot_file, 'r') as f:
    snapshot_before = json.load(f)

print("=" * 80)
print(f"🔍 VERIFICATION: NOVIEMBRE15-2 AFTER USD REPORT")
print("=" * 80)

# Get current data
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print(f"\nBatch: {batch.name}")
print(f"Payslips checked: {len(payslips)}")

changes_detected = []
no_changes = []

print(f"\n{'Employee':<25} | {'NET Before':>15} | {'NET After':>15} | Status")
print("=" * 80)

for payslip in payslips:
    payslip_id_str = str(payslip.id)
    
    if payslip_id_str not in snapshot_before:
        print(f"⚠️  {payslip.employee_id.name}: NEW PAYSLIP (not in snapshot)")
        continue
    
    before = snapshot_before[payslip_id_str]
    
    # Get current values
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    
    net_after = net_line[0].total if net_line else 0.0
    salary_after = salary_line[0].total if salary_line else 0.0
    
    # Compare
    net_changed = abs(net_after - before['net']) > 0.01
    salary_changed = abs(salary_after - before['salary']) > 0.01
    
    if net_changed or salary_changed:
        status = "❌ CHANGED!"
        changes_detected.append({
            'employee': payslip.employee_id.name,
            'net_before': before['net'],
            'net_after': net_after,
            'salary_before': before['salary'],
            'salary_after': salary_after,
        })
    else:
        status = "✅ UNCHANGED"
        no_changes.append(payslip.employee_id.name)
    
    print(f"{payslip.employee_id.name[:24]:<25} | ${before['net']:>14,.2f} | ${net_after:>14,.2f} | {status}")

print("=" * 80)

print(f"\n📊 SUMMARY:")
print(f"   Unchanged payslips: {len(no_changes)}")
print(f"   Changed payslips:   {len(changes_detected)}")

if changes_detected:
    print(f"\n❌ DATABASE MODIFICATION DETECTED!")
    print(f"\n   Details of changed payslips:")
    for change in changes_detected[:10]:  # Show first 10
        print(f"\n   {change['employee']}:")
        print(f"      NET:         ${change['net_before']:>14,.2f} → ${change['net_after']:>14,.2f}")
        print(f"      VE_SALARY_70: ${change['salary_before']:>14,.2f} → ${change['salary_after']:>14,.2f}")
    
    if len(changes_detected) > 10:
        print(f"\n   ... and {len(changes_detected) - 10} more")
    
    print(f"\n⚠️  THE REPORT IS STILL MODIFYING THE DATABASE!")
else:
    print(f"\n✅ NO DATABASE MODIFICATION!")
    print(f"   All {len(no_changes)} payslips remained unchanged.")
    print(f"   The fix is working correctly! 🎉")

