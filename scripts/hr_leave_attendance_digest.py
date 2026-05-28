#!/usr/bin/env python3
"""
hr_leave_attendance_digest.py
─────────────────────────────
Daily HR digest: leave requests vs. attendance overview (last 30 days).
Sent to recursoshumanos@ueipab.edu.ve CC arcides.arzola@ueipab.edu.ve.

Sections:
  1. 🔴 Pending approvals (action required)
  2. 📅 30-day leave activity per employee
  3. ⚠️  High-issue employees (attendance flags from state file)

Usage:
    python3 scripts/hr_leave_attendance_digest.py                        # dry run
    python3 scripts/hr_leave_attendance_digest.py --live                 # send for real
    python3 scripts/hr_leave_attendance_digest.py --live --test-email X  # preview

Cron: weekdays 08:00 VET (12:00 UTC) — runs after morning attendance alert
"""

import argparse
import json
import logging
import os
import xmlrpc.client
from collections import defaultdict
from datetime import date, datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

RRHH_EMAIL   = 'recursoshumanos@ueipab.edu.ve'
CC_EMAIL     = 'arcides.arzola@ueipab.edu.ve'
SENDER_NAME  = 'Recursos Humanos UEIPAB'
SENDER_EMAIL = 'recursoshumanos@ueipab.edu.ve'
LOGO_URL     = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'

MAIL_QUEUE_CRON_ID = 3
VET_OFFSET         = timedelta(hours=4)
LOOKBACK_DAYS      = 30
HIGH_ISSUE_THRESHOLD = 3    # employees with this many+ morning flags are highlighted

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
ALERT_STATE_FILE = os.path.join(SCRIPT_DIR, 'attendance_daily_alert_state.json')
CONFIG_PATH      = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'production.json'))

EXCLUDE_EMPLOYEE_IDS = {574, 764}

DRY_RUN    = True
TEST_EMAIL = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ============================================================================
# Odoo XML-RPC
# ============================================================================

_odoo_conn = None


def odoo():
    global _odoo_conn
    if _odoo_conn:
        return _odoo_conn
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("Odoo XML-RPC authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object", allow_none=True)
    _odoo_conn = (cfg['db'], uid, cfg['api_key'], models)
    logger.info("Odoo connected (uid=%d)", uid)
    return _odoo_conn


def odoo_execute(model, method, args, kwargs=None):
    db, uid, pwd, m = odoo()
    return m.execute_kw(db, uid, pwd, model, method, args, kwargs or {})


def odoo_search_read(model, domain, fields, limit=0, order=''):
    kwargs = {'fields': fields}
    if limit:
        kwargs['limit'] = limit
    if order:
        kwargs['order'] = order
    return odoo_execute(model, 'search_read', [domain], kwargs)

# ============================================================================
# Time helpers
# ============================================================================

def now_vet() -> datetime:
    return datetime.utcnow() - VET_OFFSET


def today_vet() -> date:
    return now_vet().date()


def utc_to_vet(utc_str: str) -> datetime | None:
    if not utc_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(utc_str, fmt) - VET_OFFSET
        except ValueError:
            pass
    return None


def fmt_date(utc_str: str) -> str:
    d = utc_to_vet(utc_str)
    return d.strftime('%d/%m/%Y') if d else '—'


def fmt_datetime(utc_str: str) -> str:
    d = utc_to_vet(utc_str)
    return d.strftime('%d/%m/%Y %H:%M') if d else '—'


def days_ago_utc(n: int) -> str:
    """UTC string for n days ago from now."""
    return (datetime.utcnow() - timedelta(days=n)).strftime('%Y-%m-%d %H:%M:%S')

# ============================================================================
# Data fetchers
# ============================================================================

def fetch_pending_leaves() -> list:
    """Leaves in confirm (awaiting 1st approval) or validate1 (awaiting 2nd/HR approval)."""
    return odoo_search_read(
        'hr.leave',
        [('state', 'in', ['confirm', 'validate1'])],
        ['id', 'employee_id', 'holiday_status_id', 'date_from', 'date_to',
         'number_of_days', 'write_date', 'state'],
        order='state asc, write_date asc',
    )


