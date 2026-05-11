"""Public controller for the Employee Private Info Request feature.

Route: /employee-info/<token>
  GET  — renders a beautiful, mobile-friendly, pre-filled form
  POST — persists changes to hr.employee, marks request completed,
         sends a diff notification to recursoshumanos@ueipab.edu.ve

No QWeb template dependency — the HTML is generated inline so the
controller works even if the module has no website/template installed.
"""

import datetime
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Selection labels ──────────────────────────────────────────────────────────

_MARITAL_LABELS = {
    'single': 'Soltero/a',
    'married': 'Casado/a',
    'cohabitant': 'Unión concubinaria',
    'widower': 'Viudo/a',
    'divorced': 'Divorciado/a',
}

_GENDER_LABELS = {
    'male': 'Masculino',
    'female': 'Femenino',
    'other': 'Otro',
}

# Ordered list of fields shown on the form
_FORM_FIELDS = [
    'identification_id',
    'private_email',
    'private_phone',
    'gender',
    'birthday',
    'place_of_birth',
    'country_of_birth',
    'private_city',
    'private_state_id',
    'private_zip',
    'private_country_id',
    'marital',
    'emergency_contact',
    'emergency_phone',
]

_FIELD_LABELS = {
    'private_email': 'Correo personal',
    'private_phone': 'Teléfono personal',
    'marital': 'Estado civil',
    'emergency_contact': 'Contacto de emergencia',
    'emergency_phone': 'Teléfono de emergencia',
    'identification_id': 'Cédula de identidad',
    'gender': 'Género',
    'birthday': 'Fecha de nacimiento',
    'place_of_birth': 'Lugar de nacimiento',
    'country_of_birth': 'País de nacimiento',
    'private_city': 'Ciudad',
    'private_state_id': 'Estado/Provincia',
    'private_zip': 'Código postal',
    'private_country_id': 'País de residencia',
}


