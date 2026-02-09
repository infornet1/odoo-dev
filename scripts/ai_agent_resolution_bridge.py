#!/usr/bin/env python3
"""
AI Agent Resolution Bridge — Freescout + Google Sheets Post-Processing

When Glenda resolves a bounce via WhatsApp, Odoo is updated (partner email,
mailing contacts, bounce log state) but two external systems are NOT:
  1. Freescout — the original bounce conversation stays open
  2. Google Sheets "Customers" tab — still shows the bounced email

This bridge script closes the loop:
  - Updates Freescout: subject prefix, internal note, close or assign
  - Updates Customers tab: remove bounced email from semicolon-separated list
  - Checks Akdemia2526 tab: if bounced email exists there, assign Freescout
    ticket to Alejandra Lopez (user_id=6) for manual Akdemia cleanup

Flow:
  1. Connect to Odoo (XML-RPC), Freescout (MySQL), Google Sheets (gspread)
  2. Query Odoo for resolved bounce logs with freescout_conversation_id
  3. Skip already-processed (Freescout subject starts with [RESUELTO-AI])
  4. For each unprocessed:
     a. Check Akdemia2526 for bounced email
     b. Update Freescout (subject, note, status/assignment)
     c. Update Customers tab (remove bounced email)

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_resolution_bridge.py
    python3 /opt/odoo-dev/scripts/ai_agent_resolution_bridge.py --live

Author: Claude Code Assistant
Date: 2026-02-09
"""

import argparse
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime

import pymysql

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True  # True = no modifications, False = apply changes
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

# Alejandra Lopez — Freescout user for Akdemia cleanup
ALEJANDRA_USER_ID = 6

# Google Sheets
SHEETS_CREDENTIALS = '/opt/odoo-dev/config/google_sheets_credentials.json'
SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
CUSTOMERS_TAB = 'Customers'
CUSTOMERS_HEADER_ROW = 2  # headers at row 2 (1-indexed)
CUSTOMERS_DATA_START = 3  # data starts at row 3
CUSTOMERS_VAT_COL = 'A'   # Registration/VAT column
CUSTOMERS_EMAIL_COL = 'J'  # Email column
AKDEMIA_TAB = 'Akdemia2526'

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helpers — Odoo
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


