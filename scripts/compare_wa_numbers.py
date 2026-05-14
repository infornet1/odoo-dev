#!/usr/bin/env python3
"""
Phase 0 — WA Number Audit: Odoo Production vs Google Sheets

Compares WA phone numbers for Representante (tag 25) and Representante PDVSA (tag 26)
partners between production Odoo and the Google Sheets Customers tab (column L).

Read-only. No writes to Odoo, no WA sends, no sheet modifications.

Sheet eligibility filter applied before comparison:
  - Column C (Status)      in {ACTIVE, PENDING}
  - Column Q (Notify_SMS)  = YES
  - Column R (Notify_Email)= YES

Status codes in output:
  MATCH            Odoo mobile matches Sheet col L (after normalisation)
  MISMATCH         Both have numbers but they differ
  ODOO_ONLY        Odoo has a number, Sheet col L empty
  SHEET_ONLY       Sheet has a number, Odoo mobile/phone empty
  BOTH_EMPTY       No phone in either source
  NOT_IN_SHEET     Partner VAT not found in sheet at all
  SKIP_NOT_ELIGIBLE Found in sheet but C/Q/R filter not met

Usage:
    python3 scripts/compare_wa_numbers.py           # production (default)
    python3 scripts/compare_wa_numbers.py --csv     # also write results.csv
"""

import argparse
import csv
import json
import os
import sys
import xmlrpc.client
from collections import defaultdict

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

TAG_REPRESENTANTE      = 25
TAG_REPRESENTANTE_PDVSA = 26
TAG_NAMES = {
    TAG_REPRESENTANTE:       'Representante',
    TAG_REPRESENTANTE_PDVSA: 'Representante PDVSA',
}

# ============================================================================
# Helpers
# ============================================================================

def load_odoo_config():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    return cfg['production']['xmlrpc']


def normalise_phone(raw):
    """Strip spaces, dashes, parentheses; ensure string."""
    if not raw:
        return ''
    return ''.join(c for c in str(raw) if c.isdigit())


def odoo_connect(cfg):
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    return cfg['db'], uid, cfg['api_key'], models


def search_read(db, uid, pw, models, model, domain, fields):
    return models.execute_kw(db, uid, pw, model, 'search_read',
                             [domain], {'fields': fields, 'limit': 0})


# ============================================================================
# Step 1 — Load Odoo partners
# ============================================================================

def load_odoo_partners(db, uid, pw, models):
    """Return dict: vat -> {id, name, vat, mobile, phone, tags}"""
    partners = search_read(db, uid, pw, models, 'res.partner',
        [('category_id', 'in', [TAG_REPRESENTANTE, TAG_REPRESENTANTE_PDVSA]),
         ('active', '=', True)],
        ['id', 'name', 'vat', 'mobile', 'phone', 'category_id'])

    result = {}
    for p in partners:
        vat = (p.get('vat') or '').strip().upper()
        if not vat:
            continue
        tag_ids = p.get('category_id') or []
        tags = [TAG_NAMES[t] for t in tag_ids if t in TAG_NAMES]
        result[vat] = {
            'id':     p['id'],
            'name':   p['name'],
            'vat':    vat,
            'mobile': (p.get('mobile') or '').strip(),
            'phone':  (p.get('phone') or '').strip(),
            'tags':   ', '.join(sorted(tags)),
        }
    return result


# ============================================================================
# Step 2 — Load Google Sheets eligible rows
# ============================================================================

def load_sheet_rows():
    """Return two dicts keyed by VAT (col A, uppercase):
       eligible   -> {vat, name, status, col_l_raw}
       ineligible -> {vat, name, status, col_q, col_r}   (failed C/Q/R filter)
    """
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(SHEETS_CREDS, scopes=scopes)
    gc    = gspread.authorize(creds)
    ws    = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_TAB)
    rows  = ws.get_all_values()[2:]   # skip title row + header row

    eligible   = {}
    ineligible = {}

    for row in rows:
        if len(row) < 12:
            continue
        vat    = row[0].strip().upper()
        name   = row[1].strip()
        status = row[2].strip().upper()
        col_l  = row[11].strip()                              # WA phone
        col_q  = row[16].strip().upper() if len(row) > 16 else ''  # Notify_SMS
        col_r  = row[17].strip().upper() if len(row) > 17 else ''  # Notify_Email

        if not vat:
            continue

        if status in ('ACTIVE', 'PENDING') and col_q == 'YES' and col_r == 'YES':
            eligible[vat] = {
                'vat':      vat,
                'name':     name,
                'status':   status,
                'col_l':    col_l,
            }
        else:
            ineligible[vat] = {
                'vat':    vat,
                'name':   name,
                'status': status,
                'col_q':  col_q,
                'col_r':  col_r,
            }

    return eligible, ineligible


# ============================================================================
# Step 3 — Diff
# ============================================================================

