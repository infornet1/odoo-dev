#!/usr/bin/env python3
"""
Rebalance Contract Fields with Cesta Ticket Separation

This script implements the Venezuelan labor law requirement to separate
Cesta Ticket as a distinct benefit while maintaining total compensation.

BUSINESS CONTEXT:
- Column M (Cesta Ticket) must be separated as mandatory benefit
- Rebalance 70/25/5 distribution to apply only to (K+L)
- Total compensation remains unchanged: Old (K+L+M) = New (70% + 25% + 5% + M)

REBALANCING FORMULA:
  Fixed Cesta Ticket = $40 USD (monthly)
  New Base = Column K + Column L + (Column M - $40)
  ueipab_salary_base = New Base × 70%
  ueipab_bonus_regular = New Base × 25%
  ueipab_extra_bonus = New Base × 5%
  cesta_ticket_usd = $40 USD (fixed amount)

IMPORTANT SAFETY:
- Creates backup table before any changes
- Transaction-based with rollback capability
- Test mode: Updates 1 employee for validation
- Production mode: Updates all employees
- Verification after updates

Usage:
  # Test mode (1 employee)
  python3 rebalance-cesta-ticket-contracts.py test

  # Production mode (all employees)
  python3 rebalance-cesta-ticket-contracts.py production
"""

