#!/usr/bin/env python3
"""Verify contract updates"""

Employee = env['hr.employee']
Contract = env['hr.contract']

print("="*80)
print("VERIFY CONTRACT UPDATES")
print("="*80)

# YOSMARI
yosmari = Employee.search([('name', 'ilike', 'YOSMARI')], limit=1)
if yosmari:
    contract = Contract.search([('employee_id', '=', yosmari.id)], limit=1)
    if contract:
        print(f"\nYOSMARI:")
        print(f"  Contract ID: {contract.id}")
        print(f"  Prepaid Amount: ${contract.ueipab_vacation_prepaid_amount}")
        print(f"  Expected: $88.98")

# VIRGINIA
virginia = Employee.search([('name', 'ilike', 'VIRGINIA VERDE')], limit=1)
if virginia:
    contract = Contract.search([('employee_id', '=', virginia.id)], limit=1)
    if contract:
        print(f"\nVIRGINIA VERDE:")
        print(f"  Contract ID: {contract.id}")
        print(f"  Prepaid Amount: ${contract.ueipab_vacation_prepaid_amount}")
        print(f"  Expected: $256.82")

print("\n" + "="*80)
