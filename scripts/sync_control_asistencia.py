#!/usr/bin/env python3
"""
sync_control_asistencia.py
──────────────────────────
Daily bridge: control_asistencias → Odoo hr.attendance

For each teacher who submitted student attendance records in control_asistencias
on the target date, creates an hr.attendance record in Odoo (if one doesn't
already exist for that day). No biometric system required — class submission
proves teacher presence.

Backends:
  testing    → psycopg2 direct to local postgres (port 5433)
  production → XML-RPC to https://odoo.ueipab.edu.ve

Usage:
    python3 scripts/sync_control_asistencia.py              # dry run, testing, today VET
    python3 scripts/sync_control_asistencia.py --live        # apply changes
    python3 scripts/sync_control_asistencia.py --date 2026-05-06
    python3 scripts/sync_control_asistencia.py --env production --live

CRON (/etc/cron.d/sync_control_asistencia):
    30 22 * * 1-5  root  /usr/bin/python3 /opt/odoo-dev/scripts/sync_control_asistencia.py --live --env production
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
import xmlrpc.client
from datetime import date, datetime, timedelta

import pymysql
import psycopg2

# ─── Constants ────────────────────────────────────────────────────────────────

VET_TO_UTC = timedelta(hours=4)   # VET = UTC-4

# School hours in VET used when auto-creating attendance records
CHECK_IN_VET  = (7,  0)    # 07:00 VET → 11:00 UTC
CHECK_OUT_VET = (13, 30)   # 13:30 VET → 17:30 UTC
WORKED_HOURS  = 6.5        # 13:30 - 07:00

MYSQL_CFG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'control_asist',
    'password': 'y3deTsi92HrQgj0wgvVx',
    'database': 'control_asistencias',
    'charset':  'utf8mb4',
}

# Testing uses direct psycopg2; production uses XML-RPC loaded from config
PG_TESTING = {
    'host': 'localhost', 'port': 5433,
    'dbname': 'testing', 'user': 'odoo', 'password': 'odoo8069',
    'container': 'odoo-dev-web', 'odoo_db': 'testing',
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'production.json')

ALERT_TO = 'recursoshumanos@ueipab.edu.ve'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_prod_config():
    with open(os.path.abspath(CONFIG_PATH)) as f:
        return json.load(f)['production']['xmlrpc']


def vet_times(d: date):
    ci = datetime(d.year, d.month, d.day, CHECK_IN_VET[0],  CHECK_IN_VET[1])  + VET_TO_UTC
    co = datetime(d.year, d.month, d.day, CHECK_OUT_VET[0], CHECK_OUT_VET[1]) + VET_TO_UTC
    return ci, co


def today_vet() -> date:
    return (datetime.utcnow() - timedelta(hours=4)).date()


def fmt_dt(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# ─── MySQL: teachers who submitted today ──────────────────────────────────────

def get_teachers_who_submitted(target_date: date) -> dict:
    """Returns {email: (ctrl_id, full_name)} for teachers who submitted on target_date."""
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
                  AND u.email IS NOT NULL AND u.email != ''
                  AND u.activo = 1
            """, (target_date,))
            return {row[2]: (row[0], row[1]) for row in cur.fetchall()}
    finally:
        conn.close()


# ─── Backend: psycopg2 (testing) ─────────────────────────────────────────────

class PsycopgBackend:
    def __init__(self):
        self.pg = psycopg2.connect(
            host=PG_TESTING['host'], port=PG_TESTING['port'],
            dbname=PG_TESTING['dbname'], user=PG_TESTING['user'],
            password=PG_TESTING['password'],
        )
        self.cur = self.pg.cursor()

    def get_employee_map(self, emails):
        self.cur.execute(
            "SELECT id, name, work_email FROM hr_employee WHERE work_email = ANY(%s) AND active = TRUE",
            (emails,)
        )
        return {row[2]: (row[0], row[1]) for row in self.cur.fetchall()}

    def has_attendance(self, emp_id, target_date):
        self.cur.execute(
            "SELECT id FROM hr_attendance WHERE employee_id = %s AND check_in::date = %s LIMIT 1",
            (emp_id, target_date)
        )
        return self.cur.fetchone() is not None

    def create_attendance(self, emp_id, ci_utc, co_utc):
        # Guard: never insert a dangling open row (NULL check_out) — that is the
        # exact bug that left null-audit ghost rows in prod (see
        # documentation/ATTENDANCE_DANGLING_OPEN_RECORDS.md).
        if not co_utc:
            raise ValueError(
                "refusing to insert attendance with NULL check_out (emp=%s, in=%s)"
                % (emp_id, ci_utc))
        # Raw SQL bypasses the ORM, so stamp the audit columns ourselves
        # (create_uid=1 = superuser); otherwise the row has NULL create_date and
        # is indistinguishable from a manual/ghost insert.
        self.cur.execute("""
            INSERT INTO hr_attendance
                (employee_id, check_in, check_out, worked_hours,
                 create_uid, write_uid, create_date, write_date)
            VALUES (%s, %s, %s, %s, 1, 1,
                    (now() AT TIME ZONE 'UTC'), (now() AT TIME ZONE 'UTC'))
            RETURNING id
        """, (emp_id, ci_utc, co_utc, WORKED_HOURS))
        return self.cur.fetchone()[0]

    def commit(self):
        self.pg.commit()

    def close(self):
        self.pg.close()

    def send_email(self, target_date, created, skipped, no_match):
        """Send via Odoo shell (docker exec) — reuses local mail server config."""
        body = _build_email_body(target_date, created, skipped, no_match)
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
            ['docker', 'exec', '-i', PG_TESTING['container'],
             '/usr/bin/odoo', 'shell', '-d', PG_TESTING['odoo_db'], '--no-http'],
            input=script.encode(), capture_output=True, timeout=90,
        )
        return b'email_sent' in result.stdout


