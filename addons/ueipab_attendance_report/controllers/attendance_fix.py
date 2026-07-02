import base64
import hmac as _hmac
from datetime import date as date_cls, datetime as _datetime, timedelta as _timedelta

from odoo import http
from odoo.http import request

_DAYS_ES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}

# Venezuela Labor Law (LOTTT / LOPCYMAT) predefined absence reasons
_MOTIVOS = [
    ('energia',      'Corte de energía eléctrica'),
    ('medico',       'Consulta o emergencia médica  (Art. 49 LOTTT)'),
    ('reposo',       'Reposo médico prescrito'),
    ('duelo',        'Duelo familiar  (Art. 49 LOTTT)'),
    ('judicial',     'Citación judicial u obligación legal'),
    ('matrimonio',   'Matrimonio del trabajador  (Art. 49 LOTTT)'),
    ('calamidad',    'Calamidad doméstica justificada'),
    ('capacitacion', 'Participación en capacitación, taller y/o evento institucional'),
    ('otro',         'Otro motivo  (explique a continuación)'),
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
#proc-banner{display:none;position:fixed;bottom:0;left:0;right:0;z-index:9999;
  background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;
  padding:14px 20px;box-shadow:0 -4px 16px rgba(0,0,0,.25);
  animation:slideUp .3s ease-out;}
@keyframes slideUp{from{transform:translateY(100%);}to{transform:translateY(0);}}
#proc-banner .pb-inner{max-width:600px;margin:0 auto;display:flex;
  align-items:flex-start;gap:12px;}
#proc-banner .pb-spin{font-size:22px;flex-shrink:0;animation:spin 1.2s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
#proc-banner .pb-text{font-size:13px;line-height:1.6;}
#proc-banner .pb-text strong{display:block;font-size:14px;margin-bottom:2px;}
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


_DAYS_LABEL = {
    0: 'lunes', 1: 'martes', 2: 'miércoles',
    3: 'jueves', 4: 'viernes', 5: 'sábados', 6: 'domingos',
}


