import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrAttendanceRevisionWizard(models.TransientModel):
    _name = 'hr.attendance.revision.wizard'
    _description = 'Asistente — Poner Corrección en Revisión'

    correction_id = fields.Many2one(
        'hr.attendance.correction', string='Solicitud',
        required=True, ondelete='cascade',
    )
    note = fields.Text(
        string='Nota para el empleado',
        help='Mensaje opcional que se incluirá en el correo de revisión (ej: observación de CCTV).',
    )
    attachment = fields.Binary(string='Documento adjunto', attachment=False)
    attachment_name = fields.Char(string='Nombre del archivo')

    def action_confirm(self):
        self.ensure_one()
        att_data = None
        att_name = None
        if self.attachment:
            att_data = self.attachment.decode() if isinstance(self.attachment, bytes) else self.attachment
            att_name = self.attachment_name or 'adjunto'

        return self.correction_id.action_set_under_revision(
            note=self.note,
            attachment_data=att_data,
            attachment_name=att_name,
        )
