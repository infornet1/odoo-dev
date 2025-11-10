#!/usr/bin/env python3
"""
Install Odoo module via XML-RPC
"""
import xmlrpc.client

# Odoo connection details
url = 'http://localhost:8019'
db = 'testing'
username = 'admin'
password = 'admin'

# Authenticate
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"Authenticated as user ID: {uid}")

# Connect to object endpoint
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Update module list
print("Updating module list...")
models.execute_kw(db, uid, password,
    'ir.module.module', 'update_list', [])

# Search for the module
print("Searching for ueipab_payroll_enhancements module...")
module_ids = models.execute_kw(db, uid, password,
    'ir.module.module', 'search',
    [[['name', '=', 'ueipab_payroll_enhancements']]])

if not module_ids:
    print("ERROR: Module not found!")
    exit(1)

module_id = module_ids[0]
print(f"Found module with ID: {module_id}")

# Get module state
module_data = models.execute_kw(db, uid, password,
    'ir.module.module', 'read',
    [module_id], {'fields': ['name', 'state', 'summary']})

print(f"Module: {module_data[0]['name']}")
print(f"State: {module_data[0]['state']}")
print(f"Summary: {module_data[0]['summary']}")

# Install if not already installed
if module_data[0]['state'] != 'installed':
    print("\nInstalling module...")
    models.execute_kw(db, uid, password,
        'ir.module.module', 'button_immediate_install',
        [module_id])
    print("Module installed successfully!")
else:
    print("\nModule is already installed.")
