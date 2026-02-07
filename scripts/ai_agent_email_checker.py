#!/usr/bin/env python3
"""
AI Agent Email Checker - Freescout Bridge Script

Detects when customers reply to verification emails in Freescout and
auto-resolves the corresponding Odoo AI Agent conversations via XML-RPC.

Architecture mirrors daily_bounce_processor.py:
  - Odoo XML-RPC for conversation queries + resolution
  - Freescout MySQL (READ-ONLY) for email reply detection
  - DRY_RUN=True default, state file tracking

Flow:
  1. Query Odoo for conversations with verification_email_sent_date + state=waiting
  2. Query Freescout threads WHERE from LIKE %recipient_email% AND type=1
     (customer reply) AND created_at > verification_date
  3. For matches -> call action_resolve_via_email() via XML-RPC
  4. Run via crontab every 15 min

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_email_checker.py

Author: Claude Code Assistant
Date: 2026-02-07
"""

import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True  # True = no modifications, False = resolve conversations

# Target environment
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

# Freescout MySQL (READ-ONLY)
FREESCOUT_DB_HOST = os.environ.get('FREESCOUT_DB_HOST', 'localhost')
FREESCOUT_DB_USER = os.environ.get('FREESCOUT_DB_USER', 'free297')
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '1gczp1S@3!')
FREESCOUT_DB_NAME = os.environ.get('FREESCOUT_DB_NAME', 'free297')

# State file to track last check
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'ai_agent_email_checker_state.json')

# Logging
LOG_DIR = os.path.join(SCRIPT_DIR, 'ai_agent_logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'email_checker.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ============================================================================
# State Management
# ============================================================================


def load_state():
    """Load last run state from JSON file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'last_run': None}


def save_state(state):
    """Save state to JSON file."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


# ============================================================================
# Odoo XML-RPC
# ============================================================================


def connect_odoo():
    """Establish XML-RPC connection to Odoo and return (uid, models)."""
    logger.info("Connecting to Odoo at %s (db: %s)...", ODOO_URL, ODOO_DB)
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ConnectionError("Failed to authenticate with Odoo")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    logger.info("Connected to Odoo as uid=%d", uid)
    return uid, models


def odoo_search_read(models, uid, model, domain, fields):
    """Search and read records from Odoo."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        [domain], {'fields': fields}
    )


def odoo_execute(models, uid, model, method, record_ids, *args):
    """Execute a method on Odoo records."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, method,
        [record_ids] + list(args)
    )


# ============================================================================
# Freescout MySQL
# ============================================================================


def connect_freescout():
    """Establish MySQL connection to Freescout (READ-ONLY)."""
    try:
        import mysql.connector
    except ImportError:
        logger.error("mysql-connector-python not installed. Run: pip install mysql-connector-python")
        return None

    logger.info("Connecting to Freescout MySQL at %s...", FREESCOUT_DB_HOST)
    conn = mysql.connector.connect(
        host=FREESCOUT_DB_HOST,
        user=FREESCOUT_DB_USER,
        password=FREESCOUT_DB_PASSWORD,
        database=FREESCOUT_DB_NAME,
    )
    logger.info("Connected to Freescout MySQL")
    return conn


def find_email_reply(fs_conn, recipient_email, verification_date):
    """Check if a customer replied to a verification email in Freescout.

    Looks for threads (type=1 = customer message) where:
    - The 'from' field contains the recipient email
    - Created after the verification email was sent

    Returns the first matching thread body preview, or None.
    """
    cursor = fs_conn.cursor(dictionary=True)

    # Convert datetime string from Odoo to MySQL format
    if isinstance(verification_date, str):
        # Odoo datetime format: "2026-02-07 14:30:00"
        verif_dt = verification_date.replace('T', ' ')[:19]
    else:
        verif_dt = verification_date.strftime('%Y-%m-%d %H:%M:%S')

    query = """
        SELECT t.id, t.body, t.created_at, t.`from`
        FROM threads t
        JOIN conversations c ON t.conversation_id = c.id
        WHERE t.type = 1
          AND t.`from` LIKE %s
          AND t.created_at > %s
        ORDER BY t.created_at ASC
        LIMIT 1
    """

    cursor.execute(query, (f'%{recipient_email}%', verif_dt))
    result = cursor.fetchone()
    cursor.close()

    if result:
        # Extract a clean text preview from the HTML body
        body = result.get('body', '')
        # Simple HTML tag stripping
        import re
        preview = re.sub(r'<[^>]+>', '', body).strip()[:300]
        logger.info("Found Freescout reply from %s (thread %d): %s",
                     result.get('from', ''), result['id'], preview[:80])
        return preview

    return None


