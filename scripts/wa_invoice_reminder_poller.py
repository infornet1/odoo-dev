#!/usr/bin/env python3
"""
WA Invoice Reminder — UI Trigger Poller

The Odoo wizard cannot spawn processes directly (it runs inside the production
Docker container, not on the dev server where the WA script lives). Instead the
wizard writes ir.config_parameter 'wa_invoice_reminder.trigger_at'. This script
polls that parameter every 5 minutes (via cron), clears it, and runs the actual
WA script.

Cron: /etc/cron.d/wa_invoice_reminder_poller
  */5 * * * * root /usr/bin/python3 /opt/odoo-dev/scripts/wa_invoice_reminder_poller.py >> /var/log/wa_invoice_reminder.log 2>&1
"""

import json
import logging
import os
import subprocess
import sys
import xmlrpc.client
from datetime import datetime, timezone, timedelta

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(SCRIPT_DIR, '..', 'config', 'production.json')
WA_SCRIPT     = os.path.join(SCRIPT_DIR, 'wa_invoice_reminder.py')
TRIGGER_PARAM = 'wa_invoice_reminder.trigger_at'
MAX_AGE_HOURS = 2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [poller] %(message)s',
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def odoo_connect():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    return cfg['db'], uid, cfg['api_key'], models


def get_trigger(db, uid, pw, models):
    rows = models.execute_kw(db, uid, pw, 'ir.config_parameter', 'search_read',
        [[['key', '=', TRIGGER_PARAM]]],
        {'fields': ['id', 'value'], 'limit': 1})
    if not rows or not rows[0]['value']:
        return None, None
    return rows[0]['id'], rows[0]['value']


def clear_trigger(db, uid, pw, models, param_id):
    models.execute_kw(db, uid, pw, 'ir.config_parameter', 'write',
        [[param_id], {'value': ''}])


def main():
    db, uid, pw, models = odoo_connect()
    param_id, trigger_val = get_trigger(db, uid, pw, models)

    if not trigger_val:
        return  # nothing to do — silent exit keeps log clean

    try:
        trigger_dt = datetime.fromisoformat(trigger_val)
        if trigger_dt.tzinfo is None:
            trigger_dt = trigger_dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - trigger_dt
        if age > timedelta(hours=MAX_AGE_HOURS):
            log.warning("Stale trigger (%s old) — clearing without send.", age)
            clear_trigger(db, uid, pw, models, param_id)
            return
    except ValueError:
        log.warning("Unparseable trigger value '%s' — clearing.", trigger_val)
        clear_trigger(db, uid, pw, models, param_id)
        return

    log.info("Trigger found (queued %s) — launching WA script (ad-hoc).", trigger_val)
    clear_trigger(db, uid, pw, models, param_id)

    # --adhoc: send EXACTLY the wizard's selected list (payload param), not the
    # tag-based daily blast. The script force-dry-runs if WA is paused globally.
    result = subprocess.run([sys.executable, WA_SCRIPT, '--live', '--adhoc'])
    log.info("WA script exited with code %d.", result.returncode)


if __name__ == '__main__':
    main()
