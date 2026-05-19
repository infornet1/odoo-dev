#!/usr/bin/env python3
"""
Consulta Presupuestaria 2026-2027 — Vote Email Sender
======================================================
Source: Google Sheets (Customers tab, col C=ACTIVE, col J=email, col L=phone)
Writes ACK records + mail.mail to production via XML-RPC.
Stores partner_phone on each ACK record for the bounce/WA fallback flow.

Usage:
    python3 scripts/send_budget_vote_email.py            # dry-run
    python3 scripts/send_budget_vote_email.py --test     # CEO preview only
    python3 scripts/send_budget_vote_email.py --live     # full send (178)
    python3 scripts/send_budget_vote_email.py --live --test  # CEO live

Safe to re-run — skips partners who already voted or whose email was already queued.
"""

import argparse
import logging
import sys
import time
import xmlrpc.client
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

SPREADSHEET_ID = '1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA'
CREDS_PATH     = '/opt/odoo-dev/config/google_sheets_credentials.json'
PROD_CFG       = '/opt/odoo-dev/config/production.json'

NOTICE_KEY     = 'budget_consulta_2026_2027'
NOTICE_LABEL   = 'Consulta Presupuestaria 2026-2027'
ODOO_URL       = 'https://odoo.ueipab.edu.ve'
LOGO_URL       = f'{ODOO_URL}/web/image/res.company/1/logo'

CEO_PARTNER_ID = 7
CEO_EMAIL      = 'gustavo.perdomo@ueipab.edu.ve'
CEO_NAME       = 'Gustavo Perdomo'

SEND_DELAY     = 0.2   # seconds between sends


# ── Config ─────────────────────────────────────────────────────────────────────

def _load_prod_cfg():
    cfg = json.load(open(PROD_CFG))['production']['xmlrpc']
    return cfg['url'], cfg['db'], cfg['user'], cfg['api_key']


# ── XML-RPC helpers ────────────────────────────────────────────────────────────

def _connect():
    url, db, user, key = _load_prod_cfg()
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid    = common.authenticate(db, user, key, {})
    if not uid:
        raise RuntimeError('XML-RPC authentication failed')
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    return models, db, uid, key


def call(models, db, uid, key, model, method, args=None, kw=None):
    return models.execute_kw(db, uid, key, model, method,
                             args or [[]], kw or {})


# ── Google Sheets reader ───────────────────────────────────────────────────────

