from datetime import date as date_cls

from odoo import http
from odoo.http import request

_DAYS_ES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}


def _hour_select(name, selected_h='', required=False):
    """Render an hour <select> (00–23)."""
    req = 'required' if required else ''
    opts = f'<option value="">─ hora</option>'
    for h in range(0, 24):
        val = f"{h:02d}"
        sel = 'selected' if val == selected_h else ''
        opts += f'<option value="{val}" {sel}>{val}</option>'
    return (
        f'<select name="{name}" {req} '
        f'style="padding:8px 10px;border:1.5px solid #cdd5e0;border-radius:6px;'
        f'font-size:15px;color:#333;width:90px;">{opts}</select>'
    )


def _min_select(name, selected_m='00'):
    """Render a minutes <select> in 5-minute steps."""
    opts = ''
    for m in range(0, 60, 5):
        val = f"{m:02d}"
        sel = 'selected' if val == selected_m else ''
        opts += f'<option value="{val}" {sel}>{val}</option>'
    return (
        f'<select name="{name}" '
        f'style="padding:8px 10px;border:1.5px solid #cdd5e0;border-radius:6px;'
        f'font-size:15px;color:#333;width:90px;">{opts}</select>'
    )


def _time_picker(name, label, hint='', selected='', required=False, optional_label=''):
    """Render a labeled hour:minute picker pair."""
    sel_h = selected[:2] if len(selected) >= 5 else ''
    sel_m = selected[3:5] if len(selected) >= 5 else '00'
    opt_badge = (
        f'<span style="font-weight:400;color:#888;font-size:12px;"> ({optional_label})</span>'
        if optional_label else ''
    )
    colon = '<span style="font-size:20px;font-weight:700;color:#555;padding:0 4px;">:</span>'
    hint_html = f'<p style="font-size:12px;color:#888;margin:3px 0 0;">{hint}</p>' if hint else ''
    return f"""
      <label style="display:block;font-size:13px;font-weight:700;color:#333;margin:16px 0 6px;">
        {label}{opt_badge}
      </label>
      <div style="display:flex;align-items:center;gap:4px;">
        {_hour_select(name + '_h', sel_h, required=required)}
        {colon}
        {_min_select(name + '_m', sel_m)}
      </div>
      {hint_html}"""

_CSS = """
body{margin:0;font-family:Arial,sans-serif;background:#f0f4fa;}
.wrap{max-width:580px;margin:40px auto;padding:16px;}
.card{background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;}
.hdr{background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;padding:24px 28px;}
.hdr h1{margin:0;font-size:20px;font-weight:700;}
.hdr p{margin:4px 0 0;font-size:13px;opacity:.85;}
.body{padding:24px 28px;}
label{display:block;font-size:13px;font-weight:700;color:#333;margin:16px 0 4px;}
select,input[type=text],textarea{
  width:100%;box-sizing:border-box;padding:9px 12px;
  border:1.5px solid #cdd5e0;border-radius:6px;font-size:14px;color:#333;}
select:focus,input:focus,textarea:focus{border-color:#2471a3;outline:none;}
textarea{min-height:80px;resize:vertical;}
.hint{font-size:12px;color:#888;margin:3px 0 0;}
.err{background:#fde8e8;border-left:4px solid #dc3545;padding:10px 14px;
     border-radius:4px;margin-bottom:16px;font-size:13px;color:#721c24;}
.info{background:#e8f4f8;border-left:4px solid #2471a3;padding:10px 14px;
      border-radius:4px;font-size:13px;color:#1a2c5b;margin-bottom:16px;}
.ok{background:#d4edda;border-left:4px solid #28a745;padding:14px 18px;
    border-radius:4px;color:#155724;font-size:14px;}
.btn{display:block;width:100%;padding:13px;background:#2471a3;color:white;
     border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;margin-top:20px;}
.btn:hover{background:#1a2c5b;}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px;}
a{color:#2471a3;}
"""


