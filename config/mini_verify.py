# -*- coding: utf-8 -*-
import xmlrpc.client
import sys

# Connection details
URL = 'http://web:8069'
DB = 'test-aguinaldos'
USER = 'admin'
PASSWORD = 'admin'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(URL))
    print(f"Attempting to authenticate to {URL}, DB: {DB}, User: {USER}")
    uid = common.authenticate(DB, USER, PASSWORD, {})
    if uid:
        print(f"Authentication successful. UID: {uid}")
    else:
        print("Authentication failed.")
    sys.exit(0)
except Exception as e:
    print(f"An error occurred during authentication: {e}")
    sys.exit(1)
