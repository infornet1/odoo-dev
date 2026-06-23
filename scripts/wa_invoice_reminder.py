#!/usr/bin/env python3
"""
WA Invoice Reminder — Representante / Representante PDVSA

Sends a daily WhatsApp balance reminder to customers with outstanding invoices,
segmented by partner tag:

  Representante (tag 25):
    "Colegio Andrés Bello informa su saldo de cuotas pendiente por ref $X.XX USD
     pagaderos a la tasa BCV oficial https://bit.ly/tasabcv

     Este es un gentil recordatorio automático enviado desde nuestro sistema de cobranzas"

  Representante PDVSA (tag 26):
    Same but with an extra line about the current month's invoice and 35% advance.
    Partners with ANY outstanding fiscal_check=True invoice are excluded entirely.

Phone source:   Google Sheets Customers tab, column L (authoritative)
Sheet filter:   Column C in {ACTIVE, PENDING} AND Q=YES AND R=YES
Balance filter: sum(amount_residual_signed) >= $1.00 USD
Dedup:          State file — skip partner if already sent today (idempotent re-runs)
Anti-spam:      120–140s random delay between sends (MassivaMóvil recommendation)

Usage:
    python3 scripts/wa_invoice_reminder.py              # dry run
    python3 scripts/wa_invoice_reminder.py --live       # send to production
    python3 scripts/wa_invoice_reminder.py --live --partner-vat V14133887  # single test
"""

import argparse
import json
import logging
import os
import random
import sys
import time
import xmlrpc.client
from collections import defaultdict
from datetime import date, datetime, timedelta

import gspread
import requests
from google.oauth2.service_account import Credentials

# ============================================================================
# Config
# ============================================================================

SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE    = os.path.join(SCRIPT_DIR, '..', 'config', 'production.json')
WA_CONFIG_FILE = os.path.join(SCRIPT_DIR, '..', 'config', 'whatsapp_massiva.json')
SHEETS_CREDS   = os.path.join(SCRIPT_DIR, '..', 'config', 'google_sheets_credentials.json')
STATE_FILE     = os.path.join(SCRIPT_DIR, 'wa_invoice_reminder_state.json')

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
SHEET_TAB      = 'Customers'

TAG_REPRESENTANTE       = 25
TAG_REPRESENTANTE_PDVSA = 26
TAG_VIP                 = 30   # VIP customers — excluded from automated sends

# Ad-hoc mode: the Odoo wizard ("Enviar WA") writes this param with the EXACT
# selected list (partner + Odoo mobile + tag). With --adhoc we send that list
# verbatim instead of the tag-based / Sheets-phone logic.
ADHOC_PARAM   = 'wa_invoice_reminder.adhoc_payload'
# Global WA pause switch (shared with Glenda). When True, even --live is forced
# to dry-run so the armed wizard button can't fire while WA is paused.
WA_PAUSE_PARAM = 'ai_agent.dry_run'

MIN_BALANCE_USD  = 1.00   # skip near-zero rounding residuals
ANTI_SPAM_MIN    = 120    # seconds
ANTI_SPAM_MAX    = 140

MONTHS_ES = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
}

TEMPLATE_REP = (
    "Colegio Andrés Bello le informa que su saldo pendiente es de {deuda}. "
    "Le invitamos a protegerse de la volatilidad cambiaria pagando a la tasa "
    "BCV oficial, la cual puede consultar en nuestro monitor https://bit.ly/tasabcv\n\n"
    "Este es un gentil recordatorio automático de nuestro sistema de cobranzas"
)

TEMPLATE_PDVSA = (
    "Colegio Andrés Bello informa que su factura del mes de {last_month_es} esta lista, "
    "le invitamos a protegerse de volatividad cambiaria en adelantar el 35% de su factura, "
    "su saldo de cuotas pendiente por ref {deuda} pagaderos a la tasa BCV oficial "
    "https://bit.ly/tasabcv\n\n"
    "Este es un gentil recordatorio automático enviado desde nuestro sistema de cobranzas"
)

