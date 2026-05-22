"""
Pending Follow-up Digest — Consulta Presupuestaria & PDVSA Continuidad 2026-2027
==================================================================================
Staff-oriented digest showing pending parents across both campaigns with full
contact info (name, email, mobile) so customer support can follow up directly.

Two sections:
  🗳️  Budget vote pending  — everyone who hasn't voted yet
  🏭  PDVSA continuity pending — PDVSA families who haven't responded yet

Usage:
    python3 scripts/pending_followup_digest.py            # dry-run
    python3 scripts/pending_followup_digest.py --live     # send to all RECIPIENTS
    python3 scripts/pending_followup_digest.py --test     # send to CEO only (test)
"""
import os, sys, json, logging, argparse, xmlrpc.client
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

PROD_CFG    = '/opt/odoo-dev/config/production.json'
ODOO_URL    = 'https://odoo.ueipab.edu.ve'
LOGO_URL    = f'{ODOO_URL}/web/image/res.company/1/logo'
MONITOR_URL = f'{ODOO_URL}/web#action=840&cids=1&menu_id=580'

RECIPIENTS = [
    ('Gustavo Perdomo',  'gustavo.perdomo@ueipab.edu.ve'),
    ('Arcides Arzola',   'arcides.arzola@ueipab.edu.ve'),
    ('Alberto Perdomo',  'alberto.perdomo@ueipab.edu.ve'),
]
TEST_RECIPIENT = ('Gustavo Perdomo', 'gustavo.perdomo@ueipab.edu.ve')


# ── Odoo connection ────────────────────────────────────────────────────────────

def _connect():
    cfg    = json.load(open(PROD_CFG))['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/common')
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    models = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/object')
    return models, cfg['db'], uid, cfg['api_key']


def call(models, db, uid, key, model, method, args=None, kw=None):
    return models.execute_kw(db, uid, key, model, method, args or [[]], kw or {})


# ── Data fetching ──────────────────────────────────────────────────────────────

def _pid(a):
    return a['partner_id'][0] if isinstance(a['partner_id'], list) else a['partner_id']


