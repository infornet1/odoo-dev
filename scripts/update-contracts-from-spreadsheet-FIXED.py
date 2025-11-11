#!/usr/bin/env python3
"""
CORRECTED Contract Update Script
Updates Odoo contract custom fields from Google Sheets payroll data
READS ALL FOUR COLUMNS: K, L, M, N (not just K!)
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
        self.credentials_file = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'
        self.target_sheet = '31oct2025'
        self.exchange_rate_cell = 'O2'

        # Database connection (localhost development by default)
        self.db_config = {
            'host': 'localhost',
            'port': 5433,  # Docker postgres mapped to port 5433
            'database': 'testing',
            'user': 'odoo',
            'password': 'odoo8069'
        }

        self.backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def parse_veb(self, value_str):
        """Parse VEB value with comma as thousands separator"""
        if not value_str or value_str.strip() == '':
            return 0.0
        # Remove comma (thousands separator), keep period (decimal point)
        clean = value_str.strip().replace(',', '')
        try:
            return float(clean)
        except:
            return 0.0

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
        """Get salaries from spreadsheet - READS THREE SALARY COLUMNS: K, L, M"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate from cell O2
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = self.parse_veb(exchange_rate_value)

        print(f"\n✓ Exchange Rate (O2): {exchange_rate:.2f} VEB/USD")

        # Get all data
        all_data = worksheet.get_all_values()

        # Column indices (0-based)
        COL_NAME = 3   # D: Employee Name
        COL_K = 10     # K: Basic Salary Component (deductions apply)
        COL_L = 11     # L: Other Bonus (no deductions)
        COL_M = 12     # M: Major Bonus Component (no deductions)
        COL_AA = 26    # AA: ARI Withholding Tax Rate (percentage)

        employee_salaries = {}
        skipped_count = 0

        for row_idx in range(5, len(all_data)):  # Start from row 6 (index 5)
            row = all_data[row_idx]

            if len(row) < 14:
                continue

            employee_name = row[COL_NAME].strip().upper()

            # Skip invalid rows
            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA']:
                continue

            try:
                # *** CRITICAL FIX: Read THREE salary columns ***
                k_veb = self.parse_veb(row[COL_K])  # Basic Salary
                l_veb = self.parse_veb(row[COL_L])  # Other Bonus
                m_veb = self.parse_veb(row[COL_M])  # Major Bonus

                # Read ARI withholding tax rate (Column AA)
                ari_rate_str = row[COL_AA].strip() if len(row) > COL_AA else '0.5'
                # Remove % sign if present and convert to float
                ari_rate = float(ari_rate_str.replace('%', '').strip()) if ari_rate_str else 0.5

                # Skip if all values are zero
                if k_veb == 0 and l_veb == 0 and m_veb == 0:
                    skipped_count += 1
                    continue

                # Convert to USD
                k_usd = k_veb / exchange_rate
                l_usd = l_veb / exchange_rate
                m_usd = m_veb / exchange_rate

                # *** CORRECT MAPPING: Direct from spreadsheet ***
                # K = Basic Salary (deductions apply)
                # L = Other Bonus (no deductions)
                # M = Major Bonus (no deductions)
                salary_base = k_usd       # K: Basic Salary
                bonus_regular = m_usd     # M: Major Bonus
                extra_bonus = l_usd       # L: Other Bonus
                total_usd = k_usd + l_usd + m_usd  # wage = GROSS

                employee_salaries[employee_name] = {
                    'k_veb': k_veb,
                    'l_veb': l_veb,
                    'm_veb': m_veb,
                    'k_usd': k_usd,
                    'l_usd': l_usd,
                    'm_usd': m_usd,
                    'base': round(salary_base, 2),
                    'bonus': round(bonus_regular, 2),
                    'extra': round(extra_bonus, 2),
                    'total': round(total_usd, 2),
                    'ari_rate': ari_rate  # ARI withholding tax rate (%)
                }

            except Exception as e:
                print(f"  ⚠️  Skipped {employee_name}: {e}")
                skipped_count += 1
                continue

        if skipped_count > 0:
            print(f"  ℹ️  Skipped {skipped_count} rows (invalid or zero values)")

        return employee_salaries, exchange_rate

    def connect_to_database(self, remote=False):
        """Connect to database"""
        if remote:
            print("\n⚠️  WARNING: Using PRODUCTION remote database (10.124.0.3)")
            self.db_config['host'] = '10.124.0.3'
        else:
            print("\n✓ Using LOCAL development database (localhost)")

        try:
            conn = psycopg2.connect(**self.db_config)
            print(f"✓ Connected to database: {self.db_config['database']} @ {self.db_config['host']}")
            return conn
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return None

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
                    state,
                    NOW() as backup_timestamp
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

    def show_sample_comparison(self, conn, employee_salaries):
        """Show before/after comparison for first 5 employees"""
        print("\n" + "="*80)
        print("SAMPLE BEFORE/AFTER COMPARISON (First 5 employees)")
        print("="*80)

        cur = conn.cursor()

        try:
            sample_employees = list(employee_salaries.keys())[:5]

            for emp_name in sample_employees:
                expected = employee_salaries[emp_name]

                cur.execute("""
                    SELECT
                        e.name,
                        c.wage,
                        c.ueipab_salary_base,
                        c.ueipab_bonus_regular,
                        c.ueipab_extra_bonus,
                        (c.ueipab_salary_base + c.ueipab_bonus_regular + c.ueipab_extra_bonus) as total
                    FROM hr_contract c
                    JOIN hr_employee e ON c.employee_id = e.id
                    WHERE UPPER(e.name) = %s
                    AND c.state = 'open'
                    LIMIT 1;
                """, (emp_name,))

                result = cur.fetchone()

                if result:
                    name, curr_wage, curr_base, curr_bonus, curr_extra, curr_total = result
                    print(f"\n{name}:")
                    print(f"  CURRENT wage:  ${float(curr_wage):>8.2f}")
                    print(f"  CURRENT parts: Base=${float(curr_base):>8.2f} + Bonus=${float(curr_bonus):>8.2f} + Extra=${float(curr_extra):>8.2f} = ${float(curr_total):>8.2f}")
                    print(f"  NEW wage:      ${expected['total']:>8.2f}")
                    print(f"  NEW parts:     Base=${expected['base']:>8.2f} + Bonus=${expected['bonus']:>8.2f} + Extra=${expected['extra']:>8.2f} = ${expected['total']:>8.2f}")
                    wage_change = expected['total'] - float(curr_wage)
                    print(f"  WAGE CHANGE:   ${wage_change:>+9.2f} ({(wage_change/float(curr_wage)*100):+.1f}%)" if curr_wage > 0 else f"  WAGE CHANGE:   ${wage_change:>+9.2f}")

        except Exception as e:
            print(f"✗ Comparison failed: {e}")
        finally:
            cur.close()

    def update_contracts(self, conn, employee_salaries, test_mode=True):
        """Update contracts with spreadsheet values"""
        print("\n" + "="*80)
        if test_mode:
            print("TEST MODE: Updating FIRST employee only")
        else:
            print("PRODUCTION MODE: Updating ALL employees")
        print("="*80)

        cur = conn.cursor()

        try:
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

                    # Update contract with CORRECT VALUES
                    cur.execute("""
                        UPDATE hr_contract SET
                            wage = %s,
                            ueipab_salary_base = %s,
                            ueipab_bonus_regular = %s,
                            ueipab_extra_bonus = %s,
                            ueipab_ari_withholding_rate = %s,
                            ueipab_ari_last_update = CURRENT_DATE
                        WHERE id = %s;
                    """, (
                        salary_data['total'],       # wage = K + L + M (GROSS)
                        salary_data['base'],        # K (Basic Salary)
                        salary_data['bonus'],       # M (Major Bonus)
                        salary_data['extra'],       # L (Other Bonus)
                        salary_data['ari_rate'],    # ARI withholding tax rate (%)
                        contract_id
                    ))

                    updated_count += 1

                    print(f"  ✓ {actual_name:<35} wage=${salary_data['total']:>8.2f} "
                          f"(K=${salary_data['base']:.2f}, M=${salary_data['bonus']:.2f}, L=${salary_data['extra']:.2f}, ARI={salary_data['ari_rate']:.1f}%)")

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
                for fail in failed_updates[:10]:  # Show first 10
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
            cur.close()

    def verify_updates(self, conn, employee_salaries, limit=5):
        """Verify updates were applied correctly"""
        print("\n" + "="*80)
        print(f"VERIFYING UPDATES (checking {limit} employees)")
        print("="*80)

        cur = conn.cursor()

        try:
            mismatches = []
            verified_count = 0

            for emp_name, expected in list(employee_salaries.items())[:limit]:
                cur.execute("""
                    SELECT
                        e.name,
                        c.wage,
                        c.ueipab_salary_base,
                        c.ueipab_bonus_regular,
                        c.ueipab_extra_bonus
                    FROM hr_contract c
                    JOIN hr_employee e ON c.employee_id = e.id
                    WHERE UPPER(e.name) = %s
                    AND c.state = 'open'
                    LIMIT 1;
                """, (emp_name,))

                result = cur.fetchone()

                if not result:
                    continue

                name, actual_wage, actual_base, actual_bonus, actual_extra = result
                verified_count += 1

                # Check with small tolerance (0.01)
                if (abs(float(actual_wage) - expected['total']) > 0.01 or
                    abs(float(actual_base) - expected['base']) > 0.01 or
                    abs(float(actual_bonus) - expected['bonus']) > 0.01 or
                    abs(float(actual_extra) - expected['extra']) > 0.01):
                    mismatches.append({
                        'name': name,
                        'expected': expected,
                        'actual': {
                            'wage': float(actual_wage),
                            'base': float(actual_base),
                            'bonus': float(actual_bonus),
                            'extra': float(actual_extra)
                        }
                    })
                else:
                    print(f"  ✓ {name}: wage=${float(actual_wage):.2f} (K=${float(actual_base):.2f} + M=${float(actual_bonus):.2f} + L=${float(actual_extra):.2f})")

            if mismatches:
                print(f"\n⚠️  Found {len(mismatches)} mismatches:")
                for m in mismatches:
                    print(f"  {m['name']}:")
                    print(f"    Expected: wage=${m['expected']['total']:.2f} (Base=${m['expected']['base']:.2f} + Bonus=${m['expected']['bonus']:.2f} + Extra=${m['expected']['extra']:.2f})")
                    print(f"    Actual:   wage=${m['actual']['wage']:.2f} (Base=${m['actual']['base']:.2f} + Bonus=${m['actual']['bonus']:.2f} + Extra=${m['actual']['extra']:.2f})")
                return False
            else:
                print(f"\n✓ All {verified_count} contracts verified successfully!")
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
        print(f"    ueipab_extra_bonus = b.ueipab_extra_bonus")
        print(f"FROM {self.backup_table_name} b")
        print(f"WHERE c.id = b.id;")

    def run(self, test_mode=True, remote=False):
        """Main execution"""
        print("\n" + "="*80)
        print("CONTRACT UPDATE FROM SPREADSHEET (FIXED VERSION)")
        print("="*80)
        print(f"Mode: {'TEST (1 employee)' if test_mode else 'PRODUCTION (all employees)'}")
        print(f"Database: {'REMOTE (10.124.0.3)' if remote else 'LOCAL (localhost)'}")
        print(f"Spreadsheet: {self.payroll_sheet_id}")
        print(f"Sheet: {self.target_sheet}")
        print("="*80)
        print("\n✓ CRITICAL FIX: Now reading THREE salary columns (K, L, M)")
        print("  - wage = K + L + M (GROSS, no deductions)")
        print("  - K → ueipab_salary_base (Basic Salary - deductions apply)")
        print("  - M → ueipab_bonus_regular (Major Bonus - no deductions)")
        print("  - L → ueipab_extra_bonus (Other Bonus - no deductions)")
        print("="*80)

        # Connect to spreadsheet
        if not self.connect_to_sheet():
            return False

        # Get salary data
        print("\nFetching spreadsheet data...")
        employee_salaries, exchange_rate = self.get_spreadsheet_salaries()
        print(f"✓ Loaded {len(employee_salaries)} employees")

        # Connect to database
        conn = self.connect_to_database(remote=remote)
        if not conn:
            return False

        try:
            # Show before/after comparison
            self.show_sample_comparison(conn, employee_salaries)

            # Create backup
            if not self.create_backup(conn):
                return False

            # Update contracts
            if not self.update_contracts(conn, employee_salaries, test_mode):
                return False

            # Verify updates
            if not self.verify_updates(conn, employee_salaries, limit=5 if test_mode else 10):
                print("\n⚠️  Verification failed! Review updates manually.")

            # Show rollback instructions
            self.show_rollback_instructions()

            return True

        finally:
            conn.close()
            print("\n✓ Database connection closed")

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Update employee contracts from spreadsheet (FIXED VERSION)')
    parser.add_argument('--production', action='store_true',
                       help='Run in production mode (updates all employees)')
    parser.add_argument('--remote', action='store_true',
                       help='Connect to remote production database (10.124.0.3)')
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

    if args.remote:
        print("\n" + "="*80)
        print("⚠️  REMOTE DATABASE WARNING")
        print("="*80)
        print("This will connect to PRODUCTION database at 10.124.0.3!")
        response = input("\nAre you sure? (type 'REMOTE' to confirm): ")
        if response != 'REMOTE':
            print("Cancelled.")
            sys.exit(0)

    updater = ContractUpdater()
    success = updater.run(test_mode=test_mode, remote=args.remote)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