def build_report(odoo_partners, sheet_eligible, sheet_ineligible):
    rows = []

    for vat, op in sorted(odoo_partners.items(), key=lambda x: x[1]['name']):
        odoo_mobile = op['mobile']
        odoo_phone  = op['phone']
        odoo_any    = odoo_mobile or odoo_phone

        if vat in sheet_eligible:
            se       = sheet_eligible[vat]
            sheet_l  = se['col_l']
            norm_odoo   = normalise_phone(odoo_mobile or odoo_phone)
            norm_sheet  = normalise_phone(sheet_l)

            if norm_odoo and norm_sheet:
                status = 'MATCH' if norm_odoo == norm_sheet else 'MISMATCH'
            elif norm_odoo and not norm_sheet:
                status = 'ODOO_ONLY'
            elif not norm_odoo and norm_sheet:
                status = 'SHEET_ONLY'
            else:
                status = 'BOTH_EMPTY'

        elif vat in sheet_ineligible:
            si      = sheet_ineligible[vat]
            sheet_l = ''
            status  = 'SKIP_NOT_ELIGIBLE'

        else:
            sheet_l = ''
            status  = 'NOT_IN_SHEET'

        rows.append({
            'status':       status,
            'name':         op['name'],
            'vat':          vat,
            'tags':         op['tags'],
            'odoo_mobile':  odoo_mobile,
            'odoo_phone':   odoo_phone,
            'sheet_col_l':  sheet_l,
        })

    return rows


# ============================================================================
# Output
# ============================================================================

STATUS_ORDER = ['MATCH', 'MISMATCH', 'SHEET_ONLY', 'ODOO_ONLY',
                'BOTH_EMPTY', 'NOT_IN_SHEET', 'SKIP_NOT_ELIGIBLE']

STATUS_LABELS = {
    'MATCH':             '✓  MATCH',
    'MISMATCH':          '⚠  MISMATCH',
    'SHEET_ONLY':        '←  SHEET_ONLY',
    'ODOO_ONLY':         '→  ODOO_ONLY',
    'BOTH_EMPTY':        '✗  BOTH_EMPTY',
    'NOT_IN_SHEET':      '?  NOT_IN_SHEET',
    'SKIP_NOT_ELIGIBLE': '-  SKIP_NOT_ELIGIBLE',
}


def print_report(rows):
    by_status = defaultdict(list)
    for r in rows:
        by_status[r['status']].append(r)

    print()
    print("=" * 90)
    print("  WA NUMBER AUDIT — Odoo Production vs Google Sheets Customers (col L)")
    print("=" * 90)

    for status in STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue
        print(f"\n── {STATUS_LABELS[status]} ({len(group)}) " + "─" * 40)
        for r in sorted(group, key=lambda x: x['name']):
            odoo_num   = r['odoo_mobile'] or r['odoo_phone'] or '—'
            sheet_num  = r['sheet_col_l'] or '—'
            tag_short  = 'PDVSA' if 'PDVSA' in r['tags'] else 'REP'
            if status in ('MATCH', 'SHEET_ONLY', 'BOTH_EMPTY', 'NOT_IN_SHEET', 'SKIP_NOT_ELIGIBLE'):
                print(f"  [{tag_short}] {r['name']:<40} {r['vat']:<12}  sheet={sheet_num}")
            else:
                print(f"  [{tag_short}] {r['name']:<40} {r['vat']:<12}  odoo={odoo_num}  sheet={sheet_num}")

    print()
    print("── SUMMARY " + "─" * 60)
    total = len(rows)
    for status in STATUS_ORDER:
        n = len(by_status.get(status, []))
        if n:
            bar = '█' * n
            print(f"  {STATUS_LABELS[status]:<30} {n:>4}  {bar}")
    print(f"  {'TOTAL':<30} {total:>4}")
    print()


def write_csv(rows, path):
    fieldnames = ['status', 'name', 'vat', 'tags', 'odoo_mobile', 'odoo_phone', 'sheet_col_l']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"CSV written → {path}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Audit WA numbers: Odoo vs Sheets')
    parser.add_argument('--csv', action='store_true', help='Write results to compare_wa_numbers.csv')
    args = parser.parse_args()

    print("Loading Odoo config...")
    cfg = load_odoo_config()

    print(f"Connecting to Odoo production ({cfg['url']})...")
    db, uid, pw, models = odoo_connect(cfg)

    print("Reading Odoo partners (tags 25 + 26)...")
    odoo_partners = load_odoo_partners(db, uid, pw, models)
    print(f"  → {len(odoo_partners)} partners found")

    print("Reading Google Sheets Customers tab...")
    sheet_eligible, sheet_ineligible = load_sheet_rows()
    print(f"  → {len(sheet_eligible)} eligible rows (C=ACTIVE/PENDING, Q=YES, R=YES)")
    print(f"  → {len(sheet_ineligible)} ineligible rows (failed C/Q/R filter)")

    print("Building diff...")
    rows = build_report(odoo_partners, sheet_eligible, sheet_ineligible)

    print_report(rows)

    if args.csv:
        csv_path = os.path.join(SCRIPT_DIR, 'compare_wa_numbers.csv')
        write_csv(rows, csv_path)


if __name__ == '__main__':
    main()
