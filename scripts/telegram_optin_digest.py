#!/usr/bin/env python3
"""
telegram_optin_digest.py
-------------------------
Standalone digest for the Telegram opt-in campaign — tracks which Representante
parents have linked their Telegram account via the FAM_ deep-link.

Sends once per day (or on demand) to the CEO team. Only sends when there are
new linkings since the last run (no inbox spam when nothing changed).

Cron: /etc/cron.d/telegram_optin_digest
  Once daily at 09:00 VET (13:00 UTC) during opt-in campaign window.

Usage:
    python3 scripts/telegram_optin_digest.py            # dry-run
    python3 scripts/telegram_optin_digest.py --live     # send if new linkings
    python3 scripts/telegram_optin_digest.py --force    # send regardless of delta
"""

import os, sys, json, logging, argparse, xmlrpc.client
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

STATE_FILE   = os.path.join(os.path.dirname(__file__), 'telegram_optin_digest_state.json')
PROD_CFG     = '/opt/odoo-dev/config/production.json'
GSHEET_CREDS = '/opt/odoo-dev/config/google_sheets_credentials.json'
SHEET_ID     = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
ODOO_URL     = 'https://odoo.ueipab.edu.ve'
LOGO_URL     = f'{ODOO_URL}/web/image/res.company/1/logo'

RECIPIENTS = [
    ('Gustavo Perdomo', 'gustavo.perdomo@ueipab.edu.ve'),
    ('Arcides Arzola',  'arcides.arzola@ueipab.edu.ve'),
]


# ── Config ─────────────────────────────────────────────────────────────────────

def _connect():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    url, db, user, key = cfg['url'], cfg['db'], cfg['user'], cfg['api_key']
    uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, db, uid, key


def _load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def _save_state(s):
    json.dump(s, open(STATE_FILE, 'w'), indent=2, default=str)


# ── Data ───────────────────────────────────────────────────────────────────────

