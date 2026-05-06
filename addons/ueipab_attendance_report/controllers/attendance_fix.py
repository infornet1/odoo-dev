import re
from datetime import date as date_cls

from odoo import http
from odoo.http import request

_DAYS_ES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}

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

    @http.route('/attendance-fix/<string:token>', auth='public', methods=['GET', 'POST'], csrf=False)
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
        date_str  = post.get('correction_date', '').strip()
        check_in  = post.get('check_in_time', '').strip()
        check_out = post.get('check_out_time', '').strip()
        reason    = post.get('reason', '').strip()
        ip        = (request.httprequest.headers.get('X-Forwarded-For')
                     or request.httprequest.remote_addr or '')[:50]

        errors = []
        valid_dates = {str(d['date']) for d in absent_days}
        if not date_str or date_str not in valid_dates:
            errors.append("Seleccione una fecha válida de la lista.")
        if not check_in or not re.match(r'^\d{2}:\d{2}$', check_in):
            errors.append("Ingrese la hora de entrada en formato HH:MM (ej: 07:30).")
        if check_out and not re.match(r'^\d{2}:\d{2}$', check_out):
            errors.append("La hora de salida debe estar en formato HH:MM o dejarse vacía.")
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

        # Notify HR
        tmpl = request.env.ref(
            'ueipab_attendance_report.email_template_correction_request',
            raise_if_not_found=False,
        )
        if tmpl:
            tmpl.sudo().send_mail(correction.id, force_send=True)

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

        opts = '<option value="">— Seleccione una fecha —</option>'
        for d in absent_days:
            label = f"{_DAYS_ES.get(d['date'].weekday(), '')} {d['date_str']} — Sin registro"
            sel = 'selected' if post.get('correction_date') == str(d['date']) else ''
            opts += f'<option value="{d["date"]}" {sel}>{label}</option>'

        err_html = ''
        if errors:
            items = ''.join(f'<li>{e}</li>' for e in errors)
            err_html = f'<div class="err"><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

        prev_ci     = post.get('check_in_time', '')
        prev_co     = post.get('check_out_time', '')
        prev_reason = post.get('reason', '')
        period      = report.get_period_label()

        body = f"""
          <div class="hdr">
            <h1>&#128295; Solicitar Corrección de Asistencia</h1>
            <p>Instituto Privado Andrés Bello, CA</p>
          </div>
          <div class="body">
            <div class="info">
              <strong>{employee.name}</strong> &nbsp;|&nbsp; {period}
            </div>
            {err_html}
            <form method="POST">
              <label>Fecha con incidencia *</label>
              <select name="correction_date" required>{opts}</select>

              <label>Hora de entrada (HH:MM) *</label>
              <input type="text" name="check_in_time" placeholder="07:30"
                     value="{prev_ci}" maxlength="5" required/>
              <p class="hint">Hora aproximada en que llegó al trabajo</p>

              <label>Hora de salida (HH:MM)
                <span style="font-weight:400;color:#888;">(opcional — si la recuerda)</span>
              </label>
              <input type="text" name="check_out_time" placeholder="15:00"
                     value="{prev_co}" maxlength="5"/>

              <label>Motivo de la incidencia *</label>
              <textarea name="reason" required
                placeholder="Ej: Corte de energía eléctrica — el marcador biométrico no funcionó">{prev_reason}</textarea>

              <button class="btn" type="submit">&#128228; Enviar Solicitud</button>
            </form>
            <p class="note">
              Su solicitud será revisada por Recursos Humanos antes del cierre de nómina.<br/>
              ¿Consultas? <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
            </p>
          </div>"""
        return _page('Corrección de Asistencia', body)
