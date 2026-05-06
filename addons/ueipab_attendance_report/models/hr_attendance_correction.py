import re
import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

VET_TO_UTC = timedelta(hours=4)  # VET = UTC-4 → UTC = VET + 4h


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
        ('pending',  'Pendiente'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ], default='pending', required=True, string='Estado')
    rejection_reason = fields.Text(string='Motivo de rechazo')
    created_attendance_id = fields.Many2one('hr.attendance', string='Registro creado', readonly=True)
    reviewed_by   = fields.Many2one('res.users', string='Revisado por', readonly=True)
    reviewed_date = fields.Datetime(string='Fecha de revisión', readonly=True)
    submitted_ip      = fields.Char(string='IP de envío', readonly=True)
    attachment_count  = fields.Integer(string='Adjuntos', compute='_compute_attachment_count')

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

    # ─── Actions ──────────────────────────────────────────────────────────────

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Solo se pueden aprobar solicitudes pendientes."))
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
            'state': 'approved',
            'created_attendance_id': att_id,
            'reviewed_by': self.env.user.id,
            'reviewed_date': fields.Datetime.now(),
        })

        tmpl = self.env.ref(
            'ueipab_attendance_report.email_template_correction_approved',
            raise_if_not_found=False,
        )
        if tmpl and self.employee_id.work_email:
            tmpl.send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Corrección aprobada'),
                'message': _('Registro de asistencia creado para %s.') % self.employee_id.name,
                'type': 'success',
            },
        }

    def action_reject(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Solo se pueden rechazar solicitudes pendientes."))
        self.write({
            'state': 'rejected',
            'reviewed_by': self.env.user.id,
            'reviewed_date': fields.Datetime.now(),
        })
        tmpl = self.env.ref(
            'ueipab_attendance_report.email_template_correction_rejected',
            raise_if_not_found=False,
        )
        if tmpl and self.employee_id.work_email:
            tmpl.send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Solicitud rechazada'),
                'message': _('Se notificó al empleado.'),
                'type': 'warning',
            },
        }
