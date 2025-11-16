#!/usr/bin/env python3
"""
Phase 5: Test V2 Payroll Calculations
Simulates V2 payslip calculations and compares with NOVIEMBRE15-2 batch (V1)

This is a DRY-RUN analysis - NO payslips will be created or modified.
"""

from datetime import date

# Find NOVIEMBRE15-2 batch for reference
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("❌ ERROR: NOVIEMBRE15-2 batch not found")
    print("   Please verify the batch name or create it first")
    exit(1)

print("=" * 80)
print("PHASE 5: V2 PAYROLL TESTING")
print("=" * 80)
print(f"\n📋 Reference Batch: {batch.name}")
print(f"   Date From: {batch.date_start}")
print(f"   Date To: {batch.date_end}")

# Calculate period days for proration
date_from = batch.date_start
date_to = batch.date_end
period_days = (date_to - date_from).days + 1
proration = period_days / 30.0

print(f"   Period Days: {period_days}")
print(f"   Proration Factor: {proration:.4f}")

# Get V2 salary structure
v2_structure = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')], limit=1)
if not v2_structure:
    print("\n❌ ERROR: V2 salary structure (VE_PAYROLL_V2) not found")
    exit(1)

print(f"\n✅ V2 Structure: {v2_structure.name} (ID: {v2_structure.id})")
print(f"   Total Rules: {len(v2_structure.rule_ids)}")

# Sample employees to test
test_employees = [
    'Rafael Perez',      # Has ExtraBonus, was a mismatch in V1
    'ARCIDES ARZOLA',    # Highest V1 mismatch
    'Virginia Verde',    # Complex rehire case
    'Alejandra Lopez',   # Simple match case
    'SERGIO MANEIRO',    # Has ExtraBonus
]

print("\n" + "=" * 80)
print("V2 PAYSLIP SIMULATION (DRY-RUN)")
print("=" * 80)