def odoo_search_read(models, uid, model, domain, fields):
    """Helper for Odoo search_read."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        [domain], {'fields': fields},
    )


# ============================================================================
# Helpers — Freescout
# ============================================================================

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


def get_freescout_admin_id(fs_conn):
    """Get admin user ID from Freescout for thread author."""
    with fs_conn.cursor() as cursor:
        cursor.execute("SELECT id FROM users WHERE role = 2 ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        return row['id'] if row else 1


def get_freescout_folder(fs_conn, mailbox_id, folder_type, user_id=None):
    """Get Freescout folder ID by type and optional user.

    Folder types (from Freescout Folder.php constants):
        1=Unassigned(Inbox), 20=Mine(per-user), 25=Starred(per-user),
        30=Drafts, 40=Assigned, 60=Closed, 70=Deleted, 80=Spam.
    Mine (type=20) folders are per-user — requires user_id.
    """
    with fs_conn.cursor() as cursor:
        if user_id:
            cursor.execute(
                "SELECT id FROM folders "
                "WHERE mailbox_id = %s AND type = %s AND user_id = %s LIMIT 1",
                (mailbox_id, folder_type, user_id),
            )
        else:
            cursor.execute(
                "SELECT id FROM folders "
                "WHERE mailbox_id = %s AND type = %s AND user_id IS NULL LIMIT 1",
                (mailbox_id, folder_type),
            )
        row = cursor.fetchone()
        return row['id'] if row else None


def get_freescout_conversation(fs_conn, conversation_id):
    """Get Freescout conversation by database ID. Returns dict or None.

    Note: freescout_conversation_id in Odoo stores the Freescout DB id,
    not the conversation number.
    """
    with fs_conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, number, subject, status, user_id, mailbox_id "
            "FROM conversations WHERE id = %s LIMIT 1",
            (conversation_id,),
        )
        return cursor.fetchone()


# ============================================================================
# Helpers — Google Sheets
# ============================================================================

def connect_sheets():
    """Connect to Google Sheets, return (spreadsheet, gc)."""
    import gspread
    from google.oauth2.service_account import Credentials

    if not os.path.exists(SHEETS_CREDENTIALS):
        raise RuntimeError(f"Google Sheets credentials not found: {SHEETS_CREDENTIALS}")

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_file(SHEETS_CREDENTIALS, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    logger.info("Google Sheets connected (spreadsheet: %s)", SPREADSHEET_ID)
    return spreadsheet, gc


def load_akdemia_emails(spreadsheet):
    """Load all email addresses from Akdemia2526 tab.

    Returns a set of lowercase email addresses found in email columns.
    Akdemia2526 email columns (0-indexed): 46 (AU), 75 (BX), 104 (DA).
    """
    try:
        ws = spreadsheet.worksheet(AKDEMIA_TAB)
    except Exception:
        logger.warning("Akdemia2526 tab not found, skipping Akdemia check")
        return set()

    all_values = ws.get_all_values()
    akdemia_emails = set()
    # Email columns (0-indexed): 46=AU (parent 1), 75=BX (parent 2), 104=DA (parent 3)
    email_col_indices = [46, 75, 104]

    # Data starts at row 4 (index 3) — rows 0-2 are metadata + headers
    for row_idx in range(3, len(all_values)):
        row = all_values[row_idx]
        for col_idx in email_col_indices:
            if col_idx < len(row):
                val = row[col_idx].strip().lower()
                if val and val != 'nan' and '@' in val:
                    akdemia_emails.add(val)

    logger.info("Loaded %d unique emails from Akdemia2526", len(akdemia_emails))
    return akdemia_emails


def update_customers_email(spreadsheet, partner_vat, bounced_email, new_email=''):
    """Update email in the Customers tab: remove bounced, add new if provided.

    Finds the row by VAT (column A), reads email cell (column J),
    removes the bounced email from the semicolon-separated list,
    adds new_email if provided and not already present,
    and writes back the cleaned value.

    Returns True if updated, False if not found or no change needed.
    """
    try:
        ws = spreadsheet.worksheet(CUSTOMERS_TAB)
    except Exception:
        logger.warning("Customers tab not found, skipping Sheets update")
        return False

    if not partner_vat:
        return False

    # Get all VAT values from column A to find the row
    vat_values = ws.col_values(1)  # column A = 1

    # Normalize VAT for comparison (strip whitespace, uppercase)
    target_vat = partner_vat.strip().upper()
    target_row = None

    for idx, val in enumerate(vat_values):
        if idx < CUSTOMERS_HEADER_ROW:  # skip header rows (0-indexed: row 0 and 1)
            continue
        if val.strip().upper() == target_vat:
            target_row = idx + 1  # gspread uses 1-indexed rows
            break

    if not target_row:
        logger.info("  VAT %s not found in Customers tab", partner_vat)
        return False

    # Read current email cell (column J = 10)
    current_email = ws.cell(target_row, 10).value or ''

    if not current_email:
        logger.info("  Row %d: email cell is empty, nothing to clean", target_row)
        return False

    # Remove bounced email from semicolon-separated list
    emails = [e.strip() for e in current_email.split(';') if e.strip()]
    cleaned = [e for e in emails if e.lower() != bounced_email.strip().lower()]

    # Add new email if provided and not already present
    if new_email and new_email.strip().lower() not in [e.lower() for e in cleaned]:
        cleaned.append(new_email.strip())

    if cleaned == emails:
        logger.info("  Row %d: no change needed for '%s'", target_row, current_email)
        return False

    new_value = ';'.join(cleaned)
    logger.info("  Row %d: '%s' → '%s'", target_row, current_email, new_value)

    if not DRY_RUN:
        ws.update_cell(target_row, 10, new_value)

    return True


# ============================================================================
# Main Logic
# ============================================================================

def close_related_conversations(fs_conn, admin_id, bounced_email, primary_fs_id,
                                partner_name, odoo_bl_url):
    """Close other active Freescout conversations that mention the bounced email.

    DSN conversations have customer_email=mailer-daemon@googlemail.com, so the
    bounced address only appears in the thread body. This searches thread bodies
    for the bounced email and closes any matching active conversations that
    weren't already processed.

    Returns count of conversations closed.
    """
    prefix = "[DRY_RUN] " if DRY_RUN else ""

    with fs_conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT c.id, c.number, c.subject, c.mailbox_id
            FROM conversations c
            JOIN threads t ON t.conversation_id = c.id
            WHERE c.status = 1
              AND c.id != %s
              AND c.subject NOT LIKE '[RESUELTO-AI]%%'
              AND t.body LIKE %s
        """, (primary_fs_id, f'%{bounced_email}%'))
        related = cursor.fetchall()

    if not related:
        return 0

    print(f"  {prefix}Found {len(related)} related active conversation(s) for '{bounced_email}':")
    for r in related:
        print(f"    #{r['number']} (id={r['id']}): {r['subject'][:70]}")

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    note_body = (
        f"<p><strong>Cerrado automaticamente</strong> — el email rebotado "
        f"<code>{bounced_email}</code> de <strong>{partner_name}</strong> "
        f"ha sido resuelto.</p>"
        f"<p><strong>Fecha:</strong> {now_str}</p>"
        f'<p><a href="{odoo_bl_url}">Ver bounce log en Odoo</a></p>'
    )

    closed = 0
    if not DRY_RUN:
        try:
            with fs_conn.cursor() as cursor:
                for r in related:
                    new_subject = f"[RESUELTO-AI] {r['subject']}"
                    # Get Closed folder (type=60) for this conversation's mailbox
                    closed_folder = get_freescout_folder(
                        fs_conn, r['mailbox_id'], 60)
                    if closed_folder:
                        cursor.execute(
                            "UPDATE conversations SET subject = %s, status = 3, "
                            "folder_id = %s, updated_at = NOW(), "
                            "user_updated_at = NOW() WHERE id = %s",
                            (new_subject, closed_folder, r['id']),
                        )
                    else:
                        cursor.execute(
                            "UPDATE conversations SET subject = %s, status = 3, "
                            "updated_at = NOW(), user_updated_at = NOW() "
                            "WHERE id = %s",
                            (new_subject, r['id']),
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
                    """, (r['id'], note_body, admin_id, admin_id))
                    cursor.execute(
                        "UPDATE conversations SET threads_count = threads_count + 1 "
                        "WHERE id = %s",
                        (r['id'],),
                    )
                    closed += 1
            fs_conn.commit()
        except Exception as e:
            logger.error("  Error closing related conversations: %s", e)
            try:
                fs_conn.rollback()
            except Exception:
                pass
    else:
        closed = len(related)

    return closed


def get_resolved_bounce_logs(models, uid):
    """Query Odoo for resolved bounce logs with Freescout conversation ID.

    Uses broader domain + client-side filter due to Odoo Integer=0 quirk.
    """
    all_resolved = odoo_search_read(
        models, uid, 'mail.bounce.log',
        [('state', '=', 'resolved')],
        [
            'id', 'bounced_email', 'new_email', 'partner_id',
            'freescout_conversation_id', 'action_tier',
            'resolved_date', 'resolved_by',
        ],
    )

    # Filter: must have a real Freescout conversation ID (> 0)
    with_freescout = [
        bl for bl in all_resolved
        if bl.get('freescout_conversation_id') and bl['freescout_conversation_id'] > 0
    ]

    return with_freescout


def process_bounce_log(bl, fs_conn, admin_id, akdemia_emails, spreadsheet, models, uid):
    """Process a single resolved bounce log.

    Returns 'processed', 'skipped', or 'error'.
    """
    bl_id = bl['id']
    bounced_email = (bl.get('bounced_email') or '').strip().lower()
    new_email = (bl.get('new_email') or '').strip()
    fs_conv_number = bl['freescout_conversation_id']
    partner_name = bl['partner_id'][1] if bl['partner_id'] else 'Desconocido'
    partner_id = bl['partner_id'][0] if bl['partner_id'] else 0
    action_tier = bl.get('action_tier') or ''
    resolved_date = bl.get('resolved_date') or ''
    resolved_by = bl.get('resolved_by')
    resolved_by_name = resolved_by[1] if resolved_by else 'Sistema'

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    # --- Step 1: Check Freescout conversation ---
    fs_conv = get_freescout_conversation(fs_conn, fs_conv_number)
    if not fs_conv:
        logger.warning("  Freescout conversation #%d not found, skipping", fs_conv_number)
        return 'error'

    fs_db_id = fs_conv['id']
    primary_already_done = fs_conv['subject'] and fs_conv['subject'].startswith('[RESUELTO-AI]')

    # Already processed? Still run related-conversations cleanup, then skip rest
    if primary_already_done:
        logger.info("  Freescout #%d primary already processed", fs_conv_number)
        # Build odoo_bl_url for related cleanup
        odoo_bl_url = f"{ODOO_URL}/web#id={bl_id}&model=mail.bounce.log&view_type=form"
        if bounced_email:
            related_closed = close_related_conversations(
                fs_conn, admin_id, bounced_email, fs_db_id, partner_name, odoo_bl_url,
            )
            if related_closed:
                print(f"  {prefix}Closed {related_closed} related Freescout conversation(s)")
                return 'processed'
        return 'skipped'

    original_subject = fs_conv['subject'] or 'Delivery Status Notification'

    # --- Step 2: Check Akdemia2526 for bounced email ---
    in_akdemia = bounced_email in akdemia_emails if bounced_email else False
    if in_akdemia:
        logger.info("  Bounced email '%s' FOUND in Akdemia2526 — Alejandra assignment needed",
                     bounced_email)
    else:
        logger.info("  Bounced email '%s' NOT in Akdemia2526 — will close conversation",
                     bounced_email)

    # --- Step 3: Get partner details for note ---
    partner_vat = ''
    partner_current_email = ''
    if partner_id:
        partner_data = odoo_search_read(
            models, uid, 'res.partner',
            [('id', '=', partner_id)],
            ['vat', 'email'],
        )
        if partner_data:
            partner_vat = partner_data[0].get('vat') or ''
            partner_current_email = partner_data[0].get('email') or ''

    # --- Step 4: Update Freescout ---
    fs_mailbox_id = fs_conv.get('mailbox_id')
    if in_akdemia:
        new_subject = '[RESUELTO-AI] Se requiere actualización de correo electrónico en Akdemia'
        new_status = 1  # Keep Active — Alejandra closes after updating Akdemia
        assign_to = ALEJANDRA_USER_ID
        # Move to Assigned folder (type=40) — shared folder for all assigned convs
        new_folder_id = get_freescout_folder(fs_conn, fs_mailbox_id, 40)
    else:
        new_subject = f'[RESUELTO-AI] {original_subject}'
        new_status = 3  # Closed
        assign_to = None
        # Move to Closed folder (type=60)
        new_folder_id = get_freescout_folder(fs_conn, fs_mailbox_id, 60)

    # Build internal note body
    odoo_bl_url = f"{ODOO_URL}/web#id={bl_id}&model=mail.bounce.log&view_type=form"
    odoo_partner_url = f"{ODOO_URL}/web#id={partner_id}&model=res.partner&view_type=form"
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Resolution summary
    if action_tier == 'clean':
        resolution_action = f"Email <code>{bounced_email}</code> eliminado del contacto (rebote permanente)"
    elif new_email:
        resolution_action = f"Email <code>{bounced_email}</code> reemplazado por <code>{new_email}</code>"
    else:
        resolution_action = f"Email <code>{bounced_email}</code> restaurado en el contacto"

    note_body = (
        f"<h3>Resolucion de Rebote (AI Agent)</h3>"
        f"<p><strong>Fecha:</strong> {now_str}</p>"
        f"<p><strong>Contacto:</strong> {partner_name}</p>"
        f"<p><strong>Accion:</strong> {resolution_action}</p>"
    )
    if partner_current_email:
        note_body += f"<p><strong>Emails actuales:</strong> <code>{partner_current_email}</code></p>"
    note_body += f"<p><strong>Resuelto por:</strong> {resolved_by_name}</p>"
    if in_akdemia:
        note_body += f"<hr/>"
        if new_email:
            note_body += (
                f"<p><strong>⚠ Accion requerida en Akdemia:</strong> "
                f"Reemplazar el correo <code>{bounced_email}</code> "
                f"por <code>{new_email}</code> en la plataforma Akdemia.</p>"
            )
        else:
            note_body += (
                f"<p><strong>⚠ Accion requerida en Akdemia:</strong> "
                f"Eliminar el correo <code>{bounced_email}</code> "
                f"de la plataforma Akdemia (correo restaurado o removido).</p>"
            )
    note_body += f"<hr/>"
    note_body += f'<p><a href="{odoo_bl_url}">Ver bounce log en Odoo</a></p>'
    note_body += f'<p><a href="{odoo_partner_url}">Ver contacto en Odoo</a></p>'

    print(f"  {prefix}Freescout #{fs_conv_number}:")
    print(f"    Subject: {new_subject}")
    print(f"    Status: {new_status} ({'Active (Alejandra)' if new_status == 1 else 'Closed'})")
    if assign_to:
        print(f"    Assign to: user_id={assign_to} (Alejandra Lopez)")
    if new_folder_id:
        print(f"    Folder: {new_folder_id} ({'Assigned' if assign_to else 'Closed'})")
    print(f"    Internal note: resolution summary added")

    if not DRY_RUN:
        try:
            with fs_conn.cursor() as cursor:
                # Update conversation subject + status + assignment + folder
                if assign_to and new_folder_id:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s, "
                        "user_id = %s, folder_id = %s, "
                        "updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, assign_to, new_folder_id, fs_db_id),
                    )
                elif new_folder_id:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s, "
                        "folder_id = %s, "
                        "updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, new_folder_id, fs_db_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s, "
                        "updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, fs_db_id),
                    )

                # Add internal note thread
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
                """, (fs_db_id, note_body, admin_id, admin_id))

                # Update threads_count
                cursor.execute(
                    "UPDATE conversations SET threads_count = threads_count + 1 "
                    "WHERE id = %s",
                    (fs_db_id,),
                )

            fs_conn.commit()
            logger.info("  Freescout #%d updated", fs_conv_number)
        except Exception as e:
            logger.error("  Error updating Freescout #%d: %s", fs_conv_number, e)
            try:
                fs_conn.rollback()
            except Exception:
                pass
            return 'error'

    # --- Step 5: Close related Freescout conversations ---
    if bounced_email:
        related_closed = close_related_conversations(
            fs_conn, admin_id, bounced_email, fs_db_id, partner_name, odoo_bl_url,
        )
        if related_closed:
            print(f"  {prefix}Closed {related_closed} related Freescout conversation(s)")

    # --- Step 6: Update Customers Google Sheet ---
    if spreadsheet and partner_vat and bounced_email:
        action_desc = f"replacing '{bounced_email}' with '{new_email}'" if new_email else f"removing '{bounced_email}'"
        print(f"  {prefix}Customers tab: {action_desc} for VAT={partner_vat}")
        try:
            updated = update_customers_email(spreadsheet, partner_vat, bounced_email, new_email)
            if updated:
                print(f"  {prefix}Customers tab updated")
            else:
                print(f"  Customers tab: no change needed (not found or already clean)")
        except Exception as e:
            logger.error("  Error updating Customers tab: %s", e)
    else:
        if not partner_vat:
            print(f"  Skipping Customers tab: no VAT on partner")

    return 'processed'


