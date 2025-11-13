#!/usr/bin/env python3
"""
Fetch Monica Mosqueda liquidation data from Google Sheets
"""

import json
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load service account credentials
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/gsheet_credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# Spreadsheet details
LIQUIDATION_SPREADSHEET_ID = '1fvmY6AUWR2OvoLVApIlxu8Z3p_A8TcM9nBDc03_6WUQ'
LIQUIDATION_SHEET_NAME = 'Liquidacion Monica Mosqueda'

INTEREST_SPREADSHEET_ID = '1-lSovpboNcKli9_qlYe1i8DTXajIR8QBUiKuhaDNZfU'
INTEREST_SHEET_NAME = 'Monica Mosqueda'

def get_sheets_service():
    """Create Google Sheets API service"""
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    service = build('sheets', 'v4', credentials=credentials)
    return service

def fetch_sheet_data(service, spreadsheet_id, sheet_name):
    """Fetch all data from a specific sheet"""
    try:
        # Get all data from the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{sheet_name}'!A1:Z1000"  # Fetch columns A-Z, rows 1-1000
        ).execute()

        values = result.get('values', [])

        if not values:
            print(f"No data found in sheet: {sheet_name}")
            return None

        return values
    except Exception as e:
        print(f"Error fetching sheet '{sheet_name}': {e}")
        return None

def print_table(data, title):
    """Print data in a formatted table"""
    if not data:
        print(f"\n{title}: NO DATA")
        return

    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")

    # Print each row
    for row_idx, row in enumerate(data):
        if row_idx == 0:
            # Header row
            print(" | ".join(f"{cell:20}" for cell in row))
            print("-" * 80)
        else:
            # Data rows
            print(" | ".join(f"{cell:20}" for cell in row))

    print()

def main():
    print("Fetching Monica Mosqueda liquidation data from Google Sheets...")
    print()

    # Create service
    service = get_sheets_service()

    # Fetch liquidation data
    print(f"Fetching: {LIQUIDATION_SPREADSHEET_ID} / '{LIQUIDATION_SHEET_NAME}'")
    liquidation_data = fetch_sheet_data(service, LIQUIDATION_SPREADSHEET_ID, LIQUIDATION_SHEET_NAME)
    print_table(liquidation_data, "LIQUIDATION DATA - Monica Mosqueda")

    # Fetch interest calculation data
    print(f"\nFetching: {INTEREST_SPREADSHEET_ID} / '{INTEREST_SHEET_NAME}'")
    interest_data = fetch_sheet_data(service, INTEREST_SPREADSHEET_ID, INTEREST_SHEET_NAME)
    print_table(interest_data, "INTEREST CALCULATION DATA - Monica Mosqueda")

    # Save to JSON for further analysis
    output_file = '/opt/odoo-dev/scripts/monica_mosqueda_data.json'
    with open(output_file, 'w') as f:
        json.dump({
            'liquidation': liquidation_data,
            'interest': interest_data
        }, f, indent=2)

    print(f"\n✅ Data saved to: {output_file}")
    print()

if __name__ == '__main__':
    main()
