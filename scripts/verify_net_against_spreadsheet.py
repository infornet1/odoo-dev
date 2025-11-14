#!/usr/bin/env python3
"""
Verify NOVIEMBRE15-2 payslip VE_NET values against Google Spreadsheet
Spreadsheet: 19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s
Range: D5:Y48 (Employee names in D, VE_NET in Y)
NO DATABASE MODIFICATIONS - pure verification
"""

import sys
sys.path.append('/var/www/dev/odoo_api_bridge')

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Setup Google Sheets connection
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    '/var/www/dev/odoo_api_bridge/gsheet_credentials.json', 
    scope
)
gc = gspread.authorize(credentials)

print("=" * 100)
print("🔍 VERIFICATION: NOVIEMBRE15-2 VE_NET vs Google Spreadsheet")
print("=" * 100)

# Open the spreadsheet
try:
    spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
    sheet = gc.open_by_key(spreadsheet_id)
    
    # Get the first worksheet (or specify by name if needed)
    worksheet = sheet.get_worksheet(0)
    
    print(f"\n✅ Connected to Google Spreadsheet")
    print(f"   Title: {sheet.title}")
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
            name_clean = name.strip().upper()
            
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

# Now get Odoo payslip data
print(f"\n📊 Fetching NOVIEMBRE15-2 payslips from Odoo...")

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

if not batch:
    print("❌ NOVIEMBRE15-2 batch not found in Odoo")
    exit()

payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])
print(f"   Payslips found: {len(payslips)}")

# Compare
print(f"\n{'Employee':<30} | {'Odoo VE_NET':>15} | {'Sheet VE_NET':>15} | {'Diff':>12} | Status")
print("=" * 100)

matches = 0
mismatches = 0
not_found_in_sheet = 0

for payslip in payslips.sorted(lambda p: p.employee_id.name):
    employee_name = payslip.employee_id.name
    employee_name_clean = employee_name.upper()
    
    # Get VE_NET from payslip
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0
    
    # Find in spreadsheet
    sheet_net = spreadsheet_data.get(employee_name_clean)
    
    if sheet_net is None:
        status = "❓ NOT IN SHEET"
        not_found_in_sheet += 1
        diff = 0.0
    else:
        diff = abs(odoo_net - sheet_net)
        
        if diff < 0.01:  # Allow 1 cent difference
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
    print(f"\n🎉 ALL PAYSLIPS MATCH SPREADSHEET PERFECTLY!")
elif mismatches > 0:
    print(f"\n⚠️  {mismatches} payslips have different VE_NET values than spreadsheet")
    print(f"   This may indicate calculation differences")
else:
    print(f"\n⚠️  {not_found_in_sheet} employees not found in spreadsheet")

print("\n" + "=" * 100)

