#!/usr/bin/env python3
"""
Inspect Google Spreadsheet structure to understand column layout
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'

print("Inspecting Spreadsheet Structure")
print("=" * 80)

# Connect to Google Sheets
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE, scope
)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet(TAB_NAME)

print(f"Spreadsheet: {spreadsheet.title}")
print(f"Worksheet: {TAB_NAME}")
print("=" * 80)

# Read first 5 rows to understand structure
print("\nReading rows 1-10, columns A-J...")
print("-" * 80)

header_data = worksheet.get('A1:J10')

for row_idx, row in enumerate(header_data, start=1):
    print(f"Row {row_idx}: {row}")

print("\n" + "=" * 80)
print("Now reading the data range D4:D48 that user mentioned...")
print("-" * 80)

wage_data = worksheet.get('D4:D48')
for row_idx, row in enumerate(wage_data, start=4):
    print(f"Row {row_idx}, Col D: {row}")
