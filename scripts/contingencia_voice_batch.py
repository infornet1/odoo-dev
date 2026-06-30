#!/usr/bin/env python3
"""Heads-up-then-call batch runner — Contingencia Académica voice reminders.

For each pending non-responder of the contingencia survey:
  1. Send a WhatsApp heads-up (so they answer the foreign caller ID), then
  2. Place a Glenda voice reminder call that captures their SÍ/NO live and
     notifies votacion@.

SAFE BY DEFAULT (DRY-RUN). Nothing is sent or called without --live.
Idempotent: skips already-voted ballots and parents already processed (state file).

Usage:
    python3 scripts/contingencia_voice_batch.py                 # DRY (default) — full list
    python3 scripts/contingencia_voice_batch.py --limit 5       # DRY — first 5 only
    python3 scripts/contingencia_voice_batch.py --limit 5 --live # LIVE pilot of 5
    python3 scripts/contingencia_voice_batch.py --live          # LIVE — all pending

Env: TARGET_ENV=production (default) | testing
Pacing: WA heads-up → HEADSUP_DELAY → call; ≥WA_MIN_INTERVAL between parents (anti-spam).
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import xmlrpc.client

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger('contingencia-voice')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(ROOT, 'scripts', 'contingencia_voice_batch_state.json')
NOTICE_KEY = 'contingencia_academica_2026'

HEADSUP_DELAY = 45        # seconds between the WhatsApp heads-up and the call
WA_MIN_INTERVAL = 130     # min seconds between parents (MassivaMóvil anti-spam ≥120s)

WA_TEMPLATE = (
    "Hola {name} 👋 En unos minutos le llamará *Glenda*, la asistente virtual del "
    "Colegio Andrés Bello, desde un *número internacional (+1)*, para recordarle "
    "la encuesta del *Plan de Contingencia Académica* (cierra mañana 1 de julio). "
    "Por favor conteste; será breve. 🎓 También puede responder por este WhatsApp con "
    "*SÍ* o *NO*."
)


# ───────────────────────────── helpers ─────────────────────────────
def load_json(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save_state(state):
    with open(STATE_FILE, 'w') as fh:
        json.dump(state, fh, indent=2)


def norm_ve(raw):
    """Normalise a Venezuelan number to 12 digits '58XXXXXXXXXX', or None."""
    d = re.sub(r'\D', '', str(raw or ''))
    if d.startswith('58') and len(d) == 12:
        return d
    if d.startswith('0') and len(d) == 11:       # 0414xxxxxxx
        return '58' + d[1:]
    if len(d) == 10 and d[0] == '4':             # 414xxxxxxx
        return '58' + d
    if d.startswith('58') and len(d) > 12:
        return d[:12]
    return None


def odoo_connect():
    cfg = json.load(open(os.path.join(ROOT, 'config', 'production.json')))
    env_key = os.environ.get('TARGET_ENV', 'production')
    c = cfg['production']['xmlrpc'] if env_key == 'production' else None
    if not c:
        sys.exit("Only production XML-RPC wired here; set TARGET_ENV=production.")
    common = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/common")
    uid = common.authenticate(c['db'], c['user'], c['api_key'], {})
    models = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/object")

    def x(model, method, *a):
        return models.execute_kw(c['db'], uid, c['api_key'], model, method, *a)
    return x


def wa_send(wa_cfg, digits, message):
    import requests
    acc = next(a for a in wa_cfg['whatsapp_accounts'] if a.get('primary'))
    url = wa_cfg['api']['base_url'].rstrip('/') + '/send/whatsapp'
    data = {'secret': wa_cfg['api']['secret'], 'account': acc['unique_id'],
            'recipient': digits, 'type': 'text', 'message': message}
    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    res = r.json()
    if res.get('status') == 200:
        return True, res.get('data', {}).get('messageId', '')
    return False, res.get('message', 'unknown')


# ───────────────────────────── main ────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='actually send WA + place calls')
    ap.add_argument('--limit', type=int, default=0, help='cap number of parents (0 = all)')
    args = ap.parse_args()
    mode = 'LIVE' if args.live else 'DRY-RUN'

    x = odoo_connect()
    state = load_json(STATE_FILE, {})
    wa_cfg = json.load(open(os.path.join(ROOT, 'config', 'whatsapp_massiva.json')))

    pending = x('partner.communication.ack', 'search_read',
                [[('notice_key', '=', NOTICE_KEY), ('state', '=', 'pending')]],
                {'fields': ['id', 'partner_id', 'partner_name', 'partner_phone']})
    # only those with a usable VE phone
    targets = []
    for a in pending:
        digits = norm_ve(a.get('partner_phone'))
        if not digits:
            continue
        targets.append({**a, 'digits': digits})

    log.info("=== Contingencia voice batch — %s ===", mode)
    log.info("pending non-responders: %d | with valid phone: %d", len(pending), len(targets))

    if args.limit:
        targets = targets[:args.limit]
        log.info("limited to first %d", len(targets))

    done = skipped = failed = 0
    for i, t in enumerate(targets, 1):
        ack_id = str(t['id'])
        name = (t.get('partner_name') or (t['partner_id'][1] if t.get('partner_id') else '')
                ).split()[0].title() if (t.get('partner_name') or t.get('partner_id')) else 'Representante'
        full = t.get('partner_name') or (t['partner_id'][1] if t.get('partner_id') else '')
        digits, e164 = t['digits'], '+' + t['digits']

        # idempotency: skip already processed
        if state.get(ack_id, {}).get('call_placed'):
            log.info("[%d/%d] SKIP (already processed) %s", i, len(targets), full)
            skipped += 1
            continue
        # re-check the vote hasn't arrived since the query
        cur = x('partner.communication.ack', 'read', [[t['id']]], {'fields': ['state']})
        if cur and cur[0]['state'] != 'pending':
            log.info("[%d/%d] SKIP (already voted: %s) %s", i, len(targets), cur[0]['state'], full)
            skipped += 1
            continue

        if not args.live:
            log.info("[%d/%d] WOULD heads-up + call %s  (%s)", i, len(targets), full, e164)
            done += 1
            continue

        # 1) WhatsApp heads-up
        try:
            ok, msgid = wa_send(wa_cfg, digits, WA_TEMPLATE.format(name=name))
            log.info("[%d/%d] WA → %s  %s (id %s)", i, len(targets), full,
                     'OK' if ok else 'FAIL', msgid)
        except Exception as e:
            log.warning("[%d/%d] WA send error for %s: %s", i, len(targets), full, e)
            ok, msgid = False, ''
        state.setdefault(ack_id, {}).update({'name': full, 'phone': e164,
                                             'wa_ok': ok, 'wa_msgid': msgid, 'ts': time.time()})
        save_state(state)

        # 2) brief pause so they see the heads-up, then place the call
        time.sleep(HEADSUP_DELAY)
        try:
            res = x('ai.agent.voice.call', 'place_contingencia_reminder', [t['partner_id'][0]],
                    {'phone': e164, 'notice_key': NOTICE_KEY})
            log.info("[%d/%d] CALL → %s  call=%s sid=%s status=%s%s", i, len(targets), full,
                     res.get('call_id'), res.get('sid', ''), res.get('status', ''),
                     (' ERR=' + res['error']) if res.get('error') else '')
            state[ack_id].update({'call_placed': True, 'call_id': res.get('call_id'),
                                  'call_sid': res.get('sid', ''), 'call_err': res.get('error', '')})
            save_state(state)
            done += 1 if not res.get('error') else 0
            failed += 1 if res.get('error') else 0
        except Exception as e:
            log.error("[%d/%d] CALL error for %s: %s", i, len(targets), full, e)
            failed += 1

        # 3) inter-parent spacing (anti-spam), accounting for the heads-up delay already waited
        if i < len(targets):
            remaining = max(0, WA_MIN_INTERVAL - HEADSUP_DELAY)
            time.sleep(remaining)

    log.info("=== %s done — processed=%d skipped=%d failed=%d ===", mode, done, skipped, failed)


if __name__ == '__main__':
    main()
