#!/usr/bin/env python3
"""
leave_notification.py
─────────────────────
Sends a notification to recursoshumanos@ueipab.edu.ve whenever an employee
submits a leave request (state = confirm).

Runs every 15 min via cron. State file tracks already-notified leave IDs.

Usage:
    python3 scripts/leave_notification.py                        # dry run
    python3 scripts/leave_notification.py --live                 # send for real
    python3 scripts/leave_notification.py --live --test-email X  # preview

Cron: /etc/cron.d/leave_notification
"""

import argparse
import json
import logging
import os
import xmlrpc.client
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

RRHH_EMAIL   = 'recursoshumanos@ueipab.edu.ve'
SENDER_NAME  = 'Recursos Humanos UEIPAB'
SENDER_EMAIL = 'recursoshumanos@ueipab.edu.ve'
LOGO_URL     = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
ODOO_BASE    = 'https://odoo.ueipab.edu.ve'

MAIL_QUEUE_CRON_ID = 3
VET_OFFSET         = timedelta(hours=4)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
STATE_FILE  = os.path.join(SCRIPT_DIR, 'leave_notification_state.json')
CONFIG_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'config', 'production.json'))

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
# State
# ============================================================================

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)


def prune_state(state: dict, days: int = 60):
    cutoff = datetime.now() - timedelta(days=days)
    to_del = []
    for k, v in state.items():
        try:
            if datetime.fromisoformat(str(v)) < cutoff:
                to_del.append(k)
        except Exception:
            pass
    for k in to_del:
        del state[k]

# ============================================================================
# Time helpers
# ============================================================================

def utc_to_vet(utc_str: str) -> datetime | None:
    if not utc_str:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(utc_str, fmt) - VET_OFFSET
        except ValueError:
            pass
    return None

# ============================================================================
# Email builder
# ============================================================================

_EMAIL_CSS = """
  body {{ margin:0; padding:0; background:#f0f4f8; font-family:Arial,Helvetica,sans-serif; }}
  .wrap {{ max-width:560px; margin:20px auto; background:#fff; border-radius:8px;
           overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,.1); }}
  .hdr  {{ padding:28px 24px; text-align:center; }}
  .hdr h1 {{ margin:10px 0 4px; color:#fff; font-size:19px; font-weight:700; }}
  .hdr p  {{ margin:0; color:rgba(255,255,255,.85); font-size:13px; }}
  .body {{ padding:20px 24px; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:18px; }}
  td {{ padding:9px 10px; font-size:13px; border-bottom:1px solid #f0f0f0; vertical-align:top; }}
  td:first-child {{ color:#666; width:165px; }}
  td:last-child  {{ color:#222; font-weight:600; }}
  .footer {{ background:#f8f9fa; padding:12px 24px; text-align:center; font-size:11px; color:#aaa;
             border-top:1px solid #eee; }}
"""


