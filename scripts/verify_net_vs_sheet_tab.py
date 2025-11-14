#!/usr/bin/env python3
"""
Verify NOVIEMBRE15-2 VE_NET against Google Spreadsheet tab "15nov2025"
Using CSV export with specific sheet GID
"""

import subprocess

print("=" * 100)
print("🔍 VERIFICATION: NOVIEMBRE15-2 VE_NET vs Google Spreadsheet (tab: 15nov2025)")
print("=" * 100)

# Get Odoo data
print(f"\n📊 Fetching NOVIEMBRE15-2 payslips from Odoo...")

batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
payslips = env['hr.payslip'].search([('payslip_run_id', '=', batch.id)])

print(f"   Payslips found: {len(payslips)}")

odoo_data = {}
for payslip in payslips:
    employee_name = payslip.employee_id.name.strip()
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0
    odoo_data[employee_name] = odoo_net

# Get list of all sheets to find the GID for "15nov2025"
print(f"\n📊 Fetching Google Spreadsheet tab '15nov2025'...")

spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'

# Try common GID values (sheets usually have GID 0, 1, 2, etc.)
# Or we can try the tab name in the URL
for gid in [0, 1, 2, '15nov2025']:
    csv_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv&gid={gid}"
    
    print(f"   Trying GID={gid}...")
    
    result = subprocess.run(
        ['curl', '-sL', csv_url, '-o', '/tmp/payroll_sheet.csv'],
        capture_output=True,
        timeout=10
    )
    
    if result.returncode != 0:
        continue
    
    # Check if we got HTML (login page) or actual CSV
    with open('/tmp/payroll_sheet.csv', 'r') as f:
        first_line = f.readline()
        
        if '<!DOCTYPE' in first_line or '<html' in first_line:
            print(f"      Authentication required")
            continue
        else:
            print(f"      ✅ Got CSV data!")
            break
else:
    print(f"\n❌ Could not access spreadsheet")
    print(f"   The spreadsheet requires authentication or is not publicly shared")
    print(f"\n💡 To make it accessible:")
    print(f"   1. Open: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    print(f"   2. Click 'Share' → 'Anyone with the link' → 'Viewer'")
    print(f"   OR use service account credentials")
    exit()

# Parse CSV
import csv

sheet_data = {}
try:
    with open('/tmp/payroll_sheet.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        print(f"   Downloaded CSV: {len(rows)} rows")
        
        # Show first few rows to understand structure
        print(f"\n   First 3 rows preview:")
        for i in range(min(3, len(rows))):
            row = rows[i]
            # Show first 5 columns
            preview = ' | '.join(row[:5]) if len(row) > 0 else '(empty)'
            print(f"      Row {i}: {preview}")
        
        # Parse rows 5-48 (indices 4-47)
        # Column D (index 3) = employee name
        # Column Y (index 24) = VE_NET
        for row_idx in range(4, min(48, len(rows))):
            if row_idx < len(rows):
                row = rows[row_idx]
                
                if len(row) > 3:  # Has column D
                    employee_name = row[3].strip() if len(row) > 3 else ''
                    
                    if len(row) > 24:  # Has column Y
                        ve_net_str = row[24].strip()
                        try:
                            # Clean currency formatting
                            ve_net_clean = ve_net_str.replace('$', '').replace(',', '').replace(' ', '').strip()
                            ve_net = float(ve_net_clean) if ve_net_clean else 0.0
                            
                            if employee_name:
                                sheet_data[employee_name] = ve_net
                        except ValueError:
                            pass
        
        print(f"\n   Valid entries parsed: {len(sheet_data)}")
        
        if len(sheet_data) > 0:
            print(f"   Sample entries:")
            for i, (name, value) in enumerate(list(sheet_data.items())[:3]):
                print(f"      {name}: ${value:,.2f}")

except Exception as e:
    print(f"   ❌ Error parsing CSV: {e}")
    import traceback
    traceback.print_exc()
    exit()

if len(sheet_data) == 0:
    print(f"\n⚠️  No data parsed from spreadsheet")
    print(f"   This might mean:")
    print(f"   - Wrong sheet tab")
    print(f"   - Data is in different columns")
    print(f"   - Sheet structure is different than expected")
    exit()

# Compare
print(f"\n{'Employee':<30} | {'Odoo VE_NET':>15} | {'Sheet VE_NET':>15} | {'Diff':>12} | Status")
print("=" * 100)

matches = 0
mismatches = 0
not_found = 0

for employee_name in sorted(odoo_data.keys()):
    odoo_net = odoo_data[employee_name]
    
    # Try to find in sheet data (exact match)
    sheet_net = sheet_data.get(employee_name)
    
    # Try uppercase
    if sheet_net is None:
        sheet_net = sheet_data.get(employee_name.upper())
    
    # Try lowercase
    if sheet_net is None:
        sheet_net = sheet_data.get(employee_name.lower())
    
    # Try title case
    if sheet_net is None:
        sheet_net = sheet_data.get(employee_name.title())
    
    if sheet_net is None:
        status = "❓ NOT IN SHEET"
        not_found += 1
        diff = 0.0
    else:
        diff = abs(odoo_net - sheet_net)
        if diff < 0.50:  # Allow 50 cents difference
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
print(f"   📊 Total:                {len(odoo_data)}")

if mismatches == 0 and not_found == 0:
    print(f"\n🎉 ALL {matches} PAYSLIPS MATCH SPREADSHEET PERFECTLY!")
    print(f"   VE_NET values in Odoo NOVIEMBRE15-2 are correct!")
elif mismatches > 0:
    print(f"\n⚠️  {mismatches} mismatches found - these may need investigation")

print("\n" + "=" * 100)

