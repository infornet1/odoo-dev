#!/usr/bin/env python3
"""
Test Aguinaldos Payslip Computation and Confirmation
Tests the updated salary rule formula that matches working pattern.
"""

import sys
import os

# Add Odoo to path
sys.path.append('/usr/lib/python3/dist-packages')
import odoo
from odoo import api, SUPERUSER_ID

def test_payslip_confirmation():
    """Test payslip compute and confirmation"""

    # Initialize Odoo
    odoo.tools.config.parse_config([
        '--database=testing',
        '--db_host=localhost',
        '--db_port=5433',
        '--db_user=odoo',
        '--db_password=odoo8069'
    ])

    with odoo.api.Environment.manage():
        registry = odoo.registry('testing')
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})

            # Find ARCIDES ARZOLA's employee
            employee = env['hr.employee'].search([
                ('name', '=ilike', 'ARCIDES ARZOLA')
            ], limit=1)

            if not employee:
                print("ERROR: Employee ARCIDES ARZOLA not found")
                return False

            print(f"✓ Found employee: {employee.name} (ID: {employee.id})")

            # Get contract
            contract = env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open')
            ], limit=1)

            if not contract:
                print("ERROR: No open contract found")
                return False

            print(f"✓ Found contract: {contract.name} (ID: {contract.id})")
            print(f"  Monthly Salary: ${contract.ueipab_monthly_salary:.2f}")
            print(f"  Expected Aguinaldos: ${contract.ueipab_monthly_salary * 2:.2f}")

            # Find Aguinaldos salary structure
            struct = env['hr.payroll.structure'].search([
                ('code', '=', 'AGUINALDOS_2025')
            ], limit=1)

            if not struct:
                print("ERROR: AGUINALDOS_2025 structure not found")
                return False

            print(f"✓ Found salary structure: {struct.name} (ID: {struct.id})")

            # Find existing payslip or create new one
            payslip = env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('struct_id', '=', struct.id),
                ('state', '=', 'draft')
            ], limit=1)

            if payslip:
                print(f"✓ Found existing draft payslip: {payslip.number} (ID: {payslip.id})")
            else:
                # Create new payslip
                print("Creating new test payslip...")
                payslip = env['hr.payslip'].create({
                    'employee_id': employee.id,
                    'contract_id': contract.id,
                    'struct_id': struct.id,
                    'name': f'Aguinaldos Test - {employee.name}',
                    'date_from': '2025-12-01',
                    'date_to': '2025-12-15',
                })
                print(f"✓ Created payslip: {payslip.number} (ID: {payslip.id})")

            # Test 1: Compute payslip
            print("\n=== TEST 1: Computing payslip ===")
            try:
                payslip.compute_sheet()
                print("✓ Compute successful")

                # Show computed lines
                for line in payslip.line_ids:
                    if line.code == 'AGUINALDOS':
                        print(f"  {line.name}: ${line.total:.2f}")
                        expected = contract.ueipab_monthly_salary * 2
                        if abs(line.total - expected) < 0.01:
                            print(f"  ✓ Amount matches expected: ${expected:.2f}")
                        else:
                            print(f"  ✗ Amount mismatch! Expected: ${expected:.2f}, Got: ${line.total:.2f}")
                            return False

            except Exception as e:
                print(f"✗ Compute failed: {e}")
                import traceback
                traceback.print_exc()
                return False

            # Test 2: Confirm payslip (this is where it was failing before)
            print("\n=== TEST 2: Confirming payslip (CRITICAL TEST) ===")
            try:
                payslip.action_payslip_done()
                print("✓ Confirmation successful!")
                print(f"  Payslip state: {payslip.state}")

                # Check if move was created
                if payslip.move_id:
                    print(f"  ✓ Journal entry created: {payslip.move_id.name}")
                    print(f"    Journal: {payslip.move_id.journal_id.name}")

                    # Show move lines
                    for line in payslip.move_id.line_ids:
                        account_code = line.account_id.code
                        if line.debit > 0:
                            print(f"    Dr {account_code} ({line.account_id.name}): ${line.debit:.2f}")
                        if line.credit > 0:
                            print(f"    Cr {account_code} ({line.account_id.name}): ${line.credit:.2f}")
                else:
                    print("  ⚠ No journal entry created")

                return True

            except Exception as e:
                print(f"✗ Confirmation failed: {e}")
                import traceback
                traceback.print_exc()

                # Show the salary rule that's causing issues
                rule = env['hr.salary.rule'].search([('code', '=', 'AGUINALDOS')], limit=1)
                if rule:
                    print(f"\nSalary Rule Details:")
                    print(f"  Code: {rule.code}")
                    print(f"  Name: {rule.name}")
                    print(f"  Amount Select: {rule.amount_select}")
                    print(f"  Python Code:")
                    print("  ---")
                    print(f"  {rule.amount_python_compute}")
                    print("  ---")

                return False

if __name__ == '__main__':
    print("=== Aguinaldos Payslip Confirmation Test ===\n")
    success = test_payslip_confirmation()

    if success:
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("✗ TESTS FAILED")
        print("="*50)
        sys.exit(1)
