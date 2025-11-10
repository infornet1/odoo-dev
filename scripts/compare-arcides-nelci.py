#!/usr/bin/env python3
"""Compare ARCIDES and NELCI spreadsheet data with current Odoo contracts"""

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
exchange_rate_str = worksheet.acell('O2').value
exchange_rate = float(exchange_rate_str.replace(',', ''))

# Get all data
all_data = worksheet.get_all_values()

print("=" * 80)
print("COMPARING ARCIDES and NELCI - Spreadsheet vs Odoo")
print("=" * 80)
print(f"Exchange Rate: {exchange_rate:.2f} VEB/USD\n")

# Current Odoo values (from production query)
odoo_data = {
    'ARCIDES ARZOLA': {
        'wage': 549.94,
        'ueipab_salary_base': 204.49,
        'ueipab_bonus_regular': 73.03,
        'ueipab_extra_bonus': 14.61,
        'total_70_25_5': 292.13
    },
    'NELCI BRITO': {
        'wage': 163.52,  # Assumed from earlier analysis
        'ueipab_salary_base': 114.46,
        'ueipab_bonus_regular': 40.88,
        'ueipab_extra_bonus': 8.18,
        'total_70_25_5': 163.52
    }
}

for target_name in ['ARCIDES', 'NELCI']:
    for row in all_data[4:]:  # Start from row 5 (index 4)
        if len(row) > 25 and target_name in row[3].upper():
            emp_name = row[3]

            # Parse VEB values
            k_veb = float(row[10].replace(',', '')) if row[10] else 0
            l_veb = float(row[11].replace(',', '')) if row[11] else 0
            m_veb = float(row[12].replace(',', '')) if row[12] else 0
            z_str = row[25]
            z_usd = float(z_str.replace(',', '')) if z_str else 0

            # Convert to USD
            k_usd = k_veb / exchange_rate
            l_usd = l_veb / exchange_rate
            m_usd = m_veb / exchange_rate
            total_klm = k_usd + l_usd + m_usd

            print(f"{'='*80}")
            print(f"{emp_name}")
            print(f"{'='*80}")

            print(f"\nSPREADSHEET DATA:")
            print(f"  Column K: {k_veb:>12,.2f} VEB = ${k_usd:>8.2f} USD")
            print(f"  Column L: {l_veb:>12,.2f} VEB = ${l_usd:>8.2f} USD")
            print(f"  Column M: {m_veb:>12,.2f} VEB = ${m_usd:>8.2f} USD")
            print(f"  {'─'*50}")
            print(f"  K+L+M:    {k_veb+l_veb+m_veb:>12,.2f} VEB = ${total_klm:>8.2f} USD")
            print(f"  Column Z (NET):                   ${z_usd:>8.2f} USD")

            # Get Odoo data
            full_name = [k for k in odoo_data.keys() if target_name in k][0]
            odoo = odoo_data[full_name]

            print(f"\nCURRENT ODOO CONTRACT:")
            print(f"  wage:                 ${odoo['wage']:>8.2f}")
            print(f"  ueipab_salary_base:   ${odoo['ueipab_salary_base']:>8.2f}")
            print(f"  ueipab_bonus_regular: ${odoo['ueipab_bonus_regular']:>8.2f}")
            print(f"  ueipab_extra_bonus:   ${odoo['ueipab_extra_bonus']:>8.2f}")
            print(f"  {'─'*50}")
            print(f"  Total (70+25+5):      ${odoo['total_70_25_5']:>8.2f}")

            print(f"\nANALYSIS:")
            print(f"  Spreadsheet K+L+M:    ${total_klm:>8.2f}")
            print(f"  Odoo wage field:      ${odoo['wage']:>8.2f}")
            print(f"  Difference:           ${abs(odoo['wage'] - total_klm):>8.2f}")
            print()
            print(f"  Odoo 70+25+5 sum:     ${odoo['total_70_25_5']:>8.2f}")
            print(f"  Spreadsheet K+L+M:    ${total_klm:>8.2f}")
            print(f"  Difference:           ${abs(odoo['total_70_25_5'] - total_klm):>8.2f}")

            print()
            break

print("=" * 80)
