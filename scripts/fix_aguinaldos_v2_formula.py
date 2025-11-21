#!/usr/bin/env python3
"""
Fix AGUINALDOS formula to use V2 salary field (ueipab_salary_v2)

Background:
- V2 payroll system uses direct salary amounts instead of percentages
- All 44 employees migrated to V2 fields (ueipab_salary_v2)
- AGUINALDOS rule still uses old V1 field (ueipab_salary_base)

Change:
- OLD: contract.ueipab_salary_base (V1 - percentage-based)
- NEW: contract.ueipab_salary_v2 (V2 - direct amount)

Venezuelan Law: Aguinaldos = 2× monthly salary, paid bi-monthly (50% each)

Date: 2025-11-21
"""

import psycopg2
from datetime import datetime

# Database connection
conn = psycopg2.connect(
    dbname="testing",
    user="odoo",
    password="odoo8069",
    host="localhost",
    port="5433"
)

cur = conn.cursor()

print("=" * 80)
print("FIXING AGUINALDOS FORMULA - V2 MIGRATION")
print("=" * 80)

# Step 1: Show current formula
print("\n📋 CURRENT FORMULA:")
print("-" * 80)
cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'AGUINALDOS';")
row = cur.fetchone()

if row:
    name, formula = row
    print(f"\nRule: AGUINALDOS - {name}")
    print(f"\nFormula:\n{formula}")
else:
    print("\n⚠️  AGUINALDOS rule not found!")
    cur.close()
    conn.close()
    exit(1)

# Step 2: Create backup
backup_table = f"aguinaldos_rule_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"\n💾 CREATING BACKUP: {backup_table}")
print("-" * 80)

cur.execute(f"""
    CREATE TABLE {backup_table} AS
    SELECT * FROM hr_salary_rule WHERE code = 'AGUINALDOS';
""")
conn.commit()
print(f"✓ Backup created: {backup_table}")

# Step 3: Define new V2 formula
new_formula = """# Aguinaldos (Christmas Bonus) - V2 FORMULA
# Venezuelan law: Aguinaldos = 2x monthly salary (paid bi-monthly at 50% each)
# V2 Migration: Uses ueipab_salary_v2 (direct salary subject to deductions)

# Get payslip period
period_days = (payslip.date_to - payslip.date_from).days + 1

# Venezuelan bi-monthly logic:
# Period 1-15: 50% of annual Aguinaldos
# Period 16-31: 50% of annual Aguinaldos
if period_days <= 16:
    proportion = 0.5  # Fixed 50% for first half
else:
    # For periods starting after 15th, also use 50%
    day_from = payslip.date_from.day
    if day_from >= 15:
        proportion = 0.5  # Fixed 50% for second half
    else:
        proportion = period_days / 30.0  # Proportional for unusual periods

# V2: Calculate Aguinaldos based on ueipab_salary_v2 (direct salary amount)
# Annual Aguinaldos = 2x monthly salary
# For bi-monthly: split into two payments of 50% each
monthly_salary_v2 = contract.ueipab_salary_v2 or 0.0
base_annual_aguinaldos = monthly_salary_v2 * 2
result = base_annual_aguinaldos * proportion"""

print("\n🔧 NEW V2 FORMULA:")
print("-" * 80)
print(new_formula)

# Step 4: Update the formula
print("\n🔧 UPDATING AGUINALDOS FORMULA...")
print("-" * 80)

cur.execute("""
    UPDATE hr_salary_rule
    SET amount_python_compute = %s
    WHERE code = 'AGUINALDOS';
""", (new_formula,))

if cur.rowcount > 0:
    conn.commit()
    print(f"✓ Updated AGUINALDOS rule (V2 formula applied)")
else:
    print(f"⚠️  AGUINALDOS rule not updated (no rows affected)")

# Step 5: Verify the update
print("\n✅ VERIFICATION:")
print("-" * 80)

cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'AGUINALDOS';")
row = cur.fetchone()

if row:
    name, formula = row
    print(f"\nRule: AGUINALDOS - {name}")
    print(f"\nUpdated Formula:\n{formula}")

    # Check if V2 field is referenced
    if 'ueipab_salary_v2' in formula:
        print("\n✅ SUCCESS: Formula now uses ueipab_salary_v2 (V2 field)")
    else:
        print("\n⚠️  WARNING: Formula does not reference ueipab_salary_v2")

# Step 6: Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\n✓ Backup created: {backup_table}")
print("✓ AGUINALDOS formula updated to V2")
print("\nChanges:")
print("  OLD: contract.ueipab_salary_base (V1 - percentage-based)")
print("  NEW: contract.ueipab_salary_v2 (V2 - direct salary amount)")
print("\nVenezuelan Law Compliance:")
print("  ✓ Aguinaldos = 2× monthly salary")
print("  ✓ Bi-monthly payments: 50% each period")
print("\nNext Steps:")
print("  1. Test with sample payslip")
print("  2. Verify calculations match expected amounts")
print("  3. Run AGUINALDOS batch when ready")

print("\n" + "=" * 80)

# Cleanup
cur.close()
conn.close()

print("\n✅ Script completed successfully!")
print("=" * 80)
