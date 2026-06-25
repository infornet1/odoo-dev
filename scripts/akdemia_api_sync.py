#!/usr/bin/env python3
"""
Akdemia API Sync Pipeline

Replaces: customer_matching_daily.py + akdemia_email_sync.py
Source:   Akdemia REST API v1 (no Playwright / XLS required)

Phases:
  1. Fetch all students from Akdemia REST API
  2. Build parent email map from guardian fields
  3. Compare with Odoo unresolved bounce logs
  4. Auto-resolve detected email changes
  5. Write Akdemia2526 Google Sheet tab (130 cols, exact schema match)
  6. Email summary/alert → gustavo.perdomo@ueipab.edu.ve

Safety:
  - DRY_RUN=True by default; pass --live to apply real changes
  - Aborts sheet write if < 200 students fetched (partial-data guard)
  - Reports Odoo sync status to ir.config_parameter (backward-compat keys)

Usage:
    python3 akdemia_api_sync.py               # dry run
    python3 akdemia_api_sync.py --live         # apply changes
    python3 akdemia_api_sync.py --skip-sheets  # skip sheet update
    python3 akdemia_api_sync.py --skip-odoo    # skip bounce log sync
"""

import argparse
import json
import os
import re
import smtplib
import sys
import xmlrpc.client
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

load_dotenv('/var/www/dev/odoo_api_bridge/.env')

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True

AKDEMIA_API_KEY  = os.getenv('AKDEMIA_API_KEY', '')
AKDEMIA_BASE_URL = os.getenv('AKDEMIA_BASE_URL', 'https://api-staging.akdemia.com')
AKDEMIA_PER_PAGE = 200
MIN_STUDENTS     = 200  # abort sheet write if below this

SPREADSHEET_ID   = os.getenv('GSHEET_ID', '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA')
AKDEMIA_TAB      = 'Akdemia2526'
SHEETS_CREDS     = '/var/www/dev/odoo_api_bridge/gsheet_credentials.json'

TARGET_ENV = os.environ.get('TARGET_ENV', 'production')
ODOO_CONFIGS = {
    'testing': {
        'url': 'http://localhost:8019',
        'db': 'testing',
        'user': 'tdv.devs@gmail.com',
        'password': '35baa2abcc6dee920fa75014f0274c8e551871ce',
    },
    'production': {
        'url': os.environ.get('ODOO_URL', 'https://odoo.ueipab.edu.ve'),
        'db': os.environ.get('ODOO_DB', 'DB_UEIPAB'),
        'user': os.environ.get('ODOO_USER', 'tdv.devs@gmail.com'),
        'password': os.environ.get('ODOO_PASSWORD', ''),
    },
}

if TARGET_ENV == 'production' and not ODOO_CONFIGS['production']['password']:
    raise RuntimeError(
        "ODOO_PASSWORD env var required for TARGET_ENV=production. "
        "Run: source /var/www/dev/.odoo_agent_env_prod"
    )

SMTP_SERVER   = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT     = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER     = os.getenv('SMTP_USERNAME', '')
SMTP_PASS     = os.getenv('SMTP_PASSWORD', '')
SMTP_SENDER   = os.getenv('SENDER_EMAIL', '')
ADMIN_EMAIL   = 'gustavo.perdomo@ueipab.edu.ve'

PROTECTED_EMAILS = {'todalacomunidad@ueipab.edu.ve'}

# ============================================================================
# Value translation tables  (API English → sheet Spanish)
# ============================================================================

STUDENT_STATUS = {
    'active': 'Activo', 'retired': 'Retirado',
    'graduated': 'Graduado', 'not_enrolled': 'No inscrito',
}
STUDENT_CONDITION = {
    'regular': 'Regular', 'drag_subjects': 'Arrastra materias',
    'repeating': 'Repitiente',
}
SCHOLARSHIP = {
    'not_given': 'No becado', 'partial': 'Beca parcial', 'full': 'Beca completa',
}
CIVIL_STATUS = {
    'married': 'Casado/a', 'single': 'Soltero/a',
    'divorced': 'Divorciado/a', 'widowed': 'Viudo/a',
}

