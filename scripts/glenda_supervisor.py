"""
Glenda AI Supervisor — Quality control digest for CEO Command Center.

Reviews recent Glenda conversations using Claude Haiku and sends a digest
to the CEO via OdooBot DM + email. WA alert for critical issues.

Usage:
    python3 scripts/glenda_supervisor.py           # dry-run
    python3 scripts/glenda_supervisor.py --live    # send digest

Cron: /etc/cron.d/glenda_supervisor
  Every 2h weekdays 07:00-21:00 VET (11:00-23:00 UTC):
  0 11-23/2 * * 1-5 root python3 /opt/odoo-dev/scripts/glenda_supervisor.py --live \
    >> /var/log/glenda_supervisor.log 2>&1
"""
import os, sys, json, logging, argparse, requests
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

STATE_FILE   = os.path.join(os.path.dirname(__file__), 'glenda_supervisor_state.json')
PROD_CFG     = '/opt/odoo-dev/config/production.json'
ANTHROPIC_CFG= '/opt/odoo-dev/config/anthropic_api.json'

# Review window: conversations with activity in last N hours
REVIEW_WINDOW_HOURS = 2

REVIEW_SYSTEM_PROMPT = """Eres supervisor de calidad de Glenda, asistente virtual del Instituto Privado Andrés Bello (Venezuela).

CONOCIMIENTO QUE GLENDA DEBE TENER (actualizado 11/06/2026 — comunicado oficial 10/06/2026):
- Mensualidad vigente 2025-2026: $197,38 | Pronto pago: $162,39 (primeros 10 días)
- Tarifas 2026-2027 CONFIRMADAS (Opción A aprobada el 26/05/2026; la votación CERRÓ — Glenda NO debe mencionar la Opción B ni hablar de votación pendiente)
- 3 llamados de inscripción 2026-2027:
  · 1er llamado (11 jun - 31 jul): inscripción $187,51 / mensualidad convenio $197,38. Incluye CONVENIO DE PAGO (requisito: solvente con junio 2026; fechas definitivas se firman EN LA INSTITUCIÓN)
  · 2do llamado (agosto): inscripción $207,93 / mensualidad $218,88 (solvencia al 31/07)
  · 3er llamado (septiembre): inscripción $218,88 / mensualidad $218,88 (solvencia total)
- Descuentos hermanos en mensualidad (aplican TAMBIÉN sobre la tarifa promocional): 2 hijos -5% ($187,51 promo) | 3 hijos -8% ($181,59) | 4+ -11% ($175,67)
- Costos anuales únicos por alumno: $111,58 hasta el 31 jul (seguro $30,58 + guía inglés $35 + olimpiadas $10 + enciclopedia $36); $116,58 desde el 1 ago (inglés sube a $40)
- COTIZACIONES FORMALES: las genera el SISTEMA, no Glenda. Glenda emite un marcador interno y el sistema envía un mensaje aparte "📋 Cotización S00XXX" con los totales exactos del motor de Odoo. NO penalizar que Glenda no calcule totales (es lo correcto); SÍ penalizar si Glenda inventa o calcula totales por su cuenta. El mensaje del sistema es la cifra autoritativa.
- Seguro escolar: Seguros Caracas — Póliza Accidentes Escolares Alt.2
- Reclamos seguro: WA 0414-903.3738 / amis@grupov.com.ve / App Asegurados
- Asesora local: Johanna Hernández WA +58 424-834-0051
- Año escolar 2025-2026 finaliza 31 agosto 2026 (NO en junio)
- Glenda NO debe pedir información que el sistema ya tiene (mensualidad, nombre de alumno, grado)
- Glenda SÍ debe ofrecer la promoción del 1er llamado (inscripción anticipada + convenio) en consultas de mensualidad/inscripción

CRITERIOS DE EVALUACIÓN:
1. Datos correctos (precios, fechas, nombres de empresa, enlaces)
2. Respondió la pregunta real (no desvió o pidió info innecesaria)
3. Aprovechó oportunidades comerciales (inscripción anticipada, Cashea, propuesta)
4. Tono cálido y profesional, respuesta concisa
5. No hizo preguntas que el sistema ya podía responder

RESPONDE ÚNICAMENTE con este JSON (sin texto adicional):
{
  "score": <1-5>,
  "status": "<ok|warning|critical>",
  "issues": ["<problema 1>", "<problema 2>"],
  "highlights": ["<positivo 1>"],
  "summary": "<una oración evaluando la conversación>"
}

score 5=excelente, 4=bien, 3=aceptable con mejoras menores, 2=problemas notables, 1=crítico
status ok=score≥4, warning=score 2-3, critical=score 1 o dato incorrecto grave"""