def fetch_leaves_last_30d() -> list:
    """All non-draft leaves in the last 30 days."""
    cutoff = days_ago_utc(LOOKBACK_DAYS)
    return odoo_search_read(
        'hr.leave',
        [
            ('state', 'not in', ['draft', 'refuse']),
            ('date_from', '>=', cutoff),
        ],
        ['id', 'employee_id', 'holiday_status_id', 'date_from', 'date_to',
         'number_of_days', 'state'],
        order='employee_id asc, date_from asc',
    )


def fetch_employee_names(emp_ids: list) -> dict:
    """Return {emp_id: name} for the given ids."""
    if not emp_ids:
        return {}
    rows = odoo_search_read(
        'hr.employee',
        [('id', 'in', emp_ids)],
        ['id', 'name'],
    )
    return {r['id']: r['name'] for r in rows}


def build_attendance_issue_counts() -> dict:
    """
    Parse attendance_daily_alert_state.json and count morning_* entries per
    employee_id in the last LOOKBACK_DAYS days.
    Returns {emp_id(int): count}.
    """
    if not os.path.exists(ALERT_STATE_FILE):
        return {}
    with open(ALERT_STATE_FILE) as f:
        state = json.load(f)

    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    counts: dict[int, int] = defaultdict(int)

    for key, ts_str in state.items():
        if not key.startswith('morning_'):
            continue
        try:
            ts = datetime.fromisoformat(str(ts_str))
            if ts < cutoff:
                continue
            # key format: morning_YYYY-MM-DD_EMPID
            parts = key.split('_')
            emp_id = int(parts[-1])
            if emp_id not in EXCLUDE_EMPLOYEE_IDS:
                counts[emp_id] += 1
        except Exception:
            pass
    return dict(counts)

# ============================================================================
# HTML builders
# ============================================================================

_CSS = """
body { margin:0; padding:0; background:#f0f4f8; font-family:Arial,Helvetica,sans-serif; }
.wrap { max-width:620px; margin:0 auto; background:#fff; border-radius:8px;
        overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,.1); }
.hdr { background:linear-gradient(135deg,#1a73e8,#0d47a1); padding:28px 24px; text-align:center; }
.hdr h1 { margin:10px 0 4px; color:#fff; font-size:20px; font-weight:700; }
.hdr p  { margin:0; color:rgba(255,255,255,.85); font-size:13px; }
.section { padding:18px 24px 4px; }
.section-title { font-size:15px; font-weight:700; color:#333; margin:0 0 12px;
                 padding-bottom:6px; border-bottom:2px solid #e0e0e0; }
.no-issues { background:#e8f5e9; border-radius:6px; padding:10px 14px;
             font-size:13px; color:#2e7d32; margin-bottom:16px; }
.alert-box { background:#fce8e6; border-left:4px solid #d32f2f; border-radius:4px;
             padding:10px 14px; font-size:13px; color:#b71c1c; margin-bottom:16px; }
table.data { width:100%; border-collapse:collapse; font-size:12px; margin-bottom:16px; }
table.data th { background:#e8f0fe; color:#1a73e8; text-align:left; padding:7px 8px;
                font-weight:700; font-size:11px; text-transform:uppercase; letter-spacing:.4px; }
table.data td { padding:7px 8px; border-bottom:1px solid #f0f0f0; color:#333; vertical-align:top; }
table.data tr:hover td { background:#fafafa; }
.badge-pending  { display:inline-block; background:#fff3cd; color:#856404; border-radius:10px;
                  padding:2px 8px; font-size:11px; font-weight:600; }
.badge-approved { display:inline-block; background:#e8f5e9; color:#2e7d32; border-radius:10px;
                  padding:2px 8px; font-size:11px; font-weight:600; }
.badge-warn     { display:inline-block; background:#fce8e6; color:#c62828; border-radius:10px;
                  padding:2px 8px; font-size:11px; font-weight:600; }
.divider { height:1px; background:#f0f0f0; margin:0 24px; }
.footer { background:#f8f9fa; padding:14px 24px; text-align:center; font-size:11px;
          color:#aaa; border-top:1px solid #eee; }
"""


def _days_waiting(write_date_utc: str) -> str:
    d = utc_to_vet(write_date_utc)
    if not d:
        return '—'
    delta = (now_vet() - d).days
    if delta == 0:
        return 'Hoy'
    return f"{delta} día{'s' if delta != 1 else ''}"


