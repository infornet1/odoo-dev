#!/usr/bin/env python3
"""
Sync WA phone numbers from Google Sheets → Odoo res.partner.mobile

Reads column L (WA phone) from the Customers sheet and updates Odoo
mobile field for any partner whose VAT matches sheet column A (Registration).

Rules:
  - Sheet col L is authoritative; only writes, never erases
  - Only updates partners where normalised value differs from current Odoo mobile
  - Stores with '+' prefix (Odoo convention)
  - If Odoo mobile contains an email address (data bug), replaces it
  - Never touches the Odoo 'phone' field
  - All sheet rows are considered (eligibility filter C/Q/R does NOT apply here)

Usage:
    python3 scripts/sync_wa_numbers_from_sheet.py           # dry run
    python3 scripts/sync_wa_numbers_from_sheet.py --live    # apply to production
    python3 scripts/sync_wa_numbers_from_sheet.py --live --partner-vat V14133887  # single partner
"""

import argparse
import json
import os
import re
import sys
import xmlrpc.client

import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# Config
# ============================================================================

SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE    = os.path.join(SCRIPT_DIR, '..', 'config', 'production.json')
SHEETS_CREDS   = os.path.join(SCRIPT_DIR, '..', 'config', 'google_sheets_credentials.json')
SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
SHEET_TAB      = 'Customers'

# ============================================================================
# Helpers
# ============================================================================

def load_odoo_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)['production']['xmlrpc']


def odoo_connect(cfg):
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    return cfg['db'], uid, cfg['api_key'], models


def normalise(raw):
    """Digits only, no spaces/dashes/plus."""
    return ''.join(c for c in str(raw or '') if c.isdigit())


def is_email(value):
    return bool(re.search(r'@', value or ''))


def format_phone(raw):
    """Return normalised number with leading '+'. Returns '' if no digits."""
    digits = normalise(raw)
    return f'+{digits}' if digits else ''


# ============================================================================
# Load data
# ============================================================================

def load_sheet_phones():
    """Return dict: vat_upper -> col_l_formatted ('+58...' or '')"""
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds  = Credentials.from_service_account_file(SHEETS_CREDS, scopes=scopes)
    gc     = gspread.authorize(creds)
    ws     = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_TAB)
    rows   = ws.get_all_values()[2:]   # skip title + header

    result = {}
    for row in rows:
        if len(row) < 12:
            continue
        vat   = row[0].strip().upper()
        col_l = row[11].strip()
        if not vat or not col_l:
            continue
        formatted = format_phone(col_l)
        if formatted:
            result[vat] = formatted
    return result


def load_odoo_partners(db, uid, pw, models, vat_filter=None):
    """Return dict: vat_upper -> {id, name, vat, mobile}"""
    domain = [('vat', '!=', False), ('active', '=', True)]
    if vat_filter:
        domain.append(('vat', 'in', vat_filter))

    partners = models.execute_kw(db, uid, pw, 'res.partner', 'search_read',
        [domain], {'fields': ['id', 'name', 'vat', 'mobile'], 'limit': 0})

    result = {}
    for p in partners:
        vat = (p.get('vat') or '').strip().upper()
        if vat:
            result[vat] = p
    return result


# ============================================================================
# Diff
# ============================================================================

def build_updates(odoo_partners, sheet_phones):
    """Return list of dicts describing each required update."""
    updates = []

    for vat, sheet_phone in sorted(sheet_phones.items()):
        p = odoo_partners.get(vat)
        if not p:
            continue   # VAT in sheet but not in Odoo — nothing to update

        current_mobile = (p.get('mobile') or '').strip()
        email_in_mobile = is_email(current_mobile)

        if email_in_mobile:
            # Data bug: email stored in mobile field
            reason = f'email in mobile → replace with sheet number'
            updates.append({
                'id':      p['id'],
                'name':    p['name'],
                'vat':     vat,
                'old':     current_mobile,
                'new':     sheet_phone,
                'reason':  reason,
            })
        elif normalise(current_mobile) == normalise(sheet_phone):
            # Already correct (format may differ, e.g. missing '+') — normalise if needed
            if current_mobile != sheet_phone:
                updates.append({
                    'id':     p['id'],
                    'name':   p['name'],
                    'vat':    vat,
                    'old':    current_mobile,
                    'new':    sheet_phone,
                    'reason': 'normalise format (same number, different format)',
                })
            # else: perfect match, skip
        elif not current_mobile:
            # Sheet only — Odoo mobile is empty
            updates.append({
                'id':     p['id'],
                'name':   p['name'],
                'vat':    vat,
                'old':    '—',
                'new':    sheet_phone,
                'reason': 'SHEET_ONLY — add missing mobile',
            })
        else:
            # Mismatch — different numbers; sheet wins
            updates.append({
                'id':     p['id'],
                'name':   p['name'],
                'vat':    vat,
                'old':    current_mobile,
                'new':    sheet_phone,
                'reason': 'MISMATCH — sheet value replaces Odoo',
            })

    return updates