def _load_spreadsheet_recipients():
    """Return list of dicts: {name, email, phone} for all ACTIVE rows."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    svc = build('sheets', 'v4', credentials=creds)
    result = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Customers!A2:M').execute()
    rows = result.get('values', [])
    data = rows[1:]  # skip header row

    recipients = []
    for row in data:
        r = (row + [''] * 13)[:13]
        name   = r[1].strip()
        status = r[2].strip().upper()
        email  = r[9].strip()
        phone  = r[11].strip()
        if not name or status != 'ACTIVE':
            continue
        if not email and not phone:
            log.warning("SKIP (no email, no phone): %s", name)
            continue
        if not email:
            log.info("No email — will route via Glenda WA: %s (phone=%s)", name, phone)
        recipients.append({'name': name, 'email': email, 'phone': phone})

    log.info("Spreadsheet: %d ACTIVE rows loaded", len(recipients))
    return recipients


# ── Partner matching ───────────────────────────────────────────────────────────

def _build_email_index(models, db, uid, key):
    """Return dict of {first_email_lower: partner_id} for all active partners."""
    partners = call(models, db, uid, key,
        'res.partner', 'search_read',
        [[('active', '=', True), ('email', '!=', False)]],
        {'fields': ['id', 'email']})

    index = {}
    for p in partners:
        raw = (p.get('email') or '').replace(';', ',')
        for addr in raw.split(','):
            addr = addr.strip().lower()
            if addr:
                index.setdefault(addr, p['id'])
    return index


def _find_partner(row, email_index, models, db, uid, key):
    """Find res.partner id for a spreadsheet row. Returns None if not found."""
    # Try each address in the email field
    raw = row['email'].replace(';', ',')
    for addr in raw.split(','):
        addr = addr.strip().lower()
        pid = email_index.get(addr)
        if pid:
            return pid

    # Fallback: name search
    results = call(models, db, uid, key,
        'res.partner', 'search_read',
        [[('name', 'ilike', row['name']), ('active', '=', True)]],
        {'fields': ['id', 'name'], 'limit': 1})
    if results:
        log.warning("Email not matched — found by name: %s (id=%d)",
                    results[0]['name'], results[0]['id'])
        return results[0]['id']

    return None


# ── ACK record helpers ─────────────────────────────────────────────────────────

def _get_existing_ack(models, db, uid, key, partner_id):
    recs = call(models, db, uid, key,
        'partner.communication.ack', 'search_read',
        [[('notice_key', '=', NOTICE_KEY), ('partner_id', '=', partner_id)]],
        {'fields': ['id', 'state', 'token', 'partner_email'], 'limit': 1})
    return recs[0] if recs else None


def _create_ack(models, db, uid, key, partner_id, name, email, phone):
    result = call(models, db, uid, key,
        'partner.communication.ack', 'create', [[{
            'notice_key':    NOTICE_KEY,
            'notice_label':  NOTICE_LABEL,
            'partner_id':    partner_id,
            'partner_name':  name,
            'partner_email': email,
            'partner_phone': phone,
        }]])
    return result[0] if isinstance(result, list) else result


def _get_token(models, db, uid, key, ack_id):
    rec = call(models, db, uid, key,
        'partner.communication.ack', 'read', [[ack_id]],
        {'fields': ['token']})
    return rec[0]['token'] if rec else None


def _create_glenda_vote_conv(models, db, uid, key, name, phone, partner_id):
    """Create + start a Glenda WA conversation for a parent with no email.
    The initial_message triggers Claude to respond with the full vote intro
    including the Google Slides link and both options.
    """
    skills = call(models, db, uid, key,
        'ai.agent.skill', 'search_read',
        [[('code', '=', 'general_inquiry')]],
        {'fields': ['id'], 'limit': 1})
    if not skills:
        log.warning("  Could not find general_inquiry skill — skipping Glenda conv")
        return None
    skill_id = skills[0]['id']

    initial_msg = (
        "Hola, no tengo correo electrónico registrado y quisiera ver "
        "la propuesta presupuestaria 2026-2027 y ejercer mi voto."
    )

    conv_vals = {
        'skill_id':        skill_id,
        'phone':           phone,
        'initial_message': initial_msg,
        'state':           'draft',
    }
    if partner_id:
        conv_vals['partner_id'] = partner_id

    result = call(models, db, uid, key,
        'ai.agent.conversation', 'create', [[conv_vals]])
    conv_id = result[0] if isinstance(result, list) else result
    try:
        call(models, db, uid, key,
             'ai.agent.conversation', 'action_start', [[conv_id]])
    except Exception as e:
        if 'cannot marshal None' not in str(e) and 'NoneType' not in str(e):
            raise
    return conv_id


# ── HTML builder ───────────────────────────────────────────────────────────────

def _build_html(partner_name, si_url, no_url, is_test=False):
    test_banner = (
        '<div style="background:#c0392b;color:#fff;text-align:center;padding:10px;'
        'font-size:13px;font-weight:bold;">'
        '⚠️ PRUEBA DE REVISIÓN — Los botones funcionan, pero este voto no cuenta para '
        'el resultado final.</div>'
    ) if is_test else ''

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Consulta Presupuestaria 2026-2027</title>
</head>
<body style="margin:0;padding:0;background:#f0f4fa;font-family:Arial,Helvetica,sans-serif;">
{test_banner}
<table cellpadding="0" cellspacing="0" width="100%" style="background:#f0f4fa;">
<tr><td align="center" style="padding:28px 12px;">
<table cellpadding="0" cellspacing="0" width="600"
       style="max-width:600px;background:#fff;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 28px rgba(0,0,0,0.11);">

  <!-- ══ HEADER ══ -->
  <tr>
    <td style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
               padding:36px 32px 30px;text-align:center;">
      <img src="{LOGO_URL}" alt="Colegio Andrés Bello" width="80" height="80"
           style="border-radius:50%;border:3px solid rgba(255,255,255,0.3);
                  display:block;margin:0 auto 14px;"/>
      <h1 style="margin:0;color:#fff;font-size:21px;font-weight:bold;line-height:1.3;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo;
      </h1>
      <p style="margin:5px 0 16px;color:rgba(255,255,255,0.8);font-size:13px;">
        El Tigre, Estado Anzo&aacute;tegui
      </p>
      <div style="display:inline-block;background:rgba(255,255,255,0.18);
                  border:1px solid rgba(255,255,255,0.4);border-radius:20px;
                  padding:7px 22px;">
        <span style="color:#fff;font-size:14px;font-weight:bold;">
          🗳️ CONSULTA PRESUPUESTARIA 2026-2027
        </span>
      </div>
    </td>
  </tr>

  <!-- ══ GREETING ══ -->
  <tr>
    <td style="padding:28px 32px 6px;">
      <p style="margin:0 0 12px;color:#1a2c5b;font-size:15px;line-height:1.6;">
        Estimado(a) <strong>{partner_name}</strong>,
      </p>
      <p style="margin:0;color:#444;font-size:14px;line-height:1.75;">
        Conforme a lo establecido en las Resoluciones 0009 y 024-2020 del MPPE,
        el <strong>Comit&eacute; de Contralor&iacute;a</strong> analiz&oacute; la propuesta
        econ&oacute;mica 2026-2027 y emiti&oacute; su informe <strong>sin objeciones</strong>.
        A continuaci&oacute;n le presentamos las dos opciones para que ejerza su voto.
      </p>
    </td>
  </tr>

  <!-- ══ CONTEXT BOX ══ -->
  <tr>
    <td style="padding:12px 32px 6px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border-left:4px solid #f0a500;
                    border-radius:0 8px 8px 0;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 10px;font-size:11px;color:#b37a00;font-weight:bold;
                      text-transform:uppercase;letter-spacing:0.5px;">
              Contexto Econ&oacute;mico — Justificaci&oacute;n del Ajuste
            </p>
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td width="33%" style="text-align:center;padding:6px 4px;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">611,86%</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Inflaci&oacute;n 2025</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px 4px;
                    border-left:1px solid #f0d080;border-right:1px solid #f0d080;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">Bs. 487,12</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Tipo de cambio</div>
                </td>
                <td width="33%" style="text-align:center;padding:6px 4px;">
                  <div style="font-size:22px;font-weight:bold;color:#1a2c5b;">8,5%</div>
                  <div style="font-size:11px;color:#666;margin-top:2px;">Crecimiento econ.</div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ SECTION TITLE ══ -->
  <tr>
    <td style="padding:22px 32px 10px;text-align:center;">
      <h2 style="margin:0;color:#1a2c5b;font-size:17px;">
        Seleccione su opci&oacute;n de mensualidad para 2026-2027
      </h2>
      <p style="margin:6px 0 0;color:#777;font-size:13px;">
        Ambas opciones incluyen los mismos servicios educativos STEAM+G
      </p>
    </td>
  </tr>

  <!-- ══ OPTION CARDS ══ -->
  <tr>
    <td style="padding:4px 32px 16px;">
      <table cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <!-- OPCIÓN A -->
          <td width="48%" valign="top"
              style="background:#f0f7ff;border:2px solid #1a2c5b;
                     border-radius:12px;overflow:hidden;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="background:#1a2c5b;padding:11px 14px;text-align:center;">
                  <span style="color:#fff;font-size:13px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;">OPCIÓN A</span>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 14px 6px;text-align:center;">
                  <div style="font-size:12px;color:#666;margin-bottom:3px;">Mensualidad</div>
                  <div style="font-size:36px;font-weight:bold;color:#1a2c5b;line-height:1.1;">
                    $218,88
                  </div>
                  <div style="display:inline-block;background:#e8f5e9;border-radius:12px;
                               padding:3px 10px;margin-top:6px;">
                    <span style="font-size:11px;color:#2e7d32;">+10,89% vs año anterior</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 14px;">
                  <table cellpadding="5" cellspacing="0" width="100%"
                         style="background:#dceefb;border-radius:7px;font-size:12px;">
                    <tr>
                      <td style="color:#555;padding-bottom:0;">💰 Pronto pago (1–10 c/mes)</td>
                    </tr>
                    <tr>
                      <td style="text-align:center;padding-top:2px;">
                        <span style="font-size:20px;font-weight:bold;color:#1a2c5b;">$207,93</span>
                        <span style="font-size:11px;color:#2e7d32;"> — ahorras $10,95</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:4px 14px 6px;font-size:12px;color:#555;text-align:center;">
                  📅 Costo anual est.: <strong style="color:#1a2c5b;">$2.845,45</strong>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 14px 16px;text-align:center;">
                  <a href="{si_url}"
                     style="display:block;background:#1a2c5b;color:#fff;font-size:14px;
                            font-weight:bold;text-decoration:none;padding:13px 8px;
                            border-radius:8px;">
                    ✅ Votar Opci&oacute;n A
                  </a>
                </td>
              </tr>
            </table>
          </td>

          <td width="4%"></td>

          <!-- OPCIÓN B -->
          <td width="48%" valign="top"
              style="background:#f5f0ff;border:2px solid #6c3483;
                     border-radius:12px;overflow:hidden;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td style="background:#6c3483;padding:11px 14px;text-align:center;">
                  <span style="color:#fff;font-size:13px;font-weight:bold;
                               text-transform:uppercase;letter-spacing:1px;">OPCIÓN B</span>
                </td>
              </tr>
              <tr>
                <td style="padding:18px 14px 6px;text-align:center;">
                  <div style="font-size:12px;color:#666;margin-bottom:3px;">Mensualidad</div>
                  <div style="font-size:36px;font-weight:bold;color:#6c3483;line-height:1.1;">
                    $236,58
                  </div>
                  <div style="display:inline-block;background:#f3e5f5;border-radius:12px;
                               padding:3px 10px;margin-top:6px;">
                    <span style="font-size:11px;color:#6c3483;">+19,86% vs año anterior</span>
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:8px 14px;">
                  <table cellpadding="5" cellspacing="0" width="100%"
                         style="background:#ede7f6;border-radius:7px;font-size:12px;">
                    <tr>
                      <td style="color:#555;padding-bottom:0;">💰 Pronto pago (1–10 c/mes)</td>
                    </tr>
                    <tr>
                      <td style="text-align:center;padding-top:2px;">
                        <span style="font-size:20px;font-weight:bold;color:#6c3483;">$224,75</span>
                        <span style="font-size:11px;color:#2e7d32;"> — ahorras $11,82</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:4px 14px 6px;font-size:12px;color:#555;text-align:center;">
                  📅 Costo anual est.: <strong style="color:#6c3483;">$3.075,55</strong>
                </td>
              </tr>
              <tr>
                <td style="padding:10px 14px 16px;text-align:center;">
                  <a href="{no_url}"
                     style="display:block;background:#6c3483;color:#fff;font-size:14px;
                            font-weight:bold;text-decoration:none;padding:13px 8px;
                            border-radius:8px;">
                    ✅ Votar Opci&oacute;n B
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ DESCUENTOS HERMANOS ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;">
        <tr>
          <td style="padding:12px 18px;">
            <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              🏫 Descuentos por familia numerosa (ambas opciones)
            </p>
            <table cellpadding="3" cellspacing="0" width="100%"
                   style="font-size:13px;color:#444;">
              <tr>
                <td>1er hijo/representado</td>
                <td style="text-align:right;">5% descuento</td>
              </tr>
              <tr style="background:#f0f0f0;">
                <td>2do hijo/representado</td>
                <td style="text-align:right;">8% descuento</td>
              </tr>
              <tr>
                <td>3ro y sucesivos</td>
                <td style="text-align:right;">11% descuento</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ COSTOS ANUALES ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fff8e7;border:1px solid #ffc107;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 8px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              📋 Costos &Uacute;nicos Anuales por Alumno
              <span style="font-weight:normal;color:#777;font-size:11px;
                            text-transform:none;"> — pagaderos en inscripci&oacute;n</span>
            </p>
            <table cellpadding="4" cellspacing="0" width="100%"
                   style="font-size:13px;color:#444;">
              <tr>
                <td>Seguro escolar (Seguros Caracas)</td>
                <td style="text-align:right;">$30,58</td>
              </tr>
              <tr style="background:rgba(0,0,0,0.04);">
                <td>Gu&iacute;a de ingl&eacute;s</td>
                <td style="text-align:right;">$25,00</td>
              </tr>
              <tr>
                <td>Olimpiadas recreativas</td>
                <td style="text-align:right;">$10,00</td>
              </tr>
              <tr style="background:rgba(0,0,0,0.04);">
                <td>Enciclopedia digital (todos los niveles)</td>
                <td style="text-align:right;">$36,00</td>
              </tr>
              <tr style="border-top:2px solid #ffc107;">
                <td style="font-weight:bold;color:#1a2c5b;padding-top:7px;">
                  Total por alumno
                </td>
                <td style="text-align:right;font-weight:bold;color:#1a2c5b;padding-top:7px;">
                  $101,58
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ SEGURO ESCOLAR ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td valign="middle" width="36"
                    style="font-size:26px;padding-right:12px;">🛡️</td>
                <td valign="middle">
                  <p style="margin:0 0 3px;font-size:12px;font-weight:bold;color:#1a2c5b;
                            text-transform:uppercase;letter-spacing:0.4px;">
                    Seguro Escolar 2026-2027 &mdash; Seguros Caracas
                  </p>
                  <p style="margin:0;font-size:13px;color:#555;line-height:1.55;">
                    Cobertura para todos los estudiantes incluida en el costo anual
                    ($30,58/alumno). Reclamaciones:
                    <a href="https://wa.me/584149033738" style="color:#1a2c5b;">WA 0414-903.3738</a>
                    &nbsp;/&nbsp;
                    <a href="mailto:amis@grupov.com.ve" style="color:#1a2c5b;">amis@grupov.com.ve</a>.
                    Asesora: Johanna Hern&aacute;ndez.
                  </p>
                </td>
                <td valign="middle" style="padding-left:16px;white-space:nowrap;">
                  <a href="https://drive.google.com/file/d/1KLJ5i9IgE5f0BhN1sGJvmVUCZMX7-mtU/view?usp=drive_link"
                     style="display:inline-block;background:#fff;color:#1a2c5b;font-size:12px;
                            font-weight:bold;text-decoration:none;padding:8px 14px;
                            border:1.5px solid #1a2c5b;border-radius:6px;white-space:nowrap;">
                    Ver p&oacute;liza ↗
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ OFERTA INSCRIPCIÓN ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);
                    border-radius:8px;border:1px solid #a5d6a7;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 4px;font-size:12px;font-weight:bold;color:#1b5e20;
                      text-transform:uppercase;">
              🎉 Oferta de Inscripci&oacute;n Anticipada — hasta el 31 de julio
            </p>
            <p style="margin:0;font-size:14px;color:#1b5e20;">
              Inscripci&oacute;n: <strong>$187,51</strong>
              &nbsp;&middot;&nbsp;
              Mensualidad septiembre: <strong>$197,38</strong>
            </p>
            <p style="margin:4px 0 0;font-size:11px;color:#555;">
              Requisito: solvencia completa 2025-2026. Descuentos por familia numerosa aplicables.
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ CRONOGRAMA ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#f0f4fa;border-radius:8px;border:1px solid #c9d7eb;">
        <tr>
          <td style="padding:14px 18px;">
            <p style="margin:0 0 10px;font-size:12px;font-weight:bold;color:#1a2c5b;
                      text-transform:uppercase;">
              📅 Cronograma del Proceso
            </p>
            <table cellpadding="4" cellspacing="0" width="100%" style="font-size:13px;">
              <tr>
                <td width="22" style="color:#27ae60;">✅</td>
                <td><strong>18 mayo:</strong> Comit&eacute; de Contralor&iacute;a — aprobado sin objeciones</td>
              </tr>
              <tr style="background:rgba(26,44,91,0.04);">
                <td style="color:#27ae60;">✅</td>
                <td><strong>19–20 mayo:</strong> Videollamadas de consulta (3:00 pm y 2:00 pm)</td>
              </tr>
              <tr>
                <td style="color:#f0a500;font-weight:bold;">🗳️</td>
                <td>
                  <strong>21–22 mayo:</strong> Per&iacute;odo de votaci&oacute;n —
                  <strong style="color:#c0392b;">ACTIVO AHORA</strong>
                </td>
              </tr>
              <tr style="background:rgba(26,44,91,0.04);">
                <td style="color:#aaa;">📊</td>
                <td style="color:#888;"><strong>26 mayo:</strong> Publicaci&oacute;n de resultados</td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ POLÍTICA DE MORA ══ -->
  <tr>
    <td style="padding:4px 32px 12px;">
      <table cellpadding="0" cellspacing="0" width="100%"
             style="background:#fafafa;border:1px solid #e0e0e0;border-radius:8px;">
        <tr>
          <td style="padding:14px 18px;">
            <table cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td valign="middle" width="36"
                    style="font-size:26px;padding-right:12px;">⚖️</td>
                <td valign="middle">
                  <p style="margin:0 0 3px;font-size:12px;font-weight:bold;color:#1a2c5b;
                            text-transform:uppercase;letter-spacing:0.4px;">
                    Pol&iacute;tica de Convivencia Financiera
                  </p>
                  <p style="margin:0;font-size:13px;color:#555;line-height:1.55;">
                    El proceso es progresivo y dialogado en 4 etapas — desde un convenio de pago
                    hasta la notificaci&oacute;n a organismos competentes.
                    <strong style="color:#1a2c5b;">El estudiante contin&uacute;a asistiendo
                    regularmente en todo momento.</strong>
                  </p>
                </td>
                <td valign="middle" style="padding-left:16px;white-space:nowrap;">
                  <a href="https://odoo.ueipab.edu.ve/mora-policy/"
                     style="display:inline-block;background:#fff;color:#1a2c5b;font-size:12px;
                            font-weight:bold;text-decoration:none;padding:8px 14px;
                            border:1.5px solid #1a2c5b;border-radius:6px;white-space:nowrap;">
                    Ver pol&iacute;tica ↗
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ BOTONES FINALES ══ -->
  <tr>
    <td style="padding:16px 32px 28px;text-align:center;">
      <p style="margin:0 0 16px;font-size:13px;color:#555;">
        Vote antes del <strong>22 de mayo de 2026</strong>.
        Puede consultar a Glenda sus dudas sobre las opciones.
      </p>
      <table cellpadding="0" cellspacing="0" style="margin:0 auto;">
        <tr>
          <td style="padding:0 6px;">
            <a href="{si_url}"
               style="display:inline-block;background:#1a2c5b;color:#fff;font-weight:bold;
                      font-size:14px;text-decoration:none;padding:13px 22px;border-radius:8px;">
              ✅ Votar Opci&oacute;n A — $218,88
            </a>
          </td>
          <td style="padding:0 6px;">
            <a href="{no_url}"
               style="display:inline-block;background:#6c3483;color:#fff;font-weight:bold;
                      font-size:14px;text-decoration:none;padding:13px 22px;border-radius:8px;">
              ✅ Votar Opci&oacute;n B — $236,58
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ══ FOOTER ══ -->
  <tr>
    <td style="background:#f8f9fa;border-top:1px solid #e0e0e0;
               padding:18px 32px;text-align:center;">
      <p style="margin:0 0 6px;font-size:12px;color:#888;">¿Preguntas? Estamos para ayudarle:</p>
      <p style="margin:0;font-size:13px;color:#555;">
        ✉️ <a href="mailto:votacion@ueipab.edu.ve" style="color:#1a2c5b;">votacion@ueipab.edu.ve</a>
        &nbsp;|&nbsp;
        💬 <a href="https://wa.me/584148321989" style="color:#1a2c5b;">Glenda WhatsApp</a>
        &nbsp;|&nbsp;
        📱 <a href="https://t.me/GlendaUeipabBot" style="color:#1a2c5b;">Glenda Telegram</a>
      </p>
      <p style="margin:8px 0 0;font-size:10px;color:#bbb;">
        Instituto Privado &ldquo;Andr&eacute;s Bello&rdquo; &mdash; El Tigre, Estado Anzo&aacute;tegui
      </p>
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

    mode = 'TEST (CEO only)' if test else ('LIVE — 178 families' if live else 'DRY RUN')
    log.info("=" * 70)
    log.info("CONSULTA PRESUPUESTARIA 2026-2027 — %s", mode)
    log.info("=" * 70)

    # Load recipients from spreadsheet
    if test:
        rows = [{'name': CEO_NAME, 'email': CEO_EMAIL,
                 'phone': '', 'partner_id': CEO_PARTNER_ID}]
    else:
        rows = _load_spreadsheet_recipients()
        # Match each row to a res.partner
        email_index = _build_email_index(models, db, uid, key)
        total_rows = len(rows)
        matched = []
        for row in rows:
            pid = _find_partner(row, email_index, models, db, uid, key)
            if pid:
                row['partner_id'] = pid
                matched.append(row)
            else:
                log.warning("UNMATCHED — no partner found: %s <%s>",
                            row['name'], row['email'])
                unmatched += 1
        rows = matched
        log.info("Matched %d / %d rows to Odoo partners", len(rows), total_rows)

    log.info("Recipients to process: %d", len(rows))

    # Build set of emails already in the mail queue (idempotency guard)
    already_queued = set()
    if live and not test:
        queued_mails = call(models, db, uid, key,
            'mail.mail', 'search_read',
            [[('subject', 'ilike', 'Consulta Presupuestaria 2026-2027'),
              ('state', 'in', ['outgoing', 'sent'])]],
            {'fields': ['email_to'], 'limit': 500})
        import re as _re
        for mail in queued_mails:
            for addr in _re.findall(r'[\w.+\-]+@[\w.\-]+', mail.get('email_to','') or ''):
                already_queued.add(addr.lower())
        if already_queued:
            log.info("Idempotency guard: %d addresses already in mail queue — will skip",
                     len(already_queued))

    sent = skipped = glenda_direct = 0

    for row in rows:
        name       = row['name']
        email      = CEO_EMAIL if test else row['email']
        phone      = row.get('phone', '')
        partner_id = row['partner_id']

        # ── No email but has phone → Glenda WA directly ──────────────────────
        if not email and phone and not test:
            if not live:
                log.info("  DRY  %s — no email, would create Glenda WA (phone=%s)",
                         name, phone)
                continue
            conv_id = _create_glenda_vote_conv(
                models, db, uid, key, name, phone, partner_id)
            if conv_id:
                log.info("  GLENDA %s — WA conv #%d started (no email)", name, conv_id)
                glenda_direct += 1
            else:
                log.warning("  SKIP %s — no email and Glenda conv failed", name)
                skipped += 1
            time.sleep(SEND_DELAY)
            continue

        if not email:
            log.warning("  SKIP %s — no email, no phone", name)
            skipped += 1
            continue

        # Check existing ACK
        ack = _get_existing_ack(models, db, uid, key, partner_id)

        if ack and ack.get('state') != 'pending':
            log.info("  SKIP %s — already voted (%s)", name, ack['state'])
            skipped += 1
            continue

        if not live:
            log.info("  DRY  %s <%s> phone=%s", name, email, phone)
            continue

        # Create ACK if not exists
        if not ack:
            ack_id = _create_ack(models, db, uid, key,
                                  partner_id, name, email, phone)
        else:
            ack_id = ack['id']
            # Update partner_phone if not set
            if phone and not ack.get('partner_phone'):
                call(models, db, uid, key,
                     'partner.communication.ack', 'write',
                     [[ack_id], {'partner_phone': phone}])

        # Skip if any of this partner's addresses already queued
        partner_addrs = set(a.strip().lower()
            for a in email.replace(';',',').split(',') if a.strip())
        if already_queued & partner_addrs:
            log.info("  SKIP %s — email already in queue", name)
            skipped += 1
            continue

        token  = _get_token(models, db, uid, key, ack_id)
        si_url = f"{ODOO_URL}/partner-ack/{token}/si"
        no_url = f"{ODOO_URL}/partner-ack/{token}/no"
        html   = _build_html(name, si_url, no_url, is_test=test)

        call(models, db, uid, key, 'mail.mail', 'create', [[{
            'subject':    'Consulta Presupuestaria 2026-2027 — Ejerza su voto',
            'email_from': 'Colegio Andrés Bello <votacion@ueipab.edu.ve>',
            'email_to':   f'{name} <{email}>',
            'email_cc':   'votacion@ueipab.edu.ve',
            'reply_to':   'votacion@ueipab.edu.ve',
            'body_html':  html,
            'state':      'outgoing',
        }]])

        log.info("  QUEUED %s <%s>", name, email)
        sent += 1
        time.sleep(SEND_DELAY)

    # Trigger mail queue
    if live and sent > 0:
        try:
            call(models, db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])
            log.info("✅ Mail queue triggered.")
        except Exception as e:
            log.warning("Could not trigger mail queue: %s", e)

    log.info("=" * 70)
    log.info("QUEUED: %d  |  GLENDA DIRECT: %d  |  SKIPPED: %d",
             sent, glenda_direct, skipped)
    log.info("=" * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live',  action='store_true', help='Actually send emails')
    parser.add_argument('--test',  action='store_true', help='CEO preview only')
    args = parser.parse_args()
    main(live=args.live, test=args.test)
