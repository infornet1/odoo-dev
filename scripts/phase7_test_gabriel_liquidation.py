#!/usr/bin/env python3
"""
Phase 7: Test Gabriel España Liquidation (Simple Case)
======================================================

Create liquidation payslip for Gabriel España and verify calculations.

Test Case: Simple employee with no rehire history
- Original hire: Jul 27, 2022
- Contract start: Sep 1, 2023 (company liability)
- Previous liquidation: Jul 31, 2023
- Vacation paid until: Aug 1, 2024
- Liquidation date: Jul 31, 2025
"""

import datetime

print("=" * 80)
print("PHASE 7: GABRIEL ESPAÑA LIQUIDATION TEST")
print("=" * 80)

# Find Gabriel España
employee = env['hr.employee'].search([('name', 'ilike', 'GABRIEL ESPAÑA')], limit=1)

if not employee:
    print("\n❌ Employee 'GABRIEL ESPAÑA' not found!")
    exit(1)

print(f"\n✅ Found employee: {employee.name} (ID: {employee.id})")

# Get active contract
contract = env['hr.contract'].search([
    ('employee_id', '=', employee.id),
    ('state', 'in', ['open', 'close'])
], limit=1)

if not contract:
    print(f"❌ No active contract found for {employee.name}")
    exit(1)

print(f"✅ Found contract: {contract.name} (ID: {contract.id})")

# Display contract information
print("\n" + "-" * 80)
print("CONTRACT INFORMATION")
print("-" * 80)
print(f"Employee: {employee.name}")
print(f"Contract Start: {contract.date_start}")
print(f"Original Hire Date: {contract.ueipab_original_hire_date}")
print(f"Previous Liquidation: {contract.ueipab_previous_liquidation_date}")
print(f"Vacation Paid Until: {contract.ueipab_vacation_paid_until}")
print(f"Deduction Base: ${contract.ueipab_deduction_base}")

# Find liquidation salary structure
liquidation_structure = env['hr.payroll.structure'].search([
    ('name', 'ilike', 'Liquidación')
], limit=1)

if not liquidation_structure:
    print("\n❌ Liquidation salary structure not found!")
    exit(1)

print(f"\n✅ Liquidation structure: {liquidation_structure.name} (ID: {liquidation_structure.id})")

# Create liquidation payslip
liquidation_date = datetime.date(2025, 7, 31)

print(f"\n" + "=" * 80)
print(f"CREATING LIQUIDATION PAYSLIP")
print(f"=" * 80)
print(f"Liquidation Date: {liquidation_date}")

payslip = env['hr.payslip'].create({
    'name': f'Liquidation Test - {employee.name}',
    'employee_id': employee.id,
    'contract_id': contract.id,
    'struct_id': liquidation_structure.id,
    'date_from': contract.date_start,
    'date_to': liquidation_date,
    'state': 'draft'
})

print(f"✅ Created payslip: {payslip.name} (ID: {payslip.id})")

# Compute payslip
print(f"\n{'=' * 80}")
print("COMPUTING PAYSLIP...")
print("=" * 80)

try:
    # In Odoo 17 Community, use action_payslip_compute or _compute_line_values
    payslip.action_payslip_compute()
    print("✅ Payslip computed successfully!")
except Exception as e:
    print(f"❌ Error computing payslip: {e}")
    print("Trying alternative compute method...")
    try:
        payslip._compute_line_values()
        print("✅ Payslip computed successfully (alternative method)!")
    except Exception as e2:
        print(f"❌ Both compute methods failed: {e2}")
        exit(1)

# Display results
print(f"\n{'=' * 80}")
print("LIQUIDATION CALCULATION RESULTS")
print("=" * 80)
print(f"\n{'-' * 80}")
print(f"{'Line':<40} {'Code':<25} {'Amount':>12}")
print(f"{'-' * 80}")

total_gross = 0
total_deductions = 0
net_amount = 0

