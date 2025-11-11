#!/usr/bin/env python3
"""Fix AGUINALDOS formula to use Column K (salary base) instead of total wage"""
import psycopg2

NEW_FORMULA = """# Aguinaldos (Christmas Bonus) - Based on Column K (Salary Base) ONLY
# Venezuelan law: Aguinaldos = 2x monthly K (salary base component)
# For 15-day periods: 50% of annual Aguinaldos

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

# Calculate Aguinaldos based on Column K (Salary Base) ONLY
# Annual Aguinaldos = 2x monthly K (salary base)
# For bi-monthly: split into two payments of 50% each
monthly_k = contract.ueipab_salary_base or 0.0
base_annual_aguinaldos = monthly_k * 2
result = base_annual_aguinaldos * proportion"""

conn = psycopg2.connect(host='localhost', port=5433, database='testing', user='odoo', password='odoo8069')
cur = conn.cursor()

print("=" * 80)
print("FIXING AGUINALDOS FORMULA")
print("=" * 80)

# Get current formula
print("\n📋 CURRENT FORMULA (BEFORE):")
cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'AGUINALDOS';")
result = cur.fetchone()
if result:
    name = result[0]
    if isinstance(name, dict):
        name = name.get('en_US', str(name))
    print(f"\nRule: AGUINALDOS - {name}")
    print("\nUsing: contract.ueipab_monthly_salary (K+M+L total) ❌")
else:
    print("\n⚠️  AGUINALDOS rule not found!")
    cur.close()
    conn.close()
    exit(1)

# Create backup
from datetime import datetime
backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_table = f"aguinaldos_rule_backup_{backup_timestamp}"

print(f"\n📦 Creating backup: {backup_table}")
cur.execute(f"""
    CREATE TABLE {backup_table} AS
    SELECT * FROM hr_salary_rule WHERE code = 'AGUINALDOS';
""")
print(f"✓ Backed up rule")

# Update formula
print("\n🔧 UPDATING AGUINALDOS FORMULA...")
cur.execute("""
    UPDATE hr_salary_rule
    SET amount_python_compute = %s
    WHERE code = 'AGUINALDOS';
""", (NEW_FORMULA,))

if cur.rowcount > 0:
    print(f"✓ Updated AGUINALDOS rule")
else:
    print(f"⚠️  AGUINALDOS rule not updated (no rows affected)")

# Show new formula
print("\n📋 NEW FORMULA (AFTER):")
cur.execute("SELECT name, amount_python_compute FROM hr_salary_rule WHERE code = 'AGUINALDOS';")
result = cur.fetchone()
if result:
    name = result[0]
    if isinstance(name, dict):
        name = name.get('en_US', str(name))
    print(f"\nRule: AGUINALDOS - {name}")
    print("\nNow using: contract.ueipab_salary_base (Column K ONLY) ✓")

# Show expected impact
print("\n" + "=" * 80)
print("EXPECTED IMPACT - FLORMAR HERNANDEZ")
print("=" * 80)

flormar_k = 204.94
flormar_total = 420.97

print(f"\n📊 FLORMAR HERNANDEZ Contract:")
print(f"  K (Salary Base):     ${flormar_k:8.2f}")
print(f"  Total (K+M+L):       ${flormar_total:8.2f}")

print(f"\n❌ OLD Calculation (using total):")
print(f"  Annual Aguinaldos:   ${flormar_total * 2:8.2f}  (Total × 2)")
print(f"  15-day payment (50%): ${flormar_total:8.2f}")

print(f"\n✅ NEW Calculation (using K only):")
print(f"  Annual Aguinaldos:   ${flormar_k * 2:8.2f}  (K × 2)")
print(f"  15-day payment (50%): ${flormar_k:8.2f}")

print(f"\n💰 Difference: ${flormar_total - flormar_k:8.2f} (overpayment corrected)")

# Commit
conn.commit()
print("\n✓ Changes committed!")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("1. Restart Odoo: docker restart odoo-dev-web")
print("2. Recompute SLIP/203 (FLORMAR HERNANDEZ)")
print("3. Verify Aguinaldos = $204.94 (was $420.97)")
print("4. Recompute all Aguinaldos payslips")

print("\n" + "=" * 80)
print("ROLLBACK INSTRUCTIONS (if needed)")
print("=" * 80)
print(f"""
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
FROM {backup_table} b
WHERE r.id = b.id;
""")

cur.close()
conn.close()
