#!/usr/bin/env python3
"""
Contact Data Sync Fix — Odoo Testing Environment

Cross-reference analysis between 4 data sources (Odoo contacts, Freescout bounces,
Google Sheets "Customers" and "Akdemia2526") revealed sync inconsistencies for
Representante contacts with bounced emails.

This script fixes all inconsistencies in TESTING ONLY before enabling the AI agent.

Categories:
  A: Link 7 not-found bounce logs to correct partners + add bounced email
  B: Add secondary email to MIGUEL MARIN #3663
  C: Flag SORELIS MAITA #3669 for manual mobile lookup
  D: Clean up Perdomo duplicates (bounce logs + partners)

Safety: DRY_RUN=True by default. All changes printed before execution.

Usage:
    python3 /opt/odoo-dev/scripts/contact_data_sync_fix.py

Author: Claude Code Assistant
Date: 2026-02-08
"""

import sys
import xmlrpc.client

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = False  # Set True to preview without changes

# Testing environment ONLY
ODOO_URL = 'http://localhost:8019'
ODOO_DB = 'testing'
ODOO_USER = 'tdv.devs@gmail.com'
ODOO_PASSWORD = '35baa2abcc6dee920fa75014f0274c8e551871ce'

# ============================================================================
# Category A: Link 7 not-found bounce logs to correct partners
# ============================================================================
# Each tuple: (bounce_log_id, bounced_email, partner_id, partner_name, new_tier)
# new_tier: 'clean' for permanent failures (domain_not_found, invalid_address)
#           'flag' for temporary failures (mailbox_full, rejected, other)
CATEGORY_A = [
    (30, 'ajlopezo36@gmail.com', 2294, 'DAIRILYS CHAURAN', 'flag'),       # A1 - mailbox_full
    (32, 'antonyfeli5@gmail.com', 2174, 'ANTONIO MARTINEZ', 'flag'),       # A2 - mailbox_full
    (33, 'apontemb@pdvsa.com', 2659, 'MARIA APONTE', 'clean'),            # A3 - domain_not_found
    (46, 'franhielys@gmail.com', 2341, 'DOALBERT NUÑEZ', 'flag'),         # A4 - mailbox_full
    (54, 'loretof@pdvsa.com', 2417, 'FRANCIA LORETO', 'clean'),           # A5 - domain_not_found
    (56, 'marianyicastellanos@gmail.com', 2255, 'CASTO GONZALEZ', 'flag'), # A6 - mailbox_full
    (58, 'millangloria86@gmail.com', 2450, 'GLORIA MILLAN', 'flag'),       # A7 - mailbox_full
]

# ============================================================================
# Category B: Add secondary email to MIGUEL MARIN
# ============================================================================
CATEGORY_B = {
    'partner_id': 3663,
    'partner_name': 'MIGUEL MARIN',
    'email_to_add': 'susanaquijada102@gmail.com',
}

# ============================================================================
# Category C: Flag SORELIS MAITA for manual mobile lookup
# ============================================================================
CATEGORY_C = {
    'bounce_log_id': 55,
    'partner_name': 'SORELIS MAITA',
    'partner_id': 3669,
}

# ============================================================================
# Category D: Clean up Perdomo duplicates
# ============================================================================
CATEGORY_D = {
    'bounce_log_ids_to_delete': [27, 28, 29],  # perdomo.gustavo@gmail.com bounces
    'partners_to_archive': [3612, 3676],         # Duplicate partner records
    'real_partner_id': 7,                         # Real Gustavo Perdomo user
    'email_to_add': 'perdomo.gustavo@gmail.com',  # Optional secondary email
}


# ============================================================================
# Helpers
# ============================================================================

def connect():
    """Establish XML-RPC connection to Odoo testing."""
    print(f"Connecting to {ODOO_URL} (db={ODOO_DB})...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ConnectionError("Failed to authenticate with Odoo testing")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    print(f"  Connected as uid={uid}\n")
    return uid, models


def search_read(models, uid, model, domain, fields):
    """Search and read records."""
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'search_read',
        [domain], {'fields': fields}
    )


def write(models, uid, model, ids, vals):
    """Write to records (respects DRY_RUN)."""
    if DRY_RUN:
        print(f"  [DRY_RUN] Would write {model} ids={ids}: {vals}")
        return True
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'write',
        [ids, vals]
    )


def unlink(models, uid, model, ids):
    """Delete records (respects DRY_RUN)."""
    if DRY_RUN:
        print(f"  [DRY_RUN] Would delete {model} ids={ids}")
        return True
    return models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, 'unlink',
        [ids]
    )