for line in payslip.line_ids.sorted(key=lambda l: l.sequence):
    amount = line.amount
    print(f"{line.name:<40} {line.code:<25} ${amount:>11.2f}")

    if line.code == 'LIQUID_NET':
        net_amount = amount
    elif line.code in ['LIQUID_FAOV', 'LIQUID_INCES']:
        total_deductions += abs(amount)
    elif line.code.startswith('LIQUID_') and line.code not in ['LIQUID_NET', 'LIQUID_SERVICE_MONTHS', 'LIQUID_DAILY_SALARY', 'LIQUID_INTEGRAL_DAILY', 'LIQUID_ANTIGUEDAD_DAILY']:
        if amount > 0:
            total_gross += amount

print(f"{'-' * 80}")
print(f"{'TOTAL GROSS':<40} {'':<25} ${total_gross:>11.2f}")
print(f"{'TOTAL DEDUCTIONS':<40} {'':<25} ${total_deductions:>11.2f}")
print(f"{'NET LIQUIDATION':<40} {'':<25} ${net_amount:>11.2f}")

# Detailed analysis
print(f"\n{'=' * 80}")
print("DETAILED ANALYSIS")
print("=" * 80)

# Service period
service_months_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_SERVICE_MONTHS')
if service_months_line:
    service_months = service_months_line[0].amount
    print(f"\n📅 Service Period:")
    print(f"   From: {contract.date_start}")
    print(f"   To: {liquidation_date}")
    print(f"   Months: {service_months:.2f}")

# Antiguedad calculation
antiguedad_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_ANTIGUEDAD')
if antiguedad_line:
    print(f"\n👤 Antiguedad (Seniority):")
    if contract.ueipab_original_hire_date:
        total_days = (liquidation_date - contract.ueipab_original_hire_date).days
        total_months = total_days / 30.0
        print(f"   Original hire: {contract.ueipab_original_hire_date}")
        print(f"   Total seniority: {total_months:.2f} months")

        if contract.ueipab_previous_liquidation_date:
            paid_days = (contract.ueipab_previous_liquidation_date - contract.ueipab_original_hire_date).days
            paid_months = paid_days / 30.0
            net_months = total_months - paid_months
            print(f"   Previous liquidation: {contract.ueipab_previous_liquidation_date}")
            print(f"   Already paid: {paid_months:.2f} months")
            print(f"   Net owed: {net_months:.2f} months")
            print(f"   Amount: ${antiguedad_line[0].amount:.2f}")

# Vacation calculation
vacaciones_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_VACACIONES')
if vacaciones_line:
    print(f"\n🏖️  Vacaciones:")
    if contract.ueipab_vacation_paid_until:
        period_start = contract.ueipab_vacation_paid_until + datetime.timedelta(days=1)
        period_days = (liquidation_date - period_start).days + 1
        period_months = period_days / 30.0
        print(f"   Last paid: {contract.ueipab_vacation_paid_until}")
        print(f"   Period: {period_start} to {liquidation_date}")
        print(f"   Days: {period_days} ({period_months:.2f} months)")
        print(f"   Amount: ${vacaciones_line[0].amount:.2f}")

# Bono Vacacional
bono_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_BONO_VACACIONAL')
if bono_line:
    print(f"\n🎁 Bono Vacacional:")
    if contract.ueipab_original_hire_date:
        total_years = (liquidation_date - contract.ueipab_original_hire_date).days / 365.0
        print(f"   Total seniority: {total_years:.2f} years")
        if total_years >= 5:
            print(f"   Rate: 14 days/year (≥ 5 years)")
        else:
            print(f"   Rate: {7 + (total_years * 1.4):.2f} days/year")
    print(f"   Amount: ${bono_line[0].amount:.2f}")

# Interest rate
interest_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_INTERESES')
if interest_line:
    print(f"\n💰 Interest (13% annual):")
    print(f"   Amount: ${interest_line[0].amount:.2f}")

print(f"\n{'=' * 80}")
print("✅ PHASE 7 TEST COMPLETE")
print("=" * 80)
print(f"\nPayslip State: {payslip.state}")
print(f"You can now review this payslip in Odoo UI:")
print(f"  HR → Payslips → {payslip.name}")
print("=" * 80)
