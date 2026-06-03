#!/usr/bin/env python3
"""
attendance_daily_alert.py
─────────────────────────
Daily attendance alert system for UEIPAB employees.

Two modes:

  morning  (07:30 VET = 11:30 UTC) — recap yesterday
    • No attendance record at all → "Sin registro de entrada"
    • Has check_in but no check_out → "Salida sin registrar"
    • Worked < 5.0 hours (with check_out) → "Horas trabajadas insuficientes"
    Only sends email if at least one issue found.
    Special-schedule employees (571, 606, 610) skip absent + short-hours checks.

  evening  (19:30 VET = 23:30 UTC) — after sync crons (22:30 + 22:35 UTC)
    • Has check_in today but check_out is still False AND check_in < resolved checkout:
      → Queries Router 2 (HapAC3) via SSH for the employee's last WiFi 'logged out'
        event today (uses wifi_hotspot_users username mapping from payroll_db).
      → If WiFi logout found and < 20:00 VET: AUTO-FILLS with that exact time.
      → If not found (not on WiFi / no mapping): AUTO-FILLS with 14:00 VET fallback.
      → No email sent in either case.
    • Has check_in today but check_out is still False AND check_in >= resolved checkout:
      → Skipped silently (edge case — late check-in, WiFi data before check-in, etc.).
    Special-schedule employees (571, 606, 610) are skipped entirely.

Excluded employees:
  • IDs 574 and 764 (test accounts, tdv.devs@gmail.com)
  • Holidays from ir.config_parameter key 'attendance_report.holidays'

State file: scripts/attendance_daily_alert_state.json
  Keys: "evening_YYYY-MM-DD_EMPID" / "morning_YYYY-MM-DD_EMPID" → ISO timestamp
  Entries older than 14 days are pruned on each run.

Usage:
    python3 scripts/attendance_daily_alert.py               # dry run, auto-detect mode
    python3 scripts/attendance_daily_alert.py --mode morning
    python3 scripts/attendance_daily_alert.py --mode evening
    python3 scripts/attendance_daily_alert.py --live --mode morning

Cron: /etc/cron.d/attendance_daily_alert

Author: Claude Code Assistant
Date: 2026-05-19
"""

import argparse
import json
import logging
import os
import re
import subprocess
import xmlrpc.client
from datetime import date, datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

DRY_RUN = True
TEST_EMAIL = None   # when set, all emails go to this address only (no state writes)

VET_OFFSET = timedelta(hours=4)          # VET = UTC-4 (no DST in Venezuela)

EXCLUDE_EMPLOYEE_IDS = {574, 764}        # test accounts — Administrador 3Dv
SPECIAL_SCHEDULE_IDS = {571, 606, 610}   # maintenance / security — non-standard hours

MIN_WORKED_HOURS = 5.0                   # below this → short-hours alert
AUTO_CHECKOUT_VET_HOUR = 14              # 14:00 VET = 18:00 UTC — school day end for auto-fill
WIFI_LOGOUT_CAP_HOUR = 20               # ignore WiFi logouts at or after 20:00 VET

# Mikrotik Router 2 (HapAC3) — hotspot session log source
MIKROTIK_HOST = '172.28.10.10'          # ZeroTier VPN address
MIKROTIK_USER = 'odooapi'
MIKROTIK_PASS = 'Steam*1'

# WiFi username mapping DB (payroll_db — same DB as sync_mikrotik_attendance)
WIFI_DB = {
    'host': 'localhost', 'port': 3306,
    'user': 'bcv_script', 'password': 'oCurrency*1',
    'database': 'payroll_db', 'charset': 'utf8mb4',
}

# control_asistencias DB — teacher work-delivery signal (Phase 1)
CA_DB = {
    'host': 'localhost', 'port': 3306,
    'user': 'control_asist', 'password': 'y3deTsi92HrQgj0wgvVx',
    'database': 'control_asistencias', 'charset': 'utf8mb4',
}

MIN_WORKED_HOURS_TEACHER = 4.5   # teachers finish ~12:45 VET (morning block only)

# Confidence score thresholds — below SCORE_FULL_ALERT → suppress employee email
SCORE_SILENCE    = 60   # multiple signals confirm presence → complete silence
SCORE_RRHH_ONLY  = 30   # some signals confirm → log internally, no employee email

SIGNAL_WEIGHTS = {
    'asistencia_submitted': 65,  # teacher submitted student attendance — alone sufficient for silence
    'wifi_connected':       25,  # on-campus network confirmed
    'odoo_checkin':         20,  # kiosk tap
    'odoo_hours_adequate':  20,  # worked >= expected hours
}

LOGO_URL = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
RRHH_EMAIL = 'recursoshumanos@ueipab.edu.ve'
SENDER_NAME = 'Recursos Humanos UEIPAB'
SENDER_EMAIL = 'recursoshumanos@ueipab.edu.ve'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, 'attendance_daily_alert_state.json')
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'production.json'))

MAIL_QUEUE_CRON_ID = 3   # ir.cron id=3 in production

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
    return {}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def prune_state(state, days=14):
    """Remove state entries older than `days` days."""
    cutoff = datetime.now() - timedelta(days=days)
    keys_to_remove = []
    for key, ts in state.items():
        try:
            if datetime.fromisoformat(ts) < cutoff:
                keys_to_remove.append(key)
        except Exception:
            pass
    for k in keys_to_remove:
        del state[k]
    return len(keys_to_remove)

# ============================================================================
# Odoo XML-RPC
# ============================================================================

_odoo_conn = None


def _load_prod_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)['production']['xmlrpc']


def odoo():
    global _odoo_conn
    if _odoo_conn:
        return _odoo_conn
    cfg = _load_prod_config()
    url = cfg['url']
    db  = cfg['db']
    user = cfg['user']
    api_key = cfg['api_key']

    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, api_key, {})
    if not uid:
        raise RuntimeError("Odoo XML-RPC authentication failed")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    _odoo_conn = (db, uid, api_key, models)
    logger.info("Odoo connected (uid=%d, db=%s)", uid, db)
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


