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
import pymysql
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

LIVE = '--live' in sys.argv

FS_MAILBOX_ID   = 2        # pagos@ueipab.edu.ve
FS_INBOX_FOLDER = 25       # type=1 (Unassigned inbox)
PROCESSED_TAG   = '[FAQ-AI]'
ESCALATION_TAG  = '[FAQ-AI][ESCALAR]'

FS_DB = dict(
    host='localhost', user='free297', password='1gczp1S@3!',
    database='free297', charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
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

CONOCIMIENTO — PROPUESTA ECONÓMICA 2026-2027:
Aprobada sin objeción por contraloría el 18/05/2026 (Resoluciones MPPE 0009 y 024-2020).

OPCIÓN A — $218,88/mes (incremento 10,89%):
- Pronto pago días 1-10: ahorro $10,95 → pagas $207,93
- Costo anual por alumno: $2.845,45
- Presupuesto total: $589.649 (67% personal + 33% materiales/servicios)

OPCIÓN B — $236,58/mes (incremento 19,86%):
- Pronto pago días 1-10: ahorro $11,82 → pagas $224,75
- Costo anual por alumno: $3.075,55
- Presupuesto total: $637.284 (67% personal + 33% materiales/servicios)

DESCUENTOS POR HERMANOS (sobre mensualidad base):
- 1er hijo/a: 5% | 2do: 8% | 3er en adelante: 11%
- Pronto pago (5% adicional) se aplica sobre la mensualidad ya descontada

COSTOS ÚNICOS ANUALES POR ALUMNO (pagaderos en inscripción):
- Seguro escolar: $30,58 | Guía de inglés: $25 | Olimpiadas: $10
- Enciclopedia digital: $36 | MUN Bachillerato: $5 | MUN Primaria: $5 | Talleres: $5

OFERTA INSCRIPCIÓN ANTICIPADA (hasta 31 julio 2026):
- Inscripción: $187,51 | Mensualidad septiembre: $197,38 (tarifa actual)
- Requisito: año 2025-2026 completamente saldado

CONTEXTO ECONÓMICO:
- Inflación 611,86% | Bs/USD $487,12 (vs $154 en abril) — justifica el ajuste

CRONOGRAMA VOTACIÓN:
- 18/05: Contraloría aprobó por unanimidad
- 19/05 3pm y 20/05 2pm: Videollamadas de aclaración
- 21-23/05: Período de divulgación y votación (correo personalizado)
- 26/05: Anuncio del resultado

VOTACIÓN:
- Solo representantes ACTIVOS reciben enlace de votación por correo
- Una sola vez por familia | Correo a pagos@ueipab.edu.ve si no recibió enlace

PRESENTACIÓN OFICIAL:
https://docs.google.com/presentation/d/16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA

MÉTODOS DE PAGO ACEPTADOS:
- Transferencia bancaria, Pago Móvil, Cashea (cuotas), tarjetas nacionales e internacionales
- Confirmar detalles bancarios en pagos@ueipab.edu.ve

MORA: https://odoo.ueipab.edu.ve/mora-policy/

PROPUESTA ECONÓMICA 2026-2027 — ETAPA DE CONSULTA ACTIVA:
La propuesta ha sido presentada oficialmente. Comparte ambas opciones con total transparencia:
- Opción A: $218,88/mes (incremento 10,89%). Pronto pago: $207,93.
- Opción B: $236,58/mes (incremento 19,86%). Pronto pago: $224,75.
- Votación: 22–23 de mayo por correo electrónico. Un voto por familia.
- Presentación: https://docs.google.com/presentation/d/16EmMb-8mMtnsvdLLnc4Cx8srhzDrzjrsOvNIcXvTkEA
- Sin enlace de votación: indicar que escriba a pagos@ueipab.edu.ve.
La mensualidad VIGENTE es $197,38 | Pronto pago: $162,39 | Cashea disponible.

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
- NO inventes porcentajes de votación ni resultados — no están disponibles aún
- Si es una consulta de votación y no recibió enlace: indícale que escriba a pagos@ueipab.edu.ve

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
# FreeScout MySQL helpers
# ============================================================================

def get_new_conversations(conn, processed_ids):
    """Fetch active unprocessed conversations in pagos@ inbox."""
    placeholders = ','.join(['%s'] * len(processed_ids)) if processed_ids else '0'
    not_in = f"AND c.id NOT IN ({placeholders})" if processed_ids else ""
    query = f"""
        SELECT c.id, c.subject, c.created_at, c.user_id,
               e.email AS customer_email,
               cu.first_name, cu.last_name,
               (SELECT t.body FROM threads t
                WHERE t.conversation_id = c.id AND t.type = 1
                ORDER BY t.created_at DESC LIMIT 1) AS last_body,
               (SELECT t.`from` FROM threads t
                WHERE t.conversation_id = c.id AND t.type = 1
                ORDER BY t.created_at DESC LIMIT 1) AS last_from
        FROM conversations c
        LEFT JOIN customers cu ON c.customer_id = cu.id
        LEFT JOIN emails e ON e.customer_id = cu.id
        WHERE c.mailbox_id = {FS_MAILBOX_ID}
          AND c.status = 1
          AND c.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
          AND c.subject NOT LIKE %s
          AND c.subject NOT LIKE %s
          {not_in}
        ORDER BY c.created_at ASC
        LIMIT 20
    """
    params = [f'%{PROCESSED_TAG}%', f'%[AUSENCIA]%'] + (processed_ids if processed_ids else [])
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()


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

# ============================================================================
# Claude Haiku
# ============================================================================

def call_claude(subject, body_plain):
    """Call Claude Haiku and return parsed JSON response."""
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
            'system': SYSTEM_PROMPT,
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

    conn = pymysql.connect(**FS_DB)
    try:
        conversations = get_new_conversations(conn, processed_ids)
    finally:
        conn.close()

    if not conversations:
        logger.info("No new conversations to process.")
        return

    logger.info("Found %d new conversation(s) in pagos@ inbox", len(conversations))

    answered = escalated = errors = 0

    for conv in conversations:
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
            reply_html = reply_text.replace('\n', '<br/>')
            new_subject = f"{PROCESSED_TAG} {subject}"

            if LIVE:
                try:
                    fs_post_reply(conv_id, reply_html)
                    fs_update_subject(conv_id, new_subject)
                    logger.info("  Reply sent + subject updated")
                    answered += 1
                except Exception as e:
                    logger.error("  FS API error: %s", e)
                    errors += 1
                    continue
            else:
                logger.info("  DRY RUN — reply:\n    %s", reply_text[:200])
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
