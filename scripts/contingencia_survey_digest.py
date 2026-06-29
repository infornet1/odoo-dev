#!/usr/bin/env python3
"""
Encuesta Plan de Contingencia Académica — Progress Digest
=========================================================
Sends a delivery + response digest to the school director and CEO while the
SÍ/NO bimodal-contingency survey is live, and flags when the 50%+1 approval
threshold is reached (so the survey can be CLOSED with CEO approval).

Reads (XML-RPC, prod by default):
  • partner.communication.ack  notice_key='contingencia_academica_2026'
      → SÍ (continuing) / NO (leaving) / Pendiente (pending) tally
  • mail.mail subject ~ survey  → delivery stats (sent / outgoing / exception)

Threshold = (plantilla_total // 2) + 1.  plantilla_total comes from
ir.config_parameter 'contingencia.plantilla_total' (default = ballots issued).
Recipients come from 'contingencia.digest_to' (CSV; default = CEO only).

Config params (set in Odoo → Technical → System Parameters, or via this script's
sibling wiring; all optional with sane defaults):
    contingencia.digest_to         CSV of recipient emails  (default CEO)
    contingencia.plantilla_total   int base for 50%+1       (default = #ballots)

Usage:
    python3 scripts/contingencia_survey_digest.py                 # DRY (print stats, no send)
    python3 scripts/contingencia_survey_digest.py --test          # preview to CEO only
    python3 scripts/contingencia_survey_digest.py --live          # send to contingencia.digest_to
    TARGET_ENV=testing python3 scripts/contingencia_survey_digest.py --test
"""
import argparse
import json
import os
import sys
import xmlrpc.client

NOTICE_KEY = 'contingencia_academica_2026'
SUBJECT_MATCH = 'Plan de Contingencia Académica'
SURVEY_DEADLINE = '01 de julio de 2026'

CEO_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'
SENDER = 'Encuesta Contingencia <votacion@ueipab.edu.ve>'
PJSON = '/opt/odoo-dev/config/production.json'

DIGEST_SUBJECT = '📊 Encuesta Contingencia Académica — Avance de votación'


def _cfg():
    env = os.environ.get('TARGET_ENV', 'production').strip().lower()
    blocks = json.load(open(PJSON))
    if env in ('test', 'testing'):
        # testing has no dedicated xmlrpc creds block; reuse local instance
        return ('http://localhost:8019', 'testing',
                os.environ.get('ODOO_USER', 'admin'),
                os.environ.get('ODOO_KEY', 'admin'))
    c = blocks['production']['xmlrpc']
    return c['url'], c['db'], c['user'], c['api_key']


def _connect():
    url, db, user, key = _cfg()
    uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, key, {})
    if not uid:
        sys.exit('ERROR: XML-RPC authentication failed')
    return xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True), db, uid, key


def _call(m, db, uid, key, model, method, args, kw=None):
    return m.execute_kw(db, uid, key, model, method, args, kw or {})


def _param(m, db, uid, key, name, default=None):
    r = _call(m, db, uid, key, 'ir.config_parameter', 'get_param', [name])
    return r if r not in (False, None, '') else default