def odoo_get_param(key, default=''):
    rows = odoo_search_read('ir.config_parameter', [('key', '=', key)], ['value'], limit=1)
    return rows[0]['value'] if rows else default


_web_base_url = None

def get_fix_url_for_employee(emp_id: int, target_date: date):
    """Return the /attendance-fix/<token> URL for this employee's active report
    that covers target_date, or None if no matching report exists."""
    global _web_base_url
    try:
        date_str = target_date.strftime('%Y-%m-%d')
        reports = odoo_search_read(
            'hr.attendance.report',
            [
                ('employee_id', '=', emp_id),
                ('date_from',   '<=', date_str),
                ('date_to',     '>=', date_str),
                ('state',       'in', ['sent', 'draft']),
            ],
            ['ack_token'],
            limit=1,
        )
        if not reports or not reports[0].get('ack_token'):
            return None
        token = reports[0]['ack_token']
        if not _web_base_url:
            _web_base_url = odoo_get_param('web.base.url', 'https://odoo.ueipab.edu.ve').rstrip('/')
        return f"{_web_base_url}/attendance-fix/{token}"
    except Exception as e:
        logger.debug("get_fix_url_for_employee emp=%d: %s", emp_id, e)
        return None

# ============================================================================
# VET time helpers
# ============================================================================

def now_vet() -> datetime:
    return datetime.utcnow() - VET_OFFSET


def today_vet() -> date:
    return now_vet().date()


def vet_date_to_utc_range(d: date):
    """Return (start_utc, end_utc) string pair covering the full VET day."""
    start = datetime(d.year, d.month, d.day, 0, 0, 0) + VET_OFFSET
    end   = datetime(d.year, d.month, d.day, 23, 59, 59) + VET_OFFSET
    return start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')


def utc_to_vet(utc_str):
    """Convert Odoo UTC datetime string → VET datetime. Returns None on failure."""
    if not utc_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(utc_str, fmt) - VET_OFFSET
        except ValueError:
            pass
    return None

# ============================================================================
# Data fetchers
# ============================================================================

def get_holidays():
    """Return set of holiday dates from ir.config_parameter."""
    raw = odoo_get_param('attendance_report.holidays')
    dates = set()
    for part in raw.split(','):
        part = part.strip()
        if part:
            try:
                dates.add(date.fromisoformat(part))
            except ValueError:
                pass
    return dates


def get_payroll_employees():
    """Return list of active payroll employees (excluding test accounts)."""
    # Use active contracts to get payroll employees
    contracts = odoo_search_read(
        'hr.contract',
        [('state', '=', 'open')],
        ['employee_id'],
    )
    employee_ids = list({
        c['employee_id'][0]
        for c in contracts
        if c.get('employee_id') and c['employee_id'][0] not in EXCLUDE_EMPLOYEE_IDS
    })

    if not employee_ids:
        return []

    employees = odoo_search_read(
        'hr.employee',
        [('id', 'in', employee_ids), ('active', '=', True)],
        ['id', 'name', 'work_email'],
    )
    return [e for e in employees if e['id'] not in EXCLUDE_EMPLOYEE_IDS]


def get_guide_urls(employee_ids: list) -> dict:
    """Return {emp_id: notice-ack URL} for employees with an unacknowledged
    attendance_guide_2026_v1 record. Employees who already acked are omitted."""
    global _web_base_url
    if not _web_base_url:
        _web_base_url = odoo_get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
    try:
        rows = odoo_search_read(
            'hr.notice.acknowledgment',
            [('notice_key', '=', 'attendance_guide_2026_v1'),
             ('employee_id', 'in', employee_ids),
             ('state', '=', 'pending')],
            ['employee_id', 'token'],
        )
        return {r['employee_id'][0]: f"{_web_base_url}/attendance-guide/{r['token']}"
                for r in rows if r.get('token')}
    except Exception as e:
        logger.warning("get_guide_urls failed: %s", e)
        return {}


def get_attendance_for_date(employee_ids, target_date: date):
    """Return dict of employee_id → attendance record(s) for the given VET date."""
    start_utc, end_utc = vet_date_to_utc_range(target_date)
    records = odoo_search_read(
        'hr.attendance',
        [
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', start_utc),
            ('check_in', '<=', end_utc),
        ],
        ['id', 'employee_id', 'check_in', 'check_out', 'worked_hours'],
    )
    # Group by employee_id; keep the record with latest check_in if multiple
    result = {}
    for r in records:
        emp_id = r['employee_id'][0]
        if emp_id not in result:
            result[emp_id] = r
        else:
            # keep latest check_in
            if (r['check_in'] or '') > (result[emp_id]['check_in'] or ''):
                result[emp_id] = r
    return result


def get_leaves_for_date(employee_ids: list, target_date: date) -> dict:
    """Return dict of employee_id → list of leave records covering target_date."""
    start_utc, end_utc = vet_date_to_utc_range(target_date)
    records = odoo_search_read(
        'hr.leave',
        [
            ('employee_id', 'in', employee_ids),
            ('date_from', '<=', end_utc),
            ('date_to', '>=', start_utc),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ],
        ['id', 'employee_id', 'holiday_status_id', 'date_from', 'date_to',
         'state', 'number_of_days'],
    )
    result = {}
    for r in records:
        emp_id = r['employee_id'][0]
        result.setdefault(emp_id, []).append(r)
    return result


_LEAVE_STATE_LABELS = {
    'confirm':   ('⏳', 'Pendiente de aprobación', '#fff8e1', '#f9a825', '#f57f17'),
    'validate1': ('⏳', 'Pendiente de aprobación', '#fff8e1', '#f9a825', '#f57f17'),
    'validate':  ('✅', 'Aprobado',                '#e8f5e9', '#43a047', '#2e7d32'),
}


