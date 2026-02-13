#!/usr/bin/env python3
"""
AI Agent Escalation Bridge - Freescout Ticket + WhatsApp Group Notification

Creates Freescout support tickets for escalated AI Agent conversations and
notifies the "ueipab soporte" WhatsApp group for fast pickup.

Architecture mirrors daily_bounce_processor.py / ai_agent_email_checker.py:
  - Odoo XML-RPC for querying pending escalations + updating ticket numbers
  - Freescout MySQL (direct INSERT) for ticket creation
  - MassivaMóvil WhatsApp API for group notification

Flow:
  1. Query Odoo for conversations with escalation_date but no freescout ticket
  2. Create Freescout conversation + initial thread for each
  3. Send WhatsApp notification to support group
  4. Update Odoo with Freescout ticket number

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py           # dry run
    python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py --live    # apply real changes

Author: Claude Code Assistant
Date: 2026-02-08
"""

import argparse
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime

import pymysql
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

# Freescout MySQL
FREESCOUT_DB_HOST = os.environ.get('FREESCOUT_DB_HOST', 'localhost')
FREESCOUT_DB_USER = os.environ.get('FREESCOUT_DB_USER', 'free297')
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '1gczp1S@3!')
FREESCOUT_DB_NAME = os.environ.get('FREESCOUT_DB_NAME', 'free297')
FREESCOUT_BASE_URL = 'https://soporte.ueipab.edu.ve'

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


def connect_freescout():
    """Connect to Freescout MySQL."""
    logger.info("Connecting to Freescout MySQL at %s...", FREESCOUT_DB_HOST)
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


def get_freescout_admin_id(fs_conn):
    """Get admin user ID from Freescout for thread author."""
    with fs_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE role = 2 ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return row['id'] if row else 1


def get_freescout_mailbox_id(fs_conn):
    """Get Soporte mailbox ID from Freescout."""
    with fs_conn.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM mailboxes WHERE email = 'soporte@ueipab.edu.ve' "
            "ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row['id']
        # Fallback to first mailbox
        cursor.execute("SELECT id FROM mailboxes ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return row['id'] if row else 1


def get_freescout_inbox_folder(fs_conn, mailbox_id):
    """Get the Inbox folder (type=1) for a mailbox."""
    with fs_conn.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM folders "
            "WHERE mailbox_id = %s AND type = 1 AND user_id IS NULL LIMIT 1",
            (mailbox_id,),
        )
        row = cursor.fetchone()
        return row['id'] if row else 1


def get_next_conversation_number(fs_conn):
    """Get next conversation number for Freescout."""
    with fs_conn.cursor() as cursor:
        cursor.execute("SELECT COALESCE(MAX(number), 0) + 1 AS next_num FROM conversations")
        row = cursor.fetchone()
        return int(row['next_num'])