def _load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {'last_reviewed_per_conv': {}, 'last_run': None}


def _save_state(state):
    json.dump(state, open(STATE_FILE, 'w'), indent=2)


def _odoo_call(m, db, uid, key, model, method, args=None, kw=None):
    import xmlrpc.client
    return xmlrpc.client.ServerProxy(f'{m}/xmlrpc/2/object', allow_none=True).execute_kw(
        db, uid, key, model, method, args or [], kw or {})


def _call_claude(messages, system):
    cfg = json.load(open(ANTHROPIC_CFG))
    api_key = cfg.get('api', {}).get('api_key') or cfg.get('api_key', '')
    resp = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01',
                 'content-type': 'application/json'},
        json={'model': 'claude-haiku-4-5-20251001', 'max_tokens': 512,
              'system': system, 'messages': messages},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()['content'][0]['text'].strip()


def _review_conversation(conv, msgs):
    """Ask Claude to score a conversation. Returns dict or None on error."""
    transcript = '\n'.join(
        f"[{'GLENDA' if m['direction']=='outbound' else 'CLIENTE'}] {m['body'][:400]}"
        for m in msgs
    )
    prompt = f"Conversación #{conv['id']} — {conv['partner_id'][1] if conv['partner_id'] else 'Anónimo'}:\n\n{transcript}"
    try:
        raw = _call_claude([{'role': 'user', 'content': prompt}], REVIEW_SYSTEM_PROMPT)
        # Extract JSON
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        log.warning("Claude review failed for conv %s: %s", conv['id'], e)
    return None


def _send_digest(cfg_prod, digest, live=False):
    url, db, uid, key = (cfg_prod['xmlrpc']['url'], cfg_prod['xmlrpc']['db'],
                         2, cfg_prod['xmlrpc']['api_key'])
    m = url

    def call(model, method, args=None, kw=None):
        return _odoo_call(m, db, uid, key, model, method, args, kw)

    # Get CEO params
    icp = {p['key']: p['value'] for p in call('ir.config_parameter', 'search_read',
        [[['key', 'in', ['wa_monitor.ceo_email', 'wa_monitor.ceo_phone',
                          'ai_agent.agent_display_name']]]], {'fields': ['key','value']})}
    ceo_email = icp.get('wa_monitor.ceo_email', 'gustavo.perdomo@ueipab.edu.ve')
    ceo_phone = icp.get('wa_monitor.ceo_phone', '')

    now_vet = datetime.now(timezone.utc) - timedelta(hours=4)
    ts = now_vet.strftime('%d/%m/%Y %H:%M VET')

    total   = len(digest['results'])
    ok      = sum(1 for r in digest['results'] if r['review']['status'] == 'ok')
    warn    = sum(1 for r in digest['results'] if r['review']['status'] == 'warning')
    crit    = sum(1 for r in digest['results'] if r['review']['status'] == 'critical')
    avg_score = (sum(r['review']['score'] for r in digest['results']) / total) if total else 0

    status_icon = '🔴' if crit else ('🟡' if warn else '🟢')

    # ── OdooBot DM ───────────────────────────────────────────────────────────
    dm_lines = [
        f"🤖 *GLENDA SUPERVISOR* — {ts}",
        f"{status_icon} {total} convs · ✅{ok} ⚠️{warn} ❌{crit} · Promedio: {avg_score:.1f}/5",
        "",
    ]
    if crit:
        dm_lines.append("*❌ CRÍTICO:*")
        for r in digest['results']:
            if r['review']['status'] == 'critical':
                issues = ' | '.join(r['review'].get('issues', []))[:100]
                dm_lines.append(f"  Conv #{r['conv_id']} ({r['partner']}): {issues}")
        dm_lines.append("")
    if warn:
        dm_lines.append("*⚠️ OBSERVACIONES:*")
        for r in digest['results']:
            if r['review']['status'] == 'warning':
                dm_lines.append(f"  Conv #{r['conv_id']} ({r['partner']}): {r['review']['summary'][:80]}")
        dm_lines.append("")
    dm_lines.append("*✅ BIEN:*")
    for r in digest['results']:
        if r['review']['status'] == 'ok':
            dm_lines.append(f"  Conv #{r['conv_id']} ({r['partner']}): {r['review']['summary'][:70]}")

    dm_text = '\n'.join(dm_lines)
    log.info("Digest:\n%s", dm_text)

    if not live:
        log.info("DRY-RUN — nothing sent")
        return

    # Send OdooBot DM to CEO
    try:
        admin = call('res.users', 'search', [[['login','=','admin']]])[0] if \
                call('res.users', 'search_count', [[['login','=','admin']]]) else 2
        ceo_partner = call('res.users', 'search_read',
            [[['email','=',ceo_email]]], {'fields':['partner_id'], 'limit':1})
        if ceo_partner:
            pid = ceo_partner[0]['partner_id'][0]
            # Find or create direct message channel
            bot_id = call('res.users', 'search', [[['login','=','OdooBot']]] )
            if bot_id:
                channels = call('discuss.channel', 'search', [[
                    ['channel_type','=','chat'],
                    ['channel_member_ids.partner_id','=',pid],
                ]])
                if channels:
                    call('discuss.channel', 'message_post', [[channels[0]]],
                         {'body': dm_text.replace('\n','<br/>'), 'message_type': 'comment'})
                    log.info("OdooBot DM sent to CEO")
    except Exception as e:
        log.warning("OdooBot DM failed: %s", e)

    # ── Email to CEO ──────────────────────────────────────────────────────────
    rows_html = ''
    status_colors = {'ok': '#dcfce7', 'warning': '#fef3c7', 'critical': '#fee2e2'}
    status_labels = {'ok': '✅ Bien', 'warning': '⚠️ Observación', 'critical': '❌ Crítico'}
    for r in sorted(digest['results'], key=lambda x: x['review']['score']):
        rev = r['review']
        color = status_colors.get(rev['status'], '#f9fafb')
        label = status_labels.get(rev['status'], rev['status'])
        issues_html = ''.join(f'<li style="color:#991b1b;">{i}</li>' for i in rev.get('issues', []))
        hi_html     = ''.join(f'<li style="color:#166534;">{h}</li>' for h in rev.get('highlights', []))
        rows_html += f"""
        <tr style="background:{color};">
          <td style="padding:10px 12px;font-size:12px;font-weight:700;white-space:nowrap;">
            #{r['conv_id']}</td>
          <td style="padding:10px 12px;font-size:12px;">{r['partner']}</td>
          <td style="padding:10px 12px;font-size:12px;text-align:center;font-weight:700;">
            {rev['score']}/5</td>
          <td style="padding:10px 12px;font-size:12px;">{label}</td>
          <td style="padding:10px 12px;font-size:12px;">
            {rev.get('summary','')[:100]}
            {'<ul style="margin:4px 0;padding-left:16px;">'+issues_html+'</ul>' if issues_html else ''}
            {'<ul style="margin:4px 0;padding-left:16px;">'+hi_html+'</ul>' if hi_html else ''}
          </td>
        </tr>"""

    body_html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"/></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;">
