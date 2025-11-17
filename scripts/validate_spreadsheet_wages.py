#!/usr/bin/env python3
"""
Validate that current Odoo contract wages match Google Spreadsheet "15nov2025" tab
This is a preliminary validation for Venezuelan Payroll V2 migration planning.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from odoo import api, SUPERUSER_ID

# Google Sheets configuration
SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
CREDENTIALS_FILE = '/tmp/gsheet_credentials.json'
TAB_NAME = '15nov2025'
DATA_RANGE = 'D4:D48'  # Employee wages in VEB

# Exchange rate used in spreadsheet
VEB_USD_RATE = 234.8715

print("=" * 80)
print("PRELIMINARY WAGE VALIDATION - Spreadsheet vs Odoo Contracts")
print("=" * 80)
print(f"Spreadsheet ID: {SPREADSHEET_ID}")
print(f"Tab: {TAB_NAME}")
print(f"Data Range: {DATA_RANGE}")
print(f"Exchange Rate: {VEB_USD_RATE} VEB/USD")
print("=" * 80)

# Connect to Google Sheets
print("\n[1/4] Connecting to Google Sheets...")
try:
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE, scope
    )
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(TAB_NAME)
    print(f"✓ Connected to spreadsheet: {spreadsheet.title}")
    print(f"✓ Reading worksheet: {TAB_NAME}")
except Exception as e:
    print(f"✗ ERROR connecting to Google Sheets: {e}")
    exit(1)

# Read spreadsheet data
print(f"\n[2/4] Reading spreadsheet data ({DATA_RANGE})...")
try:
    # Get employee names (column C) and wages in VEB (column D)
    names_range = 'C4:C48'
    wages_range = 'D4:D48'

    employee_names = worksheet.get(names_range)
    employee_wages_veb = worksheet.get(wages_range)

    # Convert to USD
    spreadsheet_data = {}
    for i, name_row in enumerate(employee_names):
        if name_row and name_row[0]:
            name = name_row[0].strip()
            wage_veb_str = employee_wages_veb[i][0] if i < len(employee_wages_veb) and employee_wages_veb[i] else '0'

            # Clean the wage string (remove commas, spaces)
            wage_veb_str = wage_veb_str.replace(',', '').replace(' ', '').strip()

            try:
                wage_veb = float(wage_veb_str)
                wage_usd = wage_veb / VEB_USD_RATE
                spreadsheet_data[name] = {
                    'wage_veb': wage_veb,
                    'wage_usd': wage_usd
                }
            except ValueError:
                print(f"⚠ Warning: Could not parse wage for {name}: '{wage_veb_str}'")
                continue

    print(f"✓ Read {len(spreadsheet_data)} employees from spreadsheet")

except Exception as e:
    print(f"✗ ERROR reading spreadsheet data: {e}")
    exit(1)

# Connect to Odoo and read contract data
print("\n[3/4] Reading Odoo contract data...")
try:
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        # Get all active contracts
        contracts = env['hr.contract'].search([
            ('state', '=', 'open')
        ])

        print(f"✓ Found {len(contracts)} active contracts in Odoo")

        odoo_data = {}
        for contract in contracts:
            emp_name = contract.employee_id.name
            odoo_data[emp_name] = {
                'wage': contract.wage,
                'contract_id': contract.id,
                'employee_id': contract.employee_id.id
            }

        print(f"✓ Read {len(odoo_data)} employee wages from Odoo")

except Exception as e:
    print(f"✗ ERROR reading Odoo data: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Compare data
print("\n[4/4] Comparing spreadsheet vs Odoo wages...")
print("=" * 80)

matches = []
mismatches = []
spreadsheet_only = []
odoo_only = []

# Check all spreadsheet employees
for emp_name, sheet_data in sorted(spreadsheet_data.items()):
    if emp_name in odoo_data:
        sheet_wage_usd = sheet_data['wage_usd']
        odoo_wage = odoo_data[emp_name]['wage']

        # Calculate difference
        diff = abs(sheet_wage_usd - odoo_wage)
        diff_pct = (diff / odoo_wage * 100) if odoo_wage > 0 else 0

        # Consider match if within $0.01 (1 cent)
        if diff < 0.01:
            matches.append({
                'name': emp_name,
                'sheet_usd': sheet_wage_usd,
                'odoo_usd': odoo_wage,
                'diff': diff
            })
        else:
            mismatches.append({
                'name': emp_name,
                'sheet_usd': sheet_wage_usd,
                'odoo_usd': odoo_wage,
                'diff': diff,
                'diff_pct': diff_pct
            })
    else:
        spreadsheet_only.append(emp_name)

# Check for employees only in Odoo
for emp_name in odoo_data.keys():
    if emp_name not in spreadsheet_data:
        odoo_only.append(emp_name)

# Print results
print(f"\n{'Employee Name':<30} {'Sheet (USD)':<15} {'Odoo (USD)':<15} {'Diff (USD)':<15}")
print("-" * 80)

for match in matches:
    print(f"{match['name']:<30} ${match['sheet_usd']:>12.2f}  ${match['odoo_usd']:>12.2f}  ${match['diff']:>12.4f} ✓")

for mismatch in mismatches:
    print(f"{mismatch['name']:<30} ${mismatch['sheet_usd']:>12.2f}  ${mismatch['odoo_usd']:>12.2f}  ${mismatch['diff']:>12.4f} ✗ ({mismatch['diff_pct']:.2f}%)")

# Print summary
print("\n" + "=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print(f"✓ Exact Matches:          {len(matches)}/{len(spreadsheet_data)} ({len(matches)/len(spreadsheet_data)*100:.1f}%)")
print(f"✗ Mismatches:             {len(mismatches)}/{len(spreadsheet_data)} ({len(mismatches)/len(spreadsheet_data)*100:.1f}%)")
print(f"⚠ Spreadsheet Only:       {len(spreadsheet_only)}")
print(f"⚠ Odoo Only:              {len(odoo_only)}")

if spreadsheet_only:
    print(f"\nEmployees in Spreadsheet but NOT in Odoo:")
    for name in spreadsheet_only:
        print(f"  - {name}")

if odoo_only:
    print(f"\nEmployees in Odoo but NOT in Spreadsheet:")
    for name in odoo_only:
        print(f"  - {name}")

print("\n" + "=" * 80)

# Final validation result
if len(matches) == len(spreadsheet_data) and len(mismatches) == 0:
    print("✅ VALIDATION PASSED: 100% wage match!")
    print("   → Spreadsheet is accurate source for V2 migration")
    print("   → Safe to proceed with SalaryStructureV2 spreadsheet import method")
    exit(0)
else:
    print("⚠️  VALIDATION INCOMPLETE: Not all wages match")
    print("   → Review mismatches before proceeding with V2 migration")
    print("   → May need manual reconciliation")
    exit(1)
