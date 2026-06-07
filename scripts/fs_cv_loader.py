#!/usr/bin/env python3
"""
fs_cv_loader.py — Freescout → Odoo CV sync processor with Claude AI scoring.

Polls recursoshumanos@ Freescout mailbox (mailbox_id=4), extracts CV content
from email body + attachments (PDF/DOCX/images), scores each with Claude Haiku,
and creates hr.applicant records in Odoo.

Run as daily cron while the position is open:
    python3 fs_cv_loader.py --live           # normal daily run
    python3 fs_cv_loader.py --dry-run        # preview without writing (default)
    python3 fs_cv_loader.py --live --env production  # requires confirmation

Freescout: REST API only — no direct DB queries (policy).
Idempotent: skips conversations already loaded (by conv_id and by email+job_id).
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import xmlrpc.client
from datetime import datetime, date

import requests

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import docx as python_docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ── Config ────────────────────────────────────────────────────────────────────

FS_CONFIG_PATH   = '/opt/odoo-dev/config/freescout_api.json'
ANTH_CONFIG_PATH = '/opt/odoo-dev/config/anthropic_api.json'
ODOO_CONFIG_PATH = '/opt/odoo-dev/config/production.json'

ACTIVE           = True           # set False to disable cron without removing it
FS_MAILBOX_ID    = 4              # recursoshumanos@ueipab.edu.ve
CV_SINCE_DATE    = '2026-06-06'   # ad published date — floor for all runs
JOB_POSITION_ID  = 8             # Auxiliar de Contabilidad y Administración (testing)

INTERNAL_DOMAINS = {'ueipab.edu.ve'}

EXCLUDE_SUBJECT_PATTERNS = [
    r'asistencia', r'mikrotik', r'hotspot', r'slip/', r'comprobante',
    r'renuncia', r'resumen hr', r'permiso', r'SLIP',
]

CLAUDE_MODEL         = 'claude-haiku-4-5-20251001'
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024   # 8 MB hard cap per file
MAX_PDF_PAGES        = 3                 # pages to extract / send via vision
PDF_TEXT_MIN_CHARS   = 80               # below this → treat as image-based PDF
MAX_ATTACHMENTS      = 3                # max files to process per conversation
SUPPORTED_IMAGE_MIMES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}

STATE_PATH = '/opt/odoo-dev/scripts/fs_cv_processor_state.json'


# ── Freescout API helpers ──────────────────────────────────────────────────────

def fs_headers(api_key):
    return {'X-FreeScout-API-Key': api_key, 'Accept': 'application/json'}


def fs_get_conversations(base_url, api_key, mailbox_id, page=1):
    r = requests.get(
        f"{base_url}/conversations",
        headers=fs_headers(api_key),
        params={'mailboxId': mailbox_id, 'status': 'all', 'perPage': 50, 'page': page},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def fs_get_conversation_detail(base_url, api_key, conv_id):
    r = requests.get(
        f"{base_url}/conversations/{conv_id}",
        headers=fs_headers(api_key),
        params={'embed': 'threads'},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def fs_get_threads(base_url, api_key, conv_id):
    detail = fs_get_conversation_detail(base_url, api_key, conv_id)
    return detail.get('_embedded', {}).get('threads', [])


def extract_body_text(threads):
    """Strip HTML from thread bodies → plain text for Claude."""
    parts = []
    for t in threads:
        body = t.get('body', '') or ''
        text = re.sub(r'<[^>]+>', ' ', body)
        text = re.sub(r'\s+', ' ', text).strip()
        if text and len(text) > 20:
            parts.append(text[:2000])
    return '\n\n---\n\n'.join(parts)[:4000]


def get_thread_attachments(threads):
    """Collect attachment metadata from all threads (_embedded.attachments)."""
    attachments = []
    for t in threads:
        for a in t.get('_embedded', {}).get('attachments', []):
            if a.get('fileUrl'):
                attachments.append(a)
    return attachments


# ── Attachment extraction ──────────────────────────────────────────────────────

def download_file(file_url):
    """Download attachment bytes. Token is embedded in URL — no auth header needed."""
    r = requests.get(file_url, timeout=30, stream=True)
    r.raise_for_status()
    chunks = []
    total = 0
    for chunk in r.iter_content(chunk_size=65536):
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_ATTACHMENT_BYTES:
            break
    return b''.join(chunks)


def extract_pdf_text(pdf_bytes):
    """Try text-layer extraction. Returns (text, is_image_based)."""
    if not HAS_PDFPLUMBER:
        return '', True
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = '\n'.join(
                (p.extract_text() or '') for p in pdf.pages[:MAX_PDF_PAGES]
            ).strip()
        return text, len(text) < PDF_TEXT_MIN_CHARS
    except Exception:
        return '', True


def extract_docx_text(docx_bytes):
    """Extract paragraph text from a DOCX file."""
    if not HAS_DOCX:
        return ''
    try:
        doc = python_docx.Document(io.BytesIO(docx_bytes))
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())[:6000]
    except Exception:
        return ''


def process_attachments(attachments):
    """
    Download and process up to MAX_ATTACHMENTS files.

    Returns:
        text_parts  — list of extracted text strings (one per file)
        vision_blocks — list of Anthropic content blocks (document/image)
        notes       — list of processing notes for ai_eval_notes
    """
    text_parts = []
    vision_blocks = []
    notes = []

    for a in attachments[:MAX_ATTACHMENTS]:
        mime  = a.get('mimeType', '')
        fname = a.get('fileName', 'archivo')
        url   = a.get('fileUrl', '')

        try:
            file_bytes = download_file(url)
        except Exception as e:
            notes.append(f"[{fname}] descarga fallida: {e}")
            continue

        if mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_docx_text(file_bytes)
            if text:
                text_parts.append(f"[CV DOCX — {fname}]\n{text}")
                notes.append(f"[{fname}] DOCX — {len(text)} chars extraídos")
            else:
                notes.append(f"[{fname}] DOCX vacío o ilegible")

        elif mime == 'application/pdf':
            text, is_image_based = extract_pdf_text(file_bytes)
            if not is_image_based:
                text_parts.append(f"[CV PDF — {fname}]\n{text[:4000]}")
                notes.append(f"[{fname}] PDF texto — {len(text)} chars extraídos")
            else:
                # Image-based PDF → Claude document block
                b64 = base64.b64encode(file_bytes).decode()
                vision_blocks.append({
                    'type': 'document',
                    'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': b64},
                })
                notes.append(f"[{fname}] PDF imagen — enviado via vision")

        elif mime in SUPPORTED_IMAGE_MIMES:
            b64 = base64.b64encode(file_bytes).decode()
            vision_blocks.append({
                'type': 'image',
                'source': {'type': 'base64', 'media_type': mime, 'data': b64},
            })
            notes.append(f"[{fname}] imagen — enviado via vision")

        elif fname.lower().endswith('.pub') or 'publisher' in mime:
            notes.append(f"[{fname}] formato Publisher — revisar manualmente en Freescout")

        else:
            notes.append(f"[{fname}] formato no soportado ({mime})")

    return text_parts, vision_blocks, notes


# ── CV filter ──────────────────────────────────────────────────────────────────

def is_cv_conversation(conv, since_date):
    created = conv.get('createdAt', '')[:10]
    if created < since_date:
        return False, 'before_ad_date'

    customer = conv.get('customer') or {}
    sender_email = customer.get('email', '') or ''
    domain = sender_email.split('@')[-1].lower() if '@' in sender_email else ''
    if domain in INTERNAL_DOMAINS:
        return False, 'internal_sender'

    subject = (conv.get('subject', '') or '').lower()
    for pattern in EXCLUDE_SUBJECT_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            return False, f'excluded_subject({pattern})'

    return True, 'ok'


# ── Claude scoring ─────────────────────────────────────────────────────────────

# Prompt is split so attachment blocks can be inserted between prefix and suffix
# in the multimodal case.

SCORE_PROMPT_PREFIX = """You are evaluating a job application CV for:

Role: Auxiliar de Contabilidad y Administración (Enfoque Tecnológico)
Employer: Venezuelan private school (El Tigre, Anzoátegui)
Budget: $250–$300/month total (salary + bonus) — entry/junior level
The ad explicitly promised: (1) a technical exam, (2) AI tools training.
Target profile: TSU or técnico medio in accounting/administration.
Note: Licenciados/Contadores Públicos who apply may expect senior salaries — flag this.

Candidate name: {candidate_name}
Candidate email: {candidate_email}
Email subject: {subject}

Email body text:
{body_text}

{attachment_note}"""

SCORE_PROMPT_SUFFIX = """Score this candidate 0–100 on:
- Education match (30%): TSU/técnico medio in accounting/admin = full. Técnico medio = 80%. Licenciado = 60% (may expect senior salary). Unrelated field = 20%.
- Technical foundation (30%): mentions debe/haber, cuentas por cobrar/pagar, conciliaciones, Excel, SAINT, Odoo, etc.
- Tech/AI openness (20%): mentions tech tools, AI curiosity, digital skills, adaptability.
- Communication quality (20%): email is well-written, organized, professional Spanish.

Return ONLY valid JSON, no markdown, no explanation:
{{
  "score": <int 0-100>,
  "tier": "<A|B|C>",
  "education_summary": "<one line: degree + institution if mentioned>",
  "tech_signals": ["<signal1>", "<signal2>"],
  "red_flags": ["<flag1>"],
  "salary_risk": <true|false>,
  "summary": "<2 sentences max, in Spanish>"
}}

