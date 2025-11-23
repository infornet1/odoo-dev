# -*- coding: utf-8 -*-
import xmlrpc.client
import sys
import time

# Connection details
URL = 'http://web:8069'
DB = 'test-aguinaldos'
USER = 'admin'
PASSWORD = 'admin'

def odoo_rpc_call(method, *args, **kwargs):
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
    uid = common.authenticate(DB, USER, PASSWORD, {{}})
    if not uid:
        print("ERROR: Authentication failed.")
        sys.exit(1)
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(URL))
    return models.execute_kw(DB, uid, PASSWORD, method, *args, **kwargs)

try:
    print(f"Connecting to Odoo database '{DB}' as user '{USER}'...")

    # 1. Uninstall the module
    print("Attempting to uninstall 'ueipab_payroll_enhancements' module...")
    module_id = odoo_rpc_call('ir.module.module', 'search', [[('name', '=', 'ueipab_payroll_enhancements')]])
    if not module_id:
        print("ERROR: Module 'ueipab_payroll_enhancements' not found.")
        sys.exit(1)
    
    odoo_rpc_call('ir.module.module', 'button_immediate_uninstall', [module_id])
    print("Module 'ueipab_payroll_enhancements' uninstalled successfully. Waiting for Odoo to restart...")
    time.sleep(10) # Give Odoo time to process and restart if needed

    # 2. Start Odoo service to ensure it's up before install
    # This might not be strictly necessary if odoo_rpc_call handles restarts but safer.
    # docker-compose up -d is run manually before this script, so we assume it's running.

    # 3. Install the module
    print("Attempting to install 'ueipab_payroll_enhancements' module...")
    module_id = odoo_rpc_call('ir.module.module', 'search', [[('name', '=', 'ueipab_payroll_enhancements')]])
    if not module_id:
        print("ERROR: Module 'ueipab_payroll_enhancements' not found after uninstall (unexpected).")
        sys.exit(1)
    
    odoo_rpc_call('ir.module.module', 'button_immediate_install', [module_id])
    print("Module 'ueipab_payroll_enhancements' installed successfully.")

    print("\nModule reinstallation completed. Please restart your Odoo client (browser refresh) and test.")

except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
    sys.exit(1)
