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
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)
    logger.info("Odoo connected (uid=%d)", uid)
    return uid, models


def odoo_search_read(models, uid, model, domain, fields):
    """Helper for Odoo search_read."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        [domain], {'fields': fields},
    )


def odoo_post_note(models, uid, model, res_id, body):
    """Post an internal note (HTML) to a record's chatter.

    Uses mail.message create() directly because message_post() via XML-RPC
    escapes HTML entities (plaintext2html). Direct create preserves HTML.
    """
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'mail.message', 'create',
        [{'model': model, 'res_id': res_id, 'body': body,
          'message_type': 'notification', 'subtype_id': 2}],
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
            "SELECT id, number, subject, status, user_id, mailbox_id, "
            "customer_id, customer_email "
            "FROM conversations WHERE id = %s LIMIT 1",
            (conversation_id,),
        )
        return cursor.fetchone()


def find_freescout_customer(fs_conn, email):
    """Find a Freescout customer by email address.

    Returns dict with customer_id, first_name, last_name, email or None.
    Looks up the emails table which maps email addresses to customers.
    """
    if not email:
        return None
    with fs_conn.cursor() as cursor:
        cursor.execute(
            "SELECT e.customer_id, e.email, c.first_name, c.last_name "
            "FROM emails e JOIN customers c ON e.customer_id = c.id "
            "WHERE e.email = %s LIMIT 1",
            (email.strip().lower(),),
        )
        return cursor.fetchone()


def update_conversation_customer(fs_conn, conversation_id, customer_id, customer_email):
    """Update a Freescout conversation's customer_id and customer_email.

    Used to replace mailer-daemon@googlemail.com with the actual person
    on DSN bounce conversations, so support staff see the real customer.
    """
    with fs_conn.cursor() as cursor:
        cursor.execute(
            "UPDATE conversations SET customer_id = %s, customer_email = %s, "
            "updated_at = NOW(), user_updated_at = NOW() WHERE id = %s",
            (customer_id, customer_email, conversation_id),
        )


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


def load_akdemia_cedula_map(spreadsheet):
    """Load cedula → emails mapping from Akdemia2526 tab.

    Returns dict: {normalized_cedula: set of lowercase emails}
    Cedula columns (0-indexed): 33 (AH), 62 (BK), 91 (CN)
    Email columns (0-indexed): 46 (AU), 75 (BX), 104 (DA)
    """
    import re

    try:
        ws = spreadsheet.worksheet(AKDEMIA_TAB)
    except Exception:
        logger.warning("Akdemia2526 tab not found, skipping cedula map")
        return {}

    all_values = ws.get_all_values()
    cedula_map = {}  # {cedula_str: set of emails}

    # Paired columns: (cedula_col, email_col) for parent 1, 2, 3
    paired_columns = [(33, 46), (62, 75), (91, 104)]

    # Data starts at row 4 (index 3) — rows 0-2 are metadata + headers
    for row_idx in range(3, len(all_values)):
        row = all_values[row_idx]
        for ced_col, email_col in paired_columns:
            if ced_col >= len(row) or email_col >= len(row):
                continue

            ced_val = re.sub(r'[^0-9]', '', str(row[ced_col]))
            email_val = row[email_col].strip().lower()

            if not ced_val or not email_val or '@' not in email_val or email_val == 'nan':
                continue

            if ced_val not in cedula_map:
                cedula_map[ced_val] = set()
            cedula_map[ced_val].add(email_val)

    logger.info("Loaded %d cedulas with emails from Akdemia2526", len(cedula_map))
    return cedula_map


def load_akdemia_family_map(spreadsheet):
    """Load cedula → family records mapping from Akdemia2526 tab.

    Returns dict: {normalized_cedula: [family_records]}
    Each family_record is a dict with 'student' and 'parents' list.
    A parent with 2 kids will appear in 2 entries.

    Column indices (0-based):
    - Student: first_name=2, last_name=4
    - Parent 1: first_name=27, last_name=30, cedula=33, email=46
    - Parent 2: first_name=56, last_name=59, cedula=62, email=75
    - Parent 3: first_name=85, last_name=88, cedula=91, email=104
    """
    import re

    try:
        ws = spreadsheet.worksheet(AKDEMIA_TAB)
    except Exception:
        logger.warning("Akdemia2526 tab not found, skipping family map")
        return {}

    all_values = ws.get_all_values()
    family_map = {}  # {cedula_str: [family_records]}

    # Parent slot definitions: (first_name_col, last_name_col, cedula_col, email_col, slot_label)
    parent_slots = [
        (27, 30, 33, 46, 'Representante'),
        (56, 59, 62, 75, 'Representante.1'),
        (85, 88, 91, 104, 'Representante.2'),
    ]

    # Data starts at row 4 (index 3) — rows 0-2 are metadata + headers
    for row_idx in range(3, len(all_values)):
        row = all_values[row_idx]

        # Student name
        student_first = row[2].strip() if len(row) > 2 else ''
        student_last = row[4].strip() if len(row) > 4 else ''
        student_name = f"{student_first} {student_last}".strip()
        if not student_name:
            continue

        # Collect all parents for this row
        row_parents = []
        row_cedulas = []
        for fn_col, ln_col, ced_col, email_col, slot in parent_slots:
            if ced_col >= len(row):
                continue
            ced_val = re.sub(r'[^0-9]', '', str(row[ced_col]))
            if not ced_val:
                continue

            fn = row[fn_col].strip() if fn_col < len(row) else ''
            ln = row[ln_col].strip() if ln_col < len(row) else ''
            email = row[email_col].strip().lower() if email_col < len(row) else ''
            if email == 'nan':
                email = ''

            parent_info = {
                'name': f"{fn} {ln}".strip(),
                'cedula': ced_val,
                'email': email,
                'slot': slot,
            }
            row_parents.append(parent_info)
            row_cedulas.append(ced_val)

        if not row_parents:
            continue

        # Build family record for this student row
        family_record = {
            'student': student_name,
            'parents': row_parents,
        }

        # Index by each parent's cedula
        for ced in set(row_cedulas):
            if ced not in family_map:
                family_map[ced] = []
            family_map[ced].append(family_record)

    logger.info("Loaded family map for %d cedulas from Akdemia2526", len(family_map))
    return family_map


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


def enrich_family_emails(bl, models, uid, known_bounced, spreadsheet=None):
    """Enrich partner + mailing contacts + Sheets with family emails from Akdemia.

    Reads the family context from the bounce log's akdemia_family_emails JSON,
    collects valid emails from other family members, filters out known-bounced
    emails, and appends them to:
      1. res.partner email field (;-separated)
      2. mailing.contact records matching the partner
      3. Customers Google Sheet col J

    Returns list of emails actually added (empty if none).
    """
    prefix = "[DRY_RUN] " if DRY_RUN else ""

    family_json = bl.get('akdemia_family_emails')
    if not family_json:
        return []

    try:
        family = json.loads(family_json)
    except (json.JSONDecodeError, TypeError):
        return []

    partner_id = bl['partner_id'][0] if bl.get('partner_id') else 0
    bounced = (bl.get('bounced_email') or '').strip().lower()
    new_email = (bl.get('new_email') or '').strip().lower()

    # Collect all valid family emails (deduplicated)
    family_emails = set()
    for rec in family:
        for parent in rec.get('parents', []):
            email = (parent.get('email') or '').strip().lower()
            if email:
                family_emails.add(email)

    # Filter: remove bounced, new (already applied), and known-bounced
    candidates = family_emails - {bounced}
    if new_email:
        candidates -= {new_email}
    if known_bounced:
        skipped = candidates & known_bounced
        if skipped:
            logger.info("  Family enrichment: skipping known-bounced %s", ', '.join(skipped))
        candidates -= known_bounced

    if not candidates:
        return []

    # Read partner current email
    if not partner_id:
        return []
    partner_data = odoo_search_read(
        models, uid, 'res.partner',
        [('id', '=', partner_id)], ['email', 'vat'])
    if not partner_data:
        return []

    current_email = partner_data[0].get('email', '') or ''
    partner_vat = partner_data[0].get('vat', '') or ''
    current_list = [e.strip().lower() for e in current_email.split(';') if e.strip()]

    # Only add emails not already on partner
    to_add = [e for e in sorted(candidates) if e not in current_list]
    if not to_add:
        logger.info("  Family enrichment: all family emails already on partner")
        return []

    logger.info("  Family enrichment: adding %d email(s): %s", len(to_add), ', '.join(to_add))

    # 1. Update partner email field
    new_partner_email = current_email
    for email in to_add:
        if new_partner_email:
            new_partner_email += ';' + email
        else:
            new_partner_email = email

    if not DRY_RUN:
        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'write',
            [[partner_id], {'email': new_partner_email}])

    print(f"  {prefix}Partner #{partner_id} email: {current_email} → {new_partner_email}")

    # 2. Sync mailing contacts (find MCs with partner's current/bounced email)
    searched_emails = set()
    for search_email in [bounced, new_email] + current_list:
        if not search_email or search_email in searched_emails:
            continue
        searched_emails.add(search_email)
        try:
            mcs = odoo_search_read(
                models, uid, 'mailing.contact',
                [('email', 'ilike', search_email)],
                ['id', 'email'])
            for mc in mcs:
                mc_email = mc.get('email', '') or ''
                mc_list = [e.strip().lower() for e in mc_email.split(';') if e.strip()]
                mc_to_add = [e for e in to_add if e not in mc_list]
                if mc_to_add:
                    new_mc_email = mc_email
                    for email in mc_to_add:
                        new_mc_email += ';' + email if new_mc_email else email
                    if not DRY_RUN:
                        models.execute_kw(
                            ODOO_DB, uid, ODOO_PASSWORD,
                            'mailing.contact', 'write',
                            [[mc['id']], {'email': new_mc_email}])
                    print(f"  {prefix}MC#{mc['id']} email: {mc_email} → {new_mc_email}")
        except Exception as e:
            logger.warning("  MC sync error for '%s': %s", search_email, e)

    # 3. Update Google Sheets Customers tab
    if spreadsheet and partner_vat:
        try:
            ws = spreadsheet.worksheet(CUSTOMERS_TAB)
            vat_values = ws.col_values(1)
            target_vat = partner_vat.strip().upper()
            target_row = None
            for idx, val in enumerate(vat_values):
                if idx < CUSTOMERS_HEADER_ROW:
                    continue
                if val.strip().upper() == target_vat:
                    target_row = idx + 1
                    break
            if target_row:
                cell_value = ws.cell(target_row, 10).value or ''
                cell_list = [e.strip().lower() for e in cell_value.split(';') if e.strip()]
                sheet_to_add = [e for e in to_add if e not in cell_list]
                if sheet_to_add:
                    new_cell = cell_value
                    for email in sheet_to_add:
                        new_cell += ';' + email if new_cell else email
                    logger.info("  Sheets row %d: '%s' → '%s'", target_row, cell_value, new_cell)
                    if not DRY_RUN:
                        ws.update_cell(target_row, 10, new_cell)
                    print(f"  {prefix}Customers sheet: added family emails")
        except Exception as e:
            logger.warning("  Sheets family enrichment error: %s", e)

    return to_add


def sync_customers_family_emails(spreadsheet, akdemia_cedula_map, known_bounced,
                                  models=None, uid=None):
    """Sync ALL Akdemia family emails to Customers sheet + Odoo partner + MC.

    For each Customers row with a VAT matching an Akdemia cedula:
      1. Collect all Akdemia emails for that cedula (cross all parent slots)
      2. Filter out known-bounced
      3. Compare with current col J -> append missing to sheet
      4. Look up Odoo partner by VAT -> append missing to partner email
      5. Find mailing.contacts for that partner -> append missing

    Returns (sheets_updated, odoo_updated, total_checked).
    """
    import re

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    try:
        ws = spreadsheet.worksheet(CUSTOMERS_TAB)
    except Exception as e:
        logger.warning("Customers tab not found: %s", e)
        return 0, 0, 0

    # Single bulk read of the entire sheet
    all_values = ws.get_all_values()
    if len(all_values) < CUSTOMERS_DATA_START:
        logger.info("  Customers sheet has no data rows")
        return 0, 0, 0

    sheets_updated = 0
    odoo_updated = 0
    total_checked = 0

    # Data rows start at index CUSTOMERS_HEADER_ROW (0-indexed = row 2 = index 2)
    for row_idx in range(CUSTOMERS_HEADER_ROW, len(all_values)):
        row = all_values[row_idx]
        if len(row) < 10:
            continue

        vat_raw = (row[0] or '').strip()
        if not vat_raw:
            continue

        # Normalize VAT to digits for cedula lookup
        cedula = re.sub(r'[^0-9]', '', str(vat_raw))
        if not cedula:
            continue

        akdemia_set = akdemia_cedula_map.get(cedula)
        if not akdemia_set:
            continue

        total_checked += 1

        # Filter out known-bounced emails
        valid = akdemia_set - (known_bounced or set())

        # Parse current col J (index 9) — semicolon-separated, strip+filter empties
        current_raw = (row[9] or '').strip()
        current_list = [e.strip().lower() for e in current_raw.split(';') if e.strip()]
        current_set = set(current_list)

        to_add = sorted(valid - current_set)
        if not to_add:
            continue

        sheet_row = row_idx + 1  # gspread uses 1-indexed rows
        logger.info("  Row %d (VAT=%s): adding %d email(s): %s",
                     sheet_row, vat_raw, len(to_add), ', '.join(to_add))

        # --- Sheet: append to col J ---
        # Rebuild from parsed list to avoid trailing semicolons
        current_clean = ';'.join(e for e in current_raw.split(';') if e.strip())
        new_cell = current_clean
        for email in to_add:
            new_cell = new_cell + ';' + email if new_cell else email

        print(f"  {prefix}Sheet row {sheet_row}: '{current_raw}' -> '{new_cell}'")
        if not DRY_RUN:
            ws.update_cell(sheet_row, 10, new_cell)
        sheets_updated += 1

        # --- Odoo partner: search by VAT, append missing emails ---
        if models and uid:
            try:
                partners = odoo_search_read(
                    models, uid, 'res.partner',
                    [('vat', '=', vat_raw)], ['id', 'email'])
                if partners:
                    partner = partners[0]
                    partner_email = partner.get('email', '') or ''
                    partner_list = [e.strip().lower() for e in partner_email.split(';')
                                    if e.strip()]
                    partner_to_add = [e for e in to_add if e not in partner_list]

                    if partner_to_add:
                        # Clean trailing semicolons before appending
                        partner_email_clean = ';'.join(
                            e for e in partner_email.split(';') if e.strip())
                        new_partner_email = partner_email_clean
                        for email in partner_to_add:
                            new_partner_email = (new_partner_email + ';' + email
                                                 if new_partner_email else email)

                        print(f"  {prefix}Partner #{partner['id']}: "
                              f"'{partner_email}' -> '{new_partner_email}'")
                        if not DRY_RUN:
                            models.execute_kw(
                                ODOO_DB, uid, ODOO_PASSWORD,
                                'res.partner', 'write',
                                [[partner['id']], {'email': new_partner_email}])

                        # --- MC: find mailing.contacts, append missing ---
                        mc_searched = set()
                        for search_email in partner_list + [partner_email.strip().lower()]:
                            if not search_email or search_email in mc_searched:
                                continue
                            mc_searched.add(search_email)
                            try:
                                mcs = odoo_search_read(
                                    models, uid, 'mailing.contact',
                                    [('email', 'ilike', search_email)],
                                    ['id', 'email'])
                                for mc in mcs:
                                    mc_email = mc.get('email', '') or ''
                                    mc_list = [e.strip().lower()
                                               for e in mc_email.split(';') if e.strip()]
                                    mc_to_add = [e for e in partner_to_add
                                                 if e not in mc_list]
                                    if mc_to_add:
                                        new_mc_email = mc_email
                                        for email in mc_to_add:
                                            new_mc_email = (new_mc_email + ';' + email
                                                            if new_mc_email else email)
                                        print(f"  {prefix}MC#{mc['id']}: "
                                              f"'{mc_email}' -> '{new_mc_email}'")
                                        if not DRY_RUN:
                                            models.execute_kw(
                                                ODOO_DB, uid, ODOO_PASSWORD,
                                                'mailing.contact', 'write',
                                                [[mc['id']], {'email': new_mc_email}])
                            except Exception as e:
                                logger.warning("  MC sync error for '%s': %s",
                                               search_email, e)

                        odoo_updated += 1
                else:
                    logger.info("  No Odoo partner found for VAT=%s (sheet-only update)",
                                vat_raw)
            except Exception as e:
                logger.warning("  Odoo partner/MC update error for VAT=%s: %s", vat_raw, e)

    return sheets_updated, odoo_updated, total_checked


# ============================================================================
# Main Logic
# ============================================================================

def close_related_conversations(fs_conn, admin_id, search_email, primary_fs_id,
                                partner_name, odoo_bl_url,
                                real_customer=None):
    """Close other active Freescout conversations that mention an email address.

    Searches three places for the email:
    - thread body (DSN conversations where bounced address appears in body)
    - conversation customer_email (verification email replies from new address)
    - thread from field (reply sender address)

    If real_customer is provided (dict with customer_id, email), also reassigns
    DSN conversations from mailer-daemon to the actual customer.

    Returns count of conversations closed.
    """
    prefix = "[DRY_RUN] " if DRY_RUN else ""

    with fs_conn.cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT c.id, c.number, c.subject, c.mailbox_id,
                   c.customer_email, c.customer_id
            FROM conversations c
            LEFT JOIN threads t ON t.conversation_id = c.id
            WHERE c.status = 1
              AND c.id != %s
              AND c.subject NOT LIKE '[RESUELTO-AI]%%'
              AND (t.body LIKE %s
                   OR c.customer_email LIKE %s
                   OR t.`from` LIKE %s)
        """, (primary_fs_id, f'%{search_email}%', f'%{search_email}%', f'%{search_email}%'))
        related = cursor.fetchall()

    if not related:
        return 0

    print(f"  {prefix}Found {len(related)} related active conversation(s) for '{search_email}':")
    for r in related:
        print(f"    #{r['number']} (id={r['id']}): {r['subject'][:70]}")

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    note_body = (
        f"<p><strong>Cerrado automaticamente</strong> — el email "
        f"<code>{search_email}</code> de <strong>{partner_name}</strong> "
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

                    # Reassign DSN conversations from mailer-daemon to real customer
                    customer_fields = ""
                    customer_params = []
                    if real_customer and r.get('customer_email', '').lower() == 'mailer-daemon@googlemail.com':
                        customer_fields = ", customer_id = %s, customer_email = %s"
                        customer_params = [real_customer['customer_id'], real_customer['email']]
                        logger.info("    #%d: reassigning customer from mailer-daemon → %s",
                                    r['number'], real_customer['email'])

                    if closed_folder:
                        cursor.execute(
                            "UPDATE conversations SET subject = %s, status = 3, "
                            "folder_id = %s, closed_at = NOW(), closed_by_user_id = %s"
                            + customer_fields +
                            ", updated_at = NOW(), user_updated_at = NOW() WHERE id = %s",
                            (new_subject, closed_folder, admin_id,
                             *customer_params, r['id']),
                        )
                    else:
                        cursor.execute(
                            "UPDATE conversations SET subject = %s, status = 3, "
                            "closed_at = NOW(), closed_by_user_id = %s"
                            + customer_fields +
                            ", updated_at = NOW(), user_updated_at = NOW() "
                            "WHERE id = %s",
                            (new_subject, admin_id, *customer_params, r['id']),
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
    """Query Odoo for resolved/akdemia_pending bounce logs with Freescout conversation ID.

    Both states need Freescout post-processing (subject prefix, notes, close/assign).
    Uses broader domain + client-side filter due to Odoo Integer=0 quirk.
    """
    all_resolved = odoo_search_read(
        models, uid, 'mail.bounce.log',
        [('state', 'in', ['resolved', 'akdemia_pending'])],
        [
            'id', 'bounced_email', 'new_email', 'partner_id',
            'freescout_conversation_id', 'action_tier',
            'resolved_date', 'resolved_by', 'state', 'in_akdemia',
            'akdemia_family_emails',
        ],
    )

    # Filter: must have a real Freescout conversation ID (> 0)
    with_freescout = [
        bl for bl in all_resolved
        if bl.get('freescout_conversation_id') and bl['freescout_conversation_id'] > 0
    ]

    return with_freescout


def process_bounce_log(bl, fs_conn, admin_id, akdemia_emails, spreadsheet, models, uid,
                       known_bounced=None):
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

    # --- Look up real customer for DSN conversation reassignment ---
    real_customer = None
    if bounced_email:
        real_customer = find_freescout_customer(fs_conn, bounced_email)
        if real_customer:
            logger.info("  Real customer for '%s': #%d (%s %s)",
                        bounced_email, real_customer['customer_id'],
                        real_customer['first_name'], real_customer['last_name'])

    # Reassign primary conversation if it's a mailer-daemon DSN
    fs_customer_email = (fs_conv.get('customer_email') or '').lower()
    if real_customer and fs_customer_email == 'mailer-daemon@googlemail.com':
        print(f"  {prefix}Reassigning primary #{fs_conv['number']} customer: "
              f"mailer-daemon → {real_customer['email']} "
              f"({real_customer['first_name']} {real_customer['last_name']})")
        if not DRY_RUN:
            update_conversation_customer(
                fs_conn, fs_db_id,
                real_customer['customer_id'], real_customer['email'],
            )
            fs_conn.commit()

    # Already processed? Still run related-conversations cleanup, then skip rest
    if primary_already_done:
        logger.info("  Freescout #%d primary already processed", fs_conv_number)
        # Build odoo_bl_url for related cleanup
        odoo_bl_url = f"{ODOO_URL}/web#id={bl_id}&model=mail.bounce.log&view_type=form"
        any_closed = 0
        if bounced_email:
            related_closed = close_related_conversations(
                fs_conn, admin_id, bounced_email, fs_db_id, partner_name, odoo_bl_url,
                real_customer=real_customer,
            )
            if related_closed:
                print(f"  {prefix}Closed {related_closed} related conversation(s) (bounced email)")
                any_closed += related_closed
        if new_email and new_email.lower() != bounced_email:
            related_new = close_related_conversations(
                fs_conn, admin_id, new_email, fs_db_id, partner_name, odoo_bl_url,
                real_customer=real_customer,
            )
            if related_new:
                print(f"  {prefix}Closed {related_new} related conversation(s) (new email)")
                any_closed += related_new
        # Family enrichment runs even for already-processed BLs
        family_added = []
        if bl.get('akdemia_family_emails'):
            family_added = enrich_family_emails(
                bl, models, uid, known_bounced, spreadsheet)
            if family_added:
                print(f"  {prefix}Family emails added: {', '.join(family_added)}")
                any_closed += 1  # count as "processed" so we don't return 'skipped'
        # Post audit note for family enrichment on already-processed BLs
        if family_added and not DRY_RUN:
            try:
                # Re-read partner email for accurate audit
                updated_email = ''
                if partner_id:
                    p = odoo_search_read(
                        models, uid, 'res.partner',
                        [('id', '=', partner_id)], ['email'])
                    if p:
                        updated_email = p[0].get('email', '')
                items = [
                    f'<li><b>Emails familiares agregados (Akdemia):</b> '
                    f'<code>{"; ".join(family_added)}</code></li>',
                ]
                if updated_email:
                    items.append(
                        f'<li><b>Emails actuales del contacto:</b> '
                        f'<code>{updated_email}</code></li>')
                post_body = (
                    f'<p><b>Enriquecimiento familiar (Resolution Bridge)</b></p>'
                    f'<ul>{"".join(items)}</ul>'
                )
                odoo_post_note(models, uid, 'mail.bounce.log', bl_id, post_body)
            except Exception as e:
                logger.warning("  Could not post family enrichment note to BL#%d: %s", bl_id, e)
        return 'processed' if any_closed else 'skipped'

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
                # When closing (status=3), set closed_at/closed_by for Freescout UI visibility
                closed_fields = ", closed_at = NOW(), closed_by_user_id = %s" if new_status == 3 else ""
                closed_params = [admin_id] if new_status == 3 else []

                if assign_to and new_folder_id:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s, "
                        "user_id = %s, folder_id = %s"
                        + closed_fields +
                        ", updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, assign_to, new_folder_id,
                         *closed_params, fs_db_id),
                    )
                elif new_folder_id:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s, "
                        "folder_id = %s"
                        + closed_fields +
                        ", updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, new_folder_id,
                         *closed_params, fs_db_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE conversations SET subject = %s, status = %s"
                        + closed_fields +
                        ", updated_at = NOW(), user_updated_at = NOW() "
                        "WHERE id = %s",
                        (new_subject, new_status, *closed_params, fs_db_id),
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
    total_related_closed = 0
    if bounced_email:
        related_closed = close_related_conversations(
            fs_conn, admin_id, bounced_email, fs_db_id, partner_name, odoo_bl_url,
            real_customer=real_customer,
        )
        if related_closed:
            print(f"  {prefix}Closed {related_closed} related conversation(s) (bounced email)")
            total_related_closed += related_closed

    # Also close conversations mentioning the NEW email (e.g. verification email replies)
    if new_email and new_email.lower() != bounced_email:
        related_new = close_related_conversations(
            fs_conn, admin_id, new_email, fs_db_id, partner_name, odoo_bl_url,
            real_customer=real_customer,
        )
        if related_new:
            print(f"  {prefix}Closed {related_new} related conversation(s) (new email)")
            total_related_closed += related_new

    # --- Step 5b: Enrich with family emails ---
    family_emails_added = []
    if bl.get('akdemia_family_emails'):
        family_emails_added = enrich_family_emails(
            bl, models, uid, known_bounced, spreadsheet)
        if family_emails_added:
            print(f"  {prefix}Family emails added: {', '.join(family_emails_added)}")
            # Re-read partner email for accurate audit trail
            if partner_id:
                partner_data = odoo_search_read(
                    models, uid, 'res.partner',
                    [('id', '=', partner_id)], ['email'])
                if partner_data:
                    partner_current_email = partner_data[0].get('email', '')

    # --- Step 6: Update Customers Google Sheet ---
    sheets_updated = False
    if spreadsheet and partner_vat and bounced_email:
        action_desc = f"replacing '{bounced_email}' with '{new_email}'" if new_email else f"removing '{bounced_email}'"
        print(f"  {prefix}Customers tab: {action_desc} for VAT={partner_vat}")
        try:
            updated = update_customers_email(spreadsheet, partner_vat, bounced_email, new_email)
            if updated:
                print(f"  {prefix}Customers tab updated")
                sheets_updated = True
            else:
                print(f"  Customers tab: no change needed (not found or already clean)")
        except Exception as e:
            logger.error("  Error updating Customers tab: %s", e)
    else:
        if not partner_vat:
            print(f"  Skipping Customers tab: no VAT on partner")

    # --- Step 7: Post audit trail to bounce log chatter ---
    if not DRY_RUN:
        try:
            fs_url = f"{FREESCOUT_BASE_URL}/conversation/{fs_conv['number']}"
            items = []
            # Freescout primary
            if in_akdemia:
                items.append(
                    f'<li>Freescout <a href="{fs_url}">#{fs_conv["number"]}</a>: '
                    f'[RESUELTO-AI], Asignado a Alejandra (Akdemia)</li>')
            else:
                items.append(
                    f'<li>Freescout <a href="{fs_url}">#{fs_conv["number"]}</a>: '
                    f'[RESUELTO-AI], Cerrado</li>')
            # DSN customer reassignment
            if real_customer and fs_customer_email == 'mailer-daemon@googlemail.com':
                items.append(
                    f'<li>Cliente Freescout reasignado: mailer-daemon &rarr; '
                    f'{real_customer["first_name"]} {real_customer["last_name"]} '
                    f'({real_customer["email"]})</li>')
            # Related conversations
            if total_related_closed:
                items.append(
                    f'<li>{total_related_closed} conversacion(es) DSN relacionada(s) cerrada(s)</li>')
            # Customers sheet
            if sheets_updated:
                items.append('<li>Hoja Customers (Google Sheets): actualizada</li>')
            # Partner email
            # Family enrichment
            if family_emails_added:
                items.append(
                    f'<li><b>Emails familiares agregados (Akdemia):</b> '
                    f'<code>{"; ".join(family_emails_added)}</code></li>')
            if partner_current_email:
                items.append(
                    f'<li><b>Emails actuales del contacto:</b> '
                    f'<code>{partner_current_email}</code></li>')

            post_body = (
                f'<p><b>Post-procesamiento completado (Resolution Bridge)</b></p>'
                f'<ul>{"".join(items)}</ul>'
            )
            odoo_post_note(models, uid, 'mail.bounce.log', bl_id, post_body)
        except Exception as e:
            logger.warning("  Could not post audit note to BL#%d: %s", bl_id, e)

    return 'processed'


