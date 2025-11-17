#!/usr/bin/env python3
"""
Check ACTUAL "OTROS BONOS" (Column L) values from spreadsheet
to see which employees have ExtraBonus
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'
VEB_USD_RATE = 234.8715

print("=" * 80)
print("CHECKING ACTUAL OTROS BONOS (COLUMN L) FROM SPREADSHEET")
print("=" * 80)

# Connect to spreadsheet
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE, scope
)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = sheet.worksheet(TAB_NAME)

print(f"Spreadsheet: {sheet.title}")
print(f"Tab: {TAB_NAME}")
print(f"Exchange Rate: {VEB_USD_RATE} VEB/USD")
print("=" * 80)

# Read columns D (Name), K (Salary+Bonus), L (Other Bonuses), M (Cesta Ticket)
# Rows 5-48 (44 employees)
data = worksheet.get('D5:M48')

print(f"\n{'Employee Name':<30} {'Col K (VEB)':<15} {'Col L (VEB)':<15} {'Col M (VEB)':<15} {'ExtraBonus USD':<15}")
print("-" * 80)

employees_with_extrabonus = []
employees_without_extrabonus = []

for row in data:
    if not row or len(row) < 3:
        continue

    name = row[0].strip()

    # Column K (index 7): SALARIO MENSUAL MAS BONO
    col_k = row[7].replace(',', '').strip() if len(row) > 7 and row[7] else '0'

    # Column L (index 8): OTROS BONOS
    col_l = row[8].replace(',', '').strip() if len(row) > 8 and row[8] else '0'

    # Column M (index 9): CESTA TICKET
    col_m = row[9].replace(',', '').strip() if len(row) > 9 and row[9] else '0'

    try:
        k_veb = float(col_k)
        l_veb = float(col_l)
        m_veb = float(col_m)

        # Convert to USD
        extrabonus_usd = l_veb / VEB_USD_RATE

        if extrabonus_usd > 0.01:  # Has extra bonus
            employees_with_extrabonus.append({
                'name': name,
                'k_veb': k_veb,
                'l_veb': l_veb,
                'm_veb': m_veb,
                'extrabonus_usd': extrabonus_usd
            })
            print(f"{name:<30} {k_veb:>13.2f}  {l_veb:>13.2f}  {m_veb:>13.2f}  ${extrabonus_usd:>13.2f} ✓")
        else:
            employees_without_extrabonus.append({
                'name': name,
                'k_veb': k_veb,
                'l_veb': l_veb,
                'm_veb': m_veb,
                'extrabonus_usd': extrabonus_usd
            })

    except ValueError:
        print(f"{name:<30} ERROR parsing values")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nEmployees WITH ExtraBonus (Column L > 0): {len(employees_with_extrabonus)}")
for emp in employees_with_extrabonus:
    print(f"  - {emp['name']:<30} ExtraBonus: ${emp['extrabonus_usd']:.2f} USD ({emp['l_veb']:.2f} VEB)")

print(f"\nEmployees WITHOUT ExtraBonus (Column L = 0): {len(employees_without_extrabonus)}")

print("\n" + "=" * 80)
print("DETAILED BREAKDOWN - Employees WITH ExtraBonus")
print("=" * 80)

for emp in employees_with_extrabonus:
    print(f"\n{emp['name']}:")
    print(f"  Column K (Salary+Bonus):  {emp['k_veb']:>10.2f} VEB = ${emp['k_veb']/VEB_USD_RATE:>8.2f} USD")
    print(f"  Column L (Other Bonuses): {emp['l_veb']:>10.2f} VEB = ${emp['l_veb']/VEB_USD_RATE:>8.2f} USD ← ExtraBonus V2")
    print(f"  Column M (Cesta Ticket):  {emp['m_veb']:>10.2f} VEB = ${emp['m_veb']/VEB_USD_RATE:>8.2f} USD")
    print(f"  Total Wage:               {emp['k_veb']+emp['l_veb']+emp['m_veb']:>10.2f} VEB = ${(emp['k_veb']+emp['l_veb']+emp['m_veb'])/VEB_USD_RATE:>8.2f} USD")
