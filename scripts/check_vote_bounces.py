#!/usr/bin/env python3
"""
Vote Bounce Detector — Consulta Presupuestaria 2026-2027
=========================================================
Detects bounced vote emails (mail.mail state=exception), then for each:
  1. Creates a Glenda WA conversation so the parent can vote via WhatsApp
  2. Opens a FreeScout conversation in votacion@ (mailbox_id=8) as unassigned
     with direct Odoo hyperlinks for staff follow-up
  3. Stores the FreeScout conv ID on the ACK record (partner.communication.ack)
  4. Sets bounce_wa_sent=True to prevent reprocessing

Usage:
    python3 scripts/check_vote_bounces.py           # dry-run
    python3 scripts/check_vote_bounces.py --live    # process + notify

State file: scripts/vote_bounces_state.json
"""

import argparse
import json
import logging
import os
import sys
import time
import xmlrpc.client
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────

PROD_CFG      = '/opt/odoo-dev/config/production.json'
FS_CFG        = '/opt/odoo-dev/config/freescout_api.json'
STATE_FILE    = os.path.join(os.path.dirname(__file__), 'vote_bounces_state.json')

NOTICE_KEY    = 'budget_consulta_2026_2027'
ODOO_URL      = 'https://odoo.ueipab.edu.ve'
FS_MAILBOX_ID = 8          # votacion@ueipab.edu.ve
FS_BYUSER     = 10         # Gustavo Perdomo
FS_FOLDER_INBOX = 271      # Unassigned inbox for mailbox 8

# Odoo UI deep-links
ACK_URL       = (ODOO_URL +
                 '/web#id={ack_id}&cids=1&action=840'
                 '&model=partner.communication.ack&view_type=form')
PARTNER_URL   = ODOO_URL + '/web#id={partner_id}&model=res.partner&view_type=form&cids=1'
GLENDA_URL    = (ODOO_URL +
                 '/web#id={conv_id}&model=ai.agent.conversation'
                 '&view_type=form&cids=1&menu_id=566&action=830')


# ── Connection helpers ─────────────────────────────────────────────────────────

def _odoo_connect():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    return models, cfg['db'], uid, cfg['api_key']


def call(m, db, uid, key, model, method, args=None, kw=None):
    return m.execute_kw(db, uid, key, model, method, args or [[]], kw or {})


def _fs_headers():
    cfg = json.load(open(FS_CFG))
    return (cfg['api_url'], {'X-FreeScout-API-Key': cfg['api_key'],
                              'Content-Type': 'application/json',
                              'Accept': 'application/json'})


# ── State ──────────────────────────────────────────────────────────────────────

def _load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {'processed_ack_ids': []}


def _save_state(state):
    json.dump(state, open(STATE_FILE, 'w'), indent=2)


# ── Bounce detection ───────────────────────────────────────────────────────────

def _find_bounced_acks(m, db, uid, key):
    """Return list of ACK records whose vote email bounced and WA not yet sent."""
    # Get all pending ACKs not yet bounce-notified
    acks = call(m, db, uid, key,
        'partner.communication.ack', 'search_read',
        [[('notice_key',     '=', NOTICE_KEY),
          ('state',          '=', 'pending'),
          ('bounce_wa_sent', '=', False),
          ('partner_phone',  '!=', False)]],
        {'fields': ['id', 'partner_id', 'partner_name', 'partner_email',
                    'partner_phone', 'token']})
    if not acks:
        return []

    # Find failed mail.mail records for the vote campaign
    failed_mails = call(m, db, uid, key,
        'mail.mail', 'search_read',
        [[('subject', 'ilike', 'Consulta Presupuestaria 2026-2027'),
          ('state', '=', 'exception')]],
        {'fields': ['id', 'email_to', 'failure_reason']})

    if not failed_mails:
        log.info("No bounced mail.mail records found for the vote campaign.")
        return []

    # Build set of bounced addresses (lower-cased)
    bounced_addrs = set()
    for mail in failed_mails:
        raw = mail.get('email_to', '') or ''
        # email_to format: "Name <addr>" or just "addr"
        import re
        for addr in re.findall(r'[\w.+\-]+@[\w.\-]+', raw):
            bounced_addrs.add(addr.lower())

    # Match ACKs to bounced addresses
    bounced_acks = []
    for ack in acks:
        emails = (ack.get('partner_email') or '').replace(';', ',')
        for addr in emails.split(','):
            if addr.strip().lower() in bounced_addrs:
                bounced_acks.append(ack)
                log.info("Bounce detected: %s <%s>",
                         ack['partner_name'], addr.strip())
                break

    return bounced_acks