# ============================================================================
# Logging
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)

# ============================================================================
# State
# ============================================================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'partners': {}, 'last_run': None}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def already_sent_today(state, partner_id):
    entry = state['partners'].get(str(partner_id))
    if not entry:
        return False
    return entry.get('last_sent') == str(date.today())


def mark_sent(state, partner_id, balance):
    state['partners'][str(partner_id)] = {
        'last_sent':    str(date.today()),
        'last_balance': round(balance, 2),
    }

# ============================================================================
# Helpers
# ============================================================================

def fmt_usd(amount):
    return f'${amount:,.2f} USD'


def last_month_es():
    """Return the Spanish name of the previous calendar month."""
    first_of_this_month = date.today().replace(day=1)
    prev_month = (first_of_this_month - timedelta(days=1)).month
    return MONTHS_ES[prev_month]


def normalise_phone(raw):
    return ''.join(c for c in str(raw or '') if c.isdigit())

# ============================================================================
# Step 1 — Load WA config
# ============================================================================

def load_wa_config():
    with open(WA_CONFIG_FILE) as f:
        cfg = json.load(f)
    accounts = cfg.get('whatsapp_accounts', [])
    primary  = next((a for a in accounts if a.get('primary')), accounts[0])
    return {
        'secret':     cfg['api']['secret'],
        'account_id': primary['unique_id'],
        'base_url':   cfg['api']['base_url'],
    }

# ============================================================================
# Step 2 — Load Google Sheets eligible phones
# ============================================================================

def load_sheet_phones():
    """Return dict: vat_upper -> phone ('+58...')"""
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds  = Credentials.from_service_account_file(SHEETS_CREDS, scopes=scopes)
    gc     = gspread.authorize(creds)
    ws     = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_TAB)
    rows   = ws.get_all_values()[2:]

    result = {}
    for row in rows:
        if len(row) < 12:
            continue
        vat    = row[0].strip().upper()
        status = row[2].strip().upper()
        col_l  = row[11].strip()
        col_q  = row[16].strip().upper() if len(row) > 16 else ''
        col_r  = row[17].strip().upper() if len(row) > 17 else ''

        if not vat or not col_l:
            continue
        if status not in ('ACTIVE', 'PENDING'):
            continue
        if col_q != 'YES' or col_r != 'YES':
            continue

        digits = normalise_phone(col_l)
        if digits:
            result[vat] = f'+{digits}'

    return result

# ============================================================================
# Step 3 — Load Odoo partners + invoice balances
# ============================================================================

def odoo_connect():
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    return cfg['db'], uid, cfg['api_key'], models


