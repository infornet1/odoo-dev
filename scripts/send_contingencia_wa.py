#!/usr/bin/env python3
"""
Encuesta Plan de Contingencia Académica — WhatsApp sender (no-email families)
=============================================================================
Reaches the ACTIVE families that have NO col-J email (so the email blast could
not include them) over WhatsApp, via Glenda's MassivaMóvil number. Each family
gets the survey + two TOKENIZED vote links:
    SÍ → {base}/partner-ack/<token>/si   (state 'continuing')
    NO → {base}/partner-ack/<token>/no   (state 'leaving')
Tapping a link records the vote through the SAME public controller as the email
flow — no email needed. If a parent replies on WhatsApp, Glenda's general_inquiry
skill answers (incoming WA already routes to Glenda).

Recipients : Customers tab, Status==ACTIVE, col J Email EMPTY, col L Phone set.
Ballot     : reuse-or-create partner.communication.ack (notice_key below) per
             family → token. Partner matched by name/phone; created if missing
             (these 9 are deliberately enfranchised into the base-178 plantilla).
Target     : PRODUCTION (DB_UEIPAB) via XML-RPC; WA via MassivaMóvil backup #.

Usage (run on a host with google libs + the configs):
    python3 scripts/send_contingencia_wa.py            # DRY (list, no ACK, no WA)
    python3 scripts/send_contingencia_wa.py --test     # one real WA to the CEO's phone
    python3 scripts/send_contingencia_wa.py --live      # create ACKs + WA the 9 families

Anti-spam: 120s between sends (MassivaMóvil). 9 families ≈ 16 min — run detached
(nohup) for --live. Idempotent: skips already-voted ballots and phones already
sent (scripts/contingencia_wa_state.json).
"""
import argparse
import json
import os
import sys
import time
import logging
import xmlrpc.client

import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger('contingencia_wa')

NOTICE_KEY   = 'contingencia_academica_2026'
NOTICE_LABEL = 'Plan de Contingencia Académica — Modelo Bimodal'

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
CREDS_PATH     = '/opt/odoo-dev/config/google_sheets_credentials.json'
WA_CONFIG      = '/opt/odoo-dev/config/whatsapp_massiva.json'
PJSON          = '/opt/odoo-dev/config/production.json'
STATE_PATH     = '/opt/odoo-dev/scripts/contingencia_wa_state.json'

CEO_TEST_PHONE = '584142337463'   # Gustavo — preview recipient for --test
ANTISPAM_SECS  = 120


# ── WhatsApp (MassivaMóvil) ──────────────────────────────────────────────────
TERTIARY_PHONE = '+584148321963'

def load_wa_config(account=None):
    """account: None/'backup' → the connected primary (+584248944898);
    'tertiary' → +584148321963; or pass an explicit '+58…' phone."""
    cfg = json.load(open(WA_CONFIG))
    accounts = cfg.get('whatsapp_accounts', [])
    if account == 'tertiary':
        acc = next(a for a in accounts if a['phone'] == TERTIARY_PHONE)
    elif account in (None, 'backup'):
        acc = next((a for a in accounts if a.get('primary')), accounts[0])
    else:
        acc = next(a for a in accounts if a['phone'] == account)
    return {'secret': cfg['api']['secret'], 'account_id': acc['unique_id'],
            'base_url': cfg['api']['base_url'], 'from_phone': acc['phone']}


def send_whatsapp(wa, phone, message):
    url = wa['base_url'].rstrip('/') + '/send/whatsapp'
    data = {'secret': wa['secret'], 'account': wa['account_id'],
            'recipient': phone, 'type': 'text', 'message': message}
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if result.get('status') == 200:
        return True, result.get('data', {}).get('messageId', '')
    return False, result.get('message', 'unknown')


def _norm(raw):
    return ''.join(c for c in str(raw or '') if c.isdigit())


# ── Google sheet: ACTIVE + no email + phone ─────────────────────────────────
def load_no_email_families():
    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute().get('values', [])[1:]
    fam = []
    for r in rows:
        x = (r + [''] * 13)[:13]
        name, status, email, phone = x[1].strip(), x[2].strip().upper(), x[9].strip(), x[11].strip()
        if status == 'ACTIVE' and name and not email and phone:
            fam.append({'name': name, 'phone': _norm(phone)})
    log.info("ACTIVE no-email families with a phone: %d", len(fam))
    return fam


