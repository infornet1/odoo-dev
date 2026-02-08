#!/usr/bin/env python3
"""
Sync Mailing Lists and Contacts from Production to Testing

One-shot script to import production mailing.list and mailing.contact
records into testing for environment parity.

SAFETY:
  - Never touches todalacomunidad@ueipab.edu.ve
  - DRY_RUN=True by default
  - Only writes to TESTING, reads from PRODUCTION

Usage:
    python3 /opt/odoo-dev/scripts/sync_mailing_contacts.py
    python3 /opt/odoo-dev/scripts/sync_mailing_contacts.py --live

Author: Claude Code Assistant
Date: 2026-02-08
"""

import argparse
import xmlrpc.client
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True

PROD = {
    'url': 'https://odoo.ueipab.edu.ve',
    'db': 'DB_UEIPAB',
    'user': 'tdv.devs@gmail.com',
    'password': 'f69330e5bd6ae043320f054e9df9fcbbb34522db',
}

TEST = {
    'url': 'http://localhost:8019',
    'db': 'testing',
    'user': 'tdv.devs@gmail.com',
    'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
}

# Protected emails — must NEVER be modified or synced
PROTECTED_EMAILS = {'todalacomunidad@ueipab.edu.ve'}


# ============================================================================
# Helpers
# ============================================================================

def connect(cfg, label):
    print(f"Connecting to {label}: {cfg['url']} (db={cfg['db']})...")
    common = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/common')
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise ConnectionError(f"Failed to authenticate with {label}")
    models = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/object')
    print(f"  Connected as uid={uid}")
    return uid, models, cfg['db'], cfg['password']


def search_read(models, db, uid, pw, model, domain, fields):
    return models.execute_kw(db, uid, pw, model, 'search_read', [domain], {'fields': fields})


def search(models, db, uid, pw, model, domain):
    return models.execute_kw(db, uid, pw, model, 'search', [domain])


def create(models, db, uid, pw, model, vals):
    return models.execute_kw(db, uid, pw, model, 'create', [vals])


