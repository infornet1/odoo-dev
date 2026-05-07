#!/usr/bin/env python3
"""
sync_control_asistencia.py
──────────────────────────
Daily bridge: control_asistencias → Odoo hr.attendance

For each teacher who submitted student attendance records in control_asistencias
on the target date, creates an hr.attendance record in Odoo (if one doesn't
already exist for that day).

Since there is no biometric system, this IS the attendance source for teachers.

Usage:
    python3 scripts/sync_control_asistencia.py              # dry run, testing, today VET
    python3 scripts/sync_control_asistencia.py --live        # apply changes
    python3 scripts/sync_control_asistencia.py --date 2026-05-06
    python3 scripts/sync_control_asistencia.py --env production --live

CRON (add to /etc/cron.d/):
    30 22 * * 1-5  root  /usr/bin/python3 /opt/odoo-dev/scripts/sync_control_asistencia.py --live --env production
    # 22:30 UTC = 18:30 VET — after school day ends, weekdays only
"""

import argparse
import json
import subprocess
import sys
import textwrap
from datetime import date, datetime, timedelta

import pymysql
import psycopg2

# ─── Constants ────────────────────────────────────────────────────────────────

VET_TO_UTC = timedelta(hours=4)  # VET = UTC-4 → add 4h to get UTC

# Default school hours in VET used when auto-creating attendance records.
# No biometric → we use standard morning schedule as proxy.
CHECK_IN_VET  = (7, 0)    # 07:00 VET → 11:00 UTC
CHECK_OUT_VET = (13, 30)  # 13:30 VET → 17:30 UTC
WORKED_HOURS  = 6.5       # 13:30 - 07:00

MYSQL_CFG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'control_asist',
    'password': 'y3deTsi92HrQgj0wgvVx',
    'database': 'control_asistencias',
    'charset':  'utf8mb4',
}

ODOO_ENVS = {
    'testing': {
        'pg_host':   'localhost',
        'pg_port':   5433,          # exposed from odoo-dev-postgres container
        'pg_db':     'testing',
        'pg_user':   'odoo',
        'pg_pass':   'odoo8069',
        'container': 'odoo-dev-web',
        'odoo_db':   'testing',
    },
    'production': {
        # Requires SSH tunnel before running:
        # ssh -L 5434:localhost:5432 root@10.124.0.3 -N -f
        'pg_host':   'localhost',
        'pg_port':   5434,
        'pg_db':     'DB_UEIPAB',
        'pg_user':   'odoo',
        'pg_pass':   'odoo8069',
        'container': '0ef7d03db702_ueipab17',
        'odoo_db':   'DB_UEIPAB',
    },
}

ALERT_TO = 'recursoshumanos@ueipab.edu.ve'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def vet_times(d: date):
    """Return (check_in_utc, check_out_utc) datetimes for a VET school day."""
    ci = datetime(d.year, d.month, d.day, CHECK_IN_VET[0],  CHECK_IN_VET[1])  + VET_TO_UTC
    co = datetime(d.year, d.month, d.day, CHECK_OUT_VET[0], CHECK_OUT_VET[1]) + VET_TO_UTC
    return ci, co


def today_vet() -> date:
    return (datetime.utcnow() - timedelta(hours=4)).date()


# ─── Step 1 — Query control_asistencias ───────────────────────────────────────

