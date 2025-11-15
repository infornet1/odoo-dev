#!/usr/bin/env python3
"""
DIAGNOSTIC: Access Google Spreadsheet and analyze actual calculations
Compare spreadsheet values with Odoo to find source of $1-3 differences
NO DATABASE MODIFICATIONS - pure read-only analysis
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

print("=" * 160)
print("🔍 DIAGNOSTIC: SPREADSHEET FORMULA ANALYSIS")
print("=" * 160)

try:
    spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
    sheet = gc.open_by_key(spreadsheet_id)

    # Find the "15nov2025" worksheet
    worksheet = None
    for ws in sheet.worksheets():
        if '15nov2025' in ws.title.lower():
            worksheet = ws
            break

    if not worksheet:
        worksheet = sheet.get_worksheet(0)

    print(f"\n✅ Connected to spreadsheet: {sheet.title}")
    print(f"   Worksheet: {worksheet.title}")

    # Get the data range D4:Z48 (headers row 4, data rows 5-48)
    print(f"\n📊 Reading data range D4:Z48...")

    # Get all values in the range
    all_values = worksheet.get('D4:Z48')

    if not all_values or len(all_values) < 2:
        print("❌ No data found in range")
        exit()

    # First row is headers (row 4)
    headers = all_values[0]
    data_rows = all_values[1:]  # Rows 5-48

    print(f"   Found {len(data_rows)} data rows")
    print(f"   Found {len(headers)} columns")

    # Display column headers with their indices
    print(f"\n📋 COLUMN HEADERS (D4:Z4):")
    print(f"   {'Col':<5} | {'Letter':<7} | {'Header':<50}")
    print(f"   {'-' * 70}")

    col_letters = [chr(68 + i) if i < 23 else chr(65) + chr(65 + i - 23) for i in range(len(headers))]
    for i, header in enumerate(headers):
        col_letter = col_letters[i] if i < len(col_letters) else f"Col{i}"
        print(f"   {i:<5} | {col_letter:<7} | {header[:50]:<50}")

    # Now let's find our 4 mismatched employees
    print(f"\n{'=' * 160}")
    print(f"🔍 ANALYZING 4 MISMATCHED EMPLOYEES")
    print(f"{'=' * 160}")

    mismatched_employees = [
        'ARCIDES ARZOLA',
        'Rafael Perez',
        'SERGIO MANEIRO',
        'PABLO NAVARRO'
    ]

    # Get Odoo data for comparison
    batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)

    for emp_name in mismatched_employees:
        print(f"\n{'=' * 160}")
        print(f"EMPLOYEE: {emp_name}")
        print(f"{'=' * 160}")

        # Find employee in spreadsheet (column D is index 0 in our data)
        sheet_row = None
        sheet_row_num = None
        for idx, row in enumerate(data_rows):
            if len(row) > 0:
                name_in_sheet = row[0].strip() if row[0] else ''
                if name_in_sheet.upper() == emp_name.upper():
                    sheet_row = row
                    sheet_row_num = idx + 5  # +5 because data starts at row 5
                    break

        if not sheet_row:
            print(f"   ❌ Not found in spreadsheet")
            continue

        print(f"   ✅ Found in spreadsheet row {sheet_row_num}")

        # Get Odoo data
        payslip = env['hr.payslip'].search([
            ('employee_id.name', 'ilike', emp_name),
            ('payslip_run_id', '=', batch.id)
        ], limit=1)

        if not payslip:
            print(f"   ❌ Payslip not found in Odoo")
            continue

        # Display all spreadsheet values for this employee
        print(f"\n   SPREADSHEET VALUES (row {sheet_row_num}):")
        print(f"   {'Col':<5} | {'Header':<50} | {'Value':<20}")
        print(f"   {'-' * 80}")

        for i, value in enumerate(sheet_row):
            if i < len(headers):
                header = headers[i]
                print(f"   {i:<5} | {header[:50]:<50} | {str(value)[:20]:<20}")

        # Get Odoo payslip lines
        print(f"\n   ODOO PAYSLIP LINES:")
        print(f"   {'Code':<20} | {'Name':<50} | {'Total':>15}")
        print(f"   {'-' * 90}")

        for line in payslip.line_ids.sorted(lambda l: l.sequence):
            if line.total != 0:
                print(f"   {line.salary_rule_id.code:<20} | {line.name[:50]:<50} | ${line.total:>14,.2f}")

        # Try to match key values
        print(f"\n   COMPARISON:")
        print(f"   {'Item':<30} | {'Odoo':>15} | {'Spreadsheet':>15} | {'Diff':>12}")
        print(f"   {'-' * 80}")

        # Try to find VE_NET in spreadsheet (should be in column Y, index 21 in D-Z range)
        # Column Y is the 22nd column starting from D (D=0, E=1, ..., Y=21)
        if len(sheet_row) > 21:
            try:
                sheet_net_str = str(sheet_row[21]).replace('$', '').replace(',', '').strip()
                sheet_net = float(sheet_net_str) if sheet_net_str else 0.0
            except:
                sheet_net = 0.0

            odoo_net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
            odoo_net = odoo_net_line[0].total if odoo_net_line else 0.0

            diff = odoo_net - sheet_net
            print(f"   {'VE_NET':<30} | ${odoo_net:>14,.2f} | ${sheet_net:>14,.2f} | ${diff:>11,.2f}")

    print(f"\n{'=' * 160}")
    print(f"💡 NEXT STEP:")
    print(f"   Now that we can see the spreadsheet columns, we need to identify:")
    print(f"   1. Which columns contain Salary, Bonus, Gross")
    print(f"   2. Which columns contain SSO, FAOV, PARO deductions")
    print(f"   3. Compare each component to find where the $1-3 difference comes from")
    print(f"{'=' * 160}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