def _fetch_data(models, db, uid, key):
    # PDVSA partner ids (tag 26)
    pdvsa_partners = call(models, db, uid, key, 'res.partner', 'search_read',
        [[['category_id', 'in', [26]]]],
        {'fields': ['id', 'name', 'mobile', 'email'], 'limit': 300})
    pdvsa_ids   = {p['id'] for p in pdvsa_partners}
    partner_map = {p['id']: p for p in pdvsa_partners}

    # Budget ACKs
    budget_acks = call(models, db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', 'budget_consulta_2026_2027']]],
        {'fields': ['partner_id', 'partner_name', 'partner_email', 'partner_phone',
                    'state', 'sent_date', 'bounce_wa_sent', 'ack_date'], 'limit': 500})

    # PDVSA continuity ACKs
    pdvsa_acks = call(models, db, uid, key, 'partner.communication.ack', 'search_read',
        [[['notice_key', '=', 'pdvsa_continuacion_2026_2027']]],
        {'fields': ['partner_id', 'partner_name', 'partner_email', 'partner_phone',
                    'state', 'sent_date', 'bounce_wa_sent', 'ack_date'], 'limit': 300})

    budget_map = {_pid(a): a for a in budget_acks}
    pdvsa_map  = {_pid(a): a for a in pdvsa_acks}

    # Fill partner_map for any partner not in PDVSA list
    missing = [p for p in set(budget_map) | set(pdvsa_map) if p not in partner_map]
    if missing:
        for p in call(models, db, uid, key, 'res.partner', 'read',
                      [missing], {'fields': ['id', 'name', 'mobile', 'email']}):
            partner_map[p['id']] = p

    # Summary numbers
    b_continuing = sum(1 for a in budget_acks if a['state'] == 'continuing')
    b_leaving    = sum(1 for a in budget_acks if a['state'] == 'leaving')
    b_pending    = sum(1 for a in budget_acks if a['state'] == 'pending')
    b_total      = len(budget_acks)
    b_voted      = b_continuing + b_leaving
    goal         = (b_total // 2) + 1
    goal_met     = b_continuing >= goal

    p_continuing = sum(1 for a in pdvsa_acks if a['state'] == 'continuing')
    p_leaving    = sum(1 for a in pdvsa_acks if a['state'] == 'leaving')
    p_pending    = sum(1 for a in pdvsa_acks if a['state'] == 'pending')
    p_total      = len(pdvsa_acks)

    return {
        'budget_map':  budget_map,
        'pdvsa_map':   pdvsa_map,
        'pdvsa_ids':   pdvsa_ids,
        'partner_map': partner_map,
        'summary': {
            'b_continuing': b_continuing, 'b_leaving': b_leaving,
            'b_pending': b_pending, 'b_total': b_total, 'b_voted': b_voted,
            'b_pct_voted': round(b_voted / b_total * 100) if b_total else 0,
            'p_continuing': p_continuing, 'p_leaving': p_leaving,
            'p_pending': p_pending, 'p_total': p_total,
            'goal': goal, 'goal_met': goal_met,
        },
    }


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _phone_link(mobile):
    if not mobile:
        return '<span style="color:#ccc;">—</span>'
    clean = mobile.replace(' ', '').replace('-', '').lstrip('+')
    return (f'<a href="https://wa.me/{clean}" target="_blank"'
            f' style="color:#25D366;text-decoration:none;font-weight:bold;">'
            f'📱 {mobile}</a>')


def _wa_badge(sent):
    if sent:
        return '<span style="background:#e8f5e9;color:#2e7d32;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:bold;">WA ✓</span>'
    return '<span style="background:#fafafa;color:#aaa;padding:2px 7px;border-radius:10px;font-size:10px;border:1px solid #eee;">WA —</span>'


def _row(pid, partner_map, b_ack, c_ack, badge_html):
    partner = partner_map.get(pid, {})
    mobile  = partner.get('mobile') or (b_ack or c_ack or {}).get('partner_phone') or ''
    email   = (b_ack or c_ack or {}).get('partner_email') or partner.get('email') or '—'
    name    = (b_ack or c_ack or {}).get('partner_name') or partner.get('name') or f'id={pid}'
    wa_sent = (b_ack or c_ack or {}).get('bounce_wa_sent', False)

    return f"""
<tr style="border-bottom:1px solid #f0f0f0;">
  <td style="padding:8px 10px;vertical-align:top;">
    <div style="font-size:13px;font-weight:bold;color:#1a2c5b;">{name}</div>
    <div style="font-size:11px;color:#888;margin-top:1px;">{email}</div>
  </td>
  <td style="padding:8px 10px;vertical-align:middle;white-space:nowrap;">
    {_phone_link(mobile or None)}
  </td>
  <td style="padding:8px 10px;vertical-align:middle;text-align:center;">
    {badge_html}
  </td>
  <td style="padding:8px 10px;vertical-align:middle;text-align:center;">
    {_wa_badge(wa_sent)}
  </td>
</tr>"""


def _table(rows_html):
    if not rows_html:
        return ('<div style="padding:12px 14px;background:#f8f9fa;border-radius:6px;'
                'font-size:12px;color:#aaa;">✅ Sin pendientes en esta sección.</div>')
    return f"""
<table cellpadding="0" cellspacing="0" width="100%"
       style="border:1px solid #dde;border-radius:8px;overflow:hidden;margin-top:8px;">
  <thead>
    <tr style="background:#f0f4fa;">
      <th style="padding:7px 10px;text-align:left;font-size:11px;color:#555;width:40%;">Representante / Email</th>
      <th style="padding:7px 10px;text-align:left;font-size:11px;color:#555;width:24%;">Teléfono WA</th>
      <th style="padding:7px 10px;text-align:center;font-size:11px;color:#555;width:20%;">Estado</th>
      <th style="padding:7px 10px;text-align:center;font-size:11px;color:#555;width:16%;">WA enviado</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>"""


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(d):
    s       = d['summary']
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M VET')

    goal_block = (
        f'<div style="margin-top:6px;font-size:11px;color:#2e7d32;font-weight:bold;">✅ Meta alcanzada — Opción A con {s["b_continuing"]} votos</div>'
        if s['goal_met'] else
        f'<div style="margin-top:6px;font-size:11px;color:#e65100;">🎯 Faltan {s["goal"] - s["b_continuing"]} votos para mayoría ({s["goal"]} = 50%+1 de {s["b_total"]})</div>'
    )

    # ── Section 1: budget pending ──────────────────────────────────────────────
    budget_rows = ''
    budget_pending_pids = sorted(
        [pid for pid, a in d['budget_map'].items() if a['state'] == 'pending'],
        key=lambda p: (d['budget_map'].get(p) or {}).get('partner_name') or ''
    )
    for pid in budget_pending_pids:
        b_ack    = d['budget_map'].get(pid)
        c_ack    = d['pdvsa_map'].get(pid)
        is_pdvsa = pid in d['pdvsa_ids']
        badge    = ('<span style="background:#e8f0fb;color:#1a2c5b;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;">PDVSA</span>'
                    if is_pdvsa else
                    '<span style="background:#f3f4f6;color:#888;padding:2px 8px;border-radius:10px;font-size:10px;">Regular</span>')
        budget_rows += _row(pid, d['partner_map'], b_ack, c_ack, badge)

    # ── Section 2: PDVSA continuity pending ───────────────────────────────────
    pdvsa_rows = ''
    pdvsa_pending_pids = sorted(
        [pid for pid, a in d['pdvsa_map'].items() if a['state'] == 'pending'],
        key=lambda p: (d['pdvsa_map'].get(p) or {}).get('partner_name') or ''
    )
    for pid in pdvsa_pending_pids:
        b_ack   = d['budget_map'].get(pid)
        c_ack   = d['pdvsa_map'].get(pid)
        b_voted = b_ack and b_ack.get('state') != 'pending'
        badge   = ('<span style="background:#e8f5e9;color:#2e7d32;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;">Ppto ✓</span>'
                   if b_voted else
                   '<span style="background:#ffebee;color:#c62828;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;">Ppto ✗</span>')
        pdvsa_rows += _row(pid, d['partner_map'], b_ack, c_ack, badge)

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,sans-serif;">
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:24px 12px;">
<table cellpadding="0" cellspacing="0" width="640"
       style="max-width:640px;background:#fff;border-radius:14px;
              box-shadow:0 4px 20px rgba(0,0,0,0.10);overflow:hidden;">

  <!-- Header -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:24px 28px 20px;text-align:center;">
      <img src="{LOGO_URL}" alt="Colegio Andrés Bello" width="64" height="64"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 12px;"/>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:4px;letter-spacing:1px;">
        SEGUIMIENTO STAFF · PENDIENTES
      </div>
      <h1 style="margin:0;color:#fff;font-size:18px;font-weight:bold;">
        📋 Reporte de Pendientes — Consulta 2026-2027
      </h1>
      <div style="margin-top:6px;font-size:12px;color:rgba(255,255,255,0.8);">
        {now_str}
      </div>
    </td>
  </tr>

  <!-- Summary cards -->
  <tr>
    <td style="padding:24px 28px 0;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <!-- Budget card -->
          <td width="49%" style="padding-right:8px;vertical-align:top;">
            <div style="background:#e8f0fb;border:2px solid #b8cef5;border-radius:10px;padding:16px;">
              <div style="font-size:11px;font-weight:bold;color:#1a2c5b;margin-bottom:8px;">
                🗳️ CONSULTA PRESUPUESTARIA
              </div>
              <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="text-align:center;">
                    <div style="font-size:30px;font-weight:bold;color:#1a2c5b;">{s['b_voted']}</div>
                    <div style="font-size:10px;color:#2471a3;">Votaron</div>
                  </td>
                  <td style="text-align:center;border-left:1px solid #b8cef5;">
                    <div style="font-size:30px;font-weight:bold;color:#e65100;">{s['b_pending']}</div>
                    <div style="font-size:10px;color:#e65100;">Pendientes</div>
                  </td>
                  <td style="text-align:center;border-left:1px solid #b8cef5;">
                    <div style="font-size:30px;font-weight:bold;color:#555;">{s['b_total']}</div>
                    <div style="font-size:10px;color:#888;">Total</div>
                  </td>
                </tr>
              </table>
              <div style="margin-top:10px;background:#cfe2ff;border-radius:4px;height:8px;">
                <div style="background:#1a2c5b;border-radius:4px;height:8px;width:{s['b_pct_voted']}%;"></div>
              </div>
              <div style="margin-top:3px;font-size:10px;color:#555;text-align:right;">{s['b_pct_voted']}% participación</div>
              {goal_block}
            </div>
          </td>
          <!-- PDVSA card -->
          <td width="49%" style="padding-left:8px;vertical-align:top;">
            <div style="background:#fff8e1;border:2px solid #ffe082;border-radius:10px;padding:16px;">
              <div style="font-size:11px;font-weight:bold;color:#e65100;margin-bottom:8px;">
                🏭 CONTINUIDAD PDVSA
              </div>
              <table cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="text-align:center;">
                    <div style="font-size:30px;font-weight:bold;color:#2e7d32;">{s['p_continuing']}</div>
                    <div style="font-size:10px;color:#2e7d32;">Continúan</div>
                  </td>
                  <td style="text-align:center;border-left:1px solid #ffe082;">
                    <div style="font-size:30px;font-weight:bold;color:#e65100;">{s['p_pending']}</div>
                    <div style="font-size:10px;color:#e65100;">Pendientes</div>
                  </td>
                  <td style="text-align:center;border-left:1px solid #ffe082;">
                    <div style="font-size:30px;font-weight:bold;color:#bf360c;">{s['p_leaving']}</div>
                    <div style="font-size:10px;color:#bf360c;">No continúan</div>
                  </td>
                </tr>
              </table>
              <div style="margin-top:18px;font-size:10px;color:#888;">
                Total familias PDVSA: {s['p_total']} &nbsp;·&nbsp; Deadline: 08 Jun 2026
              </div>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- Section 1: Budget pending -->
  <tr>
    <td style="padding:24px 28px 0;">
      <div style="font-size:14px;font-weight:bold;color:#1a2c5b;">
        🗳️ Pendientes — Consulta Presupuestaria
        <span style="background:#e65100;color:#fff;padding:2px 10px;border-radius:12px;
                     font-size:12px;margin-left:8px;">{len(budget_pending_pids)}</span>
      </div>
      <div style="font-size:11px;color:#888;margin-top:3px;">
        Aún no han votado Opción A o B · Columna "Estado" indica si es familia PDVSA
      </div>
      {_table(budget_rows)}
    </td>
  </tr>

  <!-- Section 2: PDVSA pending -->
  <tr>
    <td style="padding:24px 28px 0;">
      <div style="font-size:14px;font-weight:bold;color:#e65100;">
        🏭 Pendientes — Continuidad PDVSA
        <span style="background:#e65100;color:#fff;padding:2px 10px;border-radius:12px;
                     font-size:12px;margin-left:8px;">{len(pdvsa_pending_pids)}</span>
      </div>
      <div style="font-size:11px;color:#888;margin-top:3px;">
        Aún no confirmaron continuidad · "Ppto ✓/✗" indica si ya votaron el presupuesto
      </div>
      {_table(pdvsa_rows)}
    </td>
  </tr>

  <!-- CTA -->
  <tr>
    <td style="padding:24px 28px;text-align:center;">
      <a href="{MONITOR_URL}"
         style="display:inline-block;background:#1a2c5b;color:#fff;
                padding:11px 28px;border-radius:8px;font-size:13px;
                font-weight:bold;text-decoration:none;">
        📊 Ver en Odoo →
      </a>
    </td>
  </tr>

  <tr>
    <td style="background:#f8f9fa;padding:12px 24px;text-align:center;
               font-size:10px;color:#aaa;border-top:1px solid #e8e8e8;">
      Reporte de seguimiento staff · Consulta Presupuestaria & PDVSA Continuidad 2026-2027 ·
      <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">votacion@ueipab.edu.ve</a>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main(live, test):
    models, db, uid, key = _connect()
    d    = _fetch_data(models, db, uid, key)
    s    = d['summary']
    html = _build_html(d)

    log.info("Budget — A:%d B:%d Pending:%d/%d | PDVSA — Cont:%d Pend:%d Leave:%d/%d",
             s['b_continuing'], s['b_leaving'], s['b_pending'], s['b_total'],
             s['p_continuing'], s['p_pending'], s['p_leaving'], s['p_total'])

    subject = (f"📋 Seguimiento Pendientes — Presupuesto: {s['b_pending']} sin votar "
               f"| PDVSA: {s['p_pending']} sin responder")

    if not live and not test:
        log.info("DRY RUN — would send: %s", subject)
        return

    recipients = [TEST_RECIPIENT] if test else RECIPIENTS
    if test:
        log.info("TEST MODE — sending only to %s", TEST_RECIPIENT[1])

    email_to = ', '.join(f'{n} <{e}>' for n, e in recipients)
    mail_id = models.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
        'subject':    subject,
        'email_from': 'Votación UEIPAB <votacion@ueipab.edu.ve>',
        'email_to':   email_to,
        'body_html':  html,
        'state':      'outgoing',
    }]])

    try:
        models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
    except Exception as e:
        log.warning("Could not trigger mail queue: %s", e)

    log.info("Digest sent — mail.mail id=%s | to=%s", mail_id, email_to)
    log.info("Subject: %s", subject)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Send to all recipients')
    parser.add_argument('--test', action='store_true', help='Send to CEO only (test)')
    args = parser.parse_args()
    main(live=args.live, test=args.test)
