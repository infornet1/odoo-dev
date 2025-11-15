#!/usr/bin/env python3
"""
CRITICAL DIAGNOSTIC: Analyze bi-weekly period scaling in deduction formulas
Check if the formulas are INTENTIONALLY using different rates for bi-weekly periods
NO DATABASE MODIFICATIONS - pure diagnostic
"""

print("=" * 140)
print("🔍 CRITICAL DIAGNOSTIC: BI-WEEKLY PERIOD SCALING ANALYSIS")
print("=" * 140)

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

# Get a few sample payslips to check date ranges
sample_employees = ['RAFAEL PEREZ', 'ALEJANDRA LOPEZ', 'ARCIDES ARZOLA']

print(f"\n📅 STEP 1: CHECK PAYSLIP DATE RANGES")
print(f"{'Employee':<20} | {'Date From':>12} | {'Date To':>12} | {'Days':>5} | {'Period Type':>15}")
print(f"{'-' * 80}")

for emp_name in sample_employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if payslip:
        date_from = payslip.date_from
        date_to = payslip.date_to
        period_days = (date_to - date_from).days + 1
        period_type = "Bi-weekly (15d)" if period_days == 15 else f"Custom ({period_days}d)"

        print(f"{emp_name:<20} | {str(date_from):>12} | {str(date_to):>12} | {period_days:>5} | {period_type:>15}")

print(f"\n{'=' * 140}")
print(f"🧮 STEP 2: UNDERSTAND THE FORMULA LOGIC")
print(f"{'=' * 140}")

print(f"\nCurrent VE_SSO_DED Formula:")
print(f"   Line 6: monthly_ivss = original_k * 0.0225  # 2.25%")
print(f"   Line 10: proportion = period_days / 15.0")
print(f"   Line 12: result = -(monthly_ivss * proportion)")

print(f"\n🤔 INTERPRETATION OPTIONS:")
print(f"\n   OPTION A: Formula is WRONG")
print(f"      - Legal rate is 4% per MONTH")
print(f"      - For 15 days (bi-weekly): Should be 4% / 2 = 2% of base")
print(f"      - For 30 days (full month): Should be 4% of base")
print(f"      - Current formula gives 2.25% for 15 days, 4.5% for 30 days ❌")

print(f"\n   OPTION B: Formula is CORRECT (different interpretation)")
print(f"      - Maybe legal rate is 4.5% per MONTH")
print(f"      - For 15 days: 4.5% / 2 = 2.25% ✅")
print(f"      - For 30 days: 4.5% ✅")
print(f"      - Variable name says 'monthly_ivss' suggesting 2.25% is the MONTHLY rate for a 15-day period")

print(f"\n   OPTION C: Formula is for SEMI-MONTHLY (not bi-weekly)")
print(f"      - If they pay twice per month (not every 14 days)")
print(f"      - Legal rate might be 4.5% per month")
print(f"      - Each semi-monthly period = 2.25%")

print(f"\n{'=' * 140}")
print(f"🔍 STEP 3: CALCULATE WHAT FORMULA PRODUCES")
print(f"{'=' * 140}")

print(f"\nUsing Rafael Perez as example:")
print(f"   Deduction Base: $170.30")

payslip = env['hr.payslip'].search([
    ('employee_id.name', 'ilike', 'RAFAEL PEREZ'),
    ('payslip_run_id', '=', batch.id)
], limit=1)