SHEET_HEADERS = [
    'Grado', 'Sección', 'Nombre', 'Teléfono celular', 'Apellido',
    'Código postal', 'Cédula de identidad', 'Ciudad', '¿Es cédula escolar?',
    'Fecha de nacimiento', 'Municipio', 'Estado de nacimiento', 'Estado',
    'Municipio de nacimiento', 'Parroquia', 'Parroquia de nacimiento', 'País',
    'Nacionalidad', 'Correo electrónico', 'Género', 'Dirección',
    'Grupo sanguíneo', 'Alergias', 'Ciudad de nacimiento', 'Edad',
    'Grupo Familiar', 'Estatus', 'Condición', 'Condición de pago',
    # Guardian 1 (31 fields)
    'Nombre de Representante', 'Teléfono celular de Representante',
    'Profesión de Representante', 'Apellido de Representante',
    'Código postal de Representante', 'Ocupación de Representante',
    'Cédula de identidad de Representante', 'Ciudad de Representante',
    'Nombre de la compañía donde trabaja de Representante',
    'Fecha de nacimiento de Representante', 'Municipio de Representante',
    'Dirección de oficina de Representante', 'Parroquia de Representante',
    'Parroquia de nacimiento de Representante',
    'Estado de nacimiento de Representante', 'Estado de Representante',
    'Teléfono de oficina de Representante', 'Nacionalidad de Representante',
    'País de Representante', 'País de oficina de Representante',
    'Género de Representante', 'Correo electrónico de Representante',
    'Estado de oficina de Representante', 'Grupo sanguíneo de Representante',
    'Ciudad de oficina de Representante', 'Estado civil de Representante',
    'Ingreso mensual de Representante', 'Dirección de Representante',
    'Teléfono de domicilio de Representante', 'Grupo Familiar de Representante',
    'Parentesco de Representante',
    # Guardian 2 (31 fields — same names)
    'Nombre de Representante', 'Teléfono celular de Representante',
    'Profesión de Representante', 'Apellido de Representante',
    'Código postal de Representante', 'Ocupación de Representante',
    'Cédula de identidad de Representante', 'Ciudad de Representante',
    'Nombre de la compañía donde trabaja de Representante',
    'Fecha de nacimiento de Representante', 'Municipio de Representante',
    'Dirección de oficina de Representante', 'Parroquia de Representante',
    'Parroquia de nacimiento de Representante',
    'Estado de nacimiento de Representante', 'Estado de Representante',
    'Teléfono de oficina de Representante', 'Nacionalidad de Representante',
    'País de Representante', 'País de oficina de Representante',
    'Género de Representante', 'Correo electrónico de Representante',
    'Estado de oficina de Representante', 'Grupo sanguíneo de Representante',
    'Ciudad de oficina de Representante', 'Estado civil de Representante',
    'Ingreso mensual de Representante', 'Dirección de Representante',
    'Teléfono de domicilio de Representante', 'Grupo Familiar de Representante',
    'Parentesco de Representante',
    # Guardian 3 (31 fields — same names)
    'Nombre de Representante', 'Teléfono celular de Representante',
    'Profesión de Representante', 'Apellido de Representante',
    'Código postal de Representante', 'Ocupación de Representante',
    'Cédula de identidad de Representante', 'Ciudad de Representante',
    'Nombre de la compañía donde trabaja de Representante',
    'Fecha de nacimiento de Representante', 'Municipio de Representante',
    'Dirección de oficina de Representante', 'Parroquia de Representante',
    'Parroquia de nacimiento de Representante',
    'Estado de nacimiento de Representante', 'Estado de Representante',
    'Teléfono de oficina de Representante', 'Nacionalidad de Representante',
    'País de Representante', 'País de oficina de Representante',
    'Género de Representante', 'Correo electrónico de Representante',
    'Estado de oficina de Representante', 'Grupo sanguíneo de Representante',
    'Ciudad de oficina de Representante', 'Estado civil de Representante',
    'Ingreso mensual de Representante', 'Dirección de Representante',
    'Teléfono de domicilio de Representante', 'Grupo Familiar de Representante',
    'Parentesco de Representante',
    # Authorized representatives (cols 122-129 — not in API, kept empty)
    'Nombre (Representante autorizado)', 'Apellido (Representante autorizado)',
    'Cédula (Representante autorizado)', 'Teléfono (Representante autorizado)',
    'Nombre (Representante autorizado)', 'Apellido (Representante autorizado)',
    'Cédula (Representante autorizado)', 'Teléfono (Representante autorizado)',
]

