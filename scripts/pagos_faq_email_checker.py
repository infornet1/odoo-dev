#!/usr/bin/env python3
"""
Pagos@ FAQ Email Checker — UEIPAB

Monitors the pagos@ueipab.edu.ve FreeScout mailbox for incoming customer
emails and auto-responds with AI-generated FAQ answers using Claude Haiku.

Behaviour:
- Finds new ACTIVE unassigned conversations in pagos@ (mailbox_id=2)
- Calls Claude Haiku with full budget/billing knowledge
- FAQ answer  → posts a customer-visible reply, keeps UNASSIGNED
- Needs escalation → posts an internal note flagged ⚠️, keeps UNASSIGNED
- Marks processed conversations with [FAQ-AI] subject prefix

Usage:
    python3 scripts/pagos_faq_email_checker.py           # dry-run
    python3 scripts/pagos_faq_email_checker.py --live    # send replies

Cron: /etc/cron.d/pagos_faq_email_checker
    */30 10-21 * * 1-5  root  TARGET_ENV=production source /root/.odoo_agent_env_prod && \
        python3 /opt/odoo-dev/scripts/pagos_faq_email_checker.py --live \
        >> /var/log/pagos_faq_email_checker.log 2>&1
"""

import json
import logging
import os
import re
import sys
import requests
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

LIVE = '--live' in sys.argv

FS_MAILBOX_ID   = 2        # pagos@ueipab.edu.ve
FS_INBOX_FOLDER = 25       # type=1 (Unassigned inbox)
PROCESSED_TAG   = '[FAQ-AI]'
ESCALATION_TAG  = '[FAQ-AI][ESCALAR]'

# Senders that are always automated — never genuine parent inquiries
SYSTEM_SENDERS = frozenset({
    'mailer-daemon', 'postmaster', 'daemon', 'noreply', 'no-reply',
    'donotreply', 'do-not-reply', 'notifications@', 'notificaciones@',
    'finanzas@ueipab.edu.ve',          # internal BCV rate / automated notifications
    'pagos@ueipab.edu.ve',             # circular — our own mailbox
    'soporte@ueipab.edu.ve',
    'recursoshumanos@ueipab.edu.ve',
})

# Subject patterns that identify automated/system emails
_AUTO_SUBJECT_RE = re.compile(
    r'tasa\s+bcv'
    r'|delivery\s+status\s+notification'
    r'|mail\s+delivery\s+(failed|sub)'
    r'|undelivered\s+mail|returned\s+mail'
    r'|out\s+of\s+(office|the\s+office)'
    r'|auto.?reply|automatic\s+reply'
    r'|\[glenda\]'               # Glenda-generated escalation convs looping back
    r'|backup\s+payment'         # payment processor marketing spam
    r'|order\s+disruption',
    re.IGNORECASE,
)

ANTHROPIC_CONFIG_PATH = '/opt/odoo-dev/config/anthropic_api.json'
FS_API_CONFIG_PATH    = '/opt/odoo-dev/config/freescout_api.json'

STATE_FILE = os.path.join(os.path.dirname(__file__), 'pagos_faq_email_checker_state.json')
LOG_FILE   = '/var/log/pagos_faq_email_checker.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ============================================================================
# Knowledge block injected into Claude's system prompt
# ============================================================================

