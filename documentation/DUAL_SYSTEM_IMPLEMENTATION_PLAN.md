# Dual System Implementation Plan: Option 3 Enhanced
**Date:** November 9, 2025
**Approach:** Add tracking fields without affecting existing payroll structure
**Enhancement:** Include exchange rate reference in notes for complete audit trail

---

## 🎯 **Solution Overview**

### **Dual Tracking System:**

```
┌─────────────────────────────────────────────────────────────┐
│ EXISTING PAYROLL (Keep Unchanged)                          │
├─────────────────────────────────────────────────────────────┤
│ ueipab_salary_base      → Used for bi-monthly payroll      │
│ ueipab_bonus_regular    → Used for bi-monthly payroll      │
│ ueipab_extra_bonus      → Used for bi-monthly payroll      │
│                                                             │
│ Regular payroll calculations continue unchanged ✅          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ NEW TRACKING FIELDS (For Aguinaldos & Special Bonuses)     │
├─────────────────────────────────────────────────────────────┤
│ ueipab_monthly_salary   → Total from spreadsheet Column K  │
│ ueipab_salary_notes     → Complete audit trail with:       │
│                           - Source sheet & date             │
│                           - Column reference                │
│                           - VEB amount                      │
│                           - Exchange rate used              │
│                                                             │
│ Example:                                                    │
│ $285.39                                                     │
│ "From payroll sheet 31oct2025, Column K (62,748.90 VEB)    │
│  @ 219.87 VEB/USD"                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 **Enhanced Notes Format**

### **Template:**
```
From payroll sheet {SHEET_NAME}, Column K ({VEB_AMOUNT} VEB) @ {EXCHANGE_RATE} VEB/USD
```

### **Real Examples:**

**ARCIDES ARZOLA:**
```
ueipab_monthly_salary: 285.39
ueipab_salary_notes: "From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"
```

**NORKA LA ROSA:**
```
ueipab_monthly_salary: 274.44
ueipab_salary_notes: "From payroll sheet 31oct2025, Column K (60,340.09 VEB) @ 219.87 VEB/USD"
```

**VIRGINIA VERDE:**
```
ueipab_monthly_salary: 134.01
ueipab_salary_notes: "From payroll sheet 31oct2025, Column K (29,463.89 VEB) @ 219.87 VEB/USD"
```

### **Why This Format Is Perfect:**

| Information | Purpose | Benefit |
|-------------|---------|---------|
| **Sheet name** | Source identification | Know which payroll period |
| **Column K** | Data location | Easy to verify in spreadsheet |
| **VEB amount** | Original value | Can recalculate if needed |
| **Exchange rate** | Conversion factor | Full transparency |
| **@ symbol** | Clear separator | Easy to parse |

**Audit Trail Example:**
```
In December 2025, if asked "How was ARCIDES' Aguinaldos calculated?"

Answer: Check contract notes:
"From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"

Verification:
62,748.90 VEB ÷ 219.87 = $285.39 ✅
Aguinaldos: $285.39 × 2 = $570.78 ✅
```

---

## 🗄️ **Database Schema Changes**

### **SQL Implementation:**

```sql
-- Add new tracking fields to hr_contract table
ALTER TABLE hr_contract
ADD COLUMN ueipab_monthly_salary NUMERIC(12,2),
ADD COLUMN ueipab_salary_notes TEXT;

-- Add comments for documentation
COMMENT ON COLUMN hr_contract.ueipab_monthly_salary IS
'Total monthly salary from payroll spreadsheet (Column K in USD).
Used for Aguinaldos, year-end bonuses, and other special calculations.
This field tracks the official salary independent of the 70/25/5 distribution used for regular payroll.';

COMMENT ON COLUMN hr_contract.ueipab_salary_notes IS
'Complete audit trail for ueipab_monthly_salary including:
- Source spreadsheet and date
- Column reference
- Original VEB amount
- Exchange rate used
Format: "From payroll sheet {date}, Column K ({veb} VEB) @ {rate} VEB/USD"';

-- Create index for better query performance
CREATE INDEX idx_hr_contract_monthly_salary
ON hr_contract(ueipab_monthly_salary)
WHERE ueipab_monthly_salary IS NOT NULL;

-- Verify changes
SELECT
    column_name,
    data_type,
    character_maximum_length,
    col_description('hr_contract'::regclass, ordinal_position) as description
FROM information_schema.columns
WHERE table_name = 'hr_contract'
  AND column_name IN ('ueipab_monthly_salary', 'ueipab_salary_notes')