def load_partners_with_balances(db, uid, pw, models, vat_filter=None):
    """
    Returns list of dicts:
      {id, name, vat, tags, balance, skip_reason}

    skip_reason is set (and balance=0) when:
      - balance < MIN_BALANCE_USD
      - PDVSA partner has any fiscal_check=True outstanding invoice (Option A)
    """
    domain = [
        ('category_id', 'in', [TAG_REPRESENTANTE, TAG_REPRESENTANTE_PDVSA]),
        ('active', '=', True),
    ]
    if vat_filter:
        domain.append(('vat', 'in', vat_filter))

    partners = models.execute_kw(db, uid, pw, 'res.partner', 'search_read',
        [domain], {'fields': ['id', 'name', 'vat', 'category_id'], 'limit': 0})

    if not partners:
        return []

    partner_ids  = [p['id'] for p in partners]
    partner_map  = {p['id']: p for p in partners}

    # Employee VATs — partners whose cedula matches an active employee are excluded
    employees = models.execute_kw(db, uid, pw, 'hr.employee', 'search_read',
        [[('active', '=', True), ('identification_id', '!=', False)]],
        {'fields': ['identification_id'], 'limit': 0})
    employee_vats = {(e['identification_id'] or '').strip().upper() for e in employees}

    # All unpaid posted invoices — for balance aggregation
    invoices = models.execute_kw(db, uid, pw, 'account.move', 'search_read',
        [[
            ('partner_id',    'in', partner_ids),
            ('move_type',     'in', ['out_invoice', 'out_receipt']),
            ('state',         '=',  'posted'),
            ('payment_state', 'not in', ['paid', 'reversed']),
        ]],
        {'fields': ['partner_id', 'amount_residual_signed', 'invoice_date'], 'limit': 0})

    # All posted invoices (paid or not) — to find the latest invoice per PDVSA partner
    all_posted = models.execute_kw(db, uid, pw, 'account.move', 'search_read',
        [[
            ('partner_id', 'in', partner_ids),
            ('move_type',  'in', ['out_invoice', 'out_receipt']),
            ('state',      '=',  'posted'),
        ]],
        {'fields': ['partner_id', 'fiscal_check', 'invoice_date',
                    'amount_total', 'amount_residual', 'payment_state'], 'limit': 0})

    # Aggregate unpaid balance per partner
    balance_map = defaultdict(float)
    for inv in invoices:
        balance_map[inv['partner_id'][0]] += inv['amount_residual_signed']

    # Find latest posted invoice per partner → determines fiscal exclusion + month context
    latest_inv_map = {}   # pid -> {invoice_date, fiscal_check, amount_total, amount_residual, payment_state}
    for inv in all_posted:
        pid = inv['partner_id'][0]
        d   = inv.get('invoice_date') or ''
        if d > latest_inv_map.get(pid, {}).get('invoice_date', ''):
            latest_inv_map[pid] = {
                'invoice_date':    d,
                'fiscal_check':    inv.get('fiscal_check', False),
                'amount_total':    inv.get('amount_total') or 0.0,
                'amount_residual': inv.get('amount_residual') or 0.0,
                'payment_state':   inv.get('payment_state', ''),
            }

    results = []
    for p in partners:
        pid  = p['id']
        vat  = (p.get('vat') or '').strip().upper()
        tags = p.get('category_id') or []
        is_pdvsa = TAG_REPRESENTANTE_PDVSA in tags
        balance  = balance_map.get(pid, 0.0)

        # Exclude VIP customers — handled manually, not via automated blast
        if TAG_VIP in tags:
            results.append({
                'id': pid, 'name': p['name'], 'vat': vat,
                'is_pdvsa': is_pdvsa, 'balance': balance,
                'skip_reason': 'VIP_EXCLUDED',
            })
            continue

        # Exclude partners who are also active employees (match by VAT = identification_id)
        if vat and vat in employee_vats:
            results.append({
                'id': pid, 'name': p['name'], 'vat': vat,
                'is_pdvsa': is_pdvsa, 'balance': balance,
                'skip_reason': 'IS_EMPLOYEE',
            })
            continue

        # PDVSA exclusion rules (check latest posted invoice):
        #   1. fiscal_check=True → PDVSA company covering this invoice
        #   2. payment_state=partial AND paid ≥ 30% of invoice → customer already advanced ~35%
        if is_pdvsa:
            latest = latest_inv_map.get(pid, {})
            excl_reason = None

            if latest.get('fiscal_check', False):
                excl_reason = 'PDVSA_FISCAL_EXCLUDED'
            elif latest.get('payment_state') == 'partial':
                total = latest.get('amount_total') or 0.0
                residual = latest.get('amount_residual') or 0.0
                paid_pct = ((total - residual) / total * 100) if total > 0 else 0
                if paid_pct >= 30.0:
                    excl_reason = 'PDVSA_ADVANCE_PAID'

            if excl_reason:
                results.append({
                    'id': pid, 'name': p['name'], 'vat': vat,
                    'is_pdvsa': is_pdvsa, 'balance': balance,
                    'skip_reason': excl_reason,
                })
                continue

        if balance < MIN_BALANCE_USD:
            results.append({
                'id': pid, 'name': p['name'], 'vat': vat,
                'is_pdvsa': is_pdvsa, 'balance': balance,
                'skip_reason': 'BELOW_THRESHOLD',
            })
            continue

        # For PDVSA: use the latest invoice's month for the message context
        if is_pdvsa:
            latest = latest_inv_map.get(pid, {})
            inv_date_str = latest.get('invoice_date') or ''
            if inv_date_str:
                inv_month = int(inv_date_str[5:7])
            else:
                first_of_this_month = date.today().replace(day=1)
                inv_month = (first_of_this_month - timedelta(days=1)).month
            invoice_month_es = MONTHS_ES[inv_month]
        else:
            invoice_month_es = None

        results.append({
            'id': pid, 'name': p['name'], 'vat': vat,
            'is_pdvsa': is_pdvsa, 'balance': balance,
            'invoice_month_es': invoice_month_es,
            'skip_reason': None,
        })

    return results

