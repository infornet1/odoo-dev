#!/usr/bin/env python3
"""
AI Agent Email Checker - Freescout Bridge Script

Detects when customers reply to verification emails in Freescout and
auto-resolves the corresponding Odoo AI Agent conversations via XML-RPC.

Post-processing: updates Freescout conversations with [RESUELTO-AI] prefix,
internal note with Odoo links, and closes the conversation.

Architecture mirrors daily_bounce_processor.py:
  - Odoo XML-RPC for conversation queries + resolution
  - Freescout MySQL (read for detection, write for post-processing)
  - DRY_RUN=True default, state file tracking

Flow:
  1. Query Odoo for conversations with verification_email_sent_date + state=waiting
  2. Query Freescout threads WHERE from LIKE %recipient_email% AND type=1
     (customer reply) AND created_at > verification_date
  3. For matches -> call action_resolve_via_email() via XML-RPC
  4. Post-process Freescout: prefix, internal note, close conversation
  5. Run via crontab every 15 min

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_email_checker.py

Author: Claude Code Assistant
Date: 2026-02-07
Updated: 2026-05-13 — Freescout writes migrated to REST API (PUT /api/conversations,
  POST /api/conversations/{id}/threads). SQL kept for thread/from search (no API equivalent).
"""

import json
import logging
import os
import re
import requests
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
        'url': os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve'),
        'db': os.environ.get('ODOO_DB', 'DB_UEIPAB'),
        'user': os.environ.get('ODOO_USER', 'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}

ODOO_URL = ODOO_CONFIGS[TARGET_ENV]['url']
ODOO_DB = ODOO_CONFIGS[TARGET_ENV]['db']
ODOO_USER = ODOO_CONFIGS[TARGET_ENV]['user']
ODOO_PASSWORD = ODOO_CONFIGS[TARGET_ENV]['password']

# Fail fast if production credentials are missing from environment
if TARGET_ENV == 'production' and not ODOO_PASSWORD:
    raise RuntimeError(
        "ODOO_PASSWORD env var required for TARGET_ENV=production. "
        "Run: source /root/.odoo_agent_env_prod"
    )
if TARGET_ENV == 'production' and not os.environ.get('FREESCOUT_DB_PASSWORD'):
    raise RuntimeError(
        "FREESCOUT_DB_PASSWORD env var required for TARGET_ENV=production. "
        "Run: source /root/.odoo_agent_env_prod"
    )

# Freescout MySQL
FREESCOUT_DB_HOST = os.environ.get('FREESCOUT_DB_HOST', 'localhost')
FREESCOUT_DB_USER = os.environ.get('FREESCOUT_DB_USER', 'free297')
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '')
FREESCOUT_DB_NAME = os.environ.get('FREESCOUT_DB_NAME', 'free297')

# Freescout base URL for hyperlinks in Odoo
FREESCOUT_BASE_URL = 'https://freescout.ueipab.edu.ve'

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
    """Establish MySQL connection to Freescout using pymysql."""
    try:
        import pymysql
    except ImportError:
        logger.error("pymysql not installed. Run: pip install pymysql")
        return None

    logger.info("Connecting to Freescout MySQL at %s...", FREESCOUT_DB_HOST)
    conn = pymysql.connect(
        host=FREESCOUT_DB_HOST,
        user=FREESCOUT_DB_USER,
        password=FREESCOUT_DB_PASSWORD,
        database=FREESCOUT_DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    logger.info("Connected to Freescout MySQL")
    return conn


def get_freescout_admin_id(fs_conn):
    """Get the admin user ID for note authorship."""
    with fs_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return row['id'] if row else 1


def find_email_reply(fs_conn, recipient_email, verification_date):
    """Check if a customer replied to a verification email in Freescout.

    Looks for threads (type=1 = customer message) where:
    - The 'from' field contains the recipient email
    - Created after the verification email was sent

    Returns dict with reply info (preview, conversation_id) or None.
    """
    # Convert datetime string from Odoo to MySQL format
    if isinstance(verification_date, str):
        verif_dt = verification_date.replace('T', ' ')[:19]
    else:
        verif_dt = verification_date.strftime('%Y-%m-%d %H:%M:%S')

    query = """
        SELECT t.id, t.body, t.created_at, t.`from`, t.conversation_id
        FROM threads t
        WHERE t.type = 1
          AND t.`from` LIKE %s
          AND t.created_at > %s
        ORDER BY t.created_at ASC
        LIMIT 1
    """

    with fs_conn.cursor() as cursor:
        cursor.execute(query, (f'%{recipient_email}%', verif_dt))
        result = cursor.fetchone()

    if result:
        body = result.get('body', '')
        preview = re.sub(r'<[^>]+>', '', body).strip()[:300]
        logger.info("Found Freescout reply from %s (thread %d, conv %d): %s",
                     result.get('from', ''), result['id'],
                     result['conversation_id'], preview[:80])
        return {
            'preview': preview,
            'conversation_id': result['conversation_id'],
            'thread_id': result['id'],
        }

    return None


# ============================================================================
# Freescout REST API
# ============================================================================

_FS_API_CFG = None
_FS_STATUS_STR = {1: 'active', 2: 'pending', 3: 'closed',
                  'active': 'active', 'pending': 'pending', 'closed': 'closed'}


def _get_fs_api_cfg():
    global _FS_API_CFG
    if _FS_API_CFG is not None:
        return _FS_API_CFG
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.normpath(os.path.join(script_dir, '..', 'config', 'freescout_api.json')),
        '/home/vision/ueipab17/config/freescout_api.json',
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path) as f:
                _FS_API_CFG = json.load(f)
            logger.info("Freescout API config loaded from %s", path)
            return _FS_API_CFG
    raise RuntimeError("freescout_api.json not found in config dirs")