# ─── Backend: XML-RPC (production) ───────────────────────────────────────────

class XmlRpcBackend:
    def __init__(self):
        cfg = load_prod_config()
        self.db      = cfg['db']
        self.api_key = cfg['api_key']
        common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, cfg['user'], self.api_key, {})
        if not self.uid:
            raise RuntimeError("XML-RPC authentication failed for production")
        self.models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")

    def _call(self, model, method, args, kwargs=None):
        return self.models.execute_kw(
            self.db, self.uid, self.api_key,
            model, method, args, kwargs or {}
        )

    def get_employee_map(self, emails):
        recs = self._call('hr.employee', 'search_read',
                          [[['work_email', 'in', emails], ['active', '=', True]]],
                          {'fields': ['id', 'name', 'work_email']})
        return {r['work_email']: (r['id'], r['name']) for r in recs}

    def has_attendance(self, emp_id, target_date):
        count = self._call('hr.attendance', 'search_count', [[
            ['employee_id', '=', emp_id],
            ['check_in', '>=', fmt_dt(datetime.combine(target_date, datetime.min.time()))],
            ['check_in', '<',  fmt_dt(datetime.combine(target_date + timedelta(days=1), datetime.min.time()))],
        ]])
        return count > 0

    def create_attendance(self, emp_id, ci_utc, co_utc):
        try:
            return self._call('hr.attendance', 'create', [{
                'employee_id':  emp_id,
                'check_in':     fmt_dt(ci_utc),
                'check_out':    fmt_dt(co_utc),
                'worked_hours': WORKED_HOURS,
            }])
        except xmlrpc.client.Fault as e:
            if 'ya registr' in str(e) or 'overlap' in str(e).lower():
                return None  # existing record detected via ORM constraint — skip
            raise

    def commit(self):
        pass  # XML-RPC auto-commits

    def close(self):
        pass

    def send_email(self, target_date, created, skipped, no_match):
        body = _build_email_body(target_date, created, skipped, no_match)
        self._call('mail.mail', 'create', [{
            'subject':    f"📊 Asistencia Docente {target_date.strftime('%d/%m/%Y')} — {len(created)} creado{'s' if len(created) != 1 else ''}, {len(skipped)} ya registrado{'s' if len(skipped) != 1 else ''}",
            'email_from': 'recursoshumanos@ueipab.edu.ve',
            'email_to':   ALERT_TO,
            'body_html':  body,
            'auto_delete': True,
            'state':      'outgoing',   # queued — Odoo cron delivers within 1 min
        }])
        return True


# ─── Email body builder ───────────────────────────────────────────────────────