def build_section_pending(pending: list) -> str:
    if not pending:
        return """
  <div class="section">
    <p class="section-title">🔴 Solicitudes Pendientes de Aprobación</p>
    <div class="no-issues">✅ No hay solicitudes pendientes en este momento.</div>
  </div>"""

    confirm_rows   = ''
    validate1_rows = ''

    for lv in pending:
        emp    = (lv.get('employee_id') or [None, '—'])[1]
        ltype  = (lv.get('holiday_status_id') or [None, '—'])[1]
        days   = float(lv.get('number_of_days') or 0)
        lv_id  = lv.get('id', '')
        lv_st  = lv.get('state', 'confirm')
        url    = f"https://odoo.ueipab.edu.ve/odoo/time-off/{lv_id}"

        if lv_st == 'validate1':
            btn_color = '#e65100'
            btn_label = 'Validar →'
        else:
            btn_color = '#1a73e8'
            btn_label = 'Aprobar →'

        row = f"""
      <tr>
        <td><strong>{emp}</strong></td>
        <td>{ltype}</td>
        <td>{fmt_date(lv.get('date_from', ''))}</td>
        <td style="text-align:center;">{days:.1f}d</td>
        <td style="text-align:center;"><span class="badge-warn">{_days_waiting(lv.get('write_date',''))}</span></td>
        <td style="text-align:center;">
          <a href="{url}"
             style="display:inline-block;background:{btn_color};color:#ffffff !important;
                    padding:4px 12px;border-radius:5px;text-decoration:none;
                    font-size:11px;font-weight:700;font-family:Arial,sans-serif;
                    white-space:nowrap;">
            {btn_label}
          </a>
        </td>
      </tr>"""
        if lv_st == 'validate1':
            validate1_rows += row
        else:
            confirm_rows += row

    n_confirm   = sum(1 for lv in pending if lv.get('state') == 'confirm')
    n_validate1 = sum(1 for lv in pending if lv.get('state') == 'validate1')
    alert_parts = []
    if n_validate1:
        alert_parts.append(f'<strong>{n_validate1} segunda(s) validación</strong> pendiente(s) de RRHH')
    if n_confirm:
        alert_parts.append(f'<strong>{n_confirm} solicitud(es)</strong> sin primera aprobación')
    alert = (f'<div class="alert-box">⚠️ ' + ' · '.join(alert_parts) + '</div>') if alert_parts else ''

    header_row = """
        <tr>
          <th>Empleado</th><th>Tipo de Permiso</th><th>Fecha</th>
          <th style="text-align:center;">Días</th>
          <th style="text-align:center;">Espera</th>
          <th style="text-align:center;">Acción</th>
        </tr>"""

    validate1_section = ''
    if validate1_rows:
        validate1_section = f"""
    <p style="font-size:13px;font-weight:700;color:#e65100;margin:4px 0 6px;">
      🔔 Segunda Validación — Pendiente de RRHH
    </p>
    <table class="data">
      <thead>{header_row}</thead>
      <tbody>{validate1_rows}
      </tbody>
    </table>"""

    confirm_section = ''
    if confirm_rows:
        confirm_section = f"""
    <p style="font-size:13px;font-weight:700;color:#1a73e8;margin:12px 0 6px;">
      📋 Primera Aprobación — Pendiente de Supervisor
    </p>
    <table class="data">
      <thead>{header_row}</thead>
      <tbody>{confirm_rows}
      </tbody>
    </table>"""

    return f"""
  <div class="section">
    <p class="section-title">🔴 Solicitudes Pendientes de Aprobación</p>
    {alert}
    {validate1_section}
    {confirm_section}
  </div>"""


def build_section_activity(leaves_30d: list) -> str:
    # Aggregate per employee
    by_emp: dict[str, dict] = {}
    for lv in leaves_30d:
        emp_tuple = lv.get('employee_id') or [None, '—']
        emp_id    = emp_tuple[0]
        emp_name  = emp_tuple[1]
        state     = lv.get('state', '')
        days      = float(lv.get('number_of_days') or 0)

        if emp_id not in by_emp:
            by_emp[emp_id] = {'name': emp_name, 'approved': 0.0, 'pending': 0.0, 'count': 0}
        by_emp[emp_id]['count'] += 1
        if state == 'validate':
            by_emp[emp_id]['approved'] += days
        elif state in ('confirm', 'validate1'):
            by_emp[emp_id]['pending'] += days

    if not by_emp:
        return """
  <div class="section">
    <p class="section-title">📅 Actividad de Permisos — Últimos 30 Días</p>
    <div class="no-issues">Sin solicitudes de permiso en los últimos 30 días.</div>
  </div>"""

    rows = ''
    for emp_data in sorted(by_emp.values(), key=lambda x: x['name']):
        approved = emp_data['approved']
        pending  = emp_data['pending']
        count    = emp_data['count']
        approved_badge = f'<span class="badge-approved">{approved:.1f}d</span>' if approved else '—'
        pending_badge  = f'<span class="badge-pending">{pending:.1f}d</span>' if pending else '—'
        rows += f"""
      <tr>
        <td>{emp_data['name']}</td>
        <td style="text-align:center;">{count}</td>
        <td style="text-align:center;">{approved_badge}</td>
        <td style="text-align:center;">{pending_badge}</td>
      </tr>"""

    return f"""
  <div class="section">
    <p class="section-title">📅 Actividad de Permisos — Últimos 30 Días</p>
    <table class="data">
      <thead>
        <tr>
          <th>Empleado</th>
          <th style="text-align:center;">Solicitudes</th>
          <th style="text-align:center;">Días Aprobados</th>
          <th style="text-align:center;">Días Pendientes</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>"""


def build_section_attendance_flags(issue_counts: dict, emp_names: dict) -> str:
    high = {emp_id: cnt for emp_id, cnt in issue_counts.items()
            if cnt >= HIGH_ISSUE_THRESHOLD}

    if not high:
        return f"""
  <div class="section">
    <p class="section-title">⚠️ Empleados con Más Incidencias — Últimos {LOOKBACK_DAYS} Días</p>
    <div class="no-issues">✅ Ningún empleado supera {HIGH_ISSUE_THRESHOLD} incidencias en el período.</div>
  </div>"""

    rows = ''
    for emp_id, cnt in sorted(high.items(), key=lambda x: -x[1]):
        name = emp_names.get(emp_id, f'ID {emp_id}')
        bar  = '█' * min(cnt, 10)
        severity = 'badge-warn' if cnt >= 5 else 'badge-pending'
        rows += f"""
      <tr>
        <td>{name}</td>
        <td style="text-align:center;"><span class="{severity}">{cnt}</span></td>
        <td style="color:#aaa;font-size:11px;">{bar}</td>
      </tr>"""

    return f"""
  <div class="section">
    <p class="section-title">⚠️ Empleados con Más Incidencias — Últimos {LOOKBACK_DAYS} Días</p>
    <table class="data">
      <thead>
        <tr>
          <th>Empleado</th>
          <th style="text-align:center;">Alertas Matutinas</th>
          <th>Frecuencia</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
  </div>"""


