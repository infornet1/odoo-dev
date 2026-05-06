import base64
from datetime import date as date_cls

from odoo import http
from odoo.http import request

_DAYS_ES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}

# Venezuela Labor Law (LOTTT / LOPCYMAT) predefined absence reasons
_MOTIVOS = [
    ('energia',    'Corte de energía eléctrica'),
    ('medico',     'Consulta o emergencia médica  (Art. 49 LOTTT)'),
    ('reposo',     'Reposo médico prescrito'),
    ('duelo',      'Duelo familiar  (Art. 49 LOTTT)'),
    ('judicial',   'Citación judicial u obligación legal'),
    ('matrimonio', 'Matrimonio del trabajador  (Art. 49 LOTTT)'),
    ('calamidad',  'Calamidad doméstica justificada'),
    ('otro',       'Otro motivo  (explique a continuación)'),
]
_MOTIVOS_DICT = dict(_MOTIVOS)
MAX_MB = 5  # max attachment size


# ── Time helpers ──────────────────────────────────────────────────────────────

def _to_24h(hour12, ampm):
    """Convert 12h hour string + AM/PM → 24h integer."""
    h = int(hour12)
    if ampm.upper() == 'AM':
        return 0 if h == 12 else h
    else:
        return h if h == 12 else h + 12


def _fmt_12h(time_24):
    """HH:MM (24h) → '12:30 PM' for display."""
    if not time_24 or len(time_24) < 5:
        return '—'
    h, m = int(time_24[:2]), time_24[3:5]
    ampm = 'AM' if h < 12 else 'PM'
    return f"{h % 12 or 12}:{m} {ampm}"


def _hour_sel(name, sel_h='', required=False):
    req = 'required' if required else ''
    opts = '<option value="">hr</option>'
    for h in range(1, 13):
        s = 'selected' if str(h) == sel_h else ''
        opts += f'<option value="{h}" {s}>{h:02d}</option>'
    return (
        f'<select name="{name}" {req} style="{_SEL_STYLE};width:72px;">{opts}</select>'
    )


def _min_sel(name, sel_m='00'):
    opts = ''
    for m in range(0, 60, 5):
        v = f'{m:02d}'
        s = 'selected' if v == sel_m else ''
        opts += f'<option value="{v}" {s}>{v}</option>'
    return f'<select name="{name}" style="{_SEL_STYLE};width:72px;">{opts}</select>'


def _ampm_sel(name, sel='AM'):
    opts = ''.join(
        f'<option value="{v}" {"selected" if v == sel else ""}>{v}</option>'
        for v in ('AM', 'PM')
    )
    return f'<select name="{name}" style="{_SEL_STYLE};width:72px;">{opts}</select>'


def _time_row(name, label, hint='', sel_h='', sel_m='00', sel_ap='AM',
              required=False, opt_label=''):
    badge = (f' <span style="color:#888;font-size:12px;font-weight:400;">'
             f'({opt_label})</span>') if opt_label else ''
    colon = '<span style="font-size:18px;font-weight:700;color:#555;padding:0 2px;">:</span>'
    hint_html = f'<p style="font-size:12px;color:#888;margin:3px 0 0;">{hint}</p>' if hint else ''
    return (
        f'<label style="{_LBL_STYLE}">{label}{badge}</label>'
        f'<div style="display:flex;align-items:center;gap:4px;">'
        f'{_hour_sel(name+"_hour", sel_h, required)}{colon}'
        f'{_min_sel(name+"_min", sel_m)}'
        f'{_ampm_sel(name+"_ampm", sel_ap)}</div>'
        f'{hint_html}'
    )


# ── Shared style strings ──────────────────────────────────────────────────────

_SEL_STYLE = ('padding:8px 10px;border:1.5px solid #cdd5e0;border-radius:6px;'
              'font-size:14px;color:#333;')
_LBL_STYLE = 'display:block;font-size:13px;font-weight:700;color:#333;margin:16px 0 6px;'

