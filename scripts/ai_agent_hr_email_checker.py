#!/usr/bin/env python3
"""
AI Agent HR Email Checker - Freescout HR Mailbox Bridge

Monitors the Freescout HR mailbox (recursoshumanos@ueipab.edu.ve, mailbox_id=4)
for employee replies containing document attachments (Cedula, RIF photos).
Matches sender email to employees with active hr.data.collection.request,
downloads attachments, and uploads them to Odoo via XML-RPC.

Architecture mirrors ai_agent_email_checker.py:
  - Odoo XML-RPC for collection request queries + attachment creation
  - Freescout MySQL for thread/attachment detection
  - Freescout disk for attachment file reads
  - DRY_RUN=True default, state file tracking

Flow:
  1. Query Odoo for active hr.data.collection.request records
  2. Query Freescout HR mailbox threads for replies matching employee work emails
  3. Detect attachments (images/PDFs) in matching threads
  4. Download from Freescout disk, upload to Odoo ir.attachment
  5. Link to employee identification_attachment_ids + update request
  6. Post Freescout note confirming receipt

Usage:
    python3 /opt/odoo-dev/scripts/ai_agent_hr_email_checker.py          # DRY_RUN
    python3 /opt/odoo-dev/scripts/ai_agent_hr_email_checker.py --live   # LIVE

Author: Claude Code Assistant
Date: 2026-02-18
"""

import argparse
import base64
import json
import logging
import os
import sys
import xmlrpc.client
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True  # True = no modifications, --live to override

TARGET_ENV = os.environ.get('TARGET_ENV', 'testing')

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
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
}

FREESCOUT_DB = {
    'host': 'localhost',
    'user': 'free297',
    'password': '1gczp1S@3!',
    'database': 'free297',
}

# Freescout HR mailbox
HR_MAILBOX_ID = 4
HR_MAILBOX_EMAIL = 'recursoshumanos@ueipab.edu.ve'

# Freescout attachment storage root
FREESCOUT_ATTACHMENT_PATH = '/var/www/freescout/storage/app/attachment'

# State file for tracking last run
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'ai_agent_hr_email_checker_state.json')

# Accepted attachment MIME types
ACCEPTED_MIMES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'application/pdf',
}

# ============================================================================
# Logging
# ============================================================================

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_agent_logs')
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger('hr_email_checker')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(os.path.join(LOG_DIR, 'hr_email_checker.log'))
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(fh)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger.addHandler(sh)

# ============================================================================
# State management
# ============================================================================


