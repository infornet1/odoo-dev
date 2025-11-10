#!/usr/bin/env python3
"""
Test Aguinaldos Fiscal Year Limit Logic
Fiscal Year: September 1 - August 31
"""

from datetime import datetime, date

def determine_fiscal_year(payslip_date):
    """Determine fiscal year based on payslip date"""
    if payslip_date.month >= 9:  # September to December
        fiscal_year_start = date(payslip_date.year, 9, 1)
        fiscal_year_end = date(payslip_date.year + 1, 8, 31)
        fiscal_year_name = f"{payslip_date.year}-{payslip_date.year + 1}"
    else:  # January to August
        fiscal_year_start = date(payslip_date.year - 1, 9, 1)
        fiscal_year_end = date(payslip_date.year, 8, 31)
        fiscal_year_name = f"{payslip_date.year - 1}-{payslip_date.year}"

    return fiscal_year_name, fiscal_year_start, fiscal_year_end

# Test scenarios
test_dates = [
    date(2025, 9, 15),   # September 2025 (start of FY 2025-2026)
    date(2025, 10, 15),  # October 2025
    date(2025, 11, 15),  # November 2025
    date(2025, 12, 15),  # December 2025
    date(2026, 1, 15),   # January 2026
    date(2026, 2, 15),   # February 2026
    date(2026, 8, 15),   # August 2026 (end of FY 2025-2026)
    date(2026, 9, 15),   # September 2026 (start of FY 2026-2027)
]

print("="*80)
print("AGUINALDOS FISCAL YEAR LIMIT - TEST SCENARIOS")
print("="*80)
print(f"\n{'Payslip Date':<20} {'Fiscal Year':<15} {'FY Start':<15} {'FY End':<15}")
print("-"*80)

for test_date in test_dates:
    fy_name, fy_start, fy_end = determine_fiscal_year(test_date)
    print(f"{test_date.strftime('%Y-%m-%d'):<20} {fy_name:<15} {fy_start.strftime('%Y-%m-%d'):<15} {fy_end.strftime('%Y-%m-%d'):<15}")

print("\n" + "="*80)
print("LIMIT ENFORCEMENT EXAMPLE")
print("="*80)
print("\nEmployee: ANDRES MORALES")
print("Monthly Salary: $124.19")
print("Annual Limit (2x): $248.38")
print("\nFiscal Year: 2025-2026 (Sep 1, 2025 - Aug 31, 2026)")
print("-"*80)

# Simulate multiple Aguinaldos payments
payments = [
    {"date": date(2025, 12, 15), "period": "12/01-12/15", "calculated": 124.19},
    {"date": date(2025, 12, 31), "period": "12/16-12/31", "calculated": 124.19},
    {"date": date(2026, 1, 15), "period": "01/01-01/15", "calculated": 124.19},
]

annual_limit = 248.38
total_paid = 0.0

print(f"\n{'Payment':<10} {'Date':<12} {'Period':<15} {'Calculated':<12} {'Already Paid':<14} {'Remaining':<12} {'Actual Paid':<12} {'Status'}")
print("-"*120)

for i, payment in enumerate(payments, 1):
    calculated = payment['calculated']
    remaining = max(0.0, annual_limit - total_paid)
    actual_paid = min(calculated, remaining)

    status = "✓ Paid" if actual_paid > 0 else "✗ BLOCKED (Limit Reached)"

    print(f"{i:<10} {payment['date'].strftime('%Y-%m-%d'):<12} {payment['period']:<15} ${calculated:<11.2f} ${total_paid:<13.2f} ${remaining:<11.2f} ${actual_paid:<11.2f} {status}")

    total_paid += actual_paid

print("-"*120)
print(f"{'TOTAL PAID IN FY 2025-2026:':<73} ${total_paid:.2f}")
print(f"{'ANNUAL LIMIT:':<73} ${annual_limit:.2f}")

if total_paid <= annual_limit:
    print(f"{'STATUS:':<73} ✓ WITHIN LIMIT")
else:
    print(f"{'STATUS:':<73} ✗ EXCEEDED LIMIT")

print("\n" + "="*80)
print("KEY POINTS:")
print("="*80)
print("1. Fiscal Year: September 1 - August 31")
print("2. Annual Limit: 2x monthly salary per fiscal year")
print("3. Limit check includes ALL confirmed Aguinaldos payslips in same fiscal year")
print("4. If limit reached, subsequent payslips will show $0.00 for Aguinaldos")
print("5. Limit resets on September 1st each year")
print("="*80)
