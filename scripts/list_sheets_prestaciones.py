#!/usr/bin/env python3
"""
List sheets in Prestaciones Interest spreadsheet
=================================================

Author: Claude Code
Date: 2025-11-13
"""

import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load service account credentials
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/gsheet_credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

with open(CREDENTIALS_FILE, 'r') as f:
    creds_data = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds_data, scopes=SCOPES)

# Build the service
service = build('sheets', 'v4', credentials=credentials)

SPREADSHEET_ID = '1-lSovpboNcKli9_qlYe1i8DTXajIR8QBUiKuhaDNZfU'

print("Fetching sheet names...")

try:
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get('sheets', [])

    print(f"\nFound {len(sheets)} sheets:")
    for i, sheet in enumerate(sheets, 1):
        properties = sheet.get('properties', {})
        sheet_id = properties.get('sheetId')
        title = properties.get('title')
        print(f"  {i}. '{title}' (ID: {sheet_id})")

except Exception as e:
    print(f"Error: {e}")
