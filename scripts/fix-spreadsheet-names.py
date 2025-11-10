#!/usr/bin/env python3
"""Fix name mismatches in spreadsheet"""
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

print('Updating names in spreadsheet...')

# Update Row 13, Column D: GABRIEL ESPANA → GABRIEL ESPAÑA
worksheet.update_acell('D13', 'GABRIEL ESPAÑA')
print('✓ Row 13 (D13): GABRIEL ESPANA → GABRIEL ESPAÑA')

# Update Row 22, Column D: YUDELIS BRITO → YUDELYS BRITO
worksheet.update_acell('D22', 'YUDELYS BRITO')
print('✓ Row 22 (D22): YUDELIS BRITO → YUDELYS BRITO')

print('\n✓ Spreadsheet names corrected!')