def _suggest_checkout(env, emp_id, target_date):
    """Return (h12_str, mm_str, ampm_str, label) for the pre-selected checkout suggestion.

    3-tier fallback:
      1. ≥3 clean records on same weekday → weekday median
      2. ≥5 clean records any weekday    → all-day median
      3. default                         → 17:00 PM
    "Clean" = session duration ≥ 3 h (filters auto-fill artifacts).
    Weekday is taken from check_in VET (the day the shift started).
    Result is rounded to nearest 5 min and clamped to 07:00–21:00 VET.
    """
    target_wd = target_date.weekday()
    recs = env['hr.attendance'].sudo().search(
        [('employee_id', '=', emp_id), ('check_out', '!=', False)],
        order='check_in desc', limit=60,
    )

    all_clean, wd_clean = [], []
    for r in recs:
        if (r.check_out - r.check_in).total_seconds() < 3 * 3600:
            continue
        ci_vet = r.check_in  - _timedelta(hours=4)
        co_vet = r.check_out - _timedelta(hours=4)
        m = co_vet.hour * 60 + co_vet.minute
        all_clean.append(m)
        if ci_vet.weekday() == target_wd:
            wd_clean.append(m)

    def _pick(pool):
        raw = sorted(pool)[len(pool) // 2]        # median
        return max(7 * 60, min(21 * 60, round(raw / 5) * 5))  # clamp + round

    if len(wd_clean) >= 3:
        mins = _pick(wd_clean)
        label = f'Sugerido según tu historial de los {_DAYS_LABEL.get(target_wd, "")}'
    elif len(all_clean) >= 5:
        mins = _pick(all_clean)
        label = 'Sugerido según tu historial general'
    else:
        return '12', '45', 'PM', 'Hora estándar de cierre'

    h24   = mins // 60
    mm    = f'{mins % 60:02d}'
    ampm  = 'AM' if h24 < 12 else 'PM'
    h12   = str(h24 % 12 or 12)
    return h12, mm, ampm, label


def _make_direct_sig(secret: str, emp_id: int, date_str: str) -> str:
    """HMAC-SHA256 signature for a direct fix URL (first 16 hex chars)."""
    return _hmac.new(secret.encode(), f"{emp_id}:{date_str}".encode(), 'sha256').hexdigest()[:16]


def _utc_to_vet_str(utc_val) -> str:
    """Convert an Odoo UTC datetime (str or datetime) to VET HH:MM string."""
    if not utc_val:
        return ''
    try:
        if isinstance(utc_val, str):
            utc_val = _datetime.fromisoformat(utc_val.replace('Z', ''))
        return (utc_val + _timedelta(hours=-4)).strftime('%H:%M')
    except Exception:
        return ''


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

        employee = report.employee_id
        today    = date_cls.today()
        all_days = report.get_attendance_days()
        # Include both absent AND missing_exit days — both are correctable
        incident_days = [d for d in all_days
                         if d['status'] in ('absent', 'missing_exit')
                         and d['date'] <= today]

        if not incident_days:
            return _page('Sin incidencias', f"""
              <div class="hdr"><h1>&#9989; Sin incidencias registradas</h1></div>
              <div class="body"><p>El reporte de <strong>{employee.name}</strong>
              no tiene ausencias ni salidas pendientes en este período.</p></div>""")

        if request.httprequest.method == 'POST':
            return self._handle_post(report, employee, incident_days, post)

        return self._render_form(report, employee, incident_days)

    # ── POST ─────────────────────────────────────────────────────────────────

    def _handle_post(self, report, employee, incident_days, post):
        # ── Decode encoded date value: "absent|2026-05-15" or "missing_exit|2026-05-15" ──
        raw_date  = post.get('correction_date', '').strip()
        parts     = raw_date.split('|', 1)
        day_type  = parts[0] if len(parts) == 2 else ''
        date_str  = parts[1] if len(parts) == 2 else ''
        valid_map = {f"{d['status']}|{d['date']}": d for d in incident_days}

        # ── Time ─────────────────────────────────────────────────────────────
        ci_h  = post.get('ci_hour', '').strip()
        ci_m  = post.get('ci_min',  '00').strip()
        ci_ap = post.get('ci_ampm', 'AM').strip()
        co_h  = post.get('co_hour', '').strip()
        co_m  = post.get('co_min',  '00').strip()
        co_ap = post.get('co_ampm', 'AM').strip()

        check_in  = f"{_to_24h(ci_h, ci_ap):02d}:{ci_m}" if ci_h else ''
        check_out = f"{_to_24h(co_h, co_ap):02d}:{co_m}" if co_h else ''

        # For missing_exit: check_in comes from hidden field (actual recorded value)
        if day_type == 'missing_exit' and not check_in:
            check_in = post.get('existing_checkin', '').strip()

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

        ip = (request.httprequest.headers.get('X-Forwarded-For')
              or request.httprequest.remote_addr or '')[:50]

        # ── Validate ─────────────────────────────────────────────────────────
        errors = []
        if not raw_date or raw_date not in valid_map:
            errors.append("Seleccione una fecha válida de la lista.")
        if day_type == 'absent' and not ci_h:
            errors.append("Seleccione la hora de entrada.")
        if day_type == 'missing_exit' and not co_h:
            errors.append("Seleccione la hora de salida.")
        if not motivo_key:
            errors.append("Seleccione el motivo de la solicitud de corrección.")
        if motivo_key == 'otro' and not motivo_detail:
            errors.append("Seleccionó 'Otro motivo' — por favor explique a continuación.")
        if att_ok:
            att_file.seek(0)
            if len(att_file.read()) > MAX_MB * 1024 * 1024:
                errors.append(f"El archivo adjunto no puede superar {MAX_MB} MB.")
            att_file.seek(0)

        if errors:
            return self._render_form(
                report, employee, incident_days, errors=errors, post=post,
            )

        correction_date = date_cls.fromisoformat(date_str)

        # Update existing record (pending or under_revision) rather than creating a new one.
        # under_revision means RRHH re-invited the employee — we update in place and reset to pending.
        existing = request.env['hr.attendance.correction'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '=', correction_date),
            ('state', 'in', ('pending', 'under_revision')),
        ], limit=1)

        if existing:
            existing.sudo().write({
                'check_in_time':  check_in,
                'check_out_time': check_out or False,
                'reason':         reason,
                'motivo_key':     motivo_key,
                'submitted_ip':   ip or False,
                'state':          'pending',
            })
            correction = existing
        else:
            correction = request.env['hr.attendance.correction'].sudo().create({
                'employee_id':          employee.id,
                'attendance_report_id': report.id,
                'date':                 correction_date,
                'check_in_time':        check_in,
                'check_out_time':       check_out or False,
                'reason':               reason,
                'motivo_key':           motivo_key,
                'submitted_ip':         ip or False,
            })

        # Save attachment if provided — linked via Many2many for inline display
        if att_ok:
            att_file.seek(0)
            file_bytes = att_file.read()
            if file_bytes:
                att = request.env['ir.attachment'].sudo().create({
                    'name':      att_file.filename,
                    'datas':     base64.b64encode(file_bytes).decode(),
                    'res_model': 'hr.attendance.correction',
                    'res_id':    correction.id,
                    'mimetype':  att_file.content_type or 'application/octet-stream',
                })
                correction.sudo().write({'attachment_ids': [(4, att.id)]})

        # Notify HR
        tmpl_id = request.env['ir.model.data'].sudo()._xmlid_to_res_id(
            'ueipab_attendance_report.email_template_correction_request'
        )
        if tmpl_id:
            request.env['mail.template'].sudo().browse(tmpl_id).send_mail(
                correction.id, force_send=True,
            )

        # Confirmation email to employee — CC recursoshumanos@
        emp_email = employee.work_email or ''
        if emp_email:
            ci_disp_c = _fmt_12h(check_in)
            co_disp_c = _fmt_12h(check_out) if check_out else '— no indicada'
            att_line  = f'<br/>📎 Adjunto: <em>{att_file.filename}</em>' if att_ok else ''
            conf_body = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">
  <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;padding:20px 26px;">
    <h2 style="margin:0;font-size:17px;">&#128295; Solicitud de corrección recibida</h2>
    <p style="margin:4px 0 0;font-size:12px;opacity:.85;">Instituto Privado Andrés Bello, CA</p>
  </div>
  <div style="padding:22px 26px;">
    <p style="font-size:14px;color:#333;">Estimado/a <strong>{employee.name}</strong>,</p>
    <p style="font-size:13px;color:#555;line-height:1.6;">
      Hemos recibido tu solicitud de corrección de asistencia. Recursos Humanos la revisará
      antes del cierre de nómina y te notificará con el resultado.
    </p>
    <div style="background:#d4edda;border-left:4px solid #28a745;padding:12px 16px;
                border-radius:4px;margin:16px 0;font-size:13px;color:#155724;line-height:1.8;">
      &#128197; <strong>Fecha:</strong> {correction_date.strftime('%d/%m/%Y')}<br/>
      &#9203; <strong>Entrada:</strong> {ci_disp_c} &nbsp;|&nbsp;
              <strong>Salida:</strong> {co_disp_c}<br/>
      &#128172; <strong>Motivo:</strong> {reason}{att_line}
    </div>
    <p style="font-size:12px;color:#888;margin:0;">
      ¿Tienes otra fecha por corregir?
      <a href="/attendance-fix/{report.ack_token}" style="color:#2471a3;">Envía otra solicitud</a>.
    </p>
    <p style="font-size:12px;color:#888;margin:14px 0 0;">Cordialmente,<br/>
      <strong>Recursos Humanos</strong> — Instituto Privado Andrés Bello, CA</p>
  </div>
