#!/usr/bin/env python3
"""
Freescout pagos@ Payment Receipt Processor

Monitors unassigned conversations in the pagos@ mailbox (mailbox_id=2).
For each one it:
  1. Identifies the customer via their email → res.partner lookup in Odoo
  2. Extracts payment data using three strategies (in order, cheapest first):
       a. Regex  — bank auto-notification emails (Bs. / Monto: / Fecha: patterns)
       b. GPT text  — unstructured customer email body (gpt-4o-mini, ~$0.0001)
       c. GPT Vision — receipt image from attachment/inline img (~$0.001)
  3. Runs the standard payment pipeline:
       dedup → resolve journal → match invoice → create draft account.payment
  4. Posts an internal Freescout note with the Odoo deep link
  5. Prefixes the conversation subject with [GLENDA] so subsequent runs skip it

Conversations already assigned to a staff member are never touched.
Internal-sender conversations (ueipab.edu.ve domain, finanzas@) are skipped.

Usage:
    python3 scripts/pagos_receipt_processor.py           # dry run (default)
    python3 scripts/pagos_receipt_processor.py --live    # apply changes

Cron: /etc/cron.d/pagos_receipt_processor — every 15 min

Author: Claude Code Assistant
Date: 2026-05-13
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import xmlrpc.client
from datetime import datetime, timedelta

import requests

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True
TARGET_ENV = os.environ.get('TARGET_ENV', 'testing')

ODOO_CONFIGS = {
    'testing': {
        'url':      'http://localhost:8019',
        'db':       'testing',
        'user':     'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url':      os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve'),
        'db':       os.environ.get('ODOO_DB', 'DB_UEIPAB'),
        'user':     os.environ.get('ODOO_USER', 'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}

PAGOS_MAILBOX_ID = 2
PROCESSED_SUBJECT_PREFIX = '[GLENDA]'
INTERNAL_DOMAIN = 'ueipab.edu.ve'
# Hard-blocked system/automation accounts — never touch these regardless of content
SYSTEM_EMAILS = {
    'finanzas@ueipab.edu.ve', 'recursoshumanos@ueipab.edu.ve',
    'compras@ueipab.edu.ve', 'pagos@ueipab.edu.ve',
    'mailer-daemon@googlemail.com',
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'pagos_processor_state.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ============================================================================
# State
# ============================================================================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'processed_ids': [], 'last_run': None}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

# ============================================================================
# Freescout API
# ============================================================================

_FS_CFG = None

def _fs_cfg():
    global _FS_CFG
    if _FS_CFG:
        return _FS_CFG
    candidates = [
        os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'freescout_api.json')),
        '/home/vision/ueipab17/config/freescout_api.json',
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p) as f:
                _FS_CFG = json.load(f)
            return _FS_CFG
    raise RuntimeError("freescout_api.json not found")

def _fs_headers():
    return {'X-FreeScout-API-Key': _fs_cfg()['api_key']}

def _fs_api_url():
    return _fs_cfg()['api_url']


def fs_get_unassigned_conversations():
    """Return all active unassigned conversations in pagos@ mailbox."""
    convs = []
    page = 1
    while True:
        r = requests.get(
            f"{_fs_api_url()}/conversations",
            headers=_fs_headers(),
            params={'mailboxId': PAGOS_MAILBOX_ID, 'status': 'active', 'page': page},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        page_convs = data.get('_embedded', {}).get('conversations', [])
        if not page_convs:
            break
        for c in page_convs:
            if c.get('assignee') is None and c.get('state') == 'published':
                convs.append(c)
        # Stop if we got fewer than a full page (no more pages)
        if len(page_convs) < 25:
            break
        page += 1
    return convs


def fs_get_conversation(conv_id):
    """Return full conversation dict with embedded threads."""
    r = requests.get(
        f"{_fs_api_url()}/conversations/{conv_id}",
        headers=_fs_headers(), timeout=15,
    )
    r.raise_for_status()
    return r.json()


def fs_post_note(conv_id, html_body, admin_user_id=1):
    """Post an internal note on a Freescout conversation."""
    if DRY_RUN:
        logger.info("  [DRY] Would post note to FS#%d", conv_id)
        return
    r = requests.post(
        f"{_fs_api_url()}/conversations/{conv_id}/threads",
        headers=_fs_headers(),
        json={'type': 'note', 'text': html_body, 'user': admin_user_id},
        timeout=15,
    )
    r.raise_for_status()


def fs_update_subject(conv_id, new_subject, admin_user_id=1):
    """Prefix conversation subject with [GLENDA] to mark as processed."""
    if DRY_RUN:
        logger.info("  [DRY] Would update subject to: %s", new_subject[:60])
        return
    r = requests.put(
        f"{_fs_api_url()}/conversations/{conv_id}",
        headers=_fs_headers(),
        json={'subject': new_subject, 'byUser': admin_user_id},
        timeout=15,
    )
    r.raise_for_status()

# ============================================================================
# Odoo XML-RPC
# ============================================================================

_odoo_conn = None

def odoo():
    global _odoo_conn
    if _odoo_conn:
        return _odoo_conn
    cfg = ODOO_CONFIGS[TARGET_ENV]
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    _odoo_conn = (cfg['db'], uid, cfg['password'], models)
    logger.info("Odoo connected (uid=%d, db=%s)", uid, cfg['db'])
    return _odoo_conn


def odoo_search_read(model, domain, fields, limit=0, order=''):
    db, uid, pwd, m = odoo()
    kwargs = {'fields': fields}
    if limit:
        kwargs['limit'] = limit
    if order:
        kwargs['order'] = order
    return m.execute_kw(db, uid, pwd, model, 'search_read', [domain], kwargs)


def odoo_get_param(key, default=''):
    rows = odoo_search_read('ir.config_parameter', [('key', '=', key)], ['value'], limit=1)
    return rows[0]['value'] if rows else default


_wa_cfg_cache = None

def _wa_cfg():
    global _wa_cfg_cache
    if _wa_cfg_cache:
        return _wa_cfg_cache
    candidates = [
        os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'whatsapp_massiva.json')),
        '/home/vision/ueipab17/config/whatsapp_massiva.json',
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p) as f:
                _wa_cfg_cache = json.load(f)
                return _wa_cfg_cache
    return None


def notify_ceo_wa(msg):
    """Send a WA monitoring alert to CEO. No-ops if param unset, dry_run, or WA config missing."""
    if DRY_RUN:
        logger.info("[CEO_NOTIFY dry_run] %s", msg[:120])
        return
    ceo_phone = odoo_get_param('wa_monitor.ceo_phone')
    if not ceo_phone:
        return
    wa = _wa_cfg()
    if not wa:
        return
    try:
        resp = requests.post(
            wa['base_url'].rstrip('/') + '/send/whatsapp',
            data={'secret': wa['secret'], 'account': wa['account_id'],
                  'recipient': ceo_phone, 'type': 'text', 'message': msg},
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("CEO WA notify failed: %s", exc)


def odoo_find_partner_by_email(email):
    """Find res.partner by email (exact match, customer only)."""
    if not email:
        return None
    rows = odoo_search_read('res.partner',
        [('email', '=ilike', email.strip().lower()), ('customer_rank', '>', 0)],
        ['id', 'name', 'email', 'vat', 'child_ids'], limit=1)
    return rows[0] if rows else None


def odoo_get_bcv_rate():
    raw = odoo_get_param('ai_agent.bcv_rate_context')
    if not raw:
        return 0.0
    try:
        return float(json.loads(raw).get('current', {}).get('rate', 0.0))
    except Exception:
        return 0.0


def odoo_resolve_journal(banco, moneda):
    """Map bank + moneda → journal_id via config param."""
    fallback_veb, fallback_usd = 162, 158
    if not banco:
        return fallback_usd if (moneda or '').upper() == 'USD' else fallback_veb
    raw = odoo_get_param('ai_agent.payment_journal_map')
    if not raw:
        return fallback_veb
    try:
        config = json.loads(raw)
    except Exception:
        return fallback_veb
    banco_lower = banco.lower()
    moneda_key = (moneda or 'VES').upper()
    for keyword, cmap in config.get('keywords', {}).items():
        if keyword in banco_lower:
            jid = cmap.get(moneda_key) or cmap.get('VES')
            if jid:
                return jid
    return config.get('fallback_usd', fallback_usd) if moneda_key == 'USD' \
        else config.get('fallback_veb', fallback_veb)


def odoo_match_invoice(partner_id, child_ids, monto, moneda, bcv_rate):
    """Find best matching outstanding invoice. Returns dict or None."""
    if not monto or float(monto) <= 0:
        return None
    monto_usd = float(monto) / bcv_rate if (moneda or '').upper() in ('VES', 'VEB') and bcv_rate > 0 \
        else float(monto)

    partner_ids = [partner_id] + (child_ids or [])
    invoices = odoo_search_read('account.move', [
        ('partner_id', 'in', partner_ids),
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('payment_state', 'in', ('not_paid', 'partial')),
        ('amount_residual_signed', '>', 0),
    ], ['id', 'name', 'amount_residual_signed', 'payment_state', 'invoice_date'],
       order='invoice_date asc')

    best = None
    for inv in invoices:
        residual = float(inv['amount_residual_signed'])
        if residual <= 0:
            continue
        if abs(monto_usd - residual) / residual <= 0.02:
            return {'id': inv['id'], 'name': inv['name'], 'residual': residual,
                    'match_type': 'exact'}
        if monto_usd < residual and best is None:
            best = {'id': inv['id'], 'name': inv['name'], 'residual': residual,
                    'match_type': 'partial'}
    return best


def odoo_check_duplicate(partner_id, referencia):
    """Return existing payment name if duplicate found (last 4 ref digits, 30-day window)."""
    if not referencia:
        return None
    digits = re.sub(r'\D', '', str(referencia))
    last4 = digits[-4:] if len(digits) >= 4 else digits
    if not last4:
        return None
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    rows = odoo_search_read('account.payment', [
        ('partner_id', '=', partner_id),
        ('ref', 'ilike', last4),
        ('date', '>=', cutoff),
        ('payment_type', '=', 'inbound'),
    ], ['id', 'name'], limit=1)
    return rows[0]['name'] if rows else None


def odoo_create_draft_payment(partner_id, receipt, journal_id, matched_invoice, conv_subject=''):
    """Create a draft account.payment. Returns (payment_id, odoo_url) or (None, None)."""
    db, uid, pwd, m = odoo()
    monto  = receipt.get('monto') or 0.0
    moneda = (receipt.get('moneda') or 'VES').upper()
    ref    = receipt.get('referencia') or ''
    banco  = receipt.get('banco') or ''
    tipo   = receipt.get('tipo_pago') or ''
    fecha  = receipt.get('fecha') or ''

    currency_id = 2 if moneda in ('VES', 'VEB') else 1

    _fecha_parts = (fecha or '').split()
    fecha_str = _fecha_parts[0].strip() if _fecha_parts else ''
    payment_date = datetime.now().strftime('%Y-%m-%d')
    for fmt in ('%Y-%m-%d', '%d/%m/%y', '%d-%m-%y', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            parsed = datetime.strptime(fecha_str, fmt)
            if parsed.year >= 2020:
                payment_date = parsed.strftime('%Y-%m-%d')
                break
        except (ValueError, TypeError):
            continue

    # bank_reference = raw bank ref number; ref (communication) = customer subject
    bank_reference_val = ref[:64] if ref else ''
    communication_val  = (conv_subject or ref or 'Freescout pagos@')[:190]

    # Get inbound payment method line from journal
    journals = odoo_search_read('account.journal',
        [('id', '=', journal_id)], ['inbound_payment_method_line_ids'], limit=1)
    method_line_id = False
    if journals and journals[0].get('inbound_payment_method_line_ids'):
        method_line_id = journals[0]['inbound_payment_method_line_ids'][0]

    vals = {
        'payment_type':   'inbound',
        'partner_type':   'customer',
        'partner_id':     partner_id,
        'amount':         float(monto),
        'currency_id':    currency_id,
        'journal_id':     journal_id,
        'date':           payment_date,
        'effective_date': payment_date,
        'ref':            communication_val,
        'bank_reference': bank_reference_val,
    }
    if method_line_id:
        vals['payment_method_line_id'] = method_line_id

    if DRY_RUN:
        logger.info("  [DRY] Would create+confirm payment: %s %s journal=%d date=%s bank_ref=%s comm=%s",
                    monto, moneda, journal_id, payment_date, bank_reference_val, communication_val[:40])
        return -1, 'https://odoo.ueipab.edu.ve/web#dry-run'

    try:
        payment_id = m.execute_kw(db, uid, pwd, 'account.payment', 'create', [vals])
    except Exception as e:
        logger.error("  Failed to create payment: %s", e)
        return None, None

    try:
        m.execute_kw(db, uid, pwd, 'account.payment', 'action_post', [[payment_id]])
    except xmlrpc.client.Fault as e:
        # action_post() may return a dict with None values that Odoo's XML-RPC
        # server can't serialize (allow_none=False server-side). The post itself
        # usually succeeds — verify state before treating as failure.
        if 'cannot marshal None' in str(e):
            rows = m.execute_kw(db, uid, pwd, 'account.payment', 'read',
                                [[payment_id]], {'fields': ['state']})
            if rows and rows[0].get('state') == 'posted':
                logger.info("  action_post serialization warning (payment IS posted)")
            else:
                logger.error("  action_post failed and payment not posted: %s", e)
                return payment_id, None
        else:
            logger.error("  action_post failed: %s", e)
            return payment_id, None
    except Exception as e:
        logger.error("  action_post failed: %s", e)
        return payment_id, None

    base_url = odoo_get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
    odoo_url = f"{base_url}/web#id={payment_id}&model=account.payment&view_type=form"
    logger.info("  Payment #%d confirmed (journal=%d, %s %s)", payment_id, journal_id, monto, moneda)
    return payment_id, odoo_url

# ============================================================================
# Receipt extraction — 3 strategies
# ============================================================================

# --- Strategy A: Regex for Venezuelan bank auto-notifications ---

# Venezuelan bank code prefixes (first 4 digits of account/phone numbers)
_BANK_CODE_MAP = {
    '0102': 'venezuela',
    '0104': 'venezolano',
    '0105': 'mercantil',
    '0108': 'provincial',
    '0114': 'bancaribe',
    '0115': 'exterior',
    '0116': 'occidental',
    '0128': 'caroni',
    '0134': 'banesco',
    '0137': 'sofitasa',
    '0146': 'bangente',
    '0151': 'bfc',
    '0156': '100%banco',
    '0163': 'tesoro',
    '0166': 'banplus',
    '0172': 'bancamiga',
    '0174': 'banplus',
    '0175': 'bicentenario',
    '0191': 'bnc',
}

_BANK_PATTERNS = [
    # BBVA Provinet / similar structured notifications
    (re.compile(r'Monto[:\s]+(?:Bs\.?\s*)?([\d.,]+)', re.I), 'monto_ves'),
    (re.compile(r'Monto[:\s]+\$\s*([\d.,]+)',           re.I), 'monto_usd'),
    (re.compile(r'Fecha de Operaci[oó]n[:\s]+([\d\-/]+)', re.I), 'fecha'),
    (re.compile(r'Referencia[:\s]+([A-Z0-9\-]+)',        re.I), 'referencia'),
    (re.compile(r'Entidad[:\s]+([A-Za-z\s]+)',           re.I), 'banco_entidad'),
    (re.compile(r'Cuenta Origen[^A-Z]*([A-Z][A-ZÁÉÍÓÚÜÑ\s]+)',re.I), 'titular'),
    (re.compile(r'N[uú]mero de Referencia[:\s]+(\d+)',   re.I), 'referencia2'),
    (re.compile(r'Nro\.?\s*de\s*Referencia[:\s]+(\d+)',  re.I), 'referencia3'),
    (re.compile(r'Operaci[oó]n No\.?\s*:?\s*(\d+)',      re.I), 'referencia4'),
]

def regex_extract(text):
    """Try to extract payment data from a bank auto-notification email body.

    Returns receipt dict if enough fields found, else None.
    """
    monto, moneda, fecha, referencia, banco, titular = None, None, None, None, None, None

    for pattern, field in _BANK_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        val = m.group(1).strip()
        if field == 'monto_ves':
            try:
                monto = float(val.replace('.', '').replace(',', '.'))
                moneda = 'VES'
            except ValueError:
                pass
        elif field == 'monto_usd':
            try:
                monto = float(val.replace(',', ''))
                moneda = 'USD'
            except ValueError:
                pass
        elif field == 'fecha' and not fecha:
            fecha = val
        elif field.startswith('referencia') and not referencia:
            referencia = val
        elif field == 'banco_entidad' and not banco:
            banco = val.strip()
        elif field == 'titular' and not titular:
            titular = val.strip()[:60]

    # Need at least monto to be useful
    if monto is None:
        return None

    # Detect bank from text if not found via pattern
    if not banco:
        text_lower = text.lower()
        for keyword in ('venezuela', 'mercantil', 'banplus', 'bancamiga',
                        'plaza', 'provincial', 'bbva', 'cashea', 'zelle'):
            if keyword in text_lower:
                banco = keyword.capitalize()
                break
    # Detect bank from 4-digit account code (e.g. "0174 **** **** 74138559" → banplus)
    if not banco:
        for code_match in re.finditer(r'\b(0\d{3})\b', text):
            mapped = _BANK_CODE_MAP.get(code_match.group(1))
            if mapped:
                banco = mapped
                break

    # Detect tipo_pago
    tipo = None
    text_lower = text.lower()
    if 'pago m' in text_lower:
        tipo = 'pago_movil'
    elif 'biopago' in text_lower:
        tipo = 'biopago'
    elif 'zelle' in text_lower:
        tipo = 'zelle'
    elif 'cashea' in text_lower:
        tipo = 'cashea'
    elif 'transf' in text_lower:
        tipo = 'transferencia'

    return {
        'is_receipt': True,
        'banco':          banco,
        'monto':          monto,
        'moneda':         moneda or 'VES',
        'referencia':     referencia,
        'fecha':          fecha,
        'titular_origen': titular,
        'cuenta_destino': None,
        'tipo_pago':      tipo,
        '_source':        'regex',
    }


# --- Strategy B: GPT text extraction (unstructured customer emails) ---

def gpt_extract_text(text, api_key):
    """Extract payment data from unstructured email text via GPT-4o-mini."""
    if not text or len(text.strip()) < 20:
        return None

    schema = {
        'type': 'object',
        'properties': {
            'is_receipt':     {'type': 'boolean'},
            'banco':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'monto':          {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
            'moneda':         {'anyOf': [{'type': 'string', 'enum': ['VES', 'USD', 'EUR']}, {'type': 'null'}]},
            'referencia':     {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'fecha':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'titular_origen': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'cuenta_destino': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'tipo_pago':      {'anyOf': [{'type': 'string',
                                          'enum': ['pago_movil', 'transferencia', 'zelle',
                                                   'biopago', 'cashea', 'otro']},
                                         {'type': 'null'}]},
        },
        'required': ['is_receipt', 'banco', 'monto', 'moneda', 'referencia',
                     'fecha', 'titular_origen', 'cuenta_destino', 'tipo_pago'],
        'additionalProperties': False,
    }
    prompt = (
        "Analiza este texto de correo electrónico venezolano. "
        "Si contiene datos de un comprobante de pago (monto, banco, referencia), extráelos. "
        "El campo 'monto' debe ser número decimal. Si el texto NO es un comprobante de pago "
        "responde con is_receipt=false y el resto en null. "
        "Para el campo 'banco': si ves un número de cuenta con prefijo 0174 o 0166 → 'banplus'; "
        "0102 → 'venezuela'; 0105 → 'mercantil'; 0108 o 0177 → 'provincial'; "
        "0172 → 'bancamiga'; 0175 → 'bicentenario'; 0134 → 'banesco'."
    )
    try:
        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'max_tokens': 300,
                'response_format': {
                    'type': 'json_schema',
                    'json_schema': {'name': 'payment_receipt', 'strict': True, 'schema': schema},
                },
                'messages': [{'role': 'user', 'content': f"{prompt}\n\nTexto:\n{text[:2000]}"}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()['choices'][0]['message']['content'])
        if not data.get('is_receipt') or not data.get('monto'):
            return None
        data['_source'] = 'gpt_text'
        return data
    except Exception as e:
        logger.warning("GPT text extraction failed: %s", e)
        return None


# --- Strategy C: GPT Vision (receipt image) ---

def gpt_extract_image(image_url, api_key):
    """Download image from Freescout and extract payment data via GPT-4o-mini Vision."""
    try:
        img_resp = requests.get(image_url, timeout=20)
        img_resp.raise_for_status()
        img_b64 = base64.b64encode(img_resp.content).decode('utf-8')
        mime = img_resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
    except Exception as e:
        logger.warning("Image download failed: %s", e)
        return None

    schema = {
        'type': 'object',
        'properties': {
            'is_receipt':     {'type': 'boolean'},
            'banco':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'monto':          {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
            'moneda':         {'anyOf': [{'type': 'string', 'enum': ['VES', 'USD', 'EUR']}, {'type': 'null'}]},
            'referencia':     {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'fecha':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'titular_origen': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'cuenta_destino': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
            'tipo_pago':      {'anyOf': [{'type': 'string',
                                          'enum': ['pago_movil', 'transferencia', 'zelle',
                                                   'biopago', 'cashea', 'otro']},
                                         {'type': 'null'}]},
        },
        'required': ['is_receipt', 'banco', 'monto', 'moneda', 'referencia',
                     'fecha', 'titular_origen', 'cuenta_destino', 'tipo_pago'],
        'additionalProperties': False,
    }
    prompt = (
        "Analiza esta imagen venezolana. Si es comprobante de pago (transferencia, "
        "pago móvil, Zelle, biopago, Cashea, app bancaria), extrae los datos. "
        "El campo 'monto' debe ser número decimal puro. "
        "Si NO es comprobante, responde con is_receipt=false y el resto en null. "
        "Para el campo 'banco': si ves un número de cuenta con prefijo 0174 o 0166 → 'banplus'; "
        "0102 → 'venezuela'; 0105 → 'mercantil'; 0108 o 0177 → 'provincial'; "
        "0172 → 'bancamiga'; 0175 → 'bicentenario'; 0134 → 'banesco'."
    )
    try:
        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'model': 'gpt-4o-mini',
                'max_tokens': 400,
                'response_format': {
                    'type': 'json_schema',
                    'json_schema': {'name': 'payment_receipt', 'strict': True, 'schema': schema},
                },
                'messages': [{'role': 'user', 'content': [
                    {'type': 'image_url',
                     'image_url': {'url': f'data:{mime};base64,{img_b64}', 'detail': 'low'}},
                    {'type': 'text', 'text': prompt},
                ]}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()['choices'][0]['message']['content'])
        if not data.get('is_receipt') or not data.get('monto'):
            return None
        data['_source'] = 'gpt_vision'
        return data
    except Exception as e:
        logger.warning("GPT Vision extraction failed: %s", e)
        return None


def extract_receipt(thread, api_key):
    """Try all three extraction strategies. Returns receipt dict or None."""
    body_html = thread.get('body', '') or ''
    body_text = re.sub(r'<[^>]+>', ' ', body_html)
    body_text = re.sub(r'&nbsp;', ' ', body_text)
    body_text = re.sub(r'\s+', ' ', body_text).strip()

    # Strategy A: regex on text body (free)
    result = regex_extract(body_text)
    if result:
        logger.info("    Receipt extracted via regex: banco=%s monto=%s %s",
                    result.get('banco'), result.get('monto'), result.get('moneda'))
        return result

    # Collect image URLs: _embedded.attachments[].fileUrl + <img src> in body
    image_urls = []
    for att in thread.get('_embedded', {}).get('attachments', []):
        url = att.get('fileUrl') or att.get('url') or ''
        if url and att.get('mimeType', '').startswith('image/'):
            image_urls.append(url)
    img_tags = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body_html)
    for u in img_tags:
        if u not in image_urls:
            image_urls.append(u)

    if not api_key:
        logger.info("    No OpenAI key — skipping GPT strategies")
        return None

    # Strategy B: GPT text (cheap, ~$0.0001)
    result = gpt_extract_text(body_text, api_key)
    if result:
        logger.info("    Receipt extracted via GPT text: banco=%s monto=%s %s",
                    result.get('banco'), result.get('monto'), result.get('moneda'))
        return result

    # Strategy C: GPT Vision on first image (~$0.001)
    for img_url in image_urls[:1]:
        result = gpt_extract_image(img_url, api_key)
        if result:
            logger.info("    Receipt extracted via GPT Vision: banco=%s monto=%s %s",
                        result.get('banco'), result.get('monto'), result.get('moneda'))
            return result

    return None

# ============================================================================
# Note HTML builders
# ============================================================================

def build_note_no_partner(customer_email, conv_number):
    return (
        f'<p><b>🤖 Glenda — Cliente no identificado</b></p>'
        f'<p>El email <code>{customer_email}</code> no está registrado como cliente en Odoo. '
        f'Por favor verificar y registrar el pago manualmente.</p>'
        f'<p><small>Freescout #{conv_number} · procesado automáticamente</small></p>'
    )

def build_note_no_receipt(source_tried, conv_number):
    return (
        f'<p><b>🤖 Glenda — No se detectó comprobante de pago</b></p>'
        f'<p>Se analizó el mensaje (estrategias: {source_tried}) pero no se encontraron '
        f'datos de pago. Si hay un comprobante adjunto en formato no soportado, '
        f'registrar manualmente.</p>'
        f'<p><small>Freescout #{conv_number}</small></p>'
    )

def build_note_duplicate(partner_name, existing_payment_name, receipt, conv_number):
    banco = receipt.get('banco') or '—'
    monto = receipt.get('monto') or '—'
    moneda = receipt.get('moneda') or '—'
    ref = receipt.get('referencia') or '—'
    return (
        f'<p><b>🤖 Glenda — ⚠️ Referencia duplicada detectada</b></p>'
        f'<p>Cliente: <b>{partner_name}</b></p>'
        f'<p>Banco: {banco} | Monto: {monto} {moneda} | Ref: {ref}</p>'
        f'<p>Ya existe el pago <b>{existing_payment_name}</b> con esta referencia en los últimos 30 días. '
        f'Verificar si es reenvío antes de registrar.</p>'
        f'<p><small>Freescout #{conv_number}</small></p>'
    )

def build_note_success(partner_name, receipt, payment_id, odoo_url,
                        matched_invoice, bcv_rate, conv_number, base_url='https://odoo.ueipab.edu.ve'):
    banco  = receipt.get('banco') or '—'
    monto  = receipt.get('monto')
    moneda = (receipt.get('moneda') or 'VES').upper()
    ref    = receipt.get('referencia') or '—'
    fecha  = receipt.get('fecha') or '—'
    tipo   = receipt.get('tipo_pago') or '—'
    source = receipt.get('_source', '?')

    monto_str = f"{float(monto):,.2f}" if monto else '—'

    bcv_line = ''
    if moneda in ('VES', 'VEB') and monto and bcv_rate > 0:
        monto_usd = float(monto) / bcv_rate
        bcv_line = f'<p>Equiv. USD: <b>${monto_usd:,.2f}</b> (BCV {bcv_rate:,.2f})</p>'

    inv_line = '<p>⚠️ No se encontró factura correspondiente — reconciliar manualmente.</p>'
    if matched_invoice:
        mtype = {'exact': 'Coincidencia exacta', 'partial': 'Pago parcial'}.get(
            matched_invoice['match_type'], matched_invoice['match_type'])
        inv_url = f"{base_url}/web#id={matched_invoice['id']}&model=account.move&view_type=form"
        inv_line = (
            f'<p>Factura: <a href="{inv_url}"><b>{matched_invoice["name"]}</b></a> · '
            f'Pendiente: <b>${matched_invoice["residual"]:,.2f}</b> · {mtype}</p>'
        )

    pay_label = f'Pago #{payment_id} confirmado' if payment_id and payment_id > 0 else 'Pago (dry run)'

    return (
        f'<p><b>🤖 Glenda — {pay_label} automáticamente</b></p>'
        f'<p>Cliente: <b>{partner_name}</b></p>'
        f'<p>Banco: {banco} | Tipo: {tipo} | Monto: <b>{monto_str} {moneda}</b> | '
        f'Ref: {ref} | Fecha: {fecha}</p>'
        f'{bcv_line}'
        f'{inv_line}'
        f'<p><a href="{odoo_url}"><b>→ Abrir y validar en Odoo</b></a></p>'
        f'<p><small>Extracción: {source} · Freescout #{conv_number}</small></p>'
    )

# ============================================================================
# Main conversation processor
# ============================================================================

def is_system_sender(email):
    """Hard-block: automated system accounts that must never be processed."""
    return bool(email) and email.lower() in SYSTEM_EMAILS

def is_internal_domain(email):
    """True if sender is from the school's internal domain (but not a system account)."""
    if not email or '@' not in email:
        return False
    return email.lower().split('@')[-1] == INTERNAL_DOMAIN