class EmployeeInfoController(http.Controller):

    # ── Main route ────────────────────────────────────────────────────────────

    @http.route(
        '/employee-info/<string:token>',
        type='http',
        auth='public',
        website=False,
        methods=['GET', 'POST'],
        csrf=False,
    )
    def employee_info(self, token, **kwargs):
        InfoRequest = request.env['hr.employee.info.request'].sudo()
        info_req = InfoRequest.search([('token', '=', token)], limit=1)

        if not info_req:
            return self._respond(self._page_not_found())

        if request.httprequest.method == 'POST':
            return self._handle_post(info_req, kwargs)
        else:
            return self._handle_get(info_req)

    # ── GET — render the form ─────────────────────────────────────────────────

    def _handle_get(self, info_req):
        if info_req.state == 'completed':
            return self._respond(self._page_already_completed(info_req))
        return self._respond(self._page_form(info_req))

    # ── POST — process submission ─────────────────────────────────────────────

    def _handle_post(self, info_req, form_data):
        if info_req.state == 'completed':
            return self._respond(self._page_already_completed(info_req))

        emp = info_req.employee_id

        # Snapshot old values before any write
        old_vals = self._snapshot_employee(emp)

        # Build write dict from submitted form fields
        write_vals = {}
        m2o_fields = {'country_of_birth', 'private_state_id', 'private_country_id'}

        for fname in _FORM_FIELDS:
            raw = form_data.get(fname, '').strip()
            if not raw:
                # Never clear existing data — only update if value provided
                continue
            if fname in m2o_fields:
                try:
                    write_vals[fname] = int(raw)
                except (ValueError, TypeError):
                    pass
            else:
                write_vals[fname] = raw

        if write_vals:
            emp.sudo().write(write_vals)

        # Snapshot new values after write for diff
        new_vals = self._snapshot_employee(emp)
        diff = self._compute_diff(old_vals, new_vals)

        # Mark request as completed
        ip = (
            request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '')
            .split(',')[0].strip()
            or request.httprequest.remote_addr
        )
        info_req.write({
            'state': 'completed',
            'completed_date': datetime.datetime.now(),
            'completed_ip': ip,
            'submitted_values': json.dumps({
                'old': old_vals,
                'new': new_vals,
                'diff': diff,
                'ip': ip,
                'ts': datetime.datetime.now().isoformat(),
            }, ensure_ascii=False),
        })

        # Notify HR with diff
        self._notify_hr(info_req, emp, diff, old_vals, new_vals)

        return self._respond(self._page_thank_you(info_req, emp))

    # ── Employee value snapshot ───────────────────────────────────────────────

    def _snapshot_employee(self, emp):
        """Return a plain-dict snapshot of the 14 form fields."""
        snap = {}
        for fname in _FORM_FIELDS:
            val = getattr(emp, fname, None)
            if hasattr(val, 'id'):
                # Many2one — store id + display name
                snap[fname] = {'id': val.id, 'name': val.name} if val else None
            elif isinstance(val, datetime.date):
                snap[fname] = val.isoformat()
            else:
                snap[fname] = val or ''
        return snap

    def _compute_diff(self, old_vals, new_vals):
        """Return {fname: {old: ..., new: ...}} for changed fields only."""
        diff = {}
        for fname in _FORM_FIELDS:
            old = old_vals.get(fname)
            new = new_vals.get(fname)
            # Normalize for comparison
            old_s = (old.get('name') if isinstance(old, dict) else old) or ''
            new_s = (new.get('name') if isinstance(new, dict) else new) or ''
            if old_s != new_s:
                diff[fname] = {'old': old_s, 'new': new_s}
        return diff

    # ── HR notification ───────────────────────────────────────────────────────

    def _notify_hr(self, info_req, emp, diff, old_vals, new_vals):
        """Send a diff email to recursoshumanos on every submission."""
        dt = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

        if diff:
            rows_html = ''
            for fname, change in diff.items():
                label = _FIELD_LABELS.get(fname, fname)
                old_disp = change['old'] or '<em style="color:#aaa;">Sin valor</em>'
                new_disp = change['new'] or '<em style="color:#aaa;">Sin valor</em>'
                rows_html += f"""
      <tr>
        <td style="padding:10px 14px;border-bottom:1px solid #e0e8f0;
                   font-size:13px;color:#555;width:35%;">{label}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e0e8f0;
                   font-size:13px;color:#c62828;text-decoration:line-through;
                   width:30%;">{old_disp}</td>
        <td style="padding:10px 14px;border-bottom:1px solid #e0e8f0;
                   font-size:13px;color:#155724;font-weight:bold;
                   width:30%;">{new_disp}</td>
      </tr>"""
            changes_section = f"""
    <p style="font-size:13px;color:#333;margin:0 0 12px;">
      El empleado actualizó <strong>{len(diff)}</strong> campo(s):
    </p>
    <table cellpadding="0" cellspacing="0" width="100%"
           style="border-collapse:collapse;border:1px solid #c8d8e8;
                  border-radius:8px;overflow:hidden;">
      <thead>
        <tr style="background:#1a2c5b;">
          <th style="padding:10px 14px;color:#fff;font-size:12px;
                     text-align:left;font-weight:600;">CAMPO</th>
          <th style="padding:10px 14px;color:#fff;font-size:12px;
                     text-align:left;font-weight:600;">VALOR ANTERIOR</th>
          <th style="padding:10px 14px;color:#fff;font-size:12px;
                     text-align:left;font-weight:600;">VALOR NUEVO</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>"""
            badge_bg = '#d4edda'
            badge_color = '#155724'
            badge_border = '#c3e6cb'
            badge_text = f'✅ {len(diff)} cambio(s) registrado(s)'
        else:
            changes_section = """
    <div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:8px;
                padding:16px;font-size:13px;color:#1a2c5b;">
      El empleado revisó su información y <strong>no realizó ningún cambio</strong>.
      Los datos actuales son correctos.
    </div>"""
            badge_bg = '#e8f4f8'
            badge_color = '#1a2c5b'
            badge_border = '#bee5eb'
            badge_text = 'Sin cambios — datos confirmados'

        body = f"""
<div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;">
  <div style="background:linear-gradient(135deg,#1a2c5b 0%,#2471a3 100%);
              color:#fff;padding:22px 28px;border-radius:8px 8px 0 0;">
    <h2 style="margin:0;font-size:18px;">
      Actualización de Datos Personales
    </h2>
    <p style="margin:6px 0 0;font-size:13px;opacity:0.85;">
      Respuesta recibida de empleado — {dt}
    </p>
  </div>
  <div style="background:#fff;border:1px solid #dde;
              padding:24px 28px;border-radius:0 0 8px 8px;">
    <div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;
                margin-bottom:20px;">
      <span style="font-size:12px;color:#888;display:block;margin-bottom:4px;">
        EMPLEADO
      </span>
      <strong style="font-size:16px;color:#1a2c5b;">{emp.name}</strong>
      &nbsp;·&nbsp;
      <span style="font-size:13px;color:#555;">{emp.work_email or ''}</span>
    </div>
    <span style="display:inline-block;background:{badge_bg};color:{badge_color};
                 border:1px solid {badge_border};font-size:12px;font-weight:bold;
                 padding:4px 14px;border-radius:20px;margin-bottom:18px;">
      {badge_text}
    </span>
    {changes_section}
    <p style="font-size:11px;color:#aaa;margin:20px 0 0;border-top:1px solid #eee;
              padding-top:14px;">
      Campaña: <code>{info_req.campaign_key}</code> &nbsp;|&nbsp;
      Token: <code>{info_req.token[:8]}...</code> &nbsp;|&nbsp;
      IP: {info_req.completed_ip or 'desconocida'}
    </p>
  </div>
</div>"""

        try:
            request.env['mail.mail'].sudo().create({
                'subject': f'[RRHH] Datos actualizados — {emp.name}',
                'email_from': 'Sistema UEIPAB <recursoshumanos@ueipab.edu.ve>',
                'email_to': 'recursoshumanos@ueipab.edu.ve',
                'body_html': body,
                'state': 'outgoing',
            }).send()
        except Exception:
            _logger.exception(
                "employee_info_controller: failed to send HR diff email "
                "for request id=%s", info_req.id
            )

    # ── HTML pages ────────────────────────────────────────────────────────────

    def _respond(self, html):
        return request.make_response(
            html, headers=[('Content-Type', 'text/html; charset=utf-8')]
        )

    def _base_page(self, title, body_content, extra_head=''):
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} &mdash; UEIPAB</title>
  <style>
    *,*::before,*::after {{box-sizing:border-box;}}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      background: #f0f4fa;
      margin: 0;
      padding: 24px 12px 48px;
      min-height: 100vh;
    }}
    .card {{
      max-width: 660px;
      margin: 0 auto;
      background: #fff;
      border-radius: 14px;
      box-shadow: 0 6px 32px rgba(26,44,91,0.13);
      overflow: hidden;
    }}
    .hdr {{
      background: linear-gradient(135deg, #1a2c5b 0%, #2471a3 100%);
      color: #fff;
      padding: 28px 28px 24px;
      text-align: center;
    }}
    .hdr .logo-text {{
      font-size: 13px;
      letter-spacing: 2px;
      text-transform: uppercase;
      opacity: 0.75;
      margin: 0 0 6px;
    }}
    .hdr h1 {{
      margin: 0 0 8px;
      font-size: 20px;
      font-weight: bold;
      line-height: 1.3;
    }}
    .hdr .subtitle {{
      font-size: 14px;
      opacity: 0.85;
      margin: 0;
    }}
    .body-wrap {{
      padding: 28px 28px;
    }}
    .greeting {{
      font-size: 15px;
      color: #333;
      margin: 0 0 24px;
      line-height: 1.6;
    }}
    .field-group {{
      margin-bottom: 18px;
    }}
    label {{
      display: block;
      font-size: 12px;
      font-weight: bold;
      color: #1a2c5b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }}
    input[type=text],
    input[type=email],
    input[type=tel],
    input[type=date],
    select {{
      width: 100%;
      padding: 11px 14px;
      border: 1.5px solid #c8d8e8;
      border-radius: 8px;
      font-size: 14px;
      color: #222;
      background: #fff;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
      appearance: auto;
    }}
    input:focus, select:focus {{
      border-color: #2471a3;
      box-shadow: 0 0 0 3px rgba(36,113,163,0.15);
    }}
    .field-empty input,
    .field-empty select {{
      border-left: 4px solid #f39c12;
      background: #fffdf5;
    }}
    .empty-hint {{
      font-size: 11px;
      color: #f39c12;
      margin: 4px 0 0;
    }}
    .section-title {{
      font-size: 11px;
      font-weight: bold;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: #2471a3;
      margin: 28px 0 14px;
      padding-bottom: 6px;
      border-bottom: 2px solid #e0eaf8;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}
    @media (max-width: 480px) {{
      .two-col {{ grid-template-columns: 1fr; }}
      .body-wrap {{ padding: 20px 18px; }}
      .hdr {{ padding: 22px 18px 18px; }}
    }}
    .btn-submit {{
      display: block;
      width: 100%;
      margin-top: 30px;
      padding: 15px;
      background: #1a2c5b;
      color: #fff;
      border: none;
      border-radius: 10px;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
      letter-spacing: 0.3px;
      transition: background 0.2s;
    }}
    .btn-submit:hover {{ background: #2471a3; }}
    .footer {{
      background: #f8f9fa;
      padding: 14px 24px;
      text-align: center;
      font-size: 11px;
      color: #aaa;
      border-top: 1px solid #eaeaea;
    }}
    {extra_head}
  </style>
</head>
<body>
  <div class="card">
    <div class="hdr">
      <p class="logo-text">Instituto Privado Andr&eacute;s Bello, CA &mdash; UEIPAB</p>
      <h1>Actualizaci&oacute;n de Datos Personales</h1>
    </div>
    <div class="body-wrap">
      {body_content}
    </div>
    <div class="footer">
      Este enlace es personal e intransferible. &mdash;
      <a href="mailto:recursoshumanos@ueipab.edu.ve"
         style="color:#aaa;">recursoshumanos@ueipab.edu.ve</a>
    </div>
  </div>
</body>
</html>"""

    def _page_form(self, info_req):
        """Build the data-entry form pre-filled with current employee values."""
        emp = info_req.employee_id

        # Fetch all countries and states for <select> dropdowns
        Country = request.env['res.country'].sudo()
        State = request.env['res.country.state'].sudo()
        countries = Country.search([], order='name asc')
        states = State.search([], order='name asc')

        def country_options(selected_id):
            opts = ['<option value="">-- Seleccionar --</option>']
            for c in countries:
                sel = ' selected' if c.id == selected_id else ''
                opts.append(f'<option value="{c.id}"{sel}>{c.name}</option>')
            return ''.join(opts)

        def state_options(selected_id):
            opts = ['<option value="">-- Seleccionar --</option>']
            for s in states:
                sel = ' selected' if s.id == selected_id else ''
                opts.append(
                    f'<option value="{s.id}"{sel}>'
                    f'{s.name} ({s.country_id.name})</option>'
                )
            return ''.join(opts)

        def marital_options(selected):
            opts = ['<option value="">-- Seleccionar --</option>']
            for k, v in _MARITAL_LABELS.items():
                sel = ' selected' if k == selected else ''
                opts.append(f'<option value="{k}"{sel}>{v}</option>')
            return ''.join(opts)

        def gender_options(selected):
            opts = ['<option value="">-- Seleccionar --</option>']
            for k, v in _GENDER_LABELS.items():
                sel = ' selected' if k == selected else ''
                opts.append(f'<option value="{k}"{sel}>{v}</option>')
            return ''.join(opts)

        def inp(fname, ftype='text', value=''):
            """Render a labeled <input> field."""
            label = _FIELD_LABELS.get(fname, fname)
            empty_cls = ' field-empty' if not value else ''
            empty_hint = (
                '<p class="empty-hint">No registrado — por favor completa este campo</p>'
                if not value else ''
            )
            val_attr = f'value="{self._esc(str(value))}"' if value else 'value=""'
            return f"""<div class="field-group{empty_cls}">
  <label for="f_{fname}">{label}</label>
  <input type="{ftype}" id="f_{fname}" name="{fname}" {val_attr}/>
  {empty_hint}
</div>"""

        def sel(fname, options_html, value=''):
            """Render a labeled <select> field."""
            label = _FIELD_LABELS.get(fname, fname)
            empty_cls = ' field-empty' if not value else ''
            empty_hint = (
                '<p class="empty-hint">No registrado — por favor completa este campo</p>'
                if not value else ''
            )
            return f"""<div class="field-group{empty_cls}">
  <label for="f_{fname}">{label}</label>
  <select id="f_{fname}" name="{fname}">{options_html}</select>
  {empty_hint}
</div>"""

        # Current field values
        birthday_str = emp.birthday.isoformat() if emp.birthday else ''
        cob_id = emp.country_of_birth.id if emp.country_of_birth else 0
        psi_id = emp.private_state_id.id if emp.private_state_id else 0
        pci_id = emp.private_country_id.id if emp.private_country_id else 0

        first_name = emp.name.split()[0] if emp.name else emp.name

        form_html = f"""
<p class="greeting">
  Hola, <strong>{self._esc(emp.name)}</strong>. Por favor confirma o actualiza
  la siguiente informaci&oacute;n personal. Los campos resaltados en
  <span style="color:#f39c12;font-weight:bold;">amarillo</span>
  a&uacute;n no tienen valor registrado.
</p>

<form method="POST" action="/employee-info/{info_req.token}">

  <div class="section-title">Identificaci&oacute;n</div>
  {inp('identification_id', 'text', emp.identification_id or '')}

  <div class="section-title">Contacto Personal</div>
  {inp('private_email', 'email', emp.private_email or '')}
  {inp('private_phone', 'tel', emp.private_phone or '')}

  <div class="section-title">Informaci&oacute;n Personal</div>
  <div class="two-col">
    {sel('gender', gender_options(emp.gender or ''), emp.gender or '')}
    {inp('birthday', 'date', birthday_str)}
  </div>
  {sel('marital', marital_options(emp.marital or ''), emp.marital or '')}
  {inp('place_of_birth', 'text', emp.place_of_birth or '')}
  {sel('country_of_birth', country_options(cob_id), cob_id)}

  <div class="section-title">Direcci&oacute;n de Residencia</div>
  {inp('private_city', 'text', emp.private_city or '')}
  <div class="two-col">
    {inp('private_zip', 'text', emp.private_zip or '')}
    {sel('private_country_id', country_options(pci_id), pci_id)}
  </div>
  {sel('private_state_id', state_options(psi_id), psi_id)}

  <div class="section-title">Contacto de Emergencia</div>
  {inp('emergency_contact', 'text', emp.emergency_contact or '')}
  {inp('emergency_phone', 'tel', emp.emergency_phone or '')}

  <button type="submit" class="btn-submit">
    &#10003;&nbsp;&nbsp;Confirmar mis datos
  </button>
</form>"""

        return self._base_page(
            'Actualización de Datos Personales',
            form_html,
        )

    def _page_thank_you(self, info_req, emp):
        dt = (
            info_req.completed_date.strftime('%d/%m/%Y a las %H:%M')
            if info_req.completed_date else ''
        )
        content = f"""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:60px;">&#9989;</div>
  <h2 style="color:#155724;margin:12px 0 4px;font-size:22px;">
    &#161;Gracias, {self._esc(emp.name.split()[0])}!
  </h2>
  <p style="color:#555;font-size:15px;margin:0;">
    Tu informaci&oacute;n ha sido registrada correctamente.
  </p>
</div>
<div style="background:#d4edda;border:1px solid #c3e6cb;border-radius:10px;
            padding:20px;font-size:14px;color:#155724;line-height:1.8;
            margin-bottom:16px;">
  <p style="margin:0 0 6px;">
    <strong>Empleado:</strong> {self._esc(emp.name)}
  </p>
  <p style="margin:0 0 6px;">
    <strong>Fecha de confirmaci&oacute;n:</strong> {dt}
  </p>
  <p style="margin:0;">
    <strong>Estado:</strong> Datos confirmados &#9989;
  </p>
</div>
<div style="background:#f0f4fa;border-radius:8px;padding:14px 18px;
            font-size:13px;color:#555;line-height:1.6;">
  Recursos Humanos ha recibido una notificaci&oacute;n autom&aacute;tica con
  los cambios realizados. Si necesitas hacer alguna correcci&oacute;n adicional,
  contacta a
  <a href="mailto:recursoshumanos@ueipab.edu.ve"
     style="color:#2471a3;">recursoshumanos@ueipab.edu.ve</a>.
</div>
<p style="font-size:12px;color:#aaa;text-align:center;margin-top:24px;">
  Puedes cerrar esta p&aacute;gina.
</p>"""
        return self._base_page('Datos confirmados', content)

    def _page_already_completed(self, info_req):
        emp = info_req.employee_id
        dt = (
            info_req.completed_date.strftime('%d/%m/%Y %H:%M')
            if info_req.completed_date else ''
        )
        content = f"""
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:60px;">&#128203;</div>
  <h2 style="color:#1a2c5b;margin:12px 0 4px;">Ya confirmado</h2>
  <p style="color:#555;font-size:14px;margin:0;">
    <strong>{self._esc(emp.name)}</strong>
  </p>
</div>
<div style="background:#e8f4f8;border:1px solid #bee5eb;border-radius:10px;
            padding:18px;font-size:14px;color:#1a2c5b;line-height:1.8;">
  <p style="margin:0;">
    Esta solicitud ya fue completada el <strong>{dt}</strong>.
    No es necesario volver a confirmar.
  </p>
  <p style="margin:8px 0 0;font-size:13px;color:#555;">
    Si necesitas actualizar alg&uacute;n dato, contacta a
    <a href="mailto:recursoshumanos@ueipab.edu.ve"
       style="color:#2471a3;">recursoshumanos@ueipab.edu.ve</a>.
  </p>
</div>"""
        return self._base_page('Ya confirmado', content)

    def _page_not_found(self):
        content = """
<div style="text-align:center;margin-bottom:24px;">
  <div style="font-size:60px;">&#10060;</div>
  <h2 style="color:#721c24;margin:12px 0 4px;">Enlace no v&aacute;lido</h2>
</div>
<div style="background:#fde8e8;border:1px solid #f5c6cb;border-radius:10px;
            padding:18px;font-size:14px;color:#721c24;">
  <p style="margin:0;">
    Este enlace no es v&aacute;lido o ha expirado. Si necesitas ayuda,
    contacta a
    <a href="mailto:recursoshumanos@ueipab.edu.ve"
       style="color:#721c24;">recursoshumanos@ueipab.edu.ve</a>.
  </p>
</div>"""
        return self._base_page('Enlace no válido', content)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _esc(text):
        """Minimal HTML escaping for values inserted into the page."""
        return (
            str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
