#!/usr/bin/env python3
"""
Test Aguinaldos formula validation without running full Odoo
"""

import psycopg2
from decimal import Decimal

# Database connection
conn = psycopg2.connect(
    host='localhost',
    port=5433,
    database='testing',
    user='odoo',
    password='odoo8069'
)

cur = conn.cursor()

print("=== Aguinaldos Formula Validation Test ===\n")

# Get the salary rule
cur.execute("""
    SELECT id, code, name, amount_python_compute
    FROM hr_salary_rule
    WHERE code = 'AGUINALDOS'
""")

rule = cur.fetchone()
if not rule:
    print("ERROR: AGUINALDOS rule not found")
    exit(1)

rule_id, rule_code, rule_name, python_code = rule
print(f"Salary Rule: {rule_name} ({rule_code})")
print(f"ID: {rule_id}")
print(f"\nPython Code:")
print("---")
print(python_code)
print("---\n")

# Get ARCIDES ARZOLA's contract
cur.execute("""
    SELECT c.id, c.name, c.ueipab_monthly_salary, e.name as employee_name
    FROM hr_contract c
    JOIN hr_employee e ON c.employee_id = e.id
    WHERE UPPER(e.name) = 'ARCIDES ARZOLA'
    AND c.state = 'open'
    LIMIT 1
""")

contract_data = cur.fetchone()
if not contract_data:
    print("ERROR: Contract not found")
    exit(1)

contract_id, contract_name, monthly_salary, employee_name = contract_data
print(f"Testing with: {employee_name}")
print(f"Contract: {contract_name} (ID: {contract_id})")
print(f"Monthly Salary: ${monthly_salary:.2f}")
print(f"Expected Result: ${monthly_salary * 2:.2f}\n")

# Create a mock contract object for testing
class MockContract:
    def __init__(self, ueipab_monthly_salary):
        self.ueipab_monthly_salary = ueipab_monthly_salary or 0.0

class MockPayslip:
    def __init__(self, date_from, date_to):
        from datetime import datetime
        self.date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        self.date_to = datetime.strptime(date_to, '%Y-%m-%d').date()

# Test the formula
print("=== Testing Formula Execution ===")
try:
    contract = MockContract(float(monthly_salary) if monthly_salary else 0.0)
    payslip = MockPayslip('2025-12-01', '2025-12-15')

    # Create safe evaluation context (similar to Odoo's safe_eval)
    local_dict = {
        'contract': contract,
        'payslip': payslip,
        'result': 0.0
    }

    # Execute the formula
    exec(python_code, {}, local_dict)
    result = local_dict['result']

    expected = float(monthly_salary) * 2 if monthly_salary else 0.0

    print(f"✓ Formula executed successfully")
    print(f"  Calculated Result: ${result:.2f}")
    print(f"  Expected Result: ${expected:.2f}")

    if abs(result - expected) < 0.01:
        print(f"  ✓ Result matches expected value")
        print("\n" + "="*50)
        print("✓ FORMULA VALIDATION PASSED")
        print("="*50)
    else:
        print(f"  ✗ Result mismatch!")
        print("\n" + "="*50)
        print("✗ FORMULA VALIDATION FAILED")
        print("="*50)
        exit(1)

except Exception as e:
    print(f"✗ Formula execution failed: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "="*50)
    print("✗ FORMULA VALIDATION FAILED")
    print("="*50)
    exit(1)

cur.close()
conn.close()

print("\nFormula validation passed. The rule should work in Odoo.")
print("Please test payslip confirmation in Odoo UI to verify.")
