#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check actual column headers in spreadsheet to understand structure
"""

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'
TARGET_SHEET = '31oct2025'

def main():
    print("=" * 80)
    print("CHECKING SPREADSHEET STRUCTURE")
    print("=" * 80)

    # Connect
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(TARGET_SHEET)

    print(f"✓ Connected to: {spreadsheet.title}")
    print(f"✓ Worksheet: {TARGET_SHEET}")

    # Get first 6 rows to see headers
    all_data = worksheet.get_all_values()

    print("\n" + "=" * 80)
    print("FIRST 6 ROWS (to identify header row)")
    print("=" * 80)

    for row_idx in range(min(6, len(all_data))):
        print(f"\nROW {row_idx + 1}:")
        row = all_data[row_idx]
        for col_idx in range(min(30, len(row))):
            col_letter = chr(65 + col_idx)
            value = row[col_idx][:50] if row[col_idx] else ""
            if value:
                print(f"  {col_letter}: {value}")

    # Find NELCI BRITO and show columns K through S
    print("\n" + "=" * 80)
    print("NELCI BRITO - COLUMNS K THROUGH S")
    print("=" * 80)

    # Get exchange rate from O2
    exchange_rate_str = worksheet.acell('O2').value
    exchange_rate = float(exchange_rate_str.replace(',', ''))
    print(f"\nExchange Rate (O2): {exchange_rate:.2f} VEB/USD")

    for row_idx, row in enumerate(all_data[5:], start=6):
        if len(row) > 3 and 'NELCI' in row[3].upper() and 'BRITO' in row[3].upper():
            print(f"\nFound NELCI BRITO at row {row_idx}:")
            print(f"  Name: {row[3]}")

            # Show columns K through S (indices 10-18)
            columns = {
                'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14,
                'P': 15, 'Q': 16, 'R': 17, 'S': 18
            }

            print("\n  VEB Values:")
            for col_letter, col_idx in columns.items():
                if len(row) > col_idx:
                    value_str = row[col_idx]
                    try:
                        value_veb = float(value_str.replace(',', ''))
                        value_usd = value_veb / exchange_rate
                        print(f"    {col_letter}: {value_veb:>12,.2f} VEB = ${value_usd:>8.2f} USD")
                    except:
                        print(f"    {col_letter}: {value_str}")

            # Calculate totals
            print("\n  Calculations:")
            k = float(row[10].replace(',', '')) if len(row) > 10 else 0
            l = float(row[11].replace(',', '')) if len(row) > 11 else 0
            m = float(row[12].replace(',', '')) if len(row) > 12 else 0

            k_usd = k / exchange_rate
            l_usd = l / exchange_rate
            m_usd = m / exchange_rate

            total_klm = k_usd + l_usd + m_usd

            print(f"    K + L + M = ${total_klm:.2f} USD (Total salary)")

            # Check Column Z (NET)
            if len(row) > 25:
                z_str = row[25]
                try:
                    z_usd = float(z_str.replace(',', ''))
                    print(f"    Column Z (NET) = ${z_usd:.2f} USD")
                    deductions = total_klm - z_usd
                    print(f"    Deductions = ${deductions:.2f} USD ({(deductions/total_klm*100):.2f}%)")
                except:
                    print(f"    Column Z: {z_str}")

            break

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