<tr><td align="center" style="padding:24px 12px;">
<table width="680" cellpadding="0" cellspacing="0"
       style="max-width:680px;width:100%;border-radius:12px;overflow:hidden;
              box-shadow:0 4px 24px rgba(0,0,0,0.12);">
  <tr>
    <td style="background:linear-gradient(135deg,#0a1628,#1a3a6b);padding:28px 36px;text-align:center;">
      <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" width="56" height="56"
           style="border-radius:50%;border:2px solid #C8A951;display:block;margin:0 auto 12px;object-fit:cover;"/>
      <h2 style="margin:0 0 4px;font-size:20px;color:#fff;">🤖 Glenda Supervisor Digest</h2>
      <p style="margin:0;font-size:13px;color:#8badd4;">{ts}</p>
    </td>
  </tr>
  <tr>
    <td style="background:#fff;padding:24px 36px;">
      <!-- Summary bar -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
        <tr>
          <td width="25%" style="text-align:center;background:#f8faff;border-radius:8px;padding:14px;margin:0 4px;">
            <p style="margin:0;font-size:24px;font-weight:800;color:#0a1628;">{total}</p>
            <p style="margin:0;font-size:11px;color:#64748b;">Conversaciones</p>
          </td>
          <td width="4%"></td>
          <td width="21%" style="text-align:center;background:#dcfce7;border-radius:8px;padding:14px;">
            <p style="margin:0;font-size:24px;font-weight:800;color:#15803d;">✅ {ok}</p>
            <p style="margin:0;font-size:11px;color:#166534;">Bien</p>
          </td>
          <td width="4%"></td>
          <td width="21%" style="text-align:center;background:#fef3c7;border-radius:8px;padding:14px;">
            <p style="margin:0;font-size:24px;font-weight:800;color:#b45309;">⚠️ {warn}</p>
            <p style="margin:0;font-size:11px;color:#92400e;">Observación</p>
          </td>
          <td width="4%"></td>
          <td width="21%" style="text-align:center;background:#fee2e2;border-radius:8px;padding:14px;">
            <p style="margin:0;font-size:24px;font-weight:800;color:#b91c1c;">❌ {crit}</p>
            <p style="margin:0;font-size:11px;color:#991b1b;">Crítico</p>
          </td>
        </tr>
      </table>
      <!-- Score bar -->
      <p style="margin:0 0 16px;font-size:13px;color:#374151;">
        Puntuación promedio: <strong>{avg_score:.1f}/5</strong>
        {'&nbsp;·&nbsp;<span style="color:#b91c1c;font-weight:700;">⚠️ Atención requerida</span>' if crit else ''}
      </p>
      <!-- Table -->
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
        <tr style="background:#0a1628;">
          <th style="padding:10px 12px;font-size:11px;color:#C8A951;text-align:left;font-weight:700;">Conv</th>
          <th style="padding:10px 12px;font-size:11px;color:#C8A951;text-align:left;font-weight:700;">Cliente</th>
          <th style="padding:10px 12px;font-size:11px;color:#C8A951;text-align:center;font-weight:700;">Score</th>
          <th style="padding:10px 12px;font-size:11px;color:#C8A951;text-align:left;font-weight:700;">Estado</th>
          <th style="padding:10px 12px;font-size:11px;color:#C8A951;text-align:left;font-weight:700;">Evaluación</th>
        </tr>
        {rows_html}
      </table>
      <!-- CTA -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
        <tr><td align="center">
          <a href="https://odoo.ueipab.edu.ve/web#action=830&model=ai.agent.conversation&view_type=list&cids=1&menu_id=566"
             style="display:inline-block;background:linear-gradient(135deg,#0a1628,#1a3a6b);
                    color:#C8A951;text-decoration:none;font-size:13px;font-weight:700;
                    padding:11px 32px;border-radius:50px;">
            📋 Ver Conversaciones en Odoo
          </a>
        </td></tr>
      </table>
    </td>
  </tr>
  <tr>
    <td style="background:#0a1628;padding:16px 36px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#4b6080;">
        Glenda AI Supervisor · Colegio Andrés Bello · El Tigre, Venezuela
      </p>
    </td>
  </tr>
