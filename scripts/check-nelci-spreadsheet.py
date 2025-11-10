#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check NELCI BRITO's salary data from Google Sheets '31oct2025' sheet
"""

import gspread
from google.oauth2.service_account import Credentials

# Configuration
SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'
TARGET_SHEET = '31oct2025'

def main():
    print("=" * 80)
    print("CHECKING NELCI BRITO IN GOOGLE SHEETS")
    print("=" * 80)

    # Connect to Google Sheets
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"✓ Connected to spreadsheet: {spreadsheet.title}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return

    # Open the worksheet
    try:
        worksheet = worksheet = spreadsheet.worksheet(TARGET_SHEET)
        print(f"✓ Opened worksheet: {TARGET_SHEET}")
    except Exception as e:
        print(f"✗ Failed to open worksheet: {e}")
        return

    # Get all data
    all_data = worksheet.get_all_values()

    # Print header
    if len(all_data) > 0:
        print("\nHeader row (row 5):")
        header = all_data[4] if len(all_data) > 4 else all_data[0]
        for idx, col in enumerate(header[:30]):  # First 30 columns
            print(f"  Column {chr(65+idx):2} ({idx:2}): {col[:50]}")

    # Search for NELCI BRITO
    print("\n" + "=" * 80)
    print("SEARCHING FOR NELCI BRITO...")
    print("=" * 80)

    nelci_found = False
    for row_idx, row in enumerate(all_data[4:], start=5):  # Start from row 5 (index 4)
        if len(row) > 3:
            employee_name = row[3].strip().upper()
            if 'NELCI' in employee_name and 'BRITO' in employee_name:
                nelci_found = True
                print(f"\n✓ FOUND at row {row_idx}:")
                print(f"  Employee Name (Col D): {row[3]}")

                # Print relevant columns
                columns = {
                    'A': ('Cedula', 0),
                    'B': ('Code/ID', 1),
                    'K': ('Monthly Salary VEB', 10),
                    'L': ('Salary 70% VEB', 11),
                    'M': ('Bonus 25% VEB', 12),
                    'N': ('Extra 5% VEB', 13),
                    'O': ('Exchange Rate', 14),
                    'Z': ('NET Salary', 25),
                }

                print("\n  Spreadsheet Data:")
                for col_letter, (col_name, col_idx) in columns.items():
                    value = row[col_idx] if len(row) > col_idx else 'N/A'
                    print(f"    Column {col_letter} ({col_name:20}): {value}")

                # Try to calculate USD values if exchange rate available
                try:
                    exchange_rate_cell = worksheet.acell('O2').value
                    exchange_rate = float(exchange_rate_cell.replace(',', '.'))
                    print(f"\n  Exchange Rate from O2: {exchange_rate:.2f} VEB/USD")

                    # Calculate USD values
                    monthly_veb = row[10] if len(row) > 10 else "0"
                    net_veb = row[25] if len(row) > 25 else "0"

                    # Clean and parse
                    monthly_veb_clean = monthly_veb.replace('.', '').replace(',', '.')
                    net_veb_clean = net_veb.replace('.', '').replace(',', '.')

                    monthly_usd = float(monthly_veb_clean) / exchange_rate if monthly_veb_clean else 0
                    net_usd = float(net_veb_clean) / exchange_rate if net_veb_clean else 0

                    print(f"\n  Calculated USD Values:")
                    print(f"    Monthly Salary (Col K): ${monthly_usd:.2f} USD")
                    print(f"    NET Salary (Col Z):     ${net_usd:.2f} USD")

                    # Calculate 70/25/5 breakdown
                    salary_70 = monthly_usd * 0.70
                    bonus_25 = monthly_usd * 0.25
                    extra_5 = monthly_usd * 0.05

                    print(f"\n  Calculated 70/25/5 Distribution:")
                    print(f"    Salary Base (70%):      ${salary_70:.2f} USD")
                    print(f"    Regular Bonus (25%):    ${bonus_25:.2f} USD")
                    print(f"    Extra Bonus (5%):       ${extra_5:.2f} USD")
                    print(f"    Total:                  ${monthly_usd:.2f} USD")

                except Exception as e:
                    print(f"\n  ⚠️  Error calculating USD values: {e}")

                break

    if not nelci_found:
        print("\n✗ NELCI BRITO not found in the spreadsheet!")
        print("   Searching for similar names...")
        for row_idx, row in enumerate(all_data[4:], start=5):
            if len(row) > 3:
                employee_name = row[3].strip().upper()
                if 'BRITO' in employee_name or 'NELCI' in employee_name:
                    print(f"   Row {row_idx}: {row[3]}")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