def _format_leave_context_html(emp_leaves: list) -> str:
    """Render leave context blocks for inclusion in the morning attendance email."""
    if not emp_leaves:
        return ''
    blocks = []
    for lv in emp_leaves:
        state = lv.get('state', 'confirm')
        icon, label, bg, border, text = _LEAVE_STATE_LABELS.get(
            state, ('ℹ️', state, '#f5f5f5', '#9e9e9e', '#616161')
        )
        leave_type = lv.get('holiday_status_id')
        type_name = (leave_type[1] if isinstance(leave_type, (list, tuple)) and len(leave_type) > 1
                     else str(leave_type or '—'))
        df_vet = utc_to_vet(lv.get('date_from') or '')
        dt_vet = utc_to_vet(lv.get('date_to') or '')
        time_range = ''
        if df_vet and dt_vet:
            time_range = f"{df_vet.strftime('%H:%M')} – {dt_vet.strftime('%H:%M')} VET · "
        days = float(lv.get('number_of_days') or 0)
        days_str = f"{days:.1f} día{'s' if days != 1.0 else ''}"
        blocks.append(f"""
    <div style="background:{bg};border-left:4px solid {border};border-radius:4px;
                padding:10px 14px;margin-bottom:10px;font-size:13px;color:{text};">
      <strong>{icon} Permiso registrado para este día:</strong> {type_name}<br>
      <span style="color:#555555;">{time_range}{days_str} · <em>{label}</em></span>
    </div>""")
    return '\n'.join(blocks)

# ============================================================================
# HTML email builders
# ============================================================================

_COMMON_CSS = """
    body { margin:0; padding:0; background:#f0f4f8; font-family: Arial, Helvetica, sans-serif; }
    .wrapper { max-width:580px; margin:0 auto; background:#ffffff; border-radius:8px;
               overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1); }
    .header { background:linear-gradient(135deg,#1a73e8,#0d47a1); padding:32px 24px;
              text-align:center; }
    .logo-wrap { display:inline-block; width:72px; height:72px; border-radius:50%;
                 overflow:hidden; border:3px solid rgba(255,255,255,0.3);
                 background:#ffffff; margin-bottom:12px; }
    .logo-wrap img { width:72px; height:72px; object-fit:cover; display:block; }
    .header h1 { margin:0; color:#ffffff; font-size:20px; font-weight:700;
                 letter-spacing:0.5px; }
    .header p  { margin:4px 0 0; color:rgba(255,255,255,0.85); font-size:13px; }
    .banner { margin:20px 16px 0; padding:14px 16px;
              background:#fff3cd; border-left:4px solid #f0ad4e; border-radius:4px; }
    .banner-title { margin:0 0 2px; font-size:15px; font-weight:700; color:#856404; }
    .body-section { padding:20px 24px; }
    .greeting { font-size:15px; color:#333333; margin:0 0 10px; }
    .context  { font-size:14px; color:#555555; margin:0 0 16px; line-height:1.5; }
    .detail-table { width:100%; border-collapse:collapse; margin-bottom:16px; }
    .detail-table td { padding:8px 10px; font-size:13px; border-bottom:1px solid #f0f0f0;
                       vertical-align:middle; }
    .detail-table td:first-child { width:28px; text-align:center; }
    .detail-table td:nth-child(2) { color:#555555; width:140px; }
    .detail-table td:last-child   { color:#222222; font-weight:600; }
    .tip-box  { background:#f8f9fa; border-radius:6px; padding:12px 14px;
                font-size:13px; color:#444444; margin-bottom:14px; line-height:1.5; }
    .rrhh-card { background:#e8f0fe; border-radius:6px; padding:12px 14px;
                 font-size:13px; color:#1a73e8; }
    .rrhh-card a { color:#1a73e8; }
    .footer { background:#f8f9fa; padding:14px 24px; text-align:center;
              font-size:11px; color:#aaaaaa; border-top:1px solid #eeeeee; }
"""


def _base_html(body_content: str, title_override: str = None) -> str:
    title = title_override or 'Control de Asistencia — UEIPAB'
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{_COMMON_CSS}</style>
</head>
<body>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:20px 0;">
<tr><td align="center">
<div class="wrapper">
  <!-- Header -->
  <div class="header">
    <img src="{LOGO_URL}" alt="UEIPAB Logo" width="72" height="72"
         style="width:72px;height:72px;border-radius:50%;display:block;margin:0 auto 12px;border:3px solid rgba(255,255,255,0.3);object-fit:cover;">
    <h1>Control de Asistencia</h1>
    <p>U.E.I.P.A.B.</p>
  </div>
  {body_content}
  <!-- Footer -->
  <div class="footer">
    Este mensaje fue generado automáticamente por el sistema de Control de Asistencia de UEIPAB.
    Por favor no responda directamente a este correo. Para consultas, escriba a
    <a href="mailto:{RRHH_EMAIL}" style="color:#aaaaaa;">{RRHH_EMAIL}</a>.
  </div>
</div>
</td></tr>
</table>
</body>
</html>"""


def build_evening_email(emp_name: str, check_in_vet: datetime, target_date: date) -> str:
    """HTML for missing check-out alert."""
    date_str = target_date.strftime('%d/%m/%Y')
    checkin_str = check_in_vet.strftime('%H:%M') if check_in_vet else '—'
    first_name = emp_name.split()[0].capitalize() if emp_name else emp_name

    body = f"""
  <!-- Alert banner -->
  <div class="banner">
    <p class="banner-title">⏰ Registro de salida pendiente</p>
    <span style="font-size:13px;color:#856404;">Se detectó entrada sin salida registrada hoy.</span>
  </div>

  <!-- Body -->
  <div class="body-section">
    <p class="greeting">Hola {first_name},</p>
    <p class="context">
      El día de hoy <strong>{date_str}</strong> tienes una entrada registrada en el sistema,
      pero aún no se ha registrado tu salida. Por favor verifica tu registro de asistencia.
    </p>

    <table class="detail-table">
      <tr>
        <td>🗓️</td><td>Fecha</td><td>{date_str}</td>
      </tr>
      <tr>
        <td>🟢</td><td>Entrada</td><td>{checkin_str}</td>
      </tr>
      <tr>
        <td>🔴</td><td>Salida</td><td>No registrada</td>
      </tr>
    </table>

    <div class="tip-box">
      💡 <strong>¿Olvidaste registrar tu salida?</strong><br>
      Si ya te retiraste, comunícate con Recursos Humanos para corregir el registro
      de asistencia de hoy. Es importante mantener el registro actualizado.
    </div>

    <div class="rrhh-card">
      📧 <strong>Recursos Humanos:</strong>
      <a href="mailto:{RRHH_EMAIL}">{RRHH_EMAIL}</a>
    </div>
  </div>
