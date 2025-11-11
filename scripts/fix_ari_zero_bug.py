#!/usr/bin/env python3
"""Fix VE_ARI_DED to properly handle 0% ARI rate"""
import psycopg2

NEW_FORMULA = """# Venezuelan ARI (Withholding Income Tax): Variable rate on K (Basic Salary) ONLY
# Rate varies by employee (0%, 1%, 2%, 3%) based on tax bracket - stored in contract
# Contract field stores the BI-WEEKLY rate directly from spreadsheet Column AA
# Spreadsheet applies bi-weekly deductions to each bi-weekly payment

# Get base salary (K component, bi-weekly)
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0

# Get ARI rate from contract (supports 0% for no withholding)
# Default to 1% if field is None/not set (lower tax bracket)
ari_rate_percent = contract.ueipab_ari_withholding_rate if contract.ueipab_ari_withholding_rate is not None else 1.0
ari_rate_biweekly = ari_rate_percent / 100.0

# Calculate deduction - apply bi-weekly rate directly
result = -(salary_base * ari_rate_biweekly)"""

conn = psycopg2.connect(host='localhost', port=5433, database='testing', user='odoo', password='odoo8069')
cur = conn.cursor()

print("Updating VE_ARI_DED formula to handle 0% ARI rate...")
cur.execute("UPDATE hr_salary_rule SET amount_python_compute = %s WHERE code = 'VE_ARI_DED'", (NEW_FORMULA,))
print(f"✓ Updated {cur.rowcount} rule(s)")

conn.commit()
cur.close()
conn.close()
print("\n✓ Formula updated successfully!")
print("\nThe fix: Changed condition from 'if value' to 'if value is not None'")
print("This allows 0% ARI rate to work correctly (0 is falsy in Python)")