# ============================================================================
# Main Logic
# ============================================================================


def main():
    logger.info("=" * 60)
    logger.info("AI Agent Email Checker - %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("Environment: %s | DRY_RUN: %s", TARGET_ENV, DRY_RUN)
    logger.info("=" * 60)

    state = load_state()

    # Connect to Odoo
    try:
        uid, models = connect_odoo()
    except Exception as e:
        logger.error("Failed to connect to Odoo: %s", e)
        return

    # Find conversations waiting for email verification
    conversations = odoo_search_read(
        models, uid,
        'ai.agent.conversation',
        [
            ('state', '=', 'waiting'),
            ('verification_email_sent_date', '!=', False),
            ('verification_email_recipient', '!=', False),
        ],
        ['id', 'verification_email_sent_date', 'verification_email_recipient',
         'partner_id', 'phone'],
    )

    if not conversations:
        logger.info("No conversations awaiting email verification. Nothing to do.")
        state['last_run'] = datetime.now().isoformat()
        save_state(state)
        return

    logger.info("Found %d conversation(s) awaiting email verification", len(conversations))

    # Connect to Freescout
    fs_conn = connect_freescout()
    if not fs_conn:
        logger.error("Cannot connect to Freescout. Aborting.")
        return

    resolved_count = 0
    checked_count = 0

    try:
        for conv in conversations:
            conv_id = conv['id']
            recipient = conv['verification_email_recipient']
            verif_date = conv['verification_email_sent_date']
            partner = conv.get('partner_id', [0, ''])[1] if conv.get('partner_id') else 'Unknown'
            phone = conv.get('phone', '')

            logger.info("Checking conversation %d (%s, %s): email=%s, verif_date=%s",
                         conv_id, partner, phone, recipient, verif_date)
            checked_count += 1

            # Look for customer reply in Freescout
            reply_preview = find_email_reply(fs_conn, recipient, verif_date)

            if not reply_preview:
                logger.info("  -> No reply found in Freescout")
                continue

            logger.info("  -> Reply found! Preview: %s", reply_preview[:100])

            if DRY_RUN:
                logger.info("  -> DRY_RUN: Would resolve conversation %d via email", conv_id)
                resolved_count += 1
                continue

            # Resolve the conversation via XML-RPC
            try:
                result = odoo_execute(
                    models, uid,
                    'ai.agent.conversation',
                    'action_resolve_via_email',
                    [conv_id],
                    reply_preview,
                )
                if result:
                    logger.info("  -> Conversation %d resolved successfully", conv_id)
                    resolved_count += 1
                else:
                    logger.warning("  -> Conversation %d: action_resolve_via_email returned False "
                                   "(already resolved or not eligible)", conv_id)
            except Exception as e:
                logger.error("  -> Failed to resolve conversation %d: %s", conv_id, e)

    finally:
        fs_conn.close()
        logger.info("Freescout connection closed")

    state['last_run'] = datetime.now().isoformat()
    save_state(state)

    logger.info("-" * 60)
    logger.info("Summary: checked=%d, resolved=%d%s",
                checked_count, resolved_count, " (DRY RUN)" if DRY_RUN else "")
    logger.info("Done.")


if __name__ == '__main__':
    main()