"""
    return _base_html(body, f'Registro de salida pendiente — {date_str}')


def build_morning_email(emp_name: str, issues: list, target_date: date,
                        fix_url: str = None, leave_context_html: str = '',
                        guide_url: str = None) -> str:
    """HTML for morning recap with one or more issues.

    issues: list of dicts with keys: icon, label, value, detail (optional)
    fix_url: if provided, show a direct correction button instead of plain email card
    guide_url: if provided, show a subtle guide link below the correction CTA
    """
    date_str = target_date.strftime('%d/%m/%Y')
    first_name = emp_name.split()[0].capitalize() if emp_name else emp_name

    # Build issue rows
    rows_html = ''
    for issue in issues:
        icon  = issue.get('icon', '⚠️')
        label = issue.get('label', '')
        value = issue.get('value', '')
        rows_html += f"""
      <tr>
        <td>{icon}</td><td>{label}</td><td>{value}</td>
      </tr>"""

    issue_count = len(issues)
    issues_label = f"{issue_count} incidencia{'s' if issue_count != 1 else ''} detectada{'s' if issue_count != 1 else ''}"

    # Correction CTA — button if we have a fix URL, plain email card otherwise
    if fix_url:
        correction_html = f"""
    <div class="tip-box">
      💡 <strong>¿Este registro no es correcto?</strong><br>
      Puedes solicitar la corrección directamente — Recursos Humanos la revisará
      antes del cierre de nómina.
    </div>
    <div style="text-align:center;margin:16px 0 8px;">
      <a href="{fix_url}"
         style="display:inline-block;background:#e65100;color:#ffffff;
                padding:12px 32px;font-size:14px;font-weight:700;
                text-decoration:none;border-radius:7px;
                box-shadow:0 2px 8px rgba(0,0,0,0.18);">
        📝 Solicitar Corrección
      </a>
    </div>
    <p style="text-align:center;font-size:11px;color:#aaa;margin:4px 0 16px;">
      El formulario ya tiene tus datos — solo indica el motivo y la hora correcta.
    </p>"""
    else:
        correction_html = f"""
    <div class="tip-box">
      💡 <strong>¿Necesitas corregir tu registro?</strong><br>
      Puedes solicitar una corrección de asistencia escribiendo a Recursos Humanos.
      Indica la fecha, hora de entrada y/o salida correcta, y el motivo del error.
    </div>
    <div class="rrhh-card">
      📧 <strong>Recursos Humanos:</strong>
      <a href="mailto:{RRHH_EMAIL}">{RRHH_EMAIL}</a>
    </div>"""

    body = f"""
  <!-- Alert banner -->
  <div class="banner">
    <p class="banner-title">📋 Resumen de asistencia — {date_str}</p>
    <span style="font-size:13px;color:#856404;">{issues_label} en tu registro del día anterior.</span>
  </div>

  <!-- Body -->
  <div class="body-section">
    <p class="greeting">Hola {first_name},</p>
    <p class="context">
      A continuación encontrarás el resumen de incidencias detectadas en tu registro
      de asistencia correspondiente al día <strong>{date_str}</strong>.
    </p>

    <table class="detail-table">
      <tr>
        <td>👤</td><td>Empleado</td><td>{emp_name}</td>
      </tr>
      <tr>
        <td>🗓️</td><td>Fecha</td><td>{date_str}</td>
      </tr>
      {rows_html}
    </table>

    {leave_context_html}
    {correction_html}
    {f'''<div style="text-align:center;margin:4px 0 12px;">
      <a href="{guide_url}"
         style="font-size:12px;color:#2471a3;text-decoration:none;font-weight:600;">
        📋 Ver Guía de Asistencia — cómo funciona y cómo te protege →
      </a>
    </div>''' if guide_url else ''}
  </div>
"""
    return _base_html(body, f'Resumen de asistencia — {date_str}')

# ============================================================================
# Email queuing via Odoo mail.mail
# ============================================================================

def queue_email(to_email: str, subject: str, body_html: str) -> int:
    """Create a mail.mail record in state='outgoing'. Returns id or -1 for dry run.

    In test mode: redirects TO to TEST_EMAIL, no CC.
    In live mode:  sends to real recipient + CC recursoshumanos@.
    """
    effective_to = TEST_EMAIL if TEST_EMAIL else to_email
    effective_subject = f"[TEST] {subject}" if TEST_EMAIL else subject

    if DRY_RUN:
        logger.info("  [DRY] Would queue email to %s (cc=%s) | %s",
                    effective_to, RRHH_EMAIL if not TEST_EMAIL else 'none', effective_subject)
        return -1

    vals = {
        'subject':       effective_subject,
        'body_html':     body_html,
        'email_to':      effective_to,
        'email_from':    f'{SENDER_NAME} <{SENDER_EMAIL}>',
        'reply_to':      RRHH_EMAIL,
        'state':         'outgoing',
        'auto_delete':   True,
    }
    if not TEST_EMAIL:
        vals['email_cc'] = RRHH_EMAIL

    mail_id = odoo_execute('mail.mail', 'create', [vals])
    logger.info("  Queued mail.mail id=%d to %s cc=%s reply_to=%s",
                mail_id, effective_to, vals.get('email_cc', 'none'), RRHH_EMAIL)
    return mail_id


def trigger_mail_queue():
    """Trigger the mail queue cron (id=3) to flush outgoing emails."""
    if DRY_RUN:
        logger.info("[DRY] Would trigger mail queue cron id=%d", MAIL_QUEUE_CRON_ID)
        return
    try:
        odoo_execute('ir.cron', 'method_direct_trigger', [[MAIL_QUEUE_CRON_ID]])
        logger.info("Mail queue cron triggered (id=%d)", MAIL_QUEUE_CRON_ID)
    except Exception as e:
        logger.warning("Failed to trigger mail queue: %s", e)


def _load_wifi_email_to_usernames() -> dict:
    """Return {work_email_lower: {username, ...}} from wifi_hotspot_users table.

    Both the laptop username (e.g. 'nlarosa') and cell username ('celnlarosa')
    are included so we capture whichever device was last seen on the hotspot.
    Returns an empty dict on any DB error — callers fall back to fixed 14:00.
    """
    import pymysql
    mapping = {}
    try:
        conn = pymysql.connect(**WIFI_DB)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT hotspot_username, odoo_login
                    FROM wifi_hotspot_users
                    WHERE user_category = 'odoo_user' AND enabled = 1
                """)
                for username, email in cur.fetchall():
                    if username and email:
                        mapping.setdefault(email.lower(), set()).add(username.lower())
        finally:
            conn.close()
    except Exception as e:
        logger.warning("WiFi DB lookup failed — checkout will use fixed fallback: %s", e)
    return mapping