def gather(m, db, uid, key):
    acks = _call(m, db, uid, key, 'partner.communication.ack', 'search_read',
                 [[['notice_key', '=', NOTICE_KEY]]], {'fields': ['state']})
    total = len(acks)
    si = sum(1 for a in acks if a['state'] == 'continuing')
    no = sum(1 for a in acks if a['state'] == 'leaving')
    pend = sum(1 for a in acks if a['state'] == 'pending')

    def mcount(state):
        return _call(m, db, uid, key, 'mail.mail', 'search_count',
                     [[['subject', 'ilike', SUBJECT_MATCH], ['state', '=', state]]])
    sent = mcount('sent')
    outgoing = mcount('outgoing')
    failed = mcount('exception')

    base = _param(m, db, uid, key, 'contingencia.plantilla_total')
    try:
        base = int(base) if base else total
    except (TypeError, ValueError):
        base = total
    threshold = (base // 2) + 1
    reached = si >= threshold

    return {
        'total': total, 'si': si, 'no': no, 'pend': pend,
        'sent': sent, 'outgoing': outgoing, 'failed': failed,
        'base': base, 'threshold': threshold, 'reached': reached,
        'voted': si + no,
        'participation': round(100.0 * (si + no) / total, 1) if total else 0.0,
        'si_pct_base': round(100.0 * si / base, 1) if base else 0.0,
    }


def _bar(value, goal, width=26):
    filled = min(width, int(round(width * value / goal))) if goal else 0
    return '█' * filled + '░' * (width - filled)


def build_html(s):
    if s['reached']:
        banner = (
            '<div style="background:#1b5e20;color:#fff;padding:14px 18px;border-radius:10px;'
            'text-align:center;font-size:15px;font-weight:bold;margin-bottom:18px;">'
            '✅ 50%&nbsp;+&nbsp;1 ALCANZADO &mdash; la encuesta puede cerrarse con '
            'aprobaci&oacute;n de la Direcci&oacute;n / CEO.</div>')
    else:
        faltan = max(0, s['threshold'] - s['si'])
        banner = (
            f'<div style="background:#fff3cd;color:#856404;padding:14px 18px;border-radius:10px;'
            f'text-align:center;font-size:14px;font-weight:bold;margin-bottom:18px;">'
            f'Faltan <span style="font-size:18px;">{faltan}</span> voto(s) S&Iacute; para '
            f'alcanzar el umbral de {s["threshold"]} (50%+1 de {s["base"]}).</div>')

    def cell(num, lbl, color):
        return (f'<td width="25%" style="text-align:center;padding:10px 6px;">'
                f'<div style="font-size:30px;font-weight:bold;color:{color};line-height:1.1;">{num}</div>'
                f'<div style="font-size:11px;color:#666;margin-top:3px;">{lbl}</div></td>')

    return f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;"><tr>
<td align="center" style="padding:26px 12px;">
<table cellpadding="0" cellspacing="0" width="600" style="max-width:600px;background:#fff;
       border-radius:14px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1);">
  <tr><td style="background:linear-gradient(135deg,#1a2c5b,#2471a3);padding:26px 30px;text-align:center;">
    <div style="color:#fff;font-size:18px;font-weight:bold;">📊 Encuesta Plan de Contingencia Acad&eacute;mica</div>
    <div style="color:rgba(255,255,255,0.85);font-size:12px;margin-top:5px;">
      Reporte de avance &mdash; cierre de votaci&oacute;n: {SURVEY_DEADLINE}</div></td></tr>
  <tr><td style="padding:24px 30px 4px;">{banner}

    <p style="margin:0 0 8px;font-size:11px;font-weight:bold;color:#888;text-transform:uppercase;letter-spacing:.5px;">Respuesta de los representantes</p>
    <table cellpadding="0" cellspacing="0" width="100%" style="background:#f8fafc;border:1px solid #e3e9f2;border-radius:10px;margin-bottom:8px;"><tr>
      {cell(s['si'], 'SÍ (de acuerdo)', '#1b5e20')}
      {cell(s['no'], 'NO', '#856404')}
      {cell(s['pend'], 'Pendientes', '#5f6b7a')}
      {cell(str(s['participation'])+'%', 'Participación', '#1a2c5b')}
    </tr></table>

    <div style="margin:16px 0 6px;font-size:12px;color:#444;">
      <strong>Avance hacia 50%+1</strong> &nbsp;
      <span style="color:#1b5e20;font-weight:bold;">{s['si']}</span> / {s['threshold']}
      <span style="color:#999;">(base {s['base']})</span></div>
    <div style="font-family:monospace;font-size:15px;color:#1b5e20;letter-spacing:1px;">{_bar(s['si'], s['threshold'])}</div>

    <p style="margin:22px 0 8px;font-size:11px;font-weight:bold;color:#888;text-transform:uppercase;letter-spacing:.5px;">Entrega de correos</p>
    <table cellpadding="6" cellspacing="0" width="100%" style="font-size:13px;color:#444;border:1px solid #e3e9f2;border-radius:8px;">
      <tr style="background:#f8fafc;"><td>✅ Enviados</td><td style="text-align:right;font-weight:bold;color:#1b5e20;">{s['sent']}</td></tr>
      <tr><td>⏳ En cola</td><td style="text-align:right;">{s['outgoing']}</td></tr>
      <tr style="background:#f8fafc;"><td>⚠️ Fallidos</td><td style="text-align:right;color:{'#c0392b' if s['failed'] else '#999'};">{s['failed']}</td></tr>
      <tr><td>🗳️ Boletas emitidas (total)</td><td style="text-align:right;font-weight:bold;">{s['total']}</td></tr>
    </table>

    <p style="margin:18px 0 0;font-size:11px;color:#aaa;line-height:1.6;">
      Monitoreo en vivo: AI Agent &rarr; Operaciones &rarr; Comunicados a Representantes
      (agrupar por Campa&ntilde;a). Opci&oacute;n A = S&Iacute;, Opci&oacute;n B = NO.
      El umbral 50%+1 usa base = {s['base']} (par&aacute;metro <i>contingencia.plantilla_total</i>).
    </p>
  </td></tr>
  <tr><td style="background:#f8f9fa;border-top:1px solid #e8e8e8;padding:14px 30px;text-align:center;font-size:11px;color:#aaa;">
    Reporte autom&aacute;tico &mdash; Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;</td></tr>