def get_teachers_who_submitted(target_date: date) -> dict:
    """
    Returns {email: (ctrl_id, full_name)} for every teacher who submitted
    student attendance records for target_date.
    """
    conn = pymysql.connect(**MYSQL_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT u.id_usuario,
                       CONCAT(u.nombre, ' ', u.apellido) AS full_name,
                       u.email
                FROM asistencia_estudiante ae
                JOIN usuario u ON ae.id_usuario = u.id_usuario
                WHERE ae.fecha = %s
                  AND u.email IS NOT NULL
                  AND u.email != ''
                  AND u.activo = 1
            """, (target_date,))
            return {row[2]: (row[0], row[1]) for row in cur.fetchall()}
    finally:
        conn.close()


# ─── Step 2 — Odoo operations via psycopg2 ────────────────────────────────────

def connect_odoo_pg(env_cfg: dict):
    return psycopg2.connect(
        host=env_cfg['pg_host'], port=env_cfg['pg_port'],
        dbname=env_cfg['pg_db'], user=env_cfg['pg_user'],
        password=env_cfg['pg_pass'],
    )


def get_employee_map(cur, emails: list) -> dict:
    """Returns {email: (employee_id, name)} for active Odoo employees."""
    if not emails:
        return {}
    cur.execute("""
        SELECT id, name, work_email
        FROM hr_employee
        WHERE work_email = ANY(%s) AND active = TRUE
    """, (emails,))
    return {row[2]: (row[0], row[1]) for row in cur.fetchall()}


def has_attendance_today(cur, employee_id: int, target_date: date) -> bool:
    cur.execute("""
        SELECT id FROM hr_attendance
        WHERE employee_id = %s
          AND check_in::date = %s
        LIMIT 1
    """, (employee_id, target_date))
    return cur.fetchone() is not None


def create_attendance(cur, employee_id: int, ci_utc: datetime, co_utc: datetime) -> int:
    cur.execute("""
        INSERT INTO hr_attendance (employee_id, check_in, check_out, worked_hours)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (employee_id, ci_utc, co_utc, WORKED_HOURS))
    return cur.fetchone()[0]


# ─── Step 3 — Summary email via Odoo mail system ──────────────────────────────

