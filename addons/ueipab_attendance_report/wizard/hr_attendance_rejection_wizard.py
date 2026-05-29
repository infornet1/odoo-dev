from odoo import fields, models


class HrAttendanceRejectionWizard(models.TransientModel):
    _name = 'hr.attendance.rejection.wizard'
    _description = 'Asistente — Rechazar Corrección de Asistencia'

    correction_id = fields.Many2one(
        'hr.attendance.correction', string='Solicitud',
        required=True, ondelete='cascade',
    )
    rejection_reason = fields.Text(
        string='Motivo de rechazo',
        help='Mensaje opcional para el empleado. Si se omite, el correo no incluirá observación.',
    )

    def action_confirm(self):
        self.ensure_one()
        return self.correction_id.action_reject(reason=self.rejection_reason or '')
