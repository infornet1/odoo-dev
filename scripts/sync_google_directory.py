#!/usr/bin/env python3
"""
Google Workspace Directory Sync — UEIPAB

Fetches all 270 student accounts from Google Directory API and stores
the result in Odoo ir.config_parameter so Glenda can do lookups from
inside the Docker container without needing the google-auth library.

Usage:
  python3 scripts/sync_google_directory.py           # dry-run (print only)
  python3 scripts/sync_google_directory.py --live    # write to Odoo param

Cron: /etc/cron.d/sync_google_directory
  0 11 * * 1-5  root  /usr/bin/python3 /opt/odoo-dev/scripts/sync_google_directory.py --live \
    >> /var/log/sync_google_directory.log 2>&1
  # 11:00 UTC = 07:00 VET — refreshed at school day start
"""

import json
import sys
import xmlrpc.client
from datetime import datetime

sys.path.insert(0, '/var/www/dev/odoo_api_bridge')

ODOO = {
    'url':     'https://odoo.ueipab.edu.ve',
    'db':      'DB_UEIPAB',
    'user':    'tdv.devs@gmail.com',
    'api_key': '6e65cfeb1762f224f675b8d26c1dfe0c',
}
PARAM_KEY = 'school.student_directory_json'
LIVE      = '--live' in sys.argv


def fetch_students():
    from google_directory_api import GoogleDirectoryAPI
    api = GoogleDirectoryAPI()
    if not api.connect():
        raise RuntimeError("Failed to connect to Google Directory API")
    all_students = api.get_students(max_results=500)
    # Only cache active (non-suspended) accounts — suspended = former students who withdrew
    result = []
    skipped = 0
    for s in all_students:
        if s.get('suspended'):
            skipped += 1
            continue
        ou = s.get('orgUnitPath', '')
        # Extract grade label from OU: /Estudiantes/5to Año → "5to Año"
        grade_label = ou.split('/')[-1] if '/' in ou else ou
        result.append({
            'email': s.get('email', ''),
            'name':  s.get('name', ''),
            'grade': grade_label,
            'ou':    ou,
        })
    print(f"  (skipped {skipped} suspended accounts)")
    return result


def push_to_odoo(students):
    common = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/common")
    uid    = common.authenticate(ODOO['db'], ODOO['user'], ODOO['api_key'], {})
    models = xmlrpc.client.ServerProxy(f"{ODOO['url']}/xmlrpc/2/object")
    payload = json.dumps({'students': students, 'synced_at': datetime.now().isoformat()})
    models.execute_kw(ODOO['db'], uid, ODOO['api_key'],
                      'ir.config_parameter', 'set_param', [PARAM_KEY, payload])
    return uid


def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    print(f"[{ts}] sync_google_directory {'(LIVE)' if LIVE else '(DRY RUN)'}")

    students = fetch_students()
    print(f"Fetched {len(students)} students from Google Directory")

    if not LIVE:
        for s in students[:8]:
            print(f"  {s['email']:<30} {s['name']:<35} {s['grade']}")
        print(f"  ... ({len(students)} total) — run with --live to push to Odoo")
        return

    uid = push_to_odoo(students)
    print(f"Pushed to Odoo ir.config_parameter '{PARAM_KEY}' (auth uid={uid})")
    print(f"Done. {len(students)} students cached.")


if __name__ == '__main__':
    main()