ORDER BY column_name;
```

---

## 🔧 **Odoo Model Extension**

### **File:** `addons/3DVision-C-A/ueipab_aguinaldos/models/hr_contract.py`

```python
# -*- coding: utf-8 -*-
from odoo import fields, models, api

class HrContractUEIPAB(models.Model):
    _inherit = 'hr.contract'

    ueipab_monthly_salary = fields.Monetary(
        string='UEIPAB Monthly Salary',
        help='Total monthly salary from payroll spreadsheet (Column K).\n'
             'Used for Aguinaldos and special bonus calculations.\n'
             'This is independent of the 70/25/5 distribution used for regular payroll.',
        currency_field='currency_id',
        tracking=True,
        groups='hr.group_hr_user',
    )

    ueipab_salary_notes = fields.Text(
        string='Salary Source Notes',
        help='Complete audit trail showing:\n'
             '- Source spreadsheet and date\n'
             '- Column reference\n'
             '- Original VEB amount\n'
             '- Exchange rate used\n\n'
             'Example: "From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"',
        tracking=True,
        groups='hr.group_hr_user',
    )

    @api.constrains('ueipab_monthly_salary')
    def _check_monthly_salary_positive(self):
        """Ensure monthly salary is positive if set"""
        for contract in self:
            if contract.ueipab_monthly_salary and contract.ueipab_monthly_salary < 0:
                raise ValidationError('UEIPAB Monthly Salary must be positive')

    def _get_salary_info_display(self):
        """Helper method to display salary information"""
        self.ensure_one()
        if self.ueipab_monthly_salary:
            info = f"Monthly: ${self.ueipab_monthly_salary:,.2f}"
            if self.ueipab_salary_notes:
                info += f"\n{self.ueipab_salary_notes}"
            return info
        return "Not set"
```

### **File:** `addons/3DVision-C-A/ueipab_aguinaldos/views/hr_contract_views.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="hr_contract_view_form_ueipab" model="ir.ui.view">
        <field name="name">hr.contract.form.ueipab</field>
        <field name="model">hr.contract</field>
        <field name="inherit_id" ref="hr_contract.hr_contract_view_form"/>
        <field name="arch" type="xml">

            <!-- Add new fields in a separate section after wage -->
            <xpath expr="//field[@name='wage']" position="after">
                <group string="UEIPAB Special Calculations (Aguinaldos, Bonuses)"
                       groups="hr.group_hr_user">
                    <field name="ueipab_monthly_salary"
                           widget="monetary"
                           options="{'currency_field': 'currency_id'}"/>
                    <field name="ueipab_salary_notes"
                           placeholder="e.g., From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"/>
                </group>
            </xpath>

        </field>
    </record>