</table></td></tr></table></body></html>"""


import datetime

STATE_PATH = '/opt/odoo-dev/scripts/contingencia_digest_state.json'
# Auto-stop: cron mode goes silent once the voting window is closed.
CRON_STOP_AFTER = datetime.date(2026, 7, 2)   # day after the 2026-07-01 deadline


def _load_state():
    try:
        return json.load(open(STATE_PATH))
    except (OSError, ValueError):
        return {}


def _save_state(s):
    json.dump({'si': s['si'], 'no': s['no'], 'pend': s['pend'],
               'reached': s['reached']}, open(STATE_PATH, 'w'))


def _send(m, db, uid, key, s, recipients):
    html = build_html(s)
    subject = DIGEST_SUBJECT + (' — ✅ 50%+1 alcanzado' if s['reached']
                                else f" — SÍ {s['si']}/{s['threshold']}")
    mid = _call(m, db, uid, key, 'mail.mail', 'create', [{
        'subject': subject,
        'email_from': SENDER,
        'email_to': ', '.join(recipients),
        'reply_to': 'votacion@ueipab.edu.ve',
        'body_html': html,
        'state': 'outgoing',
    }])
    try:
        _call(m, db, uid, key, 'mail.mail', 'send', [[mid]])
    except xmlrpc.client.Fault as exc:
        # mail.mail.send() returns None → XML-RPC 'cannot marshal None'. The send
        # already executed server-side; treat this specific fault as success.
        if 'cannot marshal None' not in str(exc):
            raise
    print('✅ Digest sent to %s (mail.mail id=%s).' % (', '.join(recipients), mid))


def _digest_to(m, db, uid, key):
    raw = _param(m, db, uid, key, 'contingencia.digest_to', CEO_EMAIL)
    return [a.strip() for a in raw.replace(';', ',').split(',') if a.strip()]


def main(live, test, cron):
    # cron mode auto-stops after the voting window closes.
    if cron and datetime.date.today() >= CRON_STOP_AFTER:
        print('Voting window closed — cron digest disabled. Remove the cron file.')
        return

    m, db, uid, key = _connect()
    s = gather(m, db, uid, key)

    print('=' * 64)
    print('CONTINGENCIA SURVEY DIGEST  (db=%s)' % db)
    print('  SÍ=%d  NO=%d  Pendientes=%d  | participación=%s%%' %
          (s['si'], s['no'], s['pend'], s['participation']))
    print('  threshold(50%%+1)=%d of base %d → %s' %
          (s['threshold'], s['base'], 'REACHED ✅' if s['reached'] else 'not yet'))
    print('  delivery: sent=%d outgoing=%d failed=%d (ballots=%d)' %
          (s['sent'], s['outgoing'], s['failed'], s['total']))
    print('=' * 64)

    if cron:
        # Send only when the tally changed since last send, or when 50%+1 first
        # flips — keeps a 20-min cadence fresh without identical-report spam.
        prev = _load_state()
        changed = (prev.get('si') != s['si'] or prev.get('no') != s['no']
                   or prev.get('pend') != s['pend'])
        newly_reached = s['reached'] and not prev.get('reached')
        if not prev or changed or newly_reached:
            _send(m, db, uid, key, s, _digest_to(m, db, uid, key))
            _save_state(s)
        else:
            print('No change since last digest — skipped (cron).')
        return

    if not (live or test):
        print('DRY RUN — no email sent. Use --test (CEO), --live (recipients), or --cron.')
        return

    recipients = [CEO_EMAIL] if test else _digest_to(m, db, uid, key)
    _send(m, db, uid, key, s, recipients)
    if live:
        _save_state(s)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--live', action='store_true', help='Send to contingencia.digest_to')
    p.add_argument('--test', action='store_true', help='Preview to CEO only')
    p.add_argument('--cron', action='store_true',
                   help='Send only if the tally changed (for the 20-min cron); auto-stops after the window')
    a = p.parse_args()
    main(live=a.live, test=a.test, cron=a.cron)
