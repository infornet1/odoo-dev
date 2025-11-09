#!/usr/bin/env python3
"""
Aguinaldos Payroll Analysis Script
Analyzes December payroll data from Google Sheets for Aguinaldos (Christmas Bonus) implementation
"""

import sys
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

class AguinaldosAnalyzer:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.salary_column = 'K'  # Column with VEB salary amounts (SALARIO MENSUAL MAS BONO)
        self.exchange_rate_cell = 'O2'  # Cell with exchange rate (found at O2: 219.87)
        self.data_start_row = 5  # Data starts at row 5

    def connect_to_sheet(self):
        """Connect to Google Sheets using service account"""
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets']
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(self.payroll_sheet_id)
            print(f"✓ Connected to payroll spreadsheet")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Google Sheets: {str(e)}")
            return False

    def explore_spreadsheet_structure(self):
        """Explore the spreadsheet structure to find exchange rate and data layout"""
        print("\n" + "="*80)
        print("SPREADSHEET STRUCTURE EXPLORATION")
        print("="*80)

        try:
            worksheet = self.spreadsheet.worksheet(self.target_sheet)
            print(f"\n✓ Found worksheet: {self.target_sheet}")
            print(f"  Rows: {worksheet.row_count}, Columns: {worksheet.col_count}")

            # Get first 5 rows to understand structure
            print(f"\n📋 First 5 rows (columns A-M):")
            print("-" * 80)
            first_rows = worksheet.get('A1:M5')
            for row_idx, row in enumerate(first_rows, start=1):
                print(f"Row {row_idx}: {row}")

            # Search for exchange rate
            print(f"\n🔍 Searching for exchange rate...")
            print("-" * 80)
            # Check common cells for exchange rate
            check_cells = ['D2', 'D3', 'D4', 'E2', 'E3', 'F2', 'O2', 'P2']
            for cell in check_cells:
                value = worksheet.acell(cell).value
                print(f"  {cell}: {value}")

        except Exception as e:
            print(f"\n✗ Error exploring structure: {str(e)}")
            import traceback
            traceback.print_exc()

    def analyze_aguinaldos_data(self):
        """Analyze the December payroll data for Aguinaldos"""
        print("\n" + "="*80)
        print("AGUINALDOS (CHRISTMAS BONUS) PAYROLL ANALYSIS")
        print("="*80)
        print(f"📊 Spreadsheet: {self.payroll_sheet_id}")
        print(f"📋 Target Sheet: {self.target_sheet}")
        print(f"💰 Salary Column: {self.salary_column}")
        print(f"💱 Exchange Rate Cell: {self.exchange_rate_cell}")
        print("="*80)

        try:
            # Get the target worksheet
            worksheet = self.spreadsheet.worksheet(self.target_sheet)
            print(f"\n✓ Found worksheet: {self.target_sheet}")
            print(f"  Rows: {worksheet.row_count}, Columns: {worksheet.col_count}")

            # Try to get exchange rate from configured cell
            exchange_rate = 0
            try:
                value = worksheet.acell(self.exchange_rate_cell).value
                if value:
                    cleaned_value = value.replace(',', '.').replace(' ', '').strip()
                    exchange_rate = float(cleaned_value)
                    print(f"\n💱 Exchange Rate from {self.exchange_rate_cell}: {exchange_rate:,.2f} VEB/USD")
            except Exception as e:
                print(f"⚠ Warning: Could not get exchange rate from {self.exchange_rate_cell}: {e}")
                # Try alternative locations
                for cell in ['O2', 'P2', 'D2']:
                    try:
                        value = worksheet.acell(cell).value
                        if value:
                            cleaned_value = value.replace(',', '.').replace(' ', '').strip()
                            test_rate = float(cleaned_value)
                            if 100 < test_rate < 300:  # Reasonable exchange rate range
                                exchange_rate = test_rate
                                print(f"✓ Exchange Rate found in {cell}: {exchange_rate:,.2f} VEB/USD")
                                break
                    except:
                        continue

            if exchange_rate == 0:
                print(f"✗ ERROR: Could not find exchange rate!")
                return None

            # Get all data from the sheet
            all_data = worksheet.get_all_values()
            headers = all_data[0] if all_data else []

            print(f"\n📋 Column Headers:")
            for i, header in enumerate(headers[:15]):  # Show first 15 columns
                col_letter = chr(65 + i)  # A=65 in ASCII
                print(f"  {col_letter}: {header}")

            # Get column K data (salary)
            salary_col_index = ord(self.salary_column) - 65  # Convert K to 10 (0-indexed)

            employees_data = []
            print(f"\n👥 Employee Salary Data (Column {self.salary_column}):")
            print("-" * 80)

            # Start from data_start_row (row 5 = index 4)
            for row_idx in range(self.data_start_row - 1, len(all_data)):
                row = all_data[row_idx]
                actual_row_num = row_idx + 1  # For display

                # Get employee name from column D (index 3) - "NOMBRE Y APELLIDO"
                employee_name = row[3] if len(row) > 3 else ""

                # Skip empty rows or header-like rows
                if not employee_name or employee_name.strip() == "" or employee_name.strip().upper() in ['NOMBRE Y APELLIDO', 'TOTAL']:
                    continue

                # Get salary from column K
                salary_veb = row[salary_col_index] if len(row) > salary_col_index else "0"

                # Clean and convert salary
                try:
                    # Handle both US format (62,748.90) and EU format (62.748,90)
                    salary_veb_clean = salary_veb.strip()

                    # Detect format by counting dots and commas
                    dot_count = salary_veb_clean.count('.')
                    comma_count = salary_veb_clean.count(',')

                    if dot_count > 0 and comma_count > 0:
                        # Mixed format - determine which is decimal separator
                        last_dot_pos = salary_veb_clean.rfind('.')
                        last_comma_pos = salary_veb_clean.rfind(',')

                        if last_dot_pos > last_comma_pos:
                            # US format: 62,748.90 -> remove comma, keep dot
                            salary_veb_clean = salary_veb_clean.replace(',', '')
                        else:
                            # EU format: 62.748,90 -> remove dot, replace comma with dot
                            salary_veb_clean = salary_veb_clean.replace('.', '').replace(',', '.')
                    elif dot_count > 1:
                        # Multiple dots = EU thousands separator: 62.748 -> 62748
                        salary_veb_clean = salary_veb_clean.replace('.', '')
                    elif comma_count > 1:
                        # Multiple commas = US thousands separator: 62,748 -> 62748
                        salary_veb_clean = salary_veb_clean.replace(',', '')
                    elif comma_count == 1 and dot_count == 0:
                        # Single comma, no dot = EU decimal: 62,90 -> 62.90
                        salary_veb_clean = salary_veb_clean.replace(',', '.')
                    # else: single dot or no separators - keep as is

                    salary_veb_float = float(salary_veb_clean) if salary_veb_clean else 0

                    # Calculate USD equivalent
                    salary_usd = salary_veb_float / exchange_rate if exchange_rate > 0 else 0

                    # Calculate Aguinaldos (2x monthly salary)
                    aguinaldos_veb = salary_veb_float * 2
                    aguinaldos_usd = salary_usd * 2

                    employees_data.append({
                        'row': actual_row_num,
                        'name': employee_name.strip(),
                        'monthly_veb': salary_veb_float,
                        'monthly_usd': salary_usd,
                        'aguinaldos_veb': aguinaldos_veb,
                        'aguinaldos_usd': aguinaldos_usd
                    })

                    print(f"  Row {actual_row_num:3d}: {employee_name[:30]:<30} | "
                          f"Monthly: {salary_veb_float:>12,.2f} VEB = ${salary_usd:>8,.2f} USD | "
                          f"Aguinaldos: ${aguinaldos_usd:>8,.2f} USD")

                except ValueError as e:
                    print(f"  Row {actual_row_num:3d}: {employee_name[:30]:<30} | ERROR: Invalid salary format '{salary_veb}'")
                    continue

            # Summary statistics
            print("\n" + "="*80)
            print("📊 AGUINALDOS SUMMARY")
            print("="*80)
            print(f"Total Employees: {len(employees_data)}")

            if employees_data:
                total_monthly_veb = sum(e['monthly_veb'] for e in employees_data)
                total_monthly_usd = sum(e['monthly_usd'] for e in employees_data)
                total_aguinaldos_veb = sum(e['aguinaldos_veb'] for e in employees_data)
                total_aguinaldos_usd = sum(e['aguinaldos_usd'] for e in employees_data)

                print(f"\nMonthly Salary Totals:")
                print(f"  VEB: {total_monthly_veb:>15,.2f}")
                print(f"  USD: ${total_monthly_usd:>14,.2f}")

                print(f"\nAguinaldos (2x Monthly) Totals:")
                print(f"  VEB: {total_aguinaldos_veb:>15,.2f}")
                print(f"  USD: ${total_aguinaldos_usd:>14,.2f}")

                print(f"\nAverage Aguinaldos per Employee:")
                print(f"  USD: ${total_aguinaldos_usd / len(employees_data):>14,.2f}")

            return {
                'exchange_rate': exchange_rate,
                'employees': employees_data,
                'total_monthly_usd': total_monthly_usd if employees_data else 0,
                'total_aguinaldos_usd': total_aguinaldos_usd if employees_data else 0
            }

        except Exception as e:
            print(f"\n✗ Error analyzing data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

def main():
    """Main execution function"""
    print("\n🎄 AGUINALDOS (CHRISTMAS BONUS) ANALYSIS")
    print(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    analyzer = AguinaldosAnalyzer()

    if not analyzer.connect_to_sheet():
        print("\n❌ Failed to connect to spreadsheet. Exiting.")
        sys.exit(1)

    # First explore the structure
    analyzer.explore_spreadsheet_structure()

    # Then analyze the data
    result = analyzer.analyze_aguinaldos_data()

    if result:
        print("\n✓ Analysis completed successfully!")
        print("\nNext Steps:")
        print("  1. Review the salary data above")
        print("  2. Verify exchange rate is correct")
        print("  3. Confirm Aguinaldos calculation (2x monthly salary)")
        print("  4. Create Odoo salary structure and rules")
        print("  5. Configure December payroll batch")
    else:
        print("\n❌ Analysis failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
