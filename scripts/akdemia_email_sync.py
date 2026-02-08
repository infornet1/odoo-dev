#!/usr/bin/env python3
"""
Akdemia Email Sync Pipeline

Detects email changes in Akdemia student management system and auto-resolves
active AI agent conversations and bounce logs in Odoo.

Phases:
  1. Get XLS data (--file, auto-download, or latest from downloads dir)
  2. Parse XLS → parent email map (by cedula)
  3. Compare with Odoo unresolved bounce logs (XML-RPC)
  4. Auto-resolve detected changes (bounce log + AI conversation)
  5. Update Akdemia2526 Google Sheet tab with fresh data

Safety: DRY_RUN=True by default. TARGET_ENV=testing by default.

Usage:
    python3 /opt/odoo-dev/scripts/akdemia_email_sync.py
    python3 /opt/odoo-dev/scripts/akdemia_email_sync.py --file /path/to/lista.xls
    python3 /opt/odoo-dev/scripts/akdemia_email_sync.py --skip-sheets

Author: Claude Code Assistant
Date: 2026-02-08
"""

import argparse
import glob
import json
import os
import re
import sys
import xmlrpc.client
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True
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
        'password': 'f69330e5bd6ae043320f054e9df9fcbbb34522db',
    },
}

ODOO_URL = ODOO_CONFIGS[TARGET_ENV]['url']
ODOO_DB = ODOO_CONFIGS[TARGET_ENV]['db']
ODOO_USER = ODOO_CONFIGS[TARGET_ENV]['user']
ODOO_PASSWORD = ODOO_CONFIGS[TARGET_ENV]['password']

# Akdemia downloads directory
AKDEMIA_DOWNLOADS_DIR = '/var/www/dev/odoo_api_bridge/akdemia_downloads'
AKDEMIA_HISTORICAL_DIR = '/var/www/dev/odoo_api_bridge/customer_matching/data/xls_uploads'

# Google Sheets
SHEETS_CREDENTIALS = '/opt/odoo-dev/config/google_sheets_credentials.json'
SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
AKDEMIA_TAB = 'Akdemia2526'

# Protected emails — must NEVER be modified by any sync operation
PROTECTED_EMAILS = {'todalacomunidad@ueipab.edu.ve'}

# XLS column names (header row 2 = index 2)
# Parent 1 (Representante)
P1_NAME = 'Nombre de Representante'
P1_SURNAME = 'Apellido de Representante'
P1_CEDULA = 'Cédula de identidad de Representante'
P1_EMAIL = 'Correo electrónico de Representante'
P1_PHONE = 'Teléfono celular de Representante'

# Parent 2 (Representante.1)
P2_NAME = 'Nombre de Representante.1'
P2_SURNAME = 'Apellido de Representante.1'
P2_CEDULA = 'Cédula de identidad de Representante.1'
P2_EMAIL = 'Correo electrónico de Representante.1'
P2_PHONE = 'Teléfono celular de Representante.1'

# Parent 3 (Representante.2)
P3_NAME = 'Nombre de Representante.2'
P3_SURNAME = 'Apellido de Representante.2'
P3_CEDULA = 'Cédula de identidad de Representante.2'
P3_EMAIL = 'Correo electrónico de Representante.2'
P3_PHONE = 'Teléfono celular de Representante.2'


# ============================================================================
# Utilities
# ============================================================================

def normalize_cedula(cedula):
    """V-12222702888 → 12222702888, V19964384 → 19964384, nan → ''"""
    if not cedula or str(cedula).lower() == 'nan':
        return ''
    return re.sub(r'[^0-9]', '', str(cedula))


def normalize_email(email):
    """Lowercase and strip, return '' for empty/nan."""
    if not email or str(email).lower() == 'nan':
        return ''
    return str(email).strip().lower()


def print_separator(char='=', length=70):
    print(char * length)


def print_header(title):
    print()
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


# ============================================================================
# Phase 1: Get XLS File
# ============================================================================