</div></div>"""
            cc_parts = ['recursoshumanos@ueipab.edu.ve']
            if emp_email != 'arcides.arzola@ueipab.edu.ve':
                cc_parts.append('arcides.arzola@ueipab.edu.ve')
            request.env['mail.mail'].sudo().create({
                'subject':    f'✅ Solicitud de corrección recibida — {correction_date.strftime("%d/%m/%Y")}',
                'email_from': '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
                'email_to':   f'"{employee.name}" <{emp_email}>',
                'email_cc':   ', '.join(cc_parts),
                'body_html':  conf_body,
                'state':      'outgoing',
            }).send()

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

    def _render_form(self, report, employee, incident_days, errors=None, post=None):
        post = post or {}

        # Build day lookup for JS: date-value → existing check_in
        day_meta = {}
        for d in incident_days:
            val = f"{d['status']}|{d['date']}"
            day_meta[val] = {
                'type':     d['status'],
                'checkin':  d.get('check_in_str', '') or '',
            }

        # Date dropdown — encode type|date in value for disambiguation
        prev_date_val = post.get('correction_date', '')
        date_opts = '<option value="">— Seleccione una fecha —</option>'
        for d in incident_days:
            val   = f"{d['status']}|{d['date']}"
            icon  = '⚠️' if d['status'] == 'missing_exit' else '❌'
            tag   = 'Sin salida' if d['status'] == 'missing_exit' else 'Sin registro'
            label = f"{icon} {_DAYS_ES.get(d['date'].weekday(),'')} {d['date_str']} — {tag}"
            sel   = 'selected' if prev_date_val == val else ''
            date_opts += f'<option value="{val}" {sel}>{label}</option>'

        # JS map for dynamic form adaptation
        import json as _json
        js_meta = _json.dumps(day_meta)

        # Restore values on validation error
        ci_h  = post.get('ci_hour', '')
        ci_m  = post.get('ci_min',  '00')
        ci_ap = post.get('ci_ampm', 'AM')
        co_h  = post.get('co_hour', '')
        co_m  = post.get('co_min',  '00')
        co_ap = post.get('co_ampm', 'AM')
        prev_motivo  = post.get('motivo', '')
        prev_detail  = post.get('motivo_detail', '')
        prev_checkin = post.get('existing_checkin', '')

        err_html = ''
        if errors:
            items = ''.join(f'<li>{e}</li>' for e in errors)
            err_html = f'<div class="err"><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

        # Motivo dropdown
        motivo_opts = '<option value="">— Seleccione un motivo —</option>'
        for key, label in _MOTIVOS:
            sel = 'selected' if key == prev_motivo else ''
            motivo_opts += f'<option value="{key}" {sel}>{label}</option>'

        is_otro = prev_motivo == 'otro'
        det_lbl = ('Explique el motivo <span style="color:#dc3545;">*</span>'
                   if is_otro else
                   'Detalles adicionales <span style="color:#888;font-size:12px;'
                   'font-weight:400;">(opcional)</span>')
        det_req = 'required' if is_otro else ''
        det_ph  = ('Describa detalladamente la razón de su ausencia…'
                   if is_otro else
                   'Puede agregar información adicional si lo considera necesario…')

        period = report.get_period_label()

        # Determine initial form mode (absent vs missing_exit) for page load
        init_type   = day_meta.get(prev_date_val, {}).get('type', 'absent')
        init_checkin= day_meta.get(prev_date_val, {}).get('checkin', '') or prev_checkin
        ci_display  = 'none' if init_type == 'missing_exit' else 'block'
        me_display  = 'block' if init_type == 'missing_exit' else 'none'

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

            <form method="POST" enctype="multipart/form-data" id="fix-form">
              <input type="hidden" name="existing_checkin" id="existing_checkin"
                     value="{init_checkin}"/>

              <!-- Date -->
              <label style="{_LBL_STYLE}">
                Fecha con incidencia <span style="color:#dc3545;">*</span>
              </label>
              <select name="correction_date" id="correction_date" required
                      style="{_SEL_STYLE};width:100%;" onchange="adaptForm(this.value)">
                {date_opts}
              </select>

              <!-- Missing-exit notice (shown when a ⚠️ day is selected) -->
              <div id="me-notice" style="display:{me_display};margin-top:12px;">
                <div class="info" id="me-info">
                  &#9888;&#65039; Ya tiene <strong>entrada registrada</strong> a las
                  <strong id="me-checkin">{init_checkin or '—'}</strong>.
                  Solo indique la hora de salida correcta.
                </div>
              </div>

              <!-- Check-in (only for absent days) -->
              <div id="ci-section" style="display:{ci_display};">
                <div class="section">
                  <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#2471a3;
                            text-transform:uppercase;letter-spacing:.5px;">Hora de entrada</p>
                  {_time_row('ci','Hora de entrada <span style="color:#dc3545;">*</span>',
                             hint='Hora aproximada en que llegó al trabajo',
                             sel_h=ci_h, sel_m=ci_m, sel_ap=ci_ap, required=False)}
                </div>
              </div>

              <!-- Check-out (always shown; required for missing_exit) -->
              <div class="section">
                <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#2471a3;
                          text-transform:uppercase;letter-spacing:.5px;">
                  Hora de salida
                  <span id="co-required-badge" style="color:#dc3545;
                        display:{'inline' if init_type=='missing_exit' else 'none'};">*</span>
                  <span id="co-optional-badge" style="color:#888;font-size:11px;font-weight:400;
                        display:{'none' if init_type=='missing_exit' else 'inline'};">(opcional)</span>
                </p>
                {_time_row('co','Hora de salida',
                           hint='Deje «hr» si no recuerda la hora exacta',
                           sel_h=co_h, sel_m=co_m, sel_ap=co_ap, required=False)}
              </div>

              <!-- Motivo -->
              <label style="{_LBL_STYLE}">
                Motivo de la solicitud de corrección <span style="color:#dc3545;">*</span>
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

              <button class="btn" type="submit" id="submit-btn">&#128228; Enviar Solicitud</button>
            </form>

            <div id="proc-banner">
              <div class="pb-inner">
                <span class="pb-spin">&#9881;&#65039;</span>
                <div class="pb-text">
                  <strong>&#128338; Espere — su solicitud está siendo procesada.</strong>
                  Aguarde un momento antes de reintentarlo. Si no ha recibido el correo
                  de confirmación en unos minutos, puede volver a intentarlo.
                </div>
              </div>
            </div>

            <p class="note">
              Su solicitud será revisada por Recursos Humanos antes del cierre de nómina.<br/>
              ¿Consultas?
              <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
            </p>
          </div>
          <script>
          var _META = {js_meta};
          function adaptForm(val) {{
            var d = _META[val] || {{}};
            var isME = (d.type === 'missing_exit');
            var ci = d.checkin || '';
            document.getElementById('existing_checkin').value = ci;
            document.getElementById('me-notice').style.display = isME ? 'block' : 'none';
            document.getElementById('me-checkin').textContent  = ci || '—';
            document.getElementById('ci-section').style.display= isME ? 'none' : 'block';
            document.getElementById('co-required-badge').style.display = isME ? 'inline' : 'none';
            document.getElementById('co-optional-badge').style.display = isME ? 'none' : 'inline';
          }}
          document.getElementById('fix-form').addEventListener('submit', function() {{
            var btn = document.getElementById('submit-btn');
            btn.disabled = true;
            btn.textContent = '⏳ Enviando…';
            document.getElementById('proc-banner').style.display = 'block';
          }});
          </script>"""
        return _page('Corrección de Asistencia', body)

    # ── Direct fix route (no report required) ────────────────────────────────

    @http.route('/attendance-fix-open/<int:emp_id>/<string:date_str>/<string:sig>',
                type='http', auth='public', website=False, csrf=False)
    def correction_form_direct(self, emp_id, date_str, sig, **post):
        """Public correction form signed with HMAC — no attendance report needed."""
        # 1. Verify HMAC signature
        secret = request.env['ir.config_parameter'].sudo().get_param('attendance.fix_secret', '')
        if not secret or not _hmac.compare_digest(sig, _make_direct_sig(secret, emp_id, date_str)):
            return _page('Enlace inválido', """
              <div class="hdr"><h1>&#128683; Enlace no válido</h1></div>
              <div class="body"><p>Este enlace no es válido o ha expirado.
              Por favor contacte a <a href="mailto:recursoshumanos@ueipab.edu.ve">
              recursoshumanos@ueipab.edu.ve</a>.</p></div>""")

        # 2. Parse date
        try:
            target_date = date_cls.fromisoformat(date_str)
        except ValueError:
            return _page('Enlace inválido', """
              <div class="hdr"><h1>Fecha inválida</h1></div>
              <div class="body"></div>""")

        # 3. Look up employee
        employee = request.env['hr.employee'].sudo().browse(emp_id)
        if not employee.exists():
            return _page('Enlace inválido', """
              <div class="hdr"><h1>Empleado no encontrado</h1></div>
              <div class="body"></div>""")

        # 4. Determine issue type from actual attendance
        next_date = target_date + _timedelta(days=1)
        att = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', emp_id),
            ('check_in',    '>=', f'{date_str} 00:00:00'),
            ('check_in',    '<',  f'{next_date} 00:00:00'),
        ], limit=1)

        if att and att.check_in and not att.check_out:
            issue_type = 'missing_exit'
            existing_checkin_vet = _utc_to_vet_str(att.check_in)
        else:
            issue_type = 'absent'
            existing_checkin_vet = ''

        if request.httprequest.method == 'POST':
            return self._handle_direct_post(employee, target_date, issue_type,
                                            existing_checkin_vet, post)
        return self._render_direct_form(employee, target_date, issue_type,
                                        existing_checkin_vet)

    def _handle_direct_post(self, employee, target_date, issue_type,
                             existing_checkin_vet, post):
        ci_h  = post.get('ci_hour', '').strip()
        ci_m  = post.get('ci_min',  '00').strip()
        ci_ap = post.get('ci_ampm', 'AM').strip()
        co_h  = post.get('co_hour', '').strip()
        co_m  = post.get('co_min',  '00').strip()
        co_ap = post.get('co_ampm', 'AM').strip()

        check_in  = f"{_to_24h(ci_h, ci_ap):02d}:{ci_m}" if ci_h else ''
        check_out = f"{_to_24h(co_h, co_ap):02d}:{co_m}" if co_h else ''

        if issue_type == 'missing_exit':
            check_in = existing_checkin_vet or post.get('existing_checkin', '').strip()

        motivo_key    = post.get('motivo', '').strip()
        motivo_detail = post.get('motivo_detail', '').strip()
        motivo_label  = _MOTIVOS_DICT.get(motivo_key, '')
        if motivo_detail and motivo_label:
            reason = f"{motivo_label}: {motivo_detail}"
        else:
            reason = motivo_detail or motivo_label

        att_file = request.httprequest.files.get('attachment')
        att_ok   = att_file and att_file.filename
        ip = (request.httprequest.headers.get('X-Forwarded-For')
              or request.httprequest.remote_addr or '')[:50]

        errors = []
        if issue_type == 'absent' and not ci_h:
            errors.append("Seleccione la hora de entrada.")
        if issue_type == 'missing_exit' and not co_h:
            errors.append("Seleccione la hora de salida.")
        if not motivo_key:
            errors.append("Seleccione el motivo de la solicitud de corrección.")
        if motivo_key == 'otro' and not motivo_detail:
            errors.append("Explique el motivo detalladamente.")
        if att_ok:
            att_file.seek(0)
            if len(att_file.read()) > MAX_MB * 1024 * 1024:
                errors.append(f"El archivo adjunto no puede superar {MAX_MB} MB.")
            att_file.seek(0)

        if errors:
            return self._render_direct_form(employee, target_date, issue_type,
                                             existing_checkin_vet, errors, post)

        existing = request.env['hr.attendance.correction'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date',        '=', target_date),
            ('state',       'in', ('pending', 'under_revision')),
        ], limit=1)

        if existing:
            existing.sudo().write({
                'check_in_time':  check_in,
                'check_out_time': check_out or False,
                'reason':         reason,
                'motivo_key':     motivo_key,
                'submitted_ip':   ip or False,
                'state':          'pending',
            })
            correction = existing
        else:
            correction = request.env['hr.attendance.correction'].sudo().create({
                'employee_id':   employee.id,
                # attendance_report_id intentionally omitted — direct alert link
                'date':          target_date,
                'check_in_time': check_in,
                'check_out_time': check_out or False,
                'reason':        reason,
                'motivo_key':    motivo_key,
                'submitted_ip':  ip or False,
            })

        if att_ok:
            att_file.seek(0)
            file_bytes = att_file.read()
            if file_bytes:
                att = request.env['ir.attachment'].sudo().create({
                    'name':      att_file.filename,
                    'datas':     base64.b64encode(file_bytes).decode(),
                    'res_model': 'hr.attendance.correction',
                    'res_id':    correction.id,
                    'mimetype':  att_file.content_type or 'application/octet-stream',
                })
                correction.sudo().write({'attachment_ids': [(4, att.id)]})

        tmpl_id = request.env['ir.model.data'].sudo()._xmlid_to_res_id(
            'ueipab_attendance_report.email_template_correction_request'
        )
        if tmpl_id:
            request.env['mail.template'].sudo().browse(tmpl_id).send_mail(
                correction.id, force_send=True,
            )

        emp_email = employee.work_email or ''
        if emp_email:
            ci_disp_c = _fmt_12h(check_in)
            co_disp_c = _fmt_12h(check_out) if check_out else '— no indicada'
            att_line  = f'<br/>&#128206; Adjunto: <em>{att_file.filename}</em>' if att_ok else ''
            conf_body = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">
  <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;padding:20px 26px;">
    <h2 style="margin:0;font-size:17px;">&#128295; Solicitud de corrección recibida</h2>
    <p style="margin:4px 0 0;font-size:12px;opacity:.85;">Instituto Privado Andrés Bello, CA</p>
  </div>
  <div style="padding:22px 26px;">
    <p style="font-size:14px;color:#333;">Estimado/a <strong>{employee.name}</strong>,</p>
    <p style="font-size:13px;color:#555;line-height:1.6;">
      Hemos recibido tu solicitud de corrección de asistencia. Recursos Humanos la revisará
      antes del cierre de nómina y te notificará con el resultado.
    </p>
    <div style="background:#d4edda;border-left:4px solid #28a745;padding:12px 16px;
                border-radius:4px;margin:16px 0;font-size:13px;color:#155724;line-height:1.8;">
      &#128197; <strong>Fecha:</strong> {target_date.strftime('%d/%m/%Y')}<br/>
      &#9203; <strong>Entrada:</strong> {ci_disp_c} &nbsp;|&nbsp;
              <strong>Salida:</strong> {co_disp_c}<br/>
      &#128172; <strong>Motivo:</strong> {reason}{att_line}
    </div>
    <p style="font-size:12px;color:#888;margin:14px 0 0;">Cordialmente,<br/>
      <strong>Recursos Humanos</strong> — Instituto Privado Andrés Bello, CA</p>
  </div>
