#!/usr/bin/env python3
"""
Production Database vs Spreadsheet Validation
Compares actual Odoo production salaries with Google Sheets payroll data
"""

import sys
import gspread
from google.oauth2.service_account import Credentials

class ProductionValidator:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.salary_column = 'K'
        self.exchange_rate_cell = 'O2'

        # Production Odoo salaries (from custom fields)
        self.odoo_production_salaries = {
            'ALEJANDRA LOPEZ': 166.68,
            'ANDRES MORALES': 149.78,
            'ARCIDES ARZOLA': 292.13,
            'AUDREY GARCIA': 141.77,
            'CAMILA ROSSATO': 178.09,
            'DAVID HERNANDEZ': 271.68,
            'DIXIA BELLORIN': 159.36,
            'DANIEL BONGIANNI': 161.45,
            'ELIS MEJIAS': 159.36,
            'EMILIO ISEA': 159.36,
            'FLORMAR HERNANDEZ': 213.07,
            'GABRIEL ESPAÑA': 182.32,
            'GABRIELA URAY': 159.36,
            'GLADYS BRITO CALZADILLA': 218.85,
            'GIOVANNI VEZZA': 205.01,
            'HEYDI RON': 159.36,
            'ISMARY ARCILA': 157.04,
            'JOSEFINA RODRIGUEZ': 166.57,
            'JOSÉ HERNÁNDEZ': 243.21,
            'JESSICA BOLIVAR': 154.13,
            'JESUS DI CESARE': 142.40,
            'LEIDYMAR ARAY': 140.37,
            'LUISA ELENA ABREU': 174.78,
            'LORENA REYES': 183.12,
            'LUIS RODRIGUEZ': 98.74,
            'MAGYELYS MATA': 159.36,
            'MARIA NIETO': 174.72,
            'MARIELA PRADO': 129.43,
            'MIRIAN HERNANDEZ': 148.03,
            'MARIA FIGUERA': 157.08,
            'NELCI BRITO': 163.52,
            'NIDYA LIRA': 114.83,
            'NORKA LA ROSA': 283.31,
            'PABLO NAVARRO': 144.65,
            'RAMON BELLO': 230.15,
            'RAFAEL PEREZ': 205.06,
            'SERGIO MANEIRO': 157.97,
            'STEFANY ROMERO': 155.00,
            'TERESA MARIN': 159.36,
            'VIRGINIA VERDE': 184.08,
            'YARITZA BRUCES': 159.36,
            'ZARETH FARIAS': 129.43,
        }

    def connect_to_sheet(self):
        """Connect to Google Sheets"""
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.payroll_sheet_id)
            print("✓ Connected to payroll spreadsheet")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {e}")
            return False

    def get_spreadsheet_salaries(self):
        """Get salaries from Google Sheets"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = float(exchange_rate_value.replace(',', '.'))

        # Get all data
        all_data = worksheet.get_all_values()
        salary_col_index = ord(self.salary_column) - 65

        sheet_salaries = {}

        for row_idx in range(4, len(all_data)):
            row = all_data[row_idx]

            employee_name = row[3].strip().upper() if len(row) > 3 else ""

            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA']:
                continue

            salary_veb = row[salary_col_index] if len(row) > salary_col_index else "0"

            try:
                salary_veb_clean = salary_veb.strip()
                dot_count = salary_veb_clean.count('.')
                comma_count = salary_veb_clean.count(',')

                if dot_count > 0 and comma_count > 0:
                    last_dot_pos = salary_veb_clean.rfind('.')
                    last_comma_pos = salary_veb_clean.rfind(',')
                    if last_dot_pos > last_comma_pos:
                        salary_veb_clean = salary_veb_clean.replace(',', '')
                    else:
                        salary_veb_clean = salary_veb_clean.replace('.', '').replace(',', '.')
                elif dot_count > 1:
                    salary_veb_clean = salary_veb_clean.replace('.', '')
                elif comma_count > 1:
                    salary_veb_clean = salary_veb_clean.replace(',', '')
                elif comma_count == 1 and dot_count == 0:
                    salary_veb_clean = salary_veb_clean.replace(',', '.')

                salary_veb_float = float(salary_veb_clean)
                salary_usd = salary_veb_float / exchange_rate

                sheet_salaries[employee_name] = {
                    'veb': salary_veb_float,
                    'usd': salary_usd
                }
            except:
                continue

        return sheet_salaries, exchange_rate

    def compare_salaries(self):
        """Compare Odoo production vs spreadsheet"""
        print("\n" + "="*100)
        print("PRODUCTION VALIDATION: Odoo Custom Fields vs Google Sheets (October 31, 2025)")
        print("="*100)

        sheet_salaries, exchange_rate = self.get_spreadsheet_salaries()

        print(f"\n📊 Data Summary:")
        print(f"  Exchange Rate: {exchange_rate:,.2f} VEB/USD")
        print(f"  Employees in Spreadsheet: {len(sheet_salaries)}")
        print(f"  Employees in Odoo Production: {len(self.odoo_production_salaries)}")

        all_employees = set(sheet_salaries.keys()) | set(self.odoo_production_salaries.keys())

        exact_matches = []
        close_matches = []
        significant_diff = []
        sheet_only = []
        odoo_only = []

        for emp_name in sorted(all_employees):
            sheet_data = sheet_salaries.get(emp_name)
            odoo_usd = self.odoo_production_salaries.get(emp_name)

            if sheet_data and odoo_usd:
                sheet_usd = sheet_data['usd']
                difference = abs(sheet_usd - odoo_usd)
                percent_diff = (difference / sheet_usd * 100) if sheet_usd > 0 else 0

                if percent_diff < 1:
                    exact_matches.append({
                        'name': emp_name,
                        'sheet': sheet_usd,
                        'odoo': odoo_usd,
                        'diff': difference,
                        'pct': percent_diff
                    })
                elif percent_diff < 15:
                    close_matches.append({
                        'name': emp_name,
                        'sheet': sheet_usd,
                        'sheet_veb': sheet_data['veb'],
                        'odoo': odoo_usd,
                        'diff': difference,
                        'pct': percent_diff
                    })
                else:
                    significant_diff.append({
                        'name': emp_name,
                        'sheet': sheet_usd,
                        'sheet_veb': sheet_data['veb'],
                        'odoo': odoo_usd,
                        'diff': difference,
                        'pct': percent_diff
                    })
            elif sheet_data:
                sheet_only.append({'name': emp_name, 'usd': sheet_data['usd'], 'veb': sheet_data['veb']})
            else:
                odoo_only.append({'name': emp_name, 'usd': odoo_usd})

        # Print results
        print(f"\n✅ EXACT MATCHES (<1% difference): {len(exact_matches)}")
        print("-" * 100)
        if exact_matches:
            for m in exact_matches[:10]:
                print(f"  {m['name']:<35} Sheet: ${m['sheet']:>8,.2f} | Odoo: ${m['odoo']:>8,.2f} | Diff: ${m['diff']:>6,.2f} ({m['pct']:.1f}%)")
            if len(exact_matches) > 10:
                print(f"  ... and {len(exact_matches) - 10} more exact matches")

        print(f"\n⚠️  CLOSE MATCHES (1-15% difference): {len(close_matches)}")
        print("-" * 100)
        if close_matches:
            for m in close_matches:
                print(f"  {m['name']:<35} Sheet: ${m['sheet']:>8,.2f} | Odoo: ${m['odoo']:>8,.2f} | Diff: ${m['diff']:>6,.2f} ({m['pct']:.1f}%)")

        print(f"\n❌ SIGNIFICANT DIFFERENCES (>15%): {len(significant_diff)}")
        print("-" * 100)
        if significant_diff:
            for m in significant_diff:
                print(f"  {m['name']:<35} Sheet: ${m['sheet']:>8,.2f} | Odoo: ${m['odoo']:>8,.2f} | Diff: ${m['diff']:>6,.2f} ({m['pct']:.1f}%)")
                print(f"    → Sheet VEB: {m['sheet_veb']:,.2f} ÷ {exchange_rate:.2f} = ${m['sheet']:.2f}")

        print(f"\n📋 IN SPREADSHEET ONLY: {len(sheet_only)}")
        if sheet_only:
            for s in sheet_only:
                print(f"  {s['name']:<35} ${s['usd']:>8,.2f} (VEB: {s['veb']:>12,.2f})")

        print(f"\n📋 IN ODOO ONLY: {len(odoo_only)}")
        if odoo_only:
            for o in odoo_only:
                print(f"  {o['name']:<35} ${o['usd']:>8,.2f}")

        # Calculate total Aguinaldos
        print("\n" + "="*100)
        print("💰 AGUINALDOS CALCULATION (2x Monthly Salary)")
        print("="*100)

        total_sheet_aguinaldos = sum(s['usd'] * 2 for s in sheet_salaries.values())
        total_odoo_aguinaldos = sum(self.odoo_production_salaries.values()) * 2

        print(f"\nUsing Spreadsheet Data:")
        print(f"  Monthly Total: ${sum(s['usd'] for s in sheet_salaries.values()):,.2f}")
        print(f"  Aguinaldos (2x): ${total_sheet_aguinaldos:,.2f}")

        print(f"\nUsing Odoo Production Data (custom fields):")
        print(f"  Monthly Total: ${sum(self.odoo_production_salaries.values()):,.2f}")
        print(f"  Aguinaldos (2x): ${total_odoo_aguinaldos:,.2f}")

        difference = abs(total_sheet_aguinaldos - total_odoo_aguinaldos)
        print(f"\nDifference: ${difference:,.2f} ({difference/total_sheet_aguinaldos*100:.1f}%)")

        # Recommendation
        print("\n" + "="*100)
        print("🎯 RECOMMENDATION")
        print("="*100)

        match_rate = (len(exact_matches) + len(close_matches)) / len(all_employees) * 100

        print(f"\nMatch Rate: {match_rate:.1f}% ({len(exact_matches) + len(close_matches)}/{len(all_employees)} employees)")

        if match_rate >= 85:
            print("\n✅ CONCLUSION: Odoo production custom fields are RELIABLE!")
            print("\n📋 FOR AGUINALDOS IMPLEMENTATION:")
            print("   Use Odoo custom fields: (ueipab_salary_base + ueipab_bonus_regular + ueipab_extra_bonus)")
            print("   Formula: Aguinaldos = (base + bonus_regular + extra_bonus) × 2")
            print(f"   Expected total: ${total_odoo_aguinaldos:,.2f}")
            return True
        else:
            print("\n⚠️  CAUTION: Significant discrepancies found!")
            print(f"   {len(significant_diff) + len(sheet_only) + len(odoo_only)} employees need review")
            return False

def main():
    validator = ProductionValidator()

    if not validator.connect_to_sheet():
        sys.exit(1)

    success = validator.compare_salaries()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
