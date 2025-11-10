#!/usr/bin/env python3
"""Check NELCI BRITO payslip SLIP/238 vs spreadsheet"""
import psycopg2
import gspread
from google.oauth2.service_account import Credentials

# Database config
db_config = {
    'host': 'localhost',
    'port': 5433,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo8069'
}

# Spreadsheet config
SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'

print("=" * 80)
print("NELCI BRITO - SLIP/238 vs SPREADSHEET COMPARISON")
print("=" * 80)

# Get payslip data from Odoo
conn = psycopg2.connect(**db_config)
cur = conn.cursor()

query = """
SELECT
    p.number,
    p.name,
    p.date_from,
    p.date_to,
    p.state,
    pl.name as line_name,
    pl.code,
    pl.total,
    pl.amount,
    pl.quantity,
    pl.rate
FROM hr_payslip p
JOIN hr_payslip_line pl ON pl.slip_id = p.id
WHERE p.number = 'SLIP/238'
ORDER BY pl.sequence, pl.id;
"""

cur.execute(query)
rows = cur.fetchall()

if not rows:
    print("⚠️  Payslip SLIP/238 not found!")
    cur.close()
    conn.close()
    exit(1)

# Display payslip header
p = rows[0]
print(f"\n📄 PAYSLIP: {p[0]}")
print(f"Employee: {p[1]}")
print(f"Period: {p[2]} to {p[3]}")
print(f"State: {p[4]}")
print(f"\n{'Line Name':<40} {'Code':<15} {'Total':>12}")
print("-" * 80)

gross = 0
net = 0
deductions = 0

for row in rows:
    line_name_raw = row[5]
    # Handle translation dict
    if isinstance(line_name_raw, dict):
        line_name = line_name_raw.get('en_US', str(line_name_raw))
    else:
        line_name = str(line_name_raw) if line_name_raw else ""

    code = str(row[6]) if row[6] else ""
    total = float(row[7]) if row[7] else 0.0

    print(f"{line_name:<50} {code:<20} ${total:>11.2f}")

    # Track gross, deductions, net
    if code in ['VE_SALARY_70', 'VE_BONUS_25', 'VE_EXTRA_5', 'VE_CESTA_TICKET']:
        gross += total
    elif code in ['VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED']:
        deductions += total
    elif code == 'VE_NET':
        net = total

print("-" * 80)
print(f"{'GROSS (before deductions):':<40} ${gross:>11.2f}")
print(f"{'DEDUCTIONS:':<40} ${deductions:>11.2f}")
print(f"{'NET (Column Z equivalent for 15 days):':<40} ${net:>11.2f}")

# Get contract data
cur.execute("""
SELECT
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO'
AND c.state = 'open'
ORDER BY c.date_start DESC
LIMIT 1;
""")

contract = cur.fetchone()
if contract:
    print(f"\n📋 CONTRACT:")
    print(f"{'wage (K+L+M GROSS):':<40} ${contract[0]:>11.2f}")
    print(f"{'ueipab_salary_base (K):':<40} ${contract[1]:>11.2f}")
    print(f"{'ueipab_bonus_regular (M):':<40} ${contract[2]:>11.2f}")
    print(f"{'ueipab_extra_bonus (L):':<40} ${contract[3]:>11.2f}")

cur.close()
conn.close()

# Get spreadsheet data
scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')

# NELCI BRITO is in Row 10
row_data = worksheet.row_values(10)

# Get exchange rate from O2
exchange_rate = float(worksheet.acell('O2').value.replace(',', '.'))

# Column indices (0-based)
COL_D = 3   # Name
COL_K = 10  # Basic Salary (VEB)
COL_L = 11  # Other Bonus (VEB)
COL_M = 12  # Major Bonus (VEB)
COL_Y = 24  # Bi-weekly calc
COL_Z = 25  # Net monthly balance

name = row_data[COL_D] if len(row_data) > COL_D else "N/A"

# Parse VEB values
# Values might be in different formats:
# - "30.859,88" (European: . thousands, , decimal)
# - "30859.88" (US: no thousands, . decimal)
# - "30,859.88" (US: , thousands, . decimal)
def parse_veb(value):
    if not value:
        return 0.0
    value = str(value).strip()

    # Check if there's both . and ,
    if '.' in value and ',' in value:
        # Determine which is decimal separator (last one)
        if value.rindex('.') > value.rindex(','):
            # . is decimal, , is thousands (US format: 30,859.88)
            value = value.replace(',', '')
        else:
            # , is decimal, . is thousands (European: 30.859,88)
            value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        # Only comma - assume decimal separator
        value = value.replace(',', '.')
    # If only . or no separator, leave as is

    try:
        return float(value)
    except:
        print(f"⚠️  Failed to parse: '{value}'")
        return 0.0

