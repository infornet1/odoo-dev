"""Batch-send wizard for Employee Private Info Requests.

HR opens this wizard from the Employees list view, selects which
employees to contact, and clicks 'Enviar solicitudes'.  The wizard
creates hr.employee.info.request records and sends the email template
to each employee's work email address.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EmployeeInfoWizard(models.TransientModel):
    _name = 'hr.employee.info.wizard'
    _description = 'Solicitar actualización de datos personales'

    campaign_key = fields.Char(
        string='Clave de campaña',
        required=True,
        default='private_info_v1',
        help='Identificador único de la campaña.  Cambia este valor para '
             'enviar una nueva ronda sin que los empleados que ya respondieron '
             'la anterior queden bloqueados.',
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados',
        default=lambda self: self._default_employees(),
        help='Empleados a quienes enviar la solicitud.  Por defecto: '
             'todos los empleados activos del tipo "Empleado".',
    )
    skip_completed = fields.Boolean(
        string='Omitir empleados que ya respondieron',
        default=True,
        help='Si está activo, no se enviará una nueva solicitud a los '
             'empleados que ya completaron la solicitud de esta misma campaña.',
    )

    @api.model
    def _default_employees(self):
        return self.env['hr.employee'].search([
            ('active', '=', True),
            ('employee_type', '=', 'employee'),
        ])

    def action_send(self):
        """Create info-request records and send emails."""
        self.ensure_one()

        if not self.employee_ids:
            raise UserError('No hay empleados seleccionados.')

        # Resolve the mail template — find by the XML id we define in data/
        template = self.env.ref(
            'ueipab_hr_employee.email_template_employee_info_request',
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(
                'No se encontró la plantilla de correo '
                '"email_template_employee_info_request".  '
                'Verifique que el módulo esté actualizado correctamente.'
            )

        InfoRequest = self.env['hr.employee.info.request']
        sent_count = 0
        skipped_count = 0
        now = fields.Datetime.now()

        for emp in self.employee_ids:
            if not emp.work_email:
                _logger.warning(
                    'employee_info_wizard: skipping %s — no work_email', emp.name
                )
                skipped_count += 1
                continue

            # Look for an existing request for this employee+campaign
            existing = InfoRequest.search([
                ('employee_id', '=', emp.id),
                ('campaign_key', '=', self.campaign_key),
            ], limit=1)

            if existing and existing.state == 'completed' and self.skip_completed:
                skipped_count += 1
                continue

            if existing:
                # Reuse existing pending request — just re-send the email
                info_req = existing
            else:
                info_req = InfoRequest.create({
                    'employee_id': emp.id,
                    'campaign_key': self.campaign_key,
                })

            # Send the email via the template (to work_email)
            try:
                template.send_mail(
                    info_req.id,
                    email_values={'email_to': emp.work_email},
                    force_send=False,   # let the Odoo mail queue handle delivery
                )
                info_req.write({'sent_date': now, 'state': 'pending'})
                sent_count += 1
            except Exception:
                _logger.exception(
                    'employee_info_wizard: failed to send email for %s (req id=%s)',
                    emp.name, info_req.id,
                )
                skipped_count += 1

        # Friendly summary notification
        msg = f'Se enviaron solicitudes a {sent_count} empleado(s).'
        if skipped_count:
            msg += f'  {skipped_count} empleado(s) omitido(s) '
            msg += '(sin correo o ya completado).' if self.skip_completed \
                else '(sin correo registrado).'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Solicitudes enviadas',
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }
