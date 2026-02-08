#!/usr/bin/env python3
"""
Sync Testing → Production: Representante Contact Emails

Applies the email field updates from testing (source of truth) to production.
Based on sync comparison report from 2026-02-08.

Actions:
  - 8 UPDATE: Append secondary emails to production partners
  - SKIP: DANMARYS BARRIOS (test-only), IRIS DE GUEDEZ (ID mismatch, manual review)

Safety: Only updates email fields. Does not create/delete partners.

Usage:
    python3 /opt/odoo-dev/scripts/sync_testing_to_production.py

Author: Claude Code Assistant
Date: 2026-02-08
"""

import xmlrpc.client

# ============================================================================
# Configuration
# ============================================================================

TESTING = {
    'url': 'http://localhost:8019',
    'db': 'testing',
    'user': 'tdv.devs@gmail.com',
    'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
}

PRODUCTION = {
    'url': 'https://odoo.ueipab.edu.ve',
    'db': 'DB_UEIPAB',
    'user': 'tdv.devs@gmail.com',
    'password': 'f69330e5bd6ae043320f054e9df9fcbbb34522db',
}

# Partners to sync (same ID in both envs) — email field only
# From sync comparison report 2026-02-08
SYNC_PARTNERS = [
    (2174, 'ANTONIO MARTINEZ'),
    (2255, 'CASTO GONZALEZ'),
    (2294, 'DAIRILYS CHAURAN'),
    (2341, 'DOALBERT NUÑEZ'),
    (2417, 'FRANCIA LORETO'),
    (2450, 'GLORIA MILLAN'),
    (2659, 'MARIA APONTE'),
    (3663, 'MIGUEL MARIN'),
]

# Excluded:
# - DANMARYS BARRIOS #2305: test-only contact, not in production
# - IRIS DE GUEDEZ: ID mismatch (test=2811, prod=2503), needs manual review


# ============================================================================
# Main
# ============================================================================

def connect(cfg, label):
    print(f"  Connecting to {label} ({cfg['url']})...")
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise ConnectionError(f"Failed to authenticate with {label}")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    print(f"  Connected as uid={uid}")
    return uid, models


def read_partner(models, uid, cfg, partner_id):
    records = models.execute_kw(
        cfg['db'], uid, cfg['password'],
        'res.partner', 'search_read',
        [[('id', '=', partner_id)]],
        {'fields': ['id', 'name', 'email']}
    )
    return records[0] if records else None


def write_partner(models, uid, cfg, partner_id, vals):
    return models.execute_kw(
        cfg['db'], uid, cfg['password'],
        'res.partner', 'write',
        [[partner_id], vals]
    )


def main():
    print("=" * 70)
    print("  SYNC: Testing → Production (Representante Email Fields)")
    print("=" * 70)
    print()

    test_uid, test_models = connect(TESTING, 'testing')
    prod_uid, prod_models = connect(PRODUCTION, 'production')
    print()

    results = {'updated': 0, 'skipped': 0, 'errors': 0}

    for partner_id, expected_name in SYNC_PARTNERS:
        print(f"--- {expected_name} (ID {partner_id}) ---")

        # Read from both
        test_p = read_partner(test_models, test_uid, TESTING, partner_id)
        prod_p = read_partner(prod_models, prod_uid, PRODUCTION, partner_id)

        if not test_p:
            print(f"  ERROR: Not found in testing!")
            results['errors'] += 1
            print()
            continue
        if not prod_p:
            print(f"  ERROR: Not found in production!")
            results['errors'] += 1
            print()
            continue

        test_email = (test_p['email'] or '').strip()
        prod_email = (prod_p['email'] or '').strip()

        print(f"  Testing:    {test_email!r}")
        print(f"  Production: {prod_email!r}")

        # Normalize for comparison
        test_set = set(e.strip().lower() for e in test_email.split(';') if e.strip())
        prod_set = set(e.strip().lower() for e in prod_email.split(';') if e.strip())

        if test_set == prod_set:
            print(f"  SKIP: Already in sync")
            results['skipped'] += 1
            print()
            continue

        # Apply testing email to production
        print(f"  Action: Update production email to {test_email!r}")
        write_partner(prod_models, prod_uid, PRODUCTION, partner_id, {'email': test_email})
        print(f"  DONE")
        results['updated'] += 1
        print()

    # Summary
    print("=" * 70)
    print(f"  SUMMARY: {results['updated']} updated, {results['skipped']} skipped, {results['errors']} errors")
    print("=" * 70)
    print()
    print("  Excluded from sync:")
    print("    - DANMARYS BARRIOS #2305 (test-only, not in production)")
    print("    - IRIS DE GUEDEZ (ID mismatch test=2811/prod=2503, manual review)")
    print()


if __name__ == '__main__':
    main()
