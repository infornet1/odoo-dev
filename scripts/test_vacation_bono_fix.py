#!/usr/bin/env python3
"""
Test Vacation & Bono Fix - Verify NET amounts
Date: 2025-11-17
Purpose: Verify that the fix produces correct NET amounts

Expected Results:
- VIRGINIA VERDE: NET $27.26 (was $0.00)
- YOSMARI GONZÁLEZ: NET $15.01 (was $0.00)
"""

from datetime import datetime

print("="*80)
print("TEST VACATION & BONO VACACIONAL FIX")
print("="*80)

Employee = env['hr.employee']
Contract = env['hr.contract']
Payslip = env['hr.payslip']
PayrollStructure = env['hr.payroll.structure']

# Get V2 structure
structure = PayrollStructure.search([('code', '=', 'LIQUID_VE_V2')], limit=1)

def test_employee(name_pattern, expected_net):
    """Test an employee's liquidation calculation"""
    print(f"\n{'='*80}")
    print(f"TEST: {name_pattern}")
    print(f"{'='*80}")

    employee = Employee.search([('name', 'ilike', name_pattern)], limit=1)
    if not employee:
        print(f"❌ Employee not found: {name_pattern}")
        return False

    print(f"Employee: {employee.name} (ID: {employee.id})")

    # Get contract
    contract = Contract.search([('employee_id', '=', employee.id)], limit=1)
    if not contract:
        print(f"❌ No contract found")
        return False

    print(f"Contract: {contract.name} (ID: {contract.id})")
    print(f"Prepaid Amount: ${contract.ueipab_vacation_prepaid_amount}")

    # Find existing liquidation payslip
    payslip = Payslip.search([
        ('employee_id', '=', employee.id),
        ('struct_id', '=', structure.id)
    ], limit=1, order='id desc')

    if not payslip:
        print(f"❌ No liquidation payslip found")
        return False

    print(f"\nPayslip: {payslip.name} (ID: {payslip.id})")
    print(f"Period: {payslip.date_from} to {payslip.date_to}")
    print(f"State: {payslip.state}")

    # Recompute the payslip
    print("\nRecomputing payslip...")
    payslip.action_compute_sheet()

    # Get the rule lines
    print("\n" + "-"*80)
    print("VACATION & BONO BREAKDOWN:")
    print("-"*80)

    vacaciones_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_VACACIONES_V2')
    bono_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_BONO_VACACIONAL_V2')
    prepaid_line = payslip.line_ids.filtered(lambda l: l.code == 'LIQUID_VACATION_PREPAID_V2')

    vacaciones_amt = vacaciones_line.total if vacaciones_line else 0.0
    bono_amt = bono_line.total if bono_line else 0.0
    prepaid_amt = prepaid_line.total if prepaid_line else 0.0
    net_vacation_bono = vacaciones_amt + bono_amt + prepaid_amt

    print(f"VACACIONES_V2:        ${vacaciones_amt:>10.2f}")
    print(f"BONO_VACACIONAL_V2:   ${bono_amt:>10.2f}")
    print(f"VACATION_PREPAID_V2:  ${prepaid_amt:>10.2f}")
    print("-"*80)
    print(f"NET (Vac + Bono):     ${net_vacation_bono:>10.2f}")
    print("-"*80)

    # Check result
    diff = abs(net_vacation_bono - expected_net)
    tolerance = 0.02  # $0.02 tolerance for rounding

    if diff <= tolerance:
        print(f"✅ TEST PASSED! NET ${net_vacation_bono:.2f} matches expected ${expected_net:.2f}")
        return True
    else:
        print(f"❌ TEST FAILED! NET ${net_vacation_bono:.2f} does NOT match expected ${expected_net:.2f}")
        print(f"   Difference: ${diff:.2f}")
        return False

# Run tests
test1_pass = test_employee('VIRGINIA VERDE', 27.26)
test2_pass = test_employee('YOSMARI', 15.01)

# Summary
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)
print(f"VIRGINIA VERDE: {'✅ PASS' if test1_pass else '❌ FAIL'}")
print(f"YOSMARI:        {'✅ PASS' if test2_pass else '❌ FAIL'}")
print("="*80)

if test1_pass and test2_pass:
    print("\n🎉 ALL TESTS PASSED! Fix is working correctly!")
else:
    print("\n⚠️  SOME TESTS FAILED! Review the calculations above.")

print("="*80)