# ============================================================================
# Utilities
# ============================================================================

def _s(val) -> str:
    """Convert any value to string, replacing None/nan/'nan' with empty string."""
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() == 'nan' else s


def _translate(mapping: dict, val) -> str:
    v = _s(val)
    return mapping.get(v.lower(), mapping.get(v, v))


def normalize_cedula(cedula) -> str:
    if not cedula or str(cedula).lower() == 'nan':
        return ''
    return re.sub(r'[^0-9]', '', str(cedula))


def normalize_email(email) -> str:
    if not email or str(email).lower() == 'nan':
        return ''
    return str(email).strip().lower()


def sep(char='=', n=70):
    print(char * n)


def header(title):
    print()
    sep()
    print(f'  {title}')
    sep()
    print()


# ============================================================================
# Phase 1: Fetch students from Akdemia API
# ============================================================================

def fetch_students() -> list:
    header('Phase 1: Fetch Students from Akdemia REST API')
    if not AKDEMIA_API_KEY:
        raise RuntimeError('AKDEMIA_API_KEY not configured in .env')

    session = requests.Session()
    session.headers['Authorization'] = f'Bearer {AKDEMIA_API_KEY}'

    entries, page = [], 1
    while True:
        resp = session.get(
            f'{AKDEMIA_BASE_URL}/api/ext/v1/students',
            params={'per_page': AKDEMIA_PER_PAGE, 'page': page},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        entries.extend(data['data'])
        meta = data['meta']
        print(f'  Page {meta["page"]}/{meta["total_pages"]} — {len(entries)}/{meta["total"]} students')
        if meta['page'] >= meta['total_pages']:
            break
        page += 1

    print(f'  Total fetched: {len(entries)} students')
    if len(entries) < MIN_STUDENTS:
        raise ValueError(
            f'Only {len(entries)} students returned (minimum {MIN_STUDENTS}). '
            'Partial data detected — aborting to protect sheet.'
        )
    return entries


# ============================================================================
# Phase 2: Build parent email map
# ============================================================================

def build_parent_map(entries: list) -> dict:
    header('Phase 2: Build Parent Email Map')
    parent_map = {}
    for entry in entries:
        for g in entry.get('guardians', []):
            cedula = normalize_cedula(g.get('unique_id', ''))
            if not cedula:
                continue
            email = normalize_email(g.get('email', ''))
            name = f"{_s(g.get('first_name'))} {_s(g.get('last_name'))}".strip()
            phone = _s(g.get('mobile_phone') or g.get('home_phone'))
            if cedula not in parent_map:
                parent_map[cedula] = {'emails': set(), 'name': name, 'phone': phone}
            if email:
                parent_map[cedula]['emails'].add(email)
            if name and not parent_map[cedula]['name']:
                parent_map[cedula]['name'] = name
            if phone and not parent_map[cedula]['phone']:
                parent_map[cedula]['phone'] = phone

    with_email = sum(1 for v in parent_map.values() if v['emails'])
    print(f'  Unique guardians: {len(parent_map)}')
    print(f'  With email: {with_email}')
    return parent_map


# ============================================================================
# Phase 2b: Build guardian->students index + publish to Odoo cache
# (mirrors enrollment.journey._akdemia_index_by_guardian — keep in lock-step)
# ============================================================================

def build_guardian_index(entries: list) -> dict:
    """Mirror enrollment.journey._akdemia_index_by_guardian.

    Returns {normalized_guardian_cedula: [{name, cedula, grade, section}, ...]}.
    Each student is indexed under EVERY guardian's normalized unique_id so that
    parent 2/3 also match. Only the guardian KEY is digit-normalized; the
    student's cedula/grade/section are kept RAW (via _s) to byte-match the
    Odoo-side index. Dedup is by (cedula, name) within each bucket.
    """
    index = {}
    for entry in entries:
        s = entry.get('student') or {}
        student = {
            'name': f"{_s(s.get('first_name'))} {_s(s.get('last_name'))}".strip(),
            'cedula': _s(s.get('unique_id')),
            'grade': _s(s.get('course_name')),
            'section': _s(s.get('batch_name')),
        }
        if not student['name']:
            continue
        for g in entry.get('guardians', []) or []:
            key = normalize_cedula(g.get('unique_id'))
            if not key:
                continue
            bucket = index.setdefault(key, [])
            if not any(x['cedula'] == student['cedula']
                       and x['name'] == student['name'] for x in bucket):
                bucket.append(student)
    return index


def publish_student_cache(index: dict):
    """Publish the guardian->students index to ir.config_parameter
    'akdemia.students_json' on every reachable env so whichever Odoo hosts
    ueipab_enrollment_journey always has a fresh (<=24h) cache for
    _akdemia_student_index(use_cache=True). Skipped under DRY_RUN."""
    header('Phase 2b: Publish Student Cache to Odoo')
    if DRY_RUN:
        print(f'  [DRY_RUN] Would publish akdemia.students_json '
              f'({len(index)} guardians) to: {", ".join(ODOO_CONFIGS)}')
        return
    json_str = json.dumps(index, ensure_ascii=False)
    for env_name, cfg in ODOO_CONFIGS.items():
        if not cfg.get('password'):
            print(f'  Skipping {env_name}: no password configured.')
            continue
        try:
            common = xmlrpc.client.ServerProxy(
                f'{cfg["url"]}/xmlrpc/2/common', allow_none=True)
            uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
            if not uid:
                print(f'  {env_name}: authentication failed - skipped.')
                continue
            models = xmlrpc.client.ServerProxy(
                f'{cfg["url"]}/xmlrpc/2/object', allow_none=True)
            models.execute_kw(cfg['db'], uid, cfg['password'],
                              'ir.config_parameter', 'set_param',
                              ['akdemia.students_json', json_str])
            print(f'  OK {env_name}: akdemia.students_json set '
                  f'({len(index)} guardians, {len(json_str)} bytes)')
        except Exception as e:
            print(f'  WARNING: {env_name} cache publish failed: {e}')


# ============================================================================
# Phases 3-4: Odoo bounce log comparison and resolution
# (Logic unchanged from akdemia_email_sync.py)
# ============================================================================

def connect_odoo():
    cfg = ODOO_CONFIGS[TARGET_ENV]
    print(f'  Connecting to Odoo: {cfg["url"]} (db={cfg["db"]})...')
    try:
        common = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/common', allow_none=True)
        uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
        if not uid:
            print('  ERROR: Odoo authentication failed.')
            return None, None, None
        models = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/object', allow_none=True)
        print(f'  Connected as uid={uid}')
        return uid, models, cfg
    except Exception as e:
        print(f'  ERROR connecting to Odoo: {e}')
        return None, None, None


def _search_read(models, cfg, uid, model, domain, fields):
    return models.execute_kw(cfg['db'], uid, cfg['password'], model, 'search_read',
                             [domain], {'fields': fields})


def _bounce_log_model_exists(models, cfg, uid) -> bool:
    """Return True if the mail.bounce.log custom module is installed on this Odoo instance."""
    try:
        result = models.execute_kw(cfg['db'], uid, cfg['password'],
                                   'ir.model', 'search_count',
                                   [[('model', '=', 'mail.bounce.log')]])
        return result > 0
    except Exception:
        return False


def find_email_changes(models, cfg, uid, parent_map: dict) -> list:
    header('Phase 3: Compare Bounce Logs with Akdemia Data')
    if not _bounce_log_model_exists(models, cfg, uid):
        print('  mail.bounce.log module not installed on this Odoo instance — skipping.')
        print('  (Install the bounce-log custom module on production to enable this phase.)')
        return []
    bounce_logs = _search_read(models, cfg, uid, 'mail.bounce.log',
                               [('state', 'not in', ['resolved']), ('partner_id', '!=', False)],
                               ['id', 'bounced_email', 'partner_id', 'state', 'new_email'])
    if not bounce_logs:
        print('  No unresolved bounce logs found.')
        return []
    print(f'  Unresolved bounce logs: {len(bounce_logs)}')

    partner_ids = list({bl['partner_id'][0] for bl in bounce_logs})
    partners = _search_read(models, cfg, uid, 'res.partner',
                            [('id', 'in', partner_ids)], ['id', 'name', 'vat', 'email'])
    partner_lookup = {p['id']: p for p in partners}

    changes = []
    for bl in bounce_logs:
        partner = partner_lookup.get(bl['partner_id'][0])
        if not partner:
            continue
        vat = normalize_cedula(partner.get('vat'))
        if not vat:
            continue
        akdemia = parent_map.get(vat)
        if not akdemia or not akdemia['emails']:
            continue
        bounced = normalize_email(bl['bounced_email'])
        new_emails = akdemia['emails'] - {bounced}
        if not new_emails:
            continue
        changes.append({
            'bounce_log_id': bl['id'],
            'bounce_log_state': bl['state'],
            'partner_id': bl['partner_id'][0],
            'partner_name': partner.get('name', ''),
            'partner_vat': vat,
            'bounced_email': bounced,
            'akdemia_new_email': sorted(new_emails)[0],
            'akdemia_all_emails': sorted(akdemia['emails']),
        })

    print(f'  Email changes detected: {len(changes)}')
    for ch in changes:
        print(f'    BL#{ch["bounce_log_id"]} {ch["partner_name"]}: '
              f'{ch["bounced_email"]} → {ch["akdemia_new_email"]}')
    return changes


def _remove_bounced(field, bounced):
    if not field:
        return ''
    return ';'.join(e for e in (e.strip() for e in field.split(';')) if e and e.lower() != bounced.lower())


def _append_email(field, new_email):
    current = (field or '').strip()
    if not current:
        return new_email.strip()
    parts = [e.strip() for e in current.split(';') if e.strip()]
    if new_email.strip().lower() not in [e.lower() for e in parts]:
        parts.append(new_email.strip())
    return ';'.join(parts)


def _sync_mailing_contacts(models, cfg, uid, bounced_email, new_email):
    if not bounced_email or bounced_email in PROTECTED_EMAILS:
        return 0
    prefix = '[DRY_RUN] ' if DRY_RUN else ''
    try:
        mc_ids = models.execute_kw(cfg['db'], uid, cfg['password'],
                                   'mailing.contact', 'search',
                                   [[('email', 'ilike', bounced_email)]])
        if not mc_ids:
            return 0
        records = models.execute_kw(cfg['db'], uid, cfg['password'],
                                    'mailing.contact', 'read',
                                    [mc_ids], {'fields': ['id', 'name', 'email']})
        updated = 0
        for mc in records:
            if (mc.get('email') or '').strip().lower() in PROTECTED_EMAILS:
                continue
            mc_emails = [e.strip().lower() for e in (mc.get('email') or '').split(';') if e.strip()]
            if bounced_email not in mc_emails:
                continue
            new_field = _append_email(_remove_bounced(mc['email'], bounced_email), new_email)
            print(f'  {prefix}mailing.contact #{mc["id"]}: "{mc["email"]}" → "{new_field}"')
            if not DRY_RUN:
                models.execute_kw(cfg['db'], uid, cfg['password'],
                                  'mailing.contact', 'write', [[mc['id']], {'email': new_field}])
            updated += 1
        return updated
    except Exception as e:
        print(f'  WARNING: mailing contact sync error: {e}')
        return 0


def apply_changes(models, cfg, uid, changes: list):
    header('Phase 4: Auto-Resolve Detected Changes')
    if not changes:
        print('  No changes to apply.')
        return {'resolved_bls': 0, 'resolved_convs': 0, 'updated_mcs': 0, 'errors': 0}

    results = {'resolved_bls': 0, 'resolved_convs': 0, 'updated_mcs': 0, 'errors': 0}
    prefix = '[DRY_RUN] ' if DRY_RUN else ''

    for ch in changes:
        bl_id = ch['bounce_log_id']
        new_email = ch['akdemia_new_email']
        bounced = ch['bounced_email']
        print(f'--- BL#{bl_id} ({ch["partner_name"]}) [state={ch["bounce_log_state"]}] ---')

        if ch['bounce_log_state'] == 'akdemia_pending':
            print(f'  {prefix}Confirming Akdemia update (new email "{new_email}")')
            if not DRY_RUN:
                try:
                    models.execute_kw(cfg['db'], uid, cfg['password'],
                                      'mail.bounce.log', 'action_confirm_akdemia', [[bl_id]])
                    print(f'  BL#{bl_id} confirmed → resolved')
                except Exception as e:
                    print(f'  ERROR: {e}')
                    results['errors'] += 1
                    continue
            results['resolved_bls'] += 1
            continue

        print(f'  {prefix}Setting new_email="{new_email}" on BL#{bl_id}')
        if not DRY_RUN:
            try:
                models.execute_kw(cfg['db'], uid, cfg['password'],
                                  'mail.bounce.log', 'write', [[bl_id], {'new_email': new_email}])
                models.execute_kw(cfg['db'], uid, cfg['password'],
                                  'mail.bounce.log', 'action_apply_new_email', [[bl_id]])
                results['resolved_bls'] += 1
            except Exception as e:
                print(f'  ERROR: {e}')
                results['errors'] += 1
                results['updated_mcs'] += _sync_mailing_contacts(models, cfg, uid, bounced, new_email)
                continue
        else:
            results['resolved_bls'] += 1

        results['updated_mcs'] += _sync_mailing_contacts(models, cfg, uid, bounced, new_email)

        try:
            convs = _search_read(models, cfg, uid, 'ai.agent.conversation',
                                 [('source_model', '=', 'mail.bounce.log'),
                                  ('source_id', '=', bl_id),
                                  ('state', 'not in', ['resolved', 'failed'])], ['id', 'state'])
            if convs:
                conv_id = convs[0]['id']
                print(f'  {prefix}Resolving AI conversation #{conv_id}')
                if not DRY_RUN:
                    models.execute_kw(cfg['db'], uid, cfg['password'],
                                      'ai.agent.conversation', 'action_resolve', [[conv_id]],
                                      {'summary': f'Email actualizado en Akdemia: {new_email}',
                                       'resolution_data': {'action': 'new_email', 'email': new_email}})
                results['resolved_convs'] += 1
        except Exception as e:
            print(f'  WARNING: AI conversation check: {e}')
        print()

    print(f'  Results: {results["resolved_bls"]} BLs resolved, '
          f'{results["resolved_convs"]} convs, {results["updated_mcs"]} mailing contacts, '
          f'{results["errors"]} errors')
    return results


# ============================================================================
# Phase 5: Build 130-column rows and write Akdemia2526
# ============================================================================

def _guardian_segment(g: dict) -> list:
    """Build 31-cell list for one guardian (or empty strings if guardian absent)."""
    if not g:
        return [''] * 31
    cs = _translate(CIVIL_STATUS, (g.get('civil_status') or '').lower())
    return [
        _s(g.get('first_name')),
        _s(g.get('mobile_phone')),
        _s(g.get('profession')),
        _s(g.get('last_name')),
        _s(g.get('home_zip_code')),
        _s(g.get('occupation')),
        _s(g.get('unique_id')),
        _s(g.get('home_city')),
        _s(g.get('company_name')),
        _s(g.get('birth_date')),
        _s(g.get('home_municipality')),
        _s(g.get('office_address')),
        _s(g.get('home_parish')),
        _s(g.get('birth_parish')),
        _s(g.get('birth_state')),
        _s(g.get('home_state')),
        _s(g.get('office_phone')),
        _s(g.get('nationality')),
        _s(g.get('home_country')),
        _s(g.get('office_country')),
        _s(g.get('gender')),
        _s(g.get('email')),
        _s(g.get('office_state')),
        _s(g.get('blood_group')),
        _s(g.get('office_city')),
        cs,
        _s(g.get('income')),
        _s(g.get('home_address')),
        _s(g.get('home_phone')),
        _s(g.get('family_group')),
        _s(g.get('relationship')),
    ]


def build_sheet_rows(entries: list) -> list:
    """Convert API entries into the 130-column sheet rows (data rows only, no headers)."""
    rows = []
    for entry in entries:
        s = entry['student']
        guardians = entry.get('guardians', [])

        age = s.get('age')
        age_val = int(age) if age is not None else ''

        student_seg = [
            _s(s.get('course_name')),
            _s(s.get('batch_name')),
            _s(s.get('first_name')),
            _s(s.get('mobile_phone')),
            _s(s.get('last_name')),
            _s(s.get('home_zip_code')),
            _s(s.get('unique_id')),
            _s(s.get('home_city')),
            'Sí' if s.get('is_academic_id') else 'No',
            _s(s.get('birth_date')),
            _s(s.get('home_municipality')),
            _s(s.get('birth_state')),
            _s(s.get('home_state')),
            _s(s.get('birth_municipality')),
            _s(s.get('home_parish')),
            _s(s.get('birth_parish')),
            _s(s.get('home_country')),
            _s(s.get('nationality')),
            _s(s.get('email')),
            _s(s.get('gender')),
            _s(s.get('home_address')),
            _s(s.get('blood_group')),
            _s(s.get('alergies')),
            _s(s.get('birth_city')),
            age_val,
            _s(s.get('family_group')),
            _translate(STUDENT_STATUS, s.get('status')),
            _translate(STUDENT_CONDITION, s.get('condition')),
            _translate(SCHOLARSHIP, s.get('scholarship')),
        ]

        row = (
            student_seg
            + _guardian_segment(guardians[0] if len(guardians) > 0 else None)
            + _guardian_segment(guardians[1] if len(guardians) > 1 else None)
            + _guardian_segment(guardians[2] if len(guardians) > 2 else None)
            + [''] * 8  # cols 122-129: authorized representatives (not in API)
        )
        assert len(row) == 130, f'Row length {len(row)} != 130'
        rows.append(row)
    return rows


def update_google_sheet(entries: list):
    header('Phase 5: Update Akdemia2526 Google Sheet')
    prefix = '[DRY_RUN] ' if DRY_RUN else ''

    data_rows = build_sheet_rows(entries)
    academic_year = _detect_academic_year()

    all_rows = [
        ['Colegio', 'UNIDAD EDUCATIVA INSTITUTO ANDRES BELLO'] + [''] * 128,
        ['Año escolar', academic_year] + [''] * 128,
        SHEET_HEADERS,
    ] + data_rows

    total_rows = len(all_rows)
    print(f'  Academic year: {academic_year}')
    print(f'  Data rows: {len(data_rows)} students')
    print(f'  Total rows to write: {total_rows} (2 metadata + 1 header + {len(data_rows)} data)')

    if DRY_RUN:
        print(f'  {prefix}Would clear "{AKDEMIA_TAB}" and write {total_rows} rows × 130 cols')
        return

    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(SHEETS_CREDS, scopes=scopes)
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(AKDEMIA_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=AKDEMIA_TAB, rows=str(total_rows + 10), cols='130')

    ws.clear()
    if ws.row_count < total_rows:
        ws.resize(rows=total_rows + 5)

    chunk_size = 100
    for start in range(0, total_rows, chunk_size):
        end = min(start + chunk_size, total_rows)
        ws.update(all_rows[start:end], f'A{start + 1}', value_input_option='USER_ENTERED')
        if end < total_rows:
            print(f'  Written rows {start + 1}–{end} of {total_rows}...')

    print(f'  ✅ Akdemia2526 updated: {total_rows} rows written')


def _detect_academic_year() -> str:
    m = datetime.now().month
    y = datetime.now().year
    return f'{y}-{y + 1}' if m >= 9 else f'{y - 1}-{y}'


# ============================================================================
# Phase 6: Email report
# ============================================================================

def send_email(subject: str, body: str, is_error: bool = False):
    if not SMTP_USER or not SMTP_PASS:
        print(f'  WARNING: SMTP not configured, skipping email ({subject})')
        return
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_SENDER or SMTP_USER
        msg['To'] = ADMIN_EMAIL
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(msg['From'], [ADMIN_EMAIL], msg.as_string())
        print(f'  Email sent → {ADMIN_EMAIL}: {subject}')
    except Exception as e:
        print(f'  WARNING: Failed to send email: {e}')


def send_success_report(students_written: int, changes_applied: int, elapsed_sec: float):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    mode = 'DRY RUN' if DRY_RUN else 'LIVE'
    subject = f'✅ Akdemia API Sync — {students_written} students | {now}'
    body = f"""
    <h3>Akdemia API Sync — SUCCESS ({mode})</h3>
    <table>
      <tr><td><b>Date</b></td><td>{now}</td></tr>
      <tr><td><b>Students written</b></td><td>{students_written}</td></tr>
      <tr><td><b>Bounce log changes</b></td><td>{changes_applied}</td></tr>
      <tr><td><b>Duration</b></td><td>{elapsed_sec:.1f}s</td></tr>
      <tr><td><b>Sheet</b></td><td>Akdemia2526</td></tr>
    </table>
    """
    send_email(subject, body)


def send_error_alert(error_msg: str, phase: str):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    subject = f'🚨 Akdemia API Sync FAILED — {phase} | {now}'
    body = f"""
    <h3>Akdemia API Sync — FAILURE</h3>
    <p><b>Phase:</b> {phase}</p>
    <p><b>Error:</b> <pre>{error_msg}</pre></p>
    <p><b>Time:</b> {now}</p>
    <p>The Akdemia2526 sheet was <b>NOT updated</b>. Please investigate.</p>
    """
    send_email(subject, body, is_error=True)


# ============================================================================
# Odoo status reporting (backward-compat keys)
# ============================================================================

def report_odoo_status(status: str, student_count: int = 0):
    try:
        cfg = ODOO_CONFIGS[TARGET_ENV]
        common = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/common', allow_none=True)
        uid = common.authenticate(cfg['db'], cfg['user'], cfg['password'], {})
        if not uid:
            return
        models = xmlrpc.client.ServerProxy(f'{cfg["url"]}/xmlrpc/2/object', allow_none=True)
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        params = {
            'ai_agent.akdemia_last_scrape_date': now_str,
            'ai_agent.akdemia_last_scrape_status': status,
            'ai_agent.akdemia_last_scrape_file': f'API:{student_count}_students',
        }
        for key, value in params.items():
            models.execute_kw(cfg['db'], uid, cfg['password'],
                              'ir.config_parameter', 'set_param', [key, value])
        print(f'  Odoo status reported: {status}')
    except Exception as e:
        print(f'  WARNING: Could not report status to Odoo: {e}')


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Akdemia API Sync Pipeline')
    parser.add_argument('--live', action='store_true', help='Apply real changes (disable DRY_RUN)')
    parser.add_argument('--skip-sheets', action='store_true', help='Skip Phase 5 (sheet update)')
    parser.add_argument('--skip-odoo', action='store_true', help='Skip Phases 3-4 (bounce log sync)')
    args = parser.parse_args()

    global DRY_RUN
    if args.live:
        DRY_RUN = False

    start = datetime.now()
    sep()
    print('  AKDEMIA API SYNC PIPELINE')
    sep()
    print(f'  Date:         {start.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Mode:         {"LIVE" if not DRY_RUN else "DRY RUN"}')
    print(f'  Target Odoo:  {TARGET_ENV}')
    print(f'  Skip sheets:  {args.skip_sheets}')
    print(f'  Skip Odoo:    {args.skip_odoo}')
    print()

    entries = []
    changes_count = 0

    # Phase 1: Fetch
    try:
        entries = fetch_students()
        report_odoo_status('ok', len(entries))
    except Exception as e:
        print(f'ERROR in Phase 1: {e}')
        send_error_alert(str(e), 'Phase 1: Fetch students from API')
        report_odoo_status('error')
        sys.exit(1)

    # Phase 2: Parent map
    parent_map = build_parent_map(entries)

    # Phase 2b: Guardian->students index cache for ueipab_enrollment_journey
    try:
        student_index = build_guardian_index(entries)
        publish_student_cache(student_index)
    except Exception as e:
        print(f'WARNING: Student cache publish error: {e}')

    # Phases 3-4: Odoo bounce log sync
    if not args.skip_odoo:
        uid, models, cfg = connect_odoo()
        if uid and models:
            try:
                changes = find_email_changes(models, cfg, uid, parent_map)
                results = apply_changes(models, cfg, uid, changes)
                changes_count = results.get('resolved_bls', 0)
            except Exception as e:
                print(f'WARNING: Odoo sync error: {e}')
        else:
            print('WARNING: Skipping Odoo phases — connection failed.')
    else:
        print('\n  Skipping Odoo phases (--skip-odoo).')

    # Phase 5: Sheet update
    if not args.skip_sheets:
        try:
            update_google_sheet(entries)
        except Exception as e:
            print(f'ERROR in Phase 5: {e}')
            send_error_alert(str(e), 'Phase 5: Write Akdemia2526 sheet')
            sys.exit(1)
    else:
        print('\n  Skipping sheet update (--skip-sheets).')

    # Phase 6: Success report
    elapsed = (datetime.now() - start).total_seconds()
    header('COMPLETE')
    if DRY_RUN:
        print('  DRY RUN — no changes applied. Use --live to apply.')
    else:
        print(f'  All changes applied in {elapsed:.1f}s.')
        send_success_report(len(entries), changes_count, elapsed)
    print()


if __name__ == '__main__':
    main()