def main():
    parser = argparse.ArgumentParser(description='AI Agent Resolution Bridge')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (apply real changes)')
    parser.add_argument('--skip-sheets', action='store_true',
                        help='Skip Google Sheets operations')
    parser.add_argument('--id', type=int,
                        help='Process only this bounce log ID')
    args = parser.parse_args()

    global DRY_RUN
    if args.live:
        DRY_RUN = False

    print("=" * 70)
    print("AI AGENT RESOLUTION BRIDGE")
    print("=" * 70)
    print(f"  Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN:   {DRY_RUN}")
    print(f"  Target:    {TARGET_ENV}")
    print(f"  Odoo:      {ODOO_URL} / {ODOO_DB}")
    print(f"  Freescout: {FREESCOUT_DB_HOST} / {FREESCOUT_DB_NAME}")
    print(f"  Sheets:    {'enabled' if not args.skip_sheets else 'disabled'}")
    if args.id:
        print(f"  Filter:    BL#{args.id} only")
    print()

    # Phase 1: Connect
    print("--- Phase 1: Connect ---")
    uid, models = connect_odoo()
    fs_conn = connect_freescout()
    admin_id = get_freescout_admin_id(fs_conn)
    logger.info("Freescout admin_id=%d", admin_id)

    # Google Sheets (optional)
    spreadsheet = None
    akdemia_emails = set()
    if not args.skip_sheets:
        try:
            spreadsheet, _ = connect_sheets()
            print("\n--- Loading Akdemia2526 emails ---")
            akdemia_emails = load_akdemia_emails(spreadsheet)
        except Exception as e:
            logger.warning("Google Sheets connection failed: %s (continuing without Sheets)", e)
    else:
        logger.info("Google Sheets operations disabled (--skip-sheets)")

    # Phase 2: Query resolved bounce logs
    print("\n--- Phase 2: Query Resolved Bounce Logs ---")
    resolved_bls = get_resolved_bounce_logs(models, uid)

    # Optional filter by bounce log ID
    if args.id:
        resolved_bls = [bl for bl in resolved_bls if bl['id'] == args.id]

    if not resolved_bls:
        print("  No resolved bounce logs with Freescout IDs found.")
        fs_conn.close()
        return

    print(f"  Found {len(resolved_bls)} resolved bounce log(s) with Freescout IDs")
    for bl in resolved_bls:
        partner_name = bl['partner_id'][1] if bl['partner_id'] else '?'
        print(f"    BL#{bl['id']}: {partner_name} — FS#{bl['freescout_conversation_id']} — "
              f"bounced={bl.get('bounced_email', '?')}")

    # Phase 3: Process each
    print("\n--- Phase 3: Process Resolved Bounce Logs ---")
    stats = {'processed': 0, 'skipped': 0, 'errors': 0}

    for bl in resolved_bls:
        bl_id = bl['id']
        partner_name = bl['partner_id'][1] if bl['partner_id'] else 'Desconocido'
        print(f"\n--- BL#{bl_id} ({partner_name}) ---")

        result = process_bounce_log(
            bl, fs_conn, admin_id, akdemia_emails, spreadsheet, models, uid,
        )
        stats[result] = stats.get(result, 0) + 1

    # Summary
    fs_conn.close()
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Resolved bounce logs found: {len(resolved_bls)}")
    print(f"  Processed: {stats['processed']}")
    print(f"  Skipped (already done): {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
