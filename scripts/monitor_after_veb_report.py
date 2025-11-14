#!/usr/bin/env python3
"""
CRITICAL VERIFICATION: Check if VEB report modified payslip database
This is the main test to ensure the fix is working!
"""

import json
import os

snapshot_file = '/tmp/noviembre15_2_before_veb.json'

if not os.path.exists(snapshot_file):
    print("❌ Snapshot file not found!")
    print("   Run monitor_before_veb_report.py first")
    exit()

# Load snapshot
with open(snapshot_file, 'r') as f:
    snapshot_before = json.load(f)

print("=" * 80)
print(f"🔍 CRITICAL VERIFICATION: AFTER VEB REPORT GENERATION")
print("=" * 80)

# Get current data
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print(f"\nBatch: {batch.name}")
print(f"Payslips checked: {len(payslips)}")

# Focus on ALEJANDRA LOPEZ
alejandra = payslips.filtered(lambda p: 'ALEJANDRA' in p.employee_id.name.upper())

if alejandra:
    payslip_id_str = str(alejandra[0].id)
    before = snapshot_before.get(payslip_id_str, {})
    
    print(f"\n🎯 DETAILED CHECK: {alejandra[0].employee_id.name}")
    print(f"=" * 80)
    
    # Get current values
    net_line = alejandra[0].line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    gross_line = alejandra[0].line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
    salary_line = alejandra[0].line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    
    net_after = net_line[0].total if net_line else 0.0
    gross_after = gross_line[0].total if gross_line else 0.0
    salary_after = salary_line[0].total if salary_line else 0.0
    
    print(f"\n{'Field':<20} | {'Before (USD)':>18} | {'After':>18} | Status")
    print("-" * 80)
    print(f"{'Contract Wage':<20} | ${before.get('wage', 0):>17,.2f} | ${alejandra[0].contract_id.wage:>17,.2f} | {'✅' if abs(alejandra[0].contract_id.wage - before.get('wage', 0)) < 0.01 else '❌ CHANGED!'}")
    print(f"{'Deduction Base':<20} | ${before.get('deduction_base', 0):>17,.2f} | ${alejandra[0].contract_id.ueipab_deduction_base:>17,.2f} | {'✅' if abs(alejandra[0].contract_id.ueipab_deduction_base - before.get('deduction_base', 0)) < 0.01 else '❌ CHANGED!'}")
    print(f"{'VE_NET':<20} | ${before.get('net', 0):>17,.2f} | ${net_after:>17,.2f} | {'✅' if abs(net_after - before.get('net', 0)) < 0.01 else '❌ CHANGED!'}")
    print(f"{'VE_GROSS':<20} | ${before.get('gross', 0):>17,.2f} | ${gross_after:>17,.2f} | {'✅' if abs(gross_after - before.get('gross', 0)) < 0.01 else '❌ CHANGED!'}")
    print(f"{'VE_SALARY_70':<20} | ${before.get('salary', 0):>17,.2f} | ${salary_after:>17,.2f} | {'✅' if abs(salary_after - before.get('salary', 0)) < 0.01 else '❌ CHANGED!'}")

# Check all payslips
changes_detected = []
unchanged = 0

print(f"\n\n📊 CHECKING ALL {len(payslips)} PAYSLIPS:")
print("=" * 80)

for payslip in payslips:
    payslip_id_str = str(payslip.id)
    
    if payslip_id_str not in snapshot_before:
        continue
    
    before = snapshot_before[payslip_id_str]
    
    # Get current values
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    salary_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    
    net_after = net_line[0].total if net_line else 0.0
    salary_after = salary_line[0].total if salary_line else 0.0
    
    # Check for changes
    net_changed = abs(net_after - before['net']) > 0.01
    salary_changed = abs(salary_after - before['salary']) > 0.01
    wage_changed = abs(payslip.contract_id.wage - before['wage']) > 0.01
    
    if net_changed or salary_changed or wage_changed:
        changes_detected.append({
            'employee': payslip.employee_id.name,
            'net_before': before['net'],
            'net_after': net_after,
            'multiplier': net_after / before['net'] if before['net'] > 0 else 0,
        })
    else:
        unchanged += 1

print(f"\n{'Status':<15} | Count")
print("-" * 30)
print(f"{'✅ Unchanged':<15} | {unchanged}")
print(f"{'❌ Modified':<15} | {len(changes_detected)}")

print("\n" + "=" * 80)

if changes_detected:
    print("❌❌❌ DATABASE CORRUPTION DETECTED! ❌❌❌")
    print("=" * 80)
    print(f"\n{len(changes_detected)} payslips were MODIFIED by VEB report generation!")
    
    print(f"\nFirst 5 corrupted payslips:")
    for i, change in enumerate(changes_detected[:5]):
        print(f"\n{i+1}. {change['employee']}:")
        print(f"   NET Before: ${change['net_before']:>14,.2f}")
        print(f"   NET After:  ${change['net_after']:>14,.2f}")
        print(f"   Multiplier: {change['multiplier']:.2f}x")
    
    print(f"\n⚠️  THE FIX IS NOT WORKING!")
    print(f"   VEB report is still modifying database records")
    
else:
    print("✅✅✅ SUCCESS! NO DATABASE MODIFICATION! ✅✅✅")
    print("=" * 80)
    print(f"\nAll {unchanged} payslips remained UNCHANGED!")
    print(f"\n✅ Payslip data is still in USD (not corrupted)")
    print(f"✅ VEB report displayed converted values WITHOUT modifying database")
    print(f"✅ The fix is working perfectly!")

print("\n" + "=" * 80)