# ============================================================================
# Apply
# ============================================================================

def apply_updates(db, uid, pw, models, updates, dry_run):
    ok = skipped = errors = 0

    for u in updates:
        if dry_run:
            ok += 1
            continue
        try:
            models.execute_kw(db, uid, pw, 'res.partner', 'write',
                [[u['id']], {'mobile': u['new']}])
            ok += 1
        except Exception as e:
            print(f"  ERROR  {u['name']} ({u['vat']}): {e}")
            errors += 1

    return ok, skipped, errors


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Sync WA numbers: Sheets → Odoo mobile')
    parser.add_argument('--live', action='store_true',
                        help='Apply changes to production (default: dry run)')
    parser.add_argument('--partner-vat', metavar='VAT',
                        help='Limit to a single partner VAT for testing')
    args = parser.parse_args()

    dry_run = not args.live

    print("=" * 80)
    print(f"  SYNC WA NUMBERS — Google Sheets col L → Odoo res.partner.mobile")
    print(f"  Mode: {'*** DRY RUN — no changes written ***' if dry_run else '*** LIVE — writing to DB_UEIPAB ***'}")
    print("=" * 80)

    print("\n[1/3] Loading Google Sheets...")
    sheet_phones = load_sheet_phones()
    print(f"      {len(sheet_phones)} rows with phone in col L")

    if args.partner_vat:
        vat_filter_upper = args.partner_vat.strip().upper()
        sheet_phones = {k: v for k, v in sheet_phones.items() if k == vat_filter_upper}
        vat_filter_list = list(sheet_phones.keys())
        print(f"      Filtered to VAT={args.partner_vat}")
    else:
        vat_filter_list = None

    print("\n[2/3] Loading Odoo partners...")
    cfg = load_odoo_config()
    db, uid, pw, models = odoo_connect(cfg)
    odoo_partners = load_odoo_partners(db, uid, pw, models, vat_filter=vat_filter_list)
    print(f"      {len(odoo_partners)} partners loaded from Odoo")

    vats_in_sheet_not_odoo = set(sheet_phones) - set(odoo_partners)
    if vats_in_sheet_not_odoo:
        print(f"      {len(vats_in_sheet_not_odoo)} sheet VATs not found in Odoo (ignored)")

    print("\n[3/3] Building update list...")
    updates = build_updates(odoo_partners, sheet_phones)

    # Group by reason for display
    by_reason = {}
    for u in updates:
        key = u['reason'].split(' — ')[0] if ' — ' in u['reason'] else u['reason']
        by_reason.setdefault(key, []).append(u)

    if not updates:
        print("\n  Nothing to update — all matched partners already in sync.")
        return

    print(f"\n  {len(updates)} partners will be updated:\n")
    print(f"  {'Name':<42} {'VAT':<14} {'Old mobile':<26} {'New mobile':<18} Reason")
    print("  " + "-" * 110)
    for u in sorted(updates, key=lambda x: x['name']):
        old = u['old'] if len(u['old']) <= 25 else u['old'][:22] + '...'
        print(f"  {u['name']:<42} {u['vat']:<14} {old:<26} {u['new']:<18} {u['reason']}")

    print(f"\n  Summary by type:")
    for reason_key, group in sorted(by_reason.items()):
        print(f"    {reason_key:<45} {len(group):>3}")
    print(f"    {'TOTAL':<45} {len(updates):>3}")

    if dry_run:
        print("\n  Dry run complete. Run with --live to apply.")
        return

    print(f"\n  Applying {len(updates)} updates to DB_UEIPAB...")
    ok, _, errors = apply_updates(db, uid, pw, models, updates, dry_run=False)

    print(f"\n  Done — {ok} updated, {errors} errors.")
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