</div></div>"""
            cc_parts = ['recursoshumanos@ueipab.edu.ve']
            if emp_email != 'arcides.arzola@ueipab.edu.ve':
                cc_parts.append('arcides.arzola@ueipab.edu.ve')
            request.env['mail.mail'].sudo().create({
                'subject':    f'&#10003; Solicitud de corrección recibida — {target_date.strftime("%d/%m/%Y")}',
                'email_from': '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
                'email_to':   f'"{employee.name}" <{emp_email}>',
                'email_cc':   ', '.join(cc_parts),
                'body_html':  conf_body,
                'state':      'outgoing',
            }).send()

        ci_disp  = _fmt_12h(check_in)
        co_disp  = _fmt_12h(check_out) if check_out else 'No indicada'
        att_note = f'<br/>&#128206; Adjunto: <em>{att_file.filename}</em>' if att_ok else ''

        return _page('Solicitud enviada', f"""
          <div class="hdr"><h1>&#10003; Solicitud enviada correctamente</h1>
            <p>{employee.name}</p></div>
          <div class="body">
            <div class="ok">
              <strong>Su solicitud fue recibida y será revisada por Recursos Humanos.</strong><br/>
              &#128197; <strong>Fecha:</strong> {target_date.strftime('%d/%m/%Y')}<br/>
              &#9203; <strong>Entrada:</strong> {ci_disp} &nbsp;|&nbsp;
              <strong>Salida:</strong> {co_disp}<br/>
              &#128172; <strong>Motivo:</strong> {reason}{att_note}
            </div>
            <p style="font-size:13px;color:#555;margin-top:18px;">
              Recibirá una notificación por correo cuando su solicitud sea procesada.
            </p>
            <p class="note">Instituto Privado Andrés Bello, CA &mdash; Recursos Humanos</p>
          </div>""")

    def _render_direct_form(self, employee, target_date, issue_type,
                             existing_checkin_vet, errors=None, post=None):
        post   = post or {}
        errors = errors or []
        date_str  = str(target_date)
        date_disp = f"{_DAYS_ES.get(target_date.weekday(), '')} {target_date.strftime('%d/%m/%Y')}"

        err_html = ''
        if errors:
            items    = ''.join(f'<li>{e}</li>' for e in errors)
            err_html = f'<div class="err"><ul style="margin:0;padding-left:18px;">{items}</ul></div>'

        if issue_type == 'missing_exit':
            issue_info   = (f'&#9888;&#65039; Tienes <strong>entrada registrada</strong> a las '
                            f'<strong>{existing_checkin_vet or "—"}</strong>. '
                            f'Solo indica la hora de salida correcta.')
            ci_section   = ''
            co_req_badge = '<span style="color:#dc3545;">*</span>'
            co_required  = True
            # Smart checkout suggestion — only on first render (not POST re-render)
            sugg_h, sugg_m, sugg_ap, sugg_label = _suggest_checkout(
                request.env, employee.id, target_date,
            )
            co_h_def  = post.get('co_hour', sugg_h)
            co_m_def  = post.get('co_min',  sugg_m)
            co_ap_def = post.get('co_ampm', sugg_ap)
        else:
            issue_info  = '&#128683; No se encontró registro de entrada para este día.'
            ci_section  = f"""
              <div class="section">
                {_time_row('ci',
                           'Hora de entrada <span style="color:#dc3545;">*</span>',
                           required=True,
                           sel_h=post.get('ci_hour',''),
                           sel_m=post.get('ci_min','00'),
                           sel_ap=post.get('ci_ampm','AM'))}
              </div>"""
            co_req_badge = '<span style="color:#888;font-size:11px;font-weight:400;">(opcional)</span>'
            co_required  = False
            sugg_label   = ''
            co_h_def  = post.get('co_hour', '')
            co_m_def  = post.get('co_min',  '00')
            co_ap_def = post.get('co_ampm', 'AM')

        sugg_hint_html = (
            f'<p style="font-size:11px;color:#2471a3;background:#eff6ff;border-radius:4px;'
            f'padding:4px 10px;display:inline-block;margin:6px 0 0;">&#128336; {sugg_label}</p>'
            if sugg_label else ''
        )

        co_section = f"""
              <div class="section">
                <p style="margin:0 0 10px;font-size:12px;font-weight:700;color:#2471a3;
                          text-transform:uppercase;letter-spacing:.5px;">
                  Hora de salida {co_req_badge}
                </p>
                {_time_row('co', 'Hora de salida',
                           hint='Ajusta si la hora sugerida no es correcta' if sugg_label else 'Deje «hr» si no recuerda la hora exacta',
                           required=co_required,
                           sel_h=co_h_def,
                           sel_m=co_m_def,
                           sel_ap=co_ap_def)}
                {sugg_hint_html}
              </div>"""

        prev_motivo = post.get('motivo', '')
        prev_detail = post.get('motivo_detail', '')
        motivo_opts = '<option value="">— Seleccione un motivo —</option>'
        for key, label in _MOTIVOS:
            sel = 'selected' if key == prev_motivo else ''
            motivo_opts += f'<option value="{key}" {sel}>{label}</option>'

        is_otro = prev_motivo == 'otro'
        det_lbl = ('Explique el motivo <span style="color:#dc3545;">*</span>' if is_otro
                   else 'Detalles adicionales '
                        '<span style="color:#888;font-size:12px;font-weight:400;">(opcional)</span>')
        det_req = 'required' if is_otro else ''
        det_ph  = ('Describa detalladamente la razón de su ausencia…' if is_otro
                   else 'Puede agregar información adicional si lo considera necesario…')

        hidden_ci = (f'<input type="hidden" name="existing_checkin" value="{existing_checkin_vet}"/>'
                     if issue_type == 'missing_exit' else '')

        body = f"""
          <div class="hdr">
            <h1>&#128295; Solicitar Corrección de Asistencia</h1>
            <p>Instituto Privado Andrés Bello, CA</p>
          </div>
          <div class="body">
            <div class="info">
              <strong>{employee.name}</strong> &#160;|&#160; {date_disp}
            </div>
            <div class="info" style="margin-top:8px;">{issue_info}</div>
            {err_html}

            <form method="POST" enctype="multipart/form-data" id="fix-form">
              {hidden_ci}
              {ci_section}
              {co_section}

              <label style="{_LBL_STYLE}">
                Motivo de la solicitud de corrección <span style="color:#dc3545;">*</span>
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

              <button class="btn" type="submit" id="submit-btn">&#128228; Enviar Solicitud</button>
            </form>

            <div id="proc-banner">
              <div class="pb-inner">
                <span class="pb-spin">&#9881;&#65039;</span>
                <div class="pb-text">
                  <strong>&#128338; Espere — su solicitud está siendo procesada.</strong>
                  Aguarde un momento antes de reintentarlo.
                </div>
              </div>
            </div>

            <p class="note">
              Su solicitud será revisada por Recursos Humanos antes del cierre de nómina.<br/>
              ¿Consultas?
              <a href="mailto:recursoshumanos@ueipab.edu.ve">recursoshumanos@ueipab.edu.ve</a>
            </p>
          </div>
          <script>
          document.getElementById('fix-form').addEventListener('submit', function() {{
            var btn = document.getElementById('submit-btn');
            btn.disabled = true;
            btn.textContent = '&#9203; Enviando…';
            document.getElementById('proc-banner').style.display = 'block';
          }});
          </script>"""
        return _page('Corrección de Asistencia', body)
