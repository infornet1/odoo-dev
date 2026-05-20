#!/usr/bin/env python3
"""
send_vote_wa_reminder.py
------------------------
WhatsApp reminder blast for pending voters in the Budget Consultation 2026-2027.

Sources:
  - Google Sheets (1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA) Customers tab
    col B=name, col C=status, col J=email, col L=phone
  - Odoo production: partner.communication.ack (notice_key=budget_consulta_2026_2027)

Logic:
  1. Load ACTIVE rows from sheet
  2. Match each to an ACK record (by email, then phone fallback)
  3. Skip: already voted (continuing/leaving), bounce_wa_sent=True, no token
  4. Send personalized WA with direct A/B vote links
  5. Mark bounce_wa_sent=True on ACK record after successful send
  6. 120s anti-spam between sends

Usage:
  python3 send_vote_wa_reminder.py            # dry run (default)
  python3 send_vote_wa_reminder.py --live     # actually send
  python3 send_vote_wa_reminder.py --phone 584XXXXXXXXX --live  # single test
"""

import argparse
import json
import logging
import os
import sys
import time
import xmlrpc.client
from datetime import datetime

import requests

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR     = os.path.join(SCRIPT_DIR, '..', 'config')
PROD_CFG_FILE  = os.path.join(CONFIG_DIR, 'production.json')
WA_CFG_FILE    = os.path.join(CONFIG_DIR, 'whatsapp_massiva.json')
GSHEET_CREDS   = os.path.join(CONFIG_DIR, 'google_sheets_credentials.json')

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
NOTICE_KEY        = 'budget_consulta_2026_2027'
PDVSA_NOTICE_KEY  = 'pdvsa_continuacion_2026_2027'
ODOO_BASE_URL  = 'https://odoo.ueipab.edu.ve'

ANTISPAM_SECS  = 122  # slightly over 120s for safety

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_wa_config():
    cfg = json.load(open(WA_CFG_FILE))
    primary = next(a for a in cfg['whatsapp_accounts'] if a.get('primary'))
    return {
        'secret':     cfg['api']['secret'],
        'account_id': primary['unique_id'],
        'base_url':   cfg['api']['base_url'],
    }


def load_odoo():
    cfg = json.load(open(PROD_CFG_FILE))['production']['xmlrpc']
    url, db, user, key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
    uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return db, uid, key, models


def load_sheet_recipients():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        GSHEET_CREDS, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute().get('values', [])
    data = rows[1:]  # row 2 is header

    recipients = []
    for row in data:
        r = (row + [''] * 13)[:13]
        name   = r[1].strip()
        status = r[2].strip().upper()
        emails_raw = r[9].strip()
        phone  = r[11].strip()
        if not name or status != 'ACTIVE':
            continue
        emails = [e.strip().lower() for e in emails_raw.split(';') if e.strip()]
        recipients.append({'name': name, 'emails': emails, 'phone': phone})

    log.info("Sheet: %d ACTIVE rows loaded", len(recipients))
    return recipients


def load_acks(db, uid, key, models):
    acks = models.execute_kw(db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', NOTICE_KEY]]],
        {'fields': ['id', 'partner_email', 'partner_phone', 'partner_name',
                    'state', 'token', 'bounce_wa_sent'], 'limit': 0})
    by_email, by_phone = {}, {}
    for a in acks:
        if a.get('partner_email'):
            for em in a['partner_email'].lower().split(';'):
                by_email[em.strip()] = a
        if a.get('partner_phone'):
            by_phone[a['partner_phone'].strip()] = a
    log.info("Odoo ACKs: %d records loaded", len(acks))
    return by_email, by_phone


def load_pdvsa_excluded_phones(db, uid, key, models):
    """
    Return set of phones for PDVSA families that have NOT confirmed continuity.
    These families are uncertain/leaving — no point spending WA tokens on them
    for the budget vote since they may not be at the school next year.
    Only PDVSA families with state='continuing' are safe to include.
    """
    pdvsa_acks = models.execute_kw(db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', PDVSA_NOTICE_KEY]]],
        {'fields': ['partner_phone', 'partner_email', 'partner_name', 'state'], 'limit': 0})

    excluded_phones = set()
    excluded_emails = set()
    excluded_count  = 0
    for a in pdvsa_acks:
        if a['state'] == 'leaving':   # confirmed not returning next year
            if a.get('partner_phone'):
                excluded_phones.add(a['partner_phone'].strip())
            if a.get('partner_email'):
                for em in a['partner_email'].lower().split(';'):
                    excluded_emails.add(em.strip())
            log.info("PDVSA exclude (%s): %s", a['state'], a.get('partner_name','?'))
            excluded_count += 1

    confirmed_count = sum(1 for a in pdvsa_acks if a['state'] == 'continuing')
    log.info("PDVSA: %d leaving (exclude) | %d continuing+pending (include)",
             excluded_count, len(pdvsa_acks) - excluded_count)
    return excluded_phones, excluded_emails