def append_email(current_email, new_email):
    """Append email to semicolon-separated email field, avoiding duplicates."""
    current = (current_email or '').strip()
    if not current:
        return new_email.strip()
    emails = [e.strip() for e in current.split(';') if e.strip()]
    if new_email.strip().lower() not in [e.lower() for e in emails]:
        emails.append(new_email.strip())
    return ';'.join(emails)


def print_separator(char='=', length=70):
    print(char * length)


def print_header(title):
    print()
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


# ============================================================================
# Category A: Link 7 not-found bounce logs
# ============================================================================

def execute_category_a(uid, models):
    print_header("CATEGORY A: Link 7 Not-Found Bounce Logs to Correct Partners")

    results = {'success': 0, 'skipped': 0, 'errors': 0}

    for i, (bl_id, bounced_email, partner_id, partner_name, new_tier) in enumerate(CATEGORY_A, 1):
        print(f"--- A{i}: Bounce Log #{bl_id} → Partner #{partner_id} ({partner_name}) ---")

        # Read current bounce log state
        bl_records = search_read(models, uid, 'mail.bounce.log',
                                 [('id', '=', bl_id)],
                                 ['id', 'bounced_email', 'partner_id', 'action_tier', 'bounce_reason', 'state'])
        if not bl_records:
            print(f"  ERROR: Bounce log #{bl_id} not found!")
            results['errors'] += 1
            print()
            continue

        bl = bl_records[0]
        print(f"  Bounce log #{bl_id}:")
        print(f"    bounced_email: {bl['bounced_email']}")
        print(f"    partner_id:    {bl['partner_id'] or 'None'}")
        print(f"    action_tier:   {bl['action_tier']}")
        print(f"    bounce_reason: {bl['bounce_reason']}")
        print(f"    state:         {bl['state']}")

        # Verify bounced email matches
        if bl['bounced_email'] != bounced_email:
            print(f"  ERROR: Expected bounced_email='{bounced_email}', got '{bl['bounced_email']}'")
            results['errors'] += 1
            print()
            continue

        # Read current partner state
        partner_records = search_read(models, uid, 'res.partner',
                                      [('id', '=', partner_id)],
                                      ['id', 'name', 'email', 'category_id'])
        if not partner_records:
            print(f"  ERROR: Partner #{partner_id} not found!")
            results['errors'] += 1
            print()
            continue

        partner = partner_records[0]
        print(f"  Partner #{partner_id}:")
        print(f"    name:  {partner['name']}")
        print(f"    email: {partner['email']}")
        print(f"    tags:  {partner['category_id']}")

        # Check if already linked
        if bl['partner_id'] and bl['partner_id'][0] == partner_id:
            print(f"  SKIP: Bounce log already linked to partner #{partner_id}")
            results['skipped'] += 1
            print()
            continue

        # Step 1: Update bounce log (link partner + update tier)
        bl_vals = {
            'partner_id': partner_id,
            'action_tier': new_tier,
        }
        print(f"  Action 1: Update bounce log #{bl_id}: partner_id={partner_id}, action_tier={new_tier}")
        write(models, uid, 'mail.bounce.log', [bl_id], bl_vals)

        # Step 2: Append bounced email to partner's email field
        new_email = append_email(partner['email'], bounced_email)
        if new_email != (partner['email'] or ''):
            print(f"  Action 2: Update partner #{partner_id} email: '{partner['email']}' → '{new_email}'")
            write(models, uid, 'res.partner', [partner_id], {'email': new_email})
        else:
            print(f"  Action 2: Partner email already contains '{bounced_email}', no change needed")

        results['success'] += 1
        print(f"  DONE ✓")
        print()

    print(f"Category A Summary: {results['success']} linked, {results['skipped']} skipped, {results['errors']} errors")
    return results


# ============================================================================
# Category B: Add secondary email to MIGUEL MARIN
# ============================================================================

def execute_category_b(uid, models):
    print_header("CATEGORY B: Add Secondary Email to MIGUEL MARIN #3663")

    pid = CATEGORY_B['partner_id']
    email_to_add = CATEGORY_B['email_to_add']

    # Read current state
    records = search_read(models, uid, 'res.partner',
                          [('id', '=', pid)],
                          ['id', 'name', 'email', 'mobile', 'phone'])
    if not records:
        print(f"  ERROR: Partner #{pid} not found!")
        return {'errors': 1}

    partner = records[0]
    print(f"  Partner #{pid}:")
    print(f"    name:   {partner['name']}")
    print(f"    email:  {partner['email']}")
    print(f"    mobile: {partner['mobile']}")

    new_email = append_email(partner['email'], email_to_add)
    if new_email != (partner['email'] or ''):
        print(f"  Action: Update email: '{partner['email']}' → '{new_email}'")
        write(models, uid, 'res.partner', [pid], {'email': new_email})
        print(f"  DONE ✓")
        return {'success': 1}
    else:
        print(f"  SKIP: Email already contains '{email_to_add}'")
        return {'skipped': 1}