# ── Odoo (prod) ──────────────────────────────────────────────────────────────
def connect():
    c = json.load(open(PJSON))['production']['xmlrpc']
    uid = xmlrpc.client.ServerProxy(c['url'] + '/xmlrpc/2/common').authenticate(
        c['db'], c['user'], c['api_key'], {})
    if not uid:
        sys.exit('ERROR: XML-RPC auth failed')
    return xmlrpc.client.ServerProxy(c['url'] + '/xmlrpc/2/object', allow_none=True), c['db'], uid, c['api_key']


def call(m, db, uid, key, model, method, args, kw=None):
    return m.execute_kw(db, uid, key, model, method, args, kw or {})


def find_or_create_partner(m, db, uid, key, name, phone, live):
    # by name first, then by phone/mobile digits
    hit = call(m, db, uid, key, 'res.partner', 'search_read',
               [[['name', 'ilike', name], ['active', '=', True]]], {'fields': ['id'], 'limit': 1})
    if hit:
        return hit[0]['id'], False
    for fld in ('mobile', 'phone'):
        hit = call(m, db, uid, key, 'res.partner', 'search_read',
                   [[[fld, 'ilike', phone[-9:]], ['active', '=', True]]], {'fields': ['id'], 'limit': 1})
        if hit:
            return hit[0]['id'], False
    if not live:
        return None, True
    pid = call(m, db, uid, key, 'res.partner', 'create',
               [{'name': name, 'mobile': '+' + phone}])
    pid = pid[0] if isinstance(pid, list) else pid
    return pid, True


def get_ack(m, db, uid, key, pid, name, phone, create):
    """Find the ballot; create one only when create=True (never in DRY)."""
    ex = call(m, db, uid, key, 'partner.communication.ack', 'search_read',
              [[['notice_key', '=', NOTICE_KEY], ['partner_id', '=', pid]]],
              {'fields': ['id', 'state', 'token'], 'limit': 1})
    if ex:
        return ex[0]['id'], ex[0]['state'], ex[0]['token']
    if not create:
        return None, None, None
    aid = call(m, db, uid, key, 'partner.communication.ack', 'create',
               [{'notice_key': NOTICE_KEY, 'notice_label': NOTICE_LABEL,
                 'partner_id': pid, 'partner_name': name, 'partner_phone': '+' + phone}])
    aid = aid[0] if isinstance(aid, list) else aid
    tok = call(m, db, uid, key, 'partner.communication.ack', 'read', [[aid]], {'fields': ['token']})[0]['token']
    return aid, 'pending', tok


def build_message(name, si_url, no_url):
    return (
        f'🏫 *Instituto Privado "Andrés Bello"* — Consulta a representantes\n\n'
        f'Estimado(a) {name}, ante las directrices de las autoridades para resguardar a '
        f'los alumnos en casa, el colegio consulta la activación del *Plan de Contingencia '
        f'Académica* (modelo bimodal con *Google Classroom* y *Google Meet*) para no '
        f'interrumpir el año escolar.\n\n'
        f'¿Está usted de acuerdo? Toque una opción para registrar su voto:\n\n'
        f'✅ *SÍ, estoy de acuerdo:*\n{si_url}\n\n'
        f'❌ *NO estoy de acuerdo:*\n{no_url}\n\n'
        f'La medida se activa al alcanzar el 50%+1. Cierre: *01/07/2026*. '
        f'Si tiene dudas, responda este mensaje y con gusto le ayudamos. 🙏'
    )


def build_reminder(name, si_url, no_url):
    return (
        f'🏫 *Instituto Privado "Andrés Bello"* — Recordatorio de consulta\n\n'
        f'Estimado(a) {name}, le recordamos amablemente fijar su postura sobre la '
        f'activación del *Plan de Contingencia Académica* (modelo bimodal con '
        f'*Google Classroom* y *Google Meet*). Su voto es importante para alcanzar '
        f'el 50%+1.\n\n'
        f'✅ *SÍ, estoy de acuerdo:*\n{si_url}\n\n'
        f'❌ *NO estoy de acuerdo:*\n{no_url}\n\n'
        f'Cierre de la votación: *01/07/2026*. Si ya votó, ignore este mensaje. '
        f'¿Dudas? Responda aquí. 🙏'
    )