def _email_shell(hdr_gradient: str, hdr_icon: str, hdr_title: str,
                 badge_html: str, rows_html: str, note: str,
                 btn_color: str, btn_label: str, odoo_url: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{_EMAIL_CSS}</style>
</head>
<body>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:20px 0;">
<tr><td align="center">
<div class="wrap">
  <div class="hdr" style="background:{hdr_gradient};">
    <img src="{LOGO_URL}" width="64" height="64"
         style="border-radius:50%;border:3px solid rgba(255,255,255,.3);display:block;
                margin:0 auto 10px;object-fit:cover;">
    <h1>{hdr_icon} {hdr_title}</h1>
    <p>U.E.I.P.A.B. — Recursos Humanos</p>
  </div>
  <div class="body">
    {badge_html}
    <table>{rows_html}
    </table>
    <p style="text-align:center;margin:16px 0 6px;">
      <a href="{odoo_url}"
         style="display:inline-block;background:{btn_color};color:#ffffff !important;
                padding:11px 30px;border-radius:6px;text-decoration:none;
                font-size:14px;font-weight:700;font-family:Arial,sans-serif;">
        {btn_label}
      </a>
    </p>
    <p style="text-align:center;font-size:11px;color:#aaa;margin:4px 0 16px;">{note}</p>
  </div>
  <div class="footer">
    Mensaje automático del sistema UEIPAB. Consultas: {RRHH_EMAIL}
  </div>
</div>
</td></tr>
</table>
</body>
</html>"""


def _common_rows(leave: dict, submitted_label: str = '🕐 Solicitado') -> tuple:
    emp_name   = (leave.get('employee_id') or [None, '—'])[1]
    leave_type = (leave.get('holiday_status_id') or [None, '—'])[1]
    df_vet     = utc_to_vet(leave.get('date_from') or '')
    dt_vet     = utc_to_vet(leave.get('date_to') or '')
    date_from  = df_vet.strftime('%d/%m/%Y %H:%M') if df_vet else '—'
    date_to    = dt_vet.strftime('%d/%m/%Y %H:%M') if dt_vet else '—'
    days       = float(leave.get('number_of_days') or 0)
    days_str   = f"{days:.1f} día{'s' if days != 1.0 else ''}"
    sub_vet    = utc_to_vet(leave.get('write_date') or '')
    submitted  = sub_vet.strftime('%d/%m/%Y %H:%M VET') if sub_vet else '—'
    rows = f"""
      <tr><td>👤 Empleado</td><td>{emp_name}</td></tr>
      <tr><td>📌 Tipo de permiso</td><td>{leave_type}</td></tr>
      <tr><td>📅 Desde</td><td>{date_from} VET</td></tr>
      <tr><td>📅 Hasta</td><td>{date_to} VET</td></tr>
      <tr><td>⏱️ Duración</td><td>{days_str}</td></tr>
      <tr><td>{submitted_label}</td><td>{submitted}</td></tr>"""
    return emp_name, leave_type, rows


def build_confirm_email(leave: dict) -> str:
    emp_name, leave_type, rows = _common_rows(leave)
    odoo_url = f"{ODOO_BASE}/web#id={leave.get('id', '')}&cids=1&menu_id=378&action=520&model=hr.leave&view_type=form"
    badge = ('<div style="display:inline-block;background:#fff3cd;color:#856404;'
             'border:1px solid #f0ad4e;border-radius:12px;padding:4px 14px;'
             'font-size:12px;font-weight:600;margin-bottom:16px;">'
             '⏳ Pendiente de aprobación</div>')
    return _email_shell(
        hdr_gradient='linear-gradient(135deg,#1a73e8,#0d47a1)',
        hdr_icon='📋', hdr_title='Nueva Solicitud de Permiso',
        badge_html=badge, rows_html=rows,
        note='Esta solicitud requiere revisión y aprobación.',
        btn_color='#1a73e8', btn_label='Ver en Odoo →', odoo_url=odoo_url,
    )


def build_validate1_email(leave: dict) -> str:
    emp_name, leave_type, rows = _common_rows(leave, submitted_label='✅ 1ª aprobación')
    odoo_url = f"{ODOO_BASE}/web#id={leave.get('id', '')}&cids=1&menu_id=378&action=520&model=hr.leave&view_type=form"
    badge = ('<div style="display:inline-block;background:#e8f5e9;color:#2e7d32;'
             'border:1px solid #66bb6a;border-radius:12px;padding:4px 14px;'
             'font-size:12px;font-weight:600;margin-bottom:8px;">'
             '✅ Aprobado por supervisor</div>'
             '<br>'
             '<div style="display:inline-block;background:#fff3cd;color:#856404;'
             'border:1px solid #f0ad4e;border-radius:12px;padding:4px 14px;'
             'font-size:12px;font-weight:600;margin:6px 0 16px;">'
             '⏳ Pendiente validación final — Recursos Humanos</div>')
    return _email_shell(
        hdr_gradient='linear-gradient(135deg,#e65100,#bf360c)',
        hdr_icon='🔔', hdr_title='Segunda Validación Requerida',
        badge_html=badge, rows_html=rows,
        note='El supervisor ya aprobó esta solicitud. Recursos Humanos debe dar la validación final.',
        btn_color='#e65100', btn_label='Validar en Odoo →', odoo_url=odoo_url,
    )


def queue_email(to: str, subject: str, body_html: str) -> int:
    effective_to      = TEST_EMAIL if TEST_EMAIL else to
    effective_subject = f"[TEST] {subject}" if TEST_EMAIL else subject
    if DRY_RUN:
        logger.info("  [DRY] Would send to %s: %s", effective_to, effective_subject)
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
    mail_id = odoo_execute('mail.mail', 'create', [vals])
    logger.info("  Queued mail.mail id=%d to %s", mail_id, effective_to)
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

    parser = argparse.ArgumentParser(description='UEIPAB Leave Submission Notifier')
    parser.add_argument('--live', action='store_true', help='Actually send emails')
    parser.add_argument('--test-email', metavar='EMAIL',
                        help='Redirect all emails here (no state write)')
    args = parser.parse_args()

    if args.live:
        DRY_RUN = False
    if args.test_email:
        TEST_EMAIL = args.test_email
        logger.info("TEST MODE — all emails → %s", TEST_EMAIL)

    print('=' * 60)
    print('LEAVE SUBMISSION NOTIFIER')
    print('=' * 60)
    print(f"  DRY_RUN    : {DRY_RUN}")
    print(f"  TEST_EMAIL : {TEST_EMAIL or '(none — real recipient)'}")
    print()

    state = load_state()
    prune_state(state)

    leaves = odoo_search_read(
        'hr.leave',
        [('state', 'in', ['confirm', 'validate1'])],
        ['id', 'employee_id', 'holiday_status_id', 'date_from', 'date_to',
         'number_of_days', 'write_date', 'state'],
        order='write_date asc',
    )
    logger.info("Found %d leave(s) needing attention (confirm + validate1)", len(leaves))

    sent = 0
    for lv in leaves:
        lv_id      = lv['id']
        lv_state   = lv.get('state', 'confirm')
        # Separate state keys so a confirm→validate1 transition triggers a second email
        state_key  = f"notified_{lv_state}_{lv_id}"
        if state_key in state and not TEST_EMAIL:
            logger.debug("  Leave #%d (%s) already notified — skipping", lv_id, lv_state)
            continue

        emp_name   = (lv.get('employee_id') or [None, '?'])[1]
        leave_type = (lv.get('holiday_status_id') or [None, '?'])[1]

        if lv_state == 'confirm':
            subject   = f"📋 Solicitud de Permiso: {emp_name} — {leave_type}"
            body_html = build_confirm_email(lv)
            logger.info("  [CONFIRM] Leave #%d — %s (%s)", lv_id, emp_name, leave_type)
        else:  # validate1
            subject   = f"🔔 Segunda Validación Requerida: {emp_name} — {leave_type}"
            body_html = build_validate1_email(lv)
            logger.info("  [VALIDATE1] Leave #%d — %s (%s)", lv_id, emp_name, leave_type)

        queue_email(RRHH_EMAIL, subject, body_html)

        if not TEST_EMAIL:
            state[state_key] = datetime.now().isoformat()
        sent += 1

    if sent > 0:
        trigger_mail_queue()

    save_state(state)

    print()
    print('=' * 60)
    print('SUMMARY')
    print('=' * 60)
    print(f"  Notifications sent : {sent}")
    print(f"  DRY_RUN            : {DRY_RUN}")
    print()


if __name__ == '__main__':
    main()
