#!/usr/bin/env python3
"""
Contract Salary Validation Script
Compares Odoo contract wages with Google Sheets payroll data
"""

import sys
import psycopg2
import gspread
from google.oauth2.service_account import Credentials

class SalaryValidator:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.salary_column = 'K'
        self.exchange_rate_cell = 'O2'

        # Odoo database connection
        self.db_config = {
            'host': 'localhost',
            'port': 5433,
            'database': 'testing',
            'user': 'odoo',
            'password': 'odoo8069'
        }

    def connect_to_sheet(self):
        """Connect to Google Sheets"""
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.payroll_sheet_id)
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

        for row_idx in range(4, len(all_data)):  # Start from row 5 (index 4)
            row = all_data[row_idx]

            # Employee name from column D (index 3)
            employee_name = row[3].strip() if len(row) > 3 else ""

            if not employee_name or employee_name.upper() in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA']:
                continue

            # Salary from column K
            salary_veb = row[salary_col_index] if len(row) > salary_col_index else "0"

            try:
                # Parse salary
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

                # Normalize employee name for matching
                normalized_name = employee_name.upper().strip()

                sheet_salaries[normalized_name] = {
                    'veb': salary_veb_float,
                    'usd': salary_usd,
                    'original_name': employee_name
                }
            except:
                continue

        return sheet_salaries, exchange_rate

    def get_odoo_contracts(self):
        """Get active contracts from Odoo"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()

            query = """
                SELECT
                    e.name as employee_name,
                    c.wage as contract_wage_usd,
                    c.state as contract_status,
                    c.date_start,
                    c.date_end,
                    e.id as employee_id,
                    c.id as contract_id
                FROM hr_contract c
                JOIN hr_employee e ON c.employee_id = e.id
                WHERE c.state = 'open'
                  AND (c.date_end IS NULL OR c.date_end >= CURRENT_DATE)
                ORDER BY e.name;
            """

            cur.execute(query)
            results = cur.fetchall()

            odoo_contracts = {}
            for row in results:
                employee_name, wage_usd, status, date_start, date_end, emp_id, contract_id = row

                # Normalize employee name for matching
                normalized_name = employee_name.upper().strip()

                # Skip duplicates (take first active contract)
                if normalized_name not in odoo_contracts:
                    odoo_contracts[normalized_name] = {
                        'usd': float(wage_usd) if wage_usd else 0,
                        'original_name': employee_name,
                        'employee_id': emp_id,
                        'contract_id': contract_id,
                        'date_start': date_start,
                        'date_end': date_end
                    }

            cur.close()
            conn.close()

            return odoo_contracts

        except Exception as e:
            print(f"✗ Error connecting to Odoo database: {e}")
            return {}

    def compare_salaries(self):
        """Compare salaries from both sources"""
        print("\n" + "="*100)
        print("SALARY VALIDATION: Odoo Contracts vs Google Sheets Payroll Data")
        print("="*100)

        # Get data from both sources
        sheet_salaries, exchange_rate = self.get_spreadsheet_salaries()
        odoo_contracts = self.get_odoo_contracts()

        print(f"\n📊 Data Summary:")
        print(f"  Exchange Rate: {exchange_rate:,.2f} VEB/USD")
        print(f"  Employees in Spreadsheet: {len(sheet_salaries)}")
        print(f"  Active Contracts in Odoo: {len(odoo_contracts)}")

        # Find all unique employee names
        all_employees = set(sheet_salaries.keys()) | set(odoo_contracts.keys())

        matches = []
        mismatches = []
        sheet_only = []
        odoo_only = []

        for emp_name in sorted(all_employees):
            sheet_data = sheet_salaries.get(emp_name)
            odoo_data = odoo_contracts.get(emp_name)

            if sheet_data and odoo_data:
                # Both sources have this employee
                sheet_usd = sheet_data['usd']
                odoo_usd = odoo_data['usd']
                difference = abs(sheet_usd - odoo_usd)
                percent_diff = (difference / sheet_usd * 100) if sheet_usd > 0 else 0

                if percent_diff < 2:  # Allow 2% tolerance
                    matches.append({
                        'name': sheet_data['original_name'],
                        'sheet_usd': sheet_usd,
                        'odoo_usd': odoo_usd,
                        'difference': difference,
                        'percent_diff': percent_diff
                    })
                else:
                    mismatches.append({
                        'name': sheet_data['original_name'],
                        'sheet_usd': sheet_usd,
                        'sheet_veb': sheet_data['veb'],
                        'odoo_usd': odoo_usd,
                        'difference': difference,
                        'percent_diff': percent_diff
                    })
            elif sheet_data and not odoo_data:
                # Only in spreadsheet
                sheet_only.append({
                    'name': sheet_data['original_name'],
                    'sheet_usd': sheet_data['usd'],
                    'sheet_veb': sheet_data['veb']
                })
            elif odoo_data and not sheet_data:
                # Only in Odoo
                odoo_only.append({
                    'name': odoo_data['original_name'],
                    'odoo_usd': odoo_data['usd']
                })

        # Print results
        print(f"\n✅ MATCHES ({len(matches)} employees):")
        print("-" * 100)
        if matches:
            print(f"{'Employee Name':<30} | {'Sheet USD':>12} | {'Odoo USD':>12} | {'Difference':>12} | {'% Diff':>8}")
            print("-" * 100)
            for m in matches[:10]:  # Show first 10
                print(f"{m['name']:<30} | ${m['sheet_usd']:>11,.2f} | ${m['odoo_usd']:>11,.2f} | ${m['difference']:>11,.2f} | {m['percent_diff']:>7.2f}%")
            if len(matches) > 10:
                print(f"... and {len(matches) - 10} more matches")
        else:
            print("  No exact matches found!")

        print(f"\n❌ MISMATCHES ({len(mismatches)} employees) - CRITICAL:")
        print("-" * 100)
        if mismatches:
            print(f"{'Employee Name':<30} | {'Sheet USD':>12} | {'Odoo USD':>12} | {'Difference':>12} | {'% Diff':>8}")
            print("-" * 100)
            for m in mismatches:
                print(f"{m['name']:<30} | ${m['sheet_usd']:>11,.2f} | ${m['odoo_usd']:>11,.2f} | ${m['difference']:>11,.2f} | {m['percent_diff']:>7.2f}%")
                print(f"  → Sheet VEB: {m['sheet_veb']:>12,.2f} ÷ {exchange_rate:.2f} = ${m['sheet_usd']:.2f}")
                print(f"  → Odoo needs UPDATE to: ${m['sheet_usd']:.2f}")
                print()

        print(f"\n⚠️  IN SPREADSHEET ONLY ({len(sheet_only)} employees):")
        print("-" * 100)
        if sheet_only:
            for s in sheet_only[:10]:
                print(f"  {s['name']:<40} ${s['sheet_usd']:>10,.2f} (VEB: {s['sheet_veb']:>12,.2f})")
                print(f"    → Need to CREATE Odoo contract")
            if len(sheet_only) > 10:
                print(f"... and {len(sheet_only) - 10} more")

        print(f"\n⚠️  IN ODOO ONLY ({len(odoo_only)} employees):")
        print("-" * 100)
        if odoo_only:
            for o in odoo_only[:10]:
                print(f"  {o['name']:<40} ${o['odoo_usd']:>10,.2f}")
                print(f"    → Not found in current payroll spreadsheet")
            if len(odoo_only) > 10:
                print(f"... and {len(odoo_only) - 10} more")

        # Summary
        print("\n" + "="*100)
        print("📊 VALIDATION SUMMARY")
        print("="*100)
        print(f"✅ Matching contracts: {len(matches)}")
        print(f"❌ Mismatched contracts: {len(mismatches)}")
        print(f"⚠️  Missing from Odoo: {len(sheet_only)}")
        print(f"⚠️  Missing from Sheet: {len(odoo_only)}")

        if mismatches or sheet_only:
            print(f"\n🚨 CRITICAL: {len(mismatches) + len(sheet_only)} contracts need correction before Aguinaldos implementation!")
            print(f"\nACTION REQUIRED:")
            if mismatches:
                print(f"  1. UPDATE {len(mismatches)} contract wages in Odoo to match spreadsheet")
            if sheet_only:
                print(f"  2. CREATE {len(sheet_only)} new contracts in Odoo")
            return False
        else:
            print(f"\n✅ SUCCESS: All employee contracts match! Ready for Aguinaldos implementation.")
            return True

def main():
    validator = SalaryValidator()

    if not validator.connect_to_sheet():
        sys.exit(1)

    success = validator.compare_salaries()

    if not success:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