# ── Build blast list ──────────────────────────────────────────────────────────

def build_blast_list(sheet_rows, ack_by_email, ack_by_phone,
                     pdvsa_excl_phones, pdvsa_excl_emails,
                     followup=False, target_phone=None):
    to_blast = []
    skipped_voted, skipped_wa_done, skipped_no_ack, skipped_pdvsa = 0, 0, 0, 0

    for sr in sheet_rows:
        if target_phone and sr['phone'] != target_phone:
            continue

        # Exclude PDVSA families that confirmed leaving
        if sr['phone'] in pdvsa_excl_phones:
            skipped_pdvsa += 1
            continue
        if any(em in pdvsa_excl_emails for em in sr['emails']):
            skipped_pdvsa += 1
            continue

        # Match budget vote ACK record
        ack = None
        for em in sr['emails']:
            if em in ack_by_email:
                ack = ack_by_email[em]
                break
        if not ack and sr['phone'] in ack_by_phone:
            ack = ack_by_phone[sr['phone']]

        if not ack:
            log.warning("No ACK found for %s (phone=%s) — skipping", sr['name'], sr['phone'])
            skipped_no_ack += 1
            continue

        if ack['state'] in ('continuing', 'leaving'):
            skipped_voted += 1
            continue

        if not ack.get('token'):
            log.warning("No token on ACK id=%s for %s — skipping", ack['id'], sr['name'])
            continue

        if followup:
            # Follow-up: only those who already got the first WA and still haven't voted
            if not ack.get('bounce_wa_sent'):
                continue
        else:
            # Initial blast: skip anyone who already received the first WA
            if ack.get('bounce_wa_sent'):
                skipped_wa_done += 1
                continue

        to_blast.append({
            'name':    sr['name'],
            'phone':   sr['phone'],
            'token':   ack['token'],
            'ack_id':  ack['id'],
        })

    mode = "follow-up" if followup else "initial"
    log.info(
        "[%s] Blast list: %d to send | %d voted | %d WA done | %d PDVSA-excl | %d no ACK",
        mode, len(to_blast), skipped_voted, skipped_wa_done, skipped_pdvsa, skipped_no_ack,
    )
    return to_blast


# ── Message builder ───────────────────────────────────────────────────────────

def build_message(name, token):
    first = name.split()[0].capitalize()
    link_a   = f'{ODOO_BASE_URL}/partner-ack/{token}/si'
    link_b   = f'{ODOO_BASE_URL}/partner-ack/{token}/no'
    slides   = 'https://docs.google.com/presentation/d/16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA'
    telegram = 'https://t.me/GlendaUeipabBot'
    return (
        f"Hola {first} 👋\n\n"
        f"Soy *Glenda*, la asistente virtual del Colegio Andrés Bello.\n\n"
        f"Le escribimos gentilmente para informarle que ya puede votar sobre la "
        f"*Consulta Presupuestaria 2026-2027* y nos gustaría contar con su participación "
        f"mediante el voto.\n\n"
        f"📊 Puede revisar la propuesta completa aquí:\n{slides}\n\n"
        f"¿Desea votar ahora? Seleccione su preferencia:\n\n"
        f"✅ *Opción A* — $218.88/mes\n{link_a}\n\n"
        f"✅ *Opción B* — $236.58/mes\n{link_b}\n\n"
        f"⏰ La consulta cierra el *26 de mayo a las 12:30pm*.\n\n"
        f"¿Tiene preguntas? Estoy disponible en Telegram para una respuesta más rápida 👇\n"
        f"{telegram}\n\n"
        f"¡Gracias por su participación! 🙏"
    )


