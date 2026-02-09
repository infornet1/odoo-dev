#!/usr/bin/env python3
"""
AI Agent WhatsApp Health Monitor

Monitors WhatsApp sender accounts for SPAM flags / unlinking.
Detects issues via MassivaMóvil validate API + Freescout email scan.
Auto-switches to backup number and recovers when primary is back.

Runs on dev server, reaches Odoo via XML-RPC (same pattern as escalation bridge).

Detection (Layer 1 - API):
  Calls MassivaMóvil GET /validate/whatsapp on the active sender number.
  If the number is not valid on WhatsApp, it was flagged/unlinked.

Detection (Layer 2 - Freescout):
  Scans Freescout inbox for emails with subject matching
  "¡Tu cuenta de WhatsApp ha sido desvinculada!" from MassivaMóvil.

Failover:
  On detection → switch active account params in Odoo to backup number.
  After 24h cooldown → check if flagged number recovered → switch back.
  Alert support WhatsApp group on every state change.

Usage:
    python3 ai_agent_wa_health_monitor.py              # dry run
    python3 ai_agent_wa_health_monitor.py --live        # apply changes
    python3 ai_agent_wa_health_monitor.py --force-switch backup  # manual switch

Author: Claude Code Assistant
Date: 2026-02-09
"""

import argparse
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime, timedelta

import pymysql
import requests

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True
TARGET_ENV = os.environ.get('TARGET_ENV', 'testing')
COOLDOWN_HOURS = 24

# Freescout subject pattern for unlink notification
FS_UNLINK_SUBJECT = '%cuenta de WhatsApp%desvinculada%'

# Odoo XML-RPC configuration per environment
ODOO_CONFIGS = {
    'testing': {
        'url': 'http://localhost:8019',
        'db': 'testing',
        'user': 'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url': 'https://odoo.ueipab.edu.ve',
        'db': 'DB_UEIPAB',
        'user': 'tdv.devs@gmail.com',
        'password': 'f69330e5bd6ae043320f054e9df9fcbbb34522db',
    },
}

# Freescout MySQL
FREESCOUT_DB_HOST = os.environ.get('FREESCOUT_DB_HOST', 'localhost')
FREESCOUT_DB_USER = os.environ.get('FREESCOUT_DB_USER', 'free297')
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '1gczp1S@3!')
FREESCOUT_DB_NAME = os.environ.get('FREESCOUT_DB_NAME', 'free297')

# WhatsApp support group for notifications
WA_GROUP_ID = '1594720028@g.us'  # ueipab soporte

# State + log files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'wa_health_state.json')
LOG_DIR = os.path.join(SCRIPT_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'wa_health_monitor.log')


# ============================================================================
# Logging
# ============================================================================

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# Config loading
# ============================================================================

def _find_config(filename):
    """Search for config file in standard paths."""
    env_path = os.environ.get('WA_CONFIG_PATH')
    if env_path and os.path.isfile(env_path):
        return env_path
    for d in ['/opt/odoo-dev/config', '/home/vision/ueipab17/config']:
        p = os.path.join(d, filename)
        if os.path.isfile(p):
            return p
    return None


def load_wa_config():
    """Load WhatsApp config with both account details."""
    path = _find_config('whatsapp_massiva.json')
    if not path:
        raise FileNotFoundError("whatsapp_massiva.json not found")
    with open(path, 'r') as f:
        cfg = json.load(f)

    accounts = cfg.get('whatsapp_accounts', [])
    primary = next((a for a in accounts if a.get('primary')), None)
    backup = next((a for a in accounts if not a.get('primary')), None)

    if not primary or not backup:
        raise ValueError("Config must have both primary and backup WhatsApp accounts")

    return {
        'secret': cfg['api']['secret'],
        'base_url': cfg['api'].get('base_url', 'https://whatsapp.massivamovil.com/api'),
        'primary': {
            'phone': primary['phone'],
            'unique_id': primary['unique_id'],
        },
        'backup': {
            'phone': backup['phone'],
            'unique_id': backup['unique_id'],
        },
    }


# ============================================================================
# State management
# ============================================================================

def load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'active_account': 'primary',
        'flagged_phone': '',
        'flagged_date': '',
        'last_freescout_conv_id': 0,
    }


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# ============================================================================
# Connections
# ============================================================================