def _state(path=STATE_PATH):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {'sent_phones': []}


def _save_state(s, path=STATE_PATH):
    json.dump(s, open(path, 'w'))


def remind(account, shard, cap, live):
    """WA reminder to pending voters — reuses each ballot's EXISTING token (same
    /si /no links, no new ballots). Splits the list by shard, caps per run, uses
    the chosen WA account, and never re-reminds (per-account state file)."""
    wa = load_wa_config(account)
    a_idx, a_tot = (0, 1)
    if shard:
        a_idx, a_tot = (int(x) for x in shard.split('/'))
    rstate_path = f'/opt/odoo-dev/scripts/contingencia_remind_state_{account or "backup"}.json'
    rstate = _state(rstate_path)
    already_wa = set(_state(STATE_PATH).get('sent_phones', []))   # the original no-email 9

    log.info("=" * 70)
    log.info("CONTINGENCIA WA REMINDER — %s | account=%s (%s) | shard=%s | cap=%s",
             'LIVE' if live else 'DRY', account or 'backup', wa['from_phone'],
             shard or '0/1', cap)
    log.info("=" * 70)

    m, db, uid, key = connect()
    base = call(m, db, uid, key, 'ir.config_parameter', 'get_param', ['web.base.url'])

    acks = call(m, db, uid, key, 'partner.communication.ack', 'search_read',
                [[['notice_key', '=', NOTICE_KEY], ['state', '=', 'pending']]],
                {'fields': ['id', 'token', 'partner_name', 'partner_phone', 'partner_id'],
                 'order': 'id'})
    # resolve phones (fall back to partner mobile/phone)
    need = [a['partner_id'][0] for a in acks if not (a.get('partner_phone') or '').strip()]
    pmap = {}
    if need:
        for p in call(m, db, uid, key, 'res.partner', 'read', [list(set(need))],
                      {'fields': ['mobile', 'phone']}):
            pmap[p['id']] = _norm(p.get('mobile') or p.get('phone') or '')

    eligible = []
    for a in acks:
        phone = _norm(a.get('partner_phone') or '') or pmap.get(a['partner_id'][0], '')
        if not phone:
            continue
        if phone in already_wa:               # don't re-hit the just-contacted 9
            continue
        if phone in rstate.get('sent_phones', []):
            continue
        eligible.append({'name': a['partner_name'] or 'Representante',
                         'phone': phone, 'token': a['token']})

    # deterministic shard split, then cap
    shard_list = [e for i, e in enumerate(eligible) if i % a_tot == a_idx]
    wave = shard_list[:cap]
    log.info("pending eligible=%d | this shard=%d | this wave (cap %d)=%d",
             len(eligible), len(shard_list), cap, len(wave))

    sent = 0
    for i, e in enumerate(wave):
        si = f"{base}/partner-ack/{e['token']}/si"
        no = f"{base}/partner-ack/{e['token']}/no"
        if not live:
            log.info("  DRY  %s  +%s", e['name'], e['phone'])
            continue
        # Freshness re-check: skip anyone who voted since the wave started
        # (the wave runs ~80 min; a parent may reply mid-wave).
        cur = call(m, db, uid, key, 'partner.communication.ack', 'search_read',
                   [[['token', '=', e['token']]]], {'fields': ['state'], 'limit': 1})
        if cur and cur[0]['state'] != 'pending':
            log.info("  SKIP %s — voted since wave start (%s)", e['name'], cur[0]['state'])
            continue
        ok, info = send_whatsapp(wa, e['phone'], build_reminder(e['name'], si, no))
        if ok:
            rstate.setdefault('sent_phones', []).append(e['phone'])
            _save_state(rstate, rstate_path)
            log.info("  SENT %s  +%s  (msgId %s)", e['name'], e['phone'], info)
            sent += 1
        else:
            log.error("  FAIL %s  +%s  : %s", e['name'], e['phone'], info)
        if i < len(wave) - 1:
            time.sleep(ANTISPAM_SECS)

    log.info("=" * 70)
    log.info("REMINDER SENT: %d / %d (account=%s)", sent, len(wave), wa['from_phone'])
    log.info("=" * 70)


