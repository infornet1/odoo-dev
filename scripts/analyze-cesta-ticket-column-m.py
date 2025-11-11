#!/usr/bin/env python3
"""
Analyze Cesta Ticket (Column M) from Payroll Spreadsheet

This script analyzes Column M (CESTA TICKET MENSUAL PTR) to prepare for:
1. Separating Cesta Ticket as a distinct benefit
2. Rebalancing 70/25/5 distribution
3. Ensuring total compensation remains unchanged

Business Context:
- Venezuelan labor law requires Cesta Ticket as separate benefit
- Currently included in total but not broken out in Odoo
- Need to rebalance: (K+L) split into 70/25/5, plus separate M (Cesta Ticket)
"""

import sys
import gspread
from google.oauth2.service_account import Credentials

class CestaTicketAnalyzer:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.exchange_rate_cell = 'O2'

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
            print(f"✗ Failed to connect: {e}")
            return False

    def parse_amount(self, value):
        """Parse Venezuelan number format (. as thousands, , as decimal)"""
        if not value or value.strip() == '':
            return 0.0

        value_clean = value.strip()

        # Count separators
        dot_count = value_clean.count('.')
        comma_count = value_clean.count(',')

        # Determine format
        if dot_count > 0 and comma_count > 0:
            # Both present - determine which is decimal
            last_dot_pos = value_clean.rfind('.')
            last_comma_pos = value_clean.rfind(',')
            if last_dot_pos > last_comma_pos:
                # US format: 1,234.56
                value_clean = value_clean.replace(',', '')
            else:
                # EU format: 1.234,56
                value_clean = value_clean.replace('.', '').replace(',', '.')
        elif dot_count > 1:
            # Multiple dots = thousands separator
            value_clean = value_clean.replace('.', '')
        elif comma_count > 1:
            # Multiple commas = thousands separator
            value_clean = value_clean.replace(',', '')
        elif comma_count == 1 and dot_count == 0:
            # Single comma = decimal
            value_clean = value_clean.replace(',', '.')

        try:
            return float(value_clean)
        except ValueError:
            print(f"⚠️  Could not parse: '{value}'")
            return 0.0

    def analyze_columns(self):
        """Analyze Columns K, L, M and their relationship"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = self.parse_amount(exchange_rate_value)
        print(f"\n💱 Exchange Rate: {exchange_rate:.2f} VEB/USD (from {self.exchange_rate_cell})")

        # Get all data
        all_data = worksheet.get_all_values()

        # Column indices (A=0, K=10, L=11, M=12)
        col_k_idx = 10  # Column K (SALARIO MENSUAL MAS BONO)
        col_l_idx = 11  # Column L (OTROS BONOS)
        col_m_idx = 12  # Column M (CESTA TICKET MENSUAL PTR)

        print(f"\n📋 Column Headers (Row 4):")
        if len(all_data) > 3:
            print(f"  K: {all_data[3][col_k_idx]}")
            print(f"  L: {all_data[3][col_l_idx]}")
            print(f"  M: {all_data[3][col_m_idx]}")

        # Analyze employee data
        employees = []

        for row_idx in range(4, len(all_data)):
            row = all_data[row_idx]

            # Get employee name (Column D, index 3)
            employee_name = row[3].strip().upper() if len(row) > 3 else ""

            # Skip headers and totals
            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA', '']:
                continue

            # Get values
            try:
                k_veb = self.parse_amount(row[col_k_idx]) if len(row) > col_k_idx else 0.0
                l_veb = self.parse_amount(row[col_l_idx]) if len(row) > col_l_idx else 0.0
                m_veb = self.parse_amount(row[col_m_idx]) if len(row) > col_m_idx else 0.0

                # Convert to USD
                k_usd = k_veb / exchange_rate if exchange_rate > 0 else 0.0
                l_usd = l_veb / exchange_rate if exchange_rate > 0 else 0.0
                m_usd = m_veb / exchange_rate if exchange_rate > 0 else 0.0

                # Calculate totals
                total_veb = k_veb + l_veb + m_veb
                total_usd = k_usd + l_usd + m_usd

                # Calculate percentages
                k_pct = (k_usd / total_usd * 100) if total_usd > 0 else 0.0
                l_pct = (l_usd / total_usd * 100) if total_usd > 0 else 0.0
                m_pct = (m_usd / total_usd * 100) if total_usd > 0 else 0.0

                employees.append({
                    'name': employee_name,
                    'row': row_idx + 1,
                    'k_veb': k_veb,
                    'l_veb': l_veb,
                    'm_veb': m_veb,
                    'k_usd': k_usd,
                    'l_usd': l_usd,
                    'm_usd': m_usd,
                    'total_veb': total_veb,
                    'total_usd': total_usd,
                    'k_pct': k_pct,
                    'l_pct': l_pct,
                    'm_pct': m_pct
                })
            except Exception as e:
                print(f"⚠️  Error processing {employee_name}: {e}")
                continue

        return employees, exchange_rate

    def print_analysis(self, employees, exchange_rate):
        """Print comprehensive analysis"""

        print(f"\n" + "="*100)
        print(f"CESTA TICKET (COLUMN M) ANALYSIS")
        print(f"="*100)

        print(f"\n📊 Total Employees: {len(employees)}")

        # Calculate statistics
        if not employees:
            print("⚠️  No employee data found")
            return

        # Cesta Ticket statistics
        m_values = [e['m_usd'] for e in employees]
        m_min = min(m_values)
        m_max = max(m_values)
        m_avg = sum(m_values) / len(m_values)
        m_total = sum(m_values)

        # Unique Cesta Ticket values
        m_unique = sorted(set(m_values), reverse=True)

        print(f"\n💰 CESTA TICKET (Column M) Statistics:")
        print(f"  Minimum:  ${m_min:>10.2f} USD")
        print(f"  Maximum:  ${m_max:>10.2f} USD")
        print(f"  Average:  ${m_avg:>10.2f} USD")
        print(f"  Total:    ${m_total:>10.2f} USD")

        print(f"\n🔢 Unique Cesta Ticket Values ({len(m_unique)}):")
        for value in m_unique:
            count = sum(1 for e in employees if e['m_usd'] == value)
            print(f"  ${value:>10.2f} USD - {count:>3} employees")

        # Distribution analysis
        print(f"\n📊 Current Compensation Breakdown (K+L+M):")
        k_total = sum(e['k_usd'] for e in employees)
        l_total = sum(e['l_usd'] for e in employees)
        m_total = sum(e['m_usd'] for e in employees)
        total_comp = k_total + l_total + m_total

        k_pct_avg = (k_total / total_comp * 100) if total_comp > 0 else 0
        l_pct_avg = (l_total / total_comp * 100) if total_comp > 0 else 0
        m_pct_avg = (m_total / total_comp * 100) if total_comp > 0 else 0

        print(f"  Column K (Salary+Bonus): ${k_total:>12,.2f} USD ({k_pct_avg:>5.2f}%)")
        print(f"  Column L (Other Bonuses): ${l_total:>12,.2f} USD ({l_pct_avg:>5.2f}%)")
        print(f"  Column M (Cesta Ticket):  ${m_total:>12,.2f} USD ({m_pct_avg:>5.2f}%)")
        print(f"  {'TOTAL:':<26} ${total_comp:>12,.2f} USD (100.00%)")

        # Show sample employees
        print(f"\n👥 Sample Employee Breakdown (First 10):")
        print(f"  {'Employee':<30} | {'K (USD)':>10} | {'L (USD)':>10} | {'M (USD)':>10} | {'Total':>10} | M%")
        print(f"  {'-'*30}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*6}")

        for emp in employees[:10]:
            print(f"  {emp['name']:<30} | ${emp['k_usd']:>9.2f} | ${emp['l_usd']:>9.2f} | ${emp['m_usd']:>9.2f} | ${emp['total_usd']:>9.2f} | {emp['m_pct']:>5.2f}%")

        if len(employees) > 10:
            print(f"  ... and {len(employees) - 10} more employees")

        # Rebalancing preview
        print(f"\n" + "="*100)
        print(f"REBALANCING PREVIEW")
        print(f"="*100)

        print(f"\n📋 Current System (Odoo):")
        print(f"  • Column K is used for 70/25/5 distribution")
        print(f"  • Column M is NOT separated (Cesta Ticket rule returns 0.0)")
        print(f"  • Total = K (distributed as 70% + 25% + 5%)")

        print(f"\n🎯 Proposed System:")
        print(f"  • Separate Column M into contract.cesta_ticket_usd field")
        print(f"  • Rebalance Column K to become (K+L)")
        print(f"  • Apply 70/25/5 distribution to (K+L)")
        print(f"  • VE_CESTA_TICKET rule uses contract.cesta_ticket_usd")
        print(f"  • Total remains: (New K × 70%) + (New K × 25%) + (New K × 5%) + M")

        print(f"\n💡 Rebalancing Formula:")
        print(f"  New Base Amount = Old K + Old L")
        print(f"  ueipab_salary_base = New Base × 70%")
        print(f"  ueipab_bonus_regular = New Base × 25%")
        print(f"  ueipab_extra_bonus = New Base × 5%")
        print(f"  cesta_ticket_usd = Old M (Column M value)")

        print(f"\n✅ Verification:")
        print(f"  Old Total = Old K + Old L + Old M")
        print(f"  New Total = (New Base × 70%) + (New Base × 25%) + (New Base × 5%) + Old M")
        print(f"  New Total = New Base + Old M")
        print(f"  New Total = (Old K + Old L) + Old M")
        print(f"  New Total = Old K + Old L + Old M ✓")

        # Show example for one employee
        if employees:
            emp = employees[0]
            print(f"\n📝 Example: {emp['name']}")
            print(f"  Current Spreadsheet:")
            print(f"    K (Salary+Bonus):  ${emp['k_usd']:>10.2f} USD")
            print(f"    L (Other Bonuses): ${emp['l_usd']:>10.2f} USD")
            print(f"    M (Cesta Ticket):  ${emp['m_usd']:>10.2f} USD")
            print(f"    TOTAL:             ${emp['total_usd']:>10.2f} USD")

            new_base = emp['k_usd'] + emp['l_usd']
            new_70 = new_base * 0.70
            new_25 = new_base * 0.25
            new_05 = new_base * 0.05
            new_cesta = emp['m_usd']
            new_total = new_70 + new_25 + new_05 + new_cesta

            print(f"\n  After Rebalancing:")
            print(f"    New Base (K+L):           ${new_base:>10.2f} USD")
            print(f"    ueipab_salary_base (70%): ${new_70:>10.2f} USD")
            print(f"    ueipab_bonus_regular (25%): ${new_25:>10.2f} USD")
            print(f"    ueipab_extra_bonus (5%):  ${new_05:>10.2f} USD")
            print(f"    cesta_ticket_usd:         ${new_cesta:>10.2f} USD")
            print(f"    TOTAL:                    ${new_total:>10.2f} USD")

            difference = abs(emp['total_usd'] - new_total)
            if difference < 0.01:
                print(f"    ✅ Totals match! (diff: ${difference:.4f})")
            else:
                print(f"    ⚠️  Difference: ${difference:.4f}")

def main():
    print("="*100)
    print("CESTA TICKET (COLUMN M) ANALYSIS")
    print("Preparing for Cesta Ticket Separation and Rebalancing")
    print("="*100)

    analyzer = CestaTicketAnalyzer()

    if not analyzer.connect_to_sheet():
        sys.exit(1)

    employees, exchange_rate = analyzer.analyze_columns()
    analyzer.print_analysis(employees, exchange_rate)

    print(f"\n" + "="*100)
    print(f"NEXT STEPS")
    print(f"="*100)
    print(f"\n1. Review analysis above")
    print(f"2. Verify Column M values are correct")
    print(f"3. Create rebalancing script")
    print(f"4. Update VE_CESTA_TICKET salary rule")
    print(f"5. Test with one employee in development")
    print(f"6. Deploy to production")

    print(f"\n✓ Analysis completed successfully!")

if __name__ == '__main__':
    main()
