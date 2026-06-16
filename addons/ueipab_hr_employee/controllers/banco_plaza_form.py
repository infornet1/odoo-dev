"""Banco Plaza Employee Data Collection Form.

Route: /banco-plaza-form/<token>
  GET  — pre-filled form showing only the 4 Banco Plaza fields (D, F, O, P).
         Re-editable: always shows current known values from XLSX + any prior submission.
  POST — validates, saves to ir.config_parameter JSON, sends 2 ACK emails.

Token: HMAC-SHA256(form_secret, employee_email)[:24]

ir.config_parameter keys used:
  banco_plaza.form_secret     — HMAC secret (created by blast script)
  banco_plaza.employees       — JSON list of employees (set by blast script)
  banco_plaza.submissions     — JSON dict keyed by email (updated on each submit)
  banco_plaza.campaign_open   — 'True'/'False' (campaign gating)
"""

import datetime
import hashlib
import hmac as _hmac
import json
import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Parameters ─────────────────────────────────────────────────────────────────
PARAM_SECRET      = 'banco_plaza.form_secret'
PARAM_EMPLOYEES   = 'banco_plaza.employees'
PARAM_SUBMISSIONS = 'banco_plaza.submissions'
PARAM_OPEN        = 'banco_plaza.campaign_open'
PARAM_DRY_RUN     = 'banco_plaza.dry_run'       # 'True' → all emails → CEO_EMAIL
CEO_EMAIL         = 'gustavo.perdomo@ueipab.edu.ve'

FORM_BASE_URL = 'https://odoo.ueipab.edu.ve/banco-plaza-form'
LOGO_URL      = 'https://odoo.ueipab.edu.ve/web/image/res.company/1/logo'
HR_EMAIL      = 'recursoshumanos@ueipab.edu.ve'
SENDER        = f'UEIPAB Recursos Humanos <{HR_EMAIL}>'


_ESTADO_CIVIL = {'S': 'Soltero/a', 'C': 'Casado/a', 'D': 'Divorciado/a', 'V': 'Viudo/a'}
_NAME_RE      = re.compile(r"^[A-Za-záéíóúÁÉÍÓÚüÜñÑ'\s\-]+$")


# ── Token + param helpers ──────────────────────────────────────────────────────

def _icp():
    return request.env['ir.config_parameter'].sudo()


def _get_param(key, default=''):
    return _icp().get_param(key, default)


def _is_dry_run() -> bool:
    return _get_param(PARAM_DRY_RUN, 'False') == 'True'


def _compute_token(secret: str, email: str) -> str:
    return _hmac.new(
        secret.encode(), email.lower().encode(), hashlib.sha256
    ).hexdigest()[:24]


def _find_employee_by_token(token: str):
    """Return employee dict from banco_plaza.employees or None."""
    secret = _get_param(PARAM_SECRET)
    if not secret:
        return None
    employees = json.loads(_get_param(PARAM_EMPLOYEES, '[]'))
    for emp in employees:
        expected = _compute_token(secret, emp['email'])
        if _hmac.compare_digest(expected, token):
            return emp
    return None


def _get_submission(email: str):
    """Return previously submitted dict for this employee, or None."""
    subs = json.loads(_get_param(PARAM_SUBMISSIONS, '{}'))
    return subs.get(email.lower())


def _save_submission(email: str, data: dict):
    """Upsert submission for employee, incrementing submission_count."""
    param_key = PARAM_SUBMISSIONS
    subs = json.loads(_get_param(param_key, '{}'))
    existing = subs.get(email.lower(), {})
    subs[email.lower()] = {
        **data,
        'submitted_at': datetime.datetime.now().isoformat(),
        'submission_count': existing.get('submission_count', 0) + 1,
    }
    _icp().set_param(param_key, json.dumps(subs, ensure_ascii=False))
    return subs[email.lower()]


