#!/usr/bin/env python3
"""
Compute payslip #81 (SLIP/083) directly via Odoo RPC
"""
import xmlrpc.client

# Connection parameters
url = 'http://localhost:8019'
db = 'testing'
username = 'admin'
password = 'admin'  # Update if different

try:
    # Connect to Odoo
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})

    if not uid:
        print("✗ Authentication failed. Check username/password.")
        exit(1)

    print(f"✓ Connected to Odoo as user ID: {uid}")

    # Get models proxy
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    # Get payslip info
    payslip_id = 81
    payslip = models.execute_kw(db, uid, password,
        'hr.payslip', 'read',
        [[payslip_id]],
        {'fields': ['number', 'employee_id', 'struct_id', 'state']}
    )

    if not payslip:
        print(f"✗ Payslip #{payslip_id} not found")
        exit(1)

    payslip = payslip[0]
    print(f"\nPayslip Information:")
    print(f"  Number: {payslip['number']}")
    print(f"  Employee: {payslip['employee_id'][1]}")
    print(f"  Structure: {payslip['struct_id'][1]}")
    print(f"  State before: {payslip['state']}")

    # Compute the payslip
    print(f"\nComputing payslip...")
    result = models.execute_kw(db, uid, password,
        'hr.payslip', 'compute_sheet',
        [[payslip_id]]
    )

    print(f"✓ Compute result: {result}")

    # Get salary lines
    line_ids = models.execute_kw(db, uid, password,
        'hr.payslip', 'read',
        [[payslip_id]],
        {'fields': ['line_ids']}
    )[0]['line_ids']

    if line_ids:
        lines = models.execute_kw(db, uid, password,
            'hr.payslip.line', 'read',
            [line_ids],
            {'fields': ['code', 'name', 'total']}
        )

        print(f"\n✓ Salary Lines ({len(lines)}):")
        for line in lines:
            print(f"  {line['code']}: {line['name']} = ${line['total']:,.2f}")
    else:
        print("\n⚠️  No salary lines generated")

    # Check final state
    final_state = models.execute_kw(db, uid, password,
        'hr.payslip', 'read',
        [[payslip_id]],
        {'fields': ['state']}
    )[0]['state']

    print(f"\n✓ State after compute: {final_state}")
    print(f"\n✓ Payslip computed successfully!")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