def _build_email_body(target_date, created, skipped, no_match):
    logo = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
    date_str = target_date.strftime('%d/%m/%Y')
    total = len(created) + len(skipped)

    def _row_green(item):
        return (f'<tr><td style="padding:7px 10px;border-bottom:1px solid #e0e0e0;">{item[0]}</td>'
                f'<td style="padding:7px 10px;border-bottom:1px solid #e0e0e0;color:#555;">07:00 → 13:30 VET</td></tr>')

    def _row_amber(item):
        return (f'<tr><td style="padding:7px 10px;border-bottom:1px solid #e0e0e0;">{item[0]}</td>'
                f'<td style="padding:7px 10px;border-bottom:1px solid #e0e0e0;color:#888;font-size:12px;">{item[1]}</td></tr>')

    def _row_red(email):
        return f'<tr><td style="padding:7px 10px;border-bottom:1px solid #e0e0e0;color:#721c24;">{email}</td></tr>'

    def _empty_row(cols=2):
        return f'<tr><td colspan="{cols}" style="padding:7px 10px;color:#aaa;font-style:italic;">Ninguno</td></tr>'

    rows_created = ''.join(_row_green(i) for i in created) or _empty_row(2)
    rows_skipped = ''.join(_row_amber(i) for i in skipped) or _empty_row(2)
    rows_nomatch = ''.join(_row_red(e) for e in no_match) or _empty_row(1)

    no_match_section = ''
    if no_match:
        no_match_section = f"""
      <div style="background:#fde8e8;border-left:4px solid #dc3545;border-radius:0 8px 8px 0;
                  padding:14px 18px;margin-bottom:20px;">
        <p style="font-size:13px;font-weight:700;color:#721c24;margin:0 0 8px;">
          ⚠️ Docentes sin cuenta en Odoo ({len(no_match)})
        </p>
        <p style="font-size:12px;color:#721c24;margin:0 0 10px;line-height:1.5;">
          Estos correos aparecen en Control de Asistencias pero no tienen un empleado activo
          en Odoo con esa dirección. Revisar y corregir si corresponde.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr style="background:#fac0c0;">
            <th style="padding:7px 10px;text-align:left;">Email en Control de Asistencias</th>
          </tr>
          {rows_nomatch}
        </table>
      </div>"""

    return f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;
                            padding:16px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;overflow:hidden;
            box-shadow:0 4px 16px rgba(0,0,0,.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);padding:22px 28px;
              display:flex;align-items:center;gap:16px;">
    <img src="{logo}" width="52" height="52"
         style="width:52px;height:52px;border-radius:50%;object-fit:cover;
                border:2px solid rgba(255,255,255,.3);flex-shrink:0;" alt="UEIPAB"/>
    <div>
      <p style="margin:0;color:white;font-size:16px;font-weight:700;">
        Asistencia Docente — {date_str}
      </p>
      <p style="margin:3px 0 0;color:rgba(255,255,255,.8);font-size:12px;">
        Sincronización automática · Sistema Control de Asistencias → Odoo
      </p>
    </div>
  </div>

  <!-- Purpose intro card -->
  <div style="padding:16px 28px 0;">
    <div style="background:#eef4fb;border-left:4px solid #2471a3;border-radius:0 8px 8px 0;
                padding:14px 18px;">
      <p style="font-size:13px;font-weight:700;color:#1a2c5b;margin:0 0 6px;">
        ¿Para qué sirve este correo?
      </p>
      <p style="font-size:12px;color:#374151;line-height:1.75;margin:0;">
        Muchos docentes no pasan por el Kiosco de Odoo, pero sí registran su presencia al tomar
        lista en <strong>Control de Asistencias</strong>. Cada noche, este proceso automático
        detecta esos registros y crea la entrada de asistencia correspondiente en Odoo —
        garantizando que la jornada quede registrada para nómina sin intervención manual.
        Este correo es el reporte de auditoría de ese proceso.
      </p>
    </div>
  </div>

  <!-- Summary chips -->
  <div style="padding:12px 28px 0;display:flex;gap:10px;flex-wrap:wrap;">
    <div style="background:#d4edda;border-radius:20px;padding:6px 16px;font-size:13px;
                font-weight:700;color:#155724;">
      ✅ {len(created)} creado{'s' if len(created) != 1 else ''}
    </div>
    <div style="background:#fff3cd;border-radius:20px;padding:6px 16px;font-size:13px;
                font-weight:700;color:#856404;">
      ⏭ {len(skipped)} ya registrado{'s' if len(skipped) != 1 else ''}
    </div>
    <div style="background:#f0f4fa;border-radius:20px;padding:6px 16px;font-size:13px;
                color:#555;">
      👩‍🏫 {total} docente{'s' if total != 1 else ''} en total
    </div>
  </div>

  <div style="padding:18px 28px 24px;">

    <!-- Created -->
    <div style="margin-bottom:20px;">
      <p style="font-size:13px;font-weight:700;color:#155724;margin:0 0 8px;">
        ✅ Registrados automáticamente hoy ({len(created)})
      </p>
      <p style="font-size:12px;color:#555;margin:0 0 8px;line-height:1.5;">
        Docentes que constan en Control de Asistencias y no tenían registro en Odoo —
        se les creó entrada 07:00 y salida 13:30 VET.
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:13px;
                    border:1px solid #c3e6cb;border-radius:6px;overflow:hidden;">
        <tr style="background:#d4edda;">
          <th style="padding:7px 10px;text-align:left;color:#155724;">Docente</th>
          <th style="padding:7px 10px;text-align:left;color:#155724;">Horario creado</th>
        </tr>
        {rows_created}
      </table>
    </div>

    <!-- Skipped -->
    <div style="margin-bottom:20px;">
      <p style="font-size:13px;font-weight:700;color:#856404;margin:0 0 8px;">
        ⏭ Ya tenían registro propio ({len(skipped)})
      </p>
      <p style="font-size:12px;color:#555;margin:0 0 8px;line-height:1.5;">
        Estos docentes ya marcaron asistencia en Odoo por su cuenta (Kiosco o sistema).
        No se realizó ninguna acción — su registro real se conserva intacto.
      </p>
      <table style="width:100%;border-collapse:collapse;font-size:13px;
                    border:1px solid #ffeeba;border-radius:6px;overflow:hidden;">
        <tr style="background:#fff3cd;">
          <th style="padding:7px 10px;text-align:left;color:#856404;">Docente</th>
          <th style="padding:7px 10px;text-align:left;color:#856404;">Email</th>
        </tr>
        {rows_skipped}
      </table>
    </div>

    <!-- No match (only shown if non-empty) -->
    {no_match_section}

  </div>

  <!-- Footer -->
  <div style="background:#f0f4fa;padding:12px 28px;border-top:1px solid #dde3ee;
              text-align:center;">
    <p style="font-size:11px;color:#aaa;margin:0;">
      Generado automáticamente · {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC ·
      sync_control_asistencia.py
    </p>
  </div>

</div>
</div>"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Sync control_asistencias teacher activity → Odoo hr.attendance'
    )
    parser.add_argument('--live', action='store_true', help='Apply changes (default: dry run)')
    parser.add_argument('--date', default=None,        help='Date YYYY-MM-DD (default: today VET)')
    parser.add_argument('--env',  default='testing',   choices=['testing', 'production'])
    args = parser.parse_args()

    dry_run     = not args.live
    target_env  = args.env
    target_date = date.fromisoformat(args.date) if args.date else today_vet()
    banner      = 'DRY RUN' if dry_run else 'LIVE'

    print(f"[{banner}] sync_control_asistencia | date={target_date} | env={target_env}")
    print('─' * 60)

    # ── 1. Get teachers who submitted ─────────────────────────────────────────
    teachers = get_teachers_who_submitted(target_date)
    print(f"Submitted in control_asistencias on {target_date}: {len(teachers)}")
    for email, (_, name) in teachers.items():
        print(f"  • {name} <{email}>")

    if not teachers:
        print("No submissions found — nothing to do.")
        return

    # ── 2. Connect to Odoo backend ────────────────────────────────────────────
    try:
        backend = PsycopgBackend() if target_env == 'testing' else XmlRpcBackend()
    except Exception as e:
        print(f"ERROR: Cannot connect to Odoo ({target_env}): {e}")
        sys.exit(1)

    # ── 3. Match emails → Odoo employees ─────────────────────────────────────
    emp_map  = backend.get_employee_map(list(teachers.keys()))
    no_match = [e for e in teachers if e not in emp_map]

    if no_match:
        print(f"\nWARNING — {len(no_match)} teacher(s) with no Odoo match:")
        for e in no_match:
            print(f"  ⚠  {e}")

    # ── 4. Create attendance records ──────────────────────────────────────────
    ci_utc, co_utc = vet_times(target_date)
    created, skipped = [], []

    print(f"\nProcessing {len(emp_map)} matched employees:")
    for email, (_, ctrl_name) in teachers.items():
        if email not in emp_map:
            continue
        emp_id, emp_name = emp_map[email]

        if backend.has_attendance(emp_id, target_date):
            print(f"  SKIP  {emp_name} — record exists for {target_date}")
            skipped.append((emp_name, email))
            continue

        if dry_run:
            print(f"  [DRY] {emp_name} — would create 07:00→13:30 VET")
        else:
            att_id = backend.create_attendance(emp_id, ci_utc, co_utc)
            if att_id is None:
                print(f"  SKIP  {emp_name} — overlap detected, existing record kept")
                skipped.append((emp_name, email))
            else:
                print(f"  ✅   {emp_name} — attendance id={att_id}")
                created.append((emp_name, email, att_id))

    if not dry_run:
        backend.commit()

    backend.close()

    # ── 5. Summary ────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"Summary | {target_date} | [{banner}] | env={target_env}")
    print(f"  Submitted in control_asistencias : {len(teachers)}")
    print(f"  Matched to Odoo employees        : {len(emp_map)}")
    print(f"  Attendance records created       : {len(created) if not dry_run else 'N/A (dry)'}")
    print(f"  Skipped (record already existed) : {len(skipped)}")
    print(f"  No Odoo match (warning)          : {len(no_match)}")

    if not dry_run:
        ok = backend.send_email(target_date, created, skipped, no_match)
        print(f"  Summary email                    : {'sent ✓' if ok else 'FAILED'}")
    else:
        print("\n  → Run with --live to apply changes.")


if __name__ == '__main__':
    main()