def _merge_values(emp_data: dict, submission: dict | None) -> dict:
    """Current best-known values: XLSX base overridden by any prior submission."""
    base = {
        'segundo_nombre':   emp_data.get('segundo_nombre') or '',
        'segundo_apellido': emp_data.get('segundo_apellido') or '',
        'operadora':        str(emp_data.get('operadora') or ''),
        'numero':           emp_data.get('numero') or '',
    }
    if submission:
        for k in base:
            v = submission.get(k)
            if v is not None:
                base[k] = v
    return base


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate(form: dict) -> list:
    """Return list of (field, message) errors."""
    errors = []
    seg_nom = form.get('segundo_nombre', '').strip()
    seg_ap  = form.get('segundo_apellido', '').strip()
    op      = form.get('operadora', '').strip()
    num     = form.get('numero', '').strip()

    if seg_nom and not _NAME_RE.match(seg_nom):
        errors.append(('segundo_nombre',
                        'Solo se permiten letras y espacios'))
    if seg_ap and not _NAME_RE.match(seg_ap):
        errors.append(('segundo_apellido',
                        'Solo se permiten letras y espacios'))
    if num:
        if not re.match(r'^\d{7}$', num):
            errors.append(('numero',
                            'Debe ser exactamente 7 dígitos (ej: 2337463)'))
        if not op:
            errors.append(('operadora',
                            'Ingresa la operadora si ingresas un número'))
    if op and not re.match(r'^\d{3}$', op):
        errors.append(('operadora', 'La operadora debe ser 3 dígitos (ej: 414)'))
    if op and not num:
        errors.append(('numero',
                        'Ingresa los 7 dígitos si ingresas una operadora'))
    return errors


# ── Controller ─────────────────────────────────────────────────────────────────

