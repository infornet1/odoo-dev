#!/usr/bin/env python3
"""List all 44 employees from spreadsheet range D5:D48"""
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

# Read range D5:D48 (44 employees)
employee_names = worksheet.col_values(4)[4:48]  # Column D, rows 5-48

print("=" * 80)
print("COMPLETE LIST OF 44 EMPLOYEES")
print("=" * 80)
print(f"\nSpreadsheet: {SPREADSHEET_ID}")
print("Sheet: 31oct2025")
print("Range: D5:D48\n")
print("-" * 80)

for i, name in enumerate(employee_names, start=1):
    row_num = i + 4  # Row 5 starts at index 1
    if i == 1:
        print(f"{i:2d}. {name} (Row {row_num}) ← FIRST")
    elif i == len(employee_names):
        print(f"{i:2d}. {name} (Row {row_num}) ← LAST")
    else:
        print(f"{i:2d}. {name} (Row {row_num})")

print("-" * 80)
print(f"\nTotal employees: {len(employee_names)}")
print(f"\nFirst employee: {employee_names[0]}")
print(f"Last employee:  {employee_names[-1]}")
print("\n" + "=" * 80)