def refresh_in_akdemia_flags(models, uid, akdemia_emails, akdemia_family_map=None):
    """Refresh in_akdemia flag and family context on all non-resolved bounce logs.

    Ensures the flag is current before any manual or AI resolution happens.
    If akdemia_family_map is provided, also updates akdemia_family_emails JSON.
    Returns (updated_count, total_checked).
    """
    import re

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    # Get all bounce logs that are not yet fully resolved
    all_bls = odoo_search_read(
        models, uid, 'mail.bounce.log',
        [('state', 'not in', ['resolved'])],
        ['id', 'bounced_email', 'in_akdemia', 'akdemia_family_emails', 'partner_id'],
    )

    if not all_bls:
        logger.info("  No non-resolved bounce logs to refresh")
        return 0, 0

    # Batch-fetch partner VATs for family context lookup
    partner_vat_map = {}
    if akdemia_family_map:
        partner_ids = list({bl['partner_id'][0] for bl in all_bls if bl.get('partner_id')})
        if partner_ids:
            partner_data = odoo_search_read(
                models, uid, 'res.partner',
                [('id', 'in', partner_ids)],
                ['id', 'vat'],
            )
            partner_vat_map = {p['id']: p.get('vat', '') for p in partner_data}

    updated = 0
    for bl in all_bls:
        bounced = (bl.get('bounced_email') or '').strip().lower()
        if not bounced:
            continue

        write_vals = {}

        # Check in_akdemia flag
        should_be = bounced in akdemia_emails
        current = bl.get('in_akdemia', False)
        if should_be != current:
            write_vals['in_akdemia'] = should_be
            logger.info("  %sBL#%d: in_akdemia %s → %s (%s)",
                        prefix, bl['id'], current, should_be, bounced)

        # Check family context
        if akdemia_family_map and bl.get('partner_id'):
            partner_id = bl['partner_id'][0]
            vat = partner_vat_map.get(partner_id, '')
            if vat:
                cedula = re.sub(r'[^0-9]', '', str(vat))
                family_records = akdemia_family_map.get(cedula, [])
                if family_records:
                    new_json = json.dumps(family_records, ensure_ascii=False)
                else:
                    new_json = ''
                current_json = bl.get('akdemia_family_emails') or ''
                if new_json != current_json:
                    write_vals['akdemia_family_emails'] = new_json or False
                    logger.info("  %sBL#%d: akdemia_family_emails updated (%d records)",
                                prefix, bl['id'], len(family_records))

        if write_vals:
            if not DRY_RUN:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.bounce.log', 'write',
                    [[bl['id']], write_vals],
                )
            updated += 1

    return updated, len(all_bls)