def _fs_api_headers():
    return {'X-FreeScout-API-Key': _get_fs_api_cfg()['api_key']}


def fs_api_update_conversation(conv_db_id, payload, by_user_id=1):
    """PUT /api/conversations/{id} — update subject/status/assignTo via REST API."""
    cfg = _get_fs_api_cfg()
    if 'status' in payload:
        payload = dict(payload)
        payload['status'] = _FS_STATUS_STR.get(payload['status'], str(payload['status']))
        payload.setdefault('byUser', by_user_id)
    resp = requests.put(
        f"{cfg['api_url']}/conversations/{conv_db_id}",
        json=payload, headers=_fs_api_headers(), timeout=15,
    )
    resp.raise_for_status()
    return resp


def fs_api_add_note(conv_db_id, html_body, user_id=1):
    """POST /api/conversations/{id}/threads — add internal note via REST API."""
    cfg = _get_fs_api_cfg()
    resp = requests.post(
        f"{cfg['api_url']}/conversations/{conv_db_id}/threads",
        json={'type': 'note', 'text': html_body, 'user': user_id},
        headers=_fs_api_headers(), timeout=15,
    )
    resp.raise_for_status()
    return resp


# ============================================================================
# Freescout Post-Processing
# ============================================================================


def build_freescout_note_html(conv_data, reply_info):
    """Build internal note HTML for a Freescout conversation."""
    now = datetime.now().strftime('%d/%m/%Y %H:%M')
    partner_name = conv_data.get('partner_name', 'N/A')
    partner_id = conv_data.get('partner_id_num', 0)
    bounced_email = conv_data.get('verification_email_recipient', '')
    bounce_log_id = conv_data.get('bounce_log_id', 0)
    odoo_conv_id = conv_data.get('id', 0)

    # Odoo contact link
    odoo_contact_html = 'N/A'
    if partner_id:
        odoo_url = f"{ODOO_URL}/web#id={partner_id}&model=res.partner&view_type=form"
        odoo_contact_html = f'<a href="{odoo_url}">{partner_name} (#{partner_id})</a>'

    # Bounce log link
    bounce_log_html = 'N/A'
    if bounce_log_id:
        bl_url = f"{ODOO_URL}/web#id={bounce_log_id}&model=mail.bounce.log&view_type=form"
        bounce_log_html = f'<a href="{bl_url}">Bounce Log #{bounce_log_id}</a>'

    # AI conversation link
    conv_html = 'N/A'
    if odoo_conv_id:
        conv_url = f"{ODOO_URL}/web#id={odoo_conv_id}&model=ai.agent.conversation&view_type=form"
        conv_html = f'<a href="{conv_url}">Conversacion #{odoo_conv_id}</a>'

    return (
        f"<b>AI Agent - Resolucion Automatica por Email</b><br/>"
        f"<b>Email verificado:</b> {bounced_email}<br/>"
        f"<b>Accion:</b> Cliente respondio al correo de verificacion. "
        f"Email restaurado automaticamente.<br/>"
        f"<b>Contacto Odoo:</b> {odoo_contact_html}<br/>"
        f"<b>Bounce Log:</b> {bounce_log_html}<br/>"
        f"<b>Conversacion AI:</b> {conv_html}<br/>"
        f"<b>Fecha:</b> {now}"
    )


