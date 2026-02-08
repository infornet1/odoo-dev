#!/usr/bin/env python3
"""
Contact Sync Comparison: Testing vs Production

Compares Representante / Representante PDVSA contacts between testing and
production Odoo environments. Testing is the source of truth after sync fixes.

Generates a diff report showing what needs to sync: testing → production.

Usage:
    python3 /opt/odoo-dev/scripts/contact_sync_comparison.py

Author: Claude Code Assistant
Date: 2026-02-08
"""

import xmlrpc.client
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

ENVS = {
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

# Tag IDs for Representante / Representante PDVSA (same in both envs)
REPRESENTANTE_TAG_IDS = [25, 26]

# Fields to compare
COMPARE_FIELDS = ['email', 'mobile', 'phone', 'vat']

# All fields to fetch
FETCH_FIELDS = ['id', 'name', 'email', 'mobile', 'phone', 'vat', 'category_id', 'active']

OUTPUT_FILE = '/opt/odoo-dev/scripts/sync_reports/contact_sync_diagnostic_2026-02-08.txt'


# ============================================================================
# Helpers
# ============================================================================

def connect(env_name):
    """Connect to an Odoo environment."""
    cfg = ENVS[env_name]
    print(f"  Connecting to {env_name} ({cfg['url']})...")
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise ConnectionError(f"Failed to authenticate with {env_name}")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    print(f"  Connected as uid={uid}")
    return uid, models, cfg


def fetch_representantes(uid, models, cfg):
    """Fetch all Representante/Representante PDVSA contacts."""
    return models.execute_kw(
        cfg['db'], uid, cfg['password'],
        'res.partner', 'search_read',
        [[('category_id', 'in', REPRESENTANTE_TAG_IDS), ('active', '=', True)]],
        {'fields': FETCH_FIELDS, 'order': 'name'}
    )


def normalize(val):
    """Normalize a field value for comparison."""
    if val is False or val is None:
        return ''
    return str(val).strip()


def normalize_email(val):
    """Normalize email for comparison (lowercase, sorted parts)."""
    raw = normalize(val)
    if not raw:
        return ''
    parts = sorted([e.strip().lower() for e in raw.split(';') if e.strip()])
    return ';'.join(parts)


def format_val(val, max_len=55):
    """Format a value for display."""
    s = repr(normalize(val))
    if len(s) > max_len:
        s = s[:max_len-3] + '...'
    return s


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("  CONTACT SYNC COMPARISON: Testing vs Production")
    print("=" * 70)
    print()

    # Connect to both environments
    test_uid, test_models, test_cfg = connect('testing')
    prod_uid, prod_models, prod_cfg = connect('production')
    print()

    # Fetch contacts
    print("Fetching Representante contacts...")
    test_contacts = fetch_representantes(test_uid, test_models, test_cfg)
    prod_contacts = fetch_representantes(prod_uid, prod_models, prod_cfg)
    print(f"  Testing:    {len(test_contacts)} contacts")
    print(f"  Production: {len(prod_contacts)} contacts")
    print()

    # Index by name
    test_by_name = {c['name'].strip().upper(): c for c in test_contacts}
    prod_by_name = {c['name'].strip().upper(): c for c in prod_contacts}

    test_names = set(test_by_name.keys())
    prod_names = set(prod_by_name.keys())

    only_test = sorted(test_names - prod_names)
    only_prod = sorted(prod_names - test_names)
    in_both = sorted(test_names & prod_names)

    # Find differences
    differences = []
    for name in in_both:
        tc = test_by_name[name]
        pc = prod_by_name[name]
        diffs = {}
        for field in COMPARE_FIELDS:
            if field == 'email':
                tv = normalize_email(tc[field])
                pv = normalize_email(pc[field])
            else:
                tv = normalize(tc[field])
                pv = normalize(pc[field])
            if tv != pv:
                diffs[field] = (tc[field], pc[field])
        if diffs:
            differences.append((name, tc, pc, diffs))

    # Generate report
    lines = []
    lines.append("SYNC DIAGNOSTIC REPORT: Representante / Representante PDVSA Contacts")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Source of truth: TESTING (after sync fixes applied 2026-02-08)")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Summary:")
    lines.append(f"  Testing contacts:    {len(test_contacts)}")
    lines.append(f"  Production contacts: {len(prod_contacts)}")
    lines.append(f"  In both (by name):   {len(in_both)}")
    lines.append(f"  Only in testing:     {len(only_test)}")
    lines.append(f"  Only in production:  {len(only_prod)}")
    lines.append(f"  With differences:    {len(differences)}")
    lines.append("")

    # Only in testing → need to create in production
    if only_test:
        lines.append(f"--- ONLY IN TESTING ({len(only_test)}) - Need to create in production ---")
        for name in only_test:
            c = test_by_name[name]
            lines.append(f"  - {c['name']} | ID: {c['id']} | VAT: {normalize(c['vat'])} "
                         f"| Email: {normalize(c['email'])} | Mobile: {normalize(c['mobile'])}")
        lines.append("")

    # Only in production → may need to create in testing or investigate
    if only_prod:
        lines.append(f"--- ONLY IN PRODUCTION ({len(only_prod)}) - Review needed ---")
        for name in only_prod:
            c = prod_by_name[name]
            lines.append(f"  - {c['name']} | ID: {c['id']} | VAT: {normalize(c['vat'])} "
                         f"| Email: {normalize(c['email'])} | Mobile: {normalize(c['mobile'])}")
        lines.append("")

    # Field differences → testing wins (source of truth)
    if differences:
        lines.append(f"--- FIELD DIFFERENCES ({len(differences)} contacts) ---")
        lines.append(f"--- Direction: TESTING → PRODUCTION (testing is source of truth) ---")
        lines.append("")

        for name, tc, pc, diffs in sorted(differences, key=lambda x: x[0]):
            test_id = tc['id']
            prod_id = pc['id']
            id_match = "same" if test_id == prod_id else f"MISMATCH test={test_id} prod={prod_id}"
            lines.append(f"  {tc['name']} (Test ID: {test_id}, Prod ID: {prod_id}) [{id_match}]")
            for field, (tv, pv) in sorted(diffs.items()):
                lines.append(f"    {field:8s}: TEST={format_val(tv):55s} PROD={format_val(pv)}")
            lines.append("")
    else:
        lines.append("--- NO FIELD DIFFERENCES ---")
        lines.append("")

    # Sync action summary
    lines.append("--- SYNC ACTIONS NEEDED (Testing → Production) ---")
    lines.append("")

    action_count = 0

    if only_test:
        lines.append(f"  CREATE in production ({len(only_test)}):")
        for name in only_test:
            c = test_by_name[name]
            lines.append(f"    - {c['name']} (test ID {c['id']})")
            action_count += 1
        lines.append("")

    if only_prod:
        lines.append(f"  REVIEW - only in production ({len(only_prod)}):")
        for name in only_prod:
            c = prod_by_name[name]
            lines.append(f"    - {c['name']} (prod ID {c['id']}) - create in testing or investigate")
            action_count += 1
        lines.append("")

    if differences:
        lines.append(f"  UPDATE in production ({len(differences)}):")
        for name, tc, pc, diffs in sorted(differences, key=lambda x: x[0]):
            field_list = ', '.join(sorted(diffs.keys()))
            lines.append(f"    - {tc['name']} (ID {tc['id']}): update {field_list}")
            action_count += 1
        lines.append("")

    lines.append(f"  Total sync actions: {action_count}")
    lines.append("")

    # Print report
    report = '\n'.join(lines)
    print(report)

    # Save to file
    with open(OUTPUT_FILE, 'w') as f:
        f.write(report + '\n')
    print(f"\nReport saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