def load_state():
    """Load last-run state from JSON file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'last_run': '2026-02-18T00:00:00'}


def save_state(state):
    """Save state to JSON file."""
    state['last_run'] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


# ============================================================================
# Connections
# ============================================================================


def connect_odoo():
    """Connect to Odoo via XML-RPC."""
    config = ODOO_CONFIGS[TARGET_ENV]
    common = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/common")
    uid = common.authenticate(config['db'], config['user'], config['password'], {})
    if not uid:
        raise ConnectionError(f"Odoo auth failed for {config['user']} on {config['db']}")
    models = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/object")
    logger.info("Connected to Odoo: %s (db=%s, uid=%d)", config['url'], config['db'], uid)
    return models, uid, config


def connect_freescout():
    """Connect to Freescout MySQL."""
    import pymysql
    conn = pymysql.connect(
        host=FREESCOUT_DB['host'],
        user=FREESCOUT_DB['user'],
        password=FREESCOUT_DB['password'],
        database=FREESCOUT_DB['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    logger.info("Connected to Freescout MySQL: %s", FREESCOUT_DB['database'])
    return conn


# ============================================================================
# Core logic
# ============================================================================


def get_active_requests(models, uid, config):
    """Get active HR data collection requests with employee info.

    Returns list of dicts with request_id, employee_id, employee_name,
    work_email, and phase status.
    """
    db, user, pwd = config['db'], config['user'], config['password']

    request_ids = models.execute_kw(db, uid, pwd,
        'hr.data.collection.request', 'search', [[
            ('state', 'in', ['in_progress', 'draft']),
        ]])

    if not request_ids:
        return []

    requests_data = models.execute_kw(db, uid, pwd,
        'hr.data.collection.request', 'read', [request_ids], {
            'fields': [
                'employee_id', 'state',
                'cedula_photo_received', 'rif_photo_received',
                'cedula_number', 'rif_number_value',
            ],
        })

    results = []
    for req in requests_data:
        emp_id = req['employee_id'][0] if req['employee_id'] else None
        if not emp_id:
            continue

        emp_data = models.execute_kw(db, uid, pwd,
            'hr.employee', 'read', [[emp_id]], {
                'fields': ['name', 'work_email'],
            })
        if not emp_data:
            continue

        results.append({
            'request_id': req['id'],
            'employee_id': emp_id,
            'employee_name': emp_data[0].get('name', ''),
            'work_email': (emp_data[0].get('work_email') or '').lower().strip(),
            'state': req['state'],
            'cedula_photo_received': req.get('cedula_photo_received', False),
            'rif_photo_received': req.get('rif_photo_received', False),
            'cedula_number': req.get('cedula_number', ''),
            'rif_number_value': req.get('rif_number_value', ''),
        })

    return results


def find_hr_threads_with_attachments(fs_conn, since_date, employee_emails):
    """Search Freescout HR mailbox for threads with attachments from known employees.

    Args:
        fs_conn: pymysql connection
        since_date: ISO datetime string — only look at threads after this date
        employee_emails: set of lowercase employee work_email addresses

    Returns list of dicts with thread info + attachment details.
    """
    if not employee_emails:
        return []

    cur = fs_conn.cursor()

    # Find conversations in HR mailbox
    cur.execute("""
        SELECT c.id AS conv_id, c.number, c.subject, c.customer_email,
               c.status, c.created_at
        FROM conversations c
        WHERE c.mailbox_id = %s
          AND c.status != 3
          AND c.created_at >= %s
    """, (HR_MAILBOX_ID, since_date))
    conversations = cur.fetchall()

    if not conversations:
        return []

    results = []
    for conv in conversations:
        conv_id = conv['conv_id']
        customer_email = (conv.get('customer_email') or '').lower().strip()

        # Match by customer email OR by thread "from" field
        matched_email = None
        if customer_email in employee_emails:
            matched_email = customer_email

        # Check threads for attachments
        cur.execute("""
            SELECT t.id AS thread_id, t.type, t.body, t.created_at,
                   t.`from` AS from_addr
            FROM threads t
            WHERE t.conversation_id = %s
              AND t.type = 1
              AND t.created_at >= %s
            ORDER BY t.created_at ASC
        """, (conv_id, since_date))
        threads = cur.fetchall()

        for thread in threads:
            thread_id = thread['thread_id']
            from_addr = (thread.get('from_addr') or '').lower().strip()

            # Try to match from address to an employee
            if not matched_email:
                for email in employee_emails:
                    if email in from_addr:
                        matched_email = email
                        break

            if not matched_email:
                continue

            # Check for attachments on this thread
            cur.execute("""
                SELECT a.id AS att_id, a.file_dir, a.file_name, a.mime_type, a.size
                FROM attachments a
                WHERE a.thread_id = %s
                  AND a.embedded = 0
            """, (thread_id,))
            attachments = cur.fetchall()

            for att in attachments:
                if att['mime_type'] not in ACCEPTED_MIMES:
                    continue
                results.append({
                    'conv_id': conv_id,
                    'conv_number': conv.get('number', 0),
                    'conv_subject': conv.get('subject', ''),
                    'thread_id': thread_id,
                    'from_addr': from_addr,
                    'matched_email': matched_email,
                    'thread_date': thread['created_at'],
                    'att_id': att['att_id'],
                    'file_dir': att['file_dir'],
                    'file_name': att['file_name'],
                    'mime_type': att['mime_type'],
                    'size': att['size'],
                })

    return results


def read_freescout_attachment(file_dir, file_name):
    """Read attachment binary from Freescout disk storage.

    Returns (binary_data, file_name) or (None, None) on failure.
    """
    file_path = os.path.join(FREESCOUT_ATTACHMENT_PATH, file_dir, file_name)
    if not os.path.exists(file_path):
        logger.warning("Attachment file not found: %s", file_path)
        return None, None
    with open(file_path, 'rb') as f:
        return f.read(), file_name


def upload_attachment_to_odoo(models, uid, config, employee_id, binary_data,
                              filename, mimetype, doc_type, doc_label):
    """Upload an attachment to Odoo and link to employee identification_attachment_ids.

    Args:
        doc_type: 'cedula' or 'rif' (for naming)
        doc_label: e.g. 'V12345678' or 'V-12345678-9'

    Returns attachment_id or None.
    """
    db, user, pwd = config['db'], config['user'], config['password']

    ext_map = {
        'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp',
        'image/gif': '.gif', 'application/pdf': '.pdf',
    }
    ext = ext_map.get(mimetype, '.jpg')
    att_name = f"{doc_type.title()} - {doc_label}{ext}" if doc_label else filename

    b64_data = base64.b64encode(binary_data).decode('utf-8')

    att_id = models.execute_kw(db, uid, pwd,
        'ir.attachment', 'create', [{
            'name': att_name,
            'type': 'binary',
            'datas': b64_data,
            'mimetype': mimetype,
            'res_model': 'hr.employee',
            'res_id': employee_id,
        }])

    # Link to identification_attachment_ids
    models.execute_kw(db, uid, pwd,
        'hr.employee', 'write', [[employee_id], {
            'identification_attachment_ids': [(4, att_id)],
        }])

    logger.info("Uploaded attachment '%s' (id=%d) for employee %d", att_name, att_id, employee_id)
    return att_id


def update_request_phase(models, uid, config, request_id, doc_type):
    """Mark document photo as received on the collection request."""
    db, user, pwd = config['db'], config['user'], config['password']

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if doc_type == 'cedula':
        models.execute_kw(db, uid, pwd,
            'hr.data.collection.request', 'write', [[request_id], {
                'cedula_photo_received': True,
                'cedula_photo_date': now,
            }])
    elif doc_type == 'rif':
        models.execute_kw(db, uid, pwd,
            'hr.data.collection.request', 'write', [[request_id], {
                'rif_photo_received': True,
                'rif_photo_date': now,
            }])
    logger.info("Request #%d: marked %s photo as received", request_id, doc_type)


def post_freescout_note(fs_conn, conv_id, note_body):
    """Post an internal note on a Freescout conversation confirming attachment receipt."""
    cur = fs_conn.cursor()

    # Get admin user for note attribution
    cur.execute("SELECT id FROM users WHERE role = 2 ORDER BY id LIMIT 1")
    admin_row = cur.fetchone()
    admin_id = admin_row['id'] if admin_row else 1

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cur.execute("""
        INSERT INTO threads (conversation_id, type, status, state, body,
                             created_by_user_id, source_via, created_at, updated_at)
        VALUES (%s, 3, 6, 2, %s, %s, 'user', %s, %s)
    """, (conv_id, note_body, admin_id, now, now))

    # Update conversation threads_count and timestamp
    cur.execute("""
        UPDATE conversations
        SET threads_count = threads_count + 1,
            user_updated_at = %s
        WHERE id = %s
    """, (now, conv_id))

    fs_conn.commit()
    logger.info("Posted Freescout note on conversation #%d", conv_id)


def guess_doc_type(filename, mime_type):
    """Try to guess if an attachment is a Cedula or RIF based on filename.

    Returns 'cedula', 'rif', or 'unknown'.
    """
    fname_lower = filename.lower()
    if 'rif' in fname_lower:
        return 'rif'
    if 'cedula' in fname_lower or 'ci' in fname_lower or 'identidad' in fname_lower:
        return 'cedula'
    # For ambiguous names, return 'unknown' — will be classified manually
    return 'unknown'


# ============================================================================
# Main
# ============================================================================


def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description='HR Email Checker for Freescout')
    parser.add_argument('--live', action='store_true', help='Disable DRY_RUN')
    parser.add_argument('--since', type=str, help='Override since date (ISO format)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False

    logger.info("=" * 60)
    logger.info("HR Email Checker starting (DRY_RUN=%s, TARGET_ENV=%s)", DRY_RUN, TARGET_ENV)

    state = load_state()
    since_date = args.since or state.get('last_run', '2026-02-18T00:00:00')
    logger.info("Checking threads since: %s", since_date)

    # Phase 1: Connect
    try:
        models, uid, config = connect_odoo()
        fs_conn = connect_freescout()
    except Exception as e:
        logger.error("Connection failed: %s", e)
        return

    try:
        # Phase 2: Get active requests + employee emails
        active_requests = get_active_requests(models, uid, config)
        if not active_requests:
            logger.info("No active data collection requests found. Done.")
            save_state(state)
            return

        email_to_request = {}
        for req in active_requests:
            if req['work_email']:
                email_to_request[req['work_email']] = req
        employee_emails = set(email_to_request.keys())
        logger.info("Active requests: %d, employee emails to watch: %s",
                     len(active_requests), employee_emails)

        # Phase 3: Find threads with attachments in HR mailbox
        matches = find_hr_threads_with_attachments(fs_conn, since_date, employee_emails)
        logger.info("Found %d attachment(s) matching active employees", len(matches))

        if not matches:
            logger.info("No new attachments. Done.")
            save_state(state)
            return

        # Phase 4: Process each matching attachment
        processed = 0
        for match in matches:
            email = match['matched_email']
            req_info = email_to_request.get(email)
            if not req_info:
                continue

            doc_type = guess_doc_type(match['file_name'], match['mime_type'])
            # Skip if this phase is already done
            if doc_type == 'cedula' and req_info['cedula_photo_received']:
                logger.info("Skipping cedula attachment — already received for request #%d",
                            req_info['request_id'])
                continue
            if doc_type == 'rif' and req_info['rif_photo_received']:
                logger.info("Skipping RIF attachment — already received for request #%d",
                            req_info['request_id'])
                continue

            doc_label = ''
            if doc_type == 'cedula':
                doc_label = req_info.get('cedula_number', '')
            elif doc_type == 'rif':
                doc_label = req_info.get('rif_number_value', '')

            logger.info(
                "Processing: conv=#%d, thread=#%d, file=%s (%s), "
                "employee=%s, type=%s",
                match['conv_id'], match['thread_id'], match['file_name'],
                match['mime_type'], req_info['employee_name'], doc_type)

            # Read file from Freescout disk
            binary_data, filename = read_freescout_attachment(
                match['file_dir'], match['file_name'])
            if not binary_data:
                logger.warning("Could not read attachment file — skipping")
                continue

            logger.info("Read %d bytes from disk: %s", len(binary_data), filename)

            if DRY_RUN:
                logger.info("DRY_RUN: Would upload '%s' (%s) for employee %s (request #%d)",
                            filename, doc_type, req_info['employee_name'],
                            req_info['request_id'])
            else:
                # Upload to Odoo
                att_id = upload_attachment_to_odoo(
                    models, uid, config,
                    req_info['employee_id'], binary_data, filename,
                    match['mime_type'], doc_type, doc_label)

                # Update request phase
                if doc_type in ('cedula', 'rif'):
                    update_request_phase(
                        models, uid, config,
                        req_info['request_id'], doc_type)

                # Post Freescout note
                note = (
                    f'<p><strong>[GLENDA-HR]</strong> Documento recibido y procesado.</p>'
                    f'<p>Tipo: {doc_type.upper()}<br/>'
                    f'Archivo: {filename}<br/>'
                    f'Empleado: {req_info["employee_name"]}<br/>'
                    f'Solicitud: #{req_info["request_id"]}</p>'
                    f'<p><em>Procesado automaticamente el '
                    f'{datetime.now().strftime("%d/%m/%Y %H:%M")}</em></p>'
                )
                post_freescout_note(fs_conn, match['conv_id'], note)

            processed += 1

        logger.info("Processed %d attachment(s). Done.", processed)
        save_state(state)

    except Exception as e:
        logger.error("Error during processing: %s", e, exc_info=True)
    finally:
        fs_conn.close()


if __name__ == '__main__':
    main()
