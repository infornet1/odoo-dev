#!/usr/bin/env python3
"""
wa_primary_relay.py
───────────────────
Holding-pattern relay for when the primary WA number (+584148321989) can
receive but not send.

Every run:
  1. Polls the primary inbox via MassivaMóvil API
  2. For each new inbound message (not yet processed), sends a gentle redirect
     via the backup number (+584248944898) including a Telegram invite
  3. Records processed message IDs in state file to avoid duplicate replies

Usage:
    python3 scripts/wa_primary_relay.py            # dry-run
    python3 scripts/wa_primary_relay.py --live     # actually send

Cron (every 5 min, same as WA poll):
    */5 * * * * root python3 /opt/odoo-dev/scripts/wa_primary_relay.py --live \
        >> /var/log/wa_primary_relay.log 2>&1
"""

import argparse, json, logging, os, sys
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger(__name__)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
STATE_FILE  = os.path.join(SCRIPT_DIR, 'wa_primary_relay_state.json')
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'production.json'))

# Message to send — redirect + Telegram invite
RELAY_MESSAGE = (
    "Hola 👋 Nuestro número principal está en mantenimiento técnico en este momento.\n\n"
    "Tu mensaje fue recibido y te respondemos desde nuestro número de respaldo.\n\n"
    "📲 *¿Quieres respuestas más rápidas?*\n"
    "Únete a Glenda en Telegram — sin esperas, disponible 24/7:\n"
    "👉 https://t.me/GlendaUeipabBot\n\n"
    "También puedes escribirnos directamente a este número en el futuro. 😊"
)

# Skip replies to these senders (internal numbers, other WA accounts)
SKIP_SENDERS = {
    '584148321989',   # primary itself
    '584248944898',   # backup
    '584148321963',   # tertiary
}


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_config():
    import xmlrpc.client
    cfg = json.load(open(CONFIG_PATH))['production']['xmlrpc']
    url, db, user, key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid    = common.authenticate(db, user, key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

    params = models.execute_kw(db, uid, key, 'ir.config_parameter', 'search_read',
        [[['key', 'in', [
            'ai_agent.whatsapp_api_secret',
            'ai_agent.whatsapp_base_url',
            'ai_agent.whatsapp_primary_unique_id',
            'ai_agent.whatsapp_backup_unique_id',
        ]]]],
        {'fields': ['key', 'value']})
    return {p['key']: p['value'] for p in params}


# ── State ───────────────────────────────────────────────────────────────────────

def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {'processed_ids': [], 'replied_phones': {}}


def save_state(state):
    # Keep only last 500 processed IDs to avoid unbounded growth
    state['processed_ids'] = state['processed_ids'][-500:]
    json.dump(state, open(STATE_FILE, 'w'), indent=2)


# ── Main ────────────────────────────────────────────────────────────────────────

def _known_school_phones(models, db, uid, key):
    """Return set of normalized phones for all school partners (res.partner)."""
    partners = models.execute_kw(db, uid, key, 'res.partner', 'search_read',
        [[['phone', '!=', False]]],
        {'fields': ['phone', 'mobile'], 'limit': 2000})
    phones = set()
    for p in partners:
        for f in ('phone', 'mobile'):
            v = (p.get(f) or '').replace('+', '').replace(' ', '').replace('-', '')
            if v: phones.add(v)
    return phones


def _glenda_conv_phones(models, db, uid, key):
    """Return set of normalized phones from any Glenda conversation (all states)."""
    convs = models.execute_kw(db, uid, key, 'ai.agent.conversation', 'search_read',
        [[['phone', '!=', False], ['channel', '=', 'whatsapp']]],
        {'fields': ['phone'], 'limit': 2000})
    return {(c['phone'] or '').replace('+','').replace(' ','') for c in convs if c.get('phone')}


def main(live: bool):
    import xmlrpc.client
    cfg   = _load_config()
    base  = cfg['ai_agent.whatsapp_base_url']
    sec   = cfg['ai_agent.whatsapp_api_secret']
    puid  = cfg['ai_agent.whatsapp_primary_unique_id']
    buid  = cfg['ai_agent.whatsapp_backup_unique_id']

    # Connect Odoo for partner lookup
    prod_cfg = json.load(open(CONFIG_PATH))['production']['xmlrpc']
    common   = xmlrpc.client.ServerProxy(f'{prod_cfg["url"]}/xmlrpc/2/common')
    uid_odoo = common.authenticate(prod_cfg['db'], prod_cfg['user'], prod_cfg['api_key'], {})
    models   = xmlrpc.client.ServerProxy(f'{prod_cfg["url"]}/xmlrpc/2/object')

    known_phones = _known_school_phones(models, prod_cfg['db'], uid_odoo, prod_cfg['api_key'])
    conv_phones  = _glenda_conv_phones(models, prod_cfg['db'], uid_odoo, prod_cfg['api_key'])
    eligible     = known_phones | conv_phones
    log.info("Eligible senders (partners + Glenda convs): %d", len(eligible))

    state     = load_state()
    processed = set(state.get('processed_ids', []))
    replied   = state.get('replied_phones', {})  # phone → last replied msg id

    # Poll primary inbox
    r = requests.get(f'{base}/get/wa.received',
        params={'secret': sec, 'account': puid, 'limit': 50}, timeout=15)
    msgs = r.json().get('data', [])
    log.info("Primary inbox: %d messages fetched", len(msgs))

    sent = 0
    for m in msgs:
        msg_id = str(m.get('id', ''))
        sender = (m.get('recipient') or '').replace('+', '').replace(' ', '')
        text   = m.get('message') or '[attachment]'

        if not msg_id or msg_id in processed:
            continue

        # Skip internal numbers and WA groups
        if not sender or sender in SKIP_SENDERS or '@g.us' in sender:
            processed.add(msg_id)
            continue

        # Only relay to known school contacts or prior Glenda conversation partners
        if sender not in eligible:
            log.debug("  Skipping unknown sender +%s: %s", sender, str(text)[:40])
            processed.add(msg_id)
            continue

        # Only re-reply if this is a newer message than our last reply to this phone
        last_replied_id = replied.get(sender)
        if last_replied_id and int(msg_id) <= int(last_replied_id):
            processed.add(msg_id)
            continue

        log.info("  Eligible msg id=%s from +%s: %s", msg_id, sender, str(text)[:60])

        if live:
            resp = requests.post(f'{base}/send/whatsapp', data={
                'secret':    sec,
                'account':   buid,
                'recipient': sender,
                'type':      'text',
                'message':   RELAY_MESSAGE,
            }, timeout=20)
            rj     = resp.json()
            wa_mid = rj.get('data', {}).get('messageId')
            if rj.get('status') == 200 and wa_mid:
                log.info("    ✅ Relay sent via backup — messageId=%s", wa_mid)
                replied[sender] = msg_id
                sent += 1
            else:
                log.warning("    ❌ Relay send failed: %s", rj)
        else:
            log.info("    DRY RUN — would relay to +%s", sender)
            # Don't mark as processed in dry-run so --live can still send
            continue

        processed.add(msg_id)

    # Only persist state on live runs
    if live:
        state['processed_ids'] = list(processed)
        state['replied_phones'] = replied
        save_state(state)

    log.info("Done — %d relay(s) sent | live=%s", sent, live)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    main(live=args.live)
