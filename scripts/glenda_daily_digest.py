#!/usr/bin/env python3
"""
Glenda Daily Executive Digest

Queries Odoo for the previous day's AI agent activity and sends an HTML
summary email to gustavo.perdomo@ueipab.edu.ve covering:
  - 24h statistics (conversations, messages, Claude spend)
  - Activity by skill
  - Most frequent topics (from resolution summaries + escalation reasons)
  - Issues Glenda couldn't handle (escalations + timeouts)
  - Suspicious activity alerts (potential bots, prompt injection probes)

Usage:
    python3 scripts/glenda_daily_digest.py               # yesterday
    python3 scripts/glenda_daily_digest.py --date 2026-05-09
    python3 scripts/glenda_daily_digest.py --env testing

Cron: /etc/cron.d/glenda_daily_digest — daily 07:00 VET
"""

import argparse
import logging
import os
import re
import sys
import xmlrpc.client
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('glenda_digest')

# ── Odoo targets ──────────────────────────────────────────────────────────────
ODOO_CONFIGS = {
    'testing': {
        'url':      'http://localhost:8019',
        'db':       'testing',
        'user':     'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url':      os.environ.get('ODOO_URL',      'https://odoo.ueipab.edu.ve'),
        'db':       os.environ.get('ODOO_DB',       'DB_UEIPAB'),
        'user':     os.environ.get('ODOO_USER',     'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}

TO_EMAIL  = 'gustavo.perdomo@ueipab.edu.ve'
FROM_EMAIL = 'Glenda — Reporte Diario <recursoshumanos@ueipab.edu.ve>'

# ── Topic detection keywords (Spanish) ───────────────────────────────────────
TOPICS = [
    ('Inscripciones / Matrícula',   r'inscripci|matr[ií]cula|inscrit|año escolar|2026-2027|cupo'),
    ('Mensualidad / Aranceles',     r'mensualidad|arancel|tarifa|precio|costo|cuota'),
    ('Saldo / Deuda / Pago',        r'saldo|deuda|pago|factura|cobro|debe|cancel|pend'),
    ('Métodos de pago',             r'zelle|binance|transferencia|mercantil|banco|pago m[oó]vil|tarjeta'),
    ('Cotización multi-alumno',     r'cotizaci[oó]n|hermano|2 alumno|varios alumnos|descuento hermano'),
    ('PDVSA / Petropiar',           r'pdvsa|petropiar|industria|cr[eé]dito 35'),
    ('Asistencia / Kiosko',         r'asistencia|kiosko|check.?in|check.?out|faltas|ausencia'),
    ('Documentos / Constancias',    r'constancia|documento|certificado|carta'),
    ('Tasa BCV / Conversión',       r'tasa|bcv|bol[ií]vares|d[oó]lar|cambio|conversi[oó]n'),
    ('Información general',         r'horario|direcci[oó]n|ubicaci[oó]n|tel[eé]fono|contacto'),
    ('Cursos extracurriculares',    r'ingl[eé]s|rob[oó]tica|kurios|dibujo|bachillerato virtual|moa'),
    ('Escalación / Soporte',        r'escalaci[oó]n|soporte|queja|problema|error|ayuda'),
]

# ── Suspicious pattern thresholds ─────────────────────────────────────────────
SUSPICIOUS = {
    'max_convs_per_phone':    3,    # same phone > N conversations in 24h
    'max_turns_normal':       18,   # conversations with more turns than this
    'min_tokens_per_turn':    600,  # avg tokens/turn above this → possible injection
    'night_start_hour_vet':   1,    # VET hour (UTC-4) — after this = night
    'night_end_hour_vet':     5,    # VET hour — before this = night
}

VET_OFFSET = -4  # Venezuela Eastern Time = UTC-4


# ── Odoo connection ───────────────────────────────────────────────────────────

def connect(env_name):
    cfg = ODOO_CONFIGS[env_name]
    if not cfg['password']:
        raise RuntimeError(f"ODOO_PASSWORD not set for {env_name}")
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid    = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise RuntimeError(f"Authentication failed for {env_name}")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    return cfg['db'], uid, cfg['password'], models


def rpc(models, db, uid, pw, model, method, args=None, kwargs=None):
    return models.execute_kw(db, uid, pw, model, method, args or [], kwargs or {})


# ── Data collection ───────────────────────────────────────────────────────────

def fetch_data(env_name, day):
    """Fetch all relevant data for the given day from Odoo."""
    db, uid, pw, models = connect(env_name)

    # Date range in UTC (Odoo stores UTC; VET = UTC-4)
    start_utc = datetime(day.year, day.month, day.day, 4, 0, 0)   # 00:00 VET
    end_utc   = start_utc + timedelta(days=1)                      # 00:00 VET next day
    start_str = start_utc.strftime('%Y-%m-%d %H:%M:%S')
    end_str   = end_utc.strftime('%Y-%m-%d %H:%M:%S')

    logger.info("Fetching data for %s (UTC %s → %s)", day, start_str, end_str)

    # Conversations active in the day: created OR last_message in range
    conv_domain = [
        '|',
        '&', ('create_date', '>=', start_str), ('create_date', '<', end_str),
        '&', ('last_message_date', '>=', start_str), ('last_message_date', '<', end_str),
    ]
    conv_fields = [
        'id', 'name', 'skill_id', 'partner_id', 'phone', 'state',
        'turn_count', 'resolution_summary', 'escalation_reason',
        'create_date', 'last_message_date', 'resolved_date',
        'channel', 'telegram_chat_id',
    ]
    convs = rpc(models, db, uid, pw, 'ai.agent.conversation', 'search_read',
                [conv_domain], {'fields': conv_fields, 'limit': 500})

    if not convs:
        logger.info("No conversations found for %s", day)
        return None, None

    conv_ids = [c['id'] for c in convs]

    # Messages for those conversations
    msg_fields = ['conversation_id', 'direction', 'body',
                  'ai_input_tokens', 'ai_output_tokens', 'create_date']
    msgs = rpc(models, db, uid, pw, 'ai.agent.message', 'search_read',
               [[('conversation_id', 'in', conv_ids)]],
               {'fields': msg_fields, 'limit': 5000})

    return convs, msgs


# ── Analysis ──────────────────────────────────────────────────────────────────

def detect_topics(text):
    """Return list of matching topic labels from free text."""
    if not text:
        return []
    text_lower = text.lower()
    found = []
    for label, pattern in TOPICS:
        if re.search(pattern, text_lower):
            found.append(label)
    return found


def analyse(convs, msgs, day):
    """Return structured analysis dict."""
    if not convs:
        return None

    # Index messages by conversation
    msgs_by_conv = defaultdict(list)
    for m in msgs:
        cid = m['conversation_id'][0] if isinstance(m['conversation_id'], list) else m['conversation_id']
        msgs_by_conv[cid].append(m)

    # ── Per-skill stats ───────────────────────────────────────────────────────
    skill_stats = defaultdict(lambda: {
        'total': 0, 'resolved': 0, 'escalated': 0, 'timeout': 0,
        'failed': 0, 'active': 0, 'turns': [], 'topics': Counter(),
    })

    topic_counter  = Counter()
    unresolved_log = []
    suspicious     = []
    phone_convs    = defaultdict(list)
    telegram_convs = []   # per-conv detail for the Telegram section

    total_in_tokens  = 0
    total_out_tokens = 0
    total_wa_sent    = 0
    total_wa_recv    = 0
    total_tg_sent    = 0

    for conv in convs:
        skill = conv['skill_id'][1] if conv.get('skill_id') else 'Unknown'
        skill_code = conv['skill_id'][1] if conv.get('skill_id') else 'unknown'
        state  = conv.get('state', 'unknown')
        phone  = conv.get('phone', '')
        cid    = conv['id']

        skill_stats[skill]['total'] += 1
        if state == 'resolved':
            skill_stats[skill]['resolved'] += 1
        elif state == 'timeout':
            skill_stats[skill]['timeout'] += 1
        elif state == 'failed':
            skill_stats[skill]['failed'] += 1
        elif state in ('waiting', 'active', 'draft'):
            skill_stats[skill]['active'] += 1

        skill_stats[skill]['turns'].append(conv.get('turn_count', 0))

        phone_convs[phone].append(conv)

        # Topic detection from summary + escalation
        combined_text = ' '.join(filter(None, [
            conv.get('resolution_summary', ''),
            conv.get('escalation_reason', ''),
        ]))
        topics = detect_topics(combined_text)
        for t in topics:
            topic_counter[t] += 1
            skill_stats[skill]['topics'][t] += 1

        # Escalated / unresolved
        if conv.get('escalation_reason') or state in ('timeout', 'failed'):
            unresolved_log.append({
                'name':    conv.get('name', f"CONV/{cid}"),
                'skill':   skill,
                'state':   state,
                'phone':   phone,
                'partner': conv['partner_id'][1] if conv.get('partner_id') else 'Desconocido',
                'reason':  (conv.get('escalation_reason') or '')[:200],
                'summary': (conv.get('resolution_summary') or '')[:150],
            })

        # Message stats
        conv_msgs = msgs_by_conv.get(cid, [])
        conv_in  = sum(m.get('ai_input_tokens', 0) or 0 for m in conv_msgs)
        conv_out = sum(m.get('ai_output_tokens', 0) or 0 for m in conv_msgs)
        total_in_tokens  += conv_in
        total_out_tokens += conv_out
        msg_out = sum(1 for m in conv_msgs if m.get('direction') == 'outbound')
        msg_in  = sum(1 for m in conv_msgs if m.get('direction') == 'inbound')

        channel = conv.get('channel', 'whatsapp')
        if channel == 'telegram':
            total_tg_sent += msg_out
            # Build first inbound message snippet for topic preview
            first_in = next(
                (m.get('body', '') for m in sorted(conv_msgs, key=lambda x: x.get('create_date',''))
                 if m.get('direction') == 'inbound'), '')
            topic_snippet = (first_in or '')[:120].replace('<br>', ' ').replace('\n', ' ')
            telegram_convs.append({
                'partner': conv['partner_id'][1] if conv.get('partner_id') else '?',
                'chat_id': conv.get('telegram_chat_id', ''),
                'state':   state,
                'turns':   conv.get('turn_count', 0),
                'topics':  topics,
                'snippet': topic_snippet,
                'create':  conv.get('create_date', '')[:16],
                'identified': not (conv['partner_id'][1] if conv.get('partner_id') else '').startswith('Telegram '),
            })
        else:
            total_wa_sent += msg_out
            total_wa_recv += msg_in

        # Suspicious: very long conversation
        turns = conv.get('turn_count', 0)
        if turns > SUSPICIOUS['max_turns_normal']:
            suspicious.append({
                'type':  'Conversación muy larga',
                'conv':  conv.get('name', f"CONV/{cid}"),
                'phone': phone,
                'detail': f"{turns} turnos",
                'partner': conv['partner_id'][1] if conv.get('partner_id') else '?',
            })

        # Suspicious: high tokens/turn (possible prompt injection)
        if turns > 0 and conv_in > 0:
            avg_tok = (conv_in + conv_out) / turns
            if avg_tok > SUSPICIOUS['min_tokens_per_turn']:
                suspicious.append({
                    'type':  'Alto consumo por turno',
                    'conv':  conv.get('name', f"CONV/{cid}"),
                    'phone': phone,
                    'detail': f"{avg_tok:.0f} tokens/turno (posible inyección)",
                    'partner': conv['partner_id'][1] if conv.get('partner_id') else '?',
                })

        # Suspicious: night activity (VET)
        create_str = conv.get('create_date', '')
        if create_str:
            try:
                cdt = datetime.strptime(create_str[:19], '%Y-%m-%d %H:%M:%S')
                vet_hour = (cdt.hour + VET_OFFSET) % 24
                if SUSPICIOUS['night_start_hour_vet'] <= vet_hour < SUSPICIOUS['night_end_hour_vet']:
                    suspicious.append({
                        'type':  'Actividad nocturna',
                        'conv':  conv.get('name', f"CONV/{cid}"),
                        'phone': phone,
                        'detail': f"Iniciada a las {vet_hour:02d}:{cdt.minute:02d} VET",
                        'partner': conv['partner_id'][1] if conv.get('partner_id') else '?',
                    })
            except Exception:
                pass

    # Suspicious: same phone > threshold conversations
    for phone, pconvs in phone_convs.items():
        if len(pconvs) > SUSPICIOUS['max_convs_per_phone']:
            suspicious.append({
                'type':  'Múltiples conversaciones — posible bot',
                'conv':  ', '.join(c.get('name', '') for c in pconvs[:4]),
                'phone': phone,
                'detail': f"{len(pconvs)} conversaciones desde el mismo número",
                'partner': pconvs[0]['partner_id'][1] if pconvs[0].get('partner_id') else '?',
            })

    # Claude cost (Haiku 4.5 rates)
    input_rate  = 0.000001
    output_rate = 0.000005
    claude_cost = (total_in_tokens * input_rate) + (total_out_tokens * output_rate)

    total_convs  = len(convs)
    resolved_ct  = sum(1 for c in convs if c['state'] == 'resolved')
    escalated_ct = sum(1 for c in convs if c.get('escalation_reason'))
    timeout_ct   = sum(1 for c in convs if c['state'] == 'timeout')
    active_ct    = sum(1 for c in convs if c['state'] in ('waiting', 'active', 'draft'))

    return {
        'day':            day,
        'total_convs':    total_convs,
        'resolved':       resolved_ct,
        'escalated':      escalated_ct,
        'timeout':        timeout_ct,
        'active':         active_ct,
        'wa_sent':        total_wa_sent,
        'wa_recv':        total_wa_recv,
        'tg_sent':        total_tg_sent,
        'in_tokens':      total_in_tokens,
        'out_tokens':     total_out_tokens,
        'claude_cost':    claude_cost,
        'skill_stats':    dict(skill_stats),
        'topics':         topic_counter.most_common(12),
        'unresolved':     unresolved_log,
        'suspicious':     suspicious,
        'telegram_convs': telegram_convs,
    }


# ── HTML generation ───────────────────────────────────────────────────────────

def _s(n, label_s, label_p):
    return f"{n} {label_s if n == 1 else label_p}"


def build_html(data, env_name, calib=None):
    day   = data['day'].strftime('%d/%m/%Y')
    today = datetime.now().strftime('%d/%m/%Y %H:%M')
    env_badge = (
        '<span style="background:#c62828;color:#fff;font-size:10px;'
        'padding:2px 6px;border-radius:4px;margin-left:6px;">TESTING</span>'
        if env_name == 'testing' else ''
    )

    res_rate = (
        f"{data['resolved'] / data['total_convs'] * 100:.0f}%"
        if data['total_convs'] else 'N/A'
    )

    # ── Summary cards — email-safe: explicit align on every element ───────────
    def card(value, label, color='#1a2c5b'):
        return (
            f'<td align="center" valign="top" style="padding:6px;">'
            f'<table cellpadding="0" cellspacing="0" width="100"'
            f' style="background:{color};border-radius:8px;">'
            f'<tr><td align="center" valign="middle"'
            f' style="padding:16px 10px 6px 10px;font-size:30px;font-weight:900;'
            f'color:#ffffff;text-align:center;line-height:1;">'
            f'{value}</td></tr>'
            f'<tr><td align="center" valign="middle"'
            f' style="padding:2px 8px 14px 8px;font-size:11px;'
            f'color:rgba(255,255,255,0.85);text-align:center;line-height:1.3;">'
            f'{label}</td></tr>'
            f'</table></td>'
        )

    cards_html = (
        '<table cellpadding="0" cellspacing="0" width="100%"'
        ' style="max-width:620px;margin:0 auto;">'
        '<tr>'
        + card(data['total_convs'],  'Conversaciones', '#1a2c5b')
        + card(data['resolved'],     'Resueltas',      '#2e7d32')
        + card(data['escalated'],    'Escaladas',      '#f9a825')
        + card(data['timeout'],      'Timeout',        '#795548')
        + card(data['active'],       'Activas',        '#1565c0')
        + card(res_rate,             'Tasa Resolución','#6a1b9a')
        + '</tr></table>'
    )

    api_row = (
        f'<tr><td style="padding:4px 12px 4px 0;color:#555;">WA enviados / recibidos</td>'
        f'<td style="font-weight:bold;">{data["wa_sent"]} / {data["wa_recv"]}</td></tr>'
        f'<tr><td style="padding:4px 12px 4px 0;color:#555;">Tokens Claude (entrada / salida)</td>'
        f'<td style="font-weight:bold;">{data["in_tokens"]:,} / {data["out_tokens"]:,}</td></tr>'
        f'<tr><td style="padding:4px 12px 4px 0;color:#555;">Costo Claude estimado</td>'
        f'<td style="font-weight:bold;color:{"#c62828" if data["claude_cost"] > 0.5 else "#2e7d32"};">'
        f'${data["claude_cost"]:.4f}</td></tr>'
    )

    # ── Skill table ───────────────────────────────────────────────────────────
    skill_rows = ''
    for skill, st in sorted(data['skill_stats'].items(),
                             key=lambda x: x[1]['total'], reverse=True):
        turns = st['turns']
        avg_t = f"{sum(turns)/len(turns):.1f}" if turns else '—'
        top_t = ', '.join(t for t, _ in st['topics'].most_common(2)) or '—'
        skill_rows += (
            f'<tr style="border-bottom:1px solid #eee;">'
            f'<td style="padding:6px 10px;">{skill}</td>'
            f'<td style="padding:6px 10px;text-align:center;">{st["total"]}</td>'
            f'<td style="padding:6px 10px;text-align:center;color:#2e7d32;">{st["resolved"]}</td>'
            f'<td style="padding:6px 10px;text-align:center;color:#f9a825;">{st["escalated"]}</td>'
            f'<td style="padding:6px 10px;text-align:center;color:#795548;">{st["timeout"] + st["failed"]}</td>'
            f'<td style="padding:6px 10px;text-align:center;">{avg_t}</td>'
            f'<td style="padding:6px 10px;font-size:11px;color:#555;">{top_t}</td>'
            f'</tr>'
        )

    # ── Topics ────────────────────────────────────────────────────────────────
    if data['topics']:
        max_count = data['topics'][0][1] if data['topics'] else 1
        topic_rows = ''
        for topic, count in data['topics']:
            bar_w = int(count / max_count * 180)
            topic_rows += (
                f'<tr><td style="padding:4px 10px 4px 0;font-size:13px;">{topic}</td>'
                f'<td style="padding:4px 0;">'
                f'<div style="display:inline-block;background:#1a2c5b;height:14px;'
                f'width:{bar_w}px;border-radius:2px;vertical-align:middle;"></div>'
                f'&nbsp;<span style="font-size:12px;color:#555;">{count}</span>'
                f'</td></tr>'
            )
        topics_section = f'<table>{topic_rows}</table>'
    else:
        topics_section = '<p style="color:#888;font-size:13px;">Sin datos de temas para este período.</p>'

    # ── Unresolved / Escalations ──────────────────────────────────────────────
    if data['unresolved']:
        unres_rows = ''
        for u in data['unresolved'][:15]:
            state_color = {'timeout': '#795548', 'failed': '#c62828'}.get(u['state'], '#f9a825')
            reason_short = (u['reason'] or u['summary'] or '—')[:120]
            unres_rows += (
                f'<tr style="border-bottom:1px solid #f0f0f0;vertical-align:top;">'
                f'<td style="padding:6px 10px;font-size:12px;">{u["name"]}</td>'
                f'<td style="padding:6px 10px;font-size:12px;">{u["partner"]}</td>'
                f'<td style="padding:6px 10px;font-size:12px;">'
                f'<span style="background:{state_color};color:#fff;padding:2px 6px;'
                f'border-radius:4px;font-size:10px;">{u["state"].upper()}</span></td>'
                f'<td style="padding:6px 10px;font-size:11px;color:#555;">{reason_short}</td>'
                f'</tr>'
            )
        unres_section = (
            '<table style="width:100%;border-collapse:collapse;">'
            '<tr style="background:#f5f5f5;">'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Conversación</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Contacto</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Estado</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Motivo / Resumen</th>'
            '</tr>'
            + unres_rows + '</table>'
        )
    else:
        unres_section = '<p style="color:#2e7d32;font-size:13px;">Sin escalaciones ni timeouts en este período.</p>'

    # ── Suspicious ────────────────────────────────────────────────────────────
    if data['suspicious']:
        sus_rows = ''
        type_colors = {
            'Múltiples conversaciones — posible bot': '#c62828',
            'Alto consumo por turno':                 '#e65100',
            'Actividad nocturna':                     '#6a1b9a',
            'Conversación muy larga':                 '#1565c0',
        }
        for s in data['suspicious']:
            color = type_colors.get(s['type'], '#555')
            sus_rows += (
                f'<tr style="border-bottom:1px solid #fce4ec;vertical-align:top;">'
                f'<td style="padding:6px 10px;font-size:12px;">'
                f'<span style="color:{color};font-weight:bold;">{s["type"]}</span></td>'
                f'<td style="padding:6px 10px;font-size:12px;">{s["phone"]}</td>'
                f'<td style="padding:6px 10px;font-size:12px;">{s["partner"]}</td>'
                f'<td style="padding:6px 10px;font-size:11px;color:#555;">{s["detail"]}</td>'
                f'</tr>'
            )
        sus_section = (
            '<div style="background:#fff8f8;border:1px solid #ffcdd2;border-radius:8px;padding:16px;">'
            '<p style="margin:0 0 10px;font-size:13px;font-weight:bold;color:#c62828;">'
            f'⚠️ {_s(len(data["suspicious"]), "alerta detectada", "alertas detectadas")}'
            '</p>'
            '<table style="width:100%;border-collapse:collapse;">'
            '<tr style="background:#ffebee;">'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Tipo</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Teléfono</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Contacto</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Detalle</th>'
            '</tr>'
            + sus_rows + '</table></div>'
        )
    else:
        sus_section = (
            '<div style="background:#e8f5e9;border-radius:8px;padding:12px 16px;">'
            '<p style="margin:0;color:#2e7d32;font-size:13px;">✓ Sin actividad sospechosa detectada.</p>'
            '</div>'
        )

    # ── Telegram section ─────────────────────────────────────────────────────
    tg_convs = data.get('telegram_convs', [])
    if tg_convs:
        state_badge = {
            'resolved': ('<span style="background:#2e7d32;color:#fff;font-size:10px;'
                         'padding:2px 6px;border-radius:4px;">RESUELTA</span>'),
            'timeout':  ('<span style="background:#795548;color:#fff;font-size:10px;'
                         'padding:2px 6px;border-radius:4px;">TIMEOUT</span>'),
            'failed':   ('<span style="background:#c62828;color:#fff;font-size:10px;'
                         'padding:2px 6px;border-radius:4px;">FALLIDA</span>'),
            'active':   ('<span style="background:#1565c0;color:#fff;font-size:10px;'
                         'padding:2px 6px;border-radius:4px;">ACTIVA</span>'),
            'waiting':  ('<span style="background:#f57f17;color:#fff;font-size:10px;'
                         'padding:2px 6px;border-radius:4px;">ESPERANDO</span>'),
        }
        tg_rows = ''
        for tc in tg_convs:
            badge = state_badge.get(tc['state'],
                f'<span style="background:#888;color:#fff;font-size:10px;padding:2px 6px;border-radius:4px;">{tc["state"].upper()}</span>')
            id_icon = '✅' if tc['identified'] else '❓'
            topics_str = ', '.join(tc['topics'][:3]) if tc['topics'] else '—'
            snippet = (tc['snippet'] or '—')[:100]
            tg_rows += (
                f'<tr style="border-bottom:1px solid #e0eeff;vertical-align:top;">'
                f'<td style="padding:7px 10px;font-size:13px;">{id_icon} {tc["partner"]}</td>'
                f'<td style="padding:7px 10px;font-size:12px;color:#555;">{tc["create"][11:16]} VET</td>'
                f'<td style="padding:7px 10px;text-align:center;">{tc["turns"]}</td>'
                f'<td style="padding:7px 10px;">{badge}</td>'
                f'<td style="padding:7px 10px;font-size:11px;color:#555;">{topics_str}</td>'
                f'<td style="padding:7px 10px;font-size:11px;color:#888;font-style:italic;">{snippet}</td>'
                f'</tr>'
            )
        identified_n = sum(1 for tc in tg_convs if tc['identified'])
        tg_section = (
            f'<div style="background:#e8f4fd;border:1px solid #bbdefb;border-radius:8px;padding:16px;">'
            f'<p style="margin:0 0 10px;font-size:13px;color:#1565c0;font-weight:bold;">'
            f'📱 {len(tg_convs)} conversación{"es" if len(tg_convs)!=1 else ""} · '
            f'{identified_n} identificado{"s" if identified_n!=1 else ""} · '
            f'{data["tg_sent"]} mensajes enviados</p>'
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<tr style="background:#bbdefb;">'
            f'<th style="padding:6px 10px;text-align:left;font-size:12px;">Empleado</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:12px;">Hora</th>'
            f'<th style="padding:6px 10px;text-align:center;font-size:12px;">Turnos</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:12px;">Estado</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:12px;">Temas</th>'
            f'<th style="padding:6px 10px;text-align:left;font-size:12px;">Primer mensaje</th>'
            f'</tr>'
            + tg_rows + '</table></div>'
        )
    else:
        tg_section = (
            '<div style="background:#f5f5f5;border-radius:8px;padding:12px 16px;">'
            '<p style="margin:0;color:#888;font-size:13px;">Sin conversaciones de Telegram en este período.</p>'
            '</div>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Glenda — Reporte Diario {day}</title></head>
<body style="font-family:Arial,sans-serif;background:#f4f6fb;margin:0;padding:24px 16px;">
<div style="max-width:720px;margin:0 auto;">

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:linear-gradient(135deg,#1a2c5b 0%,#0f1932 100%);
                border-radius:12px 12px 0 0;">
    <tr><td style="padding:24px 28px;">
      <h1 style="margin:0;color:#fff;font-size:22px;font-weight:900;">
        🤖 Glenda — Reporte Ejecutivo Diario{env_badge}
      </h1>
      <p style="margin:6px 0 0;color:#a8c0e8;font-size:14px;">
        Período: <strong>{day}</strong> &nbsp;·&nbsp; Generado: {today} VET
      </p>
    </td></tr>
    <tr><td>
      <div style="height:3px;background:linear-gradient(90deg,transparent,#d4af37,transparent);"></div>
    </td></tr>
  </table>

  <!-- Body -->
  <div style="background:#fff;padding:24px 28px;">

    <!-- Summary cards -->
    <h2 style="margin:0 0 14px;font-size:16px;color:#1a2c5b;">📊 Resumen del día</h2>
    {cards_html}

    <!-- API stats -->
    <table style="margin:18px 0 0;font-size:13px;">
      {api_row}
    </table>

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- By skill -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">🎯 Actividad por habilidad</h2>
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <tr style="background:#f0f4fa;">
        <th style="padding:6px 10px;text-align:left;">Habilidad</th>
        <th style="padding:6px 10px;text-align:center;">Total</th>
        <th style="padding:6px 10px;text-align:center;">Resuelt.</th>
        <th style="padding:6px 10px;text-align:center;">Escalad.</th>
        <th style="padding:6px 10px;text-align:center;">Timeout/Fail</th>
        <th style="padding:6px 10px;text-align:center;">Turnos avg</th>
        <th style="padding:6px 10px;text-align:left;">Temas comunes</th>
      </tr>
      {skill_rows if skill_rows else '<tr><td colspan="7" style="padding:10px;color:#888;">Sin actividad</td></tr>'}
    </table>

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- Topics -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">💬 Temas más frecuentes</h2>
    {topics_section}

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- Unresolved / Escalations -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">
      ⚡ Consultas sin resolver / Escalaciones
      <span style="font-size:13px;font-weight:normal;color:#555;">
        (temas a considerar para futuras mejoras de Glenda)
      </span>
    </h2>
    {unres_section}

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- Suspicious -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">🔍 Actividad sospechosa</h2>
    {sus_section}

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- Telegram activity -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">
      📱 Actividad en Telegram (@GlendaUeipabBot)
      <span style="font-size:13px;font-weight:normal;color:#555;">— conversaciones de empleados</span>
    </h2>
    {tg_section}

    <div style="border-top:2px solid #d4af37;margin:22px 0;"></div>

    <!-- Calibration programme -->
    <h2 style="margin:0 0 10px;font-size:16px;color:#1a2c5b;">🧪 Programa Calibración Glenda
      <span style="font-size:13px;font-weight:normal;color:#555;">
        — seguimiento de testers y bono (deadline {calib['deadline'] if calib else CALIBRATION_DEADLINE})
      </span>
    </h2>
    {build_calibration_section(calib)}

  </div>

  <!-- Footer -->
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#1a2c5b;border-radius:0 0 12px 12px;">
    <tr><td style="padding:14px 24px;text-align:center;">
      <p style="margin:0;font-size:11px;color:#a8c0e8;">
        Reporte automático generado por <strong>Glenda Daily Digest</strong> &nbsp;·&nbsp;
        Instituto Privado Andrés Bello &nbsp;·&nbsp; {today}
      </p>
    </td></tr>
  </table>

</div>
</body>
</html>"""


# ── Calibration programme data ────────────────────────────────────────────────

CALIBRATION_NOTICE_KEY = 'glenda_calibracion_v1'
CALIBRATION_DEADLINE   = '2026-05-30'
BONUS_MIN_CONVS        = 3
BONUS_MIN_FEEDBACK     = 1


def fetch_calibration_data(db, uid, pw, models, start_str, end_str):
    """Fetch calibration programme scoreboard + yesterday's activity."""

    # All enrolled participants
    acks = rpc(models, db, uid, pw, 'hr.notice.acknowledgment', 'search_read',
               [[('notice_key', '=', CALIBRATION_NOTICE_KEY)]],
               {'fields': ['id', 'employee_id', 'wa_number', 'state'], 'limit': 100})
    if not acks:
        return None

    # Build digit → participant map
    participants = {}
    for ack in acks:
        digits = re.sub(r'\D', '', ack['wa_number'] or '')
        if not digits:
            continue
        emp_name = ack['employee_id'][1] if ack['employee_id'] else '—'
        emp_id   = ack['employee_id'][0] if ack['employee_id'] else None
        participants[digits] = {
            'employee':          emp_name,
            'wa':                ack['wa_number'] or '—',
            'emp_id':            emp_id,
            'enrolled':          ack['state'] == 'acknowledged',
            'conv_total':        0,
            'conv_yesterday':    0,
            'feedback_total':    0,
            'feedback_yesterday': 0,
            'bonus_eligible':    False,
        }

    # All general_inquiry conversations — match by phone digits
    all_convs = rpc(models, db, uid, pw, 'ai.agent.conversation', 'search_read',
                    [[('skill_id.code', '=', 'general_inquiry')]],
                    {'fields': ['phone', 'create_date', 'state'], 'limit': 2000})
    for conv in all_convs:
        d = re.sub(r'\D', '', conv.get('phone') or '')
        if d not in participants:
            continue
        participants[d]['conv_total'] += 1
        if start_str <= (conv.get('create_date') or '') < end_str:
            participants[d]['conv_yesterday'] += 1

    # All feedback records
    all_fb = rpc(models, db, uid, pw, 'ai.agent.feedback', 'search_read',
                 [[]],
                 {'fields': ['employee_id', 'category', 'suggestion', 'state', 'date'], 'limit': 500})

    yesterday_feedback = []
    for fb in all_fb:
        emp_id = fb['employee_id'][0] if fb['employee_id'] else None
        # Match to participant by emp_id
        for d, p in participants.items():
            if p['emp_id'] == emp_id:
                p['feedback_total'] += 1
                fb_date = fb.get('date') or ''
                if start_str <= fb_date < end_str:
                    p['feedback_yesterday'] += 1
                    yesterday_feedback.append({
                        'employee': p['employee'],
                        'category': fb.get('category', 'otro'),
                        'suggestion': (fb.get('suggestion') or '')[:200],
                        'state': fb.get('state', 'pending'),
                    })
                break

    # Compute bonus eligibility
    bonus_count = 0
    for p in participants.values():
        p['bonus_eligible'] = (
            p['enrolled'] and
            p['conv_total'] >= BONUS_MIN_CONVS and
            p['feedback_total'] >= BONUS_MIN_FEEDBACK
        )
        if p['bonus_eligible']:
            bonus_count += 1

    # Sort: bonus eligible first, then by conv_total desc
    sorted_participants = sorted(
        participants.values(),
        key=lambda p: (not p['bonus_eligible'], -p['conv_total'], -p['feedback_total'])
    )

    active_yesterday = sum(1 for p in participants.values() if p['conv_yesterday'] > 0)

    return {
        'participants':       sorted_participants,
        'yesterday_feedback': yesterday_feedback,
        'bonus_count':        bonus_count,
        'total_enrolled':     len(participants),
        'active_yesterday':   active_yesterday,
        'deadline':           CALIBRATION_DEADLINE,
    }


def build_calibration_section(calib):
    """Build the calibration programme HTML section."""
    if not calib:
        return '<p style="color:#888;font-size:13px;">Sin datos del programa de calibración.</p>'

    bonus_count   = calib['bonus_count']
    total         = calib['total_enrolled']
    active_y      = calib['active_yesterday']
    deadline      = calib['deadline']

    # Header summary chips
    def chip(val, label, color):
        return (
            f'<span style="display:inline-block;background:{color};color:#fff;'
            f'border-radius:6px;padding:4px 12px;font-size:13px;margin:2px 4px 2px 0;">'
            f'<strong>{val}</strong> {label}</span>'
        )

    chips = (
        chip(f'{bonus_count}/{total}', 'elegibles bono', '#2e7d32') +
        chip(active_y, 'activos ayer', '#1565c0') +
        chip(len(calib['yesterday_feedback']), 'sugerencias nuevas', '#6a1b9a') +
        f'<span style="font-size:12px;color:#888;margin-left:8px;">Deadline: <strong>{deadline}</strong></span>'
    )

    # Scoreboard table
    rows = ''
    for p in calib['participants']:
        if not p['enrolled']:
            continue
        elig_badge = (
            '<span style="background:#2e7d32;color:#fff;padding:2px 7px;'
            'border-radius:4px;font-size:10px;font-weight:bold;">✓ BONO</span>'
            if p['bonus_eligible'] else ''
        )
        conv_y = f' <span style="color:#1565c0;font-size:10px;">(+{p["conv_yesterday"]} ayer)</span>' \
                 if p['conv_yesterday'] else ''
        fb_y   = f' <span style="color:#6a1b9a;font-size:10px;">(+{p["feedback_yesterday"]} ayer)</span>' \
                 if p['feedback_yesterday'] else ''

        conv_color  = '#2e7d32' if p['conv_total'] >= BONUS_MIN_CONVS else ('#f9a825' if p['conv_total'] > 0 else '#bbb')
        fb_color    = '#2e7d32' if p['feedback_total'] >= BONUS_MIN_FEEDBACK else '#bbb'

        rows += (
            f'<tr style="border-bottom:1px solid #eee;">'
            f'<td style="padding:6px 10px;font-size:12px;">{p["employee"]}</td>'
            f'<td style="padding:6px 10px;font-size:11px;color:#555;">{p["wa"]}</td>'
            f'<td style="padding:6px 10px;text-align:center;font-weight:bold;color:{conv_color};">'
            f'{p["conv_total"]}{conv_y}</td>'
            f'<td style="padding:6px 10px;text-align:center;font-weight:bold;color:{fb_color};">'
            f'{p["feedback_total"]}{fb_y}</td>'
            f'<td style="padding:6px 10px;text-align:center;">{elig_badge}</td>'
            f'</tr>'
        )

    scoreboard = (
        '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
        '<tr style="background:#f0f4fa;">'
        '<th style="padding:6px 10px;text-align:left;">Empleado</th>'
        '<th style="padding:6px 10px;text-align:left;">WhatsApp</th>'
        f'<th style="padding:6px 10px;text-align:center;">Convs (≥{BONUS_MIN_CONVS})</th>'
        f'<th style="padding:6px 10px;text-align:center;">Sugerencias (≥{BONUS_MIN_FEEDBACK})</th>'
        '<th style="padding:6px 10px;text-align:center;">Bono</th>'
        '</tr>'
        + (rows or '<tr><td colspan="5" style="padding:10px;color:#888;">Sin actividad aún</td></tr>')
        + '</table>'
    )

    # Yesterday's new suggestions
    if calib['yesterday_feedback']:
        cat_labels = {
            'flujo': 'Flujo', 'respuesta': 'Respuesta', 'idioma': 'Lenguaje',
            'asistencia': 'Asistencia', 'conocimiento': 'Conocimiento',
            'tecnico': 'Técnico', 'otro': 'Otro',
        }
        fb_rows = ''
        for fb in calib['yesterday_feedback']:
            cat = cat_labels.get(fb['category'], fb['category'])
            fb_rows += (
                f'<tr style="border-bottom:1px solid #f0e6ff;vertical-align:top;">'
                f'<td style="padding:6px 10px;font-size:12px;font-weight:bold;">{fb["employee"]}</td>'
                f'<td style="padding:6px 10px;">'
                f'<span style="background:#6a1b9a;color:#fff;padding:2px 8px;'
                f'border-radius:4px;font-size:10px;">{cat}</span></td>'
                f'<td style="padding:6px 10px;font-size:12px;color:#333;">{fb["suggestion"]}</td>'
                f'</tr>'
            )
        fb_section = (
            '<h4 style="margin:16px 0 8px;color:#6a1b9a;font-size:13px;">Sugerencias recibidas ayer</h4>'
            '<table style="width:100%;border-collapse:collapse;">'
            '<tr style="background:#f5e6ff;">'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Empleado</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Categoría</th>'
            '<th style="padding:6px 10px;text-align:left;font-size:12px;">Sugerencia</th>'
            '</tr>'
            + fb_rows + '</table>'
        )
    else:
        fb_section = (
            '<p style="color:#888;font-size:12px;margin:12px 0 0;">'
            'Sin sugerencias nuevas ayer.</p>'
        )

    return f"""
<div style="margin-bottom:4px;">{chips}</div>
{scoreboard}
{fb_section}
"""


# ── Email sending ─────────────────────────────────────────────────────────────

def send_email(env_name, subject, html_body):
    db, uid, pw, models = connect(env_name)
    # Create as 'outgoing' — Odoo's mail scheduler picks it up within minutes.
    # Calling send() via XML-RPC has session/cache issues; queuing is safer.
    mail_id = rpc(models, db, uid, pw, 'mail.mail', 'create', [[{
        'subject':    subject,
        'email_from': FROM_EMAIL,
        'email_to':   TO_EMAIL,
        'body_html':  html_body,
        'state':      'outgoing',
    }]])
    logger.info("Digest email queued (mail id=%s) → %s via %s Odoo",
                mail_id, TO_EMAIL, env_name)
    return mail_id


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='Report date YYYY-MM-DD (default: yesterday)')
    parser.add_argument('--env', default='production',
                        choices=['testing', 'production'],
                        help='Odoo environment to query (default: production)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print email body to stdout instead of sending')
    args = parser.parse_args()

    if args.date:
        day = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        day = date.today() - timedelta(days=1)

    if args.env == 'production' and not ODOO_CONFIGS['production']['password']:
        logger.error("ODOO_PASSWORD not set. Source /root/.odoo_agent_env_prod first.")
        sys.exit(1)

    convs, msgs = fetch_data(args.env, day)
    data = analyse(convs, msgs, day)

    if not data:
        logger.warning("No data for %s — sending empty digest", day)
        data = {
            'day': day, 'total_convs': 0, 'resolved': 0, 'escalated': 0,
            'timeout': 0, 'active': 0, 'wa_sent': 0, 'wa_recv': 0,
            'in_tokens': 0, 'out_tokens': 0, 'claude_cost': 0.0,
            'skill_stats': {}, 'topics': [], 'unresolved': [], 'suspicious': [],
        }

    # Calibration data (uses same connection — re-open)
    calib = None
    try:
        db, uid, pw, models_conn = connect(args.env)
        start_utc = datetime(day.year, day.month, day.day, 4, 0, 0)
        end_utc   = start_utc + timedelta(days=1)
        calib = fetch_calibration_data(
            db, uid, pw, models_conn,
            start_utc.strftime('%Y-%m-%d %H:%M:%S'),
            end_utc.strftime('%Y-%m-%d %H:%M:%S'),
        )
    except Exception as e:
        logger.warning("Could not fetch calibration data: %s", e)

    day_str = day.strftime('%d/%m/%Y')
    bonus_str = f' · {calib["bonus_count"]}/{calib["total_enrolled"]} bono' if calib else ''
    subject = (
        f"[Glenda] Reporte Diario {day_str} — "
        f"{data['total_convs']} conv · "
        f"{data['resolved']} resueltas · "
        f"${data['claude_cost']:.3f} Claude"
        f"{bonus_str}"
    )
    if args.env == 'testing':
        subject = '[TESTING] ' + subject

    html = build_html(data, args.env, calib)

    if args.dry_run:
        print(html)
        logger.info("Dry run — email not sent. Subject: %s", subject)
        return

    send_email(args.env, subject, html)
    logger.info("Done.")


if __name__ == '__main__':
    main()
