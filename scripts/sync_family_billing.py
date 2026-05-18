"""
Sync Customers spreadsheet → school.family_billing_json in production ir.config_parameter.

Usage:
    python3 scripts/sync_family_billing.py          # dry-run (prints sample)
    python3 scripts/sync_family_billing.py --live   # write to production Odoo

Cron: /etc/cron.d/sync_family_billing — weekdays 07:30 VET
    30 11 * * 1-5 root python3 /opt/odoo-dev/scripts/sync_family_billing.py --live \
        >> /var/log/sync_family_billing.log 2>&1
"""
import os, sys, json, logging, argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
PARAM_KEY      = 'school.family_billing_json'
CREDS_PATH     = '/opt/odoo-dev/config/google_sheets_credentials.json'
PROD_CFG_PATH  = '/opt/odoo-dev/config/production.json'


def _load_sheet():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_service_account_file(
        CREDS_PATH,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    result = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute()
    return result.get('values', [])


def _normalize_phone(raw):
    """Strip country code and leading zeros → 10-digit Venezuelan format."""
    p = (raw or '').strip().replace(' ', '').replace('-', '').replace('+', '')
    if p.startswith('58') and len(p) > 10:
        p = p[2:]
    p = p.lstrip('0')
    return p[-10:] if len(p) > 10 else p


def _parse_rows(rows):
    # rows[0] = header row
    families = []
    for row in rows[1:]:
        if len(row) < 3:
            continue
        cedula       = row[0].strip() if len(row) > 0 else ''
        parent_name  = row[1].strip() if len(row) > 1 else ''
        status       = row[2].strip().upper() if len(row) > 2 else ''
        students_raw = row[3].strip() if len(row) > 3 else ''
        quantity_raw = row[4].strip() if len(row) > 4 else '1'
        discount     = row[5].strip() if len(row) > 5 else ''
        monthly_raw  = row[6].strip() if len(row) > 6 else ''
        phone_raw    = row[10].strip() if len(row) > 10 else ''

        if not parent_name:
            continue

        try:
            quantity = int(quantity_raw) if quantity_raw.isdigit() else 1
        except (ValueError, AttributeError):
            quantity = 1

        try:
            monthly = float(monthly_raw.replace(',', '.')) if monthly_raw else 0.0
        except ValueError:
            monthly = 0.0

        # Students separated by " / "
        students = [s.strip() for s in students_raw.split('/') if s.strip()]

        families.append({
            'cedula':      cedula,
            'parent_name': parent_name,
            'status':      status,
            'students':    students,
            'quantity':    quantity,
            'monthly':     round(monthly, 2),
            'discount':    discount,
            'phone':       _normalize_phone(phone_raw),
        })
    return families


def _write_to_odoo(families, live=False):
    import xmlrpc.client
    cfg  = json.load(open(PROD_CFG_PATH))
    xcfg = cfg['production']['xmlrpc']
    m    = xmlrpc.client.ServerProxy(f"{xcfg['url']}/xmlrpc/2/object", allow_none=True)

    def call(model, method, args=None, kw=None):
        return m.execute_kw(xcfg['db'], 2, xcfg['api_key'], model, method, args or [], kw or {})

    payload = json.dumps(
        {'families': families, 'synced_at': datetime.utcnow().isoformat()},
        ensure_ascii=False,
    )

    if not live:
        log.info("DRY-RUN: %d families parsed (%d chars). Sample (first 2):", len(families), len(payload))
        for f in families[:2]:
            print(json.dumps(f, indent=2, ensure_ascii=False))
        return

    existing = call('ir.config_parameter', 'search', [[['key', '=', PARAM_KEY]]])
    if existing:
        call('ir.config_parameter', 'write', [existing, {'value': payload}])
    else:
        call('ir.config_parameter', 'create', [[{'key': PARAM_KEY, 'value': payload}]])
    log.info("✓ %s updated — %d families synced", PARAM_KEY, len(families))


def main():
    parser = argparse.ArgumentParser(description='Sync family billing data to Odoo param')
    parser.add_argument('--live', action='store_true', help='Write to production (default: dry-run)')
    args = parser.parse_args()

    log.info("Loading Customers sheet%s...", '' if args.live else ' (DRY-RUN)')
    rows     = _load_sheet()
    families = _parse_rows(rows)
    log.info("Parsed %d families from %d sheet rows", len(families), len(rows) - 1)
    _write_to_odoo(families, live=args.live)


if __name__ == '__main__':
    main()