def get_xls_file(file_arg=None):
    """Get XLS file path: from --file arg, or latest from downloads dir."""
    if file_arg:
        if not os.path.exists(file_arg):
            print(f"ERROR: File not found: {file_arg}")
            sys.exit(1)
        print(f"Using provided file: {file_arg}")
        return file_arg

    # Try downloads directory first
    xls_files = glob.glob(os.path.join(AKDEMIA_DOWNLOADS_DIR, '*.xls'))
    if not xls_files:
        # Fall back to historical directory
        xls_files = glob.glob(os.path.join(AKDEMIA_HISTORICAL_DIR, '**/*.xls'), recursive=True)

    if not xls_files:
        print("ERROR: No XLS files found in downloads or historical directories.")
        print(f"  Downloads: {AKDEMIA_DOWNLOADS_DIR}")
        print(f"  Historical: {AKDEMIA_HISTORICAL_DIR}")
        print("  Use --file /path/to/file.xls to specify manually.")
        sys.exit(1)

    latest = max(xls_files, key=os.path.getmtime)
    mtime = datetime.fromtimestamp(os.path.getmtime(latest)).strftime('%Y-%m-%d %H:%M')
    print(f"Using latest XLS: {latest}")
    print(f"  Modified: {mtime}")
    return latest


# ============================================================================
# Phase 2: Parse XLS → Parent Email Map
# ============================================================================

def parse_xls(filepath):
    """Parse XLS file into a parent map: {normalized_cedula: {emails, name, phone}}"""
    import pandas as pd

    print(f"\nParsing XLS: {os.path.basename(filepath)}")
    df = pd.read_excel(filepath, header=2)
    print(f"  Rows: {len(df)}, Columns: {len(df.columns)}")

    # Also read raw metadata rows for sheet update
    df_raw = pd.read_excel(filepath, header=None)

    parent_map = {}  # {cedula: {emails: set, name: str, phone: str}}
    parent_sets = [
        (P1_NAME, P1_SURNAME, P1_CEDULA, P1_EMAIL, P1_PHONE),
        (P2_NAME, P2_SURNAME, P2_CEDULA, P2_EMAIL, P2_PHONE),
        (P3_NAME, P3_SURNAME, P3_CEDULA, P3_EMAIL, P3_PHONE),
    ]

    for name_col, surname_col, cedula_col, email_col, phone_col in parent_sets:
        if cedula_col not in df.columns:
            continue

        for _, row in df.iterrows():
            cedula = normalize_cedula(row.get(cedula_col))
            if not cedula:
                continue

            email = normalize_email(row.get(email_col))
            name_val = str(row.get(name_col, '') or '').strip()
            surname_val = str(row.get(surname_col, '') or '').strip()
            # Clean 'nan' strings
            if name_val.lower() == 'nan':
                name_val = ''
            if surname_val.lower() == 'nan':
                surname_val = ''
            full_name = f"{name_val} {surname_val}".strip()

            phone_val = str(row.get(phone_col, '') or '').strip()
            if phone_val.lower() == 'nan':
                phone_val = ''

            if cedula not in parent_map:
                parent_map[cedula] = {
                    'emails': set(),
                    'name': full_name,
                    'phone': phone_val,
                }

            if email:
                parent_map[cedula]['emails'].add(email)

            # Keep best name/phone (non-empty overrides empty)
            if full_name and not parent_map[cedula]['name']:
                parent_map[cedula]['name'] = full_name
            if phone_val and not parent_map[cedula]['phone']:
                parent_map[cedula]['phone'] = phone_val

    # Stats
    with_email = sum(1 for v in parent_map.values() if v['emails'])
    total_emails = sum(len(v['emails']) for v in parent_map.values())
    print(f"  Parents parsed: {len(parent_map)}")
    print(f"  Parents with email: {with_email}")
    print(f"  Total unique emails: {total_emails}")

    return parent_map, df, df_raw


# ============================================================================
# Phase 3: Compare with Odoo Bounce Logs
# ============================================================================

def connect_odoo():
    """Establish XML-RPC connection to Odoo."""
    print(f"\nConnecting to Odoo: {ODOO_URL} (db={ODOO_DB})...")
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            print("ERROR: Odoo authentication failed.")
            return None, None
        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
        print(f"  Connected as uid={uid}")
        return uid, models
    except Exception as e:
        print(f"ERROR connecting to Odoo: {e}")
        return None, None


def search_read(models, uid, model, domain, fields):
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        [domain], {'fields': fields}
    )


