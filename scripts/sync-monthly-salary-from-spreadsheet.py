#!/usr/bin/env python3
"""
Sync Monthly Salary from Spreadsheet to Odoo Contracts
WITH ENHANCED AUDIT TRAIL NOTES

This script syncs the ueipab_monthly_salary and ueipab_salary_notes fields
from the payroll spreadsheet to employee contracts.

IMPORTANT: Only processes active employees with department_id assigned (44 employees).

Enhanced notes format includes:
- Source spreadsheet and date
- Column reference
- Original VEB amount
- Exchange rate used

Example: "From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"
"""

import sys
import psycopg2
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class MonthlySalarySync:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.salary_column = 'K'
        self.exchange_rate_cell = 'O2'

        # PHASE 1: Local development database
        # For Phase 2, change to: host='10.124.0.3', port=5432, database='testing', password='odoo'
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
            print("✓ Connected to payroll spreadsheet")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def get_salary_data(self):
        """Extract salary data with complete audit information"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = float(exchange_rate_value.replace(',', '.'))

        print(f"✓ Exchange rate: {exchange_rate:.2f} VEB/USD (from cell {self.exchange_rate_cell})")

        # Get all data
        all_data = worksheet.get_all_values()
        salary_col_index = ord(self.salary_column) - 65

        employee_data = {}

        for row_idx in range(4, len(all_data)):
            row = all_data[row_idx]

            employee_name = row[3].strip().upper() if len(row) > 3 else ""

            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA']:
                continue

            salary_veb_raw = row[salary_col_index] if len(row) > salary_col_index else "0"

            try:
                # Parse VEB amount
                salary_veb_clean = salary_veb_raw.strip()
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

                salary_veb = float(salary_veb_clean)
                salary_usd = round(salary_veb / exchange_rate, 2)

                # Create enhanced notes with complete audit trail
                notes = (
                    f"From payroll sheet {self.target_sheet}, "
                    f"Column {self.salary_column} ({salary_veb:,.2f} VEB) "
                    f"@ {exchange_rate:.2f} VEB/USD"
                )

                employee_data[employee_name] = {
                    'veb': salary_veb,
                    'usd': salary_usd,
                    'notes': notes,
                    'exchange_rate': exchange_rate,
                    'sheet': self.target_sheet
                }

            except Exception as e:
                print(f"⚠️  Skipping {employee_name}: {e}")
                continue

        return employee_data, exchange_rate

    def create_backup(self, conn):
        """Create backup before updating (only employees with department assigned)"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"contract_monthly_salary_backup_{timestamp}"

        cur = conn.cursor()
        try:
            cur.execute(f"""
                CREATE TABLE {backup_table} AS
                SELECT
                    c.id,
                    c.employee_id,
                    c.ueipab_monthly_salary,
                    c.ueipab_salary_notes
                FROM hr_contract c
                JOIN hr_employee e ON c.employee_id = e.id
                WHERE c.state = 'open'
                  AND e.department_id IS NOT NULL;
            """)
            conn.commit()

            cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
            count = cur.fetchone()[0]

            print(f"✓ Backup created: {backup_table} ({count} contracts)")
            return backup_table

        except Exception as e:
            print(f"✗ Backup failed: {e}")
            conn.rollback()
            return None
        finally:
            cur.close()

    def sync_contracts(self, conn, employee_data, test_mode=True):
        """Sync monthly salary and notes to contracts"""
        print("\n" + "="*100)
        print(f"{'TEST MODE' if test_mode else 'PRODUCTION MODE'}: Syncing monthly salaries")
        print("="*100)

        cur = conn.cursor()

        try:
            conn.autocommit = False
            updated = 0
            failed = []

            for emp_name, data in employee_data.items():
                try:
                    # Find contract (only active employees with department assigned)
                    cur.execute("""
                        SELECT c.id, e.name
                        FROM hr_contract c
                        JOIN hr_employee e ON c.employee_id = e.id
                        WHERE UPPER(e.name) = %s
                        AND c.state = 'open'
                        AND e.department_id IS NOT NULL
                        LIMIT 1;
                    """, (emp_name,))

                    result = cur.fetchone()
                    if not result:
                        failed.append({'name': emp_name, 'reason': 'Contract not found'})
                        continue

                    contract_id, actual_name = result

                    # Update monthly salary and notes
                    cur.execute("""
                        UPDATE hr_contract SET
                            ueipab_monthly_salary = %s,
                            ueipab_salary_notes = %s
                        WHERE id = %s;
                    """, (data['usd'], data['notes'], contract_id))

                    updated += 1

                    print(f"  ✓ {actual_name:<35} ${data['usd']:>8,.2f}")
                    print(f"    Notes: {data['notes']}")

                    if test_mode:
                        break

                except Exception as e:
                    failed.append({'name': emp_name, 'reason': str(e)})

            print(f"\n✓ Updated {updated} contracts")

            if failed:
                print(f"\n⚠️  Failed: {len(failed)}")
                for f in failed[:5]:
                    print(f"  - {f['name']}: {f['reason']}")

            # Confirmation
            if test_mode:
                response = input("\nCommit test update? (yes/no): ")
            else:
                response = input(f"\nCommit {updated} updates? (yes/no): ")

            if response.lower() == 'yes':
                conn.commit()
                print("✓ Changes committed")
                return True
            else:
                conn.rollback()
                print("✗ Changes rolled back")
                return False

        except Exception as e:
            print(f"\n✗ Sync failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.autocommit = True
            cur.close()

    def verify_sync(self, conn):
        """Verify sync results"""
        print("\n" + "="*100)
        print("VERIFICATION")
        print("="*100)

        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    e.name,
                    c.ueipab_monthly_salary,
                    c.ueipab_salary_notes
                FROM hr_contract c
                JOIN hr_employee e ON c.employee_id = e.id
                WHERE c.state = 'open'
                  AND c.ueipab_monthly_salary IS NOT NULL
                  AND e.department_id IS NOT NULL
                ORDER BY e.name
                LIMIT 10;
            """)

            results = cur.fetchall()

            print(f"\nSample of synced contracts ({len(results)} shown):")
            for name, salary, notes in results:
                print(f"\n{name}:")
                print(f"  Salary: ${float(salary):,.2f}")
                print(f"  Notes: {notes}")

            # Count totals (only employees with department assigned)
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(ueipab_monthly_salary) as total_salary
                FROM hr_contract c
                JOIN hr_employee e ON c.employee_id = e.id
                WHERE c.state = 'open'
                  AND c.ueipab_monthly_salary IS NOT NULL
                  AND e.department_id IS NOT NULL;
            """)

            total, total_salary = cur.fetchone()

            print(f"\n📊 Summary:")
            print(f"  Total contracts synced: {total}")
            print(f"  Total monthly salary: ${float(total_salary):,.2f}")
            print(f"  Total Aguinaldos (2x): ${float(total_salary) * 2:,.2f}")

        except Exception as e:
            print(f"✗ Verification failed: {e}")
        finally:
            cur.close()

    def run(self, test_mode=True):
        """Main execution"""
        print("\n" + "="*100)
        print("MONTHLY SALARY SYNC FROM SPREADSHEET")
        print("="*100)
        print(f"Spreadsheet: {self.payroll_sheet_id}")
        print(f"Sheet: {self.target_sheet}")
        print(f"Mode: {'TEST (1 employee)' if test_mode else 'PRODUCTION (all employees)'}")
        print("="*100)

        if not self.connect_to_sheet():
            return False

        print("\nFetching spreadsheet data...")
        employee_data, exchange_rate = self.get_salary_data()
        print(f"✓ Loaded {len(employee_data)} employees")

        print("\nConnecting to database...")
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = True  # Set initial autocommit mode
            print(f"✓ Connected to database: {self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}")
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

        try:
            # Create backup
            backup_table = self.create_backup(conn)
            if not backup_table:
                return False

            # Sync contracts
            if not self.sync_contracts(conn, employee_data, test_mode):
                return False

            # Verify
            self.verify_sync(conn)

            print(f"\n✓ Sync completed successfully!")
            print(f"✓ Backup table: {backup_table}")

            return True

        finally:
            conn.close()

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Sync monthly salary from spreadsheet')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (all employees)')
    parser.add_argument('--test', action='store_true', default=True,
                       help='Run in test mode (1 employee) - DEFAULT')

    args = parser.parse_args()
    test_mode = not args.production

    if not test_mode:
        print("\n⚠️  PRODUCTION MODE WARNING")
        print("This will update ALL employee contracts!")
        response = input("Type 'YES' to confirm: ")
        if response != 'YES':
            print("Cancelled")
            sys.exit(0)

    syncer = MonthlySalarySync()
    success = syncer.run(test_mode=test_mode)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
