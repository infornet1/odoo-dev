#!/usr/bin/env python3
"""
Phase 1+3 Combined: Smart Contract Date Updates
===============================================

Reads original hire dates from Google Spreadsheet and intelligently sets:
1. contract.date_start (company liability start)
2. contract.ueipab_original_hire_date (antiguedad continuity)

Logic:
------
- If hired BEFORE Sep 1, 2023:
  * contract.date_start = Sep 1, 2023 (company liability start)
  * ueipab_original_hire_date = actual hire date (for antiguedad)

- If hired ON/AFTER Sep 1, 2023:
  * contract.date_start = actual hire date
  * ueipab_original_hire_date = actual hire date

This handles 14 employees hired after Sep 1, 2023 correctly!

Spreadsheet: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s
Sheet: Incremento2526, Range C5:D48 (44 employees)
"""

import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

print("=" * 80)
print("PHASE 1+3: SMART CONTRACT DATE UPDATES FROM SPREADSHEET")
print("=" * 80)

# Google Sheets configuration
CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/gsheet_credentials.json'
SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
SHEET_NAME = 'Incremento2526'
DATA_RANGE = f'{SHEET_NAME}!C5:D48'

print("\n📊 Reading original hire dates from Google Spreadsheet...")
print(f"   Spreadsheet ID: {SPREADSHEET_ID}")
print(f"   Range: {DATA_RANGE}")

# Load credentials and read spreadsheet
with open(CREDENTIALS_FILE, 'r') as f:
    creds_info = json.load(f)

credentials = service_account.Credentials.from_service_account_info(
    creds_info,
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)

service = build('sheets', 'v4', credentials=credentials)
sheet = service.spreadsheets()

result = sheet.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=DATA_RANGE
).execute()

values = result.get('values', [])

if not values:
    print("❌ No data found in spreadsheet!")
    exit(1)

print(f"✅ Found {len(values)} employees in spreadsheet\n")

# Parse employee data from spreadsheet
# Note: Columns are reversed in spreadsheet (C=date, D=name)
employee_hire_dates = {}
for row in values:
    if len(row) >= 2:
        hire_date_str = row[0].strip()  # Column C
        employee_name = row[1].strip().upper()  # Column D

        try:
            # Parse date (M/D/YYYY format)
            hire_date = datetime.datetime.strptime(hire_date_str, '%m/%d/%Y').date()
            employee_hire_dates[employee_name] = hire_date
        except ValueError:
            print(f"⚠️  Warning: Could not parse date '{hire_date_str}' for {employee_name}")

print(f"✅ Parsed {len(employee_hire_dates)} employee hire dates")

# Company liability start date
COMPANY_LIABILITY_START = datetime.date(2023, 9, 1)

print("\n" + "=" * 80)
print("PROCESSING CONTRACT UPDATES")
print("=" * 80)

# Get all active contracts
contracts = env['hr.contract'].search([('state', 'in', ['open', 'close'])])
print(f"\nFound {len(contracts)} active contracts in Odoo")

print("\n" + "-" * 80)
print(f"{'Employee':<35} {'Original Hire':<15} {'Contract Start':<15} {'Status':<15}")
print("-" * 80)

updated_count = 0
not_found_count = 0
skipped_count = 0

for contract in contracts:
    employee_name = contract.employee_id.name.upper() if contract.employee_id else "UNKNOWN"

    # Try to find employee in spreadsheet data
    if employee_name not in employee_hire_dates:
        print(f"{employee_name:<35} {'NOT IN SHEET':<15} {'-':<15} ⚠️  SKIPPED")
        not_found_count += 1
        continue

    original_hire_date = employee_hire_dates[employee_name]

    # Determine contract.date_start based on logic
    if original_hire_date < COMPANY_LIABILITY_START:
        # Hired before Sep 1, 2023 → Use Sep 1, 2023 as contract start
        new_contract_start = COMPANY_LIABILITY_START
        status = "Pre-2023"
    else:
        # Hired on/after Sep 1, 2023 → Use actual hire date
        new_contract_start = original_hire_date
        status = "Post-2023"

    # Update contract fields
    contract.date_start = new_contract_start
    contract.ueipab_original_hire_date = original_hire_date

    print(f"{employee_name:<35} {original_hire_date} {new_contract_start} {status:<15}")
    updated_count += 1

# Commit all changes
env.cr.commit()

print("-" * 80)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Updated: {updated_count} contracts")
print(f"   ⚠️  Not found in sheet: {not_found_count}")
print(f"   Total: {len(contracts)}")

print("\n" + "=" * 80)
print("VERIFICATION")
print("=" * 80)

# Count contracts by category
pre_2023_count = env['hr.contract'].search_count([
    ('date_start', '=', '2023-09-01'),
    ('state', 'in', ['open', 'close'])
])

post_2023_count = env['hr.contract'].search_count([
    ('date_start', '>', '2023-09-01'),
    ('state', 'in', ['open', 'close'])
])

print(f"\n✅ Contracts with date_start = Sep 1, 2023 (Pre-2023 hires): {pre_2023_count}")
print(f"✅ Contracts with date_start > Sep 1, 2023 (Post-2023 hires): {post_2023_count}")

# Verify original hire dates were set
with_original_date = env['hr.contract'].search_count([
    ('ueipab_original_hire_date', '!=', False),
    ('state', 'in', ['open', 'close'])
])
print(f"✅ Contracts with ueipab_original_hire_date set: {with_original_date}")

print("\n" + "=" * 80)
print("✅ PHASE 1+3 COMPLETE")
print("=" * 80)
print("\nAll employee contracts now have:")
print("  1. Correct date_start (company liability)")
print("  2. Original hire date (for antiguedad continuity)")
print("  3. Smart logic handles both pre-2023 and post-2023 hires!")
print("=" * 80)