def find_email_changes(models, uid, parent_map):
    """Compare unresolved bounce logs against Akdemia parent map.

    Returns list of dicts: {bounce_log_id, partner_id, bounced_email,
                            akdemia_new_email, partner_vat, partner_name}
    """
    print_header("Phase 3: Compare Bounce Logs with Akdemia Data")

    # Get all unresolved bounce logs that have a partner linked
    bounce_logs = search_read(models, uid, 'mail.bounce.log',
                              [('state', '!=', 'resolved'), ('partner_id', '!=', False)],
                              ['id', 'bounced_email', 'partner_id', 'state', 'new_email'])

    if not bounce_logs:
        print("  No unresolved bounce logs with linked partners found.")
        return []

    print(f"  Unresolved bounce logs with partners: {len(bounce_logs)}")

    # Get all partner IDs to fetch VAT in bulk
    partner_ids = list(set(bl['partner_id'][0] for bl in bounce_logs))
    partners = search_read(models, uid, 'res.partner',
                           [('id', 'in', partner_ids)],
                           ['id', 'name', 'vat', 'email'])
    partner_lookup = {p['id']: p for p in partners}

    changes = []
    for bl in bounce_logs:
        partner_id = bl['partner_id'][0]
        partner = partner_lookup.get(partner_id)
        if not partner:
            continue

        partner_vat = normalize_cedula(partner.get('vat'))
        if not partner_vat:
            continue

        akdemia_entry = parent_map.get(partner_vat)
        if not akdemia_entry:
            continue

        bounced_email = normalize_email(bl['bounced_email'])
        akdemia_emails = akdemia_entry['emails']

        if not akdemia_emails:
            continue

        # Check if Akdemia has an email that is DIFFERENT from the bounced one
        new_emails = akdemia_emails - {bounced_email}
        if not new_emails:
            # All Akdemia emails match the bounced email — no change
            continue

        # Pick the first new email (most likely the updated one)
        akdemia_new_email = sorted(new_emails)[0]

        changes.append({
            'bounce_log_id': bl['id'],
            'bounce_log_state': bl['state'],
            'partner_id': partner_id,
            'partner_name': partner.get('name', ''),
            'partner_vat': partner_vat,
            'bounced_email': bounced_email,
            'akdemia_new_email': akdemia_new_email,
            'akdemia_all_emails': sorted(akdemia_emails),
        })

    print(f"  Email changes detected: {len(changes)}")
    for ch in changes:
        print(f"    BL#{ch['bounce_log_id']} {ch['partner_name']} (V-{ch['partner_vat']}): "
              f"{ch['bounced_email']} → {ch['akdemia_new_email']}")
        if len(ch['akdemia_all_emails']) > 1:
            print(f"      All Akdemia emails: {', '.join(ch['akdemia_all_emails'])}")

    return changes


# ============================================================================
# Phase 4: Auto-Resolve Changes
# ============================================================================

def _remove_bounced_email(email_field, bounced_email):
    """Remove a specific email from a ;-separated field."""
    if not email_field:
        return ''
    emails = [e.strip() for e in email_field.split(';') if e.strip()]
    remaining = [e for e in emails if e.lower() != bounced_email.strip().lower()]
    return ';'.join(remaining)


def _append_email(email_field, new_email):
    """Append email to ;-separated field, avoiding duplicates."""
    current = (email_field or '').strip()
    if not current:
        return new_email.strip()
    emails = [e.strip() for e in current.split(';') if e.strip()]
    if new_email.strip().lower() not in [e.lower() for e in emails]:
        emails.append(new_email.strip())
    return ';'.join(emails)


def sync_mailing_contacts(models, uid, bounced_email, new_email):
    """Find and update mailing.contact records that have the bounced email.

    Replaces the bounced email with the new email in each matching contact.
    Skips protected institutional emails.
    Returns number of contacts updated.
    """
    if not bounced_email or bounced_email.strip().lower() in PROTECTED_EMAILS:
        return 0

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    try:
        mc_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'mailing.contact', 'search',
            [[('email', 'ilike', bounced_email)]]
        )
        if not mc_ids:
            return 0

        mc_records = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'mailing.contact', 'read',
            [mc_ids],
            {'fields': ['id', 'name', 'email']}
        )

        updated = 0
        for mc in mc_records:
            # Skip protected emails
            if mc.get('email') and mc['email'].strip().lower() in PROTECTED_EMAILS:
                continue

            # Verify the bounced email actually appears
            mc_emails = [e.strip().lower() for e in (mc.get('email') or '').split(';') if e.strip()]
            if bounced_email.strip().lower() not in mc_emails:
                continue

            # Replace bounced → new
            updated_field = _remove_bounced_email(mc['email'], bounced_email)
            updated_field = _append_email(updated_field, new_email)

            print(f"  {prefix}Updating mailing.contact #{mc['id']} ({mc.get('name', '')}): "
                  f"'{mc['email']}' → '{updated_field}'")

            if not DRY_RUN:
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mailing.contact', 'write',
                    [[mc['id']], {'email': updated_field}]
                )
            updated += 1

        return updated

    except Exception as e:
        print(f"  WARNING: Error syncing mailing contacts: {e}")
        return 0


