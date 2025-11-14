#!/usr/bin/env python3
"""
Verify NOVIEMBRE15-2 VE_NET against Google Spreadsheet
Uses service account credentials from /tmp/gsheet_credentials.json
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets connection
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    '/tmp/gsheet_credentials.json',
    scope
)
gc = gspread.authorize(credentials)

print("=" * 100)
print("🔍 VERIFICATION: NOVIEMBRE15-2 VE_NET vs Google Spreadsheet")
print("=" * 100)

# Get Odoo data
print(f"\n📊 Fetching NOVIEMBRE15-2 payslips from Odoo...")

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15-2 batch not found in Odoo")
    exit()

payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])
print(f"   Payslips found: {len(payslips)}")

# Extract Odoo data
odoo_data = {}
for payslip in payslips:
    employee_name = payslip.employee_id.name.strip()
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0
    odoo_data[employee_name] = odoo_net

# Open the spreadsheet
print(f"\n📊 Connecting to Google Spreadsheet...")
try:
    spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
    sheet = gc.open_by_key(spreadsheet_id)

    print(f"   ✅ Connected to Google Spreadsheet")
    print(f"   Title: {sheet.title}")

    # Try to find the "15nov2025" worksheet
    worksheet = None
    for ws in sheet.worksheets():
        if '15nov2025' in ws.title.lower():
            worksheet = ws
            break

    # If not found by name, try first worksheet
    if not worksheet:
        worksheet = sheet.get_worksheet(0)

    print(f"   Worksheet: {worksheet.title}")

    # Get the data range D5:Y48
    print(f"\n📊 Fetching data from range D5:Y48...")

    # Get employee names from column D (D5:D48)
    employee_names = worksheet.col_values(4)[4:48]  # Column D is index 4, starting from row 5

    # Get VE_NET values from column Y (Y5:Y48)
    ve_net_values = worksheet.col_values(25)[4:48]  # Column Y is index 25, starting from row 5

    print(f"   Rows found: {len(employee_names)}")

    # Create a lookup dictionary
    spreadsheet_data = {}
    for i, name in enumerate(employee_names):
        if name and i < len(ve_net_values):
            # Clean the name
            name_clean = name.strip()

            # Parse VE_NET value (handle currency formatting)
            net_value_str = ve_net_values[i] if i < len(ve_net_values) else ''
            try:
                # Remove currency symbols, commas, spaces
                net_value_clean = net_value_str.replace('$', '').replace(',', '').replace(' ', '').strip()
                net_value = float(net_value_clean) if net_value_clean else 0.0
                spreadsheet_data[name_clean] = net_value
            except ValueError:
                print(f"   ⚠️  Could not parse VE_NET for {name}: '{net_value_str}'")
                spreadsheet_data[name_clean] = None

    print(f"   Valid entries: {len([v for v in spreadsheet_data.values() if v is not None])}")

except Exception as e:
    print(f"❌ Error connecting to Google Spreadsheet: {e}")
    import traceback
    traceback.print_exc()
    exit()

# Compare
print(f"\n{'Employee':<30} | {'Odoo VE_NET':>15} | {'Sheet VE_NET':>15} | {'Diff':>12} | Status")
print("=" * 100)

matches = 0
mismatches = 0
not_found_in_sheet = 0

for payslip in payslips.sorted(lambda p: p.employee_id.name):
    employee_name = payslip.employee_id.name

    # Get VE_NET from payslip
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0

    # Try to find in spreadsheet (exact match first)
    sheet_net = spreadsheet_data.get(employee_name.strip())

    # Try uppercase if not found
    if sheet_net is None:
        sheet_net = spreadsheet_data.get(employee_name.upper())

    # Try lowercase if not found
    if sheet_net is None:
        sheet_net = spreadsheet_data.get(employee_name.lower())

    # Try title case if not found
    if sheet_net is None:
        sheet_net = spreadsheet_data.get(employee_name.title())

    if sheet_net is None:
        status = "❓ NOT IN SHEET"
        not_found_in_sheet += 1
        diff = 0.0
    else:
        diff = abs(odoo_net - sheet_net)

        if diff < 0.50:  # Allow 50 cents difference for rounding
            status = "✅ MATCH"
            matches += 1
        else:
            status = "❌ MISMATCH"
            mismatches += 1

    sheet_net_display = f"${sheet_net:,.2f}" if sheet_net is not None else "N/A"
    diff_display = f"${diff:,.2f}" if sheet_net is not None else "N/A"

    print(f"{employee_name[:29]:<30} | ${odoo_net:>14,.2f} | {sheet_net_display:>15} | {diff_display:>12} | {status}")

print("=" * 100)

print(f"\n📊 SUMMARY:")
print(f"   ✅ Matches:              {matches}")
print(f"   ❌ Mismatches:           {mismatches}")
print(f"   ❓ Not in spreadsheet:   {not_found_in_sheet}")
print(f"   📊 Total payslips:       {len(payslips)}")

if mismatches == 0 and not_found_in_sheet == 0:
    print(f"\n🎉 ALL {matches} PAYSLIPS MATCH SPREADSHEET PERFECTLY!")
    print(f"   VE_NET values in Odoo NOVIEMBRE15-2 are correct!")
    print(f"   ✅ Safe to proceed with Salary/Bonus formula update")
elif mismatches > 0:
    print(f"\n⚠️  {mismatches} payslips have different VE_NET values than spreadsheet")
    print(f"   This may indicate calculation differences - review before proceeding")
else:
    print(f"\n⚠️  {not_found_in_sheet} employees not found in spreadsheet")
    print(f"   Verify employee names match between Odoo and spreadsheet")

print("\n" + "=" * 100)
