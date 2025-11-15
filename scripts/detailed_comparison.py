#!/usr/bin/env python3
"""
DETAILED COMPARISON: Compare each component between Odoo and Spreadsheet
Convert spreadsheet Bolivares to USD using exchange rate to match Odoo
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
print("🔍 DETAILED COMPONENT-BY-COMPONENT COMPARISON")
print("=" * 160)

# Get exchange rate
batch = env['hr.payslip.run'].search([('name', '=', 'NOVIEMBRE15-2')], limit=1)
usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
veb = env['res.currency'].search([('name', '=', 'VEB')], limit=1)

# Get period end date for exchange rate
period_end = max(batch.slip_ids.mapped('date_to'))
rate_record = env['res.currency.rate'].search([
    ('currency_id', '=', veb.id),
    ('name', '<=', period_end)
], limit=1, order='name desc')

exchange_rate = rate_record.company_rate if rate_record else 234.87
print(f"\n💱 Exchange Rate: {exchange_rate:.2f} VEB/USD (date: {rate_record.name if rate_record else 'N/A'})")

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

mismatched_employees = [
    ('ARCIDES ARZOLA', 277.83, 274.97, 2.86),
    ('Rafael Perez', 193.72, 195.70, -1.98),
    ('SERGIO MANEIRO', 147.98, 148.69, -0.71),
    ('PABLO NAVARRO', 135.47, 136.16, -0.69),
]

for emp_name, odoo_net, sheet_net, diff in mismatched_employees:
    print(f"\n{'=' * 160}")
    print(f"EMPLOYEE: {emp_name} | Diff: ${diff:,.2f}")
    print(f"{'=' * 160}")

    # Find in spreadsheet
    sheet_row = None
    for row in data_rows:
        if len(row) > 0 and row[0].strip().upper() == emp_name.upper():
            sheet_row = row
            break

    if not sheet_row:
        continue

    # Get Odoo payslip
    payslip = env['hr.payslip'].search([
        ('employee_id.name', 'ilike', emp_name),
        ('payslip_run_id', '=', batch.id)
    ], limit=1)

    if not payslip:
        continue

    # Parse spreadsheet values (all in VEB, need to convert to USD)
    def parse_veb(value_str):
        try:
            cleaned = str(value_str).replace(',', '').replace(' ', '').strip()
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    # Column indices (0-based, starting from D)
    # K=7: Salario Mensual
    # L=8: Otros Bonos
    # M=9: Cesta Ticket Mensual
    # N=10: IVSS (SSO)
    # O=11: FAOV
    # P=12: INCES
    # R=14: ARI
    # T=16: Total Deducciones
    # Y=21: Net quincenal USD

    sheet_salario_mensual_veb = parse_veb(sheet_row[7]) if len(sheet_row) > 7 else 0.0
    sheet_otros_bonos_veb = parse_veb(sheet_row[8]) if len(sheet_row) > 8 else 0.0
    sheet_cesta_mensual_veb = parse_veb(sheet_row[9]) if len(sheet_row) > 9 else 0.0
    sheet_ivss_veb = parse_veb(sheet_row[10]) if len(sheet_row) > 10 else 0.0
    sheet_faov_veb = parse_veb(sheet_row[11]) if len(sheet_row) > 11 else 0.0
    sheet_inces_veb = parse_veb(sheet_row[12]) if len(sheet_row) > 12 else 0.0
    sheet_ari_veb = parse_veb(sheet_row[14]) if len(sheet_row) > 14 else 0.0
    sheet_total_ded_veb = parse_veb(sheet_row[16]) if len(sheet_row) > 16 else 0.0

    # Convert to USD (divide by exchange rate)
    sheet_salario_mensual_usd = sheet_salario_mensual_veb / exchange_rate
    sheet_otros_bonos_usd = sheet_otros_bonos_veb / exchange_rate
    sheet_cesta_mensual_usd = sheet_cesta_mensual_veb / exchange_rate
    sheet_ivss_usd = sheet_ivss_veb / exchange_rate
    sheet_faov_usd = sheet_faov_veb / exchange_rate
    sheet_inces_usd = sheet_inces_veb / exchange_rate
    sheet_ari_usd = sheet_ari_veb / exchange_rate
    sheet_total_ded_usd = sheet_total_ded_veb / exchange_rate

    # Spreadsheet shows MONTHLY values, divide by 2 for quincenal (15 days)
    sheet_salario_quincenal = sheet_salario_mensual_usd / 2
    sheet_otros_bonos_quincenal = sheet_otros_bonos_usd / 2
    sheet_cesta_quincenal = sheet_cesta_mensual_usd / 2
    sheet_ivss_quincenal = sheet_ivss_usd
    sheet_faov_quincenal = sheet_faov_usd
    sheet_inces_quincenal = sheet_inces_usd
    sheet_ari_quincenal = sheet_ari_usd
    sheet_total_ded_quincenal = sheet_total_ded_usd

    # Get Odoo components
    odoo_salary = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SALARY_70')
    odoo_bonus_25 = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_BONUS_25')
    odoo_extra_5 = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_EXTRA_5')
    odoo_cesta = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_CESTA_TICKET')
    odoo_gross = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_GROSS')
    odoo_sso = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_SSO_DED')
    odoo_faov = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_FAOV_DED')
    odoo_paro = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_PARO_DED')
    odoo_ari = payslip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_ARI_DED')

    print(f"\n   {'Component':<35} | {'Odoo USD':>15} | {'Sheet USD':>15} | {'Diff':>12}")
    print(f"   {'-' * 85}")

    # EARNINGS
    print(f"   {'EARNINGS:':<35} | {'':>15} | {'':>15} | {'':>12}")
    odoo_salary_val = odoo_salary[0].total if odoo_salary else 0.0
    print(f"   {'  Salary (VE_SALARY_70)':<35} | ${odoo_salary_val:>14,.2f} | ${sheet_salario_quincenal:>14,.2f} | ${(odoo_salary_val - sheet_salario_quincenal):>11,.2f}")

    odoo_bonus_25_val = odoo_bonus_25[0].total if odoo_bonus_25 else 0.0
    odoo_extra_5_val = odoo_extra_5[0].total if odoo_extra_5 else 0.0
    odoo_bonuses = odoo_bonus_25_val + odoo_extra_5_val
    print(f"   {'  Bonuses (25% + 5%)':<35} | ${odoo_bonuses:>14,.2f} | ${sheet_otros_bonos_quincenal:>14,.2f} | ${(odoo_bonuses - sheet_otros_bonos_quincenal):>11,.2f}")

    odoo_cesta_val = odoo_cesta[0].total if odoo_cesta else 0.0
    print(f"   {'  Cesta Ticket':<35} | ${odoo_cesta_val:>14,.2f} | ${sheet_cesta_quincenal:>14,.2f} | ${(odoo_cesta_val - sheet_cesta_quincenal):>11,.2f}")

    odoo_gross_val = odoo_gross[0].total if odoo_gross else 0.0
    sheet_gross_calc = sheet_salario_quincenal + sheet_otros_bonos_quincenal + sheet_cesta_quincenal
    print(f"   {'  GROSS TOTAL':<35} | ${odoo_gross_val:>14,.2f} | ${sheet_gross_calc:>14,.2f} | ${(odoo_gross_val - sheet_gross_calc):>11,.2f}")

    # DEDUCTIONS
    print(f"\n   {'DEDUCTIONS:':<35} | {'':>15} | {'':>15} | {'':>12}")
    odoo_sso_val = abs(odoo_sso[0].total) if odoo_sso else 0.0
    print(f"   {'  SSO/IVSS 4.5%':<35} | ${odoo_sso_val:>14,.2f} | ${sheet_ivss_quincenal:>14,.2f} | ${(odoo_sso_val - sheet_ivss_quincenal):>11,.2f}")

    odoo_faov_val = abs(odoo_faov[0].total) if odoo_faov else 0.0
    print(f"   {'  FAOV 1%':<35} | ${odoo_faov_val:>14,.2f} | ${sheet_faov_quincenal:>14,.2f} | ${(odoo_faov_val - sheet_faov_quincenal):>11,.2f}")

    odoo_paro_val = abs(odoo_paro[0].total) if odoo_paro else 0.0
    print(f"   {'  PARO/INCES 0.25%':<35} | ${odoo_paro_val:>14,.2f} | ${sheet_inces_quincenal:>14,.2f} | ${(odoo_paro_val - sheet_inces_quincenal):>11,.2f}")

    odoo_ari_val = abs(odoo_ari[0].total) if odoo_ari else 0.0
    print(f"   {'  ARI':<35} | ${odoo_ari_val:>14,.2f} | ${sheet_ari_quincenal:>14,.2f} | ${(odoo_ari_val - sheet_ari_quincenal):>11,.2f}")

    odoo_total_ded = odoo_sso_val + odoo_faov_val + odoo_paro_val + odoo_ari_val
    print(f"   {'  TOTAL DEDUCTIONS':<35} | ${odoo_total_ded:>14,.2f} | ${sheet_total_ded_quincenal:>14,.2f} | ${(odoo_total_ded - sheet_total_ded_quincenal):>11,.2f}")

    # NET CALCULATION
    print(f"\n   {'NET CALCULATION:':<35} | {'':>15} | {'':>15} | {'':>12}")
    odoo_net_calc = odoo_gross_val - odoo_total_ded
    sheet_net_calc = sheet_gross_calc - sheet_total_ded_quincenal
    print(f"   {'  Gross - Deductions':<35} | ${odoo_net_calc:>14,.2f} | ${sheet_net_calc:>14,.2f} | ${(odoo_net_calc - sheet_net_calc):>11,.2f}")
    print(f"   {'  Actual VE_NET':<35} | ${odoo_net:>14,.2f} | ${sheet_net:>14,.2f} | ${diff:>11,.2f}")

print(f"\n{'=' * 160}")
print(f"💡 ANALYSIS COMPLETE - Ready to identify pattern")
print(f"{'=' * 160}")