def build_digest_email(pending: list, leaves_30d: list, issue_counts: dict,
                       emp_names: dict) -> str:
    today_str  = today_vet().strftime('%d/%m/%Y')
    s_pending  = build_section_pending(pending)
    s_activity = build_section_activity(leaves_30d)
    s_flags    = build_section_attendance_flags(issue_counts, emp_names)

    pending_badge = (
        f'<span style="background:#d32f2f;color:#fff;border-radius:50%;'
        f'padding:2px 7px;font-size:12px;font-weight:700;margin-left:6px;">'
        f'{len(pending)}</span>' if pending else ''
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{_CSS}</style>
</head>
<body>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:20px 0;">
<tr><td align="center">
<div class="wrap">
  <!-- Header -->
  <div class="hdr">
    <img src="{LOGO_URL}" width="64" height="64"
         style="border-radius:50%;border:3px solid rgba(255,255,255,.3);display:block;
                margin:0 auto 10px;object-fit:cover;">
    <h1>📊 Resumen Diario — Permisos y Asistencia{pending_badge}</h1>
    <p>U.E.I.P.A.B. · {today_str} · Recursos Humanos</p>
  </div>

  {s_pending}
  <div class="divider"></div>
  {s_activity}
  <div class="divider"></div>
  {s_flags}

  <!-- Footer -->
  <div class="footer">
    Reporte generado automáticamente — {today_str} · Sistema de Asistencia UEIPAB<br>
    Para consultas: <a href="mailto:{RRHH_EMAIL}" style="color:#aaa;">{RRHH_EMAIL}</a>
  </div>
</div>
</td></tr>
</table>
</body>
</html>"""

# ============================================================================
# Email dispatch
# ============================================================================

def queue_email(to: str, cc: str, subject: str, body_html: str) -> int:
    effective_to      = TEST_EMAIL if TEST_EMAIL else to
    effective_cc      = '' if TEST_EMAIL else cc
    effective_subject = f"[TEST] {subject}" if TEST_EMAIL else subject

    if DRY_RUN:
        logger.info("[DRY] Would send to=%s cc=%s subject=%s", effective_to, effective_cc or 'none', effective_subject)
        return -1

    vals = {
        'subject':     effective_subject,
        'body_html':   body_html,
        'email_to':    effective_to,
        'email_from':  f'{SENDER_NAME} <{SENDER_EMAIL}>',
        'reply_to':    RRHH_EMAIL,
        'state':       'outgoing',
        'auto_delete': True,
    }
    if effective_cc:
        vals['email_cc'] = effective_cc

    mail_id = odoo_execute('mail.mail', 'create', [vals])
    logger.info("Queued mail.mail id=%d to=%s cc=%s", mail_id, effective_to, effective_cc or 'none')
    return mail_id


def trigger_mail_queue():
    if DRY_RUN:
        logger.info("[DRY] Would trigger mail queue cron id=%d", MAIL_QUEUE_CRON_ID)
        return
    try:
        odoo_execute('ir.cron', 'method_direct_trigger', [[MAIL_QUEUE_CRON_ID]])
        logger.info("Mail queue triggered")
    except Exception as e:
        logger.warning("Failed to trigger mail queue: %s", e)

# ============================================================================
# Main
# ============================================================================

def main():
    global DRY_RUN, TEST_EMAIL

    parser = argparse.ArgumentParser(description='UEIPAB HR Leave+Attendance Daily Digest')
    parser.add_argument('--live', action='store_true', help='Actually send email')
    parser.add_argument('--test-email', metavar='EMAIL',
                        help='Redirect to this address (no CC)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False
    if args.test_email:
        TEST_EMAIL = args.test_email
        logger.info("TEST MODE — digest → %s", TEST_EMAIL)

    print('=' * 65)
    print('HR LEAVE + ATTENDANCE DIGEST')
    print('=' * 65)
    print(f"  Date VET   : {today_vet()}")
    print(f"  DRY_RUN    : {DRY_RUN}")
    print(f"  TEST_EMAIL : {TEST_EMAIL or '(none — real recipients)'}")
    print()

    logger.info("Fetching pending leaves...")
    pending = fetch_pending_leaves()
    logger.info("  %d pending leave(s)", len(pending))

    logger.info("Fetching 30-day leave activity...")
    leaves_30d = fetch_leaves_last_30d()
    logger.info("  %d leave record(s) in last %d days", len(leaves_30d), LOOKBACK_DAYS)

    logger.info("Reading attendance issue counts from state file...")
    issue_counts = build_attendance_issue_counts()
    logger.info("  %d employee(s) with morning flags in last %d days",
                len(issue_counts), LOOKBACK_DAYS)

    # Resolve names for employees in issue_counts not already in leaves data
    leave_emp_ids = {(lv['employee_id'] or [None])[0] for lv in pending + leaves_30d
                     if lv.get('employee_id')}
    flag_emp_ids  = set(issue_counts.keys())
    missing_ids   = list((flag_emp_ids - leave_emp_ids) - EXCLUDE_EMPLOYEE_IDS)
    emp_names = fetch_employee_names(missing_ids) if missing_ids else {}
    logger.info("  Resolved %d additional employee name(s) for attendance flags", len(emp_names))

    today_str  = today_vet().strftime('%d/%m/%Y')
    pending_lbl = f" ({len(pending)} pendiente{'s' if len(pending) != 1 else ''})" if pending else ''
    subject    = f"📊 Resumen HR — Permisos & Asistencia {today_str}{pending_lbl}"
    body_html  = build_digest_email(pending, leaves_30d, issue_counts, emp_names)

    queue_email(RRHH_EMAIL, CC_EMAIL, subject, body_html)
    trigger_mail_queue()

    print()
    print('=' * 65)
    print('SUMMARY')
    print('=' * 65)
    print(f"  Pending leaves        : {len(pending)}")
    print(f"  30-day leave records  : {len(leaves_30d)}")
    print(f"  High-issue employees  : {sum(1 for c in issue_counts.values() if c >= HIGH_ISSUE_THRESHOLD)}")
    print(f"  DRY_RUN               : {DRY_RUN}")
    print()


if __name__ == '__main__':
    main()
