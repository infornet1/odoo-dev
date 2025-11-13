#!/usr/bin/env python3
"""
Fetch Prestaciones Social Interest Report Example
==================================================

Fetches the example format from Josefina Rodriguez sheet
to understand the report layout requirements.

Author: Claude Code
Date: 2025-11-13
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

print("="*80)
print("FETCHING PRESTACIONES INTEREST REPORT EXAMPLE")
print("="*80)
print()

# Load service account credentials
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/gsheet_credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

with open(CREDENTIALS_FILE, 'r') as f:
    creds_data = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds_data, scopes=SCOPES)

# Build the service
service = build('sheets', 'v4', credentials=credentials)

# Spreadsheet details
SPREADSHEET_ID = '1-lSovpboNcKli9_qlYe1i8DTXajIR8QBUiKuhaDNZfU'
SHEET_NAME = 'Josefina Rodriguez '
RANGE_NAME = f'{SHEET_NAME}!A8:K20'

print(f"Spreadsheet ID: {SPREADSHEET_ID}")
print(f"Sheet: {SHEET_NAME}")
print(f"Range: A8:K20")
print()

try:
    # Fetch the data
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()

    values = result.get('values', [])

    if not values:
        print("No data found in range.")
    else:
        print(f"Found {len(values)} rows of data:")
        print("-" * 80)

        for i, row in enumerate(values, start=8):
            # Pad row to ensure 11 columns (A-K)
            row_padded = row + [''] * (11 - len(row))

            # Format for display
            print(f"Row {i:2d}: ", end='')
            for j, cell in enumerate(row_padded):
                col_letter = chr(65 + j)  # A=65, B=66, etc.
                value = str(cell)[:15] if cell else ''
                print(f"{col_letter}:{value:15s} ", end='')
            print()

        print("-" * 80)
        print()

        # Try to identify column headers (row 8)
        if len(values) > 0:
            print("COLUMN HEADERS (Row 8):")
            headers = values[0]
            for i, header in enumerate(headers):
                col_letter = chr(65 + i)
                print(f"  {col_letter}: {header}")
            print()

        # Show data rows
        if len(values) > 1:
            print("DATA ROWS (Rows 9-20):")
            for i, row in enumerate(values[1:], start=9):
                print(f"  Row {i}: {row}")
            print()

except Exception as e:
    print(f"❌ Error fetching spreadsheet: {e}")
    import traceback
    traceback.print_exc()

print("="*80)