if payslip:
    date_from = payslip.date_from
    date_to = payslip.date_to
    period_days = (date_to - date_from).days + 1
    deduction_base = payslip.contract_id.ueipab_deduction_base

    print(f"   Period: {date_from} to {date_to} ({period_days} days)")

    # Current formula
    monthly_ivss = deduction_base * 0.0225
    proportion = period_days / 15.0
    current_result = monthly_ivss * proportion

    print(f"\n   CURRENT FORMULA CALCULATION:")
    print(f"      Step 1: monthly_ivss = ${deduction_base:,.2f} × 0.0225 = ${monthly_ivss:,.2f}")
    print(f"      Step 2: proportion = {period_days} / 15.0 = {proportion:.2f}")
    print(f"      Step 3: result = ${monthly_ivss:,.2f} × {proportion:.2f} = ${current_result:,.2f}")

    # Get actual from payslip
    sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')
    actual_sso = abs(sso_line[0].total) if sso_line else 0.0
    print(f"      Actual SSO deduction: ${actual_sso:,.2f}")

    if abs(current_result - actual_sso) < 0.01:
        print(f"      ✅ Formula calculation matches actual deduction")
    else:
        print(f"      ❌ Formula calculation does NOT match (diff: ${abs(current_result - actual_sso):,.2f})")

    print(f"\n   IF FORMULA WAS 4% MONTHLY:")
    # Option 1: 4% monthly, pro-rated
    monthly_4pct = deduction_base * 0.04
    result_4pct = monthly_4pct * (period_days / 30.0)  # Pro-rate based on 30-day month
    print(f"      Step 1: monthly_sso = ${deduction_base:,.2f} × 0.04 = ${monthly_4pct:,.2f}")
    print(f"      Step 2: proportion = {period_days} / 30.0 = {period_days/30.0:.4f}")
    print(f"      Step 3: result = ${monthly_4pct:,.2f} × {period_days/30.0:.4f} = ${result_4pct:,.2f}")
    print(f"      Difference from actual: ${abs(result_4pct - actual_sso):,.2f}")

    # Option 2: 4% monthly, but use /15 scaling (bi-weekly logic)
    result_4pct_biweekly = monthly_4pct * (period_days / 15.0)
    print(f"\n   IF FORMULA WAS 4% MONTHLY (using bi-weekly scaling /15):")
    print(f"      Step 1: monthly_sso = ${deduction_base:,.2f} × 0.04 = ${monthly_4pct:,.2f}")
    print(f"      Step 2: proportion = {period_days} / 15.0 = {period_days/15.0:.2f}")
    print(f"      Step 3: result = ${monthly_4pct:,.2f} × {period_days/15.0:.2f} = ${result_4pct_biweekly:,.2f}")
    print(f"      Difference from actual: ${abs(result_4pct_biweekly - actual_sso):,.2f}")

    # Option 3: Maybe the ANNUAL rate is being divided?
    annual_rate = 0.04 * 12  # 48% annual
    semi_monthly_rate = annual_rate / 24  # 24 pay periods per year
    result_semi_monthly = deduction_base * semi_monthly_rate
    print(f"\n   IF USING SEMI-MONTHLY (24 periods/year):")
    print(f"      Annual rate: {annual_rate*100:.2f}%")
    print(f"      Per period rate: {semi_monthly_rate*100:.4f}%")
    print(f"      result = ${deduction_base:,.2f} × {semi_monthly_rate:.6f} = ${result_semi_monthly:,.2f}")
    print(f"      Difference from actual: ${abs(result_semi_monthly - actual_sso):,.2f}")

print(f"\n{'=' * 140}")
print(f"📊 STEP 4: CHECK SPREADSHEET - WHAT RATE DOES IT USE?")
print(f"{'=' * 140}")

print(f"\n   From our earlier verification, spreadsheet shows HIGHER deductions than Odoo.")
print(f"   Example: Rafael Perez")
print(f"      Odoo VE_NET:       $193.72")
print(f"      Spreadsheet NET:   $195.70")
print(f"      Odoo is LOWER by:  $1.98")
print(f"\n   If Odoo is under-deducting SSO/FAOV/PARO, the VE_NET would be HIGHER (employee gets more)")
print(f"   But Odoo VE_NET is LOWER... this suggests:")
print(f"      ❓ Spreadsheet might be using DIFFERENT deductions")
print(f"      ❓ OR there are OTHER differences (earnings, other deductions)")

print(f"\n{'=' * 140}")
print(f"💡 CRITICAL QUESTIONS TO ANSWER:")
print(f"{'=' * 140}")
print(f"\n   1. What is the LEGAL Venezuelan SSO rate?")
print(f"      - Is it 4% per MONTH? or")
print(f"      - Is it 4.5% per MONTH? or")
print(f"      - Is it 2.25% per SEMI-MONTHLY period (24 periods/year)?")
print(f"\n   2. How does the company ACTUALLY pay?")
print(f"      - Bi-weekly (every 14 days = 26 periods/year)?")
print(f"      - Semi-monthly (twice per month = 24 periods/year)?")
print(f"      - Bi-monthly for this batch (15 days, 2 times per month)?")
print(f"\n   3. What does the SPREADSHEET use?")
print(f"      - We need to see the spreadsheet formula to understand")
print(f"      - It might be using 4% monthly pro-rated to 15 days = 2%")
print(f"      - Or it might be using a different system entirely")
print(f"\n   ⚠️  RECOMMENDATION: Check with HR/Accounting what the LEGAL rate is")
print(f"   ⚠️  AND check the spreadsheet formula to see what it calculates")
print(f"{'=' * 140}")
