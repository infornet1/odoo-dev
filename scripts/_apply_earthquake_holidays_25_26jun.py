#!/usr/bin/env python3
"""One-off: register 2026-06-25 & 26 (Cierre por contingencia — sismo) in the
PROD attendance_report.holidays param so the daily alert + biweekly report skip
them. Reversible. Run once: python3 scripts/_apply_earthquake_holidays_25_26jun.py
"""
import json, xmlrpc.client
from datetime import date

cfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
c = xmlrpc.client.ServerProxy(cfg['url'] + '/xmlrpc/2/common')
uid = c.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
m = xmlrpc.client.ServerProxy(cfg['url'] + '/xmlrpc/2/object', allow_none=True)
KEY = 'attendance_report.holidays'

arr = json.loads(m.execute_kw(cfg['db'], uid, cfg['api_key'],
                              'ir.config_parameter', 'get_param', [KEY]))
have = {h['date'] for h in arr}
for a in ({"date": "2026-06-25", "name": "Cierre por contingencia (sismo)"},
          {"date": "2026-06-26", "name": "Cierre por contingencia (sismo)"}):
    if a['date'] not in have:
        arr.append(a)
arr.sort(key=lambda h: h['date'])
m.execute_kw(cfg['db'], uid, cfg['api_key'], 'ir.config_parameter', 'set_param',
             [KEY, json.dumps(arr, ensure_ascii=False, indent=2)])

back = json.loads(m.execute_kw(cfg['db'], uid, cfg['api_key'],
                               'ir.config_parameter', 'get_param', [KEY]))
print('total holidays now:', len(back))
for h in back:
    if '2026-06-24' <= h['date'] <= '2026-06-26':
        print('  ', h['date'], h['name'])
print('25 present:', any(h['date'] == '2026-06-25' for h in back),
      '| 26 present:', any(h['date'] == '2026-06-26' for h in back))