Tier rules: A=score>=70, B=score 45-69, C=score<45."""


def score_cv_with_claude(api_key, body_text, candidate_name, candidate_email,
                          subject, text_parts=None, vision_blocks=None):
    """
    Score a CV with Claude Haiku.
    - text_parts: list of extracted text strings from attachments
    - vision_blocks: list of Anthropic content blocks (document/image) for vision
    """
    text_parts   = text_parts or []
    vision_blocks = vision_blocks or []

    # Combine body text + extracted attachment text
    combined_text = body_text or ''
    if text_parts:
        combined_text += '\n\n' + '\n\n'.join(text_parts)
    combined_text = combined_text[:8000]  # cap for text-only path

    if vision_blocks:
        attachment_note = 'The candidate\'s CV attachment(s) follow below — read carefully before scoring.'
    elif text_parts:
        attachment_note = '(CV text extracted from attachment and included above)'
    else:
        attachment_note = '(No attachment text available — score based on email only)'

    prefix = SCORE_PROMPT_PREFIX.format(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        subject=subject,
        body_text=combined_text or '(sin texto)',
        attachment_note=attachment_note,
    )

    api_headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }

    if vision_blocks:
        # Multimodal message: text prefix → attachment block(s) → scoring suffix
        content = [{'type': 'text', 'text': prefix}]
        content.extend(vision_blocks)
        content.append({'type': 'text', 'text': SCORE_PROMPT_SUFFIX})
        messages = [{'role': 'user', 'content': content}]
    else:
        messages = [{'role': 'user', 'content': prefix + '\n\n' + SCORE_PROMPT_SUFFIX}]

    payload = {
        'model': CLAUDE_MODEL,
        'max_tokens': 600,
        'messages': messages,
    }
    r = requests.post(
        'https://api.anthropic.com/v1/messages',
        headers=api_headers,
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    raw = r.json()['content'][0]['text'].strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


# ── Odoo helpers ───────────────────────────────────────────────────────────────

def odoo_connect(env='testing'):
    cfg = json.load(open(ODOO_CONFIG_PATH))
    if env == 'production':
        c    = cfg['production']
        url  = c['xmlrpc']['url']
        db   = c['xmlrpc']['db']
        user = c['xmlrpc']['user']
        pwd  = c['xmlrpc']['api_key']
    else:
        url  = 'http://dev.ueipab.edu.ve:8019'
        db   = 'testing'
        user = 'gustavo.perdomo@ueipab.edu.ve'
        pwd  = 'odoo8069'

    uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, pwd, {})
    if not uid:
        raise RuntimeError(f"Odoo auth failed for {user} on {db}")
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return db, uid, pwd, models


def odoo_already_loaded_by_conv(db, uid, pwd, models, conv_id):
    ids = models.execute_kw(db, uid, pwd, 'hr.applicant', 'search',
        [[['ueipab_freescout_conv_id', '=', conv_id]]])
    return bool(ids)


def odoo_already_loaded_by_email(db, uid, pwd, models, email, job_id):
    """Dedup: same email already applied to same job position."""
    if not email:
        return False
    ids = models.execute_kw(db, uid, pwd, 'hr.applicant', 'search',
        [[['email_from', '=', email], ['job_id', '=', job_id]]])
    return bool(ids)


def odoo_create_applicant(db, uid, pwd, models, data, dry_run=True):
    if dry_run:
        print(f"    [DRY-RUN] Would create hr.applicant: {data['partner_name']} "
              f"— score={data.get('ueipab_cv_score')}")
        return None
    rec_id = models.execute_kw(db, uid, pwd, 'hr.applicant', 'create', [data])
    return rec_id


# ── State file ─────────────────────────────────────────────────────────────────

def write_state(results, tier_counts, dry_run):
    state = {
        'last_run': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'dry_run': dry_run,
        'created': results['created'],
        'skipped_dup': results['skipped_dup'],
        'skipped_email_dup': results['skipped_email_dup'],
        'skipped_error': results['skipped_error'],
        'tier_counts': tier_counts,
    }
    try:
        # Merge with existing totals
        if os.path.exists(STATE_PATH):
            prev = json.load(open(STATE_PATH))
            state['total_loaded'] = prev.get('total_loaded', 0) + (results['created'] if not dry_run else 0)
        else:
            state['total_loaded'] = results['created'] if not dry_run else 0
        with open(STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass  # state file is monitoring only — never block the main flow


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if not ACTIVE:
        print("fs_cv_loader: ACTIVE=False — exiting.")
        sys.exit(0)

    parser = argparse.ArgumentParser(description='Freescout → Odoo CV sync processor')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Preview without writing (default)')
    parser.add_argument('--live', action='store_true',
                        help='Actually create records in Odoo')
    parser.add_argument('--env', default='testing', choices=['testing', 'production'],
                        help='Odoo environment (default: testing)')
    parser.add_argument('--limit', type=int, default=200,
                        help='Max conversations to fetch from Freescout')
    args = parser.parse_args()

    dry_run = not args.live
    if args.env == 'production' and not dry_run:
        confirm = input("Writing to PRODUCTION. Type 'yes' to confirm: ")
        if confirm.strip().lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    # Load configs
    fs_cfg   = json.load(open(FS_CONFIG_PATH))
    anth_cfg = json.load(open(ANTH_CONFIG_PATH))
    FS_BASE  = fs_cfg['api_url'].rstrip('/')
    FS_KEY   = fs_cfg['api_key']
    ANTH_KEY = anth_cfg.get('api', {}).get('api_key') or anth_cfg.get('api_key')

    print(f"fs_cv_loader — {'DRY RUN' if dry_run else 'LIVE'} — {args.env} — {date.today()}")
    print(f"  pdfplumber: {'yes' if HAS_PDFPLUMBER else 'NO — pip install pdfplumber'}")
    print(f"  python-docx: {'yes' if HAS_DOCX else 'NO — pip install python-docx'}")

    # Connect to Odoo
    print(f"\nConnecting to Odoo ({args.env})...")
    db, uid, pwd, models = odoo_connect(args.env)
    print(f"  Connected as uid={uid} on db={db}")

    # Fetch conversations from Freescout
    print(f"\nFetching conversations from Freescout mailbox {FS_MAILBOX_ID}...")
    all_convs = []
    page = 1
    while len(all_convs) < args.limit:
        data = fs_get_conversations(FS_BASE, FS_KEY, FS_MAILBOX_ID, page)
        batch = data.get('_embedded', {}).get('conversations', [])
        if not batch:
            break
        all_convs.extend(batch)
        total_pages = data.get('page', {}).get('totalPages', 1)
        if page >= total_pages:
            break
        page += 1
    print(f"  Fetched {len(all_convs)} conversations total")

    # Filter to CV candidates
    cv_convs = []
    for c in all_convs:
        ok, reason = is_cv_conversation(c, CV_SINCE_DATE)
        if ok:
            cv_convs.append(c)
        else:
            print(f"  skip conv {c['id']} ({reason}): {(c.get('subject','') or '')[:50]}")

    print(f"\n→ {len(cv_convs)} CV conversations to process\n")

    results = {'created': 0, 'skipped_dup': 0, 'skipped_email_dup': 0, 'skipped_error': 0}
    tier_counts = {'A': 0, 'B': 0, 'C': 0}

    for conv in cv_convs:
        conv_id  = conv['id']
        customer = conv.get('customer') or {}
        first    = customer.get('firstName', '') or ''
        last     = customer.get('lastName', '') or ''
        name     = f"{first} {last}".strip() or f"Candidato {conv_id}"
        email    = customer.get('email', '') or ''
        subject  = conv.get('subject', '') or ''

        print(f"[{conv_id}] {name} <{email}>")
        print(f"  Subject: {subject[:70]}")

        # Dedup checks (only in live mode — dry-run always processes)
        if not dry_run:
            if odoo_already_loaded_by_conv(db, uid, pwd, models, conv_id):
                print(f"  → conv already in Odoo, skipping")
                results['skipped_dup'] += 1
                continue
            if odoo_already_loaded_by_email(db, uid, pwd, models, email, JOB_POSITION_ID):
                print(f"  → email already applied (different conv), skipping")
                results['skipped_email_dup'] += 1
                continue

        # Fetch threads + extract content
        try:
            threads     = fs_get_threads(FS_BASE, FS_KEY, conv_id)
            body_text   = extract_body_text(threads)
            raw_attachments = get_thread_attachments(threads)
        except Exception as e:
            print(f"  ⚠ Thread fetch failed: {e}")
            threads = []
            body_text = ''
            raw_attachments = []

        # Process attachments
        att_count = len(raw_attachments)
        text_parts, vision_blocks, att_notes = [], [], []
        if raw_attachments:
            print(f"  Attachments: {att_count} file(s)")
            text_parts, vision_blocks, att_notes = process_attachments(raw_attachments)
            for note in att_notes:
                print(f"    {note}")

        # Score with Claude
        try:
            score_data = score_cv_with_claude(
                ANTH_KEY, body_text, name, email, subject,
                text_parts=text_parts,
                vision_blocks=vision_blocks,
            )
        except Exception as e:
            print(f"  ⚠ Claude scoring failed: {e}")
            score_data = {
                'score': 0, 'tier': 'C',
                'education_summary': 'Error en scoring',
                'tech_signals': [], 'red_flags': [str(e)],
                'salary_risk': False,
                'summary': 'Error al procesar CV con IA.',
            }
            results['skipped_error'] += 1

        score       = score_data.get('score', 0)
        tier        = score_data.get('tier', 'C')
        summary     = score_data.get('summary', '')
        salary_risk = score_data.get('salary_risk', False)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

        extraction_method = (
            'vision' if vision_blocks else
            'text-extracted' if text_parts else
            'email-only'
        )

        ai_notes = (
            f"[fs_cv_loader — {date.today()} — {extraction_method}]\n"
            f"Tier: {tier} | Score: {score}/100 | Salary risk: {'SI' if salary_risk else 'No'}\n"
            f"Adjuntos procesados: {att_count} ({', '.join(att_notes) or 'ninguno'})\n"
            f"Educación: {score_data.get('education_summary', '?')}\n"
            f"Señales tech: {', '.join(score_data.get('tech_signals', []))}\n"
            f"Red flags: {', '.join(score_data.get('red_flags', []))}\n"
            f"Resumen: {summary}\n"
            f"Freescout: https://freescout.ueipab.edu.ve/conversation/{conv_id}"
        )

        applicant_data = {
            'name':                      f"CV — {name}",
            'partner_name':              name,
            'email_from':                email,
            'job_id':                    JOB_POSITION_ID,
            'description':               f"CV recibido vía email. Freescout conv #{conv_id}.",
            'ueipab_freescout_conv_id':  conv_id,
            'ueipab_cv_score':           float(score),
            'ueipab_cv_tier':            tier,
            'ueipab_cv_salary_risk':     bool(salary_risk),
            'ueipab_cv_extract_method':  extraction_method,
            'ueipab_confidence_pct':     float(score) * 0.40,
            'ueipab_ai_eval_notes':      ai_notes,
            'ueipab_eval_state':         'pending',
        }

        odoo_create_applicant(db, uid, pwd, models, applicant_data, dry_run=dry_run)
        results['created'] += 1

        tier_label = {'A': '🟢', 'B': '🟡', 'C': '🔴'}.get(tier, '⚪')
        print(f"  {tier_label} Tier {tier} | Score {score}/100 "
              f"| method={extraction_method}"
              f"{'  ⚠ salary risk' if salary_risk else ''}")
        print(f"  {summary}")
        print()

        time.sleep(0.5)

    # Summary
    print("=" * 60)
    print(f"DONE {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"  Created:         {results['created']}")
    print(f"  Dup (conv):      {results['skipped_dup']}")
    print(f"  Dup (email):     {results['skipped_email_dup']}")
    print(f"  Scoring errors:  {results['skipped_error']}")
    print(f"  Tier A 🟢:       {tier_counts.get('A', 0)}")
    print(f"  Tier B 🟡:       {tier_counts.get('B', 0)}")
    print(f"  Tier C 🔴:       {tier_counts.get('C', 0)}")
    if dry_run:
        print("\nRun with --live to write to Odoo.")

    write_state(results, tier_counts, dry_run)


if __name__ == '__main__':
    main()
