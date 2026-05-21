#!/usr/bin/env python3
"""
Sync Customers Google Sheet → Odoo ir.config_parameter (school.customers_sheet_json)

Reads the Customers tab (col B=parent name, col J=email) from the UEIPAB
Google Sheet and writes a JSON dict {email: name} to the Odoo config parameter
`school.customers_sheet_json` in production (or testing).

Usage:
    python3 scripts/sync_customers_sheet.py           # dry run
    python3 scripts/sync_customers_sheet.py --live    # write to Odoo

Cron note: run daily at ~07:30 VET (11:30 UTC) so it's always fresh before
the workday when Glenda handles most inquiries.
Example cron entry (/etc/cron.d/sync_customers_sheet):
    30 11 * * 1-5  root  TARGET_ENV=production source /root/.odoo_agent_env_prod && \
        python3 /opt/odoo-dev/scripts/sync_customers_sheet.py --live \
        >> /var/log/sync_customers_sheet.log 2>&1
"""

import json
import logging
import os
import sys
import xmlrpc.client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

LIVE = '--live' in sys.argv
TARGET_ENV = os.environ.get('TARGET_ENV', 'testing')

SHEETS_SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
SHEETS_CREDS_PATH = '/opt/odoo-dev/config/google_sheets_credentials.json'
PARAM_KEY = 'school.customers_sheet_json'

ODOO_CONFIGS = {
    'testing': {
        'url':      'http://localhost:8019',
        'db':       'testing',
        'user':     'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url':      os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve'),
        'db':       os.environ.get('ODOO_DB', 'DB_UEIPAB'),
        'user':     os.environ.get('ODOO_USER', 'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}


def load_customers_sheet():
    """Read Customers tab B2:J and return {email_lower: parent_name} dict."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        SHEETS_CREDS_PATH,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'],
    )
    svc = build('sheets', 'v4', credentials=creds)
    resp = svc.spreadsheets().values().get(
        spreadsheetId=SHEETS_SPREADSHEET_ID,
        range='Customers!B2:J',
    ).execute()

    rows = resp.get('values', [])
    data = {}
    skipped = 0
    for row in rows:
        name  = row[0].strip() if len(row) > 0 else ''
        email = row[8].strip().lower() if len(row) > 8 else ''
        if email and name:
            for addr in email.split(';'):
                addr = addr.strip()
                if addr:
                    data[addr] = name
        else:
            skipped += 1

    logger.info("Sheet loaded: %d entries, %d rows skipped (missing email or name)",
                len(data), skipped)
    return data


def odoo_write_param(data):
    """Write JSON dict to ir.config_parameter in Odoo."""
    cfg = ODOO_CONFIGS[TARGET_ENV]
    if TARGET_ENV == 'production' and not cfg.get('password'):
        raise RuntimeError("ODOO_PASSWORD required. Run: source /root/.odoo_agent_env_prod")

    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    db, pwd = cfg['db'], cfg['password']

    json_value = json.dumps(data)

    # Check if param exists
    existing = models.execute_kw(db, uid, pwd,
        'ir.config_parameter', 'search',
        [[('key', '=', PARAM_KEY)]], {'limit': 1})

    if existing:
        models.execute_kw(db, uid, pwd,
            'ir.config_parameter', 'write',
            [existing, {'value': json_value}])
        logger.info("Updated existing param '%s' (%d entries)", PARAM_KEY, len(data))
    else:
        models.execute_kw(db, uid, pwd,
            'ir.config_parameter', 'create',
            [{'key': PARAM_KEY, 'value': json_value}])
        logger.info("Created new param '%s' (%d entries)", PARAM_KEY, len(data))


def main():
    logger.info("=== Sync Customers Sheet → Odoo ===")
    logger.info("  Target:  %s", TARGET_ENV)
    logger.info("  Live:    %s", LIVE)

    try:
        data = load_customers_sheet()
    except Exception as e:
        logger.error("Failed to load sheet: %s", e)
        sys.exit(1)

    if not LIVE:
        logger.info("DRY RUN — would write %d entries to %s", len(data), PARAM_KEY)
        # Show sample
        sample = list(data.items())[:5]
        for email, name in sample:
            logger.info("  Sample: %s → %s", email, name)
        return

    try:
        odoo_write_param(data)
        logger.info("Done.")
    except Exception as e:
        logger.error("Failed to write to Odoo: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()
