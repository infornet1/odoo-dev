#!/usr/bin/env python3
"""
Check ALL payslips in NOVIEMBRE15-1 to see which ones have correct USD values
"""

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-1')], limit=1)
payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print(f"📊 BATCH: {batch.name}")
print(f"   Total payslips: {len(payslips)}\n")

print(f"{'Employee':<25} | {'Contract Wage':>15} | {'VE_NET (DB)':>18} | Status")
print("=" * 85)

clean_count = 0
corrupted_count = 0

for payslip in payslips.sorted(lambda p: p.employee_id.name):
    wage = payslip.contract_id.wage
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    net_db = net_line[0].total if net_line else 0.0
    
    # Check if VE_NET is reasonable (should be slightly less than wage)
    # If VE_NET > wage * 10, it's corrupted
    is_corrupted = net_db > (wage * 10) if wage > 0 else True
    
    status = "❌ CORRUPTED" if is_corrupted else "✅ OK"
    if is_corrupted:
        corrupted_count += 1
    else:
        clean_count += 1
    
    print(f"{payslip.employee_id.name[:24]:<25} | ${wage:>14,.2f} | ${net_db:>17,.2f} | {status}")

print("=" * 85)
print(f"\n📈 SUMMARY:")
print(f"   Clean payslips:     {clean_count}")
print(f"   Corrupted payslips: {corrupted_count}")

if corrupted_count == len(payslips):
    print(f"\n⚠️  ALL PAYSLIPS ARE CORRUPTED!")
    print(f"   Recommendation: Delete entire NOVIEMBRE15-1 batch and recreate")
elif corrupted_count > 0:
    print(f"\n⚠️  Some payslips are corrupted")
    print(f"   You may want to recompute those specific payslips")
else:
    print(f"\n✅ All payslips are clean!")