</table>
</td></tr></table>
</body></html>"""

    mail_id = call('mail.mail', 'create', [[{
        'subject'   : f'🤖 Glenda Digest {status_icon} — {ts} | {total} convs · avg {avg_score:.1f}/5',
        'body_html' : body_html,
        'email_to'  : f'Gustavo Perdomo <{ceo_email}>',
        'email_from': 'Glenda Supervisor <soporte@ueipab.edu.ve>',
        'state'     : 'outgoing',
    }]])
    call('ir.cron', 'method_direct_trigger', [[3]])
    log.info("Email digest sent — mail.mail id=%s", mail_id)

    # WA alert if critical (use existing WA service pattern)
    if crit and ceo_phone:
        wa_msg = f"🔴 GLENDA SUPERVISOR — {ts}\n\n❌ {crit} conversación(es) CRÍTICA(S):\n"
        for r in digest['results']:
            if r['review']['status'] == 'critical':
                issues = ' | '.join(r['review'].get('issues', []))[:120]
                wa_msg += f"\nConv #{r['conv_id']} ({r['partner']})\n{issues}\n"
        wa_msg += f"\nRevisa: odoo.ueipab.edu.ve → AI Agent → Conversaciones"
        try:
            wa_cfg  = json.load(open('/opt/odoo-dev/config/whatsapp_massiva.json'))
            api     = wa_cfg['api']
            secret  = api['secret']
            base    = api['base_url']
            requests.post(
                f"{base}/send/whatsapp",
                json={'secret': secret, 'account': ceo_phone,
                      'recipient': ceo_phone, 'type': 'text', 'message': wa_msg},
                timeout=15,
            )
            log.info("WA critical alert sent to CEO")
        except Exception as e:
            log.warning("WA alert failed: %s", e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--hours', type=int, default=REVIEW_WINDOW_HOURS,
                        help='Review conversations with activity in last N hours')
    args = parser.parse_args()

    cfg_prod  = json.load(open(PROD_CFG))['production']
    xcfg      = cfg_prod['xmlrpc']
    state     = _load_state()

    def call(model, method, a=None, k=None):
        return _odoo_call(xcfg['url'], xcfg['db'], 2, xcfg['api_key'], model, method, a, k)

    # Pull conversations with recent activity
    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).strftime('%Y-%m-%d %H:%M:%S')
    convs = call('ai.agent.conversation', 'search_read', [[
        ['skill_id.code', '=', 'general_inquiry'],
        ['last_message_date', '>=', since],
        ['state', 'not in', ['draft']],
    ]], {'fields': ['id','name','partner_id','state','turn_count','last_message_date'],
         'order': 'id desc', 'limit': 30})

    log.info("Found %d conversations with activity in last %dh", len(convs), args.hours)

    if not convs:
        log.info("Nothing to review — exiting")
        return

    results = []
    last_reviewed = state.get('last_reviewed_per_conv', {})

    for conv in convs:
        cid = str(conv['id'])
        last_msg_id = last_reviewed.get(cid, 0)

        # Get messages (only new ones since last review)
        msgs = call('ai.agent.message', 'search_read', [[
            ['conversation_id', '=', conv['id']],
            ['id', '>', last_msg_id],
        ]], {'fields': ['id','direction','body','create_date'], 'order': 'id asc'})

        if not msgs or len(msgs) < 2:
            log.debug("Conv %s: skipped (< 2 new messages)", conv['id'])
            continue

        log.info("Reviewing conv %s (%s) — %d messages", conv['id'],
                 conv['partner_id'][1] if conv['partner_id'] else '?', len(msgs))

        review = _review_conversation(conv, msgs)
        if not review:
            continue

        results.append({
            'conv_id': conv['id'],
            'partner': conv['partner_id'][1] if conv['partner_id'] else 'Anónimo',
            'state'  : conv['state'],
            'turns'  : conv['turn_count'],
            'review' : review,
        })
        # Update watermark
        last_reviewed[cid] = msgs[-1]['id']

    state['last_reviewed_per_conv'] = last_reviewed
    state['last_run'] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    if not results:
        log.info("No conversations with enough new messages to review")
        return

    digest = {'results': results, 'window_hours': args.hours}
    _send_digest(cfg_prod, digest, live=args.live)
    log.info("Done — reviewed %d conversations", len(results))


if __name__ == '__main__':
    main()
