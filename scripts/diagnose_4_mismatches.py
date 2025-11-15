#!/usr/bin/env python3
"""
DIAGNOSTIC: Why do these 4 employees have VE_NET mismatches with spreadsheet?
Analyze every calculation step to find the root cause.
NO DATABASE MODIFICATIONS - pure diagnostic
"""

print("=" * 140)
print("🔍 DIAGNOSTIC: 4 MISMATCHED EMPLOYEES - VE_NET CALCULATION ANALYSIS")
print("=" * 140)

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

# The 4 mismatched employees
mismatches = [
    ('ARCIDES ARZOLA', 277.83, 274.97, 2.86),
    ('Rafael Perez', 193.72, 195.70, -1.98),
    ('SERGIO MANEIRO', 147.98, 148.69, -0.71),
    ('PABLO NAVARRO', 135.47, 136.16, -0.69),
]

for emp_name, odoo_net, sheet_net, diff in mismatches:
    print(f"\n{'=' * 140}")
    print(f"EMPLOYEE: {emp_name}")
    print(f"Odoo VE_NET: ${odoo_net:,.2f} | Spreadsheet VE_NET: ${sheet_net:,.2f} | Difference: ${diff:,.2f} ({abs(diff/odoo_net)*100:.2f}%)")
    print(f"{'=' * 140}")

    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if not payslip:
        print(f"   ❌ Payslip not found")
        continue

    # STEP 1: Contract Information
    print(f"\n📋 STEP 1: CONTRACT FIELDS")
    print(f"   {'Field':<30} | {'Value':>15}")
    print(f"   {'-' * 48}")
    contract = payslip.contract_id
    print(f"   {'wage (total compensation)':<30} | ${contract.wage:>14,.2f}")
    print(f"   {'ueipab_deduction_base':<30} | ${contract.ueipab_deduction_base:>14,.2f}")
    print(f"   {'Deduction base %':<30} | {(contract.ueipab_deduction_base/contract.wage*100):>14,.2f}%")

    # STEP 2: All Payslip Lines
    print(f"\n📊 STEP 2: ALL PAYSLIP LINES (sorted by sequence)")
    print(f"   {'Seq':<5} | {'Code':<20} | {'Name':<50} | {'Total':>15} | {'Category':<10}")
    print(f"   {'-' * 113}")

    total_positive = 0.0
    total_negative = 0.0

    for line in payslip.line_ids.sorted(lambda l: l.sequence):
        if line.total != 0:
            category = line.salary_rule_id.category_id.code if line.salary_rule_id.category_id else 'N/A'
            print(f"   {line.sequence:<5} | {line.salary_rule_id.code:<20} | {line.name[:50]:<50} | ${line.total:>14,.2f} | {category:<10}")

            if line.total > 0:
                total_positive += line.total
            else:
                total_negative += line.total

    print(f"   {'-' * 113}")
    print(f"   {'TOTALS:':<77} | ${total_positive:>14,.2f} | (positive)")
    print(f"   {'':>77} | ${total_negative:>14,.2f} | (negative)")
    print(f"   {'':>77} | ${total_positive + total_negative:>14,.2f} | (NET)")

    # STEP 3: VE_NET Calculation Breakdown
    print(f"\n🧮 STEP 3: VE_NET CALCULATION BREAKDOWN")

    # Get all earnings
    earnings_lines = payslip.line_ids.filtered(lambda l: l.total > 0 and l.salary_rule_id.code != 'VE_GROSS')
    print(f"\n   EARNINGS (excluding VE_GROSS summary line):")
    earnings_total = 0.0
    for line in earnings_lines:
        print(f"      {line.salary_rule_id.code:<20} | ${line.total:>14,.2f}")
        earnings_total += line.total
    print(f"      {'-' * 37}")
    print(f"      {'TOTAL EARNINGS':<20} | ${earnings_total:>14,.2f}")

    # Get VE_GROSS
    gross_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
    if gross_line:
        print(f"\n   VE_GROSS (should equal earnings): ${gross_line[0].total:,.2f}")
        if abs(gross_line[0].total - earnings_total) < 0.01:
            print(f"      ✅ VE_GROSS matches earnings total")
        else:
            print(f"      ⚠️  VE_GROSS differs from earnings by ${abs(gross_line[0].total - earnings_total):,.2f}")

    # Get all deductions
    deduction_lines = payslip.line_ids.filtered(lambda l: l.total < 0)
    print(f"\n   DEDUCTIONS:")
    deductions_total = 0.0
    for line in deduction_lines:
        deduction_amount = abs(line.total)
        deductions_total += deduction_amount

        # Try to show what this deduction is based on
        base_info = ""
        if line.salary_rule_id.code in ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED'):
            # These are based on deduction_base
            expected_rate = {'VE_SSO_DED': 0.04, 'VE_FAOV_DED': 0.01, 'VE_PARO_DED': 0.005}
            rate = expected_rate.get(line.salary_rule_id.code, 0)
            calculated = contract.ueipab_deduction_base * rate
            base_info = f"(should be ${contract.ueipab_deduction_base:,.2f} × {rate*100}% = ${calculated:,.2f})"
        elif line.salary_rule_id.code == 'VE_ARI_DED':
            # ARI is based on a progressive table
            base_info = f"(progressive tax on deduction_base)"

        print(f"      {line.salary_rule_id.code:<20} | ${deduction_amount:>14,.2f} {base_info}")
    print(f"      {'-' * 37}")
    print(f"      {'TOTAL DEDUCTIONS':<20} | ${deductions_total:>14,.2f}")

    # Final VE_NET
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    if net_line:
        calculated_net = earnings_total - deductions_total
        print(f"\n   VE_NET CALCULATION:")
        print(f"      Earnings Total:    ${earnings_total:>14,.2f}")
        print(f"      - Deductions:      ${deductions_total:>14,.2f}")
        print(f"      = Calculated NET:  ${calculated_net:>14,.2f}")
        print(f"      Actual VE_NET:     ${net_line[0].total:>14,.2f}")

        if abs(calculated_net - net_line[0].total) < 0.01:
            print(f"      ✅ VE_NET calculation is correct")
        else:
            print(f"      ⚠️  VE_NET differs by ${abs(calculated_net - net_line[0].total):,.2f}")

    # STEP 4: Compare with Spreadsheet
    print(f"\n📈 STEP 4: COMPARISON WITH SPREADSHEET")
    print(f"   Odoo VE_NET:        ${odoo_net:>14,.2f}")
    print(f"   Spreadsheet NET:    ${sheet_net:>14,.2f}")
    print(f"   Difference:         ${diff:>14,.2f}")

    if diff > 0:
        print(f"   ⚠️  Odoo is HIGHER than spreadsheet by ${diff:,.2f}")
        print(f"   Possible causes:")
        print(f"      - Spreadsheet deducting MORE than Odoo")
        print(f"      - Spreadsheet calculating LOWER earnings than Odoo")
    else:
        print(f"   ⚠️  Odoo is LOWER than spreadsheet by ${abs(diff):,.2f}")
        print(f"   Possible causes:")
        print(f"      - Odoo deducting MORE than spreadsheet")
        print(f"      - Odoo calculating LOWER earnings than spreadsheet")

    # STEP 5: Check deduction base percentage
    print(f"\n🔍 STEP 5: DEDUCTION BASE ANALYSIS")
    deduction_base_deductions = 0.0
    for code in ['VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED']:
        line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == code)
        if line:
            deduction_base_deductions += abs(line[0].total)

    total_deduction_rate = (deduction_base_deductions / contract.ueipab_deduction_base * 100) if contract.ueipab_deduction_base else 0
    print(f"   Deduction Base:                ${contract.ueipab_deduction_base:>14,.2f}")
    print(f"   Total Deductions from Base:    ${deduction_base_deductions:>14,.2f}")
    print(f"   Effective Deduction Rate:      {total_deduction_rate:>14,.2f}%")
    print(f"   Expected Rate (SSO+FAOV+PARO): 5.5% (without ARI)")

print(f"\n{'=' * 140}")
print(f"\n💡 DIAGNOSIS SUMMARY:")
print(f"   Common patterns to look for:")
print(f"   1. Deduction rate differences (are all 4 using same SSO/FAOV/PARO/ARI rates?)")
print(f"   2. Deduction base differences (is spreadsheet using different base?)")
print(f"   3. Rounding method differences (Odoo vs Excel rounding)")
print(f"   4. ARI tax calculation differences (progressive tax brackets)")
print(f"   5. Earnings calculation differences (VE_SALARY_70, bonuses, cesta ticket)")
print(f"\n   Next step: Analyze if all 4 have same pattern (e.g., all missing same deduction)")
print(f"{'=' * 140}")
