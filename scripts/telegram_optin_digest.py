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

import os, sys, json, logging, argparse, unicodedata, xmlrpc.client
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
]

LAST_GRADE = '5to. Año'  # single-student families in this grade excluded from campaign


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

INCLUDE_STATUSES = {'ACTIVE', 'PIPELINE'}


def _load_quinto_excluded_from_sheet(svc):
    """Return set of parent names (uppercase) where ALL grades in cols U-Z are LAST_GRADE.
    Source: Google Sheet Customers tab cols U-Z (grades per student per row).
    """
    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Customers!A2:Z').execute().get('values', [])
    data = rows[1:]  # row 2 is the 'Grades' sub-header

    excluded = set()
    for row in data:
        r      = (row + [''] * 26)[:26]
        name   = r[1].strip()
        status = r[2].strip().upper()
        if not name or status not in INCLUDE_STATUSES:
            continue
        grades = [r[i].strip() for i in range(20, 26)
                  if r[i].strip() and r[i].strip() != '#N/A']
        if grades and all(g.lower() == LAST_GRADE.lower() for g in grades):
            excluded.add(name.upper())

    log.info("Sheet: %d families excluded (all students in %s)", len(excluded), LAST_GRADE)
    return excluded


def _load_sheet_parents():
    """Load ACTIVE + PIPELINE parents from Google Sheet Customers tab (cols A-Z).
    Excludes families where ALL students are in LAST_GRADE (cols U-Z).
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        GSHEET_CREDS, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc  = build('sheets', 'v4', credentials=creds)

    # Build exclusion set from cols U-Z before loading parents
    excluded = _load_quinto_excluded_from_sheet(svc)

    rows = svc.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range='Customers!A2:Z').execute().get('values', [])
    data = rows[1:]  # skip grades sub-header row

    parents = []
    for row in data:
        r      = (row + [''] * 26)[:26]
        name   = r[1].strip()
        status = r[2].strip().upper()
        emails_raw = r[9].strip()
        if not name or status not in INCLUDE_STATUSES:
            continue
        if name.upper() in excluded:
            continue
        emails = [e.strip().lower() for e in emails_raw.split(';') if e.strip()]
        parents.append({'name': name, 'emails': emails, 'status': status})

    counts = {s: sum(1 for p in parents if p['status'] == s) for s in INCLUDE_STATUSES}
    log.info("Sheet: %d parents loaded after exclusion %s", len(parents), counts)
    return parents


def _apply_exclusions(parents, excluded_names):
    """Remove single-5to-Año families from parent list."""
    filtered = [p for p in parents if p['name'].upper() not in excluded_names]
    skipped  = len(parents) - len(filtered)
    if skipped:
        log.info("Excluded %d %s-only single-student families", skipped, LAST_GRADE)
    return filtered


def _fetch_employee_status(models, db, uid, key):
    """Check which active employees have linked Telegram via EMP_ deep-link or FAM_ test."""
    emps = models.execute_kw(db, uid, key, 'hr.employee', 'search_read',
        [[['active', '=', True]]],
        {'fields': ['id', 'name', 'work_email', 'user_id', 'job_id'], 'limit': 200})

    # Build user_id → partner_id map
    user_ids = [e['user_id'][0] for e in emps if e.get('user_id')]
    users = models.execute_kw(db, uid, key, 'res.users', 'search_read',
        [[['id', 'in', user_ids]]],
        {'fields': ['id', 'partner_id'], 'limit': 200})
    user_to_partner = {u['id']: u['partner_id'][0] for u in users if u.get('partner_id')}

    emp_partner_ids = list(user_to_partner.values())

    # Source 1: Telegram conversations linked to employee partner
    tg_convs = models.execute_kw(db, uid, key, 'ai.agent.conversation', 'search_read',
        [[['channel', '=', 'telegram'], ['partner_id', 'in', emp_partner_ids]]],
        {'fields': ['partner_id', 'telegram_chat_id'], 'limit': 500})
    conv_linked_partners = {
        c['partner_id'][0] for c in tg_convs if c.get('partner_id')
    }

    # Source 2: res.partner.telegram_chat_id directly
    if emp_partner_ids:
        partners = models.execute_kw(db, uid, key, 'res.partner', 'search_read',
            [[['id', 'in', emp_partner_ids], ['telegram_chat_id', '!=', False]]],
            {'fields': ['id', 'telegram_chat_id'], 'limit': 200})
        direct_linked_partners = {p['id'] for p in partners}
    else:
        direct_linked_partners = set()

    all_linked_partners = conv_linked_partners | direct_linked_partners

    linked   = []
    unlinked = []
    for e in emps:
        uid_val    = e['user_id'][0] if e.get('user_id') else None
        partner_id = user_to_partner.get(uid_val) if uid_val else None
        job        = e['job_id'][1] if e.get('job_id') else '—'
        entry = {'name': e['name'], 'email': e.get('work_email') or '—', 'job': job}
        if partner_id and partner_id in all_linked_partners:
            linked.append(entry)
        else:
            unlinked.append(entry)

    return {
        'total':    len(emps),
        'linked':   linked,
        'unlinked': unlinked,
        'pct':      round(len(linked) / len(emps) * 100) if emps else 0,
    }


def _fetch_status(models, db, uid, key):
    """Match ACTIVE+PIPELINE sheet parents (excl. 5to Año only) to res.partner."""
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
                'status':           p['status'],
            })
        else:
            unlinked.append({
                'name':   p['name'],
                'email':  p['emails'][0] if p['emails'] else '—',
                'status': p['status'],
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

def _build_html(status, delta, state, emp_status=None):
    now_str  = datetime.now().strftime('%d/%m/%Y %H:%M VET')
    last_str = state.get('last_send', '—')
    linked   = status['linked']
    unlinked = status['unlinked']
    total    = status['total']
    pct      = status['pct']
    pct_bar  = max(4, pct)

    def _status_badge(s):
        color = '#2e7d32' if s == 'ACTIVE' else '#e65100'
        bg    = '#e8f5e9' if s == 'ACTIVE' else '#fff3e0'
        return (f'<span style="font-size:9px;font-weight:bold;color:{color};'
                f'background:{bg};padding:1px 5px;border-radius:4px;">{s}</span>')

    linked_rows = ''.join(
        f'<tr style="border-bottom:1px solid #f0f0f0;">'
        f'<td style="padding:5px 8px;font-size:12px;font-weight:bold;color:#0d47a1;">'
        f'{p["name"]} {_status_badge(p.get("status",""))}</td>'
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
        f'<td style="padding:4px 8px;font-size:12px;color:#555;">'
        f'{p["name"]} {_status_badge(p.get("status",""))}</td>'
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

  <!-- Employee section -->
  {f"""
  <tr>
    <td style="padding:0 28px 24px;">
      <div style="border-top:2px solid #e8edf3;margin:4px 0 16px;"></div>
      <div style="font-size:13px;font-weight:bold;color:#1a2c5b;margin-bottom:10px;">
        👥 Empleados — Telegram vinculado
      </div>
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#e8f5e9;border:2px solid #a5d6a7;border-radius:10px;padding:12px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#1b5e20;margin-bottom:2px;">VINCULADOS</div>
              <div style="font-size:32px;font-weight:bold;color:#2e7d32;">{emp_status['linked'].__len__()}</div>
              <div style="font-size:11px;color:#388e3c;">{emp_status['pct']}%</div>
            </div>
          </td>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#fff8e1;border:2px solid #ffe082;border-radius:10px;padding:12px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#e65100;margin-bottom:2px;">SIN VINCULAR</div>
              <div style="font-size:32px;font-weight:bold;color:#e65100;">{emp_status['unlinked'].__len__()}</div>
              <div style="font-size:11px;color:#e65100;">{100-emp_status['pct']}%</div>
            </div>
          </td>
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#f3e5f5;border:2px solid #ce93d8;border-radius:10px;padding:12px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#4a148c;margin-bottom:2px;">TOTAL</div>
              <div style="font-size:32px;font-weight:bold;color:#6a1b9a;">{emp_status['total']}</div>
              <div style="font-size:11px;color:#6a1b9a;">empleados</div>
            </div>
          </td>
        </tr>
      </table>
      {"" if not emp_status['linked'] else f'''
      <div style="margin-top:14px;">
        <div style="font-size:12px;font-weight:bold;color:#2e7d32;margin-bottom:6px;">
          ✅ Empleados vinculados ({len(emp_status["linked"])})
        </div>
        <table cellpadding="0" cellspacing="0" width="100%"
               style="border:1px solid #c8e6c9;border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:#e8f5e9;">
              <th style="padding:5px 8px;text-align:left;font-size:11px;color:#1b5e20;">Nombre</th>
              <th style="padding:5px 8px;text-align:left;font-size:11px;color:#1b5e20;">Cargo</th>
            </tr>
          </thead>
          <tbody>
            {"".join(
              "<tr style='border-bottom:1px solid #f0f0f0;'>"
              f"<td style='padding:4px 8px;font-size:12px;color:#1a2c5b;'>{e['name']}</td>"
              f"<td style='padding:4px 8px;font-size:11px;color:#666;'>{e['job']}</td>"
              "</tr>"
              for e in emp_status["linked"]
            )}
          </tbody>
        </table>
      </div>''' }
    </td>
  </tr>""" if emp_status else ""}

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
    state      = _load_state()
    status     = _fetch_status(models, db, uid, key)
    emp_status = _fetch_employee_status(models, db, uid, key)

    last_linked = state.get('last_linked', -1)
    delta       = len(status['linked']) - max(last_linked, 0)

    active_total   = sum(1 for p in status['linked'] + status['unlinked'] if p.get('status') == 'ACTIVE')
    pipeline_total = sum(1 for p in status['linked'] + status['unlinked'] if p.get('status') == 'PIPELINE')
    log.info("Telegram opt-in — parents:%d/%d (active:%d pipeline:%d) | empl:%d/%d | delta:+%d",
             len(status['linked']), status['total'], active_total, pipeline_total,
             len(emp_status['linked']), emp_status['total'], delta)

    if last_linked >= 0 and delta == 0 and not force:
        log.info("No new linkings since last run — skipping send.")
        return

    html    = _build_html(status, delta, state, emp_status=emp_status)
    subject = (
        f"✈️ Telegram Opt-in — Padres:{len(status['linked'])}/{status['total']}"
        f" | Empl:{len(emp_status['linked'])}/{emp_status['total']}"
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
