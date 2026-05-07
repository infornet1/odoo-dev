#!/usr/bin/env python3
"""
sync_mikrotik_attendance.py
────────────────────────────
Phase 1 — Mikrotik hotspot → Odoo hr.attendance bridge.

Runs AFTER sync_control_asistencia.py (same cron, 18:30 VET).
For each employee whose device is connected to the school hotspot with
sufficient uptime, creates an hr.attendance record if none exists yet.

Priority rule: control_asistencias records (or any existing record) always win.
This script only fills the gap for employees NOT covered by other sources
(primarily admin/maintenance staff like ZARETH FARIAS, MARIELA PRADO, etc.).

Confidence criteria:
  - Username maps to a known Odoo employee (via wifi_hotspot_users table OR
    dynamic generation from employee name using username_helper.py)
  - login_time (= poll_time - uptime) is before MAX_LOGIN_VET_HOUR (14:00)
  - uptime >= MIN_UPTIME_MINUTES (120 min = 2 hours)
  - Username is not a guest or lab computer

Usage:
    python3 scripts/sync_mikrotik_attendance.py              # dry run, today VET
    python3 scripts/sync_mikrotik_attendance.py --live        # apply changes
    python3 scripts/sync_mikrotik_attendance.py --date 2026-05-07
    python3 scripts/sync_mikrotik_attendance.py --min-uptime 90

CRON (runs after sync_control_asistencia.py):
    35 22 * * 1-5  root  cd /var/www/dev/odoo_api_bridge && source odoo_env/bin/activate &&
        python3 /opt/odoo-dev/scripts/sync_mikrotik_attendance.py --live
"""

import argparse
import json
import re
import sys
import xmlrpc.client
from datetime import date, datetime, timedelta

import pymysql

# ─── Configuration ────────────────────────────────────────────────────────────

VET_TO_UTC = timedelta(hours=4)
VET_OFFSET  = timedelta(hours=-4)

# Confidence thresholds
MIN_UPTIME_MINUTES = 120   # 2 hours minimum session uptime
MAX_LOGIN_VET_HOUR = 14    # must have connected before 14:00 VET

# Standard school hours for created attendance records (same as control_asistencias)
CHECK_IN_VET  = (7,  0)
CHECK_OUT_VET = (13, 30)
WORKED_HOURS  = 6.5

WIFI_DB = {
    'host': 'localhost', 'port': 3306,
    'user': 'bcv_script', 'password': 'oCurrency*1',
    'database': 'payroll_db', 'charset': 'utf8mb4',
}

MIKROTIK_HOST = '172.28.10.10'
MIKROTIK_USER = 'odooapi'
MIKROTIK_PASS = 'Steam*1'

ODOO_CFG_PATH = '/opt/odoo-dev/config/production.json'
ALERT_TO      = 'recursoshumanos@ueipab.edu.ve'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def today_vet() -> date:
    return (datetime.utcnow() - timedelta(hours=4)).date()


def now_vet() -> datetime:
    return datetime.utcnow() + VET_OFFSET


