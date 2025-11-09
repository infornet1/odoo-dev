#!/usr/bin/env python3
"""
Safe Contract Update Script
Updates Odoo contract custom fields from Google Sheets payroll data
WITH FULL BACKUP AND ROLLBACK CAPABILITY
"""

import sys
import psycopg2
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class ContractUpdater:
    def __init__(self):
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.salary_column = 'K'
        self.exchange_rate_cell = 'O2'

        # Production database connection
        self.db_config = {
            'host': '10.124.0.3',
            'port': 5432,
            'database': 'testing',
            'user': 'odoo',
            'password': 'odoo'  # Update if different
        }

        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

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
        """Get salaries from spreadsheet"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = float(exchange_rate_value.replace(',', '.'))

        # Get all data
        all_data = worksheet.get_all_values()
        salary_col_index = ord(self.salary_column) - 65

        employee_salaries = {}

        for row_idx in range(4, len(all_data)):
            row = all_data[row_idx]

            employee_name = row[3].strip().upper() if len(row) > 3 else ""

            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA']:
                continue

            salary_veb = row[salary_col_index] if len(row) > salary_col_index else "0"

            try:
                # Parse VEB amount
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

                # Calculate distribution (70/25/5)
                base_70 = round(salary_usd * 0.70, 2)
                bonus_25 = round(salary_usd * 0.25, 2)
                extra_5 = round(salary_usd * 0.05, 2)

                employee_salaries[employee_name] = {
                    'veb': salary_veb_float,
                    'usd_total': salary_usd,
                    'base': base_70,
                    'bonus': bonus_25,
                    'extra': extra_5
                }
            except:
                continue

        return employee_salaries, exchange_rate

    def create_backup(self, conn):
        """Create backup of current contract values"""
        print("\n" + "="*80)
        print("CREATING BACKUP")
        print("="*80)

        cur = conn.cursor()

        try:
            # Create backup table
            backup_table = f"contract_salary_backup_{self.backup_timestamp}"

            cur.execute(f"""
                CREATE TABLE {backup_table} AS
                SELECT
                    id,
                    employee_id,
                    ueipab_salary_base,
                    ueipab_bonus_regular,
                    ueipab_extra_bonus,
                    wage,
                    wage_ves,
                    state
                FROM hr_contract
                WHERE state = 'open';
            """)

            conn.commit()

            # Verify backup
            cur.execute(f"SELECT COUNT(*) FROM {backup_table};")
            backup_count = cur.fetchone()[0]

            print(f"✓ Backup table created: {backup_table}")
            print(f"✓ Backed up {backup_count} active contracts")

            self.backup_table_name = backup_table
            return True

        except Exception as e:
            print(f"✗ Backup failed: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()

    def update_contracts(self, conn, employee_salaries, test_mode=True):
        """Update contracts with spreadsheet values"""
        print("\n" + "="*80)
        if test_mode:
            print("TEST MODE: Updating single employee")
        else:
            print("PRODUCTION MODE: Updating all employees")
        print("="*80)

        cur = conn.cursor()

        try:
            # Start transaction
            conn.autocommit = False

            updated_count = 0
            failed_updates = []

            for emp_name, salary_data in employee_salaries.items():
                try:
                    # Find contract
                    cur.execute("""
                        SELECT c.id, e.name
                        FROM hr_contract c
                        JOIN hr_employee e ON c.employee_id = e.id
                        WHERE UPPER(e.name) = %s
                        AND c.state = 'open'
                        LIMIT 1;
                    """, (emp_name,))

                    result = cur.fetchone()

                    if not result:
                        failed_updates.append({
                            'name': emp_name,
                            'reason': 'Contract not found'
                        })
                        continue

                    contract_id, actual_name = result

                    # Update contract
                    cur.execute("""
                        UPDATE hr_contract SET
                            ueipab_salary_base = %s,
                            ueipab_bonus_regular = %s,
                            ueipab_extra_bonus = %s,
                            wage = %s
                        WHERE id = %s;
                    """, (
                        salary_data['base'],
                        salary_data['bonus'],
                        salary_data['extra'],
                        salary_data['usd_total'],
                        contract_id
                    ))

                    updated_count += 1

                    print(f"  ✓ {actual_name:<35} ${salary_data['usd_total']:>8,.2f} "
                          f"(Base: ${salary_data['base']:.2f}, Bonus: ${salary_data['bonus']:.2f}, Extra: ${salary_data['extra']:.2f})")

                    # In test mode, only update first employee
                    if test_mode:
                        break

                except Exception as e:
                    failed_updates.append({
                        'name': emp_name,
                        'reason': str(e)
                    })

            # Show summary
            print(f"\n✓ Successfully updated: {updated_count} contracts")

            if failed_updates:
                print(f"\n⚠️  Failed updates: {len(failed_updates)}")
                for fail in failed_updates:
                    print(f"  - {fail['name']}: {fail['reason']}")

            # Ask for confirmation before commit
            if test_mode:
                print("\n" + "="*80)
                print("TEST COMPLETE - Transaction not committed yet")
                print("="*80)
                response = input("\nCommit this test update? (yes/no): ")
                if response.lower() == 'yes':
                    conn.commit()
                    print("✓ Test update committed")
                    return True
                else:
                    conn.rollback()
                    print("✗ Test update rolled back")
                    return False
            else:
                print("\n" + "="*80)
                print("REVIEW UPDATES ABOVE")
                print("="*80)
                response = input(f"\nCommit {updated_count} contract updates? (yes/no): ")
                if response.lower() == 'yes':
                    conn.commit()
                    print(f"✓ Committed {updated_count} contract updates")
                    return True
                else:
                    conn.rollback()
                    print("✗ Updates rolled back - no changes made")
                    return False

        except Exception as e:
            print(f"\n✗ Update failed: {e}")
            conn.rollback()
            return False
        finally:
            conn.autocommit = True
            cur.close()

    def verify_updates(self, conn, employee_salaries):
        """Verify updates were applied correctly"""
        print("\n" + "="*80)
        print("VERIFYING UPDATES")
        print("="*80)

        cur = conn.cursor()

        try:
            mismatches = []

            for emp_name, expected in employee_salaries.items():
                cur.execute("""
                    SELECT
                        e.name,
                        c.ueipab_salary_base,
                        c.ueipab_bonus_regular,
                        c.ueipab_extra_bonus,
                        c.wage
                    FROM hr_contract c
                    JOIN hr_employee e ON c.employee_id = e.id
                    WHERE UPPER(e.name) = %s
                    AND c.state = 'open'
                    LIMIT 1;
                """, (emp_name,))

                result = cur.fetchone()

                if not result:
                    continue

                name, actual_base, actual_bonus, actual_extra, actual_wage = result

                # Check with small tolerance (0.01)
                if (abs(actual_base - expected['base']) > 0.01 or
                    abs(actual_bonus - expected['bonus']) > 0.01 or
                    abs(actual_extra - expected['extra']) > 0.01):
                    mismatches.append({
                        'name': name,
                        'expected_base': expected['base'],
                        'actual_base': float(actual_base),
                        'expected_bonus': expected['bonus'],
                        'actual_bonus': float(actual_bonus)
                    })

            if mismatches:
                print(f"\n⚠️  Found {len(mismatches)} mismatches:")
                for m in mismatches:
                    print(f"  {m['name']}: Expected base ${m['expected_base']:.2f}, Got ${m['actual_base']:.2f}")
                return False
            else:
                print("✓ All updates verified successfully!")
                return True

        except Exception as e:
            print(f"✗ Verification failed: {e}")
            return False
        finally:
            cur.close()

    def show_rollback_instructions(self):
        """Show how to rollback if needed"""
        print("\n" + "="*80)
        print("ROLLBACK INSTRUCTIONS")
        print("="*80)
        print(f"\nIf you need to rollback these changes, run:")
        print(f"\nUPDATE hr_contract c SET")
        print(f"    ueipab_salary_base = b.ueipab_salary_base,")
        print(f"    ueipab_bonus_regular = b.ueipab_bonus_regular,")
        print(f"    ueipab_extra_bonus = b.ueipab_extra_bonus,")
        print(f"    wage = b.wage")
        print(f"FROM {self.backup_table_name} b")
        print(f"WHERE c.id = b.id;")

    def run(self, test_mode=True):
        """Main execution"""
        print("\n" + "="*80)
        print("CONTRACT UPDATE FROM SPREADSHEET")
        print("="*80)
        print(f"Mode: {'TEST (1 employee)' if test_mode else 'PRODUCTION (all employees)'}")
        print(f"Spreadsheet: {self.payroll_sheet_id}")
        print(f"Sheet: {self.target_sheet}")
        print("="*80)

        # Connect to spreadsheet
        if not self.connect_to_sheet():
            return False

        # Get salary data
        print("\nFetching spreadsheet data...")
        employee_salaries, exchange_rate = self.get_spreadsheet_salaries()
        print(f"✓ Loaded {len(employee_salaries)} employees")
        print(f"✓ Exchange rate: {exchange_rate:.2f} VEB/USD")

        # Connect to database
        print("\nConnecting to production database...")
        try:
            conn = psycopg2.connect(**self.db_config)
            print("✓ Connected to production database")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False

        try:
            # Create backup
            if not self.create_backup(conn):
                return False

            # Update contracts
            if not self.update_contracts(conn, employee_salaries, test_mode):
                return False

            # Verify updates
            if not self.verify_updates(conn, employee_salaries):
                print("\n⚠️  Verification failed! Review updates manually.")

            # Show rollback instructions
            self.show_rollback_instructions()

            return True

        finally:
            conn.close()
            print("\n✓ Database connection closed")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Update employee contracts from spreadsheet')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (updates all employees)')
    parser.add_argument('--test', action='store_true', default=True,
                       help='Run in test mode (updates 1 employee) - DEFAULT')

    args = parser.parse_args()

    # Default to test mode unless explicitly --production
    test_mode = not args.production

    if not test_mode:
        print("\n" + "="*80)
        print("⚠️  PRODUCTION MODE WARNING")
        print("="*80)
        print("This will update ALL employee contracts!")
        print("Make sure you have reviewed test mode results first.")
        response = input("\nAre you sure? (type 'PRODUCTION' to confirm): ")
        if response != 'PRODUCTION':
            print("Cancelled.")
            sys.exit(0)

    updater = ContractUpdater()
    success = updater.run(test_mode=test_mode)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