def send_summary_email(env_cfg: dict, target_date: date, created, skipped, no_match):
    def rows(items, fmt):
        return ''.join(f'<tr>{fmt(i)}</tr>' for i in items) or '<tr><td colspan="2">(ninguno)</td></tr>'

    body = f"""
<p>Estimados Recursos Humanos,</p>
<p>Resumen de sincronizaci&#243;n autom&#225;tica de asistencia docente
para el <strong>{target_date.strftime('%d/%m/%Y')}</strong>
(fuente: Sistema Control de Asistencias).</p>

<h3 style="color:#155724;">&#9989; Registros creados en Odoo ({len(created)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#d4edda;"><th>Docente</th><th>Horario registrado</th></tr>
{rows(created, lambda i: f'<td>{i[0]}</td><td>07:00 &#8594; 13:30 (VET)</td>')}
</table>

<h3 style="color:#856404;">&#9197; Omitidos &#8212; ya ten&#237;an registro ({len(skipped)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#fff3cd;"><th>Docente</th><th>Email</th></tr>
{rows(skipped, lambda i: f'<td>{i[0]}</td><td>{i[1]}</td>')}
</table>

<h3 style="color:#721c24;">&#9888;&#65039; Sin coincidencia en Odoo ({len(no_match)})</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
<tr style="background:#fde8e8;"><th>Email control_asistencias</th></tr>
{rows(no_match, lambda e: f'<td>{e}</td>')}
</table>

<p style="color:#888;font-size:11px;margin-top:20px;">
Generado autom&#225;ticamente por sync_control_asistencia.py &#8212;
{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
</p>
"""

    script = textwrap.dedent(f"""
mail = env['mail.mail'].sudo().create({{
    'subject': 'Asistencia Docente {target_date.strftime("%d/%m/%Y")} — Sync Control Asistencias',
    'email_from': 'recursoshumanos@ueipab.edu.ve',
    'email_to': '{ALERT_TO}',
    'body_html': {json.dumps(body)},
    'auto_delete': True,
}})
mail.send()
env.cr.commit()
print('email_sent')
""")

    result = subprocess.run(
        ['docker', 'exec', '-i', env_cfg['container'],
         '/usr/bin/odoo', 'shell', '-d', env_cfg['odoo_db'], '--no-http'],
        input=script.encode(),
        capture_output=True, timeout=90,
    )
    if b'email_sent' in result.stdout:
        print(f"Summary email sent to {ALERT_TO}")
    else:
        print(f"Email may have failed. Stderr snippet: {result.stderr[-300:].decode(errors='replace')}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Sync control_asistencias teacher activity → Odoo hr.attendance'
    )
    parser.add_argument('--live', action='store_true',
                        help='Apply changes (default: dry run)')
    parser.add_argument('--date', default=None,
                        help='Date to process YYYY-MM-DD (default: today VET)')
    parser.add_argument('--env', default='testing',
                        choices=['testing', 'production'])
    args = parser.parse_args()

    dry_run     = not args.live
    target_env  = args.env
    target_date = date.fromisoformat(args.date) if args.date else today_vet()
    env_cfg     = ODOO_ENVS[target_env]

    banner = 'DRY RUN' if dry_run else 'LIVE'
    print(f"[{banner}] sync_control_asistencia | date={target_date} | env={target_env}")
    print('─' * 60)

    # ── 1. Get teachers who submitted today ───────────────────────────────────
    teachers = get_teachers_who_submitted(target_date)
    print(f"Submitted in control_asistencias on {target_date}: {len(teachers)}")
    for email, (_, name) in teachers.items():
        print(f"  • {name} <{email}>")

    if not teachers:
        print("No teacher submissions found for this date.")
        if not dry_run:
            send_summary_email(env_cfg, target_date, [], [], [])
        return

    # ── 2. Connect to Odoo postgres ───────────────────────────────────────────
    try:
        pg = connect_odoo_pg(env_cfg)
    except Exception as e:
        print(f"ERROR: Cannot connect to Odoo postgres ({target_env}): {e}")
        if target_env == 'production':
            print("Tip: Set up SSH tunnel first:")
            print("  ssh -L 5434:localhost:5432 root@10.124.0.3 -N -f")
        sys.exit(1)

    cur = pg.cursor()

    # ── 3. Map emails → Odoo employees ───────────────────────────────────────
    emp_map  = get_employee_map(cur, list(teachers.keys()))
    no_match = [e for e in teachers if e not in emp_map]

    if no_match:
        print(f"\nWARNING — {len(no_match)} teacher(s) have no Odoo employee match:")
        for e in no_match:
            print(f"  ⚠  {e}")

    # ── 4. Create attendance records ──────────────────────────────────────────
    ci_utc, co_utc = vet_times(target_date)
    created = []
    skipped = []

    print(f"\nProcessing {len(emp_map)} matched employees:")
    for email, (ctrl_id, ctrl_name) in teachers.items():
        if email not in emp_map:
            continue
        emp_id, emp_name = emp_map[email]

        if has_attendance_today(cur, emp_id, target_date):
            print(f"  SKIP  {emp_name} — record exists for {target_date}")
            skipped.append((emp_name, email))
            continue

        if dry_run:
            print(f"  [DRY] {emp_name} — would create 07:00→13:30 VET ({ci_utc}→{co_utc} UTC)")
        else:
            att_id = create_attendance(cur, emp_id, ci_utc, co_utc)
            print(f"  ✅   {emp_name} — attendance id={att_id}")
            created.append((emp_name, email, att_id))

    if not dry_run:
        pg.commit()
    pg.close()

    # ── 5. Print summary ──────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"Summary | {target_date} | [{banner}] | env={target_env}")
    print(f"  Submitted in control_asistencias : {len(teachers)}")
    print(f"  Matched to Odoo employees        : {len(emp_map)}")
    print(f"  Attendance records created       : {len(created) if not dry_run else 'N/A (dry)'}")
    print(f"  Skipped (record already existed) : {len(skipped)}")
    print(f"  No Odoo match (warning)          : {len(no_match)}")

    if not dry_run:
        send_summary_email(env_cfg, target_date, created, skipped, no_match)
    else:
        print("\n  → Run with --live to apply changes.")


if __name__ == '__main__':
    main()