def process_conversation(conv, processed_ids, api_key):
    """Process a single unassigned pagos@ conversation. Returns result string."""
    conv_id     = conv['id']
    conv_number = conv['number']
    subject     = conv.get('subject') or ''
    customer    = conv.get('customer') or {}
    customer_email = customer.get('email') or ''

    prefix = '[DRY] ' if DRY_RUN else ''
    logger.info("\n%s--- FS#%d: %s ---", prefix, conv_number, subject[:60])
    logger.info("  customer_email: %s", customer_email)

    # Skip already processed
    if subject.startswith(PROCESSED_SUBJECT_PREFIX):
        logger.info("  Already processed (subject prefix), skipping")
        return 'skipped'

    if conv_id in processed_ids:
        logger.info("  Already in state file, skipping")
        return 'skipped'

    # Hard-block automated system accounts
    if is_system_sender(customer_email):
        logger.info("  System sender — skipping")
        return 'skipped'

    # For internal-domain senders (employees): only proceed if they are also a
    # customer in Odoo (employee who is a parent with a child enrolled).
    # Pre-fetch the partner here to avoid a duplicate lookup later.
    pre_fetched_partner = None
    if is_internal_domain(customer_email):
        pre_fetched_partner = odoo_find_partner_by_email(customer_email)
        if not pre_fetched_partner:
            logger.info("  Internal sender with no customer record — skipping")
            return 'skipped'
        logger.info("  Internal sender IS a customer (%s) — proceeding", pre_fetched_partner['name'])

    # Get full conversation with threads
    try:
        full_conv = fs_get_conversation(conv_id)
    except Exception as e:
        logger.error("  Failed to get conversation: %s", e)
        return 'error'

    threads = full_conv.get('_embedded', {}).get('threads', [])
    customer_threads = [t for t in threads if t.get('type') == 'customer']
    if not customer_threads:
        logger.info("  No customer threads found, skipping")
        return 'skipped'

    # Use most recent customer thread (last in list)
    thread = customer_threads[-1]

    # --- Extract receipt ---
    receipt = extract_receipt(thread, api_key)

    new_subject = f"{PROCESSED_SUBJECT_PREFIX} {subject}"

    if not receipt:
        logger.info("  No receipt data extracted")
        note = build_note_no_receipt('regex, gpt_text, gpt_vision', conv_number)
        try:
            fs_post_note(conv_id, note)
            fs_update_subject(conv_id, new_subject)
        except Exception as e:
            logger.error("  Failed to post note: %s", e)
        return 'no_receipt'

    logger.info("  Receipt: banco=%s monto=%s %s ref=%s source=%s",
                receipt.get('banco'), receipt.get('monto'),
                receipt.get('moneda'), receipt.get('referencia'),
                receipt.get('_source'))

    # --- Partner lookup ---
    partner = pre_fetched_partner or odoo_find_partner_by_email(customer_email)
    if not partner:
        logger.info("  Partner not found for %s", customer_email)
        note = build_note_no_partner(customer_email, conv_number)
        try:
            fs_post_note(conv_id, note)
            fs_update_subject(conv_id, new_subject)
        except Exception as e:
            logger.error("  Failed to post note: %s", e)
        return 'no_partner'

    logger.info("  Partner found: %s (id=%d)", partner['name'], partner['id'])

    # --- Duplicate check ---
    duplicate = odoo_check_duplicate(partner['id'], receipt.get('referencia'))
    if duplicate:
        logger.info("  Duplicate detected: %s", duplicate)
        note = build_note_duplicate(partner['name'], duplicate, receipt, conv_number)
        try:
            fs_post_note(conv_id, note)
            fs_update_subject(conv_id, new_subject)
        except Exception as e:
            logger.error("  Failed to post note: %s", e)
        return 'duplicate'

    # --- Payment pipeline ---
    bcv_rate   = odoo_get_bcv_rate()
    journal_id = odoo_resolve_journal(receipt.get('banco'), receipt.get('moneda'))
    child_ids  = partner.get('child_ids') or []
    matched    = odoo_match_invoice(
        partner['id'], child_ids,
        receipt.get('monto'), receipt.get('moneda'), bcv_rate)
    payment_id, odoo_url = odoo_create_draft_payment(
        partner['id'], receipt, journal_id, matched, conv_subject=subject)

    logger.info("  payment_id=%s journal=%d matched=%s",
                payment_id, journal_id,
                matched['name'] if matched else 'none')

    if payment_id:
        monto_str = f"{receipt.get('monto', '?')} {receipt.get('moneda', '')}"
        banco_str = (receipt.get('banco') or 'banco ?').title()
        ref_str = receipt.get('referencia') or '—'
        notify_ceo_wa(
            f"💰 Pago recibido\n"
            f"👤 {partner['name']}\n"
            f"💵 {monto_str} — {banco_str}\n"
            f"🔢 Ref: {ref_str[-6:] if len(ref_str) > 6 else ref_str}"
        )

    base_url = (odoo_url or '').split('/web#')[0] or 'https://odoo.ueipab.edu.ve'
    note = build_note_success(
        partner['name'], receipt, payment_id, odoo_url,
        matched, bcv_rate, conv_number, base_url)

    try:
        fs_post_note(conv_id, note)
        fs_update_subject(conv_id, new_subject)
    except Exception as e:
        logger.error("  Failed to post note/update subject: %s", e)

    return 'processed'