import sys
import psycopg2
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class CestaTicketRebalancer:
    def __init__(self, mode='test'):
        self.mode = mode
        self.payroll_sheet_id = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'
        self.credentials_file = '/var/www/dev/bcv/credentials.json'
        self.target_sheet = '31oct2025'
        self.exchange_rate_cell = 'O2'

        # Database configuration
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
            print(f"✗ Failed to connect to spreadsheet: {e}")
            return False

    def connect_to_db(self):
        """Connect to Odoo database"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            print("✓ Connected to Odoo database")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False

    def parse_amount(self, value):
        """Parse Venezuelan number format"""
        if not value or value.strip() == '':
            return 0.0

        value_clean = value.strip()
        dot_count = value_clean.count('.')
        comma_count = value_clean.count(',')

        if dot_count > 0 and comma_count > 0:
            last_dot_pos = value_clean.rfind('.')
            last_comma_pos = value_clean.rfind(',')
            if last_dot_pos > last_comma_pos:
                value_clean = value_clean.replace(',', '')
            else:
                value_clean = value_clean.replace('.', '').replace(',', '.')
        elif dot_count > 1:
            value_clean = value_clean.replace('.', '')
        elif comma_count > 1:
            value_clean = value_clean.replace(',', '')
        elif comma_count == 1 and dot_count == 0:
            value_clean = value_clean.replace(',', '.')

        try:
            return float(value_clean)
        except ValueError:
            return 0.0

    def get_spreadsheet_data(self):
        """Extract K, L, M columns with rebalancing calculations"""
        worksheet = self.spreadsheet.worksheet(self.target_sheet)

        # Get exchange rate
        exchange_rate_value = worksheet.acell(self.exchange_rate_cell).value
        exchange_rate = self.parse_amount(exchange_rate_value)
        print(f"✓ Exchange rate: {exchange_rate:.2f} VEB/USD")

        # Get all data
        all_data = worksheet.get_all_values()

        # Column indices
        col_k_idx = 10  # K: SALARIO MENSUAL MAS BONO
        col_l_idx = 11  # L: OTROS BONOS
        col_m_idx = 12  # M: CESTA TICKET MENSUAL PTR

        employees = []

        for row_idx in range(4, len(all_data)):
            row = all_data[row_idx]

            employee_name = row[3].strip().upper() if len(row) > 3 else ""

            if not employee_name or employee_name in ['NOMBRE Y APELLIDO', 'TOTAL', 'BANCO', 'BANPLUS', 'VENEZUELA', '']:
                continue

            try:
                # Get VEB values
                k_veb = self.parse_amount(row[col_k_idx]) if len(row) > col_k_idx else 0.0
                l_veb = self.parse_amount(row[col_l_idx]) if len(row) > col_l_idx else 0.0
                m_veb = self.parse_amount(row[col_m_idx]) if len(row) > col_m_idx else 0.0

                # Convert to USD
                k_usd = k_veb / exchange_rate if exchange_rate > 0 else 0.0
                l_usd = l_veb / exchange_rate if exchange_rate > 0 else 0.0
                m_usd = m_veb / exchange_rate if exchange_rate > 0 else 0.0

                # Calculate rebalanced values
                # Extract $40 from M as fixed Cesta Ticket
                cesta_fixed = 40.0
                m_remaining = m_usd - cesta_fixed

                # New base = K + L + (M - $40)
                new_base = k_usd + l_usd + m_remaining
                new_salary_base = new_base * 0.70
                new_bonus_regular = new_base * 0.25
                new_extra_bonus = new_base * 0.05
                new_cesta_ticket = cesta_fixed

                # Verification
                old_total = k_usd + l_usd + m_usd
                new_total = new_salary_base + new_bonus_regular + new_extra_bonus + new_cesta_ticket

                # Store original K+L for deduction calculations
                deduction_base = k_usd + l_usd

                employees.append({
                    'name': employee_name,
                    'row': row_idx + 1,
                    'k_usd': k_usd,
                    'l_usd': l_usd,
                    'm_usd': m_usd,
                    'new_base': new_base,
                    'new_salary_base': new_salary_base,
                    'new_bonus_regular': new_bonus_regular,
                    'new_extra_bonus': new_extra_bonus,
                    'new_cesta_ticket': new_cesta_ticket,
                    'deduction_base': deduction_base,
                    'old_total': old_total,
                    'new_total': new_total,
                    'difference': abs(old_total - new_total)
                })
            except Exception as e:
                print(f"⚠️  Error processing {employee_name}: {e}")
                continue

        return employees, exchange_rate

    def create_backup(self):
        """Create backup table with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f'hr_contract_backup_cesta_rebalance_{timestamp}'

        try:
            self.cursor.execute(f"""
                CREATE TABLE {backup_table} AS
                SELECT
                    id,
                    employee_id,
                    ueipab_salary_base,
                    ueipab_bonus_regular,
                    ueipab_extra_bonus,
                    cesta_ticket_usd,
                    ueipab_deduction_base,
                    wage,
                    state
                FROM hr_contract
                WHERE state = 'open';
            """)
            self.conn.commit()

            self.cursor.execute(f"SELECT COUNT(*) FROM {backup_table};")
            count = self.cursor.fetchone()[0]
            print(f"✓ Backup created: {backup_table} ({count} contracts)")
            return backup_table
        except Exception as e:
            print(f"✗ Failed to create backup: {e}")
            self.conn.rollback()
            return None

    def update_contracts(self, employees):
        """Update contract fields with rebalanced values"""
        if self.mode == 'test':
            employees = employees[:1]  # Only first employee in test mode
            print(f"\n⚠️  TEST MODE: Updating only 1 employee for validation")
        else:
            print(f"\n🚀 PRODUCTION MODE: Updating {len(employees)} employees")

        updated = 0
        errors = 0

        for emp in employees:
            try:
                # Find contract by employee name
                self.cursor.execute("""
                    SELECT c.id, e.name, c.ueipab_salary_base, c.ueipab_bonus_regular,
                           c.ueipab_extra_bonus, c.cesta_ticket_usd
                    FROM hr_contract c
                    JOIN hr_employee e ON c.employee_id = e.id
                    WHERE UPPER(e.name) = %s
                    AND c.state = 'open'
                    LIMIT 1;
                """, (emp['name'],))

                result = self.cursor.fetchone()
                if not result:
                    print(f"⚠️  Contract not found: {emp['name']}")
                    errors += 1
                    continue

                contract_id, emp_name, old_salary, old_bonus, old_extra, old_cesta = result

                # Update contract
                self.cursor.execute("""
                    UPDATE hr_contract
                    SET
                        ueipab_salary_base = %s,
                        ueipab_bonus_regular = %s,
                        ueipab_extra_bonus = %s,
                        cesta_ticket_usd = %s,
                        ueipab_deduction_base = %s
                    WHERE id = %s;
                """, (
                    emp['new_salary_base'],
                    emp['new_bonus_regular'],
                    emp['new_extra_bonus'],
                    emp['new_cesta_ticket'],
                    emp['deduction_base'],
                    contract_id
                ))

                print(f"✓ {emp['name']:<30} | Old: K=${emp['k_usd']:>8.2f} M=${emp['m_usd']:>8.2f} | New: 70%=${emp['new_salary_base']:>8.2f} CT=${emp['new_cesta_ticket']:>8.2f} | Diff: ${emp['difference']:.4f}")
                updated += 1

            except Exception as e:
                print(f"✗ Error updating {emp['name']}: {e}")
                errors += 1
                continue

        return updated, errors

    def verify_updates(self):
        """Verify updated contracts"""
        self.cursor.execute("""
            SELECT
                e.name,
                c.ueipab_salary_base,
                c.ueipab_bonus_regular,
                c.ueipab_extra_bonus,
                c.cesta_ticket_usd,
                c.ueipab_deduction_base,
                (c.ueipab_salary_base + c.ueipab_bonus_regular + c.ueipab_extra_bonus + c.cesta_ticket_usd) as total
            FROM hr_contract c
            JOIN hr_employee e ON c.employee_id = e.id
            WHERE c.state = 'open'
            ORDER BY e.name
            LIMIT 5;
        """)

        print(f"\n📋 Sample Verification (First 5 contracts):")
        print(f"  {'Employee':<30} | {'70%':>10} | {'25%':>10} | {'5%':>10} | {'Cesta':>10} | {'DedBase':>10} | {'Total':>10}")
        print(f"  {'-'*30}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

        for row in self.cursor.fetchall():
            name, base, bonus, extra, cesta, ded_base, total = row
            print(f"  {name:<30} | ${base:>9.2f} | ${bonus:>9.2f} | ${extra:>9.2f} | ${cesta:>9.2f} | ${ded_base:>9.2f} | ${total:>9.2f}")

    def run(self):
        """Execute rebalancing process"""
        print("="*100)
        print(f"CESTA TICKET CONTRACT REBALANCING - {self.mode.upper()} MODE")
        print("="*100)

        # Step 1: Connect to systems
        if not self.connect_to_sheet():
            return False
        if not self.connect_to_db():
            return False

        try:
            # Step 2: Get spreadsheet data
            print(f"\n📊 Fetching spreadsheet data...")
            employees, exchange_rate = self.get_spreadsheet_data()
            print(f"✓ Found {len(employees)} employees")

            # Step 3: Verify data
            if not employees:
                print("✗ No employee data found")
                return False

            # Show summary
            total_cesta = sum(e['new_cesta_ticket'] for e in employees)
            max_diff = max(e['difference'] for e in employees)
            print(f"\n📋 Rebalancing Summary:")
            print(f"  Total Employees: {len(employees)}")
            print(f"  Total Cesta Ticket: ${total_cesta:,.2f} USD")
            print(f"  Max Difference: ${max_diff:.6f} USD")

            # Step 4: Create backup
            print(f"\n💾 Creating backup...")
            backup_table = self.create_backup()
            if not backup_table:
                print("✗ Backup failed - ABORTING")
                return False

            # Step 5: Start transaction
            print(f"\n🔄 Starting transaction...")

            # Step 6: Update contracts
            updated, errors = self.update_contracts(employees)

            # Step 7: Verify
            print(f"\n✅ Verification:")
            self.verify_updates()

            # Step 8: Confirm or rollback
            print(f"\n" + "="*100)
            print(f"RESULTS:")
            print(f"  ✅ Updated: {updated} contracts")
            print(f"  ⚠️  Errors: {errors}")
            print(f"  💾 Backup: {backup_table}")

            if self.mode == 'test':
                # Auto-commit in test mode
                self.conn.commit()
                print(f"\n✅ TEST MODE: Changes committed")
                print(f"📋 Next step: Review results, then run in production mode")
            else:
                # Ask for confirmation in production mode
                print(f"\n⚠️  PRODUCTION MODE: Review changes above")
                confirm = input("Commit changes? (yes/no): ")
                if confirm.lower() == 'yes':
                    self.conn.commit()
                    print(f"✅ Changes committed successfully!")
                else:
                    self.conn.rollback()
                    print(f"❌ Changes rolled back")

            return True

        except Exception as e:
            print(f"\n✗ Error during rebalancing: {e}")
            self.conn.rollback()
            return False

        finally:
            if hasattr(self, 'cursor'):
                self.cursor.close()
            if hasattr(self, 'conn'):
                self.conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 rebalance-cesta-ticket-contracts.py [test|production]")
        print("\nModes:")
        print("  test       - Update 1 employee for validation (auto-commit)")
        print("  production - Update all employees (requires confirmation)")
        sys.exit(1)

    mode = sys.argv[1].lower()
    if mode not in ['test', 'production']:
        print("✗ Invalid mode. Use 'test' or 'production'")
        sys.exit(1)

    rebalancer = CestaTicketRebalancer(mode=mode)
    success = rebalancer.run()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