</odoo>
```

### **File:** `addons/3DVision-C-A/ueipab_aguinaldos/__manifest__.py`

```python
# -*- coding: utf-8 -*-
{
    'name': 'UEIPAB Aguinaldos & Special Bonuses',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Track monthly salary for Aguinaldos and special bonuses',
    'description': """
UEIPAB Aguinaldos & Special Bonuses
====================================

Adds tracking fields to employee contracts for special calculations:

Features:
---------
* Monthly salary tracking from payroll spreadsheet
* Complete audit trail with exchange rate information
* Independent from regular 70/25/5 payroll distribution
* Used for Aguinaldos (year-end bonus) calculations
* Used for other special bonuses and benefits

Technical:
----------
* Adds ueipab_monthly_salary field (Monetary)
* Adds ueipab_salary_notes field (Text) for audit trail
* Extends hr.contract model
* Compatible with existing UEIPAB Venezuelan Payroll structure
    """,
    'author': '3DVision C.A.',
    'website': 'https://www.3dvision.com.ve',
    'depends': ['hr_contract', 'hr_payroll_community'],
    'data': [
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

---

## 🔄 **Sync Script with Enhanced Notes**

### **File:** `scripts/sync-monthly-salary-from-spreadsheet.py`

```python
#!/usr/bin/env python3
"""
Sync Monthly Salary from Spreadsheet to Odoo Contracts
WITH ENHANCED AUDIT TRAIL NOTES
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

        # Production database
        self.db_config = {
            'host': '10.124.0.3',
            'port': 5432,
            'database': 'testing',
            'user': 'odoo',
            'password': 'odoo'
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

        print(f"✓ Exchange rate: {exchange_rate:.2f} VEB/USD")

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

                # Create enhanced notes with all audit information
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
        """Create backup before updating"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_table = f"contract_monthly_salary_backup_{timestamp}"

        cur = conn.cursor()
        try:
            cur.execute(f"""
                CREATE TABLE {backup_table} AS
                SELECT
                    id,
                    employee_id,
                    ueipab_monthly_salary,
                    ueipab_salary_notes
                FROM hr_contract
                WHERE state = 'open';
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
                ORDER BY e.name
                LIMIT 10;
            """)

            results = cur.fetchall()

            print(f"\nSample of synced contracts ({len(results)} shown):")
            for name, salary, notes in results:
                print(f"\n{name}:")
                print(f"  Salary: ${float(salary):,.2f}")
                print(f"  Notes: {notes}")

            # Count totals
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(ueipab_monthly_salary) as total_salary
                FROM hr_contract
                WHERE state = 'open'
                  AND ueipab_monthly_salary IS NOT NULL;
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

        if not self.connect_to_sheet():
            return False

        print("\nFetching spreadsheet data...")
        employee_data, exchange_rate = self.get_salary_data()
        print(f"✓ Loaded {len(employee_data)} employees")

        print("\nConnecting to database...")
        try:
            conn = psycopg2.connect(**self.db_config)
            print("✓ Connected to production database")
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
        response = input("Update ALL employees? (type 'YES'): ")
        if response != 'YES':
            print("Cancelled")
            sys.exit(0)

    syncer = MonthlySalarySync()
    success = syncer.run(test_mode=test_mode)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

---

## 📋 **Implementation Checklist**

### **Phase 1: Database Preparation**
- [ ] Connect to production database (10.124.0.3)
- [ ] Run ALTER TABLE statements to add new fields
- [ ] Verify columns created successfully
- [ ] Create index for performance
- [ ] Test connection and permissions

### **Phase 2: Initial Sync (Test Mode)**
- [ ] Run sync script in test mode (1 employee)
- [ ] Verify field values populated correctly
- [ ] Check notes format is correct
- [ ] Confirm no impact on existing payroll fields
- [ ] Review backup table created

### **Phase 3: Full Sync (Production Mode)**
- [ ] Review test results with stakeholders
- [ ] Run sync script in production mode (all 45 employees)
- [ ] Verify all contracts updated
- [ ] Confirm total matches spreadsheet ($6,376.70)
- [ ] Document completion

### **Phase 4: Odoo Module (Optional - for UI)**
- [ ] Create ueipab_aguinaldos addon folder
- [ ] Add model extension (hr_contract.py)
- [ ] Add view extension (hr_contract_views.xml)
- [ ] Create __manifest__.py
- [ ] Install module in Odoo
- [ ] Test UI display

### **Phase 5: Aguinaldos Salary Rule**
- [ ] Create Aguinaldos salary structure
- [ ] Add salary rule using ueipab_monthly_salary field
- [ ] Test with sample payslip
- [ ] Verify calculation: salary × 2
- [ ] Deploy for December

---

## 🎯 **Usage Examples**

### **Regular Payroll (Unchanged)**
```python
# Bi-monthly payslip (Oct 16-31)
VE_SALARY_70:  contract.ueipab_salary_base * 0.5    # $102.25
VE_BONUS_25:   contract.ueipab_bonus_regular * 0.5  # $36.52
VE_EXTRA_5:    contract.ueipab_extra_bonus * 0.5    # $7.31
Total: $146.08
```

### **Aguinaldos Calculation (New)**
```python
# December Aguinaldos
AGUINALDOS: contract.ueipab_monthly_salary * 2  # $570.78

# Source verification from notes:
"From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"
Calculation: 62,748.90 ÷ 219.87 = $285.39
Aguinaldos: $285.39 × 2 = $570.78 ✅
```

---

## ✅ **Benefits Summary**

| Benefit | Description |
|---------|-------------|
| **Complete Audit Trail** | Every field includes source, amount, and rate |
| **Zero Risk** | Existing payroll completely untouched |
| **Transparency** | Anyone can verify calculations |
| **Flexibility** | Different bases for different purposes |
| **Regulatory Compliance** | Full documentation for audits |
| **Easy Maintenance** | Clear process to update from spreadsheet |

---

## 📞 **Support Commands**

### **Check Field Status**
```sql
SELECT
    e.name,
    c.ueipab_monthly_salary,
    c.ueipab_salary_notes
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
ORDER BY e.name;
```

### **Verify Total Aguinaldos**
```sql
SELECT
    SUM(ueipab_monthly_salary) as monthly_total,
    SUM(ueipab_monthly_salary) * 2 as aguinaldos_total
FROM hr_contract
WHERE state = 'open'
  AND ueipab_monthly_salary IS NOT NULL;
```

### **Find Missing Syncs**
```sql
SELECT e.name
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
  AND c.ueipab_monthly_salary IS NULL;
```

---

**Ready for your review and approval!**

**Next Step:** Run database schema changes in production to add the two new fields.

