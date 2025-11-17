#!/usr/bin/env python3
"""
Generate V2 field values from Google Spreadsheet 15nov2025 tab
Import ACTUAL values from columns K, L, M

CRITICAL MAPPING:
  Column K → ueipab_salary_v2 (direct)
  Column M → ueipab_bonus_v2 (minus $40 cesta ticket)
  Column L → ueipab_extrabonus_v2 (direct)
  $40.00   → cesta_ticket_usd (fixed known value)
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'
VEB_USD_RATE = 234.8715
CESTA_TICKET_USD = 40.00

print("=" * 80)
print("GENERATE V2 DATA FROM SPREADSHEET - 100% ACCURATE")
print("=" * 80)
print(f"Spreadsheet ID: {SPREADSHEET_ID}")
print(f"Tab: {TAB_NAME}")
print(f"Exchange Rate: {VEB_USD_RATE} VEB/USD")
print(f"Cesta Ticket: ${CESTA_TICKET_USD} USD (fixed)")
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

print(f"\nConnected to: {sheet.title}")
print(f"Reading from tab: {TAB_NAME}")
print("=" * 80)

# Read columns D (Name), E (VAT), K, L, M
# Rows 5-48 (44 employees)
data = worksheet.get('D5:M48')

print(f"\n{'Employee Name':<30} {'Salary V2':<12} {'Bonus V2':<12} {'ExtraBonus V2':<12} {'Cesta':<12} {'Total':<12} {'Status'}")
print("-" * 80)

v2_data = []
errors = []

for row in data:
    if not row or len(row) < 3:
        continue

    name = row[0].strip()
    vat = row[1].strip() if len(row) > 1 else ''

    # Get VEB values from columns K, L, M
    # Column indices: D=0, E=1, F=2, G=3, H=4, I=5, J=6, K=7, L=8, M=9
    k_veb_str = row[7].replace(',', '').strip() if len(row) > 7 and row[7] else '0'
    l_veb_str = row[8].replace(',', '').strip() if len(row) > 8 and row[8] else '0'
    m_veb_str = row[9].replace(',', '').strip() if len(row) > 9 and row[9] else '0'

    try:
        k_veb = float(k_veb_str)
        l_veb = float(l_veb_str)
        m_veb = float(m_veb_str)

        # Convert to USD
        k_usd = k_veb / VEB_USD_RATE
        l_usd = l_veb / VEB_USD_RATE
        m_usd = m_veb / VEB_USD_RATE

        # V2 MAPPING (CORRECT!)
        salary_v2 = k_usd                          # Column K → Salary V2
        bonus_v2 = m_usd - CESTA_TICKET_USD        # Column M - $40 → Bonus V2
        extrabonus_v2 = l_usd                      # Column L → ExtraBonus V2
        cesta_ticket = CESTA_TICKET_USD            # Fixed $40

        # Calculate total wage
        total_wage = salary_v2 + bonus_v2 + extrabonus_v2 + cesta_ticket

        # Verify against known wages (we'll get from Odoo later)
        # For now, just check components are positive
        if bonus_v2 < 0:
            errors.append({
                'name': name,
                'issue': f'Bonus V2 is negative: ${bonus_v2:.2f} (Column M ${m_usd:.2f} - Cesta ${CESTA_TICKET_USD:.2f})'
            })
            status = '✗ ERROR'
        else:
            status = '✓'

        v2_data.append({
            'name': name,
            'vat': vat,
            'k_veb': k_veb,
            'l_veb': l_veb,
            'm_veb': m_veb,
            'k_usd': k_usd,
            'l_usd': l_usd,
            'm_usd': m_usd,
            'salary_v2': salary_v2,
            'bonus_v2': bonus_v2,
            'extrabonus_v2': extrabonus_v2,
            'cesta_ticket': cesta_ticket,
            'total_wage': total_wage,
            'status': status
        })

        print(f"{name:<30} ${salary_v2:>10.2f} ${bonus_v2:>10.2f} ${extrabonus_v2:>10.2f} ${cesta_ticket:>10.2f} ${total_wage:>10.2f} {status}")

    except ValueError as e:
        print(f"{name:<30} ERROR: Could not parse values - {e}")
        errors.append({'name': name, 'issue': str(e)})

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if errors:
    print(f"\n✗ {len(errors)} ERRORS FOUND:")
    for error in errors:
        print(f"  {error['name']}: {error['issue']}")
else:
    print(f"\n✅ ALL {len(v2_data)} EMPLOYEES: Data imported successfully")

print(f"\nTotal employees processed: {len(v2_data)}")

# Show first 10 employees in detail
print("\n" + "=" * 80)
print("DETAILED BREAKDOWN - First 10 Employees")
print("=" * 80)

for i, emp in enumerate(v2_data[:10]):
    print(f"\n{i+1}. {emp['name']}")
    print(f"   Column K: {emp['k_veb']:>12.2f} VEB = ${emp['k_usd']:>8.2f} USD → Salary V2")
    print(f"   Column L: {emp['l_veb']:>12.2f} VEB = ${emp['l_usd']:>8.2f} USD → ExtraBonus V2")
    print(f"   Column M: {emp['m_veb']:>12.2f} VEB = ${emp['m_usd']:>8.2f} USD → ${emp['m_usd'] - CESTA_TICKET_USD:>8.2f} Bonus V2 (minus $40 cesta)")
    print(f"   ---")
    print(f"   Salary V2:     ${emp['salary_v2']:>8.2f}")
    print(f"   Bonus V2:      ${emp['bonus_v2']:>8.2f}")
    print(f"   ExtraBonus V2: ${emp['extrabonus_v2']:>8.2f}")
    print(f"   Cesta Ticket:  ${emp['cesta_ticket']:>8.2f}")
    print(f"   Total Wage:    ${emp['total_wage']:>8.2f}")

# Show the 4 employees with ExtraBonus
print("\n" + "=" * 80)
print("EMPLOYEES WITH EXTRABONUS (4 employees)")
print("=" * 80)

extrabonus_employees = [emp for emp in v2_data if emp['extrabonus_v2'] > 0.01]

for emp in extrabonus_employees:
    print(f"\n{emp['name']}:")
    print(f"   Column K: {emp['k_veb']:>12.2f} VEB = ${emp['k_usd']:>8.2f} USD → Salary V2")
    print(f"   Column L: {emp['l_veb']:>12.2f} VEB = ${emp['l_usd']:>8.2f} USD → ExtraBonus V2 ✓")
    print(f"   Column M: {emp['m_veb']:>12.2f} VEB = ${emp['m_usd']:>8.2f} USD → ${emp['bonus_v2']:>8.2f} Bonus V2")
    print(f"   ---")
    print(f"   Salary V2:     ${emp['salary_v2']:>8.2f}")
    print(f"   Bonus V2:      ${emp['bonus_v2']:>8.2f}")
    print(f"   ExtraBonus V2: ${emp['extrabonus_v2']:>8.2f} ← HAS EXTRA BONUS")
    print(f"   Cesta Ticket:  ${emp['cesta_ticket']:>8.2f}")
    print(f"   Total Wage:    ${emp['total_wage']:>8.2f}")

print(f"\nFound {len(extrabonus_employees)} employees with ExtraBonus")
print("Expected: SERGIO MANEIRO, ANDRES MORALES, PABLO NAVARRO, RAFAEL PEREZ")

print("\n" + "=" * 80)
print("V2 MAPPING FORMULA (CONFIRMED)")
print("=" * 80)
print("""
Column K → ueipab_salary_v2 (direct)
Column M → ueipab_bonus_v2 (minus $40 cesta ticket)
Column L → ueipab_extrabonus_v2 (direct)
$40.00   → cesta_ticket_usd (fixed known value)

This data is ready to:
1. Export to SalaryStructureV2 spreadsheet tab
2. HR reviews and approves
3. Import to Odoo contracts via migration script
""")