def postprocess_freescout(fs_conn, admin_id, fs_conv_id, conv_data, reply_info):
    """Update Freescout conversation: prefix subject, add note, close via REST API.

    SQL used only to read current subject (idempotency guard).
    Writes go through the REST API so folder_id, closed_at, user_updated_at
    and threads_count are handled automatically by Freescout ORM.
    """
    prefix_tag = '[RESUELTO-AI]'

    # SQL read — get current subject for idempotency check
    try:
        with fs_conn.cursor() as cursor:
            cursor.execute(
                "SELECT subject FROM conversations WHERE id = %s",
                (fs_conv_id,))
            row = cursor.fetchone()
    except Exception as e:
        logger.error("  -> Failed to read Freescout conv #%d: %s", fs_conv_id, e)
        return False

    if not row:
        logger.warning("  -> Freescout conv #%d NOT FOUND, skipping post-processing",
                       fs_conv_id)
        return False

    current_subject = row['subject'] or ''

    known_prefixes = ('[RESUELTO-AI]', '[LIMPIADO]', '[REVISION]', '[NO ENCONTRADO]')
    if current_subject.startswith(known_prefixes):
        new_subject = current_subject
    else:
        new_subject = f"{prefix_tag} {current_subject}"

    if DRY_RUN:
        logger.info("  -> DRY_RUN: Would update Freescout conv #%d: "
                    "subject=\"%s\", status=closed, + internal note",
                    fs_conv_id, new_subject[:60])
        return True

    try:
        note_body = build_freescout_note_html(conv_data, reply_info)
        fs_api_update_conversation(
            fs_conv_id,
            {'subject': new_subject, 'status': 'closed'},
            by_user_id=admin_id,
        )
        fs_api_add_note(fs_conv_id, note_body, user_id=admin_id)
        logger.info("  -> Freescout conv #%d: updated via API (subject, note, closed)",
                    fs_conv_id)
        return True
    except Exception as e:
        logger.error("  -> Failed to update Freescout conv #%d via API: %s", fs_conv_id, e)
        return False


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
         'partner_id', 'phone', 'source_model', 'source_id'],
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

    admin_id = get_freescout_admin_id(fs_conn)
    logger.info("Freescout admin user_id=%d", admin_id)

    resolved_count = 0
    checked_count = 0
    fs_updated_count = 0

    try:
        for conv in conversations:
            conv_id = conv['id']
            recipient = conv['verification_email_recipient']
            verif_date = conv['verification_email_sent_date']
            partner_tuple = conv.get('partner_id')
            partner_name = partner_tuple[1] if partner_tuple else 'Unknown'
            partner_id_num = partner_tuple[0] if partner_tuple else 0
            phone = conv.get('phone', '')
            source_model = conv.get('source_model', '')
            source_id = conv.get('source_id', 0)

            # Build enriched conv_data for Freescout note
            conv_data = {
                'id': conv_id,
                'verification_email_recipient': recipient,
                'partner_name': partner_name,
                'partner_id_num': partner_id_num,
                'bounce_log_id': source_id if source_model == 'mail.bounce.log' else 0,
            }

            logger.info("Checking conversation %d (%s, %s): email=%s, verif_date=%s",
                         conv_id, partner_name, phone, recipient, verif_date)
            checked_count += 1

            # Look for customer reply in Freescout
            reply_info = find_email_reply(fs_conn, recipient, verif_date)

            if not reply_info:
                logger.info("  -> No reply found in Freescout")
                continue

            logger.info("  -> Reply found! Freescout conv #%d, preview: %s",
                         reply_info['conversation_id'], reply_info['preview'][:100])

            if DRY_RUN:
                logger.info("  -> DRY_RUN: Would resolve conversation %d via email", conv_id)
                # Still show what Freescout post-processing would do
                postprocess_freescout(fs_conn, admin_id,
                                      reply_info['conversation_id'],
                                      conv_data, reply_info)
                resolved_count += 1
                continue

            # Resolve the conversation via XML-RPC
            try:
                result = odoo_execute(
                    models, uid,
                    'ai.agent.conversation',
                    'action_resolve_via_email',
                    [conv_id],
                    reply_info['preview'],
                )
                if result:
                    logger.info("  -> Conversation %d resolved successfully in Odoo", conv_id)
                    resolved_count += 1

                    # Post-process Freescout conversation
                    if postprocess_freescout(fs_conn, admin_id,
                                             reply_info['conversation_id'],
                                             conv_data, reply_info):
                        fs_updated_count += 1
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
    logger.info("Summary: checked=%d, resolved=%d, freescout_updated=%d%s",
                checked_count, resolved_count, fs_updated_count,
                " (DRY RUN)" if DRY_RUN else "")
    logger.info("Done.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='AI Agent Email Checker')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (resolve conversations for real)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False

    main()