def apply_changes(models, uid, changes):
    """Apply detected email changes to Odoo bounce logs, conversations, and mailing contacts."""
    print_header("Phase 4: Auto-Resolve Detected Changes")

    if not changes:
        print("  No changes to apply.")
        return

    results = {'resolved_bls': 0, 'resolved_convs': 0, 'updated_mcs': 0, 'errors': 0}

    for ch in changes:
        bl_id = ch['bounce_log_id']
        new_email = ch['akdemia_new_email']
        bounced_email = ch['bounced_email']
        prefix = "[DRY_RUN] " if DRY_RUN else ""

        print(f"--- BL#{bl_id} ({ch['partner_name']}) ---")
        print(f"  {prefix}Setting new_email='{new_email}' on bounce log")

        if not DRY_RUN:
            try:
                # Step 1: Set new_email on bounce log
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.bounce.log', 'write',
                    [[bl_id], {'new_email': new_email}]
                )

                # Step 2: Trigger action_apply_new_email
                # (appends email to partner + updates mailing.contact via module + sets resolved)
                models.execute_kw(
                    ODOO_DB, uid, ODOO_PASSWORD,
                    'mail.bounce.log', 'action_apply_new_email',
                    [[bl_id]]
                )
                print(f"  Bounce log #{bl_id} resolved with new email: {new_email}")
                results['resolved_bls'] += 1
            except Exception as e:
                print(f"  ERROR resolving bounce log #{bl_id}: {e}")
                results['errors'] += 1
                # Even if module resolution fails, try mailing contact sync directly
                mc_count = sync_mailing_contacts(models, uid, bounced_email, new_email)
                results['updated_mcs'] += mc_count
                continue
        else:
            print(f"  {prefix}Would call action_apply_new_email on BL#{bl_id}")
            results['resolved_bls'] += 1

        # Step 3: Sync mailing contacts (belt-and-suspenders — module may handle this,
        # but script also does it for environments where module is not installed yet)
        mc_count = sync_mailing_contacts(models, uid, bounced_email, new_email)
        results['updated_mcs'] += mc_count

        # Step 4: Find and resolve linked AI agent conversation
        print(f"  {prefix}Checking for linked AI conversation...")
        try:
            convs = search_read(models, uid, 'ai.agent.conversation',
                                [('source_model', '=', 'mail.bounce.log'),
                                 ('source_id', '=', bl_id),
                                 ('state', 'not in', ['resolved', 'failed'])],
                                ['id', 'state'])
            if convs:
                conv_id = convs[0]['id']
                print(f"  {prefix}Resolving AI conversation #{conv_id} (state={convs[0]['state']})")
                if not DRY_RUN:
                    models.execute_kw(
                        ODOO_DB, uid, ODOO_PASSWORD,
                        'ai.agent.conversation', 'action_resolve',
                        [[conv_id]],
                        {'summary': f'Email actualizado en Akdemia: {new_email}',
                         'resolution_data': {'action': 'new_email', 'email': new_email}}
                    )
                    print(f"  AI conversation #{conv_id} resolved.")
                results['resolved_convs'] += 1
            else:
                print(f"  No active AI conversation found for BL#{bl_id}")
        except Exception as e:
            print(f"  WARNING: Error checking AI conversations: {e}")

        print()

    print(f"  Results: {results['resolved_bls']} bounce logs, "
          f"{results['resolved_convs']} conversations resolved, "
          f"{results['updated_mcs']} mailing contacts updated, "
          f"{results['errors']} errors")

    return results


# ============================================================================
# Phase 5: Update Akdemia2526 Google Sheet
# ============================================================================

