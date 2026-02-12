#!/usr/bin/env python3
"""
Daily Bounce Processor - Phase 1

Detects bounced emails from Freescout (READ-ONLY) and cleans up Odoo contacts.
Supports TEST_MODE (simulated data) and DRY_RUN (no modifications).

3-Tier Logic (reason + tag based):
  - CLEAN: Representante partner + PERMANENT failure (invalid_address, domain_not_found)
           -> remove from res.partner + mailing.contact
  - FLAG:  Temporary failure (mailbox_full, rejected, other) OR non-Representante
           -> log for manual review, no auto-modification
  - LOG:   Bounced email not found in Odoo -> CSV log only

Post-processing:
  - Creates mail.bounce.log records in Odoo (testing) for each processed bounce
  - Updates Freescout conversations with tier prefix, bounced email as customer,
    internal note, and status change (active or closed)

Usage:
    python3 /opt/odoo-dev/scripts/daily_bounce_processor.py

Author: Claude Code Assistant
Date: 2026-02-03
Updated: 2026-02-06 (Freescout post-processing + Odoo bounce log creation)
"""

import csv
import json
import os
import re
import xmlrpc.client
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

# Mode flags
TEST_MODE = False      # True = use simulated bounce data, False = query Freescout
DRY_RUN = True         # True = no modifications, False = apply changes

# Target environment: 'testing' or 'production'
TARGET_ENV = os.environ.get('TARGET_ENV', 'production')

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

# Freescout MySQL (READ-ONLY) - only used when TEST_MODE = False
FREESCOUT_DB_HOST = os.environ.get('FREESCOUT_DB_HOST', 'localhost')
FREESCOUT_DB_USER = os.environ.get('FREESCOUT_DB_USER', 'free297')
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '1gczp1S@3!')
FREESCOUT_DB_NAME = os.environ.get('FREESCOUT_DB_NAME', 'free297')

# Representante tag IDs (res.partner.category)
REPRESENTANTE_TAG_IDS = [25, 26]  # 25=Representante, 26=Representante PDVSA

# Permanent bounce reasons: safe to auto-clean (email will never work again)
PERMANENT_REASONS = {'invalid_address', 'domain_not_found'}
# Temporary bounce reasons: flag for review (customer may fix the issue)
TEMPORARY_REASONS = {'mailbox_full', 'rejected', 'other'}

# Time window: only process bounces from last N days
BOUNCE_WINDOW_DAYS = 180  # 6 months

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'bounce_state.json')
LOG_DIR = os.path.join(SCRIPT_DIR, 'bounce_logs')
CSV_LOG_FILE = os.path.join(LOG_DIR, 'bounce_log.csv')

# Odoo bounce log creation
CREATE_BOUNCE_LOG = True  # Create mail.bounce.log records in Odoo

# Freescout post-processing (MySQL writes)
FREESCOUT_POSTPROCESS = True  # Update Freescout conversations after processing
FREESCOUT_BASE_URL = 'https://freescout.ueipab.edu.ve'

# ============================================================================
# Test Bounce Data (used when TEST_MODE = True)
# ============================================================================

TEST_BOUNCE_DATA = [
    {
        'freescout_conversation_id': 9001,
        'bounced_email': 'bounce.single@example.com',
        'bounce_reason_text': '550 5.1.1 The email account does not exist',
        'subject': 'Undelivered Mail Returned to Sender',
        'created_at': '2026-02-03 07:00:00',
    },
    {
        'freescout_conversation_id': 9002,
        'bounced_email': 'bounce.multi@example.com',
        'bounce_reason_text': '550 5.2.1 mailbox full',
        'subject': 'Delivery Status Notification (Failure)',
        'created_at': '2026-02-03 07:01:00',
    },
    {
        'freescout_conversation_id': 9003,
        'bounced_email': 'bounce.mailing@example.com',
        'bounce_reason_text': '550 5.1.2 Bad destination mailbox address',
        'subject': 'Undelivered Mail Returned to Sender',
        'created_at': '2026-02-03 07:02:00',
    },
    {
        'freescout_conversation_id': 9004,
        'bounced_email': 'notfound@nonexistent-domain.com',
        'bounce_reason_text': '550 Host not found',
        'subject': 'Delivery Status Notification (Failure)',
        'created_at': '2026-02-03 07:03:00',
    },
]

# ============================================================================
# BounceProcessor
# ============================================================================