# ============================================================================
# Main
# ============================================================================

def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description='Freescout pagos@ Receipt Processor')
    parser.add_argument('--live', action='store_true', help='Disable DRY_RUN')
    args = parser.parse_args()
    if args.live:
        DRY_RUN = False

    print('=' * 65)
    print('PAGOS@ RECEIPT PROCESSOR')
    print('=' * 65)
    print(f"  Date:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  DRY_RUN:  {DRY_RUN}")
    print(f"  Target:   {TARGET_ENV}")
    print(f"  Mailbox:  pagos@ (id={PAGOS_MAILBOX_ID})")
    print()

    # Fail fast for production
    if TARGET_ENV == 'production' and not os.environ.get('ODOO_PASSWORD'):
        raise RuntimeError("ODOO_PASSWORD required. Run: source /root/.odoo_agent_env_prod")

    state = load_state()
    processed_ids = set(state.get('processed_ids', []))

    # Get OpenAI API key from Odoo config (optional — regex still works without it)
    try:
        api_key = odoo_get_param('ai_agent.openai_api_key')
    except Exception:
        api_key = ''
    print(f"  OpenAI:   {'configured' if api_key else 'not set — regex only'}")
    print()

    # Fetch unassigned conversations
    print('--- Fetching unassigned pagos@ conversations ---')
    try:
        convs = fs_get_unassigned_conversations()
    except Exception as e:
        logger.error("Failed to fetch conversations: %s", e)
        return

    print(f"  Found {len(convs)} unassigned conversation(s)")
    if not convs:
        print("  Nothing to do.")
        state['last_run'] = datetime.now().isoformat()
        save_state(state)
        return

    # Process each
    stats = {'processed': 0, 'no_receipt': 0, 'no_partner': 0,
             'duplicate': 0, 'skipped': 0, 'error': 0}

    for conv in convs:
        result = process_conversation(conv, processed_ids, api_key)
        stats[result] = stats.get(result, 0) + 1
        if result not in ('skipped', 'error'):
            processed_ids.add(conv['id'])

    # Persist processed IDs (keep last 500 to avoid unbounded growth)
    state['processed_ids'] = list(processed_ids)[-500:]
    state['last_run'] = datetime.now().isoformat()
    save_state(state)

    print()
    print('=' * 65)
    print('SUMMARY')
    print('=' * 65)
    for k, v in stats.items():
        if v:
            print(f"  {k:<12}: {v}")
    print(f"  DRY_RUN  : {DRY_RUN}")
    print()


if __name__ == '__main__':
    main()
