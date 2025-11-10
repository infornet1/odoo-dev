#!/usr/bin/env python3
"""Check what columns Y and Z actually represent"""
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

# Get headers (Row 4)
headers = worksheet.row_values(4)

# Column indices (0-based)
print("=" * 80)
print("COLUMN HEADERS CHECK")
print("=" * 80)

cols_of_interest = {
    'K': (10, 'K'),
    'L': (11, 'L'),
    'M': (12, 'M'),
    'N': (13, 'N'),
    'O': (14, 'O'),
    'Y': (24, 'Y'),
    'Z': (25, 'Z'),
}

for name, (idx, col_letter) in cols_of_interest.items():
    if len(headers) > idx:
        print(f"\nColumn {col_letter} (index {idx}):")
        print(f"  Header: {headers[idx]}")
    else:
        print(f"\nColumn {col_letter} (index {idx}): NOT FOUND")

# Get NELCI's data (Row 10)
print("\n" + "=" * 80)
print("NELCI BRITO DATA (Row 10)")
print("=" * 80)

row_10 = worksheet.row_values(10)
for name, (idx, col_letter) in cols_of_interest.items():
    if len(row_10) > idx:
        print(f"Column {col_letter}: {row_10[idx]}")
    else:
        print(f"Column {col_letter}: NOT FOUND")

print("\n" + "=" * 80)