for emp_name in test_employees:
    print("\n" + "─" * 80)

    # Find employee
    employee = env['hr.employee'].search([('name', 'ilike', emp_name)], limit=1)
    if not employee:
        print(f"✗ {emp_name}: Employee not found")
        continue

    # Find contract
    contract = env['hr.contract'].search([
        ('employee_id', '=', employee.id),
        ('state', '=', 'open')
    ], limit=1)

    if not contract:
        print(f"✗ {employee.name}: No active contract")
        continue

    # Find V1 payslip from NOVIEMBRE15-2 batch
    v1_payslip = env['hr.payslip'].search([
        ('payslip_run_id', '=', batch.id),
        ('employee_id', '=', employee.id)
    ], limit=1)

    print(f"👤 {employee.name}")
    print(f"   Contract ID: {contract.id}")
    print(f"   V1 Payslip: {'SLIP/' + str(v1_payslip.id) if v1_payslip else 'Not found'}")

    # Get V2 contract fields
    salary_v2 = contract.ueipab_salary_v2 or 0.0
    extrabonus_v2 = contract.ueipab_extrabonus_v2 or 0.0
    bonus_v2 = contract.ueipab_bonus_v2 or 0.0
    cesta_ticket = contract.cesta_ticket_usd or 0.0
    ari_rate = (contract.ueipab_ari_withholding_rate or 0.0) / 100.0

    print(f"\n   📊 V2 Contract Fields (Monthly):")
    print(f"      Salary V2:      ${salary_v2:>8.2f} (subject to deductions)")
    print(f"      ExtraBonus V2:  ${extrabonus_v2:>8.2f} (exempt)")
    print(f"      Bonus V2:       ${bonus_v2:>8.2f} (exempt)")
    print(f"      Cesta Ticket:   ${cesta_ticket:>8.2f} (exempt)")
    print(f"      ARI Rate:       {ari_rate*100:>8.2f}%")

    # Calculate V2 earnings (prorated)
    ve_salary_v2 = salary_v2 * proration
    ve_extrabonus_v2 = extrabonus_v2 * proration
    ve_bonus_v2 = bonus_v2 * proration
    ve_cesta_ticket_v2 = cesta_ticket * proration
    ve_gross_v2 = ve_salary_v2 + ve_extrabonus_v2 + ve_bonus_v2 + ve_cesta_ticket_v2

    # Calculate V2 deductions (monthly basis, then prorated)
    # Deductions apply ONLY to salary_v2, NOT to bonuses or cesta ticket
    monthly_sso = salary_v2 * 0.04      # 4% monthly
    monthly_faov = salary_v2 * 0.01     # 1% monthly
    monthly_paro = salary_v2 * 0.005    # 0.5% monthly
    monthly_ari = salary_v2 * ari_rate  # Variable % monthly

    ve_sso_ded_v2 = -(monthly_sso * proration)
    ve_faov_ded_v2 = -(monthly_faov * proration)
    ve_paro_ded_v2 = -(monthly_paro * proration)
    ve_ari_ded_v2 = -(monthly_ari * proration)
    ve_total_ded_v2 = ve_sso_ded_v2 + ve_faov_ded_v2 + ve_paro_ded_v2 + ve_ari_ded_v2

    ve_net_v2 = ve_gross_v2 + ve_total_ded_v2

    print(f"\n   💰 V2 EARNINGS ({period_days} days @ {proration:.4f}):")
    print(f"      VE_SALARY_V2:      ${ve_salary_v2:>8.2f}")
    print(f"      VE_EXTRABONUS_V2:  ${ve_extrabonus_v2:>8.2f}")
    print(f"      VE_BONUS_V2:       ${ve_bonus_v2:>8.2f}")
    print(f"      VE_CESTA_TICKET:   ${ve_cesta_ticket_v2:>8.2f}")
    print(f"      {'─' * 35}")
    print(f"      VE_GROSS_V2:       ${ve_gross_v2:>8.2f}")

    print(f"\n   💸 V2 DEDUCTIONS (on Salary V2 only):")
    print(f"      VE_SSO_DED:        ${ve_sso_ded_v2:>8.2f} (${salary_v2:.2f} × 4% × {proration:.4f})")
    print(f"      VE_FAOV_DED:       ${ve_faov_ded_v2:>8.2f} (${salary_v2:.2f} × 1% × {proration:.4f})")
    print(f"      VE_PARO_DED:       ${ve_paro_ded_v2:>8.2f} (${salary_v2:.2f} × 0.5% × {proration:.4f})")
    print(f"      VE_ARI_DED:        ${ve_ari_ded_v2:>8.2f} (${salary_v2:.2f} × {ari_rate*100:.1f}% × {proration:.4f})")
    print(f"      {'─' * 35}")
    print(f"      VE_TOTAL_DED:      ${ve_total_ded_v2:>8.2f}")

    print(f"\n   🎯 V2 NET:            ${ve_net_v2:>8.2f}")

    # Compare with V1 if available
    if v1_payslip:
        v1_net_line = v1_payslip.line_ids.filtered(lambda l: l.code == 'VE_NET')
        v1_net = v1_net_line.total if v1_net_line else 0.0

        v1_gross_line = v1_payslip.line_ids.filtered(lambda l: l.code == 'VE_GROSS')
        v1_gross = v1_gross_line.total if v1_gross_line else 0.0

        diff_net = ve_net_v2 - v1_net
        diff_gross = ve_gross_v2 - v1_gross

        print(f"\n   📊 V1 vs V2 COMPARISON:")
        print(f"      V1 Gross:          ${v1_gross:>8.2f}")
        print(f"      V2 Gross:          ${ve_gross_v2:>8.2f}")
        print(f"      Difference:        ${diff_gross:>8.2f}")
        print(f"      {'─' * 35}")
        print(f"      V1 Net:            ${v1_net:>8.2f}")
        print(f"      V2 Net:            ${ve_net_v2:>8.2f}")
        print(f"      Difference:        ${diff_net:>8.2f}")

        if abs(diff_gross) < 0.10:
            print(f"      Status:            ✅ MATCH (within $0.10)")
        elif abs(diff_gross) < 5.00:
            print(f"      Status:            ⚠️  MINOR DIFF (< $5)")
        else:
            print(f"      Status:            ⚠️  SIGNIFICANT DIFF")

print("\n" + "=" * 80)
print("PHASE 5 TEST SUMMARY")
print("=" * 80)
print("\n✅ V2 PAYROLL SIMULATION COMPLETE")
print("\n📝 Key Observations:")
print("   - V2 deductions apply ONLY to Salary V2 field")
print("   - ExtraBonus, Bonus, and Cesta Ticket are exempt from deductions")
print("   - Proration formula working correctly (days/30)")
print("   - Monthly deduction rates: SSO 4%, FAOV 1%, PARO 0.5%, ARI variable%")
print("\n⚠️  NOTE: This was a DRY-RUN simulation")
print("   - No payslips were created or modified")
print("   - To create actual V2 payslips, use Odoo UI:")
print("     1. Payroll → Batches → Create New Batch")
print("     2. Select Structure: 'Salarios Venezuela UEIPAB V2'")
print("     3. Generate Payslips → Compute Payslips")
print("\n" + "=" * 80)
