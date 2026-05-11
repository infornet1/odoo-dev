import json
import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployeeInfoRequest(models.Model):
    """Tokenized private-information update request sent to an employee.

    HR creates a request (manually or via the wizard) and sends an email.
    The employee follows the personal link, reviews pre-filled fields,
    submits corrections, and the record is marked completed.  A diff email
    is sent to recursoshumanos@ueipab.edu.ve on every submission.
    """

    _name = 'hr.employee.info.request'
    _description = 'Employee Private Info Request'
    _order = 'sent_date desc, id desc'
    # Keep chatter / log notes so HR can annotate requests
    _inherit = ['mail.thread']

    # ── Core fields ──────────────────────────────────────────────────────────

    employee_id = fields.Many2one(
        'hr.employee',
        string='Empleado',
        required=True,
        ondelete='cascade',
        index=True,
    )
    # Convenience related field for list display without a join in views
    employee_name = fields.Char(
        related='employee_id.name',
        string='Nombre del empleado',
        store=True,
        readonly=True,
    )
    campaign_key = fields.Char(
        string='Campaña',
        required=True,
        default='private_info_v1',
        help='Identifier for this campaign (e.g. private_info_v1).  '
             'Used to prevent sending duplicate requests in the same campaign.',
    )
    token = fields.Char(
        string='Token',
        readonly=True,
        copy=False,
        index=True,
        help='UUID used in the public URL.  Auto-generated on create.',
    )
    state = fields.Selection(
        [('pending', 'Pendiente'), ('completed', 'Completado')],
        string='Estado',
        default='pending',
        required=True,
        tracking=True,
    )
    sent_date = fields.Datetime(string='Fecha de envío', readonly=True)
    completed_date = fields.Datetime(string='Fecha de completado', readonly=True)
    completed_ip = fields.Char(string='IP de origen', readonly=True)
    submitted_values = fields.Text(
        string='Valores enviados (JSON)',
        readonly=True,
        help='JSON snapshot of old vs new values at the time of submission.',
    )

    # ── Reminder tracking ────────────────────────────────────────────────────

    reminder_count = fields.Integer(
        string='Recordatorios enviados',
        default=0,
        readonly=True,
        help='Number of reminder emails sent after the initial request.',
    )
    reminder_last_date = fields.Datetime(
        string='Último recordatorio',
        readonly=True,
    )
    days_pending = fields.Integer(
        string='Días pendiente',
        compute='_compute_days_pending',
        help='Days since initial email was sent without a response.',
    )

    # ── Computed ─────────────────────────────────────────────────────────────

    @api.depends('sent_date', 'state')
    def _compute_days_pending(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.state == 'completed' or not rec.sent_date:
                rec.days_pending = 0
            else:
                delta = now - rec.sent_date
                rec.days_pending = delta.days

    # ── ORM overrides ────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('token'):
                vals['token'] = str(uuid.uuid4())
        return super().create(vals_list)

    # ── URL helper ───────────────────────────────────────────────────────────

    def _get_form_url(self):
        """Return the public URL for this info-request form."""
        self.ensure_one()
        base = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('web.base.url', 'https://odoo.ueipab.edu.ve')
        ).rstrip('/')
        return f"{base}/employee-info/{self.token}"

    # ── Human-readable diff helper (used by controller) ──────────────────────

    def action_mark_sent(self):
        """Stamp sent_date on all records in the recordset."""
        self.write({'sent_date': fields.Datetime.now()})

    def action_send_reminder(self):
        """Re-send the request email as a reminder and increment counter."""
        tmpl = self.env.ref(
            'ueipab_hr_employee.email_template_employee_info_request',
            raise_if_not_found=False,
        )
        if not tmpl:
            _logger.warning('employee_info_request: reminder template not found')
            return
        now = fields.Datetime.now()
        for rec in self:
            if rec.state == 'completed':
                continue
            tmpl.send_mail(rec.id, force_send=True)
            rec.write({
                'reminder_count': rec.reminder_count + 1,
                'reminder_last_date': now,
            })
            _logger.info(
                'employee_info_request: reminder #%d sent for request %d (%s)',
                rec.reminder_count, rec.id, rec.employee_id.name,
            )

    @api.model
    def _cron_send_reminders(self):
        """Daily cron: re-send to pending requests with no response after N days.

        Schedule:
          - First reminder  → 3 days after sent_date  (reminder_count == 0)
          - Second reminder → 7 days after sent_date  (reminder_count == 1)
          - No further reminders after that (max 2 reminders).
        """
        now = fields.Datetime.now()
        pending = self.search([('state', '=', 'pending'), ('sent_date', '!=', False)])

        for rec in pending:
            days = (now - rec.sent_date).days
            last_reminder_days = (
                (now - rec.reminder_last_date).days if rec.reminder_last_date else days
            )

            # First reminder: 3+ days since initial send, no reminders yet
            if rec.reminder_count == 0 and days >= 3:
                rec.action_send_reminder()

            # Second reminder: 7+ days since initial send, at least 3 days since first reminder
            elif rec.reminder_count == 1 and days >= 7 and last_reminder_days >= 3:
                rec.action_send_reminder()

            # Max 2 reminders — stop after that

    @staticmethod
    def _field_label(fname):
        """Map technical field names to Spanish display labels."""
        return {
            'private_email': 'Correo personal',
            'private_phone': 'Teléfono personal',
            'marital': 'Estado civil',
            'emergency_contact': 'Contacto de emergencia',
            'emergency_phone': 'Teléfono de emergencia',
            'identification_id': 'Cédula de identidad',
            'gender': 'Género',
            'birthday': 'Fecha de nacimiento',
            'place_of_birth': 'Lugar de nacimiento',
            'country_of_birth': 'País de nacimiento',
            'private_city': 'Ciudad',
            'private_state_id': 'Estado/Provincia',
            'private_zip': 'Código postal',
            'private_country_id': 'País de residencia',
        }.get(fname, fname)