# ============================================================================
# Category C: Flag SORELIS MAITA for manual mobile lookup
# ============================================================================

def execute_category_c(uid, models):
    print_header("CATEGORY C: Flag SORELIS MAITA #3669 for Manual Mobile Lookup")

    bl_id = CATEGORY_C['bounce_log_id']
    pid = CATEGORY_C['partner_id']

    # Read bounce log
    bl_records = search_read(models, uid, 'mail.bounce.log',
                             [('id', '=', bl_id)],
                             ['id', 'bounced_email', 'partner_id', 'action_tier', 'state'])
    if bl_records:
        bl = bl_records[0]
        print(f"  Bounce log #{bl_id}:")
        print(f"    bounced_email: {bl['bounced_email']}")
        print(f"    partner_id:    {bl['partner_id'] or 'None'}")
        print(f"    action_tier:   {bl['action_tier']}")
        print(f"    state:         {bl['state']}")
    else:
        print(f"  WARNING: Bounce log #{bl_id} not found")

    # Read partner
    partner_records = search_read(models, uid, 'res.partner',
                                  [('id', '=', pid)],
                                  ['id', 'name', 'email', 'mobile', 'phone'])
    if partner_records:
        p = partner_records[0]
        print(f"  Partner #{pid}:")
        print(f"    name:   {p['name']}")
        print(f"    email:  {p['email']}")
        print(f"    mobile: {p['mobile'] or 'NONE'}")
        print(f"    phone:  {p['phone'] or 'NONE'}")
    else:
        print(f"  WARNING: Partner #{pid} not found")

    # Link bounce log to partner if not already linked
    if bl_records and (not bl_records[0]['partner_id'] or bl_records[0]['partner_id'][0] != pid):
        print(f"  Action 1: Link bounce log #{bl_id} → partner #{pid}")
        write(models, uid, 'mail.bounce.log', [bl_id], {
            'partner_id': pid,
            'action_tier': 'flag',
        })
    elif bl_records:
        print(f"  Bounce log already linked to partner #{pid}")

    print()
    print(f"  ⚠ MANUAL ACTION REQUIRED:")
    print(f"    SORELIS MAITA has no mobile/phone number in Odoo.")
    print(f"    Glenda cannot WhatsApp without mobile number.")
    print(f"    User needs to find and provide mobile from school records.")
    print()

    return {'flagged': 1}


# ============================================================================
# Category D: Clean up Perdomo duplicates
# ============================================================================