def write(models, db, uid, pw, model, ids, vals):
    return models.execute_kw(db, uid, pw, model, 'write', [ids, vals])


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Sync mailing contacts prod → testing')
    parser.add_argument('--live', action='store_true', help='Apply changes (disable DRY_RUN)')
    args = parser.parse_args()

    global DRY_RUN
    if args.live:
        DRY_RUN = False

    print("=" * 70)
    print("  SYNC MAILING LISTS & CONTACTS: Production → Testing")
    print("=" * 70)
    print(f"  Date:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print()

    # Connect to both environments
    p_uid, p_models, p_db, p_pw = connect(PROD, 'PRODUCTION')
    t_uid, t_models, t_db, t_pw = connect(TEST, 'TESTING')

    # ---- Step 1: Sync mailing lists ----
    print("\n" + "=" * 70)
    print("  Step 1: Sync Mailing Lists")
    print("=" * 70)

    prod_lists = search_read(p_models, p_db, p_uid, p_pw,
                             'mailing.list', [],
                             ['id', 'name', 'active', 'contact_count'])
    test_lists = search_read(t_models, t_db, t_uid, t_pw,
                             'mailing.list', [],
                             ['id', 'name', 'active', 'contact_count'])

    test_list_by_name = {ml['name']: ml for ml in test_lists}
    list_id_map = {}  # prod_id → test_id

    print(f"\n  Production lists: {len(prod_lists)}")
    for ml in prod_lists:
        print(f"    #{ml['id']} {ml['name']} ({ml['contact_count']} contacts)")

    print(f"\n  Testing lists: {len(test_lists)}")
    for ml in test_lists:
        print(f"    #{ml['id']} {ml['name']} ({ml['contact_count']} contacts)")

    for pl in prod_lists:
        existing = test_list_by_name.get(pl['name'])
        if existing:
            list_id_map[pl['id']] = existing['id']
            print(f"\n  List '{pl['name']}': already exists in testing as #{existing['id']}")
        else:
            prefix = "[DRY_RUN] " if DRY_RUN else ""
            print(f"\n  {prefix}Creating list '{pl['name']}' in testing...")
            if not DRY_RUN:
                new_id = create(t_models, t_db, t_uid, t_pw,
                                'mailing.list', {'name': pl['name'], 'active': pl['active']})
                list_id_map[pl['id']] = new_id
                print(f"    Created as #{new_id}")
            else:
                list_id_map[pl['id']] = None
                print(f"    {prefix}Would create")

    # ---- Step 2: Sync mailing contacts ----
    print("\n" + "=" * 70)
    print("  Step 2: Sync Mailing Contacts")
    print("=" * 70)

    prod_contacts = search_read(p_models, p_db, p_uid, p_pw,
                                'mailing.contact', [],
                                ['id', 'name', 'email', 'list_ids', 'is_blacklisted',
                                 'company_name', 'country_id', 'title_id', 'tag_ids'])

    # Get existing testing contacts by email for dedup
    test_contacts = search_read(t_models, t_db, t_uid, t_pw,
                                'mailing.contact', [],
                                ['id', 'name', 'email', 'list_ids'])
    test_mc_by_email = {}
    for tc in test_contacts:
        if tc.get('email'):
            test_mc_by_email[tc['email'].strip().lower()] = tc

    print(f"\n  Production contacts: {len(prod_contacts)}")
    print(f"  Testing contacts: {len(test_contacts)}")

    created = 0
    updated = 0
    skipped = 0
    protected_skipped = 0

    for pc in prod_contacts:
        email = (pc.get('email') or '').strip()
        email_lower = email.lower()

        # Skip protected emails
        if email_lower in PROTECTED_EMAILS:
            protected_skipped += 1
            continue

        # Skip empty emails
        if not email:
            skipped += 1
            continue

        # Map list IDs from production to testing
        test_list_ids = []
        for prod_list_id in pc.get('list_ids', []):
            test_lid = list_id_map.get(prod_list_id)
            if test_lid:
                test_list_ids.append(test_lid)

        prefix = "[DRY_RUN] " if DRY_RUN else ""

        existing = test_mc_by_email.get(email_lower)
        if existing:
            # Update list membership if needed
            current_lists = set(existing.get('list_ids', []))
            new_lists = set(test_list_ids) - current_lists
            if new_lists:
                # Use (4, id) command to add to list without removing existing
                list_commands = [(4, lid) for lid in new_lists]
                if not DRY_RUN:
                    write(t_models, t_db, t_uid, t_pw,
                          'mailing.contact', [existing['id']],
                          {'list_ids': list_commands})
                updated += 1
            else:
                skipped += 1
        else:
            # Create new contact
            vals = {
                'name': pc.get('name') or '',
                'email': email,
                'list_ids': [(6, 0, test_list_ids)] if test_list_ids else [],
            }

            if not DRY_RUN:
                new_id = create(t_models, t_db, t_uid, t_pw,
                                'mailing.contact', vals)
            created += 1

    print(f"\n  Results:")
    print(f"    Created:           {created}")
    print(f"    Updated (lists):   {updated}")
    print(f"    Skipped (exists):  {skipped}")
    print(f"    Protected skipped: {protected_skipped}")

    # ---- Step 3: Verify ----
    print("\n" + "=" * 70)
    print("  Step 3: Verification")
    print("=" * 70)

    if not DRY_RUN:
        final_lists = search_read(t_models, t_db, t_uid, t_pw,
                                  'mailing.list', [],
                                  ['id', 'name', 'contact_count'])
        print(f"\n  Testing lists after sync:")
        for ml in final_lists:
            print(f"    #{ml['id']} {ml['name']} ({ml['contact_count']} contacts)")

        final_count = len(search(t_models, t_db, t_uid, t_pw,
                                 'mailing.contact', []))
        print(f"\n  Total testing mailing contacts: {final_count}")
    else:
        print(f"\n  [DRY_RUN] Would have created {created} contacts, updated {updated}")

    print("\n" + "=" * 70)
    if DRY_RUN:
        print("  DRY RUN — No changes made. Use --live to apply.")
    else:
        print("  Sync complete.")
    print("=" * 70)


if __name__ == '__main__':
    main()