k_veb = parse_veb(row_data[COL_K]) if len(row_data) > COL_K else 0.0
l_veb = parse_veb(row_data[COL_L]) if len(row_data) > COL_L else 0.0
m_veb = parse_veb(row_data[COL_M]) if len(row_data) > COL_M else 0.0

# Y and Z are ALREADY in USD (headers have $ symbol)
y_usd = parse_veb(row_data[COL_Y]) if len(row_data) > COL_Y else 0.0
z_usd = parse_veb(row_data[COL_Z]) if len(row_data) > COL_Z else 0.0

# Convert K, L, M to USD
k_usd = k_veb / exchange_rate
l_usd = l_veb / exchange_rate
m_usd = m_veb / exchange_rate

gross_usd = k_usd + l_usd + m_usd

print(f"\n📊 SPREADSHEET (Row 10 - {name}):")
print(f"Exchange rate: {exchange_rate:.2f} VEB/USD")
print("-" * 80)
print(f"{'K (Basic Salary):':<40} {k_veb:>15,.2f} VEB = ${k_usd:>11.2f}")
print(f"{'L (Other Bonus):':<40} {l_veb:>15,.2f} VEB = ${l_usd:>11.2f}")
print(f"{'M (Major Bonus):':<40} {m_veb:>15,.2f} VEB = ${m_usd:>11.2f}")
print("-" * 80)
print(f"{'K+L+M (GROSS 30 days):':<40} {k_veb+l_veb+m_veb:>15,.2f} VEB = ${gross_usd:>11.2f}")
print()
print(f"{'Column Y (Bi-weekly NET + Cesta):':<40} ${y_usd:>11.2f} USD")
print(f"{'Column Z (Monthly NET + Cesta):':<40} ${z_usd:>11.2f} USD")

print("\n" + "=" * 80)
print("COMPARISON ANALYSIS")
print("=" * 80)

print(f"\n📄 PAYSLIP SLIP/238 (15 days):")
print(f"   Gross:       ${gross:>11.2f}")
print(f"   Deductions:  ${deductions:>11.2f}")
print(f"   NET:         ${net:>11.2f}")

print(f"\n📊 SPREADSHEET (bi-weekly):")
print(f"   Column Y (Bi-weekly NET + Cesta): ${y_usd:>11.2f}")

print(f"\n🔍 COMPARISON:")
diff = net - y_usd
print(f"   Payslip NET:     ${net:>11.2f}")
print(f"   Spreadsheet Y:   ${y_usd:>11.2f}")
print(f"   ──────────────────────────────")
print(f"   Difference:      ${diff:>11.2f}")

if abs(diff) < 1.0:
    print(f"\n✓ MATCH: Payslip matches spreadsheet Column Y!")
elif abs(diff) < 20.0:
    print(f"\n⚠️  SMALL DISCREPANCY: ${abs(diff):.2f}")
    print(f"\n   Possible reasons:")
    print(f"   1. Rounding differences")
    print(f"   2. Slightly different deduction rates")
    print(f"   3. Exchange rate fluctuation")
else:
    print(f"\n❌ LARGE DISCREPANCY: ${abs(diff):.2f}")
    print(f"\n   Possible reasons:")
    print(f"   1. Payslip calculated BEFORE contract update")
    print(f"   2. Different salary values used")
    print(f"   3. Old contract had wage=${contract[0]:.2f} but should be ${gross_usd:.2f}")

    print(f"\n📋 CURRENT CONTRACT VALUES:")
    print(f"   wage (K+L+M):            ${contract[0]:>11.2f}")
    print(f"   ueipab_salary_base (K):  ${contract[1]:>11.2f}")
    print(f"   ueipab_bonus_regular (M):${contract[2]:>11.2f}")
    print(f"   ueipab_extra_bonus (L):  ${contract[3]:>11.2f}")

    print(f"\n   ⚠️  This payslip was computed BEFORE we updated the contracts!")
    print(f"   ⚠️  You need to RECOMPUTE the payslip with the new contract values.")

print("\n" + "=" * 80)
