#!/usr/bin/env python3
"""Reverse-engineer the exact formula for Column Y in spreadsheet"""
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

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

# Get exchange rate
exchange_rate = float(worksheet.acell('O2').value.replace(',', '.'))

# Check a few employees to understand the pattern
print("=" * 80)
print("ANALYZING COLUMN Y FORMULA")
print("=" * 80)
print(f"\nExchange Rate: {exchange_rate:.2f} VEB/USD\n")

# Check rows 5-10 (ARCIDES to NELCI)
for row_num in [5, 6, 10]:  # ARCIDES, NORKA, NELCI
    row_data = worksheet.row_values(row_num)

    if len(row_data) > 3:
        name = row_data[3]

        # Salary columns
        k_veb = parse_veb(row_data[10]) if len(row_data) > 10 else 0.0
        l_veb = parse_veb(row_data[11]) if len(row_data) > 11 else 0.0
        m_veb = parse_veb(row_data[12]) if len(row_data) > 12 else 0.0

        # Deduction columns
        n_veb = parse_veb(row_data[13]) if len(row_data) > 13 else 0.0  # IVSS
        o_veb = parse_veb(row_data[14]) if len(row_data) > 14 else 0.0  # FAOV
        p_veb = parse_veb(row_data[15]) if len(row_data) > 15 else 0.0  # INCES
        q_veb = parse_veb(row_data[16]) if len(row_data) > 16 else 0.0  # Ref ARI
        r_veb = parse_veb(row_data[17]) if len(row_data) > 17 else 0.0  # ARI
        s_veb = parse_veb(row_data[18]) if len(row_data) > 18 else 0.0  # OTRAS

        # Result columns
        y_value = parse_veb(row_data[24]) if len(row_data) > 24 else 0.0  # Column Y
        z_value = parse_veb(row_data[25]) if len(row_data) > 25 else 0.0  # Column Z

        # Convert to USD
        k_usd = k_veb / exchange_rate
        l_usd = l_veb / exchange_rate
        m_usd = m_veb / exchange_rate

        total_salary_usd = k_usd + l_usd + m_usd

        # Deductions in USD
        n_usd = n_veb / exchange_rate
        o_usd = o_veb / exchange_rate
        p_usd = p_veb / exchange_rate
        q_usd = q_veb / exchange_rate
        r_usd = r_veb / exchange_rate
        s_usd = s_veb / exchange_rate

        total_ded_usd = n_usd + o_usd + p_usd + q_usd + r_usd + s_usd

        print(f"{'='*80}")
        print(f"Row {row_num}: {name}")
        print(f"{'='*80}")

        print(f"\n💰 SALARY (Monthly):")
        print(f"  K: ${k_usd:>10.2f}")
        print(f"  L: ${l_usd:>10.2f}")
        print(f"  M: ${m_usd:>10.2f}")
        print(f"  ─────────────────")
        print(f"  Total: ${total_salary_usd:>10.2f}")

        print(f"\n📉 DEDUCTIONS (Monthly):")
        print(f"  N (IVSS):  ${n_usd:>10.2f}")
        print(f"  O (FAOV):  ${o_usd:>10.2f}")
        print(f"  P (INCES): ${p_usd:>10.2f}")
        print(f"  Q (Ref):   ${q_usd:>10.2f}")
        print(f"  R (ARI):   ${r_usd:>10.2f}")
        print(f"  S (Other): ${s_usd:>10.2f}")
        print(f"  ─────────────────")
        print(f"  Total: ${total_ded_usd:>10.2f}")

        print(f"\n📊 SPREADSHEET VALUES:")
        print(f"  Column Y (Bi-weekly): ${y_value:>10.2f}")
        print(f"  Column Z (Monthly):   ${z_value:>10.2f}")

        # Test different formulas
        print(f"\n🔍 TESTING FORMULAS:")

        # Formula 1: (Salary - Deductions) / 2
        monthly_net = total_salary_usd - total_ded_usd
        biweekly_1 = monthly_net / 2
        print(f"\n  Formula 1: (Salary - Ded) / 2")
        print(f"    = (${total_salary_usd:.2f} - ${total_ded_usd:.2f}) / 2")
        print(f"    = ${monthly_net:.2f} / 2")
        print(f"    = ${biweekly_1:.2f}")
        print(f"    Matches Column Y? {abs(biweekly_1 - y_value) < 1.0}")
        print(f"    Difference: ${abs(biweekly_1 - y_value):.2f}")

        # Formula 2: Salary/2 - Deductions
        biweekly_2 = (total_salary_usd / 2) - total_ded_usd
        print(f"\n  Formula 2: Salary/2 - Deductions (monthly)")
        print(f"    = ${total_salary_usd:.2f}/2 - ${total_ded_usd:.2f}")
        print(f"    = ${total_salary_usd/2:.2f} - ${total_ded_usd:.2f}")
        print(f"    = ${biweekly_2:.2f}")
        print(f"    Matches Column Y? {abs(biweekly_2 - y_value) < 1.0}")
        print(f"    Difference: ${abs(biweekly_2 - y_value):.2f}")

        # Formula 3: Salary/2 - Deductions/2
        biweekly_3 = (total_salary_usd / 2) - (total_ded_usd / 2)
        print(f"\n  Formula 3: Salary/2 - Deductions/2")
        print(f"    = ${total_salary_usd/2:.2f} - ${total_ded_usd/2:.2f}")
        print(f"    = ${biweekly_3:.2f}")
        print(f"    Matches Column Y? {abs(biweekly_3 - y_value) < 1.0}")
        print(f"    Difference: ${abs(biweekly_3 - y_value):.2f}")

        # Check Column Z vs monthly net
        print(f"\n  Column Z vs Monthly NET:")
        print(f"    Column Z: ${z_value:.2f}")
        print(f"    Monthly NET: ${monthly_net:.2f}")
        print(f"    Difference: ${abs(z_value - monthly_net):.2f}")

        print()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nThe formula that matches Column Y will be identified above.")
print("This will tell us how to configure Odoo payslips correctly.")
print("=" * 80)
