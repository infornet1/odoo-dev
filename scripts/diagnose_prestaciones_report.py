#!/usr/bin/env python3
"""
Diagnostic script for Prestaciones Interest Report blank PDF issue.

Tests the report generation flow to identify where data is lost.
"""

import sys

# Get Odoo environment
env = globals().get('env')
if not env:
    print("ERROR: This script must be run via odoo shell")
    sys.exit(1)

print("=" * 80)
print("PRESTACIONES INTEREST REPORT - DIAGNOSTIC SCRIPT")
print("=" * 80)

# Test case: SLIP/568 (Josefina Rodriguez)
slip568 = env['hr.payslip'].search([('number', '=', 'SLIP/568')], limit=1)

if not slip568:
    print("\n❌ ERROR: SLIP/568 not found!")
    print("Available liquidation slips:")
    liquidation_slips = env['hr.payslip'].search([
        ('struct_id.name', '=', 'Liquidación Venezolana')
    ], limit=10)
    for slip in liquidation_slips:
        print(f"  - {slip.number}: {slip.employee_id.name}")
    sys.exit(1)

print(f"\n✅ Found test payslip: {slip568.number} ({slip568.employee_id.name})")
print(f"   Contract: {slip568.contract_id.name if slip568.contract_id else 'None'}")
print(f"   State: {slip568.state}")

# Get USD currency
usd = env.ref('base.USD')
print(f"\n✅ Currency: {usd.name} (ID: {usd.id})")

# Test 1: Check if report model exists
print("\n" + "=" * 80)
print("TEST 1: Check AbstractModel Registration")
print("=" * 80)

try:
    report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']
    print("✅ AbstractModel found: report.ueipab_payroll_enhancements.prestaciones_interest")
except KeyError as e:
    print(f"❌ AbstractModel NOT FOUND: {e}")
    print("   This is the CRITICAL ISSUE!")

# Test 2: Call _get_report_values() directly
print("\n" + "=" * 80)
print("TEST 2: Call _get_report_values() Directly")
print("=" * 80)

try:
    report_model = env['report.ueipab_payroll_enhancements.prestaciones_interest']

    # Test with docids as list (like working report)
    print(f"\nCalling _get_report_values(docids=[{slip568.id}], data={{'currency_id': {usd.id}}})")

    result = report_model._get_report_values(
        docids=[slip568.id],
        data={'currency_id': usd.id}
    )

    print("\n✅ _get_report_values() executed successfully!")
    print(f"\nReturned keys: {list(result.keys())}")

    if 'reports' in result:
        print(f"\n✅ 'reports' key found!")
        print(f"   Reports count: {len(result['reports'])}")

        if result['reports']:
            first_report = result['reports'][0]
            print(f"\n   First report keys: {list(first_report.keys())}")

            if 'monthly_data' in first_report:
                monthly_count = len(first_report['monthly_data'])
                print(f"   ✅ Monthly data rows: {monthly_count}")

                if monthly_count > 0:
                    first_month = first_report['monthly_data'][0]
                    print(f"      First month: {first_month.get('month_name')}")
                    print(f"      Prestaciones: ${first_month.get('deposit_amount', 0):.2f}")
                    print(f"      Interest: ${first_month.get('month_interest', 0):.2f}")

            if 'totals' in first_report:
                totals = first_report['totals']
                print(f"\n   ✅ Totals:")
                print(f"      Total Prestaciones: ${totals.get('total_prestaciones', 0):.2f}")
                print(f"      Total Interest: ${totals.get('total_interest', 0):.2f}")
    else:
        print(f"\n❌ 'reports' key NOT FOUND in result!")
        print(f"   This means the template has no data to iterate over!")

except Exception as e:
    print(f"\n❌ ERROR calling _get_report_values(): {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check report action configuration
print("\n" + "=" * 80)
print("TEST 3: Check Report Action Configuration")
print("=" * 80)

try:
    report_action = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')
    print(f"\n✅ Report action found:")
    print(f"   ID: {report_action.id}")
    print(f"   Name: {report_action.name}")
    print(f"   Model: {report_action.model}")
    print(f"   Report Type: {report_action.report_type}")
    print(f"   Report Name: {report_action.report_name}")
    print(f"   Report File: {report_action.report_file}")
except Exception as e:
    print(f"\n❌ Report action NOT FOUND: {e}")

# Test 4: Simulate wizard call (like UI does)
print("\n" + "=" * 80)
print("TEST 4: Simulate Wizard Call Pattern")
print("=" * 80)

try:
    report_action = env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')

    # Test Pattern 1: Using recordset (current non-working code)
    print("\nPattern 1 (CURRENT): report_action(recordset, data=data)")
    try:
        result1 = report_action.report_action(slip568, data={'currency_id': usd.id})
        print(f"   ✅ Returned: {type(result1)}")
        print(f"   Keys: {list(result1.keys()) if isinstance(result1, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # Test Pattern 2: Using docids= keyword with IDs list (working pattern)
    print("\nPattern 2 (WORKING PATTERN): report_action(docids=[id], data=data)")
    try:
        result2 = report_action.report_action(docids=[slip568.id], data={'currency_id': usd.id})
        print(f"   ✅ Returned: {type(result2)}")
        print(f"   Keys: {list(result2.keys()) if isinstance(result2, dict) else 'Not a dict'}")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

except Exception as e:
    print(f"\n❌ ERROR in wizard simulation: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Check template registration
print("\n" + "=" * 80)
print("TEST 5: Check QWeb Template Registration")
print("=" * 80)

try:
    template_id = env.ref('ueipab_payroll_enhancements.prestaciones_interest')
    print(f"\n✅ QWeb template found:")
    print(f"   ID: {template_id.id}")
    print(f"   XML ID: ueipab_payroll_enhancements.prestaciones_interest")
except Exception as e:
    print(f"\n❌ QWeb template NOT FOUND: {e}")
    print("   This would cause blank PDF!")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\nNext steps based on results:")
print("1. If AbstractModel not found → Module not installed/upgraded properly")
print("2. If _get_report_values() works but UI shows blank → Wizard call pattern issue")
print("3. If 'reports' key missing → Template iteration variable mismatch")
print("4. If template not found → XML view not registered")
