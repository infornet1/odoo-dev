#!/usr/bin/env python3
"""
AI Agent Escalation Bridge - WhatsApp Group Notification

Notifies the "ueipab soporte" WhatsApp group when AI Agent conversations
are escalated. Freescout ticket creation is handled by Odoo's email system
(email to recursoshumanos@ueipab.edu.ve → Freescout auto-creates conversation).

Flow:
  1. Query Odoo for conversations with escalation_date but not yet notified
  2. Send WhatsApp notification to support group for each
  3. Mark as notified in Odoo

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py           # dry run
    python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py --live    # apply real changes

Author: Claude Code Assistant
Date: 2026-02-08
Updated: 2026-02-19 — Removed direct Freescout SQL; escalation now via email only
"""

import argparse
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime

import requests

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True  # Default: True = no modifications. Use --live to override.
TARGET_ENV = os.environ.get('TARGET_ENV', 'testing')

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

ODOO_URL = ODOO_CONFIGS[TARGET_ENV]['url']
ODOO_DB = ODOO_CONFIGS[TARGET_ENV]['db']
ODOO_USER = ODOO_CONFIGS[TARGET_ENV]['user']
ODOO_PASSWORD = ODOO_CONFIGS[TARGET_ENV]['password']

FREESCOUT_BASE_URL = 'https://freescout.ueipab.edu.ve'

# WhatsApp group for notifications
WA_GROUP_ID = '1594720028@g.us'  # ueipab soporte

# WhatsApp config file — search multiple paths (same order as Odoo module)
def _find_wa_config():
    env_path = os.environ.get('WA_CONFIG_PATH')
    if env_path and os.path.isfile(env_path):
        return env_path
    for d in ['/opt/odoo-dev/config', '/home/vision/ueipab17/config']:
        p = os.path.join(d, 'whatsapp_massiva.json')
        if os.path.isfile(p):
            return p
    return None

WA_CONFIG_PATH = _find_wa_config()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helpers
# ============================================================================

def connect_odoo():
    """Connect to Odoo via XML-RPC, return (uid, models_proxy)."""
    logger.info("Connecting to Odoo at %s (db=%s)...", ODOO_URL, ODOO_DB)
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    logger.info("Odoo connected (uid=%d)", uid)
    return uid, models


def load_whatsapp_config():
    """Load WhatsApp API config from JSON file."""
    if not WA_CONFIG_PATH or not os.path.isfile(WA_CONFIG_PATH):
        logger.warning("WhatsApp config not found (searched dev + prod paths)")
        return None
    with open(WA_CONFIG_PATH, 'r') as f:
        cfg = json.load(f)
    secret = cfg['api']['secret']
    accounts = cfg.get('whatsapp_accounts', [])
    primary = next((a for a in accounts if a.get('primary')), accounts[0] if accounts else {})
    base_url = cfg['api'].get('base_url', 'https://whatsapp.massivamovil.com/api')
    return {
        'secret': secret,
        'account_id': primary.get('unique_id', ''),
        'base_url': base_url,
    }


def send_whatsapp_group(wa_config, message):
    """Send a WhatsApp message to the support group."""
    if not wa_config:
        logger.warning("WhatsApp config not available, skipping notification")
        return False

    url = wa_config['base_url'].rstrip('/') + '/send/whatsapp'
    data = {
        'secret': wa_config['secret'],
        'account': wa_config['account_id'],
        'recipient': WA_GROUP_ID,
        'type': 'text',
        'message': message,
    }

    try:
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if result.get('status') == 200:
            logger.info("WhatsApp group notification sent")
            return True
        logger.error("WhatsApp API error: %s", result.get('message', 'Unknown'))
        return False
    except requests.exceptions.RequestException as e:
        logger.error("WhatsApp send failed: %s", e)
        return False


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("AI AGENT ESCALATION BRIDGE")
    print("=" * 70)
    print(f"  Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN:   {DRY_RUN}")
    print(f"  Target:    {TARGET_ENV}")
    print(f"  Odoo:      {ODOO_URL} / {ODOO_DB}")
    print(f"  WA Group:  {WA_GROUP_ID}")
    print()

    # Phase 1: Connect
    uid, models = connect_odoo()
    wa_config = load_whatsapp_config()

    # Phase 2: Query pending escalations (not yet notified via WhatsApp)
    print("\n--- Phase 2: Query Pending Escalations ---")
    pending = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'ai.agent.conversation', 'search_read',
        [[
            ('escalation_date', '!=', False),
            ('escalation_notified', '=', False),
        ]],
        {'fields': [
            'partner_id', 'phone', 'escalation_reason',
            'source_model', 'source_id', 'name',
        ]},
    )

    if not pending:
        print("  No pending escalations found.")
        return

    print(f"  Found {len(pending)} pending escalation(s)")
    for esc in pending:
        partner_name = esc['partner_id'][1] if esc['partner_id'] else 'Desconocido'
        print(f"    Conv #{esc['id']}: {partner_name} — {(esc['escalation_reason'] or '')[:80]}")

    # Phase 3: Send WhatsApp group notifications
    print(f"\n--- Phase 3: WhatsApp Group Notifications ---")
    notified = 0

    for esc in pending:
        conv_id = esc['id']
        partner_name = esc['partner_id'][1] if esc['partner_id'] else 'Desconocido'
        phone = esc['phone'] or ''
        reason = esc['escalation_reason'] or 'Sin detalle'

        # Truncate reason for WhatsApp (first entry, clean timestamp)
        reason_short = reason.split('\n')[0]
        reason_short = reason_short.lstrip('[0123456789- :]')
        if len(reason_short) > 150:
            reason_short = reason_short[:147] + '...'

        odoo_url = (
            f"{ODOO_URL}/web#id={conv_id}"
            f"&model=ai.agent.conversation&view_type=form"
        )

        message = (
            f"\U0001f4cb *Escalacion AI Agent*\n"
            f"Cliente: {partner_name}\n"
            f"Telefono: {phone}\n"
            f"Motivo: {reason_short}\n"
            f"\U0001f517 Odoo: {odoo_url}"
        )

        if DRY_RUN:
            print(f"  DRY_RUN: Would send WhatsApp to group:")
            print(f"    {message}")
        else:
            success = send_whatsapp_group(wa_config, message)
            if success:
                # Mark as notified in Odoo
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'ai.agent.conversation', 'write',
                    [[conv_id], {'escalation_notified': True}],
                )
                notified += 1
            else:
                logger.warning("Failed to notify group for conv #%d", conv_id)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Pending escalations: {len(pending)}")
    if not DRY_RUN:
        print(f"  Group notifications sent: {notified}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Agent Escalation Bridge')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (send real WhatsApp notifications)')
    args = parser.parse_args()
    if args.live:
        DRY_RUN = False
    try:
        main()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