def build_followup_message(name, token):
    """Shorter nudge for parents who received the first blast but haven't voted yet."""
    first  = name.split()[0].capitalize()
    link_a = f'{ODOO_BASE_URL}/partner-ack/{token}/si'
    link_b = f'{ODOO_BASE_URL}/partner-ack/{token}/no'
    return (
        f"Hola {first} 👋 Soy *Glenda* del Colegio Andrés Bello.\n\n"
        f"Le recuerdo que su voto en la *Consulta Presupuestaria* "
        f"aún está pendiente. ¡Queda poco tiempo!\n\n"
        f"⏰ *Cierra el 26 de mayo a las 12:30pm*\n\n"
        f"Vote aquí:\n"
        f"✅ *Opción A* — $218.88/mes\n{link_a}\n\n"
        f"✅ *Opción B* — $236.58/mes\n{link_b}\n\n"
        f"¡Gracias! 🙏"
    )


# ── WA send ───────────────────────────────────────────────────────────────────

def send_whatsapp(wa_cfg, phone, message, dry_run):
    if dry_run:
        return True
    url  = wa_cfg['base_url'].rstrip('/') + '/send/whatsapp'
    data = {
        'secret':    wa_cfg['secret'],
        'account':   wa_cfg['account_id'],
        'recipient': phone,
        'type':      'text',
        'message':   message,
    }
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('status') == 200:
            return True
        log.error("WA API error for %s: %s", phone, result.get('message', 'unknown'))
        return False
    except requests.RequestException as e:
        log.error("WA send failed for %s: %s", phone, e)
        return False


def mark_wa_sent(db, uid, key, models, ack_id, dry_run):
    if dry_run:
        return
    models.execute_kw(db, uid, key, 'partner.communication.ack', 'write',
        [[ack_id], {'bounce_wa_sent': True}])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Vote WA reminder blast')
    parser.add_argument('--live',     action='store_true', help='Actually send (default: dry run)')
    parser.add_argument('--followup', action='store_true', help='Follow-up mode: nudge those who got 1st WA but still pending')
    parser.add_argument('--phone',    metavar='584XXXXXXXXX', help='Test single phone number')
    args = parser.parse_args()

    dry_run = not args.live
    mode_label = "FOLLOW-UP" if args.followup else "INITIAL BLAST"
    if dry_run:
        log.info("=== DRY RUN [%s] — pass --live to send ===", mode_label)
    else:
        log.info("=== LIVE MODE [%s] ===", mode_label)

    wa_cfg                        = load_wa_config()
    db, uid, key, models          = load_odoo()
    sheet_rows                    = load_sheet_recipients()
    ack_by_email, ack_by_phone    = load_acks(db, uid, key, models)
    pdvsa_excl_ph, pdvsa_excl_em  = load_pdvsa_excluded_phones(db, uid, key, models)
    to_blast                      = build_blast_list(
        sheet_rows, ack_by_email, ack_by_phone,
        pdvsa_excl_ph, pdvsa_excl_em,
        followup=args.followup,
        target_phone=args.phone,
    )

    if not to_blast:
        log.info("Nothing to send. Done.")
        return

    total    = len(to_blast)
    eta_mins = (total * ANTISPAM_SECS) // 60
    log.info("Will send %d messages — estimated time: ~%dh %dmin",
             total, eta_mins // 60, eta_mins % 60)

    if not dry_run:
        log.info("Starting in 5s — Ctrl+C to abort...")
        time.sleep(5)

    msg_builder = build_followup_message if args.followup else build_message

    sent_ok, sent_fail = 0, 0
    for i, entry in enumerate(to_blast, 1):
        name, phone, token, ack_id = entry['name'], entry['phone'], entry['token'], entry['ack_id']
        msg = msg_builder(name, token)

        log.info("[%d/%d] %s — %s", i, total, name, phone)
        if dry_run:
            log.info("  DRY  message preview:\n%s", msg[:200] + "...")
        else:
            log.info("  SEND → %s", phone)

        ok = send_whatsapp(wa_cfg, phone, msg, dry_run)
        if ok:
            mark_wa_sent(db, uid, key, models, ack_id, dry_run)
            sent_ok += 1
        else:
            sent_fail += 1

        # Anti-spam wait between sends (skip after last)
        if i < total and not dry_run:
            log.info("  Waiting %ds anti-spam...", ANTISPAM_SECS)
            time.sleep(ANTISPAM_SECS)

    log.info("Done — sent: %d | failed: %d | dry_run: %s", sent_ok, sent_fail, dry_run)


if __name__ == '__main__':
    main()
