#!/usr/bin/env python3
"""
BCV Rate Sync → Odoo ir.config_parameter

Reads exchange rates from the local BCV MySQL database and pushes them
to Odoo (testing + production) as ai_agent.bcv_rate_context (JSON).

The Glenda general_inquiry skill reads this parameter at conversation
load time, injecting current and historical BCV rates into the system
prompt so she can answer USD↔VEB conversion questions.

Usage:
    python3 /opt/odoo-dev/scripts/sync_bcv_to_odoo.py
    python3 /opt/odoo-dev/scripts/sync_bcv_to_odoo.py --env testing
    python3 /opt/odoo-dev/scripts/sync_bcv_to_odoo.py --env production
    python3 /opt/odoo-dev/scripts/sync_bcv_to_odoo.py --env both     (default)

Cron: every 30 minutes (see /etc/cron.d/sync_bcv_odoo)
"""

import argparse
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import date, timedelta

import pymysql

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('sync_bcv')

# ── BCV MySQL credentials ─────────────────────────────────────────────────────
BCV_DB = {
    'host':     '127.0.0.1',
    'user':     'bcv_script',
    'password': 'oCurrency*1',
    'database': 'exchange_rates_bcv',
    'connect_timeout': 5,
}

# ── Odoo targets ──────────────────────────────────────────────────────────────
ODOO_CONFIGS = {
    'testing': {
        'url':      'http://localhost:8019',
        'db':       'testing',
        'user':     'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url':      os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve'),
        'db':       os.environ.get('ODOO_DB',  'DB_UEIPAB'),
        'user':     os.environ.get('ODOO_USER', 'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}

PARAM_KEY = 'ai_agent.bcv_rate_context'
HISTORY_DAYS = 30

# ── BCV data fetch ────────────────────────────────────────────────────────────

def fetch_bcv_rates():
    """Return dict with 'current' rate and 'history' (last HISTORY_DAYS days)."""
    conn = pymysql.connect(**BCV_DB)
    try:
        with conn.cursor() as cur:
            # Current effective rate (most recent effective_date <= today)
            cur.execute("""
                SELECT rate, COALESCE(effective_date, DATE(created_at)) AS eff_date,
                       MAX(created_at) AS updated_at
                FROM bcv_rates
                WHERE COALESCE(effective_date, DATE(created_at)) <= CURDATE()
                GROUP BY rate, eff_date
                ORDER BY eff_date DESC, updated_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            if not row:
                logger.warning("No current BCV rate found")
                return None

            current = {
                'rate':       float(row[0]),
                'date':       row[1].strftime('%Y-%m-%d') if row[1] else None,
                'updated_at': row[2].strftime('%Y-%m-%d %H:%M') if row[2] else None,
            }

            # Historical rates — one per day, last HISTORY_DAYS
            since = (date.today() - timedelta(days=HISTORY_DAYS)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT
                    COALESCE(effective_date, DATE(created_at)) AS eff_date,
                    AVG(rate)                                   AS avg_rate,
                    MIN(rate)                                   AS min_rate,
                    MAX(rate)                                   AS max_rate
                FROM bcv_rates
                WHERE COALESCE(effective_date, DATE(created_at)) >= %s
                  AND COALESCE(effective_date, DATE(created_at)) <= CURDATE()
                GROUP BY eff_date
                ORDER BY eff_date DESC
                LIMIT %s
            """, (since, HISTORY_DAYS))

            history = []
            for r in cur.fetchall():
                history.append({
                    'date':     r[0].strftime('%Y-%m-%d') if r[0] else None,
                    'rate':     round(float(r[1]), 6),
                    'min_rate': round(float(r[2]), 6),
                    'max_rate': round(float(r[3]), 6),
                })

        logger.info(
            "BCV fetched: current=%.4f (%s), history=%d days",
            current['rate'], current['date'], len(history)
        )
        return {'current': current, 'history': history}

    finally:
        conn.close()


# ── Odoo push ─────────────────────────────────────────────────────────────────

def push_to_odoo(env_name, rates_json):
    cfg = ODOO_CONFIGS[env_name]
    if not cfg['password']:
        logger.warning("Skipping %s — ODOO_PASSWORD not set", env_name)
        return False
    try:
        common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
        uid    = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
        if not uid:
            logger.error("Auth failed for %s", env_name)
            return False
        models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
        models.execute_kw(
            cfg['db'], uid, cfg['password'],
            'ir.config_parameter', 'set_param',
            [PARAM_KEY, rates_json],
        )
        logger.info("Pushed BCV context to Odoo %s (uid=%s)", env_name, uid)
        return True
    except Exception as e:
        logger.error("Failed to push to %s: %s", env_name, e)
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--env', default='both',
        choices=['testing', 'production', 'both'],
        help='Odoo environment(s) to update'
    )
    args = parser.parse_args()

    rates = fetch_bcv_rates()
    if not rates:
        logger.error("No BCV data — aborting")
        sys.exit(1)

    rates_json = json.dumps(rates, ensure_ascii=False)

    targets = ['testing', 'production'] if args.env == 'both' else [args.env]
    results = {}
    for env in targets:
        results[env] = push_to_odoo(env, rates_json)

    ok = all(results.values())
    for env, success in results.items():
        logger.info("%s: %s", env, "OK" if success else "FAILED")

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