# ── Glenda conversation ────────────────────────────────────────────────────────

def _create_glenda_conv(m, db, uid, key, ack, live):
    """Create + start a Glenda WA conversation for the bounced parent."""
    # Find general_inquiry skill id
    skills = call(m, db, uid, key,
        'ai.agent.skill', 'search_read',
        [[('code', '=', 'general_inquiry')]],
        {'fields': ['id'], 'limit': 1})
    if not skills:
        log.warning("Could not find general_inquiry skill")
        return None
    skill_id   = skills[0]['id']
    partner_id = ack['partner_id'][0] if ack.get('partner_id') else False

    initial_msg = (
        f"mi correo de votación rebotó y no pude recibir el enlace. "
        f"Quiero votar por WhatsApp."
    )

    conv_vals = {
        'skill_id':       skill_id,
        'phone':          ack['partner_phone'],
        'initial_message': initial_msg,
        'state':          'draft',
    }
    if partner_id:
        conv_vals['partner_id'] = partner_id

    if not live:
        log.info("  DRY: would create Glenda conv for %s (phone=%s)",
                 ack['partner_name'], ack['partner_phone'])
        return -1  # sentinel for dry-run

    conv_id = call(m, db, uid, key,
        'ai.agent.conversation', 'create', [[conv_vals]])
    # action_start() processes initial_message → sends WA to parent
    call(m, db, uid, key,
        'ai.agent.conversation', 'action_start', [[conv_id]])
    log.info("  Glenda conv #%d created + started for %s",
             conv_id, ack['partner_name'])
    return conv_id


# ── FreeScout conversation ─────────────────────────────────────────────────────

def _create_freescout_conv(ack, glenda_conv_id, live):
    """Open a FreeScout conversation in votacion@ mailbox with Odoo hyperlinks."""
    try:
        fs_url, headers = _fs_headers()
        ack_id     = ack['id']
        partner_id = ack['partner_id'][0] if ack.get('partner_id') else 0
        name       = ack['partner_name']
        email      = ack['partner_email'] or ''
        phone      = ack['partner_phone'] or ''

        ack_link     = ACK_URL.format(ack_id=ack_id)
        partner_link = PARTNER_URL.format(partner_id=partner_id) if partner_id else ''
        glenda_link  = (GLENDA_URL.format(conv_id=glenda_conv_id)
                        if glenda_conv_id and glenda_conv_id != -1 else '')

        body = (
            f'<p><strong>Seguimiento de voto vía WhatsApp</strong></p>'
            f'<p>El correo de votación enviado a <strong>{email}</strong> fue rechazado '
            f'(bounce). Se inició conversación WhatsApp con Glenda.</p>'
            f'<hr/>'
            f'<p><strong>🔗 Accesos directos en Odoo:</strong></p>'
            f'<ul>'
            f'<li>📊 <a href="{ack_link}">Registro de voto (partner.communication.ack #{ack_id})</a></li>'
            + (f'<li>👤 <a href="{partner_link}">Contacto: {name}</a></li>' if partner_link else '')
            + (f'<li>💬 <a href="{glenda_link}">Conversación Glenda #{glenda_conv_id}</a></li>'
               if glenda_link else '')
            + f'</ul>'
            f'<hr/>'
            f'<p>📱 WA enviado a: <strong>{phone}</strong><br/>'
            f'📧 Email rebotado: <strong>{email}</strong></p>'
            f'<p><em>Acción requerida: confirmar que el representante votó via WA, '
            f'o contactar por teléfono si no responde en 24h.</em></p>'
        )

        # Find or create FreeScout customer
        cust_resp = requests.get(
            f'{fs_url}/customers?email={email.split(",")[0].strip()}',
            headers=headers, timeout=10)
        customer_id = None
        if cust_resp.status_code == 200:
            customers = cust_resp.json().get('_embedded', {}).get('customers', [])
            if customers:
                customer_id = customers[0]['id']

        payload = {
            'type':      1,       # email type
            'mailboxId': FS_MAILBOX_ID,
            'status':    'active',
            'subject':   f'[Voto WA] {name} — correo rebotó, WA iniciado',
            'customer':  {'email': email.split(',')[0].strip()},
            'threads': [{
                'type': 'message',
                'text': body,
                'user': FS_BYUSER,
            }],
        }
        if customer_id:
            payload['customer']['id'] = customer_id

        if not live:
            log.info("  DRY: would create FreeScout conv for %s", name)
            return -1

        resp = requests.post(f'{fs_url}/conversations',
                             json=payload, headers=headers, timeout=15)
        if resp.status_code in (200, 201):
            fs_conv_id = resp.json().get('id')
            log.info("  FreeScout conv #%s created for %s", fs_conv_id, name)
            return str(fs_conv_id) if fs_conv_id else None
        else:
            log.warning("  FreeScout conv creation failed: HTTP %d — %s",
                        resp.status_code, resp.text[:200])
            return None
    except Exception as e:
        log.error("  FreeScout error: %s", e)
        return None