class BancoplazaFormController(http.Controller):

    @http.route(
        '/banco-plaza-form/<string:token>',
        type='http',
        auth='public',
        website=False,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def banco_plaza_form(self, token, **kwargs):
        emp = _find_employee_by_token(token)
        if not emp:
            return self._respond(self._page_not_found())

        campaign_open = _get_param(PARAM_OPEN, 'True') == 'True'
        if not campaign_open:
            return self._respond(self._page_closed(emp))

        if request.httprequest.method == 'POST':
            return self._handle_post(token, emp, kwargs)
        return self._handle_get(token, emp)

    # ── GET ────────────────────────────────────────────────────────────────────

    def _handle_get(self, token, emp):
        submission = _get_submission(emp['email'])
        current    = _merge_values(emp, submission)
        return self._respond(
            self._page_form(token, emp, current, is_update=bool(submission))
        )

    # ── POST ───────────────────────────────────────────────────────────────────

    def _handle_post(self, token, emp, form):
        submission = _get_submission(emp['email'])
        current    = _merge_values(emp, submission)

        seg_nom = form.get('segundo_nombre', '').strip().upper()
        seg_ap  = form.get('segundo_apellido', '').strip().upper()
        op      = form.get('operadora', '').strip()
        num     = form.get('numero', '').strip()

        errors = _validate({'segundo_nombre': seg_nom, 'segundo_apellido': seg_ap,
                            'operadora': op, 'numero': num})
        if errors:
            prefill = {'segundo_nombre': seg_nom, 'segundo_apellido': seg_ap,
                       'operadora': op, 'numero': num}
            return self._respond(
                self._page_form(token, emp, prefill,
                                is_update=bool(submission), errors=dict(errors))
            )

        is_update = bool(submission)
        new_data = {
            'segundo_nombre':   seg_nom,
            'segundo_apellido': seg_ap,
            'operadora':        op,
            'numero':           num,
        }
        saved = _save_submission(emp['email'], new_data)

        self._send_ack_employee(token, emp, saved, current, is_update)
        self._send_notify_hr(emp, saved, current, is_update)

        return self._respond(self._page_success(token, emp, saved, is_update))

    # ── Emails ─────────────────────────────────────────────────────────────────

    def _send_ack_employee(self, token, emp, saved, previous, is_update):
        """Resend blast-style email to employee with their confirmed data."""
        first    = emp['primer_nombre'].capitalize()
        pronoun  = 'Estimada' if emp.get('sexo') == 'F' else 'Estimado'
        form_url = f'{FORM_BASE_URL}/{token}'
        count    = saved.get('submission_count', 1)
        badge    = ('Actualización #' + str(count)) if is_update else 'Primer envío'
        ts       = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

        def row(label, value, is_new=False):
            bg  = '#f0fdf4' if is_new and value else '#f9fafb'
            clr = '#166534' if is_new and value else '#374151'
            fw  = 'bold'    if is_new and value else 'normal'
            val = self._esc(value) if value else '<span style="color:#9ca3af;">—</span>'
            return (f'<tr style="background:{bg};">'
                    f'<td style="padding:8px 12px;font-size:13px;color:#6b7280;">{label}</td>'
                    f'<td style="padding:8px 12px;font-size:13px;color:{clr};'
                    f'font-weight:{fw};">{val}</td></tr>')

        phone_display = (f'0{saved["operadora"]}-{saved["numero"]}'
                         if saved.get('operadora') and saved.get('numero') else '')

        prev_nom = previous.get('segundo_nombre', '')
        prev_ap  = previous.get('segundo_apellido', '')
        prev_op  = previous.get('operadora', '')
        prev_num = previous.get('numero', '')

        rows = ''.join([
            row('Primer Nombre',      emp['primer_nombre']),
            row('Segundo Nombre',     saved['segundo_nombre'],
                saved['segundo_nombre'] != prev_nom),
            row('Primer Apellido',    emp['primer_apellido']),
            row('Segundo Apellido',   saved['segundo_apellido'],
                saved['segundo_apellido'] != prev_ap),
            row('Número de Cédula',   str(emp.get('cedula', ''))),
            row('Fecha de Nacimiento',emp.get('dob', '')),
            row('Estado Civil',       _ESTADO_CIVIL.get(emp.get('estado_civil', ''), '')),
            row('Teléfono',           phone_display,
                (saved['operadora'] != prev_op or saved['numero'] != prev_num)),
        ])

        body = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:30px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:8px;overflow:hidden;
              box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <tr><td style="background:#1e3a5f;padding:24px 32px;text-align:center;">
    <img src="{LOGO_URL}" height="60" alt="UEIPAB"
         style="border-radius:50%;border:2px solid #fff;">
    <p style="color:#fff;margin:10px 0 0;font-size:13px;letter-spacing:1px;">
      RECURSOS HUMANOS</p>
  </td></tr>
  <tr><td style="padding:28px 32px;">

    <div style="background:#f0fdf4;border:1px solid #86efac;border-radius:6px;
                padding:10px 16px;margin-bottom:20px;font-size:13px;color:#166534;">
      ✅ <strong>Datos recibidos</strong> &nbsp;·&nbsp; {badge} &nbsp;·&nbsp; {ts}
    </div>

    <p style="margin:0 0 16px;font-size:15px;color:#1e3a5f;">
      {pronoun} <strong>{self._esc(first)}</strong>,</p>
    <p style="margin:0 0 20px;color:#374151;font-size:14px;line-height:1.6;">
      Hemos recibido tus datos para la apertura de cuenta de nómina en
      <strong>Banco Plaza</strong>. A continuación encontrarás un resumen de la
      información registrada. Las filas en <span style="color:#166534;font-weight:bold;">
      verde</span> corresponden a los datos que actualizaste en este envío.</p>

    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;border:1px solid #e5e7eb;
                  border-radius:6px;overflow:hidden;font-size:14px;">
      <thead><tr style="background:#e8f0fe;">
        <th style="padding:8px 12px;text-align:left;color:#1e3a5f;
                   font-size:11px;text-transform:uppercase;">Campo</th>
        <th style="padding:8px 12px;text-align:left;color:#1e3a5f;
                   font-size:11px;text-transform:uppercase;">Valor</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>

    <div style="margin-top:24px;text-align:center;">
      <a href="{form_url}"
         style="display:inline-block;background:#1e3a5f;color:#fff;
                text-decoration:none;padding:12px 28px;border-radius:8px;
                font-size:14px;font-weight:bold;">
        ✏️&nbsp; Actualizar mis datos
      </a>
    </div>

    <p style="margin:20px 0 0;font-size:12px;color:#9ca3af;line-height:1.6;">
      Si detectas algún error, usa el botón de arriba para corregirlo.<br>
      Consultas: <a href="mailto:{HR_EMAIL}" style="color:#1e3a5f;">{HR_EMAIL}</a>
    </p>
  </td></tr>
  <tr><td style="background:#f9fafb;padding:14px 32px;text-align:center;">
    <p style="margin:0;font-size:11px;color:#9ca3af;">
      Instituto Privado Andrés Bello, CA &mdash; UEIPAB &mdash; El Tigre, Anzoátegui
    </p>
  </td></tr>
</table></td></tr></table>
</body></html>"""

        dry_run  = _is_dry_run()
        email_to = CEO_EMAIL if dry_run else emp['email']
        email_cc = '' if dry_run else HR_EMAIL
        try:
            request.env['mail.mail'].sudo().create({
                'subject':    ('[DRY-RUN] ' if dry_run else '') +
                              f'Banco Plaza — Datos recibidos ✅ | UEIPAB',
                'body_html':  body,
                'email_to':   email_to,
                'email_from': SENDER,
                'reply_to':   HR_EMAIL,
                'email_cc':   email_cc,
                'state':      'outgoing',
            }).send()
            _logger.info('banco_plaza_form: ACK sent to %s%s',
                         email_to, ' [DRY-RUN]' if dry_run else '')
        except Exception:
            _logger.exception('banco_plaza_form: failed to send ACK to %s', email_to)

    def _send_notify_hr(self, emp, saved, previous, is_update):
        """Notify recursoshumanos@ with a diff of what changed."""
        ts      = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        count   = saved.get('submission_count', 1)
        action  = f'Actualización #{count}' if is_update else 'Primer envío'

        def diff_row(label, old_val, new_val):
            changed = old_val != new_val
            old_html = self._esc(old_val) if old_val else '<em style="color:#aaa;">Vacío</em>'
            new_html = self._esc(new_val) if new_val else '<em style="color:#aaa;">Vacío</em>'
            bg = '#f0fdf4' if changed else '#fff'
            return (f'<tr style="background:{bg};">'
                    f'<td style="padding:8px 12px;font-size:13px;color:#555;">{label}</td>'
                    f'<td style="padding:8px 12px;font-size:13px;color:#c0392b;'
                    f'text-decoration:{"line-through" if changed else "none"};">'
                    f'{old_html}</td>'
                    f'<td style="padding:8px 12px;font-size:13px;color:#155724;'
                    f'font-weight:{"bold" if changed else "normal"};">'
                    f'{new_html}</td></tr>')

        prev_phone = (f'0{previous["operadora"]}-{previous["numero"]}'
                      if previous.get('operadora') and previous.get('numero') else '')
        new_phone  = (f'0{saved["operadora"]}-{saved["numero"]}'
                      if saved.get('operadora') and saved.get('numero') else '')

        rows = ''.join([
            diff_row('Segundo Nombre',   previous.get('segundo_nombre', ''),
                     saved['segundo_nombre']),
            diff_row('Segundo Apellido', previous.get('segundo_apellido', ''),
                     saved['segundo_apellido']),
            diff_row('Teléfono',         prev_phone, new_phone),
        ])

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;">
  <div style="background:#1e3a5f;color:#fff;padding:20px 28px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:17px;">Banco Plaza — {action}</h2>
    <p style="margin:6px 0 0;font-size:13px;opacity:0.8;">{ts}</p>
  </div>
  <div style="background:#fff;border:1px solid #e5e7eb;padding:24px 28px;
              border-radius:0 0 8px 8px;">
    <div style="background:#f0f4fa;border-radius:6px;padding:12px 16px;margin-bottom:20px;">
      <span style="font-size:12px;color:#6b7280;">EMPLEADO</span><br>
      <strong style="font-size:15px;color:#1e3a5f;">
        {self._esc(emp["primer_nombre"])} {self._esc(emp["primer_apellido"])}</strong>
      &nbsp;·&nbsp;
      <span style="font-size:13px;color:#6b7280;">{self._esc(emp["email"])}</span>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:6px;">
      <thead><tr style="background:#f3f4f6;">
        <th style="padding:8px 12px;text-align:left;font-size:12px;color:#374151;">CAMPO</th>
        <th style="padding:8px 12px;text-align:left;font-size:12px;color:#c0392b;">ANTERIOR</th>
        <th style="padding:8px 12px;text-align:left;font-size:12px;color:#155724;">NUEVO</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-size:11px;color:#9ca3af;margin:18px 0 0;border-top:1px solid #e5e7eb;
              padding-top:12px;">
      Envío #{count} &nbsp;|&nbsp; IP: {request.httprequest.environ.get(
        'HTTP_X_FORWARDED_FOR', request.httprequest.remote_addr).split(',')[0].strip()}
    </p>
  </div>
</div>"""

        dry_run  = _is_dry_run()
        email_to = CEO_EMAIL if dry_run else HR_EMAIL
        try:
            request.env['mail.mail'].sudo().create({
                'subject':    ('[DRY-RUN] ' if dry_run else '') +
                              f'[Banco Plaza] {emp["primer_nombre"]} {emp["primer_apellido"]} — {action}',
                'body_html':  body,
                'email_to':   email_to,
                'email_from': SENDER,
                'state':      'outgoing',
            }).send()
            _logger.info('banco_plaza_form: HR notify sent to %s%s',
                         email_to, ' [DRY-RUN]' if dry_run else '')
        except Exception:
            _logger.exception('banco_plaza_form: failed to send HR notify for %s', emp['email'])

    # ── Pages ──────────────────────────────────────────────────────────────────

    def _page_form(self, token, emp, current, is_update=False, errors=None):
        errors   = errors or {}
        first    = emp['primer_nombre'].capitalize()
        pronoun  = 'Estimada' if emp.get('sexo') == 'F' else 'Estimado'
        cedula   = f"V-{emp['cedula']}" if emp.get('cedula') else ''
        form_url = f'/banco-plaza-form/{token}'

        update_banner = ''
        if is_update:
            update_banner = '''
<div style="background:#eff6ff;border:1px solid #93c5fd;border-radius:6px;
            padding:10px 16px;margin-bottom:20px;font-size:13px;color:#1e40af;">
  ✏️ <strong>Modo edición</strong> — Ya enviaste tus datos anteriormente.
  Puedes corregirlos aquí y volver a enviar.
</div>'''

        def err(fname):
            if fname in errors:
                return (f'<p style="margin:4px 0 0;font-size:12px;color:#dc2626;">'
                        f'⚠ {self._esc(errors[fname])}</p>')
            return ''

        def input_cls(fname):
            if fname in errors:
                return 'border:2px solid #dc2626;background:#fef2f2;'
            return ''

        op_val = self._esc(current.get('operadora', ''))

        seg_nom_val = self._esc(current.get('segundo_nombre', ''))
        seg_ap_val  = self._esc(current.get('segundo_apellido', ''))
        num_val     = self._esc(current.get('numero', ''))

        body = f"""
{update_banner}
<p style="margin:0 0 6px;font-size:15px;color:#1e3a5f;">
  {pronoun} <strong>{self._esc(first)}</strong>,</p>
<p style="margin:0 0 22px;color:#374151;font-size:14px;line-height:1.6;">
  Para abrir tu cuenta de nómina en <strong>Banco Plaza</strong>, necesitamos
  completar los siguientes datos. Completa los campos y presiona <em>Confirmar</em>.</p>

<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
            padding:12px 16px;margin-bottom:24px;font-size:13px;color:#64748b;">
  <strong style="color:#1e3a5f;">{self._esc(emp["primer_nombre"])} {self._esc(emp["primer_apellido"])}</strong>
  &nbsp;·&nbsp; {self._esc(cedula)}
</div>

<form method="POST" action="{form_url}" novalidate>

  <p style="font-size:11px;font-weight:bold;letter-spacing:1px;color:#1e3a5f;
             text-transform:uppercase;border-bottom:2px solid #e0eaf8;
             padding-bottom:6px;margin:0 0 16px;">Nombre completo</p>

  <div style="margin-bottom:16px;">
    <label style="display:block;font-size:12px;font-weight:bold;color:#374151;
                  text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
      Segundo Nombre
    </label>
    <input type="text" name="segundo_nombre" value="{seg_nom_val}"
           placeholder="Ej: JOSE  (deja vacío si no tienes)"
           style="width:100%;padding:11px 14px;border:1.5px solid #c8d8e8;
                  border-radius:8px;font-size:14px;box-sizing:border-box;
                  {input_cls("segundo_nombre")}">
    <p style="margin:4px 0 0;font-size:11px;color:#9ca3af;">
      Si no tienes segundo nombre, deja este campo en blanco.</p>
    {err("segundo_nombre")}
  </div>

  <div style="margin-bottom:24px;">
    <label style="display:block;font-size:12px;font-weight:bold;color:#374151;
                  text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
      Segundo Apellido
    </label>
    <input type="text" name="segundo_apellido" value="{seg_ap_val}"
           placeholder="Ej: MATA  (deja vacío si no tienes)"
           style="width:100%;padding:11px 14px;border:1.5px solid #c8d8e8;
                  border-radius:8px;font-size:14px;box-sizing:border-box;
                  {input_cls("segundo_apellido")}">
    <p style="margin:4px 0 0;font-size:11px;color:#9ca3af;">
      Si no tienes segundo apellido, deja este campo en blanco.</p>
    {err("segundo_apellido")}
  </div>

  <p style="font-size:11px;font-weight:bold;letter-spacing:1px;color:#1e3a5f;
             text-transform:uppercase;border-bottom:2px solid #e0eaf8;
             padding-bottom:6px;margin:0 0 16px;">Teléfono celular</p>

  <div style="display:grid;grid-template-columns:1fr 2fr;gap:14px;margin-bottom:8px;">
    <div>
      <label style="display:block;font-size:12px;font-weight:bold;color:#374151;
                    text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
        Operadora
      </label>
      <input type="tel" name="operadora" value="{op_val}"
             placeholder="Ej: 414"
             maxlength="3"
             style="width:100%;padding:11px 14px;border:1.5px solid #c8d8e8;
                    border-radius:8px;font-size:14px;box-sizing:border-box;
                    {input_cls('operadora')}">
      {err("operadora")}
    </div>
    <div>
      <label style="display:block;font-size:12px;font-weight:bold;color:#374151;
                    text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
        Número (7 dígitos)
      </label>
      <input type="tel" name="numero" value="{num_val}"
             placeholder="Ej: 2337463"
             maxlength="7"
             style="width:100%;padding:11px 14px;border:1.5px solid #c8d8e8;
                    border-radius:8px;font-size:14px;box-sizing:border-box;
                    {input_cls("numero")}">
      {err("numero")}
    </div>
  </div>
  <p style="margin:0 0 28px;font-size:11px;color:#9ca3af;">
    Operadora: 3 dígitos (ej: 412, 414, 416, 421, 422, 424, 426 u otro).
    Número: 7 dígitos sin el prefijo. Si tu número es 0414-2337463,
    operadora es <strong>414</strong> y número es <strong>2337463</strong>.
  </p>

  <button type="submit" id="bp-submit"
          style="display:block;width:100%;padding:15px;background:#1e3a5f;
                 color:#fff;border:none;border-radius:10px;font-size:16px;
                 font-weight:bold;cursor:pointer;letter-spacing:0.3px;">
    ✓&nbsp; Confirmar y/o Actualizar mis Datos
  </button>
</form>

<script>
(function() {{
  var btn = document.getElementById('bp-submit');
  if (btn) {{
    btn.form.addEventListener('submit', function() {{
      btn.disabled = true;
      btn.textContent = 'Enviando...';
    }});
  }}
  // Auto-uppercase name fields
  ['segundo_nombre','segundo_apellido'].forEach(function(n) {{
    var el = document.querySelector('[name="' + n + '"]');
    if (el) el.addEventListener('blur', function() {{
      el.value = el.value.toUpperCase();
    }});
  }});
  // Digits only for operadora and numero
  var opEl = document.querySelector('[name="operadora"]');
  if (opEl) opEl.addEventListener('input', function() {{
    opEl.value = opEl.value.replace(/[^0-9]/g, '').slice(0, 3);
  }});
  var numEl = document.querySelector('[name="numero"]');
  if (numEl) numEl.addEventListener('input', function() {{
    numEl.value = numEl.value.replace(/[^0-9]/g, '').slice(0, 7);
  }});
}})();
</script>"""

        return self._base_page('Banco Plaza — Datos de Nómina', body)

    def _page_success(self, token, emp, saved, is_update):
        form_url = f'{FORM_BASE_URL}/{token}'
        count    = saved.get('submission_count', 1)
        action   = f'Actualización #{count}' if is_update else '¡Primer envío completado!'
        phone    = (f'0{saved["operadora"]}-{saved["numero"]}'
                    if saved.get('operadora') and saved.get('numero') else '—')

        def row(label, value):
            v = self._esc(value) if value else '<span style="color:#9ca3af;">—</span>'
            return (f'<tr><td style="padding:8px 12px;font-size:13px;color:#6b7280;">'
                    f'{label}</td>'
                    f'<td style="padding:8px 12px;font-size:13px;color:#166534;'
                    f'font-weight:bold;">{v}</td></tr>')

        rows = ''.join([
            row('Segundo Nombre',   saved['segundo_nombre']),
            row('Segundo Apellido', saved['segundo_apellido']),
            row('Teléfono',         phone),
        ])

        body = f"""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:56px;">✅</div>
  <h2 style="color:#166534;margin:10px 0 4px;font-size:21px;">{action}</h2>
  <p style="color:#374151;font-size:14px;margin:0;">
    {self._esc(emp["primer_nombre"])} {self._esc(emp["primer_apellido"])}
  </p>
</div>
<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;
            padding:16px;margin-bottom:20px;">
  <p style="margin:0 0 12px;font-size:13px;color:#166534;font-weight:bold;">
    Datos registrados:</p>
  <table width="100%" cellpadding="0" cellspacing="0"
         style="border-collapse:collapse;">
    {rows}
  </table>
</div>
<p style="font-size:13px;color:#374151;line-height:1.6;margin:0 0 20px;">
  Recursos Humanos ha sido notificado. También recibirás una copia de confirmación
  en tu correo institucional.</p>
<div style="text-align:center;">
  <a href="{form_url}"
     style="display:inline-block;background:#1e3a5f;color:#fff;
            text-decoration:none;padding:11px 24px;border-radius:8px;
            font-size:14px;">
    ✏️ Actualizar mis datos
  </a>
</div>
<p style="font-size:12px;color:#9ca3af;text-align:center;margin-top:20px;">
  Puedes cerrar esta página.</p>"""

        return self._base_page('Datos confirmados ✅', body)

    def _page_closed(self, emp):
        body = """
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">🔒</div>
  <h2 style="color:#1e3a5f;margin:10px 0 4px;">Campaña cerrada</h2>
</div>
<div style="background:#f0f4fa;border:1px solid #c8d8e8;border-radius:8px;
            padding:16px;font-size:14px;color:#374151;line-height:1.6;">
  <p style="margin:0;">
    El período de actualización de datos para Banco Plaza ha finalizado.
    Si necesitas hacer alguna corrección, contacta a
    <a href="mailto:recursoshumanos@ueipab.edu.ve"
       style="color:#1e3a5f;">recursoshumanos@ueipab.edu.ve</a>.
  </p>
</div>"""
        return self._base_page('Campaña cerrada', body)

    def _page_not_found(self):
        body = """
<div style="text-align:center;margin-bottom:20px;">
  <div style="font-size:56px;">❌</div>
  <h2 style="color:#991b1b;margin:10px 0 4px;">Enlace no válido</h2>
</div>
<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;
            padding:16px;font-size:14px;color:#991b1b;line-height:1.6;">
  <p style="margin:0;">
    Este enlace no es válido o ha expirado. Si necesitas ayuda, contacta a
    <a href="mailto:recursoshumanos@ueipab.edu.ve"
       style="color:#991b1b;">recursoshumanos@ueipab.edu.ve</a>.
  </p>
</div>"""
        return self._base_page('Enlace no válido', body)

    # ── Base page ──────────────────────────────────────────────────────────────

    def _base_page(self, title, body_content):
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{self._esc(title)} — UEIPAB</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;}}
    body{{font-family:Arial,Helvetica,sans-serif;background:#f0f4fa;
          margin:0;padding:24px 12px 48px;min-height:100vh;}}
    .card{{max-width:600px;margin:0 auto;background:#fff;border-radius:14px;
           box-shadow:0 6px 32px rgba(30,58,95,0.13);overflow:hidden;}}
    .hdr{{background:linear-gradient(135deg,#1e3a5f 0%,#2471a3 100%);
          color:#fff;padding:24px 28px;text-align:center;}}
    .hdr img{{border-radius:50%;border:2px solid rgba(255,255,255,0.6);}}
    .hdr h1{{margin:12px 0 0;font-size:18px;font-weight:bold;}}
    .hdr p{{margin:4px 0 0;font-size:12px;opacity:0.75;letter-spacing:1px;}}
    .body-wrap{{padding:28px;}}
    .ftr{{background:#f9fafb;padding:14px 28px;text-align:center;
           border-top:1px solid #e5e7eb;
           font-size:11px;color:#9ca3af;}}
    input,select{{transition:border-color .2s,box-shadow .2s;}}
    input:focus,select:focus{{outline:none;border-color:#2471a3 !important;
      box-shadow:0 0 0 3px rgba(36,113,163,.15);}}
    @media(max-width:480px){{.body-wrap{{padding:20px 16px;}}}}
  </style>
</head>
<body>
<div class="card">
  <div class="hdr">
    <img src="{LOGO_URL}" height="56" alt="UEIPAB">
    <h1>Banco Plaza &mdash; Datos de N&oacute;mina</h1>
    <p>UEIPAB &middot; Recursos Humanos</p>
  </div>
  <div class="body-wrap">
    {body_content}
  </div>
  <div class="ftr">
    Enlace personal e intransferible &mdash;
    <a href="mailto:recursoshumanos@ueipab.edu.ve"
       style="color:#9ca3af;">recursoshumanos@ueipab.edu.ve</a>
  </div>
</div>
</body>
</html>"""

    @staticmethod
    def _respond(html: str):
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')]
        )

    @staticmethod
    def _esc(text):
        return (str(text)
                .replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))