def _page(title, body):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{_CSS}</style></head>
<body><div class="wrap"><div class="card">{body}</div></div></body></html>"""


class AttendanceCorrectionController(http.Controller):

    @http.route('/attendance-fix/<string:token>', type='http', auth='public', website=False, csrf=False)
    def correction_form(self, token, **post):
        report = request.env['hr.attendance.report'].sudo().search(
            [('ack_token', '=', token)], limit=1,
        )
        if not report:
            return _page('Enlace inválido', """
              <div class="hdr"><h1>&#128683; Enlace no válido</h1></div>
              <div class="body"><p>El enlace no es válido o ha expirado.
              Contacte a <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>.</p>
              </div>""")

        employee = report.employee_id
        absent_days = [d for d in report.get_attendance_days() if d['status'] == 'absent']

        if not absent_days:
            return _page('Sin ausencias', f"""
              <div class="hdr"><h1>&#9989; Sin ausencias registradas</h1></div>
              <div class="body"><p>El reporte de <strong>{employee.name}</strong>
              no tiene ausencias pendientes de corrección en este período.</p></div>""")

        if request.httprequest.method == 'POST':
            return self._handle_post(report, employee, absent_days, post)

        return self._render_form(report, employee, absent_days)

    # ── POST handler ──────────────────────────────────────────────────────────

    def _handle_post(self, report, employee, absent_days, post):
        date_str = post.get('correction_date', '').strip()
        ci_h     = post.get('ci_h', '').strip()
        ci_m     = post.get('ci_m', '00').strip()
        co_h     = post.get('co_h', '').strip()
        co_m     = post.get('co_m', '00').strip()
        reason   = post.get('reason', '').strip()
        ip       = (request.httprequest.headers.get('X-Forwarded-For')
                    or request.httprequest.remote_addr or '')[:50]

        check_in  = f"{ci_h}:{ci_m}" if ci_h else ''
        check_out = f"{co_h}:{co_m}" if co_h else ''

        errors = []
        valid_dates = {str(d['date']) for d in absent_days}
        if not date_str or date_str not in valid_dates:
            errors.append("Seleccione una fecha válida de la lista.")
        if not ci_h:
            errors.append("Seleccione la hora de entrada.")
        if not reason:
            errors.append("Explique brevemente el motivo de la incidencia.")

        if errors:
            return self._render_form(report, employee, absent_days, errors=errors, post=post)

        correction_date = date_cls.fromisoformat(date_str)

        # Guard: duplicate pending for same employee+date
        existing = request.env['hr.attendance.correction'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '=', correction_date),
            ('state', '=', 'pending'),
        ], limit=1)
        if existing:
            return _page('Ya enviada', f"""
              <div class="hdr"><h1>&#8987; Solicitud ya enviada</h1>
                <p>{employee.name}</p></div>
              <div class="body"><p>Ya existe una solicitud pendiente para el
              <strong>{correction_date.strftime('%d/%m/%Y')}</strong>.<br/>
              Recursos Humanos la revisará en breve.</p></div>""")

        correction = request.env['hr.attendance.correction'].sudo().create({
            'employee_id':          employee.id,
            'attendance_report_id': report.id,
            'date':                 correction_date,
            'check_in_time':        check_in,
            'check_out_time':       check_out or False,
            'reason':               reason,
            'submitted_ip':         ip or False,
        })

        # Notify HR — use sudo() for ref lookup (public user has no ir.model.data access)
        tmpl = request.env['ir.model.data'].sudo()._xmlid_to_res_id(
            'ueipab_attendance_report.email_template_correction_request'
        )
        if tmpl:
            request.env['mail.template'].sudo().browse(tmpl).send_mail(
                correction.id, force_send=True
            )

        day_label = correction_date.strftime('%d/%m/%Y')
        times = f"{check_in}" + (f" — {check_out}" if check_out else " (salida no registrada)")
        return _page('Solicitud enviada', f"""
          <div class="hdr"><h1>&#10003; Solicitud enviada correctamente</h1>
            <p>{employee.name}</p></div>
          <div class="body">
            <div class="ok">
              <strong>Su solicitud fue recibida y será revisada por Recursos Humanos.</strong><br/><br/>
              &#128197; Fecha: {day_label}<br/>
              &#8987; Horario solicitado: {times}<br/>
              &#128172; Motivo: {reason}
            </div>
            <p style="font-size:13px;color:#555;margin-top:18px;">
              Recibirá un correo de confirmación una vez que su solicitud sea procesada.<br/>
              ¿Tiene otra fecha por corregir?
              <a href="/attendance-fix/{report.ack_token}">Envíe otra solicitud</a>.
            </p>
            <p class="note">Instituto Privado Andrés Bello, CA &mdash; Recursos Humanos</p>
          </div>""")

    # ── GET form renderer ─────────────────────────────────────────────────────

    def _render_form(self, report, employee, absent_days, errors=None, post=None):
        post = post or {}

        # Date dropdown
        opts = '<option value="">— Seleccione una fecha —</option>'
        for d in absent_days:
            d_date = str(d['date'])
            label  = f"{_DAYS_ES.get(d['date'].weekday(), '')} {d['date_str']} — Sin registro"
            sel    = 'selected' if post.get('correction_date') == d_date else ''
            opts  += f'<option value="{d_date}" {sel}>{label}</option>'

        # Restore previous selections on validation error
        prev_ci_h = post.get('ci_h', '')
        prev_ci_m = post.get('ci_m', '00')
        prev_co_h = post.get('co_h', '')
        prev_co_m = post.get('co_m', '00')
        prev_reason = post.get('reason', '')

        err_html = ''
        if errors:
            items = ''.join(f'<li>{e}</li>' for e in errors)
            err_html = f'<div class="err"><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

        # Build time pickers using helper functions
        ci_picker = _time_picker(
            'ci', 'Hora de entrada *',
            hint='Hora aproximada en que llegó al trabajo',
            selected=f"{prev_ci_h}:{prev_ci_m}" if prev_ci_h else '',
            required=True,
        )
        co_picker = _time_picker(
            'co', 'Hora de salida',
            hint='Deje el selector en "─ hora" si no recuerda la salida',
            selected=f"{prev_co_h}:{prev_co_m}" if prev_co_h else '',
            optional_label='opcional',
        )

        period = report.get_period_label()

        body = f"""
          <div class="hdr">
            <h1>&#128295; Solicitar Corrección de Asistencia</h1>
            <p>Instituto Privado Andrés Bello, CA</p>
          </div>
          <div class="body">
            <div class="info">
              <strong>{employee.name}</strong> &#160;|&#160; {period}
            </div>
            {err_html}
            <form method="POST">
              <label style="display:block;font-size:13px;font-weight:700;color:#333;margin:0 0 6px;">
                Fecha con incidencia *
              </label>
              <select name="correction_date" required
                style="width:100%;box-sizing:border-box;padding:9px 12px;border:1.5px solid #cdd5e0;
                       border-radius:6px;font-size:14px;color:#333;">
                {opts}
              </select>

              {ci_picker}
              {co_picker}

              <label style="display:block;font-size:13px;font-weight:700;color:#333;margin:16px 0 4px;">
                Motivo de la incidencia *
              </label>
              <textarea name="reason" required
                style="width:100%;box-sizing:border-box;padding:9px 12px;border:1.5px solid #cdd5e0;
                       border-radius:6px;font-size:14px;color:#333;min-height:80px;resize:vertical;"
                placeholder="Ej: Corte de energía eléctrica — el marcador biométrico no funcionó">{prev_reason}</textarea>

              <button class="btn" type="submit">&#128228; Enviar Solicitud</button>
            </form>
            <p class="note">
              Su solicitud será revisada por Recursos Humanos antes del cierre de nómina.<br/>
              ¿Consultas? <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
            </p>
          </div>"""
        return _page('Corrección de Asistencia', body)
