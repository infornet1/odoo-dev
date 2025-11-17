#!/usr/bin/env python3
"""
Inspect wider range to find wage columns
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'

print("Inspecting Spreadsheet - Wider Range")
print("=" * 120)

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
print("=" * 120)

# Read first 5 data rows, columns A-Z
print("\nReading rows 4-10, columns A-Z (header + 6 employees)...")
print("-" * 120)

header_data = worksheet.get('A4:Z10')

for row_idx, row in enumerate(header_data, start=4):
    # Print row number and first 20 columns
    print(f"Row {row_idx}:")
    for col_idx, cell in enumerate(row[:20], start=1):
        if cell:
            col_letter = chr(64 + col_idx)  # A=65, so 64+1=65=A
            print(f"  [{col_letter}]: {cell}")
    print()
