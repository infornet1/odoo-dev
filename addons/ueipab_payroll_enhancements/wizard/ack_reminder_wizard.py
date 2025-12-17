# -*- coding: utf-8 -*-
"""
Acknowledgment Reminder Wizard

Wizard to send reminder emails to employees who haven't acknowledged their payslips.
Provides preview of pending employees and tracks reminder count.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AckReminderWizard(models.TransientModel):
    """Wizard to send acknowledgment reminders for pending payslips."""

    _name = 'hr.payslip.ack.reminder.wizard'
    _description = 'Payslip Acknowledgment Reminder Wizard'

    # ========================================
    # FIELDS
    # ========================================

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        required=True,
        readonly=True,
    )

    batch_name = fields.Char(
        related='payslip_run_id.name',
        string='Batch Name',
        readonly=True,
    )

    pending_count = fields.Integer(
        string='Pending Count',
        compute='_compute_pending_info',
    )

    total_count = fields.Integer(
        string='Total Payslips',
        compute='_compute_pending_info',
    )

    acknowledged_count = fields.Integer(
        string='Acknowledged Count',
        compute='_compute_pending_info',
    )

    pending_line_ids = fields.One2many(
        'hr.payslip.ack.reminder.line',
        'wizard_id',
        string='Pending Employees',
    )

    state = fields.Selection([
        ('preview', 'Preview'),
        ('sending', 'Sending'),
        ('done', 'Done'),
    ], default='preview', string='State')

    sent_count = fields.Integer(
        string='Sent Count',
        default=0,
    )

    failed_count = fields.Integer(
        string='Failed Count',
        default=0,
    )

    no_email_count = fields.Integer(
        string='No Email Count',
        default=0,
    )

    # ========================================
    # COMPUTED METHODS
    # ========================================

    @api.depends('payslip_run_id')
    def _compute_pending_info(self):
        for wizard in self:
            if wizard.payslip_run_id:
                all_slips = wizard.payslip_run_id.slip_ids.filtered(
                    lambda s: s.state in ['done', 'paid']
                )
                acknowledged = all_slips.filtered(lambda s: s.is_acknowledged)
                wizard.total_count = len(all_slips)
                wizard.acknowledged_count = len(acknowledged)
                wizard.pending_count = wizard.total_count - wizard.acknowledged_count
            else:
                wizard.total_count = 0
                wizard.acknowledged_count = 0
                wizard.pending_count = 0

    # ========================================
    # DEFAULT METHODS
    # ========================================

    @api.model
    def default_get(self, fields_list):
        """Load pending payslips when wizard opens."""
        res = super().default_get(fields_list)

        # Get batch from context
        batch_id = self.env.context.get('active_id')
        if batch_id:
            batch = self.env['hr.payslip.run'].browse(batch_id)
            res['payslip_run_id'] = batch_id

            # Get pending payslips
            pending = batch.slip_ids.filtered(
                lambda s: not s.is_acknowledged
                and s.state in ['done', 'paid']
            )

            # Create wizard lines
            lines = []
            for slip in pending:
                lines.append((0, 0, {
                    'payslip_id': slip.id,
                    'employee_id': slip.employee_id.id,
                    'payslip_number': slip.number,
                    'work_email': slip.employee_id.work_email or '',
                    'reminder_count': slip.ack_reminder_count,
                    'selected': True,  # Default selected
                }))
            res['pending_line_ids'] = lines

        return res

    # ========================================
    # ACTION METHODS
    # ========================================

    def action_send_reminders(self):
        """Send reminder emails to selected employees."""
        self.ensure_one()

        # Get selected lines with valid email
        selected = self.pending_line_ids.filtered(lambda l: l.selected)
        if not selected:
            raise UserError(_('No employees selected for reminder.'))

        # Get email template
        template = self.env.ref(
            'ueipab_payroll_enhancements.email_template_payslip_ack_reminder',
            raise_if_not_found=False
        )
        if not template:
            raise UserError(_('Reminder email template not found. Please contact administrator.'))

        sent_count = 0
        failed_count = 0
        no_email_count = 0

        for line in selected:
            payslip = line.payslip_id

            # Check for email
            if not line.work_email:
                no_email_count += 1
                line.status = 'no_email'
                continue

            try:
                # Send email
                template.send_mail(payslip.id, force_send=True)

                # Update tracking
                payslip.write({
                    'ack_reminder_count': payslip.ack_reminder_count + 1,
                    'ack_reminder_last_date': fields.Datetime.now(),
                })

                sent_count += 1
                line.status = 'sent'
                line.reminder_count = payslip.ack_reminder_count

            except Exception as e:
                _logger.error(f"Failed to send reminder to {payslip.employee_id.name}: {e}")
                failed_count += 1
                line.status = 'failed'
                line.error_message = str(e)[:200]

        # Update wizard state
        self.write({
            'state': 'done',
            'sent_count': sent_count,
            'failed_count': failed_count,
            'no_email_count': no_email_count,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        """Select all pending employees."""
        self.pending_line_ids.write({'selected': True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_deselect_all(self):
        """Deselect all pending employees."""
        self.pending_line_ids.write({'selected': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class AckReminderWizardLine(models.TransientModel):
    """Line item for each pending payslip in the reminder wizard."""

    _name = 'hr.payslip.ack.reminder.line'
    _description = 'Payslip Acknowledgment Reminder Line'

    wizard_id = fields.Many2one(
        'hr.payslip.ack.reminder.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        required=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )

    payslip_number = fields.Char(
        string='Slip #',
    )

    work_email = fields.Char(
        string='Email',
    )

    reminder_count = fields.Integer(
        string='Reminders Sent',
    )

    selected = fields.Boolean(
        string='Send',
        default=True,
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('no_email', 'No Email'),
    ], default='pending', string='Status')

    error_message = fields.Char(
        string='Error',
    )
