#!/usr/bin/env python3
"""
Test if the view inheritance is working correctly
"""
import xmlrpc.client

url = 'http://localhost:8019'
db = 'testing'
username = 'admin'
password = 'admin'

# Authenticate
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"✓ Authenticated as user ID: {uid}")

# Connect to object endpoint
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Get the view for hr.payslip.employees
print("\n" + "="*60)
print("Checking hr.payslip.employees view...")
print("="*60)

# Get fields_view for form
view_data = models.execute_kw(db, uid, password,
    'hr.payslip.employees', 'fields_view_get',
    [], {'view_type': 'form'})

print(f"\nView ID: {view_data.get('view_id')}")
print(f"Model: {view_data.get('model')}")
print(f"\nFields defined:")
for field_name, field_data in sorted(view_data.get('fields', {}).items()):
    if field_name in ['structure_id', 'use_contract_structure', 'employee_ids']:
        print(f"  ✓ {field_name}: {field_data.get('type')} - {field_data.get('string')}")

print(f"\n" + "="*60)
print("Checking if structure_id appears in view arch...")
print("="*60)

arch = view_data.get('arch', '')
if 'structure_id' in arch:
    print("✓ structure_id FOUND in view architecture!")
    # Find the line with structure_id
    for line in arch.split('\n'):
        if 'structure_id' in line or 'Salary Structure' in line:
            print(f"  {line.strip()}")
else:
    print("✗ structure_id NOT FOUND in view architecture!")
    print("\nThis means the view inheritance didn't work.")
    print("Dumping first 500 chars of arch:")
    print(arch[:500])
