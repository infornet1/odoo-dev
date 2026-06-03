import logging
import re
import uuid
from datetime import datetime, time, timedelta

import requests as _requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

VET_TO_UTC = timedelta(hours=4)  # VET = UTC-4 → UTC = VET + 4h

_logger = logging.getLogger(__name__)

_FS_MAILBOX_ID = 4
_FS_SENDER_USER = 1
_HR_EMAIL = 'recursoshumanos@ueipab.edu.ve'
_DIRECTOR_EMAIL = 'arcides.arzola@ueipab.edu.ve'

# Motivos that map directly to an hr.leave.type (leave type IDs match both envs)
_MOTIVO_LEAVE_MAP = {
    'capacitacion': 1,   # Paid Time Off
    'medico':       15,  # Cita Médica personal
    'reposo':       2,   # Sick Time Off
    'duelo':        13,  # Muerte familiar (luto)
    'judicial':     18,  # Diligencia personal
    'matrimonio':   1,   # Paid Time Off
    'calamidad':    18,  # Diligencia personal
}
# 'energia'    → always attendance (employee was present, clock issue)
# 'otro'       → opens approve wizard for RRHH to decide
# anything else → attendance (safe default)


class HrAttendanceCorrection(models.Model):
    _name = 'hr.attendance.correction'
    _description = 'Solicitud de Corrección de Asistencia'
    _order = 'create_date desc'

    token = fields.Char(default=lambda self: uuid.uuid4().hex, readonly=True, copy=False)
    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True,
        ondelete='cascade', index=True,
    )
    attendance_report_id = fields.Many2one(
        'hr.attendance.report', string='Reporte', ondelete='set null',
    )
    date = fields.Date(string='Fecha a corregir', required=True)
    check_in_time = fields.Char(string='Hora entrada (HH:MM)', required=True)
    check_out_time = fields.Char(string='Hora salida (HH:MM)')
    reason = fields.Text(string='Motivo del empleado', required=True)
    state = fields.Selection([
        ('pending',        'Pendiente'),
        ('under_revision', 'En Revisión'),
        ('approved',       'Aprobado'),
        ('rejected',       'Rechazado'),
    ], default='pending', required=True, string='Estado')
    rejection_reason = fields.Text(string='Motivo de rechazo')
    revision_note = fields.Text(string='Nota de revisión')
    freescout_conversation_id = fields.Integer(
        string='Conv. Freescout', readonly=True, copy=False,
    )
    created_attendance_id = fields.Many2one('hr.attendance', string='Registro creado', readonly=True)
    reviewed_by   = fields.Many2one('res.users', string='Revisado por', readonly=True)
    reviewed_date = fields.Datetime(string='Fecha de revisión', readonly=True)
    submitted_ip      = fields.Char(string='IP de envío', readonly=True)
    attachment_ids    = fields.Many2many('ir.attachment', string='Documentos adjuntos')
    attachment_count  = fields.Integer(string='Adjuntos', compute='_compute_attachment_count')
    motivo_key = fields.Char(
        string='Categoría de motivo', readonly=True, index=True,
        help='Clave interna del motivo seleccionado por el empleado en el formulario.',
    )
    correction_type = fields.Selection([
        ('attendance', 'Corrección de asistencia'),
        ('leave',      'Permiso'),
    ], string='Tipo de resolución', readonly=True,
       help='Determinado automáticamente al aprobar según el motivo.')
    created_leave_id = fields.Many2one(
        'hr.leave', string='Permiso creado', readonly=True, ondelete='set null',
    )

    def _compute_attachment_count(self):
        Att = self.env['ir.attachment']
        for rec in self:
            rec.attachment_count = Att.search_count([
                ('res_model', '=', self._name), ('res_id', '=', rec.id),
            ])

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documentos adjuntos'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def name_get(self):
        result = []
        for r in self:
            name = f"{r.employee_id.name} | {r.date}"
            result.append((r.id, name))
        return result

    def _build_cc(self, include_hr=True):
        """Return CC string for correction emails.

        Includes HR always and the director unless they are the employee
        (to avoid sending them a duplicate of the TO line).
        """
        self.ensure_one()
        parts = [_HR_EMAIL] if include_hr else []
        if self.employee_id.work_email != _DIRECTOR_EMAIL:
            parts.append(_DIRECTOR_EMAIL)
        return ', '.join(parts) if parts else ''

    def _get_fix_url(self):
        """Public URL for the correction form (uses the same ack_token as the report)."""
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        token = self.attendance_report_id.ack_token if self.attendance_report_id else ''
        return f"{base}/attendance-fix/{token}"

    def _parse_time_utc(self, time_str):
        """Parse 'HH:MM' (VET local) on self.date → UTC datetime."""
        h, m = int(time_str[:2]), int(time_str[3:5])
        local_dt = datetime(self.date.year, self.date.month, self.date.day, h, m)
        return local_dt + VET_TO_UTC

    # ─── Freescout API helpers ─────────────────────────────────────────────────

    def _fs_config(self):
        """Return (api_url, api_key) from ir.config_parameter."""
        params = self.env['ir.config_parameter'].sudo()
        url = params.get_param('ai_agent.freescout_api_url', '').rstrip('/')
        key = params.get_param('ai_agent.freescout_api_key', '')
        if not url or not key:
            raise UserError(_(
                "Freescout API no configurada. "
                "Verifique ai_agent.freescout_api_url y ai_agent.freescout_api_key."
            ))
        return url, key

    def _fs_post(self, endpoint, payload):
        """POST to Freescout REST API. Returns parsed JSON response."""
        url, key = self._fs_config()
        resp = _requests.post(
            f"{url}{endpoint}",
            json=payload,
            headers={'X-FreeScout-API-Key': key, 'Content-Type': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def _fs_create_conversation(self, subject, html_body):
        """Create a new FS conversation with the employee as customer. Returns conv id."""
        self.ensure_one()
        emp_email = self.employee_id.work_email
        if not emp_email:
            raise UserError(_("El empleado no tiene correo de trabajo configurado."))
        thread_cc = [_DIRECTOR_EMAIL] if emp_email != _DIRECTOR_EMAIL else []
        data = self._fs_post('/conversations', {
            'type': 'email',
            'mailboxId': _FS_MAILBOX_ID,
            'subject': subject,
            'customer': {'email': emp_email},
            'threads': [{'type': 'message', 'text': html_body, 'user': _FS_SENDER_USER,
                         'cc': thread_cc}],
            'status': 'active',
        })
        return data.get('id') or data.get('_embedded', {}).get('conversations', [{}])[0].get('id')

    def _fs_add_thread(self, html_body):
        """Add a message thread to the linked FS conversation."""
        self.ensure_one()
        if not self.freescout_conversation_id:
            raise UserError(_("Esta solicitud no tiene una conversación Freescout vinculada."))
        self._fs_post(
            f'/conversations/{self.freescout_conversation_id}/threads',
            {'type': 'message', 'text': html_body, 'user': _FS_SENDER_USER},
        )

    def _fs_under_revision_html(self, note):
        """HTML body for the 'under revision' FS message sent to the employee."""
        self.ensure_one()
        first_name = self.employee_id.name.split()[0].capitalize()
        date_str = self.date.strftime('%d/%m/%Y') if self.date else ''
        note_block = ''
        if note:
            note_block = f"""
  <div style="background:#fff3cd;border-left:4px solid #f0ad4e;padding:14px 18px;
              border-radius:4px;margin:16px 0;font-size:14px;color:#856404;">
    <strong>Observación de Recursos Humanos:</strong><br/>
    {note}
  </div>"""
        return f"""
<div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;padding:20px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">
  <div style="background:linear-gradient(135deg,#f5a623,#f0c040);padding:22px 28px;">
    <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"
         width="56" height="56"
         style="width:56px;height:56px;border-radius:50%;display:block;margin:0 auto 12px;
                border:2px solid rgba(255,255,255,0.5);object-fit:cover;"/>
    <h2 style="margin:0;font-size:18px;text-align:center;color:#5a3e00;">&#128269; Solicitud en revisión</h2>
    <p style="margin:4px 0 0;font-size:13px;text-align:center;color:#5a3e00;opacity:.8;">
      Control de Asistencia — UEIPAB</p>
  </div>
  <div style="padding:24px 28px;">
    <p style="font-size:15px;color:#333;margin:0 0 12px;">
      Estimado/a <strong>{self.employee_id.name}</strong>,
    </p>
    <p style="font-size:14px;color:#555;line-height:1.6;margin:0 0 4px;">
      Hemos recibido tu solicitud de corrección de asistencia para el día
      <strong>{date_str}</strong> y actualmente está siendo <strong>revisada</strong>
      por el equipo de Recursos Humanos.
    </p>
    {note_block}
    <p style="font-size:14px;color:#555;line-height:1.6;margin:0 0 16px;">
      Puedes responder directamente a este correo si deseas aportar información adicional.
      Te notificaremos el resultado a la brevedad.
    </p>
    <p style="font-size:13px;color:#555;margin:0;">Cordialmente,<br/>
      <strong>Recursos Humanos</strong><br/>
      Instituto Privado Andrés Bello, CA</p>
  </div>
  <div style="background:#f8f9fa;padding:12px 24px;text-align:center;
              font-size:11px;color:#aaaaaa;border-top:1px solid #eeeeee;">
    Control de Asistencia — UEIPAB
  </div>
</div>
</div>"""

    def _fs_reinvite_html(self):
        """HTML body for the 're-invite' FS message with the form link."""
        self.ensure_one()
        date_str = self.date.strftime('%d/%m/%Y') if self.date else ''
        fix_url = self._get_fix_url()
        btn = ''
        if fix_url:
            btn = f"""
    <div style="text-align:center;margin:20px 0;">
      <a href="{fix_url}"
         style="display:inline-block;background:#2471a3;color:#ffffff;
                padding:13px 32px;font-size:14px;font-weight:700;
                text-decoration:none;border-radius:8px;
                box-shadow:0 4px 12px rgba(0,0,0,0.15);">
        &#128295; Re-enviar solicitud de corrección
      </a>
    </div>
    <p style="text-align:center;font-size:11px;color:#aaa;margin:0 0 16px;">
      El formulario ya tiene tus datos — actualiza los horarios acordados y envía.
    </p>"""
        return f"""
<div style="font-family:Arial,sans-serif;max-width:580px;margin:0 auto;padding:20px;background:#f0f4fa;">
<div style="background:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.1);overflow:hidden;">
  <div style="background:linear-gradient(135deg,#1a2c5b,#2471a3);color:white;padding:22px 28px;">
    <img src="https://odoo.ueipab.edu.ve/web/image/res.company/1/logo" alt="UEIPAB"
         width="56" height="56"
         style="width:56px;height:56px;border-radius:50%;display:block;margin:0 auto 12px;
                border:2px solid rgba(255,255,255,0.3);object-fit:cover;"/>
    <h2 style="margin:0;font-size:18px;text-align:center;">&#128295; Nueva solicitud requerida</h2>
    <p style="margin:4px 0 0;font-size:13px;text-align:center;opacity:.85;">
      Control de Asistencia — UEIPAB</p>
  </div>
  <div style="padding:24px 28px;">
    <p style="font-size:15px;color:#333;margin:0 0 12px;">
      Estimado/a <strong>{self.employee_id.name}</strong>,
    </p>
    <p style="font-size:14px;color:#555;line-height:1.6;margin:0 0 16px;">
      Hemos concluido la revisión de tu solicitud de corrección para el día
      <strong>{date_str}</strong>. Por favor, re-envía el formulario con los
      horarios acordados para que podamos procesarla oficialmente.
    </p>
    {btn}
    <p style="font-size:13px;color:#555;line-height:1.6;margin:0 0 20px;">
      Si tienes alguna pregunta escríbenos a:<br/>
      <a href="mailto:recursoshumanos@ueipab.edu.ve" style="color:#2471a3;font-weight:600;">
        recursoshumanos@ueipab.edu.ve</a>
    </p>
    <p style="font-size:13px;color:#555;margin:0;">Cordialmente,<br/>
      <strong>Recursos Humanos</strong><br/>
      Instituto Privado Andrés Bello, CA</p>
  </div>
  <div style="background:#f8f9fa;padding:12px 24px;text-align:center;
              font-size:11px;color:#aaaaaa;border-top:1px solid #eeeeee;">
    Control de Asistencia — UEIPAB
  </div>
</div>
</div>"""

    # ─── Actions ──────────────────────────────────────────────────────────────

    def action_open_revision_wizard(self):
        """Open the 'Poner en Revisión' wizard."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Solo se pueden poner en revisión solicitudes pendientes."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Poner en Revisión'),
            'res_model': 'hr.attendance.revision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_correction_id': self.id},
        }

    def action_set_under_revision(self, note=None, attachment_data=None, attachment_name=None):
        """Called by the wizard. Creates FS conversation and sets state."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Solo se pueden poner en revisión solicitudes pendientes."))

        note = (note or '').strip()

        # Save attachment to Odoo record if provided
        if attachment_data and attachment_name:
            att = self.env['ir.attachment'].create({
                'name': attachment_name,
                'datas': attachment_data,
                'res_model': self._name,
                'res_id': self.id,
            })
            self.write({'attachment_ids': [(4, att.id)]})

        # Build FS conversation
        subject = (
            f"\U0001f50d Revisión de corrección — "
            f"{self.employee_id.name} — {self.date}"
        )
        html = self._fs_under_revision_html(note)
        conv_id = self._fs_create_conversation(subject, html)

        self.write({
            'state': 'under_revision',
            'revision_note': note or False,
            'freescout_conversation_id': conv_id or 0,
        })

        return self._notify_and_reload(
            _('Solicitud en revisión'),
            _('Conversación Freescout creada y empleado notificado.'),
            'warning',
        )

    def action_reinvite(self):
        """Add a re-invite thread to the existing FS conversation and reset to pending."""
        self.ensure_one()
        if self.state != 'under_revision':
            raise UserError(_("Solo se puede re-invitar desde el estado 'En Revisión'."))
        if not self.attendance_report_id or not self.attendance_report_id.ack_token:
            raise UserError(_(
                "No hay token de formulario vinculado. "
                "Esta solicitud no tiene un reporte de asistencia asociado."
            ))

        html = self._fs_reinvite_html()
        self._fs_add_thread(html)

        self.write({'state': 'pending'})

        return self._notify_and_reload(
            _('Re-invitación enviada'),
            _('El empleado recibió el enlace del formulario vía Freescout.'),
            'info',
        )

    def action_approve(self):
        """Smart dispatcher: route to hr.attendance or hr.leave based on motivo_key."""
        self.ensure_one()
        if self.state not in ('pending', 'under_revision'):
            raise UserError(_("Solo se pueden aprobar solicitudes pendientes o en revisión."))

        motivo = (self.motivo_key or '').strip()

        if motivo in _MOTIVO_LEAVE_MAP:
            return self._do_approve_leave(_MOTIVO_LEAVE_MAP[motivo])
        elif motivo == 'otro':
            return {
                'type': 'ir.actions.act_window',
                'name': _('Aprobar corrección — motivo: Otro'),
                'res_model': 'hr.attendance.approve.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_correction_id': self.id},
            }
        else:
            # 'energia', unknown keys, or empty → attendance correction
            return self._do_approve_attendance()

    def _do_approve_attendance(self):
        """Create hr.attendance record — employee was present, clock issue."""
        self.ensure_one()
        if not re.match(r'^\d{2}:\d{2}$', self.check_in_time.strip()):
            raise UserError(_("Formato de hora inválido. Use HH:MM (ej: 07:30)."))

        ci_utc = self._parse_time_utc(self.check_in_time.strip())
        co_utc = None
        worked = 0.0
        if self.check_out_time and re.match(r'^\d{2}:\d{2}$', self.check_out_time.strip()):
            co_utc = self._parse_time_utc(self.check_out_time.strip())
            worked = max(0.0, (co_utc - ci_utc).total_seconds() / 3600)

        # Direct SQL — bypasses hr.attendance overlap constraint
        self.env.cr.execute("""
            INSERT INTO hr_attendance (employee_id, check_in, check_out, worked_hours)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (self.employee_id.id, ci_utc, co_utc, worked))
        att_id = self.env.cr.fetchone()[0]

        self.write({
            'state':               'approved',
            'correction_type':     'attendance',
            'created_attendance_id': att_id,
            'reviewed_by':         self.env.user.id,
            'reviewed_date':       fields.Datetime.now(),
        })

        tmpl = self.env.ref(
            'ueipab_attendance_report.email_template_correction_approved',
            raise_if_not_found=False,
        )
        if tmpl and self.employee_id.work_email:
            tmpl.send_mail(self.id, force_send=True,
                           email_values={'email_cc': self._build_cc()})

        return self._notify_and_reload(
            _('Corrección aprobada'),
            _('Registro de asistencia creado para %s.') % self.employee_id.name,
            'success',
        )

    def _do_approve_leave(self, leave_type_id):
        """Create hr.leave in confirm state — employee was genuinely absent."""
        self.ensure_one()
        leave_date = self.date

        # Full work day: VET 07:00–17:00 → UTC 11:00–21:00
        date_from_utc = datetime.combine(leave_date, time(7, 0)) + VET_TO_UTC
        date_to_utc   = datetime.combine(leave_date, time(17, 0)) + VET_TO_UTC

        leave = self.env['hr.leave'].sudo().create({
            'holiday_status_id': leave_type_id,
            'employee_id':       self.employee_id.id,
            'request_date_from': leave_date,
            'request_date_to':   leave_date,
            'date_from':         date_from_utc,
            'date_to':           date_to_utc,
            'name':              self.reason or '',
        })
        try:
            leave.sudo().action_confirm()
        except Exception as e:
            _logger.warning("Could not confirm leave %s: %s", leave.id, e)

        self.write({
            'state':           'approved',
            'correction_type': 'leave',
            'created_leave_id': leave.id,
            'reviewed_by':     self.env.user.id,
            'reviewed_date':   fields.Datetime.now(),
        })

        tmpl = self.env.ref(
            'ueipab_attendance_report.email_template_correction_approved',
            raise_if_not_found=False,
        )
        if tmpl and self.employee_id.work_email:
            tmpl.send_mail(self.id, force_send=True,
                           email_values={'email_cc': self._build_cc()})

        return self._notify_and_reload(
            _('Corrección aprobada — Permiso creado'),
            _('Permiso creado para %s y enviado a aprobación.') % self.employee_id.name,
            'success',
        )

    def action_open_leave(self):
        """Navigate to the hr.leave record created from this correction."""
        self.ensure_one()
        if not self.created_leave_id:
            raise UserError(_("No hay permiso vinculado a esta solicitud."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Permiso'),
            'res_model': 'hr.leave',
            'res_id': self.created_leave_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_rejection_wizard(self):
        self.ensure_one()
        if self.state not in ('pending', 'under_revision'):
            raise UserError(_("Solo se pueden rechazar solicitudes pendientes o en revisión."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rechazar solicitud'),
            'res_model': 'hr.attendance.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_correction_id': self.id},
        }

    def action_reject(self, reason=None):
        self.ensure_one()
        if self.state not in ('pending', 'under_revision'):
            raise UserError(_("Solo se pueden rechazar solicitudes pendientes o en revisión."))
        vals = {
            'state': 'rejected',
            'reviewed_by': self.env.user.id,
            'reviewed_date': fields.Datetime.now(),
        }
        if reason:
            vals['rejection_reason'] = reason.strip()
        self.write(vals)
        tmpl = self.env.ref(
            'ueipab_attendance_report.email_template_correction_rejected',
            raise_if_not_found=False,
        )
        if tmpl and self.employee_id.work_email:
            tmpl.send_mail(self.id, force_send=True,
                           email_values={'email_cc': self._build_cc()})

        return self._notify_and_reload(
            _('Solicitud rechazada'),
            _('Se notificó al empleado.'),
            'warning',
        )

    def action_open_freescout(self):
        self.ensure_one()
        if not self.freescout_conversation_id:
            raise UserError(_("No hay conversación Freescout vinculada."))
        base = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.freescout_api_url', 'https://freescout.ueipab.edu.ve/api'
        )
        fs_base = base.replace('/api', '').rstrip('/')
        return {
            'type': 'ir.actions.act_url',
            'url': f"{fs_base}/conversation/{self.freescout_conversation_id}",
            'target': 'new',
        }

    def action_resend_report(self):
        self.ensure_one()
        if not self.attendance_report_id:
            raise UserError(_("No hay reporte de asistencia vinculado a esta solicitud."))
        return self.attendance_report_id.action_send_email()

    def _notify_and_reload(self, title, message, msg_type):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': msg_type,
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.attendance.correction',
                    'res_id': self.id,
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'current',
                },
            },
        }
