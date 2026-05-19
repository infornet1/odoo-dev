"""
Voting Digest — Consulta Presupuestaria 2026-2027
==================================================
Sends a live vote tally to the CEO every 15 minutes during the voting window.
Skips send if no new votes since the last run (no inbox spam).

Usage:
    python3 scripts/voting_digest.py           # dry-run
    python3 scripts/voting_digest.py --live    # send digest

Cron: /etc/cron.d/voting_digest
  Every 15 min, 06:00–22:00 VET (10:00–02:00 UTC), 21–26 May 2026:
  */15 10-23,0,1 21,22,23,24,25,26 5 * root python3 /opt/odoo-dev/scripts/voting_digest.py --live \
    >> /var/log/voting_digest.log 2>&1
"""
import os, sys, json, logging, argparse, xmlrpc.client
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

NOTICE_KEY  = 'budget_consulta_2026_2027'
STATE_FILE  = os.path.join(os.path.dirname(__file__), 'voting_digest_state.json')
PROD_CFG    = '/opt/odoo-dev/config/production.json'
ODOO_URL    = 'https://odoo.ueipab.edu.ve'

# ── CEO destination ────────────────────────────────────────────────────────────
CEO_EMAIL   = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME    = 'Gustavo Perdomo'

# ── Odoo UI deep-links ─────────────────────────────────────────────────────────
MONITOR_URL = f'{ODOO_URL}/web#action=840&cids=1&menu_id=580'
LOGO_URL    = f'{ODOO_URL}/web/image/res.company/1/logo'


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_prod_cfg():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    return cfg['url'], cfg['db'], cfg['user'], cfg['api_key']


# ── State ──────────────────────────────────────────────────────────────────────

def _load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def _save_state(state):
    json.dump(state, open(STATE_FILE, 'w'), indent=2, default=str)


# ── Odoo XML-RPC ───────────────────────────────────────────────────────────────

def _connect():
    url, db, user, key = _load_prod_cfg()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid    = common.authenticate(db, user, key, {})
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, db, uid, key


def call(models, db, uid, key, model, method, args=None, kw=None):
    return models.execute_kw(db, uid, key, model, method,
                             args or [[]], kw or {})


# ── Vote data ──────────────────────────────────────────────────────────────────

def _fetch_votes(models, db, uid, key):
    records = call(models, db, uid, key,
        'partner.communication.ack', 'search_read',
        [[('notice_key', '=', NOTICE_KEY)]],
        {'fields': ['state', 'vote_channel', 'ack_date', 'partner_name',
                    'partner_email', 'recorded_by']})
    return records


def _tally(records):
    total     = len(records)
    by_state  = {'continuing': 0, 'leaving': 0, 'pending': 0}
    by_channel= {'email_link': 0, 'whatsapp': 0, 'phone': 0,
                 'in_person': 0, 'unknown': 0}
    recent    = []  # votes in last 15 min

    now = datetime.now(timezone.utc)
    for r in records:
        s = r.get('state', 'pending')
        by_state[s] = by_state.get(s, 0) + 1

        # Records voted before audit fields (v6.7) have no channel — default to email_link
        ch = r.get('vote_channel') or ('email_link' if s != 'pending' else None)
        if ch:
            by_channel[ch] = by_channel.get(ch, 0) + 1

        if r.get('ack_date') and s != 'pending':
            try:
                dt_str = r['ack_date']
                if isinstance(dt_str, str):
                    dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
                    delta = (now - dt).total_seconds()
                    if delta <= 900:   # 15 min
                        recent.append(r)
            except Exception:
                pass

    voted = by_state['continuing'] + by_state['leaving']
    return {
        'total':        total,
        'voted':        voted,
        'continuing':   by_state['continuing'],
        'leaving':      by_state['leaving'],
        'pending':      by_state['pending'],
        'by_channel':   by_channel,
        'recent':       recent,
        'pct_a':        round(by_state['continuing'] / voted * 100) if voted else 0,
        'pct_b':        round(by_state['leaving']    / voted * 100) if voted else 0,
        'pct_voted':    round(voted / total * 100) if total else 0,
        '_all_records': records,
    }


