#!/usr/bin/env python3
"""
CRITICAL ANALYSIS:
1. Verify if spreadsheet uses 70% of deduction_base for ALL employees
2. Check why 40 employees matched but 4 didn't
3. Determine impact if we change formula
NO MODIFICATIONS - pure diagnostic
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    '/tmp/gsheet_credentials.json',
    scope
)
gc = gspread.authorize(credentials)

print("=" * 160)
print("🔍 CRITICAL ANALYSIS: 70% DEDUCTION BASE PATTERN")
print("=" * 160)

# Get Odoo data
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

period_end = max(batch.slip_ids.mapped('date_to'))
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', period_end)
], limit=1, order='name desc')
exchange_rate = rate_record.company_rate if rate_record else 234.87

# Connect to spreadsheet
spreadsheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
sheet = gc.open_by_key(spreadsheet_id)
worksheet = None
for ws in sheet.worksheets():
    if '15nov2025' in ws.title.lower():
        worksheet = ws
        break
if not worksheet:
    worksheet = sheet.get_worksheet(0)

all_values = worksheet.get('D4:Z48')
headers = all_values[0]
data_rows = all_values[1:]

def parse_veb(value_str):
    try:
        cleaned = str(value_str).replace(',', '').replace(' ', '').strip()
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

print(f"\n📊 TESTING ALL 44 EMPLOYEES - Which deduction base does spreadsheet use?")
print(f"{'Employee':<25} | {'Deduction Base':>15} | {'70% Base':>15} | {'Sheet SSO':>12} | {'Calc on 100%':>15} | {'Calc on 70%':>14} | {'Match?':<10}")
print(f"{'-' * 140}")

matched_100 = 0
matched_70 = 0
neither = 0

for payslip in batch.slip_ids.sorted(lambda p: p.employee_id.name):
    emp_name = payslip.employee_id.name
    deduction_base = payslip.contract_id.ueipab_deduction_base
    base_70 = deduction_base * 0.70

    # Get Odoo SSO
    sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')
    odoo_sso = abs(sso_line[0].total) if sso_line else 0.0

    # Find in spreadsheet
    sheet_row = None
    for row in data_rows:
        if len(row) > 0 and row[0].strip().upper() == emp_name.upper():
            sheet_row = row
            break

    if not sheet_row:
        continue

    # Get spreadsheet SSO (column N = index 10)
    sheet_sso_veb = parse_veb(sheet_row[10]) if len(sheet_row) > 10 else 0.0
    sheet_sso_usd = sheet_sso_veb / exchange_rate

    # Calculate what SSO SHOULD be under both scenarios
    calc_100 = deduction_base * 0.0225  # 2.25% on full base
    calc_70 = base_70 * 0.0225          # 2.25% on 70% base

    # Check which one matches spreadsheet
    diff_100 = abs(sheet_sso_usd - calc_100)
    diff_70 = abs(sheet_sso_usd - calc_70)

    if diff_100 < 0.01:
        match = "100% ✅"
        matched_100 += 1
    elif diff_70 < 0.01:
        match = "70% ✅"
        matched_70 += 1
    else:
        match = "❓ Neither"
        neither += 1

    # Show details for mismatched employees
    if emp_name.upper() in ['ARCIDES ARZOLA', 'RAFAEL PEREZ', 'SERGIO MANEIRO', 'PABLO NAVARRO']:
        print(f"{emp_name[:24]:<25} | ${deduction_base:>14,.2f} | ${base_70:>14,.2f} | ${sheet_sso_usd:>11,.2f} | ${calc_100:>14,.2f} | ${calc_70:>13,.2f} | {match:<10}")

print(f"{'-' * 140}")

print(f"\n📊 SUMMARY:")
print(f"   Spreadsheet uses 100% deduction_base: {matched_100} employees")
print(f"   Spreadsheet uses 70% deduction_base:  {matched_70} employees")
print(f"   Neither pattern matches:              {neither} employees")

# Now check: For employees where Odoo NET matched spreadsheet, what's their pattern?
print(f"\n{'=' * 160}")
print(f"🔍 WHY DID 40 EMPLOYEES MATCH DESPITE DIFFERENT DEDUCTION BASES?")
print(f"{'=' * 160}")

# Let's check a few employees that MATCHED
matched_employees = [
    'ALEJANDRA LOPEZ',
    'GABRIEL ESPAÑA',
    'VIRGINIA VERDE',
]

print(f"\nChecking employees whose VE_NET matched spreadsheet:")
print(f"{'Employee':<25} | {'Deduction Base':>15} | {'Odoo SSO':>12} | {'Sheet SSO':>12} | {'Diff':>10} | {'VE_NET Diff':>12}")
print(f"{'-' * 105}")

for emp_name in matched_employees:
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if not payslip:
        continue

    deduction_base = payslip.contract_id.ueipab_deduction_base

    # Get Odoo SSO
    sso_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')
    odoo_sso = abs(sso_line[0].total) if sso_line else 0.0

    # Get Odoo NET
    net_line = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')
    odoo_net = net_line[0].total if net_line else 0.0

    # Find in spreadsheet
    sheet_row = None
    for row in data_rows:
        if len(row) > 0 and row[0].strip().upper() == emp_name.upper():
            sheet_row = row
            break

    if not sheet_row:
        continue

    # Get spreadsheet values
    sheet_sso_veb = parse_veb(sheet_row[10]) if len(sheet_row) > 10 else 0.0
    sheet_sso_usd = sheet_sso_veb / exchange_rate

    sheet_net_usd = parse_veb(sheet_row[21]) if len(sheet_row) > 21 else 0.0

    sso_diff = odoo_sso - sheet_sso_usd
    net_diff = odoo_net - sheet_net_usd

    print(f"{emp_name[:24]:<25} | ${deduction_base:>14,.2f} | ${odoo_sso:>11,.2f} | ${sheet_sso_usd:>11,.2f} | ${sso_diff:>9,.2f} | ${net_diff:>11,.2f}")

print(f"\n{'=' * 160}")
print(f"💡 HYPOTHESIS TO TEST:")
print(f"{'=' * 160}")
print(f"\n   If ALL employees have SSO differences, but only 4 have NET differences:")
print(f"   → There must be OFFSETTING differences in other components (earnings or other deductions)")
print(f"   → The 4 mismatched employees might have different ARI tax or earnings that don't offset")
print(f"\n   Let's check if matched employees have COMPENSATING differences...")

print(f"\n{'=' * 160}")
print(f"🚨 CRITICAL LEGAL QUESTION:")
print(f"{'=' * 160}")
print(f"\n   Venezuelan Labor Law: Should SSO/FAOV/INCES be calculated on:")
print(f"   A) 100% of 'salario base' (deduction_base = $170.30 for Rafael)")
print(f"   B) 70% of 'salario base' (salary portion = $119.21 for Rafael)")
print(f"\n   The 30% difference represents BONUSES that may or may not be subject to social security.")
print(f"\n   ⚠️  RECOMMENDATION: Check Venezuelan law or consult with labor attorney")
print(f"   ⚠️  This affects ~$2-4 per employee per payslip = $2,000-4,000 annually for 44 employees")
print(f"{'=' * 160}")
