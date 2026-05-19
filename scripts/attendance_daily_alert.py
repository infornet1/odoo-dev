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
    • Has check_in today but check_out is still False → "Registro de salida pendiente"
    Special-schedule employees are skipped entirely.

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


def build_morning_email(emp_name: str, issues: list, target_date: date) -> str:
    """HTML for morning recap with one or more issues.

    issues: list of dicts with keys: icon, label, value, detail (optional)
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

    <div class="tip-box">
      💡 <strong>¿Necesitas corregir tu registro?</strong><br>
      Puedes solicitar una corrección de asistencia escribiendo a Recursos Humanos.
      Indica la fecha, hora de entrada y/o salida correcta, y el motivo del error.
    </div>

    <div class="rrhh-card">
      📧 <strong>Recursos Humanos:</strong>
      <a href="mailto:{RRHH_EMAIL}">{RRHH_EMAIL}</a>
    </div>
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

# ============================================================================
# Evening mode: missing check-out
# ============================================================================

def run_evening(employees, state, holidays):
    target = today_vet()
    logger.info("Evening mode — target VET date: %s", target)

    if target in holidays:
        logger.info("Today (%s) is a holiday — skipping evening check", target)
        return 0

    employee_ids = [e['id'] for e in employees]
    emp_map = {e['id']: e for e in employees}

    attendance = get_attendance_for_date(employee_ids, target)
    logger.info("  Attendance records found today: %d", len(attendance))

    sent = 0
    for emp in employees:
        emp_id   = emp['id']
        emp_name = emp['name']
        emp_email = emp.get('work_email') or ''

        # Skip special schedule for evening entirely
        if emp_id in SPECIAL_SCHEDULE_IDS:
            logger.debug("  %s — special schedule, skipping evening", emp_name)
            continue

        if not emp_email:
            logger.warning("  %s — no work_email, cannot send", emp_name)
            continue

        rec = attendance.get(emp_id)
        if not rec:
            # No attendance at all today — no check-out issue to flag
            continue

        check_in_utc = rec.get('check_in')
        check_out    = rec.get('check_out')

        if not check_in_utc:
            continue

        # Only alert if check_in exists AND check_out is missing/False
        if check_out and check_out is not False:
            continue

        state_key = f"evening_{target}_{emp_id}"
        if not TEST_EMAIL and state_key in state:
            logger.info("  %s — already alerted this evening (%s), skipping",
                        emp_name, state[state_key])
            continue

        check_in_vet = utc_to_vet(check_in_utc)
        subject      = f"⏰ Registro de salida pendiente — {target.strftime('%d/%m/%Y')}"
        body_html    = build_evening_email(emp_name, check_in_vet, target)

        logger.info("  ALERT evening: %s <%s> check_in=%s check_out=missing",
                    emp_name, emp_email,
                    check_in_vet.strftime('%H:%M') if check_in_vet else '?')

        queue_email(emp_email, subject, body_html)
        if not DRY_RUN and not TEST_EMAIL:
            state[state_key] = datetime.now().isoformat()
        sent += 1

    return sent

# ============================================================================
# Morning mode: yesterday's recap
# ============================================================================

def run_morning(employees, state, holidays):
    yesterday = today_vet() - timedelta(days=1)
    logger.info("Morning mode — recap for VET date: %s", yesterday)

    if yesterday in holidays:
        logger.info("Yesterday (%s) was a holiday — skipping morning recap", yesterday)
        return 0

    employee_ids = [e['id'] for e in employees]
    attendance   = get_attendance_for_date(employee_ids, yesterday)
    logger.info("  Attendance records found for yesterday: %d", len(attendance))

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
            elif not is_special and float(worked_hours) < MIN_WORKED_HOURS:
                # Short hours
                check_out_vet = utc_to_vet(check_out_val if isinstance(check_out_val, str)
                                           else str(check_out_val))
                check_out_str = check_out_vet.strftime('%H:%M') if check_out_vet else '—'
                issues.append({
                    'icon': '🟢', 'label': 'Entrada', 'value': check_in_str,
                })
                issues.append({
                    'icon': '🟡', 'label': 'Salida', 'value': check_out_str,
                })
                issues.append({
                    'icon': '⚠️', 'label': 'Horas trabajadas',
                    'value': f"{float(worked_hours):.1f}h (mínimo {MIN_WORKED_HOURS:.1f}h)",
                })

        if not issues:
            logger.debug("  %s — no issues for %s", emp_name, yesterday)
            continue

        subject   = f"📋 Resumen de asistencia — {yesterday.strftime('%d/%m/%Y')}"
        body_html = build_morning_email(emp_name, issues, yesterday)

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
        sent = run_morning(employees, state, holidays)
    else:
        sent = run_evening(employees, state, holidays)

    # Trigger mail queue if any emails were queued
    if sent > 0:
        trigger_mail_queue()

    # Save state
    save_state(state)

    print()
    print('=' * 65)
    print('SUMMARY')
    print('=' * 65)
    print(f"  Mode     : {mode}")
    print(f"  Sent     : {sent} email(s)")
    print(f"  DRY_RUN  : {DRY_RUN}")
    print()


if __name__ == '__main__':
    main()