# ── Update ACK record ──────────────────────────────────────────────────────────

def _update_ack(m, db, uid, key, ack_id, glenda_conv_id, fs_conv_id, live):
    from datetime import datetime as _dt
    notes = f"Bounce detectado {_dt.now().strftime('%d/%m/%Y %H:%M')} — WA Glenda conv #{glenda_conv_id}"
    if fs_conv_id and fs_conv_id != -1:
        notes += f" — FreeScout conv #{fs_conv_id}"
    vals = {
        'bounce_wa_sent':    True,
        'vote_notes':        notes,
    }
    if fs_conv_id and str(fs_conv_id) != '-1':
        vals['freescout_conv_id'] = str(fs_conv_id)

    if not live:
        log.info("  DRY: would update ACK #%d with bounce_wa_sent=True", ack_id)
        return
    call(m, db, uid, key,
         'partner.communication.ack', 'write', [[ack_id], vals])
    log.info("  ACK #%d updated — bounce_wa_sent=True", ack_id)


# ── Main ───────────────────────────────────────────────────────────────────────

def main(live):
    m, db, uid, key = _odoo_connect()
    state = _load_state()
    processed_ids = set(state.get('processed_ack_ids', []))

    log.info("=" * 70)
    log.info("VOTE BOUNCE CHECKER — %s", "LIVE" if live else "DRY RUN")
    log.info("=" * 70)

    bounced = _find_bounced_acks(m, db, uid, key)
    # Skip already-processed
    bounced = [a for a in bounced if a['id'] not in processed_ids]
    log.info("Bounces to process: %d", len(bounced))

    for ack in bounced:
        log.info("Processing: %s (ack #%d)", ack['partner_name'], ack['id'])

        # 1. Create Glenda WA conversation
        glenda_conv_id = _create_glenda_conv(m, db, uid, key, ack, live)

        # 2. Create FreeScout monitoring conversation
        fs_conv_id = _create_freescout_conv(ack, glenda_conv_id, live)

        # 3. Update ACK record
        _update_ack(m, db, uid, key, ack['id'], glenda_conv_id, fs_conv_id, live)

        # Track to avoid reprocessing
        if live:
            processed_ids.add(ack['id'])

        time.sleep(0.5)

    if live:
        state['processed_ack_ids'] = list(processed_ids)
        _save_state(state)

    log.info("Done — processed %d bounce(s).", len(bounced))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    main(live=args.live)
