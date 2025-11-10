#!/usr/bin/env python3
"""Check NELCI's deduction columns in spreadsheet"""
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

# Get NELCI's row (Row 10)
nelci_row = worksheet.row_values(10)

# Get exchange rate
exchange_rate = float(worksheet.acell('O2').value.replace(',', '.'))

print("=" * 80)
print("NELCI BRITO - SPREADSHEET DEDUCTION ANALYSIS (Row 10)")
print("=" * 80)

# Parse VEB value
def parse_veb(value):
    if not value:
        return 0.0
    value = str(value).strip()
    if '.' in value and ',' in value:
        if value.rindex('.') > value.rindex(','):
            value = value.replace(',', '')
        else:
            value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        value = value.replace(',', '.')
    try:
        return float(value)
    except:
        return 0.0

print(f"\nExchange Rate: {exchange_rate:.2f} VEB/USD")
print("\n" + "-" * 80)
print(f"{'Column':<8} {'Header':<50} {'VEB':>15} {'USD':>12}")
print("-" * 80)

# Map column letters to indices
col_map = {
    'K': 10, 'L': 11, 'M': 12,
    'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
    'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23,
    'Y': 24, 'Z': 25
}

# Salary columns
salary_cols = ['K', 'L', 'M']
deduction_cols = ['N', 'O', 'P', 'Q', 'R', 'S']
calculation_cols = ['Y', 'Z']

# Show salary columns
print("\n💰 SALARY COMPONENTS:")
total_salary_veb = 0
total_salary_usd = 0
for col in salary_cols:
    idx = col_map[col]
    if len(headers) > idx and len(nelci_row) > idx:
        header = headers[idx]
        value_veb = parse_veb(nelci_row[idx])
        value_usd = value_veb / exchange_rate
        total_salary_veb += value_veb
        total_salary_usd += value_usd
        print(f"{col:<8} {header[:48]:<50} {value_veb:>15,.2f} ${value_usd:>11.2f}")

print("-" * 80)
print(f"{'TOTAL':<8} {'Gross Salary (K+L+M)':<50} {total_salary_veb:>15,.2f} ${total_salary_usd:>11.2f}")

# Show deduction columns
print("\n📉 DEDUCTIONS (Monthly):")
total_ded_veb = 0
total_ded_usd = 0
for col in deduction_cols:
    idx = col_map[col]
    if len(headers) > idx and len(nelci_row) > idx:
        header = headers[idx]
        value_veb = parse_veb(nelci_row[idx])
        value_usd = value_veb / exchange_rate
        total_ded_veb += value_veb
        total_ded_usd += value_usd
        print(f"{col:<8} {header[:48]:<50} {value_veb:>15,.2f} ${value_usd:>11.2f}")

print("-" * 80)
print(f"{'TOTAL':<8} {'Total Deductions':<50} {total_ded_veb:>15,.2f} ${total_ded_usd:>11.2f}")

# Show calculation columns
print("\n📊 CALCULATED NET:")
for col in calculation_cols:
    idx = col_map[col]
    if len(headers) > idx and len(nelci_row) > idx:
        header = headers[idx]
        value = parse_veb(nelci_row[idx])
        # Y and Z are already in USD
        print(f"{col:<8} {header[:48]:<50} {'':>15} ${value:>11.2f}")

# Manual calculation
net_monthly_calculated = total_salary_usd - total_ded_usd

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

column_z_value = parse_veb(nelci_row[col_map['Z']]) if len(nelci_row) > col_map['Z'] else 0
column_y_value = parse_veb(nelci_row[col_map['Y']]) if len(nelci_row) > col_map['Y'] else 0

print(f"\nGross (K+L+M):           ${total_salary_usd:.2f}")
print(f"Deductions (N+O+P+Q+R+S): -${total_ded_usd:.2f}")
print(f"────────────────────────────────")
print(f"Calculated NET (monthly): ${net_monthly_calculated:.2f}")
print(f"Column Z (monthly):       ${column_z_value:.2f}")
print(f"Column Y (bi-weekly):     ${column_y_value:.2f}")

# Bi-weekly calculation
gross_biweekly = total_salary_usd * 0.5
ded_biweekly = total_ded_usd * 0.5
net_biweekly = gross_biweekly - ded_biweekly

print(f"\n📋 BI-WEEKLY (15 days = 50%):")
print(f"Gross × 50%:              ${gross_biweekly:.2f}")
print(f"Deductions × 50%:        -${ded_biweekly:.2f}")
print(f"────────────────────────────────")
print(f"NET (15 days):            ${net_biweekly:.2f}")
print(f"Column Y (bi-weekly):     ${column_y_value:.2f}")
print(f"Difference:               ${abs(net_biweekly - column_y_value):.2f}")

if abs(net_biweekly - column_y_value) < 1.0:
    print("\n✓ Calculated NET matches Column Y!")
else:
    print("\n⚠️  Calculated NET doesn't match Column Y")

# Compare to Odoo payslip
odoo_gross = 178.65
odoo_ded = 9.32
odoo_net = 169.32

print("\n" + "=" * 80)
print("ODOO vs SPREADSHEET COMPARISON (15 days)")
print("=" * 80)

print(f"\n{'':30} {'Odoo SLIP/239':>15} {'Spreadsheet':>15} {'Difference':>15}")
print("-" * 80)
print(f"{'Gross:':<30} ${odoo_gross:>14.2f} ${gross_biweekly:>14.2f} ${odoo_gross - gross_biweekly:>14.2f}")
print(f"{'Deductions:':<30} ${odoo_ded:>14.2f} ${ded_biweekly:>14.2f} ${odoo_ded - ded_biweekly:>14.2f}")
print(f"{'NET:':<30} ${odoo_net:>14.2f} ${column_y_value:>14.2f} ${odoo_net - column_y_value:>14.2f}")

if abs(odoo_ded - ded_biweekly) > 5.0:
    print(f"\n❌ DEDUCTIONS are significantly different!")
    print(f"   Odoo deducts:        ${odoo_ded:.2f}")
    print(f"   Spreadsheet expects: ${ded_biweekly:.2f}")
    print(f"   Missing deductions:  ${ded_biweekly - odoo_ded:.2f}")

print("\n" + "=" * 80)
