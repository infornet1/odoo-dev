# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrAttendanceApproveWizard(models.TransientModel):
    _name = 'hr.attendance.approve.wizard'
    _description = 'Asistente — Decidir tipo de aprobación'

    correction_id = fields.Many2one(
        'hr.attendance.correction', required=True, ondelete='cascade', readonly=True,
    )
    employee_name = fields.Char(related='correction_id.employee_id.name', readonly=True)
    date          = fields.Date(related='correction_id.date', readonly=True)
    reason        = fields.Text(related='correction_id.reason', readonly=True)

    resolution = fields.Selection([
        ('attendance', 'Corrección de asistencia — el empleado estaba presente'),
        ('leave',      'Registrar como permiso — el empleado estaba ausente'),
    ], string='Tratamiento', required=True, default='attendance')

    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Tipo de permiso',
        domain=[('active', '=', True)],
    )

    def action_confirm(self):
        self.ensure_one()
        if self.resolution == 'leave' and not self.leave_type_id:
            raise UserError(_("Seleccione el tipo de permiso antes de confirmar."))
        if self.resolution == 'attendance':
            return self.correction_id._do_approve_attendance()
        return self.correction_id._do_approve_leave(self.leave_type_id.id)
