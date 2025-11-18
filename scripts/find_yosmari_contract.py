#!/usr/bin/env python3
"""Find YOSMARI's contract"""

Employee = env['hr.employee']
Contract = env['hr.contract']

yosmari = Employee.search([('name', 'ilike', 'YOSMARI')], limit=1)
if yosmari:
    print(f"Employee: {yosmari.name} (ID: {yosmari.id})")

    contracts = Contract.search([('employee_id', '=', yosmari.id)])
    print(f"\nFound {len(contracts)} contract(s):")

    for c in contracts:
        print(f"\n  Contract ID: {c.id}")
        print(f"  Name: {c.name}")
        print(f"  State: {c.state}")
        print(f"  Date Start: {c.date_start}")
        print(f"  Date End: {c.date_end}")
        print(f"  Structure: {c.struct_id.name if c.struct_id else 'None'}")