def _load_sheet_parents():
    """Load ACTIVE parents from Google Sheet Customers tab — same source as all campaign scripts."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        GSHEET_CREDS, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc  = build('sheets', 'v4', credentials=creds)
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Customers!A2:M').execute().get('values', [])
    data = rows[1:]  # skip header row

    parents = []
    for row in data:
        r      = (row + [''] * 13)[:13]
        name   = r[1].strip()
        status = r[2].strip().upper()
        emails_raw = r[9].strip()
        if not name or status != 'ACTIVE':
            continue
        emails = [e.strip().lower() for e in emails_raw.split(';') if e.strip()]
        parents.append({'name': name, 'emails': emails})

    log.info("Sheet: %d ACTIVE parents loaded", len(parents))
    return parents


def _fetch_status(models, db, uid, key):
    """Match ACTIVE sheet parents to res.partner and check telegram_chat_id."""
    sheet_parents = _load_sheet_parents()

    # Build email → partner lookup from Odoo
    all_emails = [e for p in sheet_parents for e in p['emails']]
    # Search in batches to avoid huge domain
    partner_map = {}  # email → partner record
    for i in range(0, len(all_emails), 100):
        batch = all_emails[i:i+100]
        rows  = models.execute_kw(db, uid, key, 'res.partner', 'search_read',
            [[('email', 'in', batch)]],
            {'fields': ['id', 'name', 'email', 'telegram_chat_id'], 'limit': 200})
        for r in rows:
            for em in (r['email'] or '').lower().split(';'):
                partner_map[em.strip()] = r

    linked   = []
    unlinked = []
    for p in sheet_parents:
        partner = None
        for em in p['emails']:
            if em in partner_map:
                partner = partner_map[em]
                break
        if partner and partner.get('telegram_chat_id'):
            linked.append({
                'name':             p['name'],
                'email':            p['emails'][0] if p['emails'] else '—',
                'telegram_chat_id': partner['telegram_chat_id'],
            })
        else:
            unlinked.append({
                'name':  p['name'],
                'email': p['emails'][0] if p['emails'] else '—',
            })

    total = len(sheet_parents)
    pct   = round(len(linked) / total * 100) if total else 0
    return {
        'total':    total,
        'linked':   linked,
        'unlinked': unlinked,
        'pct':      pct,
    }


# ── HTML ───────────────────────────────────────────────────────────────────────

def _build_html(status, delta, state):
    now_str  = datetime.now().strftime('%d/%m/%Y %H:%M VET')
    last_str = state.get('last_send', '—')
    linked   = status['linked']
    unlinked = status['unlinked']
    total    = status['total']
    pct      = status['pct']
    pct_bar  = max(4, pct)

    linked_rows = ''.join(
        f'<tr style="border-bottom:1px solid #f0f0f0;">'
        f'<td style="padding:5px 8px;font-size:12px;font-weight:bold;color:#0d47a1;">'
        f'{p["name"]}</td>'
        f'<td style="padding:5px 8px;font-size:11px;color:#888;">{p.get("email") or "—"}</td>'
        f'<td style="padding:5px 8px;font-size:11px;color:#aaa;font-family:monospace;">'
        f'{p["telegram_chat_id"]}</td>'
        f'</tr>'
        for p in linked
    ) if linked else (
        '<tr><td colspan="3" style="padding:10px 8px;font-size:12px;color:#aaa;text-align:center;">'
        'Ningún padre ha vinculado aún</td></tr>'
    )

    unlinked_rows = ''.join(
        f'<tr style="border-bottom:1px solid #f0f0f0;">'
        f'<td style="padding:4px 8px;font-size:12px;color:#555;">{p["name"]}</td>'
        f'<td style="padding:4px 8px;font-size:11px;color:#999;">{p.get("email") or "—"}</td>'
        f'</tr>'
        for p in unlinked[:20]
    )
    more_unlinked = (
        f'<tr><td colspan="2" style="padding:6px 8px;font-size:11px;color:#aaa;text-align:center;">'
        f'... y {len(unlinked) - 20} más sin vincular</td></tr>'
    ) if len(unlinked) > 20 else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:24px 12px;">
<table cellpadding="0" cellspacing="0" width="580"
       style="max-width:580px;background:#fff;border-radius:14px;
              box-shadow:0 4px 20px rgba(0,0,0,0.10);overflow:hidden;">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#006aaa 0%,#0088cc 100%);
               padding:24px 28px 20px;text-align:center;">
      <img src="{LOGO_URL}" alt="UEIPAB" width="60" height="60"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 12px;"/>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:4px;">
        REPORTE TELEGRAM OPT-IN
      </div>
      <h1 style="margin:0;color:#fff;font-size:18px;font-weight:bold;">
        ✈️ Vinculación Glenda — Telegram
      </h1>
      <div style="margin-top:6px;font-size:12px;color:rgba(255,255,255,0.8);">
        {now_str} &nbsp;·&nbsp; Último reporte: {last_str}
      </div>
    </td>
  </tr>

  <!-- Counts -->
  <tr>
    <td style="padding:24px 28px 0;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#e3f2fd;border:2px solid #90caf9;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#0d47a1;margin-bottom:4px;">VINCULADOS</div>
              <div style="font-size:40px;font-weight:bold;color:#0088cc;line-height:1;">{len(linked)}</div>
              <div style="font-size:11px;color:#1565c0;margin-top:4px;">{pct}%</div>
            </div>
          </td>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#fff8e1;border:2px solid #ffe082;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#e65100;margin-bottom:4px;">SIN VINCULAR</div>
              <div style="font-size:40px;font-weight:bold;color:#e65100;line-height:1;">{len(unlinked)}</div>
              <div style="font-size:11px;color:#e65100;margin-top:4px;">{100-pct}%</div>
            </div>
          </td>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#f3e5f5;border:2px solid #ce93d8;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#4a148c;margin-bottom:4px;">TOTAL REPRES.</div>
              <div style="font-size:40px;font-weight:bold;color:#6a1b9a;line-height:1;">{total}</div>
              <div style="font-size:11px;color:#6a1b9a;margin-top:4px;">familias</div>
            </div>
          </td>
        </tr>
      </table>

      <!-- Progress bar -->
      <div style="margin-top:20px;">
        <div style="display:flex;justify-content:space-between;font-size:11px;
                    color:#888;margin-bottom:4px;">
          <span>Progreso de vinculación</span>
          <span><strong>{len(linked)}/{total}</strong> ({pct}%)</span>
        </div>
        <div style="background:#e8edf3;border-radius:4px;height:12px;width:100%;">
          <div style="background:#0088cc;border-radius:4px;height:12px;width:{pct_bar}%;"></div>
        </div>
      </div>

      {"" if delta == 0 else f'''
      <div style="margin-top:16px;background:#e8f5e9;border:1px solid #66bb6a;
                  border-radius:8px;padding:12px 16px;font-size:13px;color:#1b5e20;">
        🆕 <strong>+{delta} nuevo(s) vínculo(s)</strong> desde el último reporte
      </div>'''}
    </td>
  </tr>

  <!-- Linked list -->
  <tr>
    <td style="padding:20px 28px 0;">
      <div style="font-size:13px;font-weight:bold;color:#0088cc;margin-bottom:8px;">
        ✅ Padres vinculados ({len(linked)})
      </div>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid #dde;border-radius:6px;overflow:hidden;">
        <thead>
          <tr style="background:#e3f2fd;">
            <th style="padding:6px 8px;text-align:left;font-size:11px;color:#0d47a1;">Representante</th>
            <th style="padding:6px 8px;text-align:left;font-size:11px;color:#0d47a1;">Email</th>
            <th style="padding:6px 8px;text-align:left;font-size:11px;color:#0d47a1;">Telegram ID</th>
          </tr>
        </thead>
        <tbody>{linked_rows}</tbody>
      </table>
    </td>
  </tr>

  <!-- Unlinked list (first 20) -->
  <tr>
    <td style="padding:16px 28px 24px;">
      <div style="font-size:13px;font-weight:bold;color:#e65100;margin-bottom:8px;">
        ⏳ Pendientes de vincular ({len(unlinked)})
      </div>
      <table cellpadding="0" cellspacing="0" width="100%"
             style="border:1px solid #ffe0b2;border-radius:6px;overflow:hidden;">
        <thead>
          <tr style="background:#fff8e1;">
            <th style="padding:5px 8px;text-align:left;font-size:11px;color:#e65100;">Representante</th>
            <th style="padding:5px 8px;text-align:left;font-size:11px;color:#e65100;">Email</th>
          </tr>
        </thead>
        <tbody>{unlinked_rows}{more_unlinked}</tbody>
      </table>
    </td>
  </tr>

  <!-- Footer -->
  <tr>
    <td style="background:#f8f9fa;padding:12px 24px;text-align:center;
               font-size:10px;color:#aaa;border-top:1px solid #e8e8e8;">
      Reporte Telegram Opt-in · Campaña vinculación @GlendaUeipabBot ·
      <a href="mailto:soporte@ueipab.edu.ve" style="color:#0088cc;">soporte@ueipab.edu.ve</a>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main(live, force):
    models, db, uid, key = _connect()
    state  = _load_state()
    status = _fetch_status(models, db, uid, key)

    last_linked = state.get('last_linked', -1)
    delta       = len(status['linked']) - max(last_linked, 0)

    log.info("Telegram opt-in — linked:%d/%d | delta:+%d",
             len(status['linked']), status['total'], delta)

    if last_linked >= 0 and delta == 0 and not force:
        log.info("No new linkings since last run — skipping send.")
        return

    html    = _build_html(status, delta, state)
    subject = (
        f"✈️ Telegram Opt-in — {len(status['linked'])}/{status['total']} vinculados"
        f"{f' (+{delta} nuevos)' if delta > 0 else ''}"
    )

    if not live:
        log.info("DRY RUN — would send: %s", subject)
        return

    email_to = ', '.join(f'{n} <{e}>' for n, e in RECIPIENTS)
    mail_id  = models.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
        'subject':    subject,
        'email_from': 'Glenda UEIPAB <soporte@ueipab.edu.ve>',
        'email_to':   email_to,
        'body_html':  html,
        'state':      'outgoing',
    }]])
    try:
        models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
    except Exception as e:
        log.warning("Could not trigger mail queue: %s", e)

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    state.update({'last_linked': len(status['linked']), 'last_send': now_str})
    _save_state(state)
    log.info("Digest sent — mail id=%s | %s", mail_id, subject)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live',  action='store_true', help='Actually send email')
    parser.add_argument('--force', action='store_true', help='Send even if no new linkings')
    args = parser.parse_args()
    main(live=args.live, force=args.force)