def update_google_sheet(df, df_raw):
    """Update Akdemia2526 tab with fresh data from XLS."""
    print_header("Phase 5: Update Akdemia2526 Google Sheet")

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        print("  Install with: pip install gspread google-auth")
        return

    if not os.path.exists(SHEETS_CREDENTIALS):
        print(f"ERROR: Google Sheets credentials not found: {SHEETS_CREDENTIALS}")
        return

    prefix = "[DRY_RUN] " if DRY_RUN else ""

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_file(SHEETS_CREDENTIALS, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(AKDEMIA_TAB)
    except gspread.exceptions.WorksheetNotFound:
        print(f"  {prefix}Tab '{AKDEMIA_TAB}' not found, creating it...")
        if not DRY_RUN:
            worksheet = spreadsheet.add_worksheet(
                title=AKDEMIA_TAB, rows=str(len(df_raw) + 10), cols=str(len(df_raw.columns) + 5))
        else:
            print(f"  {prefix}Would create tab '{AKDEMIA_TAB}'")
            return

    # Build all_rows: metadata rows + headers + data (from raw df)
    all_rows = []
    for i, row in df_raw.iterrows():
        row_data = []
        for val in row:
            if str(val).lower() == 'nan' or val != val:  # NaN check
                row_data.append('')
            elif isinstance(val, float) and val == int(val):
                row_data.append(str(int(val)))
            else:
                row_data.append(str(val))
        all_rows.append(row_data)

    total_rows = len(all_rows)
    total_cols = max(len(r) for r in all_rows) if all_rows else 0
    print(f"  Data: {total_rows} rows x {total_cols} cols")
    print(f"  Metadata rows: 2 (school name + year)")
    print(f"  Header row: 1")
    print(f"  Data rows: {total_rows - 3}")

    if DRY_RUN:
        print(f"  {prefix}Would clear tab '{AKDEMIA_TAB}' and write {total_rows} rows")
        print(f"  {prefix}Sample row 3: {all_rows[3][:5]}..." if len(all_rows) > 3 else "")
        return

    # Clear and write
    worksheet.clear()

    # Resize if needed
    if worksheet.row_count < total_rows:
        worksheet.resize(rows=total_rows + 5)
    if worksheet.col_count < total_cols:
        worksheet.resize(cols=total_cols + 2)

    # Batch update (gspread rate limits: 60 req/min)
    # Write in chunks to avoid payload size limits
    chunk_size = 100
    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        chunk = all_rows[start:end]
        cell_range = f'A{start + 1}'
        worksheet.update(cell_range, chunk, value_input_option='USER_ENTERED')
        if end < total_rows:
            print(f"  Written rows {start + 1}-{end} of {total_rows}...")

    print(f"  Akdemia2526 tab updated: {total_rows} rows written.")
    print(f"  Sheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Akdemia Email Sync Pipeline')
    parser.add_argument('--file', help='Path to Akdemia XLS file (skip auto-detect)')
    parser.add_argument('--skip-sheets', action='store_true',
                        help='Skip Google Sheets update (Phase 5)')
    parser.add_argument('--skip-odoo', action='store_true',
                        help='Skip Odoo comparison and resolution (Phases 3-4)')
    parser.add_argument('--live', action='store_true',
                        help='Disable DRY_RUN (apply real changes)')
    args = parser.parse_args()

    global DRY_RUN
    if args.live:
        DRY_RUN = False

    print_separator()
    print("  AKDEMIA EMAIL SYNC PIPELINE")
    print_separator()
    print(f"  Date:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN:    {DRY_RUN}")
    print(f"  Target:     {TARGET_ENV}")
    print(f"  Odoo:       {ODOO_URL} / {ODOO_DB}")
    print(f"  Skip Sheets: {args.skip_sheets}")
    print(f"  Skip Odoo:   {args.skip_odoo}")
    print()

    # Phase 1: Get XLS file
    print_header("Phase 1: Get XLS File")
    xls_path = get_xls_file(args.file)

    # Phase 2: Parse XLS
    print_header("Phase 2: Parse XLS → Parent Email Map")
    parent_map, df, df_raw = parse_xls(xls_path)

    if not parent_map:
        print("ERROR: No parent data found in XLS. Aborting.")
        sys.exit(1)

    # Phase 3-4: Odoo comparison and resolution
    if not args.skip_odoo:
        uid, models = connect_odoo()
        if uid and models:
            changes = find_email_changes(models, uid, parent_map)
            apply_changes(models, uid, changes)
        else:
            print("WARNING: Skipping Odoo phases due to connection failure.")
    else:
        print("\n  Skipping Odoo phases (--skip-odoo).")

    # Phase 5: Google Sheets update
    if not args.skip_sheets:
        update_google_sheet(df, df_raw)
    else:
        print("\n  Skipping Google Sheets update (--skip-sheets).")

    # Summary
    print_header("COMPLETE")
    if DRY_RUN:
        print("  DRY RUN — No changes were made.")
        print("  Use --live to apply changes.")
    else:
        print("  All changes applied.")
    print()


if __name__ == '__main__':
    main()