def fmt_dt(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def parse_uptime(uptime_str: str) -> int:
    """Convert Mikrotik uptime string to total minutes.
    Examples: '5h22m3s' → 322, '1w6d5h49m31s' → huge, '47m39s' → 47
    """
    total = 0
    for val, unit in re.findall(r'(\d+)([wdhms])', uptime_str):
        v = int(val)
        if unit == 'w':  total += v * 7 * 24 * 60
        elif unit == 'd': total += v * 24 * 60
        elif unit == 'h': total += v * 60
        elif unit == 'm': total += v
        # seconds ignored for minute-level precision
    return total


def vet_times(d: date):
    ci = datetime(d.year, d.month, d.day, CHECK_IN_VET[0],  CHECK_IN_VET[1])  + VET_TO_UTC
    co = datetime(d.year, d.month, d.day, CHECK_OUT_VET[0], CHECK_OUT_VET[1]) + VET_TO_UTC
    return ci, co


def is_excluded(username: str) -> bool:
    """Exclude guests, lab computers, and shared accounts."""
    u = username.lower()
    return (u == 'invitado' or u.startswith('laptop') or
            u.startswith('cel_') or u == 'admin' or u == 'test')


# ─── Step 1: Build employee → username mapping ────────────────────────────────

def load_wifi_db_map() -> dict:
    """Load explicit registrations from wifi_hotspot_users table.
    Returns {username_lower: email}.
    """
    conn = pymysql.connect(**WIFI_DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT hotspot_username, odoo_login
                FROM wifi_hotspot_users
                WHERE user_category = 'odoo_user' AND enabled = 1
            """)
            return {row[0].lower(): row[1] for row in cur.fetchall()}
    finally:
        conn.close()


def load_odoo_employees(models, db, uid, api_key) -> list:
    """Load all active employees from Odoo production."""
    return models.execute_kw(db, uid, api_key, 'hr.employee', 'search_read',
                             [[['active', '=', True]]],
                             {'fields': ['id', 'name', 'work_email']})


def build_username_map(employees: list, wifi_db_map: dict) -> dict:
    """Build complete {username_lower: email} map.
    Priority: wifi_db_map (explicit) > derived from employee name.
    """
    sys.path.insert(0, '/var/www/dev/odoo_api_bridge')
    try:
        from username_helper import generate_hotspot_usernames
        has_helper = True
    except ImportError:
        has_helper = False
        print("  WARNING: username_helper not available — using wifi_db_map only")

    mapping = {}

    # 1. Derived from Odoo employee names (lower priority)
    if has_helper:
        for emp in employees:
            if not emp.get('work_email'):
                continue
            try:
                usernames = generate_hotspot_usernames(emp['name'])
                for uname in usernames.values():
                    if uname and uname.lower() not in mapping:
                        mapping[uname.lower()] = emp['work_email']
            except Exception:
                pass

    # 2. Explicit registrations override (higher priority)
    mapping.update(wifi_db_map)

    return mapping


# ─── Step 2: Query Mikrotik active sessions ───────────────────────────────────

def get_active_sessions() -> list:
    """Returns list of dicts with user, uptime_minutes, mac."""
    sys.path.insert(0, '/var/www/dev/odoo_api_bridge')
    from mikrotik_manager import MikrotikManager

    mgr = MikrotikManager(
        host=MIKROTIK_HOST,
        username=MIKROTIK_USER,
        password=MIKROTIK_PASS,
    )
    if not mgr.connect():
        raise RuntimeError(f"Cannot connect to Mikrotik at {MIKROTIK_HOST}")

    stdout, stderr, rc = mgr._execute_command(
        '/ip hotspot active print detail without-paging'
    )
    mgr.disconnect()

    sessions = []
    current = {}
    for line in stdout.splitlines():
        line = line.strip()
        # New session block starts with a number
        if re.match(r'^\d+\s', line) or re.match(r'^;;;\s', line):
            if current.get('user'):
                sessions.append(current)
            current = {}
            # Parse inline fields on the same line
            m = re.search(r'user="([^"]+)"', line)
            if m:
                current['user'] = m.group(1)
            m = re.search(r'uptime=(\S+)', line)
            if m:
                current['uptime_str'] = m.group(1)
                current['uptime_min'] = parse_uptime(m.group(1))
            m = re.search(r'mac-address=(\S+)', line)
            if m:
                current['mac'] = m.group(1)
        else:
            # Continuation line — parse remaining fields
            if not current.get('user'):
                m = re.search(r'user="([^"]+)"', line)
                if m:
                    current['user'] = m.group(1)
            if not current.get('uptime_str'):
                m = re.search(r'uptime=(\S+)', line)
                if m:
                    current['uptime_str'] = m.group(1)
                    current['uptime_min'] = parse_uptime(m.group(1))
            if not current.get('mac'):
                m = re.search(r'mac-address=(\S+)', line)
                if m:
                    current['mac'] = m.group(1)

    if current.get('user'):
        sessions.append(current)

    return sessions


# ─── Step 3: Apply confidence criteria ───────────────────────────────────────

def check_confidence(session: dict, poll_time_vet: datetime,
                     min_uptime: int, max_login_hour: int) -> tuple:
    """
    Returns (passes: bool, reason: str).
    login_time = poll_time_vet - uptime
    """
    uptime = session.get('uptime_min', 0)

    if uptime < min_uptime:
        return False, f"uptime {uptime}min < {min_uptime}min threshold"

    login_vet = poll_time_vet - timedelta(minutes=uptime)
    if login_vet.hour >= max_login_hour:
        login_str = login_vet.strftime('%H:%M')
        return False, f"login at {login_str} VET >= {max_login_hour:02d}:00 cutoff"

    return True, f"login ~{login_vet.strftime('%H:%M')} VET, uptime {uptime}min"


# ─── Step 4: Odoo XML-RPC backend ────────────────────────────────────────────

def connect_odoo():
    with open(ODOO_CFG_PATH) as f:
        cfg = json.load(f)['production']['xmlrpc']
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg['db'], cfg['user'], cfg['api_key'], {})
    if not uid:
        raise RuntimeError("XML-RPC authentication failed")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")
    return models, cfg['db'], uid, cfg['api_key']


def has_attendance(models, db, uid, api_key, emp_id: int, target_date: date) -> bool:
    count = models.execute_kw(db, uid, api_key, 'hr.attendance', 'search_count', [[
        ['employee_id', '=', emp_id],
        ['check_in', '>=', fmt_dt(datetime.combine(target_date, datetime.min.time()))],
        ['check_in', '<',  fmt_dt(datetime.combine(target_date + timedelta(days=1), datetime.min.time()))],
    ]])
    return count > 0


def create_attendance(models, db, uid, api_key, emp_id: int, ci_utc, co_utc):
    try:
        return models.execute_kw(db, uid, api_key, 'hr.attendance', 'create', [{
            'employee_id':  emp_id,
            'check_in':     fmt_dt(ci_utc),
            'check_out':    fmt_dt(co_utc),
            'worked_hours': WORKED_HOURS,
        }])
    except xmlrpc.client.Fault as e:
        if 'ya registr' in str(e) or 'overlap' in str(e).lower():
            return None
        raise


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Mikrotik hotspot → Odoo hr.attendance (Phase 1)'
    )
    parser.add_argument('--live',        action='store_true')
    parser.add_argument('--date',        default=None, help='YYYY-MM-DD (default: today VET)')
    parser.add_argument('--min-uptime',  type=int, default=MIN_UPTIME_MINUTES,
                        help=f'Min uptime in minutes (default: {MIN_UPTIME_MINUTES})')
    parser.add_argument('--max-login-hour', type=int, default=MAX_LOGIN_VET_HOUR,
                        help=f'Max login hour VET (default: {MAX_LOGIN_VET_HOUR})')
    args = parser.parse_args()

    dry_run     = not args.live
    target_date = date.fromisoformat(args.date) if args.date else today_vet()
    poll_time   = now_vet()
    banner      = 'DRY RUN' if dry_run else 'LIVE'

    print(f"[{banner}] sync_mikrotik_attendance | date={target_date} | poll={poll_time.strftime('%H:%M')} VET")
    print(f"  Confidence: uptime >= {args.min_uptime}min, login before {args.max_login_hour:02d}:00 VET")
    print('─' * 60)

    # ── 1. Load employee → username mapping ───────────────────────────────────
    print("Loading employee mapping...")
    models, db, uid, api_key = connect_odoo()
    employees = load_odoo_employees(models, db, uid, api_key)
    wifi_db_map = load_wifi_db_map()
    username_map = build_username_map(employees, wifi_db_map)

    # Build email → employee_id map for Odoo lookups
    emp_by_email = {e['work_email']: e for e in employees if e.get('work_email')}

    print(f"  {len(employees)} Odoo employees | {len(username_map)} username mappings | {len(wifi_db_map)} explicit registrations")

    # ── 2. Get active Mikrotik sessions ───────────────────────────────────────
    print("\nQuerying Mikrotik active sessions...")
    try:
        sessions = get_active_sessions()
    except Exception as e:
        print(f"ERROR: Cannot get Mikrotik sessions: {e}")
        sys.exit(1)

    print(f"  {len(sessions)} active sessions found")

    # ── 3. Process sessions ───────────────────────────────────────────────────
    ci_utc, co_utc = vet_times(target_date)
    created, skipped_existing, skipped_confidence, no_match = [], [], [], []
    seen_emails = set()  # deduplicate: one record per employee

    print()
    for s in sessions:
        username = s.get('user', '')
        if not username or is_excluded(username):
            continue

        # Match username to employee email
        email = username_map.get(username.lower())
        if not email:
            continue  # not an employee user

        if email in seen_emails:
            continue  # already processed this employee (other device)
        seen_emails.add(email)

        emp = emp_by_email.get(email)
        if not emp:
            no_match.append((username, email))
            continue

        emp_id   = emp['id']
        emp_name = emp['name']

        # Check confidence
        passes, reason = check_confidence(s, poll_time, args.min_uptime, args.max_login_hour)
        if not passes:
            print(f"  LOW CONF  {emp_name:<30} [{username}] — {reason}")
            skipped_confidence.append((emp_name, username, reason))
            continue

        # Check existing attendance
        if has_attendance(models, db, uid, api_key, emp_id, target_date):
            print(f"  SKIP      {emp_name:<30} [{username}] — record exists")
            skipped_existing.append((emp_name, email))
            continue

        # Create attendance
        if dry_run:
            print(f"  [DRY]     {emp_name:<30} [{username}] — {reason}")
        else:
            att_id = create_attendance(models, db, uid, api_key, emp_id, ci_utc, co_utc)
            if att_id is None:
                print(f"  SKIP      {emp_name:<30} [{username}] — overlap (ORM)")
                skipped_existing.append((emp_name, email))
            else:
                print(f"  ✅        {emp_name:<30} [{username}] — id={att_id} | {reason}")
                created.append((emp_name, email, username, att_id))

    # ── 4. Summary ────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"Summary | {target_date} | [{banner}]")
    print(f"  Active sessions processed    : {len(seen_emails)}")
    print(f"  Records created              : {len(created) if not dry_run else 'N/A (dry)'}")
    print(f"  Skipped (record existed)     : {len(skipped_existing)}")
    print(f"  Skipped (low confidence)     : {len(skipped_confidence)}")
    print(f"  No Odoo match                : {len(no_match)}")

    if skipped_confidence:
        print("\n  Low confidence detail:")
        for name, uname, reason in skipped_confidence:
            print(f"    {name} [{uname}]: {reason}")

    if not dry_run and created:
        _send_summary_email(models, db, uid, api_key,
                            target_date, created, skipped_existing, skipped_confidence)
    elif dry_run:
        print("\n  → Run with --live to apply changes.")


# ─── Email summary ────────────────────────────────────────────────────────────

def _send_summary_email(models, db, uid, api_key, target_date, created, skipped, low_conf):
    def rows(items, fmt):
        return ''.join(f'<tr>{fmt(i)}</tr>' for i in items) or '<tr><td>(ninguno)</td></tr>'

    body = f"""
<p>Estimados Recursos Humanos,</p>
<p>Resumen de sincronizaci&#243;n autom&#225;tica v&#237;a <strong>WiFi Hotspot Mikrotik</strong>
para el <strong>{target_date.strftime('%d/%m/%Y')}</strong>.
Solo se crean registros para empleados sin asistencia registrada por otras fuentes.</p>

<h3 style="color:#155724;">&#9989; Registros creados ({len(created)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#d4edda;"><th>Empleado</th><th>Usuario WiFi</th><th>Horario</th></tr>
{rows(created, lambda i: f'<td>{i[0]}</td><td>{i[2]}</td><td>07:00&#8594;13:30 (VET)</td>')}
</table>

<h3 style="color:#856404;">&#9197; Omitidos &#8212; ya ten&#237;an registro ({len(skipped)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#fff3cd;"><th>Empleado</th></tr>
{rows(skipped, lambda i: f'<td>{i[0]}</td>')}
</table>

<h3 style="color:#6c757d;">&#128312; Baja confianza &#8212; no procesados ({len(low_conf)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#f8f9fa;"><th>Empleado</th><th>Usuario</th><th>Motivo</th></tr>
{rows(low_conf, lambda i: f'<td>{i[0]}</td><td>{i[1]}</td><td>{i[2]}</td>')}
</table>

<p style="color:#888;font-size:11px;margin-top:20px;">
Generado por sync_mikrotik_attendance.py &#8212;
Fuente: Hotspot MikroTik hAP ac&#179; (172.28.10.10) &#8212;
{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
</p>
"""
    models.execute_kw(db, uid, api_key, 'mail.mail', 'create', [{
        'subject':    f"Asistencia WiFi Hotspot {target_date.strftime('%d/%m/%Y')} — Mikrotik Sync",
        'email_from': 'recursoshumanos@ueipab.edu.ve',
        'email_to':   ALERT_TO,
        'body_html':  body,
        'auto_delete': True,
        'state':      'outgoing',
    }])
    print(f"  Summary email queued → {ALERT_TO}")


if __name__ == '__main__':
    main()
