#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check NELCI BRITO's salary data from Google Sheets
Compare with Odoo contract data
"""

import sys

# Note: This script requires Google Sheets API access
# For now, we'll show what needs to be checked

print("=" * 80)
print("NELCI BRITO SALARY VERIFICATION")
print("=" * 80)

print("\nSpreadsheet ID: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s")
print("Employee: NELCI BRITO")

print("\n" + "-" * 80)
print("CURRENT ODOO CONTRACT DATA (from database query):")
print("-" * 80)
print("  ueipab_salary_base (70%):     $114.46")
print("  ueipab_bonus_regular (25%):    $40.88")
print("  ueipab_extra_bonus (5%):        $8.18")
print("  " + "=" * 40)
print("  Total (70+25+5):              $163.52 per month")
print("  cesta_ticket_usd:              $40.00 per month")
print("  ueipab_monthly_salary:        $140.36 (from spreadsheet sync?)")

print("\n" + "-" * 80)
print("PAYSLIP SLIP/237 CALCULATION (Nov 1-15, 2025 - 15 days = 50%):")
print("-" * 80)
print("  Salary Base (70%):             $57.23  ($114.46 * 50%)")
print("  Regular Bonus (25%):           $20.44  ($40.88 * 50%)")
print("  Extra Bonus (5%):               $4.09  ($8.18 * 50%)")
print("  Cesta Ticket:                  $20.00  ($40.00 * 50%)")
print("  " + "=" * 40)
print("  GROSS:                        $101.76")
print("  Total Deductions (8.5%):       -$4.80")
print("  " + "=" * 40)
print("  NET:                           $96.96 for 15 days")
print("  NET (extrapolated 30 days):   $193.92")

print("\n" + "-" * 80)
print("USER REPORTED (from Spreadsheet Column Z):")
print("-" * 80)
print("  Expected NET for 30 days:     $307.81")
print("  Expected NET for 15 days:     $153.91 (approx)")

print("\n" + "-" * 80)
print("DISCREPANCY ANALYSIS:")
print("-" * 80)
print("  Difference (15 days):          $153.91 - $96.96 = $56.95 SHORT")
print("  Difference (30 days):          $307.81 - $193.92 = $113.89 SHORT")
print("  Percentage difference:         58.7% SHORT!")

print("\n" + "-" * 80)
print("ROOT CAUSE HYPOTHESIS:")
print("-" * 80)
print("  The contract data in Odoo DOES NOT MATCH the spreadsheet!")
print()
print("  To achieve NET = $307.81 for 30 days:")
print("    Required GROSS before deductions ≈ $336.40")
print("    Required Salary (70+25+5) ≈ $296.40")
print("    Current Salary (70+25+5) = $163.52")
print("    MISSING: $132.88 per month!")

print("\n" + "-" * 80)
print("VERIFICATION NEEDED:")
print("-" * 80)
print("  1. Check Google Sheets for NELCI BRITO's monthly salary")
print("  2. Look at columns for 70/25/5 breakdown")
print("  3. Verify column Z shows $307.81 NET")
print("  4. Compare with ueipab_monthly_salary field ($140.36)")
print()
print("  ⚠️  The ueipab_monthly_salary field ($140.36) is MUCH LOWER")
print("  ⚠️  than the calculated gross ($163.52), which doesn't make sense!")
print()
print("  This suggests the contract data was NOT properly synced from")
print("  the spreadsheet, or the wrong employee data was loaded.")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("  1. Access the Google Sheets directly to verify NELCI BRITO's data")
print("  2. Check if the sync script ran correctly")
print("  3. Update the contract with correct values from spreadsheet")
print("  4. Recompute the payslip SLIP/237")
print("=" * 80)
