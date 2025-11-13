#!/usr/bin/env python3
"""
Analyze SLIP/568 Interest Calculation
======================================

Reverse-engineer the interest calculation logic from SLIP/568
to understand how we get $84.85 in LIQUID_INTERESES.

Author: Claude Code
Date: 2025-11-13
"""

print("="*80)
print("ANALYZING SLIP/568 - INTEREST CALCULATION")
print("="*80)
print()

Payslip = env['hr.payslip']
PayslipLine = env['hr.payslip.line']

# Find SLIP/568
payslip = Payslip.search([('number', '=', 'SLIP/568')], limit=1)

if not payslip:
    print("❌ SLIP/568 not found!")
else:
    print(f"✅ Payslip: {payslip.number}")
    print(f"   Employee: {payslip.employee_id.name}")
    print(f"   Period: {payslip.date_from} to {payslip.date_to}")
    print(f"   State: {payslip.state}")
    print(f"   Structure: {payslip.struct_id.name}")
    print()

    # Get employee contract
    contract = payslip.contract_id
    if contract:
        print(f"📋 Contract Information:")
        print(f"   Contract Start: {contract.date_start}")
        print(f"   Contract End: {contract.date_end or 'N/A'}")
        print(f"   Wage: ${contract.wage}")
        print(f"   Deduction Base: ${contract.ueipab_deduction_base}")
        print()

        # Historical tracking fields
        if hasattr(contract, 'ueipab_original_hire_date') and contract.ueipab_original_hire_date:
            print(f"   Original Hire: {contract.ueipab_original_hire_date}")
        if hasattr(contract, 'ueipab_previous_liquidation_date') and contract.ueipab_previous_liquidation_date:
            print(f"   Previous Liquidation: {contract.ueipab_previous_liquidation_date}")
        if hasattr(contract, 'ueipab_vacation_paid_until') and contract.ueipab_vacation_paid_until:
            print(f"   Vacation Paid Until: {contract.ueipab_vacation_paid_until}")
        print()

    # Get all salary rule lines
    print("💰 Salary Rule Lines:")
    print("-" * 80)

    lines = payslip.line_ids.sorted(lambda l: l.sequence)

    for line in lines:
        code = line.code
        name = line.name
        amount = line.total

        marker = ""
        if code == 'LIQUID_INTERESES':
            marker = " ⭐ TARGET VALUE"
        elif code == 'LIQUID_PRESTACIONES':
            marker = " ⭐ BASE FOR INTEREST"
        elif code == 'LIQUID_SERVICE_MONTHS':
            marker = " ⭐ SERVICE TIME"
        elif code == 'LIQUID_INTEGRAL_DAILY':
            marker = " ⭐ DAILY RATE"

        print(f"{line.sequence:4d}  {code:30s} ${amount:12.2f}  {name}{marker}")

    print("-" * 80)
    print()

    # Extract key values for analysis
    service_months = 0
    prestaciones = 0
    intereses = 0
    integral_daily = 0
    daily_salary = 0

    for line in lines:
        if line.code == 'LIQUID_SERVICE_MONTHS':
            service_months = line.total
        elif line.code == 'LIQUID_PRESTACIONES':
            prestaciones = line.total
        elif line.code == 'LIQUID_INTERESES':
            intereses = line.total
        elif line.code == 'LIQUID_INTEGRAL_DAILY':
            integral_daily = line.total
        elif line.code == 'LIQUID_DAILY_SALARY':
            daily_salary = line.total

    print("📊 KEY VALUES FOR ANALYSIS:")
    print(f"   Service Months: {service_months:.2f} months")
    print(f"   Prestaciones: ${prestaciones:.2f}")
    print(f"   Intereses: ${intereses:.2f} ⭐ TARGET")
    print(f"   Integral Daily: ${integral_daily:.2f}")
    print(f"   Daily Salary: ${daily_salary:.2f}")
    print()

    # Calculate what the interest SHOULD be with different methods
    annual_rate = 0.13  # 13% annual
    monthly_rate = annual_rate / 12

    print("🔍 INTEREST CALCULATION ANALYSIS:")
    print("-" * 80)

    # Method 1: Simple interest on final prestaciones
    simple_on_final = prestaciones * annual_rate
    print(f"Method 1 - Simple annual on final balance:")
    print(f"   ${prestaciones:.2f} × 13% = ${simple_on_final:.2f}")
    if abs(simple_on_final - intereses) < 0.01:
        print(f"   ✅ MATCH!")
    else:
        print(f"   ❌ Difference: ${abs(simple_on_final - intereses):.2f}")
    print()

    # Method 2: Simple interest based on service time
    years = service_months / 12.0
    simple_proportional = prestaciones * annual_rate * years
    print(f"Method 2 - Simple proportional to service time:")
    print(f"   ${prestaciones:.2f} × 13% × {years:.4f} years = ${simple_proportional:.2f}")
    if abs(simple_proportional - intereses) < 0.01:
        print(f"   ✅ MATCH!")
    else:
        print(f"   ❌ Difference: ${abs(simple_proportional - intereses):.2f}")
    print()

    # Method 3: Monthly compound interest
    # Need to calculate quarterly deposits and compound monthly
    print(f"Method 3 - Monthly compound on quarterly deposits:")
    print(f"   This requires month-by-month calculation...")
    print(f"   Contract start: {contract.date_start}")
    print(f"   Liquidation end: {payslip.date_to}")
    print()

    # Calculate quarterly deposits
    quarters = service_months / 3.0
    quarterly_prestaciones = prestaciones / quarters if quarters > 0 else 0

    print(f"   Quarters: {quarters:.2f}")
    print(f"   Per quarter deposit: ${quarterly_prestaciones:.2f}")
    print()

print("="*80)
print("NEXT: Build month-by-month breakdown to reverse-engineer exact logic")
print("="*80)
