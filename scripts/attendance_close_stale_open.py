#!/usr/bin/env python3
"""
attendance_close_stale_open.py
──────────────────────────────
Safety-net sweep for DANGLING open hr.attendance records.

An attendance row with check_out = NULL is a "dangling open" session. For the
CURRENT day that is normal (the employee is still at work / the evening WiFi
auto-fill will close it). For a PRIOR day it is an anomaly — either a kiosk
check-in where the person forgot to check out, or a row inserted by a backfill
script/manual SQL that omitted check_out (those also have NULL audit fields).

Left alone, these rows:
  • report worked_hours = 0 and skew biweekly attendance totals,
  • linger forever (the daily alert flags them once, then they rot),
  • can trip Odoo's overlap/validity constraint if later touched via the ORM.

This sweep closes every open row whose check_in is BEFORE today (VET), setting
check_out = check_in + 60s → worked_hours ≈ 0, a deliberately obvious
"needs-review" signature RRHH can correct. It NEVER touches today's still-open
sessions. Idempotent: a second run finds nothing.

It is both the one-off CLEANUP tool and the nightly PREVENTION guard, so even if
some inserter misbehaves again, the dangling row is neutralised within 24h.

Usage:
    python3 scripts/attendance_close_stale_open.py                      # DRY, testing
    python3 scripts/attendance_close_stale_open.py --live               # apply, testing
    python3 scripts/attendance_close_stale_open.py --env production --live
    python3 scripts/attendance_close_stale_open.py --before 2026-06-29  # custom UTC cut

CRON (/etc/cron.d/attendance_close_stale_open) — runs after the evening alert:
    45 3 * * *  root  /usr/bin/python3 /opt/odoo-dev/scripts/attendance_close_stale_open.py --live --env production >> /var/log/attendance_close_stale_open.log 2>&1
    # 03:45 UTC = 23:45 VET
"""

import argparse
import json
import os
import sys
import xmlrpc.client
from datetime import date, datetime, timedelta, timezone

VET_TO_UTC = timedelta(hours=4)   # VET = UTC-4
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'production.json')

PG_TESTING = {
    'url': 'http://localhost:8019', 'db': 'testing',
    'user': 'tdv.devs@gmail.com', 'api_key': 'admin',  # testing uses admin login
}


def load_cfg(env):
    if env == 'production':
        with open(os.path.abspath(CONFIG_PATH)) as f:
            return json.load(f)['production']['xmlrpc']
    return PG_TESTING


def today_vet():
    return (datetime.now(timezone.utc) - timedelta(hours=4)).date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', choices=['testing', 'production'], default='testing')
    ap.add_argument('--live', action='store_true', help='Apply changes (default = dry run)')
    ap.add_argument('--before', help='UTC cut YYYY-MM-DD; close opens with check_in before this '
                                     '(default = start of today VET)')
    args = ap.parse_args()

    cfg = load_cfg(args.env)
    boundary = (args.before + ' 00:00:00') if args.before \
        else today_vet().strftime('%Y-%m-%d 00:00:00')

    common = xmlrpc.client.ServerProxy(cfg['url'] + '/xmlrpc/2/common')
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        sys.exit('ERROR: XML-RPC authentication failed for %s' % args.env)
    models = xmlrpc.client.ServerProxy(cfg['url'] + '/xmlrpc/2/object', allow_none=True)

    def kw(model, method, a=None, k=None):
        return models.execute_kw(cfg['db'], uid, cfg['api_key'], model, method, a or [], k or {})

    mode = 'LIVE' if args.live else 'DRY-RUN'
    print('=== attendance_close_stale_open [%s] env=%s ===' % (mode, args.env))
    print('Closing dangling opens with check_in < %s (UTC); today\'s sessions are left alone.\n'
          % boundary)

    stale = kw('hr.attendance', 'search_read',
               [[['check_out', '=', False], ['check_in', '<', boundary]]],
               {'fields': ['employee_id', 'check_in', 'create_date'], 'order': 'check_in'})

    if not stale:
        print('No stale open rows. Nothing to do.')
        return

    closed, failed = [], []
    for r in stale:
        emp = r['employee_id'][1] if r['employee_id'] else '?'
        ghost = '' if r['create_date'] else '  [null-audit ghost]'
        ci = datetime.strptime(r['check_in'], '%Y-%m-%d %H:%M:%S')
        co = (ci + timedelta(seconds=60)).strftime('%Y-%m-%d %H:%M:%S')
        print('  #%-6s %-24s in=%s -> out=%s%s' % (r['id'], emp[:24], r['check_in'], co, ghost))
        if args.live:
            try:
                kw('hr.attendance', 'write', [[r['id']], {'check_out': co}])
                closed.append(r['id'])
            except Exception as e:                       # noqa: BLE001
                failed.append((r['id'], str(e)[:140]))
                print('     ! FAILED: %s' % str(e)[:140])

    print('\nStale open rows found: %d' % len(stale))
    if args.live:
        print('Closed: %d   Failed: %d' % (len(closed), len(failed)))
        left = kw('hr.attendance', 'search_count',
                  [[['check_out', '=', False], ['check_in', '<', boundary]]])
        print('Remaining stale-open after sweep: %d (expect 0)' % left)
    else:
        print('DRY-RUN — re-run with --live to apply.')


if __name__ == '__main__':
    main()