# ── HTML email ─────────────────────────────────────────────────────────────────

def _channel_label(ch):
    return {
        'email_link': '📧 Enlace de correo',
        'whatsapp':   '💬 WhatsApp (Glenda)',
        'phone':      '📞 Teléfono (staff)',
        'in_person':  '🏫 Presencial',
        'unknown':    '❓ Sin canal',
    }.get(ch, ch)


def _bar(pct, color, width=280):
    px = max(4, int(width * pct / 100))
    return (
        f'<div style="background:#e8edf3;border-radius:4px;height:18px;width:{width}px;">'
        f'<div style="background:{color};border-radius:4px;height:18px;width:{px}px;"></div>'
        f'</div>'
    )


def _build_html(t, recent_delta, state):
    now_str  = datetime.now().strftime('%d/%m/%Y %H:%M VET')
    last_str = state.get('last_send', '—')

    # Recent votes list
    if recent_delta > 0 and t['recent']:
        recent_rows = ''.join(
            f'<tr><td style="padding:3px 8px;font-size:12px;color:#333;">'
            f'{r["partner_name"]}</td>'
            f'<td style="padding:3px 8px;font-size:12px;color:#555;">'
            f'{r["partner_email"]}</td>'
            f'<td style="padding:3px 8px;font-size:12px;font-weight:bold;'
            f'color:{"#1a2c5b" if r["state"]=="continuing" else "#6c3483"};">'
            f'{"Opción A" if r["state"]=="continuing" else "Opción B"}</td>'
            f'</tr>'
            for r in t['recent']
        )
        recent_section = f"""
<div style="margin-top:20px;">
  <div style="font-size:13px;font-weight:bold;color:#1a2c5b;margin-bottom:8px;">
    🆕 Últimos 15 minutos — {recent_delta} voto(s) nuevo(s)
  </div>
  <table cellpadding="0" cellspacing="0" width="100%"
         style="border:1px solid #dde;border-radius:6px;overflow:hidden;font-size:12px;">
    <thead>
      <tr style="background:#f0f4fa;">
        <th style="padding:5px 8px;text-align:left;color:#555;">Representante</th>
        <th style="padding:5px 8px;text-align:left;color:#555;">Email</th>
        <th style="padding:5px 8px;text-align:left;color:#555;">Decisión</th>
      </tr>
    </thead>
    <tbody>{recent_rows}</tbody>
  </table>
</div>"""
    else:
        recent_section = (
            '<div style="margin-top:20px;padding:10px 14px;background:#f8f9fa;'
            'border-radius:6px;font-size:12px;color:#888;">'
            '⏸ Sin votos nuevos desde el último reporte.</div>'
        )

    # Channel breakdown
    ch_rows = ''.join(
        f'<tr><td style="padding:4px 8px;font-size:12px;">{_channel_label(ch)}</td>'
        f'<td style="padding:4px 8px;font-size:13px;font-weight:bold;text-align:right;">{cnt}</td></tr>'
        for ch, cnt in t['by_channel'].items() if cnt > 0
    )
    ch_section = (
        f'<table cellpadding="0" cellspacing="0" width="100%">'
        f'{ch_rows}</table>'
    ) if ch_rows else '<span style="font-size:12px;color:#aaa;">Sin datos de canal aún</span>'

    # Full voted list (all voted, sorted most recent first)
    voted_records = sorted(
        [r for r in t.get('_all_records', []) if r.get('state') != 'pending'],
        key=lambda r: r.get('ack_date') or '',
        reverse=True,
    )
    if voted_records:
        voted_rows = ''.join(
            f'<tr style="border-bottom:1px solid #f0f0f0;">'
            f'<td style="padding:5px 8px;font-size:12px;color:#333;">{r["partner_name"]}</td>'
            f'<td style="padding:5px 8px;font-size:11px;color:#888;">{r["partner_email"]}</td>'
            f'<td style="padding:5px 8px;font-size:12px;font-weight:bold;'
            f'color:{"#1a2c5b" if r["state"]=="continuing" else "#6c3483"};">'
            f'{"Opción A" if r["state"]=="continuing" else "Opción B"}</td>'
            f'<td style="padding:5px 8px;font-size:11px;color:#aaa;">'
            f'{(r.get("ack_date") or "")[:16].replace("T"," ")}</td>'
            f'</tr>'
            for r in voted_records
        )
        voted_section = f"""
<div style="margin-top:20px;">
  <div style="font-size:13px;font-weight:bold;color:#1a2c5b;margin-bottom:8px;">
    📋 Votos registrados ({len(voted_records)})
  </div>
  <table cellpadding="0" cellspacing="0" width="100%"
         style="border:1px solid #dde;border-radius:6px;overflow:hidden;">
    <thead>
      <tr style="background:#f0f4fa;">
        <th style="padding:5px 8px;text-align:left;font-size:11px;color:#555;">Representante</th>
        <th style="padding:5px 8px;text-align:left;font-size:11px;color:#555;">Email</th>
        <th style="padding:5px 8px;text-align:left;font-size:11px;color:#555;">Decisión</th>
        <th style="padding:5px 8px;text-align:left;font-size:11px;color:#555;">Fecha/Hora</th>
      </tr>
    </thead>
    <tbody>{voted_rows}</tbody>
  </table>
</div>"""
    else:
        voted_section = ''

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
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:24px 28px 20px;text-align:center;">
      <img src="{LOGO_URL}" alt="Colegio Andrés Bello" width="64" height="64"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 12px;"/>
      <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:4px;">
        REPORTE AUTOMÁTICO · CADA 15 MIN
      </div>
      <h1 style="margin:0;color:#fff;font-size:18px;font-weight:bold;">
        🗳️ Consulta Presupuestaria 2026-2027
      </h1>
      <div style="margin-top:6px;font-size:12px;color:rgba(255,255,255,0.8);">
        {now_str} &nbsp;·&nbsp; Último reporte: {last_str}
      </div>
    </td>
  </tr>

  <!-- Main tally -->
  <tr>
    <td style="padding:24px 28px 0;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <!-- Opcion A -->
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#e8f0fb;border:2px solid #b8cef5;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#1a2c5b;margin-bottom:4px;">
                OPCIÓN A
              </div>
              <div style="font-size:36px;font-weight:bold;color:#1a2c5b;line-height:1;">
                {t['continuing']}
              </div>
              <div style="font-size:11px;color:#2471a3;margin-top:2px;">
                $218,88/mes
              </div>
              <div style="font-size:18px;font-weight:bold;color:#2471a3;margin-top:4px;">
                {t['pct_a']}%
              </div>
            </div>
          </td>
          <!-- Opcion B -->
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#f3e5f5;border:2px solid #ce93d8;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#6c3483;margin-bottom:4px;">
                OPCIÓN B
              </div>
              <div style="font-size:36px;font-weight:bold;color:#6c3483;line-height:1;">
                {t['leaving']}
              </div>
              <div style="font-size:11px;color:#6c3483;margin-top:2px;">
                $236,58/mes
              </div>
              <div style="font-size:18px;font-weight:bold;color:#6c3483;margin-top:4px;">
                {t['pct_b']}%
              </div>
            </div>
          </td>
          <!-- Pending -->
          <td width="33%" style="text-align:center;padding:0 6px;">
            <div style="background:#fff8e1;border:2px solid #ffe082;border-radius:10px;padding:16px 8px;">
              <div style="font-size:11px;font-weight:bold;color:#e65100;margin-bottom:4px;">
                PENDIENTE
              </div>
              <div style="font-size:36px;font-weight:bold;color:#e65100;line-height:1;">
                {t['pending']}
              </div>
              <div style="font-size:11px;color:#e65100;margin-top:2px;">
                sin votar
              </div>
              <div style="font-size:18px;font-weight:bold;color:#e65100;margin-top:4px;">
                {100 - t['pct_voted']}%
              </div>
            </div>
          </td>
        </tr>
      </table>

      <!-- Progress bar voted / total -->
      <div style="margin-top:16px;">
        <div style="display:flex;justify-content:space-between;
                    font-size:11px;color:#888;margin-bottom:4px;">
          <span>Participación: <strong>{t['voted']}/{t['total']}</strong>
                ({t['pct_voted']}%)</span>
        </div>
        <div style="background:#e8edf3;border-radius:4px;height:10px;width:100%;">
          <div style="background:#2471a3;border-radius:4px;height:10px;
                      width:{t['pct_voted']}%;"></div>
        </div>
      </div>

      <!-- A vs B bar (among voted) -->
      {"" if t['voted'] == 0 else f'''
      <div style="margin-top:12px;">
        <div style="font-size:11px;color:#888;margin-bottom:4px;">
          Distribución (de los {t['voted']} votos registrados):
        </div>
        <div style="display:flex;height:14px;border-radius:4px;overflow:hidden;width:100%;">
          <div style="background:#1a2c5b;width:{t['pct_a']}%;height:14px;"></div>
          <div style="background:#6c3483;width:{t['pct_b']}%;height:14px;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;
                    font-size:10px;color:#888;margin-top:2px;">
          <span style="color:#1a2c5b;">■ A: {t['pct_a']}%</span>
          <span style="color:#6c3483;">■ B: {t['pct_b']}%</span>
        </div>
      </div>
      '''}
    </td>
  </tr>

  <!-- Recent votes -->
  <tr>
    <td style="padding:12px 28px 0;">
      {recent_section}
    </td>
  </tr>

  <!-- Voted list -->
  {f'<tr><td style="padding:0 28px;">{voted_section}</td></tr>' if voted_section else ''}

  <!-- Channel breakdown -->
  <tr>
    <td style="padding:16px 28px 0;">
      <div style="font-size:12px;font-weight:bold;color:#555;margin-bottom:6px;">
        Canal de votación
      </div>
      {ch_section}
    </td>
  </tr>

  <!-- CTA button -->
  <tr>
    <td style="padding:20px 28px 24px;text-align:center;">
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
      Reporte automático cada 15 min · Solo se envía cuando hay votos nuevos ·
      <a href="mailto:votacion@ueipab.edu.ve" style="color:#2471a3;">votacion@ueipab.edu.ve</a>
    </td>
  </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main(live):
    models, db, uid, key = _connect()
    state = _load_state()

    records = _fetch_votes(models, db, uid, key)
    t       = _tally(records)
    last_voted = state.get('last_voted', -1)
    delta   = t['voted'] - max(last_voted, 0)

    log.info("Tally — A:%d B:%d Pending:%d Voted:%d/%d Delta:+%d",
             t['continuing'], t['leaving'], t['pending'],
             t['voted'], t['total'], delta)

    # Skip if no new votes (unless first run: last_voted == -1)
    if last_voted >= 0 and delta == 0:
        log.info("No new votes since last run — skipping send.")
        return

    subject = (
        f"🗳️ Votación 2026-2027 — A:{t['continuing']} / B:{t['leaving']} "
        f"/ Pend:{t['pending']} (+{delta} nuevos)"
    )

    html = _build_html(t, delta, state)

    if not live:
        log.info("DRY RUN — would send: %s", subject)
        log.info("A=%d B=%d Pending=%d Voted=%d/%d",
                 t['continuing'], t['leaving'], t['pending'],
                 t['voted'], t['total'])
        return

    # Create mail.mail via XML-RPC
    mail_id = models.execute_kw(db, uid, key, 'mail.mail', 'create', [[{
        'subject':    subject,
        'email_from': 'Votación UEIPAB <votacion@ueipab.edu.ve>',
        'email_to':   f'{CEO_NAME} <{CEO_EMAIL}>',
        'body_html':  html,
        'state':      'outgoing',
    }]])

    # Trigger mail queue
    try:
        models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
    except Exception as e:
        log.warning("Could not trigger mail queue cron: %s", e)

    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    state.update({
        'last_voted':  t['voted'],
        'last_send':   now_str,
        'last_a':      t['continuing'],
        'last_b':      t['leaving'],
    })
    _save_state(state)
    log.info("Digest sent — mail.mail id=%s subject=%s", mail_id, subject)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    main(live=args.live)