def check_akdemia_confirmations(models, uid, akdemia_emails):
    """Check akdemia_pending bounce logs and auto-confirm if new email is now in Akdemia.

    Returns count of confirmations.
    """
    prefix = "[DRY_RUN] " if DRY_RUN else ""

    pending_bls = odoo_search_read(
        models, uid, 'mail.bounce.log',
        [('state', '=', 'akdemia_pending')],
        ['id', 'new_email', 'bounced_email', 'partner_id'],
    )

    if not pending_bls:
        logger.info("  No akdemia_pending bounce logs to check")
        return 0

    confirmed = 0
    for bl in pending_bls:
        new_email = (bl.get('new_email') or '').strip().lower()
        partner_name = bl['partner_id'][1] if bl.get('partner_id') else '?'

        if not new_email:
            # REMOVE_ONLY case: bounced email was removed, check if it's gone from Akdemia
            bounced = (bl.get('bounced_email') or '').strip().lower()
            if bounced and bounced not in akdemia_emails:
                logger.info("  %sBL#%d (%s): bounced email '%s' no longer in Akdemia → confirm",
                            prefix, bl['id'], partner_name, bounced)
                if not DRY_RUN:
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'mail.bounce.log', 'action_confirm_akdemia',
                        [[bl['id']]],
                    )
                confirmed += 1
            continue

        # NEW_EMAIL case: check if new email now appears in Akdemia
        if new_email in akdemia_emails:
            logger.info("  %sBL#%d (%s): new email '%s' found in Akdemia → confirm",
                        prefix, bl['id'], partner_name, new_email)
            if not DRY_RUN:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.bounce.log', 'action_confirm_akdemia',
                    [[bl['id']]],
                )
            confirmed += 1

    return confirmed


