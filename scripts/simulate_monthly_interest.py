#!/usr/bin/env python3
"""
Simulate Monthly Interest Calculation
======================================

Build month-by-month breakdown to reverse-engineer how we get $84.85

Author: Claude Code
Date: 2025-11-13
"""

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

print("="*80)
print("MONTHLY INTEREST SIMULATION - REVERSE ENGINEERING $84.85")
print("="*80)
print()

# SLIP/568 Data
contract_start = datetime(2023, 9, 1).date()
liquidation_end = datetime(2025, 7, 31).date()
service_months = 23.30
prestaciones_total = 672.27
intereses_target = 84.85
integral_daily = 5.77

annual_rate = 0.13  # 13%
monthly_rate = annual_rate / 12  # 1.0833%

print(f"📋 INPUT DATA:")
print(f"   Contract Start: {contract_start}")
print(f"   Liquidation End: {liquidation_end}")
print(f"   Service Months: {service_months}")
print(f"   Prestaciones Total: ${prestaciones_total:.2f}")
print(f"   Target Interest: ${intereses_target:.2f}")
print(f"   Integral Daily: ${integral_daily:.2f}")
print(f"   Annual Rate: {annual_rate*100:.2f}%")
print(f"   Monthly Rate: {monthly_rate*100:.4f}%")
print()

# Calculate quarterly deposit amount (15 days per quarter)
quarterly_deposit = integral_daily * 15

print(f"💰 QUARTERLY DEPOSIT:")
print(f"   15 days × ${integral_daily:.2f} = ${quarterly_deposit:.2f}")
print()

print("="*80)
print("MONTH-BY-MONTH SIMULATION")
print("="*80)
print()

# Method A: Compound monthly interest on accumulated prestaciones
print("METHOD A: Monthly Compound Interest on Accumulated Balance")
print("-" * 80)

balance = 0.0
total_interest = 0.0
current_date = contract_start

month_num = 0

print(f"{'Month':<12} {'Date':<12} {'Deposit':<12} {'Balance':<12} {'Interest':<12} {'Cum.Int.':<12}")
print("-" * 80)

while current_date <= liquidation_end:
    month_num += 1

    # Determine if this is a deposit month (every 3 months starting from month 3)
    # Months 3, 6, 9, 12, 15, 18, 21, 24...
    deposit = 0.0
    if month_num >= 3 and (month_num - 3) % 3 == 0:
        deposit = quarterly_deposit
        balance += deposit

    # Calculate interest on current balance
    month_interest = balance * monthly_rate
    total_interest += month_interest

    month_name = current_date.strftime("%b-%y")

    print(f"{month_name:<12} {str(current_date):<12} ${deposit:>10.2f} ${balance:>10.2f} ${month_interest:>10.2f} ${total_interest:>10.2f}")

    # Move to next month
    current_date = current_date + relativedelta(months=1)
    if current_date > liquidation_end:
        break

print("-" * 80)
print(f"Final Balance: ${balance:.2f} (should be ${prestaciones_total:.2f})")
print(f"Total Interest: ${total_interest:.2f} (target ${intereses_target:.2f})")
print(f"Difference: ${abs(total_interest - intereses_target):.2f}")
print()

# Method B: Only calculate interest on months AFTER deposits
print("="*80)
print("METHOD B: Interest Only After Deposit Months")
print("-" * 80)

balance = 0.0
total_interest = 0.0
current_date = contract_start

month_num = 0

print(f"{'Month':<12} {'Date':<12} {'Deposit':<12} {'Balance':<12} {'Interest':<12} {'Cum.Int.':<12}")
print("-" * 80)

while current_date <= liquidation_end:
    month_num += 1

    # Deposit month check
    deposit = 0.0
    if month_num >= 3 and (month_num - 3) % 3 == 0:
        deposit = quarterly_deposit
        balance += deposit
        # Interest starts NEXT month
        month_interest = 0.0
    else:
        # Calculate interest on existing balance
        month_interest = balance * monthly_rate

    total_interest += month_interest

    month_name = current_date.strftime("%b-%y")

    print(f"{month_name:<12} {str(current_date):<12} ${deposit:>10.2f} ${balance:>10.2f} ${month_interest:>10.2f} ${total_interest:>10.2f}")

    current_date = current_date + relativedelta(months=1)
    if current_date > liquidation_end:
        break

print("-" * 80)
print(f"Final Balance: ${balance:.2f}")
print(f"Total Interest: ${total_interest:.2f} (target ${intereses_target:.2f})")
print(f"Difference: ${abs(total_interest - intereses_target):.2f}")
print()

# Method C: Simple annual interest divided proportionally
print("="*80)
print("METHOD C: Simple Interest Calculation Variations")
print("-" * 80)

# C1: Interest on average balance over time
avg_balance = balance / 2  # Approximate average
simple_on_avg = avg_balance * annual_rate * (service_months / 12)
print(f"C1 - On average balance: ${simple_on_avg:.2f}")

# C2: Pro-rated for actual time
time_fraction = service_months / 12
simple_prorated = prestaciones_total * annual_rate * time_fraction
print(f"C2 - Pro-rated for time: ${simple_prorated:.2f}")

# C3: Half-year convention
simple_half_year = prestaciones_total * annual_rate * 0.5
print(f"C3 - Half-year convention: ${simple_half_year:.2f}")

print()
print("="*80)
