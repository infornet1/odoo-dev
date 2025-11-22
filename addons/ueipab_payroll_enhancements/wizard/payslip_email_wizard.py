# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PayslipEmailWizard(models.TransientModel):
    _name = 'payslip.email.wizard'
    _description = 'Payslip Email Sending Wizard'

    # Payslip Selection
    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Payslips',
        required=True,
        help='Select payslips to send via email'
    )
    payslip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_payslip_count',
        store=False
    )

    # Template Selection
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        domain=[('model', '=', 'hr.payslip')],
        help='Email template to use for sending payslips'
    )
    template_type = fields.Selection([
        ('regular', 'Regular Payslip'),
        ('aguinaldos', 'AGUINALDOS (Christmas Bonus)')
    ], string='Template Type', default='regular', required=True)

    # Progress Tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('done', 'Done')
    ], string='State', default='draft', readonly=True)

    email_sent_count = fields.Integer(
        string='Emails Sent',
        default=0,
        readonly=True,
        help='Number of emails successfully sent'
    )
    email_failed_count = fields.Integer(
        string='Emails Failed',
        default=0,
        readonly=True,
        help='Number of emails that failed to send'
    )

    # Log Messages
    log_message = fields.Text(
        string='Log',
        readonly=True,
        help='Detailed log of email sending process'
    )

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        """Compute the number of selected payslips."""
        for wizard in self:
            wizard.payslip_count = len(wizard.payslip_ids)

    @api.onchange('template_type')
    def _onchange_template_type(self):
        """Auto-select template based on type."""
        if self.template_type == 'regular':
            # Find regular payslip template
            template = self.env['mail.template'].search([
                ('name', '=', 'Payslip Email - Employee Delivery'),
                ('model', '=', 'hr.payslip')
            ], limit=1)
            if template:
                self.template_id = template.id
        elif self.template_type == 'aguinaldos':
            # Find AGUINALDOS template
            template = self.env['mail.template'].search([
                ('name', '=', 'Aguinaldos Email - Christmas Bonus Delivery'),
                ('model', '=', 'hr.payslip')
            ], limit=1)
            if template:
                self.template_id = template.id

    @api.model
    def default_get(self, fields_list):
        """Set default values when wizard is opened."""
        res = super(PayslipEmailWizard, self).default_get(fields_list)

        # Get active payslip IDs from context
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', '')

        if active_model == 'hr.payslip' and active_ids:
            res['payslip_ids'] = [(6, 0, active_ids)]

        # Auto-select regular template by default
        template = self.env['mail.template'].search([
            ('name', '=', 'Payslip Email - Employee Delivery'),
            ('model', '=', 'hr.payslip')
        ], limit=1)
        if template:
            res['template_id'] = template.id

        return res

    def action_send_emails(self):
        """Send emails with PDF attachments to all selected payslips."""
        self.ensure_one()

        if not self.payslip_ids:
            raise UserError(_('Please select at least one payslip to send.'))

        # Update state to sending
        self.write({'state': 'sending'})

        # Initialize counters and log
        sent_count = 0
        failed_count = 0
        log_lines = []

        log_lines.append("=" * 80)
        log_lines.append("PAYSLIP EMAIL SENDING PROCESS")
        log_lines.append("=" * 80)
        log_lines.append(f"Template Type: {dict(self._fields['template_type'].selection).get(self.template_type)}")
        log_lines.append(f"Total Payslips: {len(self.payslip_ids)}")
        log_lines.append("")

        # Get template based on type
        if not self.template_id:
            raise UserError(_('Please select an email template.'))

        # Send emails for each payslip
        for idx, payslip in enumerate(self.payslip_ids, 1):
            try:
                log_lines.append(f"[{idx}/{len(self.payslip_ids)}] Processing: {payslip.number}")
                log_lines.append(f"    Employee: {payslip.employee_id.name}")

                # Get employee email
                employee = payslip.employee_id
                email_to = employee.work_email

                # Try alternative email fields if work_email is not set
                if not email_to and hasattr(employee, 'address_home_id') and employee.address_home_id:
                    email_to = employee.address_home_id.email
                elif not email_to and hasattr(employee, 'private_email'):
                    email_to = employee.private_email

                if not email_to:
                    log_lines.append(f"    ❌ FAILED: No email address found")
                    failed_count += 1
                    continue

                log_lines.append(f"    Email To: {email_to}")

                # Use standard Odoo template.send_mail() which automatically attaches PDF
                self.template_id.send_mail(
                    payslip.id,
                    force_send=True,
                    raise_exception=True
                )

                log_lines.append(f"    ✅ SUCCESS: Email sent with PDF attachment")
                sent_count += 1

            except Exception as e:
                log_lines.append(f"    ❌ FAILED: {str(e)}")
                failed_count += 1
                _logger.error(f"Failed to send email for payslip {payslip.number}: {str(e)}")

            log_lines.append("")

        # Final summary
        log_lines.append("=" * 80)
        log_lines.append("SUMMARY")
        log_lines.append("=" * 80)
        log_lines.append(f"✅ Successfully Sent: {sent_count}")
        log_lines.append(f"❌ Failed: {failed_count}")
        log_lines.append(f"📊 Total Processed: {sent_count + failed_count}")
        log_lines.append("=" * 80)

        # Update wizard with results
        self.write({
            'state': 'done',
            'email_sent_count': sent_count,
            'email_failed_count': failed_count,
            'log_message': '\n'.join(log_lines)
        })

        # Show result message
        if failed_count == 0:
            message = _(f'Successfully sent {sent_count} email(s)!')
            message_type = 'success'
        else:
            message = _(f'Sent {sent_count} email(s), {failed_count} failed. Check log for details.')
            message_type = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Email Sending Complete'),
                'message': message,
                'type': message_type,
                'sticky': False,
            }
        }

    def action_reset(self):
        """Reset wizard to draft state."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'email_sent_count': 0,
            'email_failed_count': 0,
            'log_message': False
        })
        return {'type': 'ir.actions.act_window_close'}
