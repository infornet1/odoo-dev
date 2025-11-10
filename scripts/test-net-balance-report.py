#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Script: Verify Net Balance appears in payslip after activating VE_NET rule
Creates a test payslip and checks if VE_NET line is computed
"""

import xmlrpc.client
from datetime import datetime, timedelta

# Odoo connection parameters
ODOO_URL = 'http://localhost:8069'
DB_NAME = 'testing'
USERNAME = 'admin'
PASSWORD = 'admin'

def main():
    print("=" * 70)
    print("NET BALANCE REPORT TEST")
    print("=" * 70)

    # Connect to Odoo
    print("\n1. Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})

    if not uid:
        print("❌ Authentication failed!")
        return

    print(f"✅ Connected as user ID: {uid}")

    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # Check if VE_NET rule is active
    print("\n2. Checking VE_NET salary rule status...")
    ve_net_rules = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.salary.rule', 'search_read',
        [[['code', '=', 'VE_NET']]],
        {'fields': ['code', 'name', 'active', 'appears_on_payslip']}
    )

    if ve_net_rules:
        rule = ve_net_rules[0]
        print(f"   Code: {rule['code']}")
        print(f"   Name: {rule['name']}")
        print(f"   Active: {rule['active']}")
        print(f"   Appears on Payslip: {rule['appears_on_payslip']}")

        if not rule['active']:
            print("❌ VE_NET rule is INACTIVE!")
            return
        else:
            print("✅ VE_NET rule is ACTIVE")
    else:
        print("❌ VE_NET rule not found!")
        return

    # Find UEIPAB_VE structure
    print("\n3. Finding UEIPAB_VE payroll structure...")
    structures = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payroll.structure', 'search_read',
        [[['code', '=', 'UEIPAB_VE']]],
        {'fields': ['id', 'name', 'code'], 'limit': 1}
    )

    if not structures:
        print("❌ UEIPAB_VE structure not found!")
        return

    struct_id = structures[0]['id']
    print(f"✅ Found structure: {structures[0]['name']} (ID: {struct_id})")

    # Find a test employee
    print("\n4. Finding test employee...")
    employees = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.employee', 'search_read',
        [[['active', '=', True]]],
        {'fields': ['id', 'name'], 'limit': 1}
    )

    if not employees:
        print("❌ No employees found!")
        return

    employee_id = employees[0]['id']
    employee_name = employees[0]['name']
    print(f"✅ Found employee: {employee_name} (ID: {employee_id})")

    # Create test batch
    print("\n5. Creating test payslip batch...")
    date_from = datetime.now().replace(day=1)
    date_to = (date_from + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    batch_id = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payslip.run', 'create',
        [{
            'name': f'TEST_NET_BALANCE_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'date_start': date_from.strftime('%Y-%m-%d'),
            'date_end': date_to.strftime('%Y-%m-%d'),
        }]
    )
    print(f"✅ Created batch ID: {batch_id}")

    # Create payslip
    print("\n6. Creating test payslip...")
    payslip_id = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payslip', 'create',
        [{
            'employee_id': employee_id,
            'payslip_run_id': batch_id,
            'date_from': date_from.strftime('%Y-%m-%d'),
            'date_to': date_to.strftime('%Y-%m-%d'),
            'struct_id': struct_id,
        }]
    )
    print(f"✅ Created payslip ID: {payslip_id}")

    # Compute payslip
    print("\n7. Computing payslip...")
    models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payslip', 'compute_sheet',
        [[payslip_id]]
    )
    print("✅ Payslip computed")

    # Check payslip lines
    print("\n8. Checking payslip lines...")
    payslip_lines = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payslip.line', 'search_read',
        [[['slip_id', '=', payslip_id]]],
        {'fields': ['code', 'name', 'total', 'appears_on_payslip'], 'order': 'sequence'}
    )

    print(f"\n   Found {len(payslip_lines)} payslip lines:")
    print("   " + "-" * 70)

    ve_net_found = False
    ve_total_ded_found = False
    ve_gross_found = False
    net_amount = 0

    for line in payslip_lines:
        code = line['code']
        name = line['name']
        total = line['total']
        appears = line['appears_on_payslip']

        print(f"   {code:15} | ${total:8.2f} | Appears: {appears}")

        if code == 'VE_NET':
            ve_net_found = True
            net_amount = total
        if code == 'VE_TOTAL_DED':
            ve_total_ded_found = True
        if code == 'VE_GROSS':
            ve_gross_found = True

    print("   " + "-" * 70)

    # Results
    print("\n9. RESULTS:")
    print("   " + "=" * 70)

    if ve_gross_found:
        print("   ✅ VE_GROSS (Gross Total) line FOUND")
    else:
        print("   ❌ VE_GROSS (Gross Total) line MISSING")

    if ve_total_ded_found:
        print("   ✅ VE_TOTAL_DED (Total Deductions) line FOUND")
    else:
        print("   ❌ VE_TOTAL_DED (Total Deductions) line MISSING")

    if ve_net_found:
        print(f"   ✅ VE_NET (Net Salary) line FOUND - Amount: ${net_amount:.2f}")
        print("\n   🎉 SUCCESS! Net Balance will now appear in reports!")
    else:
        print("   ❌ VE_NET (Net Salary) line MISSING")
        print("   ⚠️  Reports will NOT show Net Balance properly")

    print("   " + "=" * 70)

    # Get payslip details
    payslip_data = models.execute_kw(DB_NAME, uid, PASSWORD,
        'hr.payslip', 'read',
        [[payslip_id]],
        {'fields': ['number', 'name', 'employee_id']}
    )[0]

    print(f"\n10. Test Payslip Details:")
    print(f"    Number: {payslip_data.get('number', 'Not assigned yet')}")
    print(f"    Name: {payslip_data['name']}")
    print(f"    Employee: {payslip_data['employee_id'][1]}")
    print(f"    Batch ID: {batch_id}")
    print(f"\n    You can view this payslip in Odoo UI to check the reports!")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    main()
