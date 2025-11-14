#!/usr/bin/env python3
"""
Verify NOVIEMBRE15-2 VE_NET against Google Spreadsheet
Run via Odoo shell to access env
"""

import subprocess
import json

print("=" * 100)
print("🔍 VERIFICATION: NOVIEMBRE15-2 VE_NET vs Google Spreadsheet")
print("=" * 100)

# First, fetch Odoo data
print(f"\n📊 Fetching NOVIEMBRE15-2 payslips from Odoo...")

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15-2 batch not found")
    exit()

payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])
print(f"   Payslips found: {len(payslips)}")

# Extract Odoo data
odoo_data = {}
for payslip in payslips:
    employee_name = payslip.employee_id.name
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0
    odoo_data[employee_name] = odoo_net

# Save to temp file for the external script
with open('/tmp/odoo_payslip_data.json', 'w') as f:
    json.dump(odoo_data, f, indent=2)

print(f"   ✅ Saved Odoo data to /tmp/odoo_payslip_data.json")

# Now call external Python script to fetch Google Sheets data
print(f"\n📊 Fetching Google Spreadsheet data...")

external_script = '''
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    '/var/www/dev/odoo_api_bridge/gsheet_credentials.json', 
    scope
)
gc = gspread.authorize(credentials)

spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
sheet = gc.open_by_key(spreadsheet_id)
worksheet = sheet.get_worksheet(0)

# Get employee names from column D (D5:D48)
employee_names = worksheet.col_values(4)[4:48]

# Get VE_NET from column Y (Y5:Y48) 
ve_net_values = worksheet.col_values(25)[4:48]

spreadsheet_data = {}
for i, name in enumerate(employee_names):
    if name and i < len(ve_net_values):
        net_str = ve_net_values[i] if i < len(ve_net_values) else ''
        try:
            net_clean = net_str.replace('$', '').replace(',', '').replace(' ', '').strip()
            net_value = float(net_clean) if net_clean else 0.0
            spreadsheet_data[name.strip()] = net_value
        except:
            pass

with open('/tmp/sheet_data.json', 'w') as f:
    json.dump(spreadsheet_data, f, indent=2)

print("OK")
'''

try:
    result = subprocess.run(
        ['python3', '-c', external_script],
        capture_output=True,
        text=True,
        timeout=30
    )
    
    if result.returncode == 0:
        print(f"   ✅ Fetched spreadsheet data")
    else:
        print(f"   ❌ Error: {result.stderr}")
        exit()
except Exception as e:
    print(f"   ❌ Error running external script: {e}")
    exit()

# Load sheet data
with open('/tmp/sheet_data.json', 'r') as f:
    sheet_data = json.load(f)

print(f"   Spreadsheet entries: {len(sheet_data)}")

# Compare
print(f"\n{'Employee':<30} | {'Odoo VE_NET':>15} | {'Sheet VE_NET':>15} | {'Diff':>12} | Status")
print("=" * 100)

matches = 0
mismatches = 0
not_found = 0

for employee_name in sorted(odoo_data.keys()):
    odoo_net = odoo_data[employee_name]
    
    # Try exact match first
    sheet_net = sheet_data.get(employee_name)
    
    # Try uppercase match
    if sheet_net is None:
        sheet_net = sheet_data.get(employee_name.upper())
    
    if sheet_net is None:
        status = "❓ NOT IN SHEET"
        not_found += 1
        diff = 0.0
    else:
        diff = abs(odoo_net - sheet_net)
        if diff < 0.01:
            status = "✅ MATCH"
            matches += 1
        else:
            status = "❌ MISMATCH"
            mismatches += 1
    
    sheet_display = f"${sheet_net:,.2f}" if sheet_net is not None else "N/A"
    diff_display = f"${diff:,.2f}" if sheet_net is not None else "N/A"
    
    print(f"{employee_name[:29]:<30} | ${odoo_net:>14,.2f} | {sheet_display:>15} | {diff_display:>12} | {status}")

print("=" * 100)
print(f"\n📊 SUMMARY:")
print(f"   ✅ Matches:              {matches}")
print(f"   ❌ Mismatches:           {mismatches}")
print(f"   ❓ Not in spreadsheet:   {not_found}")

if mismatches == 0 and not_found == 0:
    print(f"\n🎉 ALL {matches} PAYSLIPS MATCH SPREADSHEET!")
elif mismatches > 0:
    print(f"\n⚠️  {mismatches} mismatches found")