SYSTEM_PROMPT = """Eres el asistente virtual de pagos del Colegio Andrés Bello (UEIPAB), El Tigre, Venezuela.
Tu función es responder preguntas frecuentes sobre la propuesta económica 2026-2027 y pagos en general.
Recibirás el contenido de un correo electrónico enviado a pagos@ueipab.edu.ve y debes decidir:

A) RESPONDER: Si puedes responder la pregunta de forma factual con el conocimiento que tienes.
B) ESCALAR: Si la consulta requiere revisión humana (disputas, excepciones, casos complejos, datos específicos de cuenta).

CONOCIMIENTO — PROPUESTA ECONÓMICA 2026-2027 (APROBADA):
La consulta parental cerró el 26/05/2026. Opción A ganó con 108 votos (60,7% de 114 votantes).
Vigente a partir de septiembre 2026. Aprobada por contraloría (Resoluciones MPPE 0009 y 024-2020).

TARIFAS CONFIRMADAS 2026-2027:
- Mensualidad: $218,88/mes (incremento 10,89% vs año anterior)
- Pronto pago (días 1-10): $207,93
- Costo anual por alumno: $2.845,45
- Presupuesto total: $589.649 (67% personal + 33% materiales/servicios)

TARIFA ACTUAL (2025-2026, vigente hasta agosto 2026):
- Mensualidad: $197,38 | Pronto pago: $162,39 | Cashea disponible

__PRICING_GROUND_TRUTH__

COSTOS OPCIONALES (según presentación oficial, NO incluidos en cotización estándar):
- MUN Bachillerato: $5 | MUN Primaria: $5 | Talleres: $5

CONTEXTO ECONÓMICO:
- Inflación 611,86% | Bs/USD $487,12 (vs $154 en abril) — justifica el ajuste

PRESENTACIÓN OFICIAL:
https://docs.google.com/presentation/d/16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA

MÉTODOS DE PAGO ACEPTADOS:
- Transferencia bancaria, Pago Móvil, Cashea (cuotas), tarjetas nacionales e internacionales
- Confirmar detalles bancarios en pagos@ueipab.edu.ve

MORA: https://odoo.ueipab.edu.ve/mora-policy/

CUÁNDO ESCALAR (responde "escalar"):
- Solicitud de excepción, descuento especial o prórroga
- Disputa de cobro o reclamo formal
- Preguntas sobre saldo o deuda específica del representante
- Amenaza legal o queja grave
- Cualquier caso donde no tienes datos concretos para responder

INSTRUCCIONES DE RESPUESTA:
- Responde en español venezolano, cálido y profesional
- Sé conciso — máximo 200 palabras por respuesta
- Siempre firma: "Equipo de Pagos — Colegio Andrés Bello"
- Incluye el enlace de la presentación cuando pregunten por la propuesta
- Si preguntan por la votación o el resultado: la consulta cerró el 26/05/2026 con Opción A ganadora (108 votos, 60,7%)
- Cuando menciones las tarifas 2026-2027, SIEMPRE destaca primero la promoción del 1er llamado (inscripción anticipada + convenio de pago, hasta el 31 julio 2026, según TARIFAS OFICIALES arriba) antes de mencionar la mensualidad regular. Es una oportunidad de ahorro concreta y vigente.

FORMATO DE RESPUESTA (JSON estricto, sin markdown):
{
  "action": "responder" o "escalar",
  "reply": "texto de respuesta al cliente (si action=responder)",
  "escalation_reason": "motivo breve (si action=escalar)",
  "escalation_note": "nota interna detallada para el equipo (si action=escalar)"
}
"""

# ============================================================================
# State management
# ============================================================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'processed_conv_ids': []}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ============================================================================
# FreeScout REST API helpers (read)
# ============================================================================

def _is_automated(conv):
    """Return True if this looks like a system/automated email, not a parent inquiry."""
    sender  = (conv.get('last_from') or conv.get('customer_email') or '').lower()
    subject = (conv.get('subject') or '').lower()
    if any(s in sender for s in SYSTEM_SENDERS):
        return True
    if _AUTO_SUBJECT_RE.search(subject):
        return True
    return False