# ============================================================================
# Step 4 — Build send list
# ============================================================================

def get_param(db, uid, pw, models, key):
    rows = models.execute_kw(db, uid, pw, 'ir.config_parameter', 'search_read',
        [[['key', '=', key]]], {'fields': ['id', 'value'], 'limit': 1})
    if not rows:
        return None, None
    return rows[0]['id'], rows[0]['value']


def load_adhoc_payload(db, uid, pw, models):
    """Read + clear (consume-once) the wizard's ad-hoc payload param.

    Returns a list of items: {partner_id, name, phone, balance, is_pdvsa, month}.
    Clearing immediately mirrors the poller's handling of trigger_at and
    prevents a stale payload from being re-sent on a later run.
    """
    pid, value = get_param(db, uid, pw, models, ADHOC_PARAM)
    if pid:
        models.execute_kw(db, uid, pw, 'ir.config_parameter', 'write',
            [[pid], {'value': ''}])
    if not value:
        return None
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        log.error("Ad-hoc payload is not valid JSON — ignoring.")
        return None


def build_adhoc_send_list(payload, state):
    """Turn the wizard payload into the send-list shape, applying same-day dedup."""
    to_send, skipped = [], []
    for item in payload or []:
        pid   = item.get('partner_id')
        phone = item.get('phone')
        if not phone:
            skipped.append({**item, 'name': item.get('name', ''), 'reason': 'NO_PHONE'})
            continue
        if already_sent_today(state, pid):
            skipped.append({**item, 'name': item.get('name', ''),
                            'reason': 'ALREADY_SENT_TODAY'})
            continue
        month = item.get('month')
        to_send.append({
            'id':               pid,
            'name':             item.get('name', ''),
            'vat':              '',
            'is_pdvsa':         bool(item.get('is_pdvsa')),
            'balance':          float(item.get('balance') or 0.0),
            'invoice_month_es': MONTHS_ES.get(month) if month else last_month_es(),
            'phone':            phone,
            'skip_reason':      None,
        })
    return to_send, skipped


def build_send_list(partners, sheet_phones, state):
    """Cross-reference partners with sheet phones, apply dedup. Returns (to_send, skipped)."""
    to_send = []
    skipped = []

    for p in partners:
        vat = p['vat']

        if p['skip_reason']:
            skipped.append({**p, 'reason': p['skip_reason']})
            continue

        phone = sheet_phones.get(vat)
        if not phone:
            skipped.append({**p, 'reason': 'NO_PHONE_IN_SHEET'})
            continue

        if already_sent_today(state, p['id']):
            skipped.append({**p, 'reason': 'ALREADY_SENT_TODAY'})
            continue

        to_send.append({**p, 'phone': phone})

    return to_send, skipped

# ============================================================================
# Step 5 — Build message
# ============================================================================