class BounceProcessor:

    def __init__(self):
        self.uid = None
        self.models = None
        self.state = {}
        self.freescout_conn = None       # Persistent Freescout MySQL connection
        self.freescout_admin_id = None   # Freescout admin user ID for notes
        self.freescout_updates = {}      # conv_id -> update info for post-processing
        self.results = {
            'processed': [],
            'partners_cleaned': [],
            'mailing_contacts_cleaned': [],
            'flagged': [],          # non-Representante bounces for review
            'not_found': [],
            'errors': [],
            'bounce_logs_created': [],  # mail.bounce.log records created
            'freescout_updated': [],    # Freescout conversations updated
            'skipped_existing': 0,      # bounces skipped (already in Odoo)
        }

    # ---- Main orchestrator ------------------------------------------------

    def run(self):
        cutoff_date = (datetime.now() - timedelta(days=BOUNCE_WINDOW_DAYS)).strftime('%Y-%m-%d')

        print("=" * 70)
        print("DAILY BOUNCE PROCESSOR")
        print("=" * 70)
        print(f"  Date:      {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  TEST_MODE: {TEST_MODE}")
        print(f"  DRY_RUN:   {DRY_RUN}")
        print(f"  Target:    {TARGET_ENV}")
        print(f"  Odoo:      {ODOO_URL} / {ODOO_DB}")
        print(f"  Tags:      {REPRESENTANTE_TAG_IDS} (Representante, Representante PDVSA)")
        print(f"  Window:    Last {BOUNCE_WINDOW_DAYS} days (>= {cutoff_date})")
        print(f"  CLEAN:     Representante + permanent ({', '.join(sorted(PERMANENT_REASONS))})")
        print(f"  FLAG:      Temporary ({', '.join(sorted(TEMPORARY_REASONS))}) or non-Representante")
        print(f"  Bounce Log:  {CREATE_BOUNCE_LOG} (create mail.bounce.log in Odoo)")
        print(f"  FS Postproc: {FREESCOUT_POSTPROCESS} (update Freescout conversations)")
        print()

        self.load_state()

        bounces = self.get_bounce_data()
        if not bounces:
            print("No new bounces to process.")
            return

        # Deduplicate: only process first occurrence of each email
        seen_emails = set()
        unique_bounces = []
        for b in bounces:
            email = b['bounced_email'].lower()
            if email not in seen_emails:
                seen_emails.add(email)
                unique_bounces.append(b)

        print(f"Found {len(bounces)} bounce(s), {len(unique_bounces)} unique email(s) to process.\n")
        bounces = unique_bounces

        if not self.connect_odoo():
            print("ERROR: Cannot connect to Odoo. Aborting.")
            return

        for bounce in bounces:
            self.process_bounce(bounce)

        # Freescout post-processing (MySQL writes)
        if FREESCOUT_POSTPROCESS and self.freescout_updates:
            self._apply_freescout_postprocessing()

        self.save_state()
        self.write_csv_log()
        self.generate_report()
        self.print_summary()

        # Close Freescout connection if open
        self._close_freescout_connection()

    # ---- State management -------------------------------------------------

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                self.state = json.load(f)
            print(f"Loaded state: last_conversation_id={self.state.get('last_conversation_id', 0)}, "
                  f"last_thread_id={self.state.get('last_thread_id', 0)}")
        else:
            self.state = {
                'last_conversation_id': 0,
                'last_thread_id': 0,
                'last_run': None,
            }
            print("No previous state found. Starting fresh.")

    def save_state(self):
        processed = self.results['processed']
        if processed:
            max_conv_id = max(b['freescout_conversation_id'] for b in processed)
            if max_conv_id > self.state.get('last_conversation_id', 0):
                self.state['last_conversation_id'] = max_conv_id

        self.state['last_run'] = datetime.now().isoformat()

        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)
        print(f"\nState saved to {STATE_FILE}")

    # ---- Bounce data retrieval --------------------------------------------

    def get_bounce_data(self):
        if TEST_MODE:
            print("Using TEST bounce data (simulated).\n")
            return TEST_BOUNCE_DATA
        else:
            return self._query_freescout()

    def _connect_freescout(self):
        """Open and return persistent Freescout MySQL connection."""
        if self.freescout_conn and self.freescout_conn.open:
            return self.freescout_conn
        try:
            import pymysql
        except ImportError:
            print("ERROR: pymysql not installed. Run: pip install pymysql")
            return None

        try:
            self.freescout_conn = pymysql.connect(
                host=FREESCOUT_DB_HOST,
                user=FREESCOUT_DB_USER,
                password=FREESCOUT_DB_PASSWORD,
                database=FREESCOUT_DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
            )
            # Get admin user ID for note authorship
            with self.freescout_conn.cursor() as cursor:
                cursor.execute("SELECT id FROM users ORDER BY id LIMIT 1")
                row = cursor.fetchone()
                self.freescout_admin_id = row['id'] if row else 1
            print(f"Connected to Freescout MySQL (admin user_id={self.freescout_admin_id})")
            return self.freescout_conn
        except Exception as e:
            print(f"ERROR connecting to Freescout MySQL: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _close_freescout_connection(self):
        """Close Freescout MySQL connection if open."""
        if self.freescout_conn and self.freescout_conn.open:
            self.freescout_conn.close()
            print("Freescout MySQL connection closed.")

    def _query_freescout(self):
        conn = self._connect_freescout()
        if not conn:
            return []

        bounces = []
        last_conv_id = self.state.get('last_conversation_id', 0)
        last_thread_id = self.state.get('last_thread_id', 0)
        cutoff_date = (datetime.now() - timedelta(days=BOUNCE_WINDOW_DAYS)).strftime('%Y-%m-%d')

        try:
            with conn.cursor() as cursor:
                # Type 1: Standalone DSN conversations (with date filter)
                cursor.execute("""
                    SELECT c.id, c.subject, c.created_at, t.body
                    FROM conversations c
                    JOIN threads t ON t.conversation_id = c.id
                    WHERE (c.subject LIKE '%%Undelivered%%' OR c.subject LIKE '%%Delivery Status%%')
                      AND c.id > %s
                      AND c.created_at >= %s
                    ORDER BY c.id ASC
                """, (last_conv_id, cutoff_date))

                for row in cursor.fetchall():
                    email = self.extract_email_from_dsn(row.get('body', ''))
                    reason_text = self._extract_error_block(row.get('body', ''))
                    if email:
                        bounces.append({
                            'freescout_conversation_id': row['id'],
                            'bounced_email': email,
                            'bounce_reason_text': reason_text,
                            'subject': row.get('subject', ''),
                            'created_at': str(row.get('created_at', '')),
                        })

                # Type 2: Inline bounce threads (with date filter)
                cursor.execute("""
                    SELECT c.id AS conversation_id, t.id AS thread_id, t.body, t.created_at
                    FROM threads t
                    JOIN conversations c ON t.conversation_id = c.id
                    WHERE (t.`from` LIKE '%%postmaster@%%' OR t.`from` LIKE '%%mailer-daemon@%%')
                      AND t.id > %s
                      AND t.created_at >= %s
                    ORDER BY t.id ASC
                """, (last_thread_id, cutoff_date))

                for row in cursor.fetchall():
                    email = self.extract_email_from_dsn(row.get('body', ''))
                    reason_text = self._extract_error_block(row.get('body', ''))
                    if email:
                        bounces.append({
                            'freescout_conversation_id': row['conversation_id'],
                            'bounced_email': email,
                            'bounce_reason_text': reason_text,
                            'subject': 'Inline bounce thread',
                            'created_at': str(row.get('created_at', '')),
                        })
                        if row['thread_id'] > self.state.get('last_thread_id', 0):
                            self.state['last_thread_id'] = row['thread_id']

        except Exception as e:
            print(f"ERROR querying Freescout: {e}")
            import traceback
            traceback.print_exc()

        return bounces

    # ---- Email extraction / classification --------------------------------

    @staticmethod
    def _extract_error_block(html_body):
        """Extract the monospace error block from bounce HTML for better classification."""
        if not html_body:
            return ''
        # Google/Outlook bounces put the raw error in a monospace <p>
        match = re.search(r'<p style="font-family:monospace">\s*(.*?)\s*</p>', html_body, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: MailChannels style "I'm sorry to have to inform you..."
        match = re.search(r"I'm sorry.*?(?=<br|$)", html_body, re.DOTALL)
        if match:
            return match.group(0).strip()[:300]
        return html_body[:300]

    @staticmethod
    def extract_email_from_dsn(html_body):
        """Extract the bounced email address from DSN bounce HTML body."""
        if not html_body:
            return None

        # Pattern 1: "Final-Recipient: rfc822; user@domain.com"
        match = re.search(r'Final-Recipient:\s*rfc822;\s*([^\s<>"]+@[^\s<>"]+)', html_body, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()

        # Pattern 2: "Original-Recipient: rfc822;user@domain.com"
        match = re.search(r'Original-Recipient:\s*rfc822;\s*([^\s<>"]+@[^\s<>"]+)', html_body, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()

        # Pattern 3: Google/Outlook style: <b>email@domain.com</b>
        match = re.search(r'<b>([^\s<>"]+@[^\s<>"]+)</b>', html_body, re.IGNORECASE)
        if match:
            email = match.group(1).strip().lower()
            skip = ('postmaster@', 'mailer-daemon@', 'noreply@', 'no-reply@', 'soporte@')
            if not any(email.startswith(p) for p in skip):
                return email

        # Pattern 4: "to/for/address" phrases
        match = re.search(r'(?:to|for|address|recipient)[:\s]+<?([^\s<>"]+@[^\s<>"]+)>?', html_body, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()

        # Pattern 5: generic email in the first few lines
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', html_body)
        if match:
            email = match.group(0).lower()
            skip_prefixes = ('postmaster@', 'mailer-daemon@', 'noreply@', 'no-reply@')
            if not any(email.startswith(p) for p in skip_prefixes):
                return email

        return None

    @staticmethod
    def classify_bounce_reason(reason_text):
        """Categorize bounce type from error text."""
        if not reason_text:
            return 'other'

        text = reason_text.lower()

        if any(p in text for p in (
            'mailbox full', '5.2.1', 'over quota', 'overquota',
            'out of storage', '4.2.2', 'quota exceeded', 'inbox is full',
        )):
            return 'mailbox_full'
        if any(p in text for p in (
            'does not exist', '5.1.1', 'user unknown', 'no such user',
            'address not found', 'unavailable', '5.5.0',
            'address couldn', 'unable to receive',
        )):
            return 'invalid_address'
        if any(p in text for p in (
            'host not found', '5.1.2', 'domain not found', 'no mx',
            'dns error', 'deadline_exceeded', 'dns type',
            'name or service not known',
        )):
            return 'domain_not_found'
        if any(p in text for p in (
            'rejected', '5.7.', 'blocked', 'spam',
            'policy', 'not allowed', 'blacklist',
        )):
            return 'rejected'

        return 'other'

    # ---- Odoo connection --------------------------------------------------

    def connect_odoo(self):
        try:
            common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
            self.uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})

            if not self.uid:
                print("ERROR: Odoo authentication failed.")
                return False

            self.models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            print(f"Connected to Odoo as user ID: {self.uid}\n")
            return True

        except Exception as e:
            print(f"ERROR connecting to Odoo: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ---- Tag checking -----------------------------------------------------

    def _partner_has_representante_tag(self, partner_id):
        """Check if a partner has any of the Representante tags."""
        partner = self.models.execute_kw(
            ODOO_DB, self.uid, ODOO_PASSWORD,
            'res.partner', 'read',
            [[partner_id]],
            {'fields': ['category_id']}
        )
        if partner:
            return bool(set(partner[0].get('category_id', [])) & set(REPRESENTANTE_TAG_IDS))
        return False

    def _get_partner_tags(self, tag_ids):
        """Get tag names from IDs."""
        if not tag_ids:
            return []
        tags = self.models.execute_kw(
            ODOO_DB, self.uid, ODOO_PASSWORD,
            'res.partner.category', 'read',
            [tag_ids],
            {'fields': ['name']}
        )
        return [t['name'] for t in tags]

    # ---- Bounce log creation (Odoo) --------------------------------------

    def _create_bounce_log_record(self, bounced_email, reason, reason_text,
                                  conv_id, tier, partner_id=None,
                                  mailing_contact_id=None):
        """Create a mail.bounce.log record in Odoo via XML-RPC."""
        if not CREATE_BOUNCE_LOG:
            return None

        vals = {
            'bounced_email': bounced_email,
            'bounce_reason': reason,
            'bounce_detail': (reason_text or '')[:500],
            'freescout_conversation_id': conv_id,
            'action_tier': tier,
        }
        if partner_id:
            vals['partner_id'] = partner_id
        if mailing_contact_id:
            vals['mailing_contact_id'] = mailing_contact_id

        prefix = "[DRY_RUN] " if DRY_RUN else ""
        print(f"     {prefix}Creating mail.bounce.log: tier={tier}, "
              f"partner={partner_id or 'N/A'}, mc={mailing_contact_id or 'N/A'}")

        if DRY_RUN:
            self.results['bounce_logs_created'].append({
                'bounced_email': bounced_email, 'tier': tier,
                'conv_id': conv_id, 'record_id': None,
            })
            return None

        try:
            record_id = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mail.bounce.log', 'create',
                [vals]
            )
            print(f"     Created mail.bounce.log #{record_id}")
            self.results['bounce_logs_created'].append({
                'bounced_email': bounced_email, 'tier': tier,
                'conv_id': conv_id, 'record_id': record_id,
            })
            return record_id
        except Exception as e:
            print(f"     WARNING: Could not create bounce log: {e}")
            self.results['errors'].append({
                'email': bounced_email, 'model': 'mail.bounce.log',
                'error': str(e),
            })
            return None

    # ---- Freescout update accumulation ------------------------------------

    def _accumulate_freescout_update(self, conv_id, tier, bounced_email,
                                     reason, partner_id=None,
                                     partner_name=None,
                                     remaining_emails=None,
                                     bounce_log_id=None,
                                     mailing_contact_id=None):
        """Accumulate a Freescout conversation update for post-processing."""
        if not FREESCOUT_POSTPROCESS:
            return

        tier_config = {
            'clean': {
                'prefix': '[LIMPIADO]',
                'status': 3,  # Closed - resolution handled in Odoo
                'action_desc': 'Email removido automaticamente del contacto Odoo',
            },
            'flag': {
                'prefix': '[REVISION]',
                'status': 3,  # Closed - resolution handled in Odoo
                'action_desc': 'Marcado para revision manual en Odoo',
            },
            'not_found': {
                'prefix': '[NO ENCONTRADO]',
                'status': 3,  # Closed - no action possible
                'action_desc': 'Email no encontrado en Odoo',
            },
            'resolved_dup': {
                'prefix': '[RESUELTO-AI]',
                'status': 3,  # Closed - already resolved
                'action_desc': 'Duplicado de bounce ya resuelto en Odoo',
            },
            'existing_dup': {
                'prefix': '[DUPLICADO]',
                'status': 3,  # Closed - already tracked
                'action_desc': 'Duplicado de bounce ya registrado en Odoo',
            },
        }

        config = tier_config.get(tier, tier_config['flag'])

        # Only store first update per conversation (dedup)
        if conv_id in self.freescout_updates:
            return

        self.freescout_updates[conv_id] = {
            'tier': tier,
            'prefix': config['prefix'],
            'conv_status': config['status'],
            'action_desc': config['action_desc'],
            'bounced_email': bounced_email,
            'reason': reason,
            'partner_id': partner_id,
            'partner_name': partner_name,
            'remaining_emails': remaining_emails,
            'bounce_log_id': bounce_log_id,
            'mailing_contact_id': mailing_contact_id,
        }

    # ---- Per-bounce processing (3-tier) -----------------------------------

    def _check_existing_bounce_log(self, email):
        """Check if a bounce log already exists for this email in Odoo.

        Returns: dict with 'exists' bool, 'state' str, 'id' int, or None.
        """
        try:
            bl_ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mail.bounce.log', 'search_read',
                [[('bounced_email', '=', email)]],
                {'fields': ['id', 'state'], 'limit': 1,
                 'order': 'id desc'}
            )
            if bl_ids:
                return bl_ids[0]
        except Exception as e:
            print(f"  WARNING: Could not check existing bounce logs: {e}")
        return None

    def process_bounce(self, bounce):
        email = bounce['bounced_email']
        conv_id = bounce['freescout_conversation_id']
        reason_text = bounce['bounce_reason_text']
        reason = self.classify_bounce_reason(reason_text)

        print("-" * 70)
        print(f"Processing bounce: {email}")
        print(f"  Freescout conversation: #{conv_id}")
        print(f"  Reason: {reason} ({reason_text[:80]}...)" if len(reason_text) > 80
              else f"  Reason: {reason} ({reason_text})")

        self.results['processed'].append(bounce)

        # ── Cross-check: skip if bounce log already exists in Odoo ──
        existing_bl = self._check_existing_bounce_log(email)
        if existing_bl:
            bl_state = existing_bl['state']
            bl_id = existing_bl['id']
            print(f"  -> SKIP: Bounce log #{bl_id} already exists (state={bl_state})")
            # Tag Freescout conversation so support team sees it's handled
            if bl_state == 'resolved':
                self._accumulate_freescout_update(
                    conv_id, 'resolved_dup', email, reason,
                    bounce_log_id=bl_id)
            else:
                self._accumulate_freescout_update(
                    conv_id, 'existing_dup', email, reason,
                    bounce_log_id=bl_id)
            self.results['skipped_existing'] = self.results.get('skipped_existing', 0) + 1
            return

        # Search for the email in res.partner
        partner_ids = self._search_partners_by_email(email)

        if partner_ids:
            partners = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'res.partner', 'read',
                [partner_ids],
                {'fields': ['id', 'name', 'email', 'category_id']}
            )

            # Separate into Representante vs non-Representante
            rep_partners = []
            non_rep_partners = []
            for p in partners:
                # Verify email actually matches (ilike can be too broad)
                emails_in_field = [e.strip().lower() for e in (p.get('email') or '').split(';') if e.strip()]
                if email.lower() not in emails_in_field:
                    continue
                if set(p.get('category_id', [])) & set(REPRESENTANTE_TAG_IDS):
                    rep_partners.append(p)
                else:
                    non_rep_partners.append(p)

            is_permanent = reason in PERMANENT_REASONS

            # TIER 1: CLEAN only Representante + permanent failure
            if is_permanent:
                for partner in rep_partners:
                    tag_names = self._get_partner_tags(partner.get('category_id', []))
                    self._clean_partner(partner, email, reason, reason_text, conv_id, tag_names)

                # Also clean mailing.contact if any Representante partner was cleaned
                if rep_partners:
                    self._search_and_clean_mailing_contacts(email, reason, reason_text, conv_id)
            else:
                # Temporary failure: FLAG even Representante partners
                for partner in rep_partners:
                    tag_names = self._get_partner_tags(partner.get('category_id', []))
                    self._flag_partner(partner, email, reason, reason_text, conv_id, tag_names,
                                       flag_reason='temporary')

            # TIER 2: FLAG non-Representante partners (any reason)
            for partner in non_rep_partners:
                tag_names = self._get_partner_tags(partner.get('category_id', []))
                self._flag_partner(partner, email, reason, reason_text, conv_id, tag_names,
                                   flag_reason='non-representante')

            if not rep_partners and not non_rep_partners:
                # Email found via ilike but didn't actually match any partner
                self._handle_not_found(email, conv_id)

        else:
            # Check mailing.contact only (no partner found)
            mc_found = self._search_mailing_contacts_by_email(email)
            if mc_found:
                # Email exists in mailing.contact but no partner -> FLAG
                self._flag_mailing_contact_only(email, reason, reason_text, conv_id, mc_found)
            else:
                # TIER 3: LOG - not found anywhere
                self._handle_not_found(email, conv_id)

        print()

    def _search_partners_by_email(self, email):
        """Search res.partner by email (ilike for case-insensitive)."""
        try:
            return self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'res.partner', 'search',
                [[['email', 'ilike', email]]]
            )
        except Exception as e:
            print(f"  -> ERROR searching partners: {e}")
            self.results['errors'].append({'email': email, 'model': 'res.partner', 'error': str(e)})
            return []

    def _search_mailing_contacts_by_email(self, email):
        """Search mailing.contact by email."""
        try:
            contact_ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mailing.contact', 'search',
                [[['email', 'ilike', email]]]
            )
            if contact_ids:
                return self.models.execute_kw(
                    ODOO_DB, self.uid, ODOO_PASSWORD,
                    'mailing.contact', 'read',
                    [contact_ids],
                    {'fields': ['id', 'name', 'email']}
                )
        except Exception as e:
            print(f"  -> ERROR searching mailing contacts: {e}")
        return []

    # ---- TIER 1: CLEAN (Representante) ------------------------------------

    def _clean_partner(self, partner, email, reason, reason_text, conv_id, tag_names):
        """Remove bounced email from a Representante partner."""
        current_email = partner.get('email', '') or ''
        new_email = self.remove_bounced_email(current_email, email)

        prefix = "[DRY_RUN] " if DRY_RUN else ""
        tags_str = ', '.join(tag_names)
        print(f"  -> {prefix}CLEAN res.partner #{partner['id']} ({partner['name']}) [{tags_str}]")
        print(f"     Before: {current_email}")
        print(f"     After:  {new_email or '(empty)'}")

        if not DRY_RUN:
            self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'res.partner', 'write',
                [[partner['id']], {'email': new_email}]
            )
            self._post_chatter_note(
                'res.partner', partner['id'],
                email, reason, reason_text,
                current_email, new_email, conv_id
            )

        # Create bounce log record
        log_id = self._create_bounce_log_record(
            email, reason, reason_text, conv_id, 'clean',
            partner_id=partner['id'])

        # Accumulate Freescout update
        self._accumulate_freescout_update(
            conv_id, 'clean', email, reason,
            partner_id=partner['id'],
            partner_name=partner['name'],
            remaining_emails=new_email or None,
            bounce_log_id=log_id)

        self.results['partners_cleaned'].append({
            'partner_id': partner['id'],
            'partner_name': partner['name'],
            'email': email,
            'old_email_field': current_email,
            'new_email_field': new_email,
            'reason': reason,
            'conversation_id': conv_id,
            'tags': tag_names,
        })

    def _search_and_clean_mailing_contacts(self, email, reason, reason_text, conv_id):
        """Clean mailing.contact records for a Representante bounce."""
        try:
            contact_ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mailing.contact', 'search',
                [[['email', 'ilike', email]]]
            )

            if not contact_ids:
                return

            contacts = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mailing.contact', 'read',
                [contact_ids],
                {'fields': ['id', 'name', 'email']}
            )

            for contact in contacts:
                current_email = contact.get('email', '') or ''
                emails_in_field = [e.strip().lower() for e in current_email.split(';') if e.strip()]
                if email.lower() not in emails_in_field:
                    continue

                new_email = self.remove_bounced_email(current_email, email)

                prefix = "[DRY_RUN] " if DRY_RUN else ""
                print(f"  -> {prefix}CLEAN mailing.contact #{contact['id']} ({contact['name']})")
                print(f"     Before: {current_email}")
                print(f"     After:  {new_email or '(empty)'}")

                if not DRY_RUN:
                    self.models.execute_kw(
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'mailing.contact', 'write',
                        [[contact['id']], {'email': new_email}]
                    )

                self.results['mailing_contacts_cleaned'].append({
                    'contact_id': contact['id'],
                    'contact_name': contact['name'],
                    'email': email,
                    'old_email_field': current_email,
                    'new_email_field': new_email,
                    'reason': reason,
                    'conversation_id': conv_id,
                })

        except Exception as e:
            print(f"  -> ERROR cleaning mailing contacts: {e}")
            self.results['errors'].append({'email': email, 'model': 'mailing.contact', 'error': str(e)})

    # ---- TIER 2: FLAG (non-Representante) ---------------------------------

    def _flag_partner(self, partner, email, reason, reason_text, conv_id, tag_names,
                      flag_reason='non-representante'):
        """Flag a partner's bounce for review (temporary failure or non-Representante)."""
        tags_str = ', '.join(tag_names) if tag_names else '(sin etiquetas)'
        prefix = "[DRY_RUN] " if DRY_RUN else ""
        if flag_reason == 'temporary':
            detail = f"Temporary bounce ({reason}) - flagged for review"
        else:
            detail = "Not Representante - flagged for review"
        print(f"  -> {prefix}FLAG res.partner #{partner['id']} ({partner['name']}) [{tags_str}]")
        print(f"     {detail}")

        # Create bounce log record
        log_id = self._create_bounce_log_record(
            email, reason, reason_text, conv_id, 'flag',
            partner_id=partner['id'])

        # Accumulate Freescout update
        self._accumulate_freescout_update(
            conv_id, 'flag', email, reason,
            partner_id=partner['id'],
            partner_name=partner['name'],
            bounce_log_id=log_id)

        self.results['flagged'].append({
            'partner_id': partner['id'],
            'partner_name': partner['name'],
            'partner_email': partner.get('email', ''),
            'bounced_email': email,
            'reason': reason,
            'reason_text': reason_text[:200],
            'conversation_id': conv_id,
            'tags': tag_names,
            'source': 'res.partner',
            'flag_reason': flag_reason,
        })

    def _flag_mailing_contact_only(self, email, reason, reason_text, conv_id, contacts):
        """Flag a bounce found only in mailing.contact (no partner)."""
        prefix = "[DRY_RUN] " if DRY_RUN else ""
        for mc in contacts:
            emails_in_field = [e.strip().lower() for e in (mc.get('email') or '').split(';') if e.strip()]
            if email.lower() not in emails_in_field:
                continue
            print(f"  -> {prefix}FLAG mailing.contact #{mc['id']} ({mc['name']})")
            print(f"     No linked partner - flagged for review")

            # Create bounce log record
            log_id = self._create_bounce_log_record(
                email, reason, reason_text, conv_id, 'flag',
                mailing_contact_id=mc['id'])

            # Accumulate Freescout update
            self._accumulate_freescout_update(
                conv_id, 'flag', email, reason,
                partner_name=mc.get('name'),
                mailing_contact_id=mc['id'],
                bounce_log_id=log_id)

            self.results['flagged'].append({
                'partner_id': None,
                'partner_name': None,
                'partner_email': None,
                'bounced_email': email,
                'reason': reason,
                'reason_text': reason_text[:200],
                'conversation_id': conv_id,
                'tags': [],
                'source': f"mailing.contact #{mc['id']}",
            })

    # ---- TIER 3: NOT FOUND -----------------------------------------------

    def _handle_not_found(self, email, conv_id):
        print(f"  -> Not found in Odoo (neither res.partner nor mailing.contact)")

        # Create bounce log record (no partner/mailing contact link)
        log_id = self._create_bounce_log_record(
            email, 'other', '', conv_id, 'not_found')

        # Accumulate Freescout update
        self._accumulate_freescout_update(
            conv_id, 'not_found', email, 'other',
            bounce_log_id=log_id)

        self.results['not_found'].append({
            'email': email,
            'conversation_id': conv_id,
        })

    # ---- Email field manipulation -----------------------------------------

    @staticmethod
    def remove_bounced_email(email_field, bounced_email):
        """
        Remove the bounced email from a potentially multi-email field.
        Emails are separated by ';'. Case-insensitive matching.
        """
        if not email_field:
            return ''

        emails = [e.strip() for e in email_field.split(';') if e.strip()]
        remaining = [e for e in emails if e.lower() != bounced_email.lower()]

        return ';'.join(remaining)

    # ---- Chatter note -----------------------------------------------------

    def _post_chatter_note(self, model, record_id, bounced_email, reason,
                           reason_text, old_email, new_email, conv_id):
        """Post an internal note on the record's chatter for audit trail."""
        reason_labels = {
            'mailbox_full': 'Buzon lleno',
            'invalid_address': 'Direccion invalida',
            'domain_not_found': 'Dominio no encontrado',
            'rejected': 'Rechazado por servidor',
            'other': 'Otro',
        }

        now = datetime.now().strftime('%d/%m/%Y %H:%M')
        reason_label = reason_labels.get(reason, reason)
        detail = reason_text[:200] if reason_text else ''

        body = (
            f"<b>Email rebotado removido:</b> {bounced_email}<br/>"
            f"<b>Razon:</b> {reason_label} ({detail})<br/>"
            f"<b>Antes:</b> {old_email}<br/>"
            f"<b>Despues:</b> {new_email or '(vacio)'}<br/>"
            f"<b>Fuente:</b> Freescout Conversation #{conv_id}<br/>"
            f"<b>Fecha:</b> {now}"
        )

        try:
            self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'mail.message', 'create',
                [{
                    'body': body,
                    'message_type': 'comment',
                    'subtype_id': self._get_note_subtype_id(),
                    'model': model,
                    'res_id': record_id,
                }]
            )
        except Exception as e:
            print(f"     WARNING: Could not post chatter note: {e}")

    def _get_note_subtype_id(self):
        """Cache and return the ID of mail.mt_note subtype."""
        if not hasattr(self, '_note_subtype_id'):
            ids = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_PASSWORD,
                'ir.model.data', 'search_read',
                [[['module', '=', 'mail'], ['name', '=', 'mt_note']]],
                {'fields': ['res_id'], 'limit': 1}
            )
            self._note_subtype_id = ids[0]['res_id'] if ids else False
        return self._note_subtype_id

    # ---- Freescout post-processing (MySQL writes) -------------------------

    def _apply_freescout_postprocessing(self):
        """Apply accumulated updates to Freescout conversations via MySQL."""
        if not self.freescout_updates:
            return

        print("\n" + "-" * 70)
        print("FREESCOUT POST-PROCESSING")
        print("-" * 70)

        if TEST_MODE:
            print("TEST_MODE: Skipping Freescout post-processing (no real connection).")
            for conv_id, info in self.freescout_updates.items():
                print(f"  Would update conv #{conv_id}: "
                      f"subject={info['prefix']}..., status={'Active' if info['conv_status'] == 1 else 'Closed'}")
            return

        conn = self._connect_freescout()
        if not conn:
            print("ERROR: Cannot connect to Freescout for post-processing.")
            return

        reason_labels = {
            'mailbox_full': 'Buzon lleno',
            'invalid_address': 'Direccion invalida',
            'domain_not_found': 'Dominio no encontrado',
            'rejected': 'Rechazado por servidor',
            'other': 'Otro',
        }

        for conv_id, info in self.freescout_updates.items():
            prefix = "[DRY_RUN] " if DRY_RUN else ""
            try:
                with conn.cursor() as cursor:
                    # Read current subject
                    cursor.execute(
                        "SELECT subject FROM conversations WHERE id = %s",
                        (conv_id,))
                    row = cursor.fetchone()
                    if not row:
                        print(f"  {prefix}Conv #{conv_id}: NOT FOUND in Freescout, skipping")
                        continue

                    current_subject = row['subject'] or ''
                    tier_prefix = info['prefix']

                    # Skip if already prefixed
                    if current_subject.startswith('[LIMPIADO]') or \
                       current_subject.startswith('[REVISION]') or \
                       current_subject.startswith('[NO ENCONTRADO]'):
                        new_subject = current_subject
                    else:
                        new_subject = f"{tier_prefix} {current_subject}"

                    status_label = 'Active' if info['conv_status'] == 1 else 'Closed'
                    print(f"  {prefix}Conv #{conv_id}: subject=\"{new_subject[:60]}...\", "
                          f"status={status_label}, customer={info['bounced_email']}")

                    if DRY_RUN:
                        # Build note body for logging
                        note_body = self._build_freescout_note_html(info, reason_labels)
                        print(f"  {prefix}Would insert internal note on conv #{conv_id}")
                        self.results['freescout_updated'].append({
                            'conv_id': conv_id, 'tier': info['tier'],
                            'prefix': tier_prefix, 'dry_run': True,
                        })
                        continue

                    # UPDATE conversation: subject, customer_email, status
                    cursor.execute("""
                        UPDATE conversations
                        SET subject = %s,
                            customer_email = %s,
                            status = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (new_subject, info['bounced_email'],
                          info['conv_status'], conv_id))

                    # INSERT internal note thread
                    note_body = self._build_freescout_note_html(info, reason_labels)
                    cursor.execute("""
                        INSERT INTO threads
                            (conversation_id, type, body, state, status,
                             source_via, source_type,
                             created_by_user_id, user_id,
                             created_at, updated_at)
                        VALUES (%s, 3, %s, 2, 6, 2, 2, %s, %s, NOW(), NOW())
                    """, (conv_id, note_body,
                          self.freescout_admin_id, self.freescout_admin_id))

                    # Update threads_count
                    cursor.execute("""
                        UPDATE conversations
                        SET threads_count = threads_count + 1
                        WHERE id = %s
                    """, (conv_id,))

                conn.commit()
                print(f"  Conv #{conv_id}: Updated successfully")

                self.results['freescout_updated'].append({
                    'conv_id': conv_id, 'tier': info['tier'],
                    'prefix': tier_prefix, 'dry_run': False,
                })

            except Exception as e:
                print(f"  ERROR updating conv #{conv_id}: {e}")
                self.results['errors'].append({
                    'email': info['bounced_email'],
                    'model': 'freescout',
                    'error': str(e),
                })
                try:
                    conn.rollback()
                except Exception:
                    pass

        print(f"\nFreescout post-processing complete: "
              f"{len(self.results['freescout_updated'])} conversations updated.")

    def _build_freescout_note_html(self, info, reason_labels):
        """Build internal note HTML for a Freescout conversation."""
        reason_label = reason_labels.get(info['reason'], info['reason'])
        now = datetime.now().strftime('%d/%m/%Y %H:%M')

        # Odoo contact link
        odoo_contact_html = 'N/A'
        if info.get('partner_id'):
            odoo_url = (f"{ODOO_URL}/web#id={info['partner_id']}"
                        f"&model=res.partner&view_type=form")
            odoo_contact_html = (
                f'<a href="{odoo_url}">'
                f'{info.get("partner_name", "")} (#{info["partner_id"]})</a>')

        # Bounce log link
        bounce_log_html = 'N/A'
        if info.get('bounce_log_id'):
            bl_url = (f"{ODOO_URL}/web#id={info['bounce_log_id']}"
                      f"&model=mail.bounce.log&view_type=form")
            bounce_log_html = f'<a href="{bl_url}">Ver registro</a>'

        remaining = info.get('remaining_emails') or 'N/A'

        return (
            f"<b>Bounce Processor - Accion Automatica</b><br/>"
            f"<b>Email rebotado:</b> {info['bounced_email']}<br/>"
            f"<b>Razon:</b> {reason_label}<br/>"
            f"<b>Accion:</b> {info['action_desc']}<br/>"
            f"<b>Contacto Odoo:</b> {odoo_contact_html}<br/>"
            f"<b>Emails restantes:</b> {remaining}<br/>"
            f"<b>Bounce Log Odoo:</b> {bounce_log_html}<br/>"
            f"<b>Fecha:</b> {now}"
        )

    # ---- CSV log ----------------------------------------------------------

    def write_csv_log(self):
        os.makedirs(LOG_DIR, exist_ok=True)

        file_exists = os.path.exists(CSV_LOG_FILE)
        prefix = "[DRY_RUN] " if DRY_RUN else ""

        with open(CSV_LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow([
                    'date', 'bounced_email', 'partner_id', 'partner_name',
                    'mailing_contact_id', 'bounce_reason', 'freescout_conversation_id',
                    'action', 'tags', 'notes'
                ])

            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for item in self.results['partners_cleaned']:
                writer.writerow([
                    now, item['email'], item['partner_id'], item['partner_name'],
                    '', item['reason'], item['conversation_id'],
                    'cleaned', ';'.join(item.get('tags', [])),
                    f'{prefix}res.partner cleaned'
                ])

            for item in self.results['mailing_contacts_cleaned']:
                writer.writerow([
                    now, item['email'], '', '',
                    item['contact_id'], item['reason'], item['conversation_id'],
                    'cleaned', '',
                    f'{prefix}mailing.contact cleaned'
                ])

            for item in self.results['flagged']:
                writer.writerow([
                    now, item['bounced_email'], item.get('partner_id', ''),
                    item.get('partner_name', ''),
                    '', item['reason'], item['conversation_id'],
                    'flagged', ';'.join(item.get('tags', [])),
                    f'{prefix}Flagged for review ({item["source"]})'
                ])

            for item in self.results['not_found']:
                writer.writerow([
                    now, item['email'], '', '',
                    '', '', item['conversation_id'],
                    'not_found', '',
                    f'{prefix}Not found in Odoo'
                ])

        print(f"CSV log written to {CSV_LOG_FILE}")

    # ---- Report -----------------------------------------------------------

    def generate_report(self):
        partners = self.results['partners_cleaned']
        mailings = self.results['mailing_contacts_cleaned']
        flagged = self.results['flagged']
        not_found = self.results['not_found']
        errors = self.results['errors']

        print("\n" + "=" * 70)
        print("BOUNCE REPORT")
        print("=" * 70)

        if partners:
            print(f"\nCLEANED - Permanent failures, Representante ({len(partners)}):")
            for p in partners:
                tags = ', '.join(p.get('tags', []))
                multi = ' [MULTI]' if ';' in (p.get('old_email_field') or '') else ''
                print(f"  - {p['partner_name']} (#{p['partner_id']}): "
                      f"removed {p['email']} [{p['reason']}] ({tags}){multi}")

        if mailings:
            print(f"\nCLEANED - Mailing contacts ({len(mailings)}):")
            for m in mailings:
                print(f"  - {m['contact_name'] or '(sin nombre)'} (#{m['contact_id']}): "
                      f"removed {m['email']} [{m['reason']}]")

        if flagged:
            # Separate temporary Representante from non-Representante flags
            temp_flags = [f for f in flagged if f.get('flag_reason') == 'temporary']
            nonrep_flags = [f for f in flagged if f.get('flag_reason') != 'temporary']

            if temp_flags:
                print(f"\nFLAGGED - Temporary bounce, Representante ({len(temp_flags)}):")
                for fl in temp_flags:
                    tags = ', '.join(fl.get('tags', [])) or '(sin etiquetas)'
                    print(f"  - {fl['partner_name']} (#{fl['partner_id']}): "
                          f"{fl['bounced_email']} [{fl['reason']}] ({tags})")

            if nonrep_flags:
                print(f"\nFLAGGED - Non-Representante / mailing.contact only ({len(nonrep_flags)}):")
                for fl in nonrep_flags:
                    tags = ', '.join(fl.get('tags', [])) or '(sin etiquetas)'
                    name = fl.get('partner_name') or fl.get('source', '')
                    pid = fl.get('partner_id') or ''
                    pid_str = f" (#{pid})" if pid else ''
                    print(f"  - {name}{pid_str}: "
                          f"{fl['bounced_email']} [{fl['reason']}] ({tags})")

        if not_found:
            print(f"\nNOT FOUND in Odoo ({len(not_found)}):")
            for nf in not_found:
                print(f"  - {nf['email']} (Freescout #{nf['conversation_id']})")

        if errors:
            print(f"\nERRORS ({len(errors)}):")
            for err in errors:
                print(f"  - {err['email']} ({err['model']}): {err['error']}")

        # Bounce log records created
        bl_created = self.results['bounce_logs_created']
        if bl_created:
            print(f"\nBOUNCE LOG RECORDS ({len(bl_created)}):")
            for bl in bl_created:
                rid = bl.get('record_id') or '(dry-run)'
                print(f"  - {bl['bounced_email']} -> mail.bounce.log #{rid} [{bl['tier']}]")

        # Freescout post-processing
        fs_updated = self.results['freescout_updated']
        if fs_updated:
            print(f"\nFREESCOUT UPDATES ({len(fs_updated)}):")
            for fs in fs_updated:
                dr = " [DRY_RUN]" if fs.get('dry_run') else ""
                print(f"  - Conv #{fs['conv_id']}: {fs['prefix']} [{fs['tier']}]{dr}")

    # ---- Summary ----------------------------------------------------------

    def print_summary(self):
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        flagged = self.results['flagged']
        temp_count = sum(1 for f in flagged if f.get('flag_reason') == 'temporary')
        nonrep_count = len(flagged) - temp_count

        print(f"  Total bounces processed:     {len(self.results['processed'])}")
        print(f"  Skipped (already in Odoo):   {self.results['skipped_existing']}")
        print(f"  CLEANED (permanent + Representante):")
        print(f"    Partners cleaned:          {len(self.results['partners_cleaned'])}")
        print(f"    Mailing contacts cleaned:  {len(self.results['mailing_contacts_cleaned'])}")
        print(f"  FLAGGED (for review):        {len(flagged)}")
        print(f"    Temporary (Representante): {temp_count}")
        print(f"    Non-Representante/other:   {nonrep_count}")
        print(f"  NOT FOUND in Odoo:           {len(self.results['not_found'])}")
        print(f"  Bounce logs created:         {len(self.results['bounce_logs_created'])}")
        print(f"  Freescout convs updated:     {len(self.results['freescout_updated'])}")
        print(f"  Errors:                      {len(self.results['errors'])}")

        if DRY_RUN:
            print("\n" + "=" * 70)
            print("DRY RUN MODE - No changes were made to Odoo!")
            print("Set DRY_RUN = False to apply changes.")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("All changes applied successfully.")
            print("=" * 70)

        print("\nScript completed.")


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Daily Bounce Processor')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (apply real changes)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False

    processor = BounceProcessor()
    processor.run()