def main(live, test):
    wa = load_wa_config()
    mode = 'LIVE (WA the 9 families)' if live else ('TEST (one WA to CEO)' if test else 'DRY RUN')
    log.info("=" * 70)
    log.info("CONTINGENCIA WHATSAPP — %s  (from %s)", mode, wa['from_phone'])
    log.info("=" * 70)

    m, db, uid, key = connect()
    base = call(m, db, uid, key, 'ir.config_parameter', 'get_param', ['web.base.url'])
    families = load_no_email_families()
    state = _state()

    if test:
        # one real WA to the CEO using a throwaway ballot under the CEO partner
        ceo = call(m, db, uid, key, 'res.partner', 'search_read',
                   [[['email', 'ilike', 'gustavo.perdomo@ueipab.edu.ve']]], {'fields': ['id', 'name'], 'limit': 1})
        pid, name = ceo[0]['id'], ceo[0]['name']
        _, _, tok = get_ack(m, db, uid, key, pid, name, CEO_TEST_PHONE, create=True)
        msg = build_message(name, f'{base}/partner-ack/{tok}/si', f'{base}/partner-ack/{tok}/no')
        ok, info = send_whatsapp(wa, CEO_TEST_PHONE, msg)
        log.info("TEST WA → %s : %s (%s)", CEO_TEST_PHONE, 'OK' if ok else 'FAIL', info)
        return

    sent = skipped = 0
    for i, fam in enumerate(families):
        name, phone = fam['name'], fam['phone']
        if phone in state['sent_phones']:
            log.info("  SKIP %s — WA already sent", name); skipped += 1; continue

        pid, created = find_or_create_partner(m, db, uid, key, name, phone, live)
        if not pid:
            log.warning("  %s — no partner (would create on --live)", name)
            if not live:
                continue
        aid, st, tok = (None, None, None)
        if pid:
            aid, st, tok = get_ack(m, db, uid, key, pid, name, phone, create=live)
            if st and st != 'pending':
                log.info("  SKIP %s — already voted (%s)", name, st); skipped += 1; continue

        if not live:
            log.info("  DRY  %s  +%s  %s", name, phone,
                     ('[partner #%s%s, %s]' % (pid, ' NEW' if created else '',
                      'ballot exists' if tok else 'would create ballot')) if pid else '[no partner]')
            continue

        si_url = f'{base}/partner-ack/{tok}/si'
        no_url = f'{base}/partner-ack/{tok}/no'

        msg = build_message(name, si_url, no_url)
        ok, info = send_whatsapp(wa, phone, msg)
        if ok:
            state['sent_phones'].append(phone); _save_state(state)
            log.info("  SENT %s  +%s  (msgId %s)%s", name, phone, info, ' NEW partner' if created else '')
            sent += 1
        else:
            log.error("  FAIL %s  +%s  : %s", name, phone, info)
        if i < len(families) - 1:
            time.sleep(ANTISPAM_SECS)

    log.info("=" * 70)
    log.info("WA SENT: %d  |  SKIPPED: %d", sent, skipped)
    log.info("=" * 70)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--live', action='store_true', help='Actually send (default: DRY)')
    p.add_argument('--test', action='store_true', help='One real WA to the CEO phone')
    p.add_argument('--remind', action='store_true',
                   help='Reminder wave to PENDING voters, reusing each ballot token')
    p.add_argument('--account', default='backup', choices=['backup', 'tertiary'],
                   help='Which WA number to send from (remind mode)')
    p.add_argument('--cap', type=int, default=40, help='Max sends this run (remind mode)')
    p.add_argument('--shard', default=None, help='A/B split, e.g. 0/2 or 1/2 (remind mode)')
    a = p.parse_args()
    if a.remind:
        remind(account=a.account, shard=a.shard, cap=a.cap, live=a.live)
    else:
        main(live=a.live, test=a.test)