def build_message(partner):
    deuda = fmt_usd(partner['balance'])
    if partner['is_pdvsa']:
        return TEMPLATE_PDVSA.format(last_month_es=partner['invoice_month_es'], deuda=deuda)
    return TEMPLATE_REP.format(deuda=deuda)

# ============================================================================
# Step 6 — Chatter logging
# ============================================================================

def log_chatter(db, uid, pw, models, partner_id, partner, dry_run):
    """Post an internal note on the partner's chatter after a successful WA send."""
    if dry_run:
        return
    tag_label = 'Representante PDVSA' if partner['is_pdvsa'] else 'Representante'
    body = (
        f'<p>📨 <b>WA reminder sent</b> — '
        f'Balance <b>{fmt_usd(partner["balance"])}</b> '
        f'({tag_label}) via Glenda (+584148321989)</p>'
    )
    try:
        models.execute_kw(db, uid, pw, 'res.partner', 'message_post',
            [[partner_id]],
            {'body': body, 'message_type': 'comment', 'subtype_xmlid': 'mail.mt_note'})
    except Exception as e:
        log.warning("Chatter log failed for %s: %s", partner['name'], e)


# ============================================================================
# Step 7 — Send
# ============================================================================

def get_ceo_phone(db, uid, pw, models):
    rows = models.execute_kw(db, uid, pw, 'ir.config_parameter', 'search_read',
        [[['key', '=', 'wa_monitor.ceo_phone']]], {'fields': ['value'], 'limit': 1})
    return rows[0]['value'] if rows and rows[0]['value'] else ''


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

# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='WA Invoice Reminder — daily blast')
    parser.add_argument('--live', action='store_true',
                        help='Send messages (default: dry run)')
    parser.add_argument('--partner-vat', metavar='VAT',
                        help='Limit to a single partner VAT for testing')
    parser.add_argument('--adhoc', action='store_true',
                        help='Send the wizard ad-hoc payload (exact selected list) '
                             'instead of the tag-based daily blast')
    args   = parser.parse_args()
    dry_run = not args.live

    print("=" * 80)
    print(f"  WA INVOICE REMINDER{'  [AD-HOC / wizard list]' if args.adhoc else ''}")
    print(f"  Date:  {date.today()}")
    print(f"  Mode:  {'*** DRY RUN ***' if dry_run else '*** LIVE — sending via MassivaMóvil ***'}")
    print("=" * 80)

    log.info("Loading WA config...")
    wa_cfg = load_wa_config()

    log.info("Connecting to Odoo production...")
    db, uid, pw, models = odoo_connect()
    ceo_phone = get_ceo_phone(db, uid, pw, models)

    # Global WA pause: if WhatsApp is paused system-wide, force dry-run so the
    # wizard's (now armed) WA button cannot fire real sends while paused.
    if not dry_run:
        _, paused = get_param(db, uid, pw, models, WA_PAUSE_PARAM)
        if str(paused) == 'True':
            log.warning("WA is paused globally (%s=True) — forcing DRY RUN.", WA_PAUSE_PARAM)
            dry_run = True

    log.info("Loading state file...")
    state = load_state()

    if args.adhoc:
        log.info("Loading ad-hoc payload from wizard...")
        payload = load_adhoc_payload(db, uid, pw, models)
        if not payload:
            print("\n  No ad-hoc payload to send. Exiting.")
            return
        log.info("  %d partners in payload", len(payload))
        to_send, skipped = build_adhoc_send_list(payload, state)
    else:
        log.info("Loading Google Sheets eligible phones...")
        sheet_phones = load_sheet_phones()
        log.info("  %d eligible rows with phone", len(sheet_phones))

        vat_filter = [args.partner_vat.strip().upper()] if args.partner_vat else None
        log.info("Loading partners + invoice balances...")
        partners = load_partners_with_balances(db, uid, pw, models, vat_filter=vat_filter)
        log.info("  %d tagged partners loaded", len(partners))

        log.info("Building send list...")
        to_send, skipped = build_send_list(partners, sheet_phones, state)

    # ── Print plan ──────────────────────────────────────────────────────────

    print(f"\n  TO SEND ({len(to_send)}):")
    if to_send:
        print(f"  {'Name':<42} {'VAT':<14} {'Tag':<8} {'Balance':>12}  {'Phone'}")
        print("  " + "-" * 90)
        for p in sorted(to_send, key=lambda x: x['name']):
            tag = 'PDVSA' if p['is_pdvsa'] else 'REP'
            print(f"  {p['name']:<42} {p['vat']:<14} {tag:<8} {fmt_usd(p['balance']):>12}  {p['phone']}")

    if skipped:
        skip_groups = defaultdict(list)
        for s in skipped:
            skip_groups[s['reason']].append(s)

        print(f"\n  SKIPPED ({len(skipped)}):")
        for reason, group in sorted(skip_groups.items()):
            print(f"    {reason:<30} {len(group):>3}")

    total_balance = sum(p['balance'] for p in to_send)
    print(f"\n  Total outstanding (to send): {fmt_usd(total_balance)}")
    print(f"  Anti-spam delay: {ANTI_SPAM_MIN}–{ANTI_SPAM_MAX}s between sends")
    eta_min = len(to_send) * ANTI_SPAM_MIN // 60
    eta_max = len(to_send) * ANTI_SPAM_MAX // 60
    print(f"  Estimated run time: {eta_min}–{eta_max} min")

    if dry_run:
        print("\n  Dry run complete. Run with --live to send.")
        return

    if not to_send:
        print("\n  Nothing to send today.")
        return

    # ── Send ────────────────────────────────────────────────────────────────

    print(f"\n  Sending {len(to_send)} messages...\n")

    if ceo_phone:
        now_vet = datetime.now().strftime('%H:%M')
        send_whatsapp(wa_cfg, ceo_phone,
            f"🚀 WA Blast iniciado\n"
            f"📋 {len(to_send)} partners | ⏰ {now_vet} VET\n"
            f"💰 {fmt_usd(total_balance)} total pendiente\n"
            f"⏱️ ~{eta_min}–{eta_max} min",
            dry_run)
    sent = errors = 0

    for i, p in enumerate(to_send, 1):
        message = build_message(p)
        success = send_whatsapp(wa_cfg, p['phone'], message, dry_run)

        if success:
            mark_sent(state, p['id'], p['balance'])
            log_chatter(db, uid, pw, models, p['id'], p, dry_run)
            sent += 1
            tag = 'PDVSA' if p['is_pdvsa'] else 'REP '
            log.info("[%d/%d] SENT  [%s] %s  %s  %s",
                     i, len(to_send), tag, p['name'], fmt_usd(p['balance']), p['phone'])
        else:
            errors += 1
            log.error("[%d/%d] FAIL  %s  %s", i, len(to_send), p['name'], p['phone'])

        # Save state after each send so a crash doesn't lose progress
        state['last_run'] = datetime.now().isoformat()
        save_state(state)

        # Anti-spam delay (skip after last send)
        if i < len(to_send):
            delay = random.randint(ANTI_SPAM_MIN, ANTI_SPAM_MAX)
            log.info("  Waiting %ds before next send...", delay)
            time.sleep(delay)

    state['last_run'] = datetime.now().isoformat()
    save_state(state)

    if ceo_phone:
        send_whatsapp(wa_cfg, ceo_phone,
            f"{'✅' if not errors else '⚠️'} WA Blast completado\n"
            f"✓ Enviados: {sent}/{len(to_send)}\n"
            f"✗ Errores: {errors}\n"
            f"○ Omitidos: {len(skipped)}",
            dry_run)

    print(f"\n{'=' * 80}")
    print(f"  Done — {sent} sent, {errors} errors, {len(skipped)} skipped")
    print(f"{'=' * 80}")

    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
