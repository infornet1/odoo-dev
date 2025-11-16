#!/usr/bin/env python3
"""
Phase 4: Migrate Contracts to V2 Compensation Breakdown
Imports V2 field values from Google Spreadsheet columns K, L, M

CRITICAL V2 MAPPING FORMULA:
  Column K → ueipab_salary_v2 (direct, subject to deductions)
  Column L → ueipab_extrabonus_v2 (direct, NOT subject to deductions)
  Column M - $40 → ueipab_bonus_v2 (Cesta Ticket deducted ONLY from M)
  $40.00 → cesta_ticket_usd (fixed, reuse existing field)

Data Source: Spreadsheet 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s
Tab: 15nov2025 (NOMINA AL 15 NOVIEMBRE 2025)
Exchange Rate: 234.8715 VEB/USD
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'
VEB_USD_RATE = 234.8715
CESTA_TICKET_USD = 40.00

print("=" * 80)
print("PHASE 4: V2 CONTRACT MIGRATION")
print("=" * 80)
print("\n📋 CRITICAL V2 MAPPING FORMULA:")
print("  Column K → ueipab_salary_v2 (direct, subject to deductions)")
print("  Column L → ueipab_extrabonus_v2 (direct, NOT subject to deductions)")
print("  Column M - $40 → ueipab_bonus_v2 (Cesta Ticket deducted ONLY from M)")
print("  $40.00 → cesta_ticket_usd (fixed, reuse existing field)")
print("=" * 80)
print(f"\n📊 Data Source:")
print(f"  Spreadsheet ID: {SPREADSHEET_ID}")
print(f"  Tab: {TAB_NAME}")
print(f"  Exchange Rate: {VEB_USD_RATE} VEB/USD")
print(f"  Cesta Ticket: ${CESTA_TICKET_USD} USD (fixed)")
print("=" * 80)

# Connect to spreadsheet
try:
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

    print(f"\n✅ Connected to: {sheet.title}")
    print(f"✅ Reading from tab: {TAB_NAME}")
    print("=" * 80)
except FileNotFoundError:
    print(f"\n❌ ERROR: Credentials file not found: {CREDENTIALS_FILE}")
    print("\n⚠️  Please ensure Google Sheets API credentials are available")
    print("   You can export credentials from Google Cloud Console")
    print("   and save to /tmp/gsheet_credentials.json")
    print("\nExiting...")
    exit(1)
except Exception as e:
    print(f"\n❌ ERROR connecting to spreadsheet: {e}")
    print("\nExiting...")
    exit(1)

# Read columns D (Name), E (VAT), K, L, M from rows 5-48 (44 employees)
# Column indices in get(): D=0, E=1, ..., K=7, L=8, M=9
try:
    data = worksheet.get('D5:M48')
    print(f"\n✅ Found {len(data)} employee records in spreadsheet")
except Exception as e:
    print(f"\n❌ ERROR reading spreadsheet data: {e}")
    print("\nExiting...")
    exit(1)

print("\n" + "=" * 80)
print("PROCESSING MIGRATION...")
print("=" * 80)

success_count = 0
error_count = 0
warning_count = 0
skipped_count = 0

for idx, row in enumerate(data, start=5):
    if not row or len(row) < 3:
        print(f"⚠️  Row {idx}: Insufficient data, skipping")
        skipped_count += 1
        continue

    emp_name = row[0].strip()
    emp_vat = row[1].strip() if len(row) > 1 else ''

    # Get VEB values from columns K, L, M (indices 7, 8, 9)
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

        # ✅ V2 MAPPING (CORRECT FORMULA!)
        salary_v2 = k_usd                          # Column K → Salary V2
        extrabonus_v2 = l_usd                      # Column L → ExtraBonus V2
        bonus_v2 = m_usd - CESTA_TICKET_USD        # Column M - $40 → Bonus V2
        cesta_ticket = CESTA_TICKET_USD            # Fixed $40

        # Find employee contract by name (case-insensitive)
        employee = env['hr.employee'].search([('name', 'ilike', emp_name)], limit=1)
        if not employee:
            print(f"✗ Row {idx} - {emp_name}: Employee not found in Odoo")
            error_count += 1
            continue

        contract = env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open')
        ], limit=1)

        if not contract:
            print(f"✗ Row {idx} - {emp_name}: No active contract found")
            error_count += 1
            continue

        # Store current wage for validation
        current_wage = contract.wage

        # ✅ IMPORT ACTUAL VALUES - NO PERCENTAGE CALCULATION!
        contract.write({
            'ueipab_salary_v2': round(salary_v2, 2),
            'ueipab_extrabonus_v2': round(extrabonus_v2, 2),
            'ueipab_bonus_v2': round(bonus_v2, 2),
            # cesta_ticket_usd NOT modified (field already exists)
        })

        # Verify total matches wage
        total_wage = salary_v2 + extrabonus_v2 + bonus_v2 + cesta_ticket
        wage_diff = abs(total_wage - current_wage)

        if wage_diff > 0.10:  # Allow $0.10 tolerance for rounding
            print(f"⚠️  Row {idx} - {emp_name}: Wage mismatch - Total ${total_wage:.2f} != Current ${current_wage:.2f} (diff: ${wage_diff:.2f})")
            print(f"    Salary: ${salary_v2:.2f}, ExtraBonus: ${extrabonus_v2:.2f}, Bonus: ${bonus_v2:.2f}, Cesta: ${cesta_ticket:.2f}")
            warning_count += 1
        else:
            print(f"✓ Row {idx} - {emp_name}: Salary=${salary_v2:.2f}, ExtraBonus=${extrabonus_v2:.2f}, Bonus=${bonus_v2:.2f}, Cesta=${cesta_ticket:.2f}")
            success_count += 1

    except ValueError as e:
        print(f"✗ Row {idx} - {emp_name}: Error parsing VEB values - {e}")
        error_count += 1
    except Exception as e:
        print(f"✗ Row {idx} - {emp_name}: Migration error - {e}")
        error_count += 1

# Commit changes
env.cr.commit()

print("\n" + "=" * 80)
print("MIGRATION SUMMARY")
print("=" * 80)
print(f"✅ Success:  {success_count} contracts migrated successfully")
print(f"⚠️  Warnings: {warning_count} contracts with wage mismatch")
print(f"✗ Errors:   {error_count} contracts failed to migrate")
print(f"⏭️  Skipped:  {skipped_count} rows skipped (insufficient data)")
print(f"📊 Total:    {success_count + warning_count + error_count + skipped_count} rows processed")
print("=" * 80)

if error_count > 0:
    print("\n⚠️  ERRORS DETECTED: Some contracts failed to migrate")
    print("   Review errors above and retry failed contracts manually")
elif warning_count > 0:
    print("\n⚠️  WARNINGS DETECTED: Some contracts have wage mismatches")
    print("   Review warnings above to ensure calculations are correct")
else:
    print("\n✅ MIGRATION COMPLETE: All contracts migrated successfully!")

print("\n" + "=" * 80)
print("VERIFICATION QUERIES")
print("=" * 80)
print("\nTo verify migration results, run these queries in Odoo shell:")
print("\n# Count contracts with V2 fields populated")
print("env['hr.contract'].search_count([('ueipab_salary_v2', '>', 0)])")
print("\n# List all V2 salaries")
print("for c in env['hr.contract'].search([('state', '=', 'open')]):")
print("    print(f'{c.employee_id.name}: Salary=${c.ueipab_salary_v2:.2f}, Bonus=${c.ueipab_bonus_v2:.2f}, ExtraBonus=${c.ueipab_extrabonus_v2:.2f}')")
print("\n" + "=" * 80)