def connect_odoo():
    """Connect to Odoo via XML-RPC."""
    cfg = ODOO_CONFIGS[TARGET_ENV]
    logger.info("Connecting to Odoo at %s (db=%s)...", cfg['url'], cfg['db'])
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    logger.info("Odoo connected (uid=%d)", uid)
    return uid, models


def connect_freescout():
    """Connect to Freescout MySQL."""
    logger.info("Connecting to Freescout MySQL...")
    conn = pymysql.connect(
        host=FREESCOUT_DB_HOST,
        user=FREESCOUT_DB_USER,
        password=FREESCOUT_DB_PASSWORD,
        database=FREESCOUT_DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    logger.info("Freescout MySQL connected")
    return conn


# ============================================================================
# Detection: Layer 1 — MassivaMóvil validate API
# ============================================================================

def validate_whatsapp_number(wa_config, unique_id, phone):
    """Check if a phone number is active on WhatsApp via MassivaMóvil API.

    Returns:
        True  = number is valid on WhatsApp
        False = number is NOT valid (flagged/unlinked)
        None  = API error (indeterminate)
    """
    url = wa_config['base_url'].rstrip('/') + '/validate/whatsapp'
    params = {
        'secret': wa_config['secret'],
        'unique': unique_id,
        'phone': phone,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        is_valid = result.get('status') == 200
        logger.info("Validate %s: status=%s, valid=%s", phone, result.get('status'), is_valid)
        return is_valid
    except Exception as e:
        logger.error("MassivaMóvil validate API error for %s: %s", phone, e)
        return None


# ============================================================================
# Detection: Layer 2 — Freescout email scan
# ============================================================================

def check_freescout_unlink_emails(fs_conn, last_conv_id):
    """Check Freescout for WhatsApp unlink notification emails.

    Returns list of matching conversations (newest first).
    """
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    query = """
        SELECT c.id, c.number, c.subject, c.created_at
        FROM conversations c
        WHERE c.subject LIKE %s
          AND c.id > %s
          AND c.created_at >= %s
        ORDER BY c.id ASC
    """
    try:
        with fs_conn.cursor() as cursor:
            cursor.execute(query, (FS_UNLINK_SUBJECT, last_conv_id, cutoff))
            results = cursor.fetchall()
            if results:
                logger.info("Freescout: found %d unlink email(s)", len(results))
                for r in results:
                    logger.info("  Conv #%s: '%s' (%s)", r['number'], r['subject'], r['created_at'])
            return results
    except Exception as e:
        logger.error("Freescout query error: %s", e)
        return []


# ============================================================================
# Actions
# ============================================================================

def switch_odoo_account(uid, models, wa_config, target_account, flagged_phone=''):
    """Switch active WhatsApp account in Odoo via XML-RPC."""
    cfg = ODOO_CONFIGS[TARGET_ENV]
    target = wa_config[target_account]

    params_to_set = {
        'ai_agent.whatsapp_account_id': target['unique_id'],
        'ai_agent.whatsapp_account_phone': target['phone'],
        'ai_agent.whatsapp_active_account': target_account,
    }

    if flagged_phone:
        params_to_set['ai_agent.whatsapp_flagged_phone'] = flagged_phone
        params_to_set['ai_agent.whatsapp_flagged_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        # Recovery — clear flag
        params_to_set['ai_agent.whatsapp_flagged_phone'] = ''
        params_to_set['ai_agent.whatsapp_flagged_date'] = ''

    for key, value in params_to_set.items():
        models.execute_kw(
            cfg['db'], uid, cfg['password'],
            'ir.config_parameter', 'set_param',
            [key, str(value)],
        )

    logger.info("Odoo params updated: active=%s, flagged=%s", target_account, flagged_phone or 'none')


def send_whatsapp_alert(wa_config, active_account, message):
    """Send alert to support WhatsApp group using the ACTIVE account."""
    active = wa_config[active_account]
    url = wa_config['base_url'].rstrip('/') + '/send/whatsapp'
    data = {
        'secret': wa_config['secret'],
        'account': active['unique_id'],
        'recipient': WA_GROUP_ID,
        'type': 'text',
        'message': message,
    }
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('status') == 200:
            logger.info("WhatsApp group alert sent via %s", active['phone'])
            return True
        logger.error("WhatsApp API error: %s", result.get('message', 'Unknown'))
        return False
    except Exception as e:
        logger.error("WhatsApp alert send failed: %s", e)
        return False


# ============================================================================
# Main logic
# ============================================================================

def run_health_check(wa_config, uid, models, fs_conn, state):
    """Main health check cycle."""

    active_account = state.get('active_account', 'primary')
    active = wa_config[active_account]
    other_account = 'backup' if active_account == 'primary' else 'primary'
    flagged_phone = state.get('flagged_phone', '')
    flagged_date_str = state.get('flagged_date', '')

    # ── Recovery check (if a number is currently flagged) ───────────
    if flagged_phone and flagged_date_str:
        try:
            flagged_date = datetime.strptime(flagged_date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            flagged_date = datetime.fromisoformat(flagged_date_str)

        hours_elapsed = (datetime.now() - flagged_date).total_seconds() / 3600
        logger.info("Recovery check: %s flagged %.1fh ago (cooldown=%dh)",
                     flagged_phone, hours_elapsed, COOLDOWN_HOURS)

        if hours_elapsed >= COOLDOWN_HOURS:
            # Use the ACTIVE (working) account to validate the flagged number
            is_valid = validate_whatsapp_number(
                wa_config, active['unique_id'], flagged_phone)

            if is_valid is True:
                logger.info("RECOVERY: %s is back on WhatsApp after %.1fh!",
                            flagged_phone, hours_elapsed)

                if DRY_RUN:
                    logger.info("DRY_RUN: Would switch back to %s", other_account)
                else:
                    switch_odoo_account(uid, models, wa_config, other_account)
                    alert_msg = (
                        "\u2705 *WhatsApp Recuperado*\n"
                        f"Numero: {flagged_phone}\n"
                        f"Tiempo inactivo: {hours_elapsed:.0f}h\n"
                        f"Cuenta activa restaurada: {other_account}\n"
                        f"Telefono activo: {wa_config[other_account]['phone']}"
                    )
                    send_whatsapp_alert(wa_config, other_account, alert_msg)

                state['active_account'] = other_account
                state['flagged_phone'] = ''
                state['flagged_date'] = ''
                save_state(state)
                return 'recovered'

            elif is_valid is False:
                logger.info("Still flagged: %s (%.1fh elapsed, next check in 15 min)",
                            flagged_phone, hours_elapsed)
            else:
                logger.warning("Cannot determine status of %s (API error), "
                               "will retry next cycle", flagged_phone)
        else:
            logger.info("Cooldown active: %.1fh / %dh — skipping recovery check",
                        hours_elapsed, COOLDOWN_HOURS)
        return 'waiting_recovery'

    # ── Detection: check if active number is healthy ────────────────

    # Layer 1: MassivaMóvil validate API
    api_result = validate_whatsapp_number(
        wa_config, active['unique_id'], active['phone'])

    # Layer 2: Freescout email scan
    unlink_emails = check_freescout_unlink_emails(
        fs_conn, state.get('last_freescout_conv_id', 0))

    if unlink_emails:
        state['last_freescout_conv_id'] = unlink_emails[-1]['id']

    # Evaluate: either signal alone triggers failover
    api_flagged = api_result is False  # Explicit False, not None (API error)
    fs_flagged = len(unlink_emails) > 0
    is_flagged = api_flagged or fs_flagged

    if is_flagged:
        reasons = []
        if api_flagged:
            reasons.append("MassivaMóvil validate: numero no valido en WhatsApp")
        if fs_flagged:
            conv_nums = ', '.join(str(e['number']) for e in unlink_emails)
            reasons.append(f"Freescout: email de desvinculacion (conv #{conv_nums})")

        reason_str = ' + '.join(reasons)
        logger.warning("FLAGGED: %s — %s", active['phone'], reason_str)

        if DRY_RUN:
            logger.info("DRY_RUN: Would switch from %s to %s (%s → %s)",
                        active_account, other_account,
                        active['phone'], wa_config[other_account]['phone'])
        else:
            # Switch to backup
            switch_odoo_account(uid, models, wa_config, other_account,
                                flagged_phone=active['phone'])
            alert_msg = (
                "\u26a0\ufe0f *WhatsApp Desvinculado*\n"
                f"Numero afectado: {active['phone']}\n"
                f"Razon: {reason_str}\n"
                f"Cuenta activa cambiada a: {other_account}\n"
                f"Telefono activo: {wa_config[other_account]['phone']}\n"
                f"Recuperacion automatica en ~{COOLDOWN_HOURS}h"
            )
            send_whatsapp_alert(wa_config, other_account, alert_msg)

        state['active_account'] = other_account
        state['flagged_phone'] = active['phone']
        state['flagged_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_state(state)
        return 'failover'

    # All clear
    if api_result is None:
        logger.info("Health check: API indeterminate, Freescout clear — no action")
        save_state(state)
        return 'indeterminate'

    logger.info("Health check OK: %s is active on WhatsApp", active['phone'])
    save_state(state)
    return 'healthy'


def force_switch(wa_config, uid, models, state, target_account):
    """Manual forced switch to a specific account."""
    current = state.get('active_account', 'primary')
    if current == target_account:
        logger.info("Already on %s, no switch needed", target_account)
        return

    logger.info("Manual switch: %s → %s", current, target_account)
    current_phone = wa_config[current]['phone']

    if DRY_RUN:
        logger.info("DRY_RUN: Would switch to %s (%s)",
                     target_account, wa_config[target_account]['phone'])
    else:
        switch_odoo_account(uid, models, wa_config, target_account,
                            flagged_phone=current_phone)
        alert_msg = (
            "\U0001f504 *WhatsApp Cambio Manual*\n"
            f"De: {current} ({current_phone})\n"
            f"A: {target_account} ({wa_config[target_account]['phone']})\n"
            "Cambio realizado manualmente"
        )
        send_whatsapp_alert(wa_config, target_account, alert_msg)

    state['active_account'] = target_account
    state['flagged_phone'] = current_phone
    state['flagged_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_state(state)


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='AI Agent WhatsApp Health Monitor')
    parser.add_argument('--live', action='store_true',
                        help='Apply changes (default: dry run)')
    parser.add_argument('--target-env', choices=['testing', 'production'],
                        default=os.environ.get('TARGET_ENV', 'testing'),
                        help='Target Odoo environment')
    parser.add_argument('--force-switch', choices=['primary', 'backup'],
                        help='Force manual switch to specified account')
    args = parser.parse_args()

    global DRY_RUN, TARGET_ENV
    if args.live:
        DRY_RUN = False
    TARGET_ENV = args.target_env

    print("=" * 70)
    print("AI AGENT WHATSAPP HEALTH MONITOR")
    print("=" * 70)
    print(f"  Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN:   {DRY_RUN}")
    print(f"  Target:    {TARGET_ENV}")
    cfg = ODOO_CONFIGS[TARGET_ENV]
    print(f"  Odoo:      {cfg['url']} / {cfg['db']}")
    print()

    # Load config + state
    wa_config = load_wa_config()
    state = load_state()

    print(f"  Primary:   {wa_config['primary']['phone']}")
    print(f"  Backup:    {wa_config['backup']['phone']}")
    print(f"  Active:    {state.get('active_account', 'primary')}")
    flagged = state.get('flagged_phone', '')
    print(f"  Flagged:   {flagged or 'none'}")
    print()

    # Connect
    uid, models = connect_odoo()

    if args.force_switch:
        force_switch(wa_config, uid, models, state, args.force_switch)
        print(f"\nForce switch to {args.force_switch}: {'DRY RUN' if DRY_RUN else 'DONE'}")
        return

    fs_conn = connect_freescout()

    try:
        result = run_health_check(wa_config, uid, models, fs_conn, state)
    finally:
        fs_conn.close()

    print(f"\nResult: {result}")
    if result == 'failover':
        print(f"  SWITCHED: {wa_config[state['active_account']]['phone']} is now active")
    elif result == 'recovered':
        print(f"  RECOVERED: switched back to {state['active_account']}")
    elif result == 'healthy':
        print(f"  All clear: {wa_config[state['active_account']]['phone']} is healthy")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