def find_or_create_customer(fs_conn, email, first_name, last_name):
    """Find or create a Freescout customer by email.

    Freescout stores emails in a separate `emails` table (not on customers directly).
    """
    with fs_conn.cursor() as cursor:
        # Look up via emails table
        cursor.execute(
            "SELECT customer_id FROM emails WHERE email = %s LIMIT 1", (email,))
        row = cursor.fetchone()
        if row:
            return row['customer_id']

        # Create new customer
        cursor.execute(
            "INSERT INTO customers (first_name, last_name, created_at, updated_at) "
            "VALUES (%s, %s, NOW(), NOW())",
            (first_name, last_name),
        )
        customer_id = cursor.lastrowid

        # Create email record
        cursor.execute(
            "INSERT INTO emails (customer_id, email, type, created_at, updated_at) "
            "VALUES (%s, %s, 1, NOW(), NOW())",
            (customer_id, email),
        )
        fs_conn.commit()
        return customer_id


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
    print(f"  Freescout: {FREESCOUT_DB_HOST} / {FREESCOUT_DB_NAME}")
    print(f"  WA Group:  {WA_GROUP_ID}")
    print()

    # Phase 1: Connect
    uid, models = connect_odoo()
    fs_conn = connect_freescout()
    wa_config = load_whatsapp_config()
    admin_id = get_freescout_admin_id(fs_conn)
    mailbox_id = get_freescout_mailbox_id(fs_conn)
    inbox_folder_id = get_freescout_inbox_folder(fs_conn, mailbox_id)
    logger.info("Freescout admin_id=%d, mailbox_id=%d, inbox_folder=%d",
                admin_id, mailbox_id, inbox_folder_id)

    # Phase 2: Query pending escalations
    # Note: Odoo ORM treats Integer=0 as False in search, so we search
    # by escalation_date and filter client-side for freescout_id == 0.
    print("\n--- Phase 2: Query Pending Escalations ---")
    all_escalated = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'ai.agent.conversation', 'search_read',
        [[
            ('escalation_date', '!=', False),
        ]],
        {'fields': [
            'partner_id', 'phone', 'escalation_reason',
            'escalation_freescout_id', 'escalation_notified',
            'source_model', 'source_id', 'name',
        ]},
    )
    pending = [e for e in all_escalated if not e['escalation_freescout_id']]

    if not pending:
        print("  No pending escalations found.")
        fs_conn.close()
        return

    print(f"  Found {len(pending)} pending escalation(s)")
    for esc in pending:
        partner_name = esc['partner_id'][1] if esc['partner_id'] else 'Desconocido'
        print(f"    Conv #{esc['id']}: {partner_name} — {(esc['escalation_reason'] or '')[:80]}")

    # Phase 3: Create Freescout tickets
    print("\n--- Phase 3: Create Freescout Tickets ---")
    created_tickets = []

    for esc in pending:
        conv_id = esc['id']
        partner_name = esc['partner_id'][1] if esc['partner_id'] else 'Desconocido'
        partner_id = esc['partner_id'][0] if esc['partner_id'] else 0
        phone = esc['phone'] or ''
        reason = esc['escalation_reason'] or 'Sin detalle'

        # Get partner email for Freescout customer lookup
        partner_email = ''
        if partner_id:
            partner_data = models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'read',
                [partner_id],
                {'fields': ['email']},
            )
            if partner_data:
                partner_email = partner_data[0].get('email', '') or ''

        subject = f"[ESCALACION-AI] Requerimiento de {partner_name}"
        conv_number = get_next_conversation_number(fs_conn)

        # Build thread body
        odoo_conv_url = (
            f"{ODOO_URL}/web#id={conv_id}"
            f"&model=ai.agent.conversation&view_type=form"
        )
        odoo_partner_url = (
            f"{ODOO_URL}/web#id={partner_id}"
            f"&model=res.partner&view_type=form"
        ) if partner_id else ''

        now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        thread_body = (
            f"<h3>Escalacion desde AI Agent</h3>"
            f"<p><strong>Fecha:</strong> {now_str}</p>"
            f"<p><strong>Cliente:</strong> {partner_name}"
        )
        if partner_email:
            thread_body += f" ({partner_email})"
        thread_body += f"</p>"
        thread_body += f"<p><strong>Telefono:</strong> {phone}</p>"
        thread_body += f"<p><strong>Motivo:</strong></p><pre>{reason}</pre>"
        thread_body += f"<hr/>"
        thread_body += f'<p><a href="{odoo_conv_url}">Ver conversacion en Odoo</a></p>'
        if odoo_partner_url:
            thread_body += f'<p><a href="{odoo_partner_url}">Ver contacto en Odoo</a></p>'

        if DRY_RUN:
            print(f"  DRY_RUN: Would create Freescout ticket #{conv_number}")
            print(f"    Subject: {subject}")
            print(f"    Customer: {partner_name} <{partner_email}>")
            print(f"    Reason: {reason[:100]}")
            created_tickets.append({
                'conv_id': conv_id,
                'fs_number': conv_number,
                'partner_name': partner_name,
                'phone': phone,
                'reason': reason,
                'dry_run': True,
            })
            continue

        try:
            # Find or create Freescout customer
            name_parts = partner_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            customer_email = partner_email or f"noemail-{partner_id}@placeholder.local"
            customer_id = find_or_create_customer(
                fs_conn, customer_email, first_name, last_name,
            )

            with fs_conn.cursor() as cursor:
                # INSERT conversation
                preview = reason[:255] if reason else subject[:255]
                cursor.execute("""
                    INSERT INTO conversations
                        (number, `type`, folder_id, status, state, subject, preview,
                         mailbox_id, customer_id, customer_email,
                         threads_count, created_by_user_id, source_via, source_type,
                         created_at, updated_at, last_reply_at)
                    VALUES (%s, 1, %s, 1, 1, %s, %s,
                            %s, %s, %s,
                            1, %s, 2, 2,
                            NOW(), NOW(), NOW())
                """, (conv_number, inbox_folder_id, subject, preview, mailbox_id,
                      customer_id, customer_email, admin_id))

                conversation_db_id = cursor.lastrowid

                # INSERT initial thread (customer message type)
                cursor.execute("""
                    INSERT INTO threads
                        (conversation_id, `type`, body, state, status,
                         source_via, source_type,
                         created_by_user_id, user_id,
                         `from`, customer_id,
                         created_at, updated_at)
                    VALUES (%s, 1, %s, 2, 6,
                            2, 2,
                            %s, %s,
                            %s, %s,
                            NOW(), NOW())
                """, (conversation_db_id, thread_body,
                      admin_id, admin_id,
                      customer_email, customer_id))

            fs_conn.commit()
            logger.info("Freescout ticket #%d created for conv #%d", conv_number, conv_id)

            # Update Odoo with ticket number
            models.execute_kw(
                ODOO_DB, uid, ODOO_PASSWORD,
                'ai.agent.conversation', 'write',
                [[conv_id], {'escalation_freescout_id': conv_number}],
            )

            created_tickets.append({
                'conv_id': conv_id,
                'fs_number': conv_number,
                'partner_name': partner_name,
                'phone': phone,
                'reason': reason,
                'dry_run': False,
            })

        except Exception as e:
            logger.error("Error creating ticket for conv #%d: %s", conv_id, e)
            try:
                fs_conn.rollback()
            except Exception:
                pass

    # Phase 4: Send WhatsApp group notifications
    print(f"\n--- Phase 4: WhatsApp Group Notifications ---")
    notified = 0

    for ticket in created_tickets:
        conv_id = ticket['conv_id']
        fs_number = ticket['fs_number']
        partner_name = ticket['partner_name']
        phone = ticket['phone']
        reason = ticket['reason']

        # Truncate reason for WhatsApp
        reason_short = reason.split('\n')[0]  # first entry
        reason_short = reason_short.lstrip('[0123456789- :]')  # strip timestamp prefix
        if len(reason_short) > 150:
            reason_short = reason_short[:147] + '...'

        fs_url = f"{FREESCOUT_BASE_URL}/conversation/{fs_number}"
        odoo_url = (
            f"{ODOO_URL}/web#id={conv_id}"
            f"&model=ai.agent.conversation&view_type=form"
        )

        message = (
            f"\U0001f4cb *Nuevo Ticket de Soporte #{fs_number}*\n"
            f"Cliente: {partner_name}\n"
            f"Telefono: {phone}\n"
            f"Motivo: {reason_short}\n"
            f"\U0001f517 Freescout: {fs_url}\n"
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

    # Phase 5: Handle subsequent escalations (add notes to existing tickets)
    # Conversations that already have a Freescout ticket but have new un-notified
    # escalation entries (escalation_notified was reset by _handle_escalation...
    # actually it's not reset, but we keep this for future multi-escalation notes).
    # Filter from all_escalated: has ticket AND not notified.
    print(f"\n--- Phase 5: Check for Additional Escalations ---")
    subsequent = [
        e for e in all_escalated
        if e['escalation_freescout_id'] and not e['escalation_notified']
    ]

    if subsequent:
        print(f"  Found {len(subsequent)} conversation(s) with new escalation notes")
        for esc in subsequent:
            conv_id = esc['id']
            fs_number = esc['escalation_freescout_id']
            reason = esc['escalation_reason'] or ''
            partner_name = esc['partner_id'][1] if esc['partner_id'] else 'Desconocido'

            # Get last entry (newest escalation)
            lines = [l for l in reason.strip().split('\n') if l.strip()]
            last_entry = lines[-1] if lines else reason

            if DRY_RUN:
                print(f"  DRY_RUN: Would add note to Freescout #{fs_number}: {last_entry[:80]}")
            else:
                try:
                    # Find Freescout conversation DB id by number
                    with fs_conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT id FROM conversations WHERE number = %s",
                            (fs_number,),
                        )
                        row = cursor.fetchone()
                        if not row:
                            logger.warning("Freescout conversation #%d not found", fs_number)
                            continue

                        fs_conv_db_id = row['id']
                        note_body = (
                            f"<p><strong>Escalacion adicional:</strong></p>"
                            f"<pre>{last_entry}</pre>"
                        )
                        cursor.execute("""
                            INSERT INTO threads
                                (conversation_id, `type`, body, state, status,
                                 source_via, source_type,
                                 created_by_user_id, user_id,
                                 created_at, updated_at)
                            VALUES (%s, 3, %s, 2, 6,
                                    2, 2,
                                    %s, %s,
                                    NOW(), NOW())
                        """, (fs_conv_db_id, note_body, admin_id, admin_id))

                        cursor.execute(
                            "UPDATE conversations SET threads_count = threads_count + 1 "
                            "WHERE id = %s",
                            (fs_conv_db_id,),
                        )

                    fs_conn.commit()
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'ai.agent.conversation', 'write',
                        [[conv_id], {'escalation_notified': True}],
                    )
                    logger.info("Added note to Freescout #%d for conv #%d", fs_number, conv_id)
                except Exception as e:
                    logger.error("Error adding note to Freescout #%d: %s", fs_number, e)
                    try:
                        fs_conn.rollback()
                    except Exception:
                        pass
    else:
        print("  No additional escalation notes pending.")

    # Summary
    fs_conn.close()
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Pending escalations found: {len(pending)}")
    print(f"  Tickets created: {len(created_tickets)}")
    if not DRY_RUN:
        print(f"  Group notifications sent: {notified}")
    if subsequent:
        print(f"  Additional notes added: {len(subsequent)}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Agent Escalation Bridge')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (create real tickets + notify)')
    args = parser.parse_args()
    if args.live:
        DRY_RUN = False
    try:
        main()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
