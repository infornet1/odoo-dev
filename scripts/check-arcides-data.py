#!/usr/bin/env python3
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

# Get exchange rate
exchange_rate = float(worksheet.acell('O2').value.replace(',', ''))

# Get all data
all_data = worksheet.get_all_values()

# Find ARCIDES
for row in all_data[5:]:  # Start from row 6
    if len(row) > 3 and 'ARCIDES' in row[3].upper():
        k = float(row[10].replace(',', ''))
        l = float(row[11].replace(',', '')) if row[11] else 0
        m = float(row[12].replace(',', ''))
        z = float(row[25].replace(',', '')) if row[25] else 0

        print('ARCIDES ARZOLA Spreadsheet Data:')
        print(f'  K (Salary): {k:,.2f} VEB = ${k/exchange_rate:.2f} USD')
        print(f'  L (Other):  {l:,.2f} VEB = ${l/exchange_rate:.2f} USD')
        print(f'  M (Cesta):  {m:,.2f} VEB = ${m/exchange_rate:.2f} USD')
        print(f'  K+L+M Total: {k+l+m:,.2f} VEB = ${(k+l+m)/exchange_rate:.2f} USD')
        print(f'  Z (NET): ${z:.2f} USD')
        print()
        print('Current Odoo Contract:')
        print('  wage: $549.94')
        print('  70+25+5 sum: $292.13')
        print()
        print('Analysis:')
        print(f'  If wage should be K+L+M: ${(k+l+m)/exchange_rate:.2f} vs $549.94 (MISMATCH by ${549.94-(k+l+m)/exchange_rate:.2f})')
        print(f'  Spreadsheet NET: ${z:.2f}')
        break
