#!/usr/bin/env python3
"""
Cashea Campaign — Send from Google Sheet Customers tab

Reads Active/Pipeline customers from col J of the Customers tab,
validates + deduplicates emails, then sends via Odoo shell.

Usage:
    python3 send_cashea_campaign_from_sheet.py --dry-run   # preview list
    python3 send_cashea_campaign_from_sheet.py --send      # full send
"""

import argparse, json, re, subprocess, sys, tempfile, os
import gspread
from google.oauth2.service_account import Credentials

SHEETS_CREDS   = '/opt/odoo-dev/config/google_sheets_credentials.json'
SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
STATUSES       = {'active', 'pipeline'}
TEMPLATE_ID    = 82   # Cashea — Campaña v2 (sin precio)
CONTEXT_ID     = 2142 # Partner used as render context
SEND_DELAY     = 0.4  # seconds between sends

# ─────────────────────────────────────────────────────────────────────────────

def build_recipients():
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(SHEETS_CREDS, scopes=scopes)
    gc    = gspread.authorize(creds)
    ws    = gc.open_by_key(SPREADSHEET_ID).worksheet('Customers')
    data_rows = ws.get_all_values()[2:]  # skip title + header rows

    recipients = []
    seen       = set()
    skipped_invalid = []
    skipped_dupes   = []

    for row in data_rows:
        if len(row) < 3:
            continue
        status = row[2].strip().lower()
        if status not in STATUSES:
            continue
        name  = row[1].strip()
        col_j = row[9].strip() if len(row) > 9 else ''
        if not col_j:
            continue
        for raw in col_j.split(';'):
            email = raw.strip()
            if not email:
                continue
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                skipped_invalid.append((name, email))
                continue
            key = email.lower()
            if key in seen:
                skipped_dupes.append((name, email))
                continue
            seen.add(key)
            recipients.append({'name': name, 'status': row[2].strip(), 'email': email})

    return recipients, skipped_invalid, skipped_dupes


ODOO_SEND_SCRIPT = """\
import json, time, sys

TEMPLATE_ID = {template_id}
DELAY       = {delay}
CONTEXT_ID  = {context_id}

tmpl = env['mail.template'].browse(TEMPLATE_ID)
if not tmpl.exists():
    print(f"ERROR: template {{TEMPLATE_ID}} not found"); sys.exit(1)

with open('{recipients_file}') as f:
    recipients = json.load(f)

rendered = tmpl._generate_template([CONTEXT_ID], render_fields=['subject','body_html','email_from'])
r       = rendered[CONTEXT_ID]
subject = r['subject']
body    = r['body_html']
efrom   = r.get('email_from', '"Instituto Privado Andres Bello" <pagos@ueipab.edu.ve>')

sent = 0; errors = 0
for i, rec in enumerate(recipients, 1):
    try:
        mail = env['mail.mail'].create({{
            'subject':    subject,
            'body_html':  body,
            'email_from': efrom,
            'email_to':   rec['email'],
            'auto_delete': False,
        }})
        mail.send()
        sent += 1
        print(f"[{{i:3d}}/{{len(recipients)}}] OK   {{rec['name']:<42}} {{rec['email']}}")
    except Exception as e:
        errors += 1
        print(f"[{{i:3d}}/{{len(recipients)}}] ERR  {{rec['name']:<42}} {{rec['email']}} -- {{str(e)[:60]}}")
    if i % 20 == 0:
        env.cr.commit()
    if i < len(recipients):
        time.sleep(DELAY)

env.cr.commit()
print("=" * 60)
print(f"DONE -- Sent: {{sent}}  Errors: {{errors}}  Total: {{len(recipients)}}")
"""

# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview list only')
    parser.add_argument('--send',    action='store_true', help='Send emails')
    args = parser.parse_args()

    if not args.dry_run and not args.send:
        parser.print_help(); sys.exit(1)

    print("Reading Google Sheet...")
    recipients, skipped_invalid, skipped_dupes = build_recipients()

    print(f"Valid unique emails : {len(recipients)}")
    print(f"Skipped invalid    : {len(skipped_invalid)} — {[e for _,e in skipped_invalid]}")
    print(f"Skipped duplicates : {len(skipped_dupes)}   — {[e for _,e in skipped_dupes]}")

    if args.dry_run:
        print(f"\n{'#':<4} {'Status':<10} {'Name':<44} Email")
        print("-" * 95)
        for i, r in enumerate(recipients, 1):
            print(f"{i:<4} {r['status']:<10} {r['name']:<44} {r['email']}")
        print(f"\nTotal: {len(recipients)} — dry run complete, nothing sent.")
        return

    # Write recipients to /tmp, copy into container, run Odoo shell
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                     prefix='cashea_', delete=False) as f:
        json.dump(recipients, f)
        tmp_host = f.name
    container_path = '/tmp/cashea_recipients.json'

    subprocess.run(['docker', 'cp', tmp_host, f'odoo-dev-web:{container_path}'], check=True)

    script = ODOO_SEND_SCRIPT.format(
        template_id    = TEMPLATE_ID,
        delay          = SEND_DELAY,
        context_id     = CONTEXT_ID,
        recipients_file= container_path,
    )

    print(f"\nSending {len(recipients)} emails via Odoo shell...")
    result = subprocess.run(
        ['docker', 'exec', '-i', 'odoo-dev-web',
         '/usr/bin/odoo', 'shell', '-d', 'testing', '--no-http'],
        input=script.encode(),
        capture_output=False,
    )
    os.unlink(tmp_host)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