def _router_ssh(command: str) -> str:
    """Run a RouterOS command via SSH and return stdout. Empty string on failure."""
    try:
        result = subprocess.run(
            ['sshpass', '-p', MIKROTIK_PASS,
             'ssh',
             '-o', 'StrictHostKeyChecking=no',
             '-o', 'ConnectTimeout=10',
             '-o', 'LogLevel=ERROR',
             f'{MIKROTIK_USER}@{MIKROTIK_HOST}',
             command],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout
    except Exception as e:
        logger.warning("Mikrotik SSH error: %s", e)
        return ''


def _get_all_wifi_logouts(username_set: set, target_vet_date: date) -> dict:
    """One SSH call to Router 2 to find the last 'logged out' event per username today.

    Queries ALL hotspot logout events during school hours and filters by username
    on the Python side.  This is faster than building a long OR condition in
    the router query (Mikrotik scans ~32k log entries linearly regardless).

    Router timestamps are in VET (America/Caracas — confirmed).
    Returns {username_lower: last_logout_vet_datetime}.
    """
    if not username_set:
        return {}

    # Broad query: all hotspot logouts during school hours.
    # Python filters to the relevant usernames — avoids a long router-side OR clause.
    date_str = target_vet_date.strftime('%Y-%m-%d')
    cmd = (
        f'/ log print where topics~"hotspot"'
        f' and message~"logged out"'
        f' and time>="{date_str} 06:00:00"'
        f' and time<="{date_str} 18:00:00"'
    )

    output = _router_ssh(cmd)
    result = {}

    for line in output.splitlines():
        line = line.strip()
        # Line format: "2026-05-19 13:12:59 hotspot,info,debug nlarosa (192.168.10.x): logged out..."
        m = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(\w+)\s', line)
        if not m:
            continue
        try:
            ts       = datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S')
            username = m.group(2).lower()
            if username in username_set:
                if username not in result or ts > result[username]:
                    result[username] = ts
        except ValueError:
            pass

    return result


def auto_fill_checkout(att_id: int, checkout_utc_str: str) -> bool:
    """Write check_out on an hr.attendance record. Returns True on success."""
    if DRY_RUN:
        logger.info("  [DRY] Would write check_out=%s on attendance id=%d",
                    checkout_utc_str, att_id)
        return True
    try:
        odoo_execute('hr.attendance', 'write', [[att_id], {'check_out': checkout_utc_str}])
        return True
    except Exception as e:
        logger.error("  Failed to auto-fill check_out on attendance id=%d: %s", att_id, e)
        return False

# ============================================================================
# Phase 1: Multi-signal confidence engine
# ============================================================================

def load_teacher_emails() -> set:
    """Return set of lowercase work emails for all teachers in profesor_seccion."""
    import pymysql
    try:
        conn = pymysql.connect(**CA_DB)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT u.email
                    FROM usuario u
                    JOIN profesor_seccion ps ON ps.id_profesor = u.id_usuario
                    WHERE u.email IS NOT NULL AND u.email != ''
                """)
                return {r[0].lower() for r in cur.fetchall()}
        finally:
            conn.close()
    except Exception as e:
        logger.warning("Could not load teacher emails from control_asistencias: %s", e)
        return set()


def get_asistencia_signals_batch(teacher_emails: set, target_date: date) -> set:
    """Return set of lowercase emails that submitted asistencia_estudiante for target_date.

    One DB round-trip for all teachers. Returns empty set on any error so that
    failure never suppresses an alert (safe default = send alert).
    """
    import pymysql
    if not teacher_emails:
        return set()
    try:
        conn = pymysql.connect(**CA_DB)
        try:
            with conn.cursor() as cur:
                placeholders = ','.join(['%s'] * len(teacher_emails))
                cur.execute(
                    f"SELECT id_usuario, email FROM usuario WHERE email IN ({placeholders})",
                    list(teacher_emails),
                )
                user_map = {uid: eml.lower() for uid, eml in cur.fetchall()}
                if not user_map:
                    return set()

                id_ph = ','.join(['%s'] * len(user_map))
                cur.execute(
                    f"""SELECT DISTINCT id_usuario FROM asistencia_estudiante
                        WHERE fecha = %s AND id_usuario IN ({id_ph})""",
                    [target_date.strftime('%Y-%m-%d')] + list(user_map.keys()),
                )
                submitted_ids = {r[0] for r in cur.fetchall()}
                return {user_map[uid] for uid in submitted_ids if uid in user_map}
        finally:
            conn.close()
    except Exception as e:
        logger.warning("asistencia batch check failed (%s) — defaulting to no suppression", e)
        return set()


def get_teacher_day_patterns(teacher_emails: set, reference_date: date,
                              lookback_days: int = 45) -> dict:
    """Return per-teacher weekday submission rates based on historical data.

    Returns: {email_lower: {weekday_int: (submitted_count, total_school_days)}}
    where weekday_int 0=Mon … 4=Fri.

    Failure returns empty dict — callers fall through to normal scoring.
    """
    import pymysql
    from collections import defaultdict
    if not teacher_emails:
        return {}
    cutoff = reference_date - timedelta(days=lookback_days)
    try:
        conn = pymysql.connect(**CA_DB)
        try:
            with conn.cursor() as cur:
                # All school days in window (any teacher submitted = school was open)
                cur.execute(
                    'SELECT DISTINCT fecha FROM asistencia_estudiante WHERE fecha >= %s',
                    (cutoff.strftime('%Y-%m-%d'),),
                )
                school_days = [r[0] for r in cur.fetchall()]
                wd_totals = defaultdict(int)
                for d in school_days:
                    wd_totals[d.weekday()] += 1

                # Per-teacher submission dates in window
                ph = ','.join(['%s'] * len(teacher_emails))
                cur.execute(
                    f"""SELECT u.email, ae.fecha
                        FROM usuario u
                        JOIN asistencia_estudiante ae ON ae.id_usuario = u.id_usuario
                        WHERE u.email IN ({ph}) AND ae.fecha >= %s
                        GROUP BY u.email, ae.fecha""",
                    list(teacher_emails) + [cutoff.strftime('%Y-%m-%d')],
                )
                wd_counts = defaultdict(lambda: defaultdict(int))
                for email, fecha in cur.fetchall():
                    wd_counts[email.lower()][fecha.weekday()] += 1

                result = {}
                for email in teacher_emails:
                    e = email.lower()
                    result[e] = {
                        wd: (wd_counts[e].get(wd, 0), wd_totals.get(wd, 0))
                        for wd in range(5)
                    }
                return result
        finally:
            conn.close()
    except Exception as e:
        logger.warning("Could not compute teacher day patterns: %s", e)
        return {}


_WD_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
OFF_DAY_MAX_RATE  = 0.25   # ≤25% submissions → off day
OFF_DAY_MIN_DATA  = 4      # need at least 4 occurrences of that weekday before suppressing


def compute_confidence_score(
    is_teacher: bool,
    has_checkin: bool,
    worked_hours: float,
    asistencia_submitted: bool,
    wifi_connected: bool,
) -> tuple:
    """Return (score: int, summary: str)."""
    score = 0
    parts = []

    if asistencia_submitted:
        score += SIGNAL_WEIGHTS['asistencia_submitted']
        parts.append('asistencia ✅')
    elif is_teacher:
        parts.append('asistencia ❌')

    if wifi_connected:
        score += SIGNAL_WEIGHTS['wifi_connected']
        parts.append('wifi ✅')
    elif is_teacher:
        parts.append('wifi ❌')

    if has_checkin:
        score += SIGNAL_WEIGHTS['odoo_checkin']
        parts.append('kiosk ✅')
    else:
        parts.append('kiosk ❌')

    min_h = MIN_WORKED_HOURS_TEACHER if is_teacher else MIN_WORKED_HOURS
    if worked_hours >= min_h:
        score += SIGNAL_WEIGHTS['odoo_hours_adequate']
        parts.append(f'hours ✅({worked_hours:.1f}h)')
    else:
        parts.append(f'hours ❌({worked_hours:.1f}h)')

    return score, ' | '.join(parts)


# ============================================================================
# Evening mode: missing check-out
# ============================================================================

def run_evening(employees, state, holidays):
    target = today_vet()
    logger.info("Evening mode — target VET date: %s", target)

    if target in holidays:
        logger.info("Today (%s) is a holiday — skipping evening check", target)
        return 0

    # Fixed fallback checkout: 14:00 VET = 18:00 UTC
    fallback_vet     = datetime(target.year, target.month, target.day,
                                AUTO_CHECKOUT_VET_HOUR, 0, 0)
    fallback_utc_str = (fallback_vet + VET_OFFSET).strftime('%Y-%m-%d %H:%M:%S')

    employee_ids = [e['id'] for e in employees]
    attendance   = get_attendance_for_date(employee_ids, target)
    logger.info("  Attendance records found today: %d", len(attendance))

    # ── Pre-scan: identify candidates and load WiFi data in one shot ──────────

    # Load email → {username, ...} mapping from payroll DB
    wifi_email_map = _load_wifi_email_to_usernames()
    logger.info("  WiFi username map: %d email mappings loaded", len(wifi_email_map))

    # Identify employees who need auto-fill to gather their WiFi usernames
    candidates = []
    all_wifi_usernames = set()
    for emp in employees:
        if emp['id'] in SPECIAL_SCHEDULE_IDS:
            continue
        rec = attendance.get(emp['id'])
        if not rec or not rec.get('check_in'):
            continue
        co = rec.get('check_out')
        if co and co is not False:
            continue
        state_key = f"evening_{target}_{emp['id']}"
        if not TEST_EMAIL and state_key in state:
            continue
        candidates.append(emp)
        email = (emp.get('work_email') or '').lower()
        all_wifi_usernames.update(wifi_email_map.get(email, set()))

    # One SSH call to Router 2 for all affected usernames
    wifi_logouts = {}
    if all_wifi_usernames:
        logger.info("  Querying Router 2 WiFi log for %d username(s)...",
                    len(all_wifi_usernames))
        wifi_logouts = _get_all_wifi_logouts(all_wifi_usernames, target)
        logger.info("  WiFi logout events found: %d username(s)", len(wifi_logouts))
    else:
        logger.info("  No WiFi usernames mapped — all will use fallback 14:00 VET")

    # ── Main loop: auto-fill each candidate ───────────────────────────────────

    filled = 0
    for emp in candidates:
        emp_id       = emp['id']
        emp_name     = emp['name']
        rec          = attendance[emp_id]
        check_in_utc = rec['check_in']
        att_id       = rec['id']
        check_in_vet = utc_to_vet(check_in_utc)

        # Determine checkout from WiFi last-seen or fallback
        email          = (emp.get('work_email') or '').lower()
        emp_usernames  = wifi_email_map.get(email, set())

        # Find latest WiFi logout across all of this employee's usernames
        wifi_logout_vet = None
        for uname in emp_usernames:
            t = wifi_logouts.get(uname)
            if t and (wifi_logout_vet is None or t > wifi_logout_vet):
                wifi_logout_vet = t

        # Resolve checkout time
        if (wifi_logout_vet
                and wifi_logout_vet.hour < WIFI_LOGOUT_CAP_HOUR
                and check_in_utc < (wifi_logout_vet + VET_OFFSET).strftime('%Y-%m-%d %H:%M:%S')):
            checkout_utc_str = (wifi_logout_vet + VET_OFFSET).strftime('%Y-%m-%d %H:%M:%S')
            checkout_display = wifi_logout_vet.strftime('%H:%M')
            source           = f"WiFi logout {checkout_display} VET"
        else:
            checkout_utc_str = fallback_utc_str
            checkout_display = f"{AUTO_CHECKOUT_VET_HOUR:02d}:00"
            source           = "fallback 14:00 VET"

        # Final guard: check_in must still be before the resolved checkout
        if check_in_utc >= checkout_utc_str:
            logger.info("  %s — check_in (%s UTC) at or after checkout (%s UTC) [%s], skipping",
                        emp_name, check_in_utc[:16], checkout_utc_str[:16], source)
            continue

        logger.info("  AUTO-FILL: %s — check_in=%s → check_out=%s VET [%s] (att id=%d)",
                    emp_name,
                    check_in_vet.strftime('%H:%M') if check_in_vet else '?',
                    checkout_display, source, att_id)

        if auto_fill_checkout(att_id, checkout_utc_str):
            if not DRY_RUN and not TEST_EMAIL:
                state_key = f"evening_{target}_{emp_id}"
                state[state_key] = datetime.now().isoformat()
            filled += 1

    return filled

# ============================================================================
# Morning mode: yesterday's recap
# ============================================================================

def run_morning(employees, state, holidays):
    yesterday = today_vet() - timedelta(days=1)
    logger.info("Morning mode — recap for VET date: %s", yesterday)

    if yesterday.weekday() >= 5:  # 5=Saturday, 6=Sunday
        logger.info("Yesterday (%s) was a weekend — skipping morning recap", yesterday)
        return 0

    if yesterday in holidays:
        logger.info("Yesterday (%s) was a holiday — skipping morning recap", yesterday)
        return 0

    employee_ids = [e['id'] for e in employees]
    attendance   = get_attendance_for_date(employee_ids, yesterday)
    logger.info("  Attendance records found for yesterday: %d", len(attendance))
    leaves       = get_leaves_for_date(employee_ids, yesterday)
    logger.info("  Leave records found for yesterday: %d employee(s)", len(leaves))
    guide_urls   = get_guide_urls(employee_ids)
    logger.info("  Guide URLs (pending ack): %d employee(s)", len(guide_urls))

    # ── Phase 1: load signal sources ─────────────────────────────────────────
    teacher_emails = load_teacher_emails()
    logger.info("  Teachers in control_asistencias: %d", len(teacher_emails))

    # Asistencia batch: check all teacher emails at once
    teacher_emails_present = [
        (emp.get('work_email') or '').lower()
        for emp in employees
        if (emp.get('work_email') or '').lower() in teacher_emails
    ]
    asistencia_submitted = get_asistencia_signals_batch(set(teacher_emails_present), yesterday)
    logger.info("  Asistencia submitted yesterday: %d teacher(s)", len(asistencia_submitted))

    # Day-of-week pattern: derive each teacher's expected schedule
    teacher_day_patterns = get_teacher_day_patterns(teacher_emails, yesterday)
    logger.info("  Day patterns loaded for %d teacher(s)", len(teacher_day_patterns))

    # WiFi presence for yesterday: one SSH call covering all mapped employees
    wifi_email_map   = _load_wifi_email_to_usernames()
    all_wifi_usernames = set()
    for emp in employees:
        email = (emp.get('work_email') or '').lower()
        all_wifi_usernames.update(wifi_email_map.get(email, set()))
    wifi_presence = {}  # username_lower → last_event_vet_datetime
    if all_wifi_usernames:
        logger.info("  Querying Router 2 for yesterday WiFi presence (%d usernames)...",
                    len(all_wifi_usernames))
        wifi_presence = _get_all_wifi_logouts(all_wifi_usernames, yesterday)
        logger.info("  WiFi presence confirmed: %d username(s)", len(wifi_presence))

    sent = 0
    for emp in employees:
        emp_id    = emp['id']
        emp_name  = emp['name']
        emp_email = emp.get('work_email') or ''

        if not emp_email:
            logger.warning("  %s — no work_email, cannot send", emp_name)
            continue

        state_key = f"morning_{yesterday}_{emp_id}"
        if not TEST_EMAIL and state_key in state:
            logger.info("  %s — already sent morning recap for %s, skipping",
                        emp_name, yesterday)
            continue

        rec = attendance.get(emp_id)
        issues = []

        is_special = emp_id in SPECIAL_SCHEDULE_IDS

        if not rec:
            # No attendance record at all
            if not is_special:
                issues.append({
                    'icon': '🔴', 'label': 'Registro', 'value': 'Sin registro de entrada',
                })
        else:
            check_in_utc  = rec.get('check_in') or ''
            check_out_val = rec.get('check_out')
            worked_hours  = rec.get('worked_hours') or 0.0

            check_in_vet  = utc_to_vet(check_in_utc)
            check_in_str  = check_in_vet.strftime('%H:%M') if check_in_vet else '—'

            if not check_out_val or check_out_val is False:
                # Has check_in but missing check_out
                issues.append({
                    'icon': '🟢', 'label': 'Entrada', 'value': check_in_str,
                })
                issues.append({
                    'icon': '🔴', 'label': 'Salida', 'value': 'No registrada',
                })
            # Both check_in and check_out exist → employee registered correctly;
            # short-hours review belongs in the biweekly report, not the daily alert.

        if not issues:
            logger.debug("  %s — no issues for %s", emp_name, yesterday)
            continue

        # ── Phase 1: confidence scoring for teachers ──────────────────────────
        emp_email_lower = emp_email.lower()
        is_teacher = emp_email_lower in teacher_emails

        if is_teacher:
            # Off-day pattern check: suppress entirely if this weekday is historically absent
            wd = yesterday.weekday()
            day_pattern = teacher_day_patterns.get(emp_email_lower, {})
            submitted_n, total_n = day_pattern.get(wd, (0, 0))
            if total_n >= OFF_DAY_MIN_DATA and submitted_n / total_n <= OFF_DAY_MAX_RATE:
                pct = submitted_n / total_n * 100
                logger.info("  OFF-DAY: %s | %s %d/%d (%.0f%%) — contract off day, silence",
                            emp_name, _WD_NAMES[wd], submitted_n, total_n, pct)
                if not TEST_EMAIL:
                    state[state_key] = datetime.now().isoformat()
                continue

            rec = attendance.get(emp_id)
            has_checkin   = rec is not None and bool(rec.get('check_in'))
            worked_h      = float((rec or {}).get('worked_hours') or 0.0)
            asistencia_ok = emp_email_lower in asistencia_submitted
            emp_usernames = wifi_email_map.get(emp_email_lower, set())
            wifi_ok       = any(uname in wifi_presence for uname in emp_usernames)

            score, signal_summary = compute_confidence_score(
                is_teacher=True,
                has_checkin=has_checkin,
                worked_hours=worked_h,
                asistencia_submitted=asistencia_ok,
                wifi_connected=wifi_ok,
            )

            if score >= SCORE_SILENCE:
                logger.info("  SILENCE: %s | score=%d | %s",
                            emp_name, score, signal_summary)
                if not TEST_EMAIL:
                    state[state_key] = datetime.now().isoformat()
                continue

            if score >= SCORE_RRHH_ONLY:
                logger.info("  RRHH-ONLY: %s | score=%d | %s",
                            emp_name, score, signal_summary)
                if not TEST_EMAIL:
                    state[state_key] = datetime.now().isoformat()
                continue

            logger.info("  LOW-SCORE teacher: %s | score=%d | %s — sending alert",
                        emp_name, score, signal_summary)
        # ─────────────────────────────────────────────────────────────────────

        fix_url    = get_fix_url_for_employee(emp_id, yesterday)
        leave_html = _format_leave_context_html(leaves.get(emp_id, []))
        guide_url  = guide_urls.get(emp_id)
        subject    = f"📋 Resumen de asistencia — {yesterday.strftime('%d/%m/%Y')}"
        body_html  = build_morning_email(emp_name, issues, yesterday,
                                         fix_url=fix_url, leave_context_html=leave_html,
                                         guide_url=guide_url)

        issue_labels = ', '.join(i['label'] for i in issues if i['label'] not in ('Entrada', 'Salida'))
        if not issue_labels:
            issue_labels = ' + '.join(i['value'] for i in issues)
        logger.info("  ALERT morning: %s <%s> issues=[%s]",
                    emp_name, emp_email, issue_labels[:80])

        queue_email(emp_email, subject, body_html)
        if not TEST_EMAIL:
            state[state_key] = datetime.now().isoformat()
        sent += 1

    return sent

# ============================================================================
# Main
# ============================================================================

def main():
    global DRY_RUN

    parser = argparse.ArgumentParser(description='UEIPAB Attendance Daily Alert')
    parser.add_argument('--live', action='store_true', help='Disable dry-run (actually send emails)')
    parser.add_argument('--mode', choices=['morning', 'evening'],
                        help='Alert mode. Auto-detected from VET hour if omitted.')
    parser.add_argument('--test-email', metavar='EMAIL',
                        help='Redirect ALL outgoing emails to this address (no CC, no state write)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False

    global TEST_EMAIL
    if args.test_email:
        TEST_EMAIL = args.test_email
        logger.info("TEST MODE — all emails redirected to %s", TEST_EMAIL)

    # Auto-detect mode from VET hour if not specified
    if args.mode:
        mode = args.mode
    else:
        vet_hour = now_vet().hour
        mode = 'morning' if vet_hour < 12 else 'evening'
        logger.info("Auto-detected mode: %s (VET hour=%d)", mode, vet_hour)

    print('=' * 65)
    print('ATTENDANCE DAILY ALERT')
    print('=' * 65)
    print(f"  Date/time UTC : {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Date/time VET : {now_vet().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mode          : {mode}")
    print(f"  DRY_RUN       : {DRY_RUN}")
    print(f"  TEST_EMAIL    : {TEST_EMAIL or '(none — real recipients)'}")
    print()

    # Load and prune state
    state = load_state()
    pruned = prune_state(state)
    if pruned:
        logger.info("Pruned %d stale state entries (>14 days)", pruned)

    # Fetch holidays
    logger.info("Loading holidays from Odoo config...")
    try:
        holidays = get_holidays()
        logger.info("  Holidays: %d date(s) configured", len(holidays))
    except Exception as e:
        logger.error("Failed to load holidays: %s", e)
        holidays = set()

    # Fetch employees
    logger.info("Loading payroll employees...")
    try:
        employees = get_payroll_employees()
        logger.info("  Employees: %d active payroll employees found", len(employees))
    except Exception as e:
        logger.error("Failed to load employees: %s", e)
        return

    if not employees:
        logger.warning("No active payroll employees found — nothing to do")
        save_state(state)
        return

    # Run the selected mode
    if mode == 'morning':
        count = run_morning(employees, state, holidays)
        if count > 0:
            trigger_mail_queue()
    else:
        count = run_evening(employees, state, holidays)
        # Evening mode auto-fills attendance records — no emails, no mail queue needed

    # Save state
    save_state(state)

    print()
    print('=' * 65)
    print('SUMMARY')
    print('=' * 65)
    print(f"  Mode     : {mode}")
    if mode == 'morning':
        print(f"  Sent     : {count} email(s)")
    else:
        print(f"  Auto-filled : {count} check_out record(s) → 14:00 VET")
    print(f"  DRY_RUN  : {DRY_RUN}")
    print()


if __name__ == '__main__':
    main()