def strip_html(html):
    """Basic HTML → plain text."""
    text = re.sub(r'<br\s*/?>', '\n', html or '', flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

# ============================================================================
# FreeScout REST API helpers
# ============================================================================

def _fs_headers():
    cfg = json.load(open(FS_API_CONFIG_PATH))
    return {'X-FreeScout-API-Key': cfg['api_key'], 'Content-Type': 'application/json'}, cfg['api_url']


def fs_post_reply(conv_id, html_body):
    """Post a customer-visible reply to the conversation."""
    headers, api_url = _fs_headers()
    r = requests.post(
        f"{api_url}/conversations/{conv_id}/threads",
        json={'type': 'message', 'text': html_body, 'user': 1},
        headers=headers, timeout=15,
    )
    r.raise_for_status()
    return r


def fs_post_note(conv_id, html_body):
    """Post an internal note (not visible to customer)."""
    headers, api_url = _fs_headers()
    r = requests.post(
        f"{api_url}/conversations/{conv_id}/threads",
        json={'type': 'note', 'text': html_body, 'user': 1},
        headers=headers, timeout=15,
    )
    r.raise_for_status()
    return r


def fs_update_subject(conv_id, new_subject):
    """Update conversation subject via REST API."""
    headers, api_url = _fs_headers()
    r = requests.put(
        f"{api_url}/conversations/{conv_id}",
        json={'subject': new_subject, 'byUser': 1},
        headers=headers, timeout=15,
    )
    r.raise_for_status()
    return r


def fs_get_conversations_page(page=1):
    headers, api_url = _fs_headers()
    r = requests.get(
        f"{api_url}/conversations",
        headers=headers,
        params={'mailboxId': FS_MAILBOX_ID, 'status': 'active', 'page': page},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get('_embedded', {}).get('conversations', [])


def fs_get_conversation_detail(conv_id):
    headers, api_url = _fs_headers()
    r = requests.get(f"{api_url}/conversations/{conv_id}", headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def get_new_conversations(processed_ids):
    """Fetch active unprocessed conversations in pagos@ inbox via Freescout API."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    processed_set = set(processed_ids)
    candidates = []
    page = 1
    while True:
        convs = fs_get_conversations_page(page)
        if not convs:
            break
        for c in convs:
            conv_id = c['id']
            subject = c.get('subject', '')
            if conv_id in processed_set:
                continue
            if subject.startswith(PROCESSED_TAG) or '[AUSENCIA]' in subject:
                continue
            try:
                created = datetime.strptime(c.get('createdAt', '')[:19], '%Y-%m-%dT%H:%M:%S')
                if created < cutoff:
                    continue
            except Exception:
                pass
            candidates.append(conv_id)
        if len(convs) < 25:
            break
        page += 1

    result = []
    for conv_id in candidates[:20]:
        try:
            detail = fs_get_conversation_detail(conv_id)
            threads = detail.get('_embedded', {}).get('threads', [])
            customer_threads = [t for t in threads if t.get('type') == 'customer']
            if customer_threads:
                latest = max(customer_threads, key=lambda t: t.get('createdAt', ''))
                last_body = latest.get('body', '')
                last_from = (latest.get('createdBy') or {}).get('email', '')
            else:
                last_body = ''
                last_from = ''
            customer = detail.get('customer') or {}
            result.append({
                'id':             conv_id,
                'subject':        detail.get('subject', ''),
                'created_at':     detail.get('createdAt', ''),
                'customer_email': customer.get('email', ''),
                'first_name':     customer.get('firstName', ''),
                'last_name':      customer.get('lastName', ''),
                'last_body':      last_body,
                'last_from':      last_from,
            })
        except Exception as e:
            logger.warning("Failed to fetch conv #%d detail: %s", conv_id, e)
    return result

# ============================================================================
# Claude Haiku
# ============================================================================

# Static fallback only — live block comes from sale.order.get_pricing_ground_truth()
_PRICING_FALLBACK = """OFERTA INSCRIPCIÓN ANTICIPADA — 1er llamado (hasta 31 julio 2026):
- Inscripción: $187,51 | Mensualidad convenio: $197,38 (2 hermanos -5%: $187,51 c/u | 3 -8%: $181,59 | 4+ -11%: $175,67)
- Incluye convenio de pago; requisito: solvente con junio 2026
2do llamado (agosto): inscripción $207,93 / mensualidad $218,88 | 3er llamado (sept): $218,88 / $218,88
COSTOS ANUALES POR ALUMNO: $111,58 hasta 31 jul (seguro $30,58 + inglés $35 + olimpiadas $10 + enciclopedia $36); $116,58 desde 1 ago (inglés $40)
Todos los montos en USD, pagaderos a tasa BCV del día."""


def _resolve_system_prompt():
    """Inject live pricing ground truth (Odoo ueipab_sales catalog) into SYSTEM_PROMPT."""
    try:
        import xmlrpc.client
        xcfg = json.load(open('/opt/odoo-dev/config/production.json'))['production']['xmlrpc']
        uid = xmlrpc.client.ServerProxy(xcfg['url'] + '/xmlrpc/2/common').authenticate(
            xcfg['db'], xcfg['user'], xcfg['api_key'], {})
        pricing = xmlrpc.client.ServerProxy(xcfg['url'] + '/xmlrpc/2/object').execute_kw(
            xcfg['db'], uid, xcfg['api_key'], 'sale.order', 'get_pricing_ground_truth', [])
        logger.info("Pricing ground truth fetched live from Odoo catalog (%d chars)", len(pricing))
    except Exception as e:
        logger.warning("Pricing ground truth fetch failed (%s) — using static fallback", e)
        pricing = _PRICING_FALLBACK
    return SYSTEM_PROMPT.replace('__PRICING_GROUND_TRUTH__', pricing)


_SYSTEM_PROMPT_FINAL = None


def call_claude(subject, body_plain):
    """Call Claude Haiku and return parsed JSON response."""
    global _SYSTEM_PROMPT_FINAL
    if _SYSTEM_PROMPT_FINAL is None:
        _SYSTEM_PROMPT_FINAL = _resolve_system_prompt()
    cfg = json.load(open(ANTHROPIC_CONFIG_PATH))
    api_key = cfg.get('api', {}).get('api_key') or cfg.get('api_key', '')

    user_message = (
        f"Asunto del correo: {subject}\n\n"
        f"Contenido:\n{body_plain[:2000]}"
    )

    r = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        json={
            'model': 'claude-haiku-4-5-20251001',
            'max_tokens': 600,
            'system': _SYSTEM_PROMPT_FINAL,
            'messages': [{'role': 'user', 'content': user_message}],
        },
        timeout=30,
    )
    r.raise_for_status()

    raw = r.json()['content'][0]['text'].strip()
    # Extract first JSON object — handles extra text before/after
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in Claude response: {raw[:200]}")
    return json.loads(m.group(0))

# ============================================================================
# Main
# ============================================================================

def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info("=" * 60)
    logger.info("Pagos@ FAQ Email Checker — %s %s", ts, '(LIVE)' if LIVE else '(DRY RUN)')
    logger.info("=" * 60)

    state = load_state()
    processed_ids = state.get('processed_conv_ids', [])

    conversations = get_new_conversations(processed_ids)

    if not conversations:
        logger.info("No new conversations to process.")
        return

    logger.info("Found %d new conversation(s) in pagos@ inbox", len(conversations))

    # Filter automated/system emails before calling Claude
    genuine = []
    for conv in conversations:
        if _is_automated(conv):
            logger.info("  Skip (automated): #%d %s", conv['id'], (conv.get('subject') or '')[:60])
            processed_ids.append(conv['id'])  # mark seen to avoid re-checking next run
        else:
            genuine.append(conv)

    if not genuine:
        logger.info("All conversations filtered as automated — nothing to process.")
        save_state(state)
        return

    logger.info("%d genuine parent conversation(s) after filter", len(genuine))

    answered = escalated = errors = 0

    for conv in genuine:
        conv_id  = conv['id']
        subject  = conv['subject'] or '(sin asunto)'
        body_raw = conv.get('last_body') or ''
        body     = strip_html(body_raw)
        sender   = conv.get('last_from') or conv.get('customer_email') or 'representante'
        name     = f"{conv.get('first_name') or ''} {conv.get('last_name') or ''}".strip() or 'Representante'

        logger.info("--- Conv #%d | %s | %s", conv_id, subject[:60], sender)

        if not body.strip():
            logger.info("  Skipping — no readable body")
            processed_ids.append(conv_id)
            continue

        try:
            result = call_claude(subject, body)
        except Exception as e:
            logger.error("  Claude error: %s", e)
            errors += 1
            continue

        action = result.get('action', 'escalar')
        logger.info("  Claude decision: %s", action)

        if action == 'responder':
            reply_text = result.get('reply', '')
            now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            note_html = (
                f"<p><strong>💬 Borrador de respuesta sugerida por Glenda FAQ</strong></p>"
                f"<p><strong>Remitente:</strong> {name} ({sender})</p>"
                f"<hr/>"
                f"<p>{reply_text.replace(chr(10), '<br/>')}</p>"
                f"<hr/>"
                f"<p><em>Revisar y enviar manualmente si procede — {now_str}</em></p>"
            )
            new_subject = f"{PROCESSED_TAG} {subject}"

            if LIVE:
                try:
                    fs_post_note(conv_id, note_html)
                    fs_update_subject(conv_id, new_subject)
                    logger.info("  Draft note posted (no customer reply) + subject updated")
                    answered += 1
                except Exception as e:
                    logger.error("  FS API error: %s", e)
                    errors += 1
                    continue
            else:
                logger.info("  DRY RUN — draft note:\n    %s", reply_text[:200])
                answered += 1

        else:  # escalar
            reason  = result.get('escalation_reason', 'Consulta requiere revisión humana')
            note_detail = result.get('escalation_note', '')
            now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
            note_html = (
                f"<p><strong>⚠️ Escalación sugerida por Glenda FAQ</strong></p>"
                f"<p><strong>Motivo:</strong> {reason}</p>"
                f"<p><strong>Detalle:</strong> {note_detail}</p>"
                f"<p><strong>Remitente:</strong> {name} ({sender})</p>"
                f"<p><em>Generado automáticamente — {now_str}</em></p>"
            )
            new_subject = f"{ESCALATION_TAG} {subject}"

            if LIVE:
                try:
                    fs_post_note(conv_id, note_html)
                    fs_update_subject(conv_id, new_subject)
                    logger.info("  Escalation note posted + subject updated")
                    escalated += 1
                except Exception as e:
                    logger.error("  FS API error: %s", e)
                    errors += 1
                    continue
            else:
                logger.info("  DRY RUN — escalation: %s | note: %s", reason, note_detail[:120])
                escalated += 1

        processed_ids.append(conv_id)

    state['processed_conv_ids'] = processed_ids[-500:]  # keep last 500
    state['last_run'] = datetime.now().isoformat()
    save_state(state)

    logger.info("-" * 60)
    logger.info("Done. answered=%d  escalated=%d  errors=%d%s",
                answered, escalated, errors, '' if LIVE else ' (DRY RUN)')


if __name__ == '__main__':
    main()