def auto_resolve_from_akdemia(models, uid, akdemia_cedula_map, target_bl_id=None):
    """Auto-resolve pending bounce logs where Akdemia has a valid alternative email.

    For each pending bounce log with a linked partner:
    1. Get partner VAT → normalize to digits
    2. Look up in akdemia_cedula_map
    3. Find an email that differs from the bounced email
    4. If found: write new_email + call action_apply_new_email()

    If target_bl_id is set, only process that specific bounce log.
    Returns count of auto-resolved.
    """
    import re

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    domain = [('state', 'in', ['pending', 'notified', 'contacted']),
              ('partner_id', '!=', False)]
    if target_bl_id:
        domain.append(('id', '=', target_bl_id))

    pending_bls = odoo_search_read(
        models, uid, 'mail.bounce.log',
        domain,
        ['id', 'bounced_email', 'partner_id', 'state'],
    )

    if not pending_bls:
        logger.info("  No pending bounce logs with partners to check")
        return 0

    logger.info("  Checking %d pending bounce log(s) against Akdemia cedula map", len(pending_bls))

    # Build set of ALL known bounced emails to avoid applying one as "new"
    all_bounce_logs = odoo_search_read(
        models, uid, 'mail.bounce.log',
        [],
        ['bounced_email'],
    )
    known_bounced = {
        bl['bounced_email'].strip().lower()
        for bl in all_bounce_logs
        if bl.get('bounced_email')
    }
    logger.info("  Loaded %d known bounced emails for cross-check", len(known_bounced))

    # Batch-fetch partner VATs
    partner_ids = list({bl['partner_id'][0] for bl in pending_bls})
    partner_data = odoo_search_read(
        models, uid, 'res.partner',
        [('id', 'in', partner_ids)],
        ['id', 'vat'],
    )
    partner_vat_map = {p['id']: p.get('vat', '') for p in partner_data}

    resolved_count = 0
    for bl in pending_bls:
        bl_id = bl['id']
        bounced_email = (bl.get('bounced_email') or '').strip().lower()
        partner_id = bl['partner_id'][0]
        partner_name = bl['partner_id'][1]

        vat = partner_vat_map.get(partner_id, '')
        if not vat:
            continue

        cedula = re.sub(r'[^0-9]', '', str(vat))
        if not cedula:
            continue

        akdemia_emails = akdemia_cedula_map.get(cedula)
        if not akdemia_emails:
            continue

        # Find first email that differs from the bounced one AND is not itself a known bounce
        alternative = None
        skipped_bounced = []
        for email in sorted(akdemia_emails):  # sorted for deterministic order
            if email == bounced_email:
                continue
            if email in known_bounced:
                skipped_bounced.append(email)
                continue
            alternative = email
            break

        if skipped_bounced:
            logger.warning("  BL#%d (%s): skipped Akdemia email(s) %s — already known as bounced",
                           bl_id, partner_name, ', '.join(skipped_bounced))

        if not alternative:
            if skipped_bounced:
                print(f"  {prefix}BL#{bl_id} ({partner_name}): ALL Akdemia alternatives "
                      f"are known bounced emails ({', '.join(skipped_bounced)}), skipping")
            continue

        print(f"  {prefix}BL#{bl_id} ({partner_name}): cedula={cedula}, "
              f"bounced={bounced_email} → Akdemia has {alternative}")

        if not DRY_RUN:
            try:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.bounce.log', 'write',
                    [[bl_id], {'new_email': alternative}],
                )
                try:
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'mail.bounce.log', 'action_apply_new_email',
                        [[bl_id]],
                    )
                except xmlrpc.client.Fault as f:
                    # Odoo server returns None from button actions which it
                    # cannot marshal. The action still executed successfully.
                    if 'cannot marshal None' in str(f):
                        logger.debug("  BL#%d: action executed (ignoring None marshal fault)", bl_id)
                    else:
                        raise
                # Post audit trail to bounce log chatter
                all_akdemia = ', '.join(sorted(akdemia_emails))
                note_items = [
                    f'<li><b>Cedula:</b> {cedula} ({partner_name})</li>',
                    f'<li><b>Email rebotado:</b> <code>{bounced_email}</code></li>',
                    f'<li><b>Emails en Akdemia:</b> <code>{all_akdemia}</code></li>',
                ]
                if skipped_bounced:
                    note_items.append(
                        f'<li><b>Descartados (tambien rebotados):</b> '
                        f'<code>{", ".join(skipped_bounced)}</code></li>')
                note_items.extend([
                    f'<li><b>Email aplicado:</b> <code>{alternative}</code></li>',
                    f'<li><b>Accion:</b> Email reemplazado en contacto Odoo y mailing contacts</li>',
                ])
                note_body = (
                    f'<p><b>Resuelto automaticamente — PATH F (Akdemia Auto-Resolve)</b></p>'
                    f'<ul>{"".join(note_items)}</ul>'
                )
                odoo_post_note(models, uid, 'mail.bounce.log', bl_id, note_body)
                logger.info("  BL#%d: auto-resolved with '%s'", bl_id, alternative)
            except Exception as e:
                logger.error("  BL#%d: error applying new email: %s", bl_id, e)
                continue

        resolved_count += 1

    return resolved_count


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
    akdemia_cedula_map = {}
    akdemia_family_map = {}
    if not args.skip_sheets:
        try:
            spreadsheet, _ = connect_sheets()
            print("\n--- Loading Akdemia2526 data ---")
            akdemia_emails = load_akdemia_emails(spreadsheet)
            akdemia_cedula_map = load_akdemia_cedula_map(spreadsheet)
            akdemia_family_map = load_akdemia_family_map(spreadsheet)
        except Exception as e:
            logger.warning("Google Sheets connection failed: %s (continuing without Sheets)", e)
    else:
        logger.info("Google Sheets operations disabled (--skip-sheets)")

    # Phase 2a: Refresh in_akdemia flags
    if akdemia_emails:
        print("\n--- Phase 2a: Refresh in_akdemia Flags ---")
        updated, total = refresh_in_akdemia_flags(
            models, uid, akdemia_emails,
            akdemia_family_map=akdemia_family_map if akdemia_family_map else None)
        print(f"  Checked {total} non-resolved bounce logs, updated {updated} flags")

    # Phase 2b: Check akdemia_pending confirmations
    if akdemia_emails:
        print("\n--- Phase 2b: Check Akdemia Confirmations ---")
        confirmed = check_akdemia_confirmations(models, uid, akdemia_emails)
        print(f"  Confirmed {confirmed} akdemia_pending bounce log(s)")

    # Phase 2c: Auto-resolve from Akdemia (PATH F)
    if akdemia_cedula_map:
        print("\n--- Phase 2c: Auto-Resolve from Akdemia ---")
        auto_resolved = auto_resolve_from_akdemia(
            models, uid, akdemia_cedula_map, target_bl_id=args.id)
        print(f"  Auto-resolved {auto_resolved} bounce log(s) from Akdemia data")

    # Phase 3: Query resolved bounce logs
    print("\n--- Phase 3: Query Resolved Bounce Logs ---")
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

    # Build known-bounced set for family enrichment filtering
    all_bounce_logs = odoo_search_read(models, uid, 'mail.bounce.log', [], ['bounced_email'])
    known_bounced = {
        bl['bounced_email'].strip().lower()
        for bl in all_bounce_logs if bl.get('bounced_email')
    }
    logger.info("Loaded %d known bounced emails for family enrichment filter", len(known_bounced))

    # Phase 4: Process each
    print("\n--- Phase 4: Process Resolved/Akdemia-Pending Bounce Logs ---")
    stats = {'processed': 0, 'skipped': 0, 'errors': 0}

    for bl in resolved_bls:
        bl_id = bl['id']
        partner_name = bl['partner_id'][1] if bl['partner_id'] else 'Desconocido'
        print(f"\n--- BL#{bl_id} ({partner_name}) ---")

        result = process_bounce_log(
            bl, fs_conn, admin_id, akdemia_emails, spreadsheet, models, uid,
            known_bounced=known_bounced,
        )
        stats[result] = stats.get(result, 0) + 1

    # Phase 5: Sync Customers sheet family emails from Akdemia
    if spreadsheet and akdemia_cedula_map:
        print("\n--- Phase 5: Sync Customers Family Emails ---")
        sheets_synced, odoo_synced, checked = sync_customers_family_emails(
            spreadsheet, akdemia_cedula_map, known_bounced,
            models=models, uid=uid)
        print(f"  Checked {checked} Customers rows with Akdemia matches")
        print(f"  Sheets updated: {sheets_synced}")
        print(f"  Odoo partners/MC updated: {odoo_synced}")

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