_CSS = """
body{margin:0;font-family:Arial,sans-serif;background:#f0f4fa;}
.wrap{max-width:600px;margin:40px auto;padding:16px;}
.card{background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;}
.hdr{background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;padding:24px 28px;}
.hdr h1{margin:0;font-size:20px;font-weight:700;}
.hdr p{margin:4px 0 0;font-size:13px;opacity:.85;}
.body{padding:24px 28px;}
select,textarea{width:100%;box-sizing:border-box;padding:9px 12px;
  border:1.5px solid #cdd5e0;border-radius:6px;font-size:14px;color:#333;}
select:focus,textarea:focus,input[type=file]:focus{border-color:#2471a3;outline:none;}
textarea{min-height:80px;resize:vertical;}
.hint{font-size:12px;color:#888;margin:3px 0 0;}
.err{background:#fde8e8;border-left:4px solid #dc3545;padding:10px 14px;
     border-radius:4px;margin-bottom:16px;font-size:13px;color:#721c24;}
.info{background:#e8f4f8;border-left:4px solid #2471a3;padding:10px 14px;
      border-radius:4px;font-size:13px;color:#1a2c5b;margin-bottom:16px;}
.ok{background:#d4edda;border-left:4px solid #28a745;padding:14px 18px;
    border-radius:4px;color:#155724;font-size:14px;line-height:1.7;}
.section{background:#f8f9fa;border-radius:6px;padding:14px 16px;margin-top:16px;}
.btn{display:block;width:100%;padding:13px;background:#2471a3;color:white;
     border:none;border-radius:8px;font-size:15px;font-weight:700;cursor:pointer;margin-top:20px;}
.btn:hover{background:#1a2c5b;}
.file-wrap{border:2px dashed #cdd5e0;border-radius:6px;padding:14px 16px;
           text-align:center;cursor:pointer;margin-top:6px;}
.file-wrap:hover{border-color:#2471a3;background:#f0f8ff;}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px;}
a{color:#2471a3;}
"""

_JS = """
<script>
function updateDetail(val){
  var lbl=document.getElementById('detail-label');
  var ta=document.getElementById('motivo-detail');
  if(val==='otro'){
    lbl.innerHTML='Explique el motivo <span style="color:#dc3545;">*</span>';
    ta.required=true;
    ta.placeholder='Describa detalladamente la razón de su ausencia…';
  } else {
    lbl.innerHTML='Detalles adicionales <span style="color:#888;font-size:12px;font-weight:400;">(opcional)</span>';
    ta.required=false;
    ta.placeholder='Puede agregar información adicional si lo considera necesario…';
  }
}
function showFile(input){
  var name=input.files[0]?input.files[0].name:'Ningún archivo seleccionado';
  document.getElementById('file-name').textContent=name;
}
</script>
"""


def _page(title, body):
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title}</title><style>{_CSS}</style></head>'
        f'<body><div class="wrap"><div class="card">{body}</div></div>'
        f'{_JS}</body></html>'
    )


# ── Controller ────────────────────────────────────────────────────────────────