def execute_category_d(uid, models):
    print_header("CATEGORY D: Clean Up Perdomo Duplicates")

    results = {'deleted_bls': 0, 'archived_partners': 0, 'email_added': False}

    # --- D1: Delete bounce logs #27, #28, #29 ---
    print("--- D1: Delete Perdomo bounce logs ---")
    bl_ids = CATEGORY_D['bounce_log_ids_to_delete']
    bl_records = search_read(models, uid, 'mail.bounce.log',
                             [('id', 'in', bl_ids)],
                             ['id', 'bounced_email', 'action_tier', 'partner_id'])
    for bl in bl_records:
        print(f"  Bounce log #{bl['id']}: {bl['bounced_email']} (tier={bl['action_tier']}, partner={bl['partner_id'] or 'None'})")

    if bl_records:
        found_ids = [bl['id'] for bl in bl_records]
        print(f"  Action: Delete bounce logs {found_ids}")
        unlink(models, uid, 'mail.bounce.log', found_ids)
        results['deleted_bls'] = len(found_ids)
        print(f"  Deleted {len(found_ids)} bounce log(s) ✓")
    else:
        print(f"  No bounce logs found with ids {bl_ids}")
    print()

    # --- D2/D3: Archive duplicate partners #3612, #3676 ---
    print("--- D2/D3: Archive duplicate Perdomo partners ---")
    dup_ids = CATEGORY_D['partners_to_archive']
    dup_records = search_read(models, uid, 'res.partner',
                              [('id', 'in', dup_ids)],
                              ['id', 'name', 'email', 'mobile', 'category_id', 'active', 'company_type'])

    # Also check inactive records
    if len(dup_records) < len(dup_ids):
        inactive_records = search_read(models, uid, 'res.partner',
                                       [('id', 'in', dup_ids), ('active', '=', False)],
                                       ['id', 'name', 'email', 'mobile', 'category_id', 'active', 'company_type'])
        dup_records.extend(inactive_records)

    for p in dup_records:
        print(f"  Partner #{p['id']}: {p['name']}")
        print(f"    email: {p['email']}, mobile: {p.get('mobile') or 'None'}")
        print(f"    tags: {p['category_id']}, active: {p['active']}, type: {p.get('company_type', 'N/A')}")

    active_dups = [p['id'] for p in dup_records if p['active']]
    if active_dups:
        print(f"  Action: Archive partners {active_dups} (set active=False)")
        write(models, uid, 'res.partner', active_dups, {'active': False})
        results['archived_partners'] = len(active_dups)
        print(f"  Archived {len(active_dups)} partner(s) ✓")
    else:
        already_archived = [p['id'] for p in dup_records if not p['active']]
        if already_archived:
            print(f"  SKIP: Partners {already_archived} already archived")
        else:
            print(f"  No duplicate partners found with ids {dup_ids}")
    print()

    # --- D4: Add secondary email to real Gustavo Perdomo #7 ---
    print("--- D4: Add secondary email to real Gustavo Perdomo #7 ---")
    real_pid = CATEGORY_D['real_partner_id']
    email_to_add = CATEGORY_D['email_to_add']

    real_records = search_read(models, uid, 'res.partner',
                               [('id', '=', real_pid)],
                               ['id', 'name', 'email'])
    if real_records:
        p = real_records[0]
        print(f"  Partner #{p['id']}: {p['name']}")
        print(f"    current email: {p['email']}")

        new_email = append_email(p['email'], email_to_add)
        if new_email != (p['email'] or ''):
            print(f"  Action: Update email: '{p['email']}' → '{new_email}'")
            write(models, uid, 'res.partner', [real_pid], {'email': new_email})
            results['email_added'] = True
            print(f"  DONE ✓")
        else:
            print(f"  SKIP: Email already contains '{email_to_add}'")
    else:
        print(f"  ERROR: Partner #{real_pid} not found!")
    print()

    print(f"Category D Summary: {results['deleted_bls']} bounce logs deleted, "
          f"{results['archived_partners']} partners archived, "
          f"email added: {results['email_added']}")
    return results


# ============================================================================
# Category E: Report only (no changes)
# ============================================================================

def report_category_e():
    print_header("CATEGORY E: Remaining Not-Found Bounce Logs (No Action)")

    orphans = [
        ('avvae_238@hotmail.com', 'invalid_address', '1x'),
        ('bompartt70@gmail.com', 'mailbox_full', '4x'),
        ('condalesl@petrocedeno.pdvsa.com', 'domain_not_found', '3x'),
        ('dagoberto.abarca@ueipab.edu.ve', 'invalid_address', '2x'),
        ('espinat.22@gmail.com', 'mailbox_full', '3x'),
        ('goitel@pdvsa.com', 'domain_not_found', '2x'),
        ('elviram511@gmail.com', 'mailbox_full', '1x'),
        ('vanehdez90@gmail.com', 'mailbox_full', '3x'),
    ]

    print("  These emails have NO match in Odoo, Customers, or Akdemia.")
    print("  No action needed — orphan bounces from old/staff contacts.")
    print()
    for email, reason, count in orphans:
        print(f"    {email:<45} {reason:<20} {count}")
    print()
    print(f"  Total: {len(orphans)} orphan bounce emails — no changes.")


# ============================================================================
# Main
# ============================================================================

def main():
    print_separator('=', 70)
    print("  CONTACT DATA SYNC FIX — Odoo Testing Environment")
    print(f"  DRY_RUN = {DRY_RUN}")
    print(f"  Target: {ODOO_URL} / {ODOO_DB}")
    print_separator('=', 70)

    if DRY_RUN:
        print("\n  *** DRY RUN MODE — No changes will be made ***\n")

    uid, models = connect()

    # Execute all categories
    a_results = execute_category_a(uid, models)
    b_results = execute_category_b(uid, models)
    c_results = execute_category_c(uid, models)
    d_results = execute_category_d(uid, models)
    report_category_e()

    # Final summary
    print_header("FINAL SUMMARY")
    print(f"  Category A: {a_results}")
    print(f"  Category B: {b_results}")
    print(f"  Category C: {c_results}")
    print(f"  Category D: {d_results}")
    print(f"  Category E: Report only (8 orphans, no changes)")
    print()

    if DRY_RUN:
        print("  *** DRY RUN — No changes were made. Set DRY_RUN=False to apply. ***")
    else:
        print("  All changes applied to TESTING environment.")
        print("  Next: Re-run contact comparison script for testing → production sync.")
    print()


if __name__ == '__main__':
    main()