class AttendanceCorrectionController(http.Controller):

    @http.route('/attendance-correction/<int:correction_id>', type='http',
                auth='user', website=False)
    def correction_review(self, correction_id, **kw):
        """Login-safe redirect to the specific correction record in Odoo backend.

        auth='user' means Odoo handles the login redirect automatically,
        preserving this URL as the redirect target. After login, this route
        redirects to the hash URL — at that point the session exists so the
        hash is processed correctly by the Odoo webclient.
        """
        base = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', ''
        ).rstrip('/')
        target = (
            f"{base}/web#id={correction_id}"
            f"&model=hr.attendance.correction&view_type=form"
        )
        return request.redirect(target)

    @http.route('/attendance-fix/<string:token>', type='http', auth='public',
                website=False, csrf=False)
    def correction_form(self, token, **post):
        report = request.env['hr.attendance.report'].sudo().search(
            [('ack_token', '=', token)], limit=1,
        )
        if not report:
            return _page('Enlace inválido', """
              <div class="hdr"><h1>&#128683; Enlace no válido</h1></div>
              <div class="body"><p>El enlace no es válido o ha expirado.
              Contacte a <a href="mailto:recursoshumanos@ueipab.edu.ve">
              recursoshumanos@ueipab.edu.ve</a>.</p></div>""")

        employee    = report.employee_id
        today       = date_cls.today()
        absent_days = [d for d in report.get_attendance_days()
                       if d['status'] == 'absent' and d['date'] <= today]

        if not absent_days:
            return _page('Sin ausencias', f"""
              <div class="hdr"><h1>&#9989; Sin ausencias registradas</h1></div>
              <div class="body"><p>El reporte de <strong>{employee.name}</strong>
              no tiene ausencias pendientes de corrección en este período.</p></div>""")

        if request.httprequest.method == 'POST':
            return self._handle_post(report, employee, absent_days, post)

        return self._render_form(report, employee, absent_days)

    # ── POST ─────────────────────────────────────────────────────────────────

    def _handle_post(self, report, employee, absent_days, post):
        # ── Time ─────────────────────────────────────────────────────────────
        ci_h  = post.get('ci_hour', '').strip()
        ci_m  = post.get('ci_min',  '00').strip()
        ci_ap = post.get('ci_ampm', 'AM').strip()
        co_h  = post.get('co_hour', '').strip()
        co_m  = post.get('co_min',  '00').strip()
        co_ap = post.get('co_ampm', 'AM').strip()

        check_in  = f"{_to_24h(ci_h, ci_ap):02d}:{ci_m}" if ci_h else ''
        check_out = f"{_to_24h(co_h, co_ap):02d}:{co_m}" if co_h else ''

        # ── Motivo ───────────────────────────────────────────────────────────
        motivo_key    = post.get('motivo', '').strip()
        motivo_detail = post.get('motivo_detail', '').strip()
        motivo_label  = _MOTIVOS_DICT.get(motivo_key, '')
        if motivo_detail:
            reason = f"{motivo_label}: {motivo_detail}" if motivo_label else motivo_detail
        else:
            reason = motivo_label

        # ── Attachment ───────────────────────────────────────────────────────
        att_file = request.httprequest.files.get('attachment')
        att_ok   = att_file and att_file.filename

        date_str    = post.get('correction_date', '').strip()
        valid_dates = {str(d['date']) for d in absent_days}
        ip = (request.httprequest.headers.get('X-Forwarded-For')
              or request.httprequest.remote_addr or '')[:50]

        # ── Validate ─────────────────────────────────────────────────────────
        errors = []
        if not date_str or date_str not in valid_dates:
            errors.append("Seleccione una fecha válida de la lista.")
        if not ci_h:
            errors.append("Seleccione la hora de entrada.")
        if not motivo_key:
            errors.append("Seleccione el motivo de la incidencia.")
        if motivo_key == 'otro' and not motivo_detail:
            errors.append("Seleccionó 'Otro motivo' — por favor explique a continuación.")
        if att_ok:
            att_file.seek(0)
            if len(att_file.read()) > MAX_MB * 1024 * 1024:
                errors.append(f"El archivo adjunto no puede superar {MAX_MB} MB.")
            att_file.seek(0)

        if errors:
            return self._render_form(
                report, employee, absent_days, errors=errors, post=post,
            )

        correction_date = date_cls.fromisoformat(date_str)

        # Guard: duplicate pending
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

        # Save attachment if provided
        if att_ok:
            att_file.seek(0)
            file_bytes = att_file.read()
            if file_bytes:
                request.env['ir.attachment'].sudo().create({
                    'name':      att_file.filename,
                    'datas':     base64.b64encode(file_bytes).decode(),
                    'res_model': 'hr.attendance.correction',
                    'res_id':    correction.id,
                    'mimetype':  att_file.content_type or 'application/octet-stream',
                })

        # Notify HR
        tmpl_id = request.env['ir.model.data'].sudo()._xmlid_to_res_id(
            'ueipab_attendance_report.email_template_correction_request'
        )
        if tmpl_id:
            request.env['mail.template'].sudo().browse(tmpl_id).send_mail(
                correction.id, force_send=True,
            )

        ci_disp = _fmt_12h(check_in)
        co_disp = _fmt_12h(check_out) if check_out else 'No indicada'
        att_note = f'<br/>&#128206; Adjunto: <em>{att_file.filename}</em>' if att_ok else ''

        return _page('Solicitud enviada', f"""
          <div class="hdr"><h1>&#10003; Solicitud enviada correctamente</h1>
            <p>{employee.name}</p></div>
          <div class="body">
            <div class="ok">
              <strong>Su solicitud fue recibida y será revisada por Recursos Humanos.</strong><br/>
              &#128197; <strong>Fecha:</strong> {correction_date.strftime('%d/%m/%Y')}<br/>
              &#9203; <strong>Entrada:</strong> {ci_disp} &nbsp;|&nbsp;
              <strong>Salida:</strong> {co_disp}<br/>
              &#128172; <strong>Motivo:</strong> {reason}{att_note}
            </div>
            <p style="font-size:13px;color:#555;margin-top:18px;">
              Recibirá una notificación por correo cuando su solicitud sea procesada.<br/>
              ¿Otra fecha por corregir?
              <a href="/attendance-fix/{report.ack_token}">Envíe otra solicitud</a>.
            </p>
            <p class="note">Instituto Privado Andrés Bello, CA &mdash; Recursos Humanos</p>
          </div>""")

    # ── GET form ──────────────────────────────────────────────────────────────

    def _render_form(self, report, employee, absent_days, errors=None, post=None):
        post = post or {}

        # Date dropdown
        date_opts = '<option value="">— Seleccione una fecha —</option>'
        for d in absent_days:
            d_date = str(d['date'])
            label  = f"{_DAYS_ES.get(d['date'].weekday(),'')} {d['date_str']} — Sin registro"
            sel    = 'selected' if post.get('correction_date') == d_date else ''
            date_opts += f'<option value="{d_date}" {sel}>{label}</option>'

        # Restore values on validation error
        ci_h  = post.get('ci_hour', '')
        ci_m  = post.get('ci_min',  '00')
        ci_ap = post.get('ci_ampm', 'AM')
        co_h  = post.get('co_hour', '')
        co_m  = post.get('co_min',  '00')
        co_ap = post.get('co_ampm', 'AM')
        prev_motivo  = post.get('motivo', '')
        prev_detail  = post.get('motivo_detail', '')

        err_html = ''
        if errors:
            items = ''.join(f'<li>{e}</li>' for e in errors)
            err_html = f'<div class="err"><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

        # Motivo dropdown
        motivo_opts = '<option value="">— Seleccione un motivo —</option>'
        for key, label in _MOTIVOS:
            sel = 'selected' if key == prev_motivo else ''
            motivo_opts += f'<option value="{key}" {sel}>{label}</option>'

        is_otro   = prev_motivo == 'otro'
        det_lbl   = ('Explique el motivo <span style="color:#dc3545;">*</span>'
                     if is_otro else
                     'Detalles adicionales <span style="color:#888;font-size:12px;'
                     'font-weight:400;">(opcional)</span>')
        det_req   = 'required' if is_otro else ''
        det_ph    = ('Describa detalladamente la razón de su ausencia…'
                     if is_otro else
                     'Puede agregar información adicional si lo considera necesario…')

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

            <form method="POST" enctype="multipart/form-data">

              <!-- Date -->
              <label style="{_LBL_STYLE}">Fecha con incidencia <span style="color:#dc3545;">*</span></label>
              <select name="correction_date" required style="{_SEL_STYLE};width:100%;">
                {date_opts}
              </select>

              <!-- Check-in -->
              <div class="section">
                <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#2471a3;
                          text-transform:uppercase;letter-spacing:.5px;">Hora de entrada</p>
                {_time_row('ci','Hora de entrada <span style="color:#dc3545;">*</span>',
                           hint='Hora aproximada en que llegó al trabajo',
                           sel_h=ci_h, sel_m=ci_m, sel_ap=ci_ap, required=True)}
              </div>

              <!-- Check-out -->
              <div class="section">
                <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#2471a3;
                          text-transform:uppercase;letter-spacing:.5px;">Hora de salida</p>
                {_time_row('co','Hora de salida',
                           hint='Deje «hr» si no recuerda la hora de salida',
                           sel_h=co_h, sel_m=co_m, sel_ap=co_ap, opt_label='opcional')}
              </div>

              <!-- Motivo -->
              <label style="{_LBL_STYLE}">
                Motivo de la incidencia <span style="color:#dc3545;">*</span>
              </label>
              <select name="motivo" id="motivo" required
                      style="{_SEL_STYLE};width:100%;"
                      onchange="updateDetail(this.value)">
                {motivo_opts}
              </select>
              <p class="hint">Razones reconocidas por la legislación laboral venezolana (LOTTT / LOPCYMAT)</p>

              <label id="detail-label" style="{_LBL_STYLE}">{det_lbl}</label>
              <textarea id="motivo-detail" name="motivo_detail"
                        {det_req} placeholder="{det_ph}">{prev_detail}</textarea>

              <!-- Attachment -->
              <label style="{_LBL_STYLE}">
                Documento de soporte
                <span style="color:#888;font-size:12px;font-weight:400;">(opcional)</span>
              </label>
              <div class="file-wrap" onclick="document.getElementById('att-input').click()">
                <p style="margin:0 0 4px;font-size:13px;color:#2471a3;font-weight:600;">
                  &#128206; Adjuntar archivo
                </p>
                <p id="file-name" style="margin:0;font-size:12px;color:#888;">
                  Ningún archivo seleccionado
                </p>
              </div>
              <input id="att-input" type="file" name="attachment"
                     accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                     style="display:none;" onchange="showFile(this)"/>
              <p class="hint">Reposo médico, permiso, foto del marcador, etc.
                              Formatos: PDF, JPG, PNG, DOC &mdash; Máx. {MAX_MB} MB</p>

              <button class="btn" type="submit">&#128228; Enviar Solicitud</button>
            </form>

            <p class="note">
              Su solicitud será revisada por Recursos Humanos antes del cierre de nómina.<br/>
              ¿Consultas? <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
            </p>
          </div>"""
        return _page('Corrección de Asistencia', body)
