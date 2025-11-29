# -*- coding: utf-8 -*-
"""
Batch Email Progress Wizard

Provides real-time feedback when sending payslips by email from batch.
Shows progress, success/failure status per employee, and error details.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class BatchEmailWizard(models.TransientModel):
    """Wizard for sending batch emails with progress tracking."""

    _name = 'hr.payslip.batch.email.wizard'
    _description = 'Batch Email Progress Wizard'

    # ========================================
    # FIELDS
    # ========================================

    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        required=True,
        readonly=True
    )

    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        domain="[('model', '=', 'hr.payslip')]"
    )

    state = fields.Selection([
        ('confirm', 'Confirm'),
        ('sending', 'Sending'),
        ('done', 'Complete')
    ], string='State', default='confirm')

    # Progress tracking
    total_count = fields.Integer(string='Total Payslips', readonly=True)
    processed_count = fields.Integer(string='Processed', readonly=True, default=0)
    sent_count = fields.Integer(string='Sent Successfully', readonly=True, default=0)
    failed_count = fields.Integer(string='Failed', readonly=True, default=0)
    no_email_count = fields.Integer(string='No Email', readonly=True, default=0)

    current_employee = fields.Char(string='Current Employee', readonly=True)
    progress_percent = fields.Float(string='Progress %', compute='_compute_progress')

    # Result lines
    result_ids = fields.One2many(
        'hr.payslip.batch.email.result',
        'wizard_id',
        string='Results'
    )

    # Display fields
    show_results = fields.Boolean(compute='_compute_show_results')

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    @api.depends('processed_count', 'total_count')
    def _compute_progress(self):
        for wizard in self:
            if wizard.total_count > 0:
                wizard.progress_percent = (wizard.processed_count / wizard.total_count) * 100
            else:
                wizard.progress_percent = 0

    @api.depends('state')
    def _compute_show_results(self):
        for wizard in self:
            wizard.show_results = wizard.state in ('sending', 'done')

    # ========================================
    # ACTIONS
    # ========================================

    def action_start_sending(self):
        """Start the email sending process."""
        self.ensure_one()

        if not self.email_template_id:
            raise UserError(_("Please select an email template."))

        batch = self.payslip_run_id
        if not batch.slip_ids:
            raise UserError(_("No payslips in this batch."))

        # Initialize results for all payslips
        result_vals = []
        for slip in batch.slip_ids:
            result_vals.append({
                'wizard_id': self.id,
                'payslip_id': slip.id,
                'employee_name': slip.employee_id.name,
                'payslip_number': slip.number or 'N/A',
                'employee_email': slip.employee_id.work_email or '',
                'status': 'pending',
            })

        self.env['hr.payslip.batch.email.result'].create(result_vals)

        # Update wizard state
        self.write({
            'state': 'sending',
            'total_count': len(batch.slip_ids),
            'processed_count': 0,
            'sent_count': 0,
            'failed_count': 0,
            'no_email_count': 0,
        })

        # Start processing (will be called via action_process_next)
        return self.action_process_next()

    def action_process_next(self):
        """Process the next pending email."""
        self.ensure_one()

        # Find next pending result
        pending = self.result_ids.filtered(lambda r: r.status == 'pending')

        if not pending:
            # All done
            self.write({'state': 'done', 'current_employee': ''})
            return self._get_wizard_action()

        # Process next one
        result = pending[0]
        slip = result.payslip_id
        employee = slip.employee_id

        # Update current employee
        self.write({'current_employee': employee.name})
        result.write({'status': 'sending'})

        # Commit to show progress
        self.env.cr.commit()

        try:
            if not employee.work_email:
                result.write({
                    'status': 'no_email',
                    'error_message': _('Employee has no work email configured')
                })
                self.write({
                    'processed_count': self.processed_count + 1,
                    'no_email_count': self.no_email_count + 1,
                })
            else:
                # Send the email
                self.email_template_id.send_mail(
                    slip.id,
                    force_send=True,
                    email_values={'email_to': employee.work_email}
                )
                result.write({'status': 'sent'})
                self.write({
                    'processed_count': self.processed_count + 1,
                    'sent_count': self.sent_count + 1,
                })

        except Exception as e:
            error_msg = str(e)
            _logger.error(f"Failed to send email for {employee.name}: {error_msg}")
            result.write({
                'status': 'error',
                'error_message': error_msg[:255] if len(error_msg) > 255 else error_msg
            })
            self.write({
                'processed_count': self.processed_count + 1,
                'failed_count': self.failed_count + 1,
            })

        # Commit progress
        self.env.cr.commit()

        # Return action to refresh and continue
        return self._get_wizard_action()

    def action_process_all(self):
        """Process all remaining emails at once (background)."""
        self.ensure_one()

        pending = self.result_ids.filtered(lambda r: r.status == 'pending')

        for result in pending:
            slip = result.payslip_id
            employee = slip.employee_id

            self.write({'current_employee': employee.name})
            result.write({'status': 'sending'})

            try:
                if not employee.work_email:
                    result.write({
                        'status': 'no_email',
                        'error_message': _('Employee has no work email configured')
                    })
                    self.write({
                        'processed_count': self.processed_count + 1,
                        'no_email_count': self.no_email_count + 1,
                    })
                else:
                    self.email_template_id.send_mail(
                        slip.id,
                        force_send=True,
                        email_values={'email_to': employee.work_email}
                    )
                    result.write({'status': 'sent'})
                    self.write({
                        'processed_count': self.processed_count + 1,
                        'sent_count': self.sent_count + 1,
                    })

            except Exception as e:
                error_msg = str(e)
                _logger.error(f"Failed to send email for {employee.name}: {error_msg}")
                result.write({
                    'status': 'error',
                    'error_message': error_msg[:255] if len(error_msg) > 255 else error_msg
                })
                self.write({
                    'processed_count': self.processed_count + 1,
                    'failed_count': self.failed_count + 1,
                })

            # Commit after each to save progress
            self.env.cr.commit()

        # Mark as done
        self.write({'state': 'done', 'current_employee': ''})

        return self._get_wizard_action()

    def action_close(self):
        """Close the wizard."""
        return {'type': 'ir.actions.act_window_close'}

    def _get_wizard_action(self):
        """Return action to refresh the wizard view."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.batch.email.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class BatchEmailResult(models.TransientModel):
    """Individual email result tracking."""

    _name = 'hr.payslip.batch.email.result'
    _description = 'Batch Email Result'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        'hr.payslip.batch.email.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(default=10)
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    employee_name = fields.Char(string='Employee')
    payslip_number = fields.Char(string='Payslip #')
    employee_email = fields.Char(string='Email')

    status = fields.Selection([
        ('pending', 'Pending'),
        ('sending', 'Sending...'),
        ('sent', 'Sent'),
        ('no_email', 'No Email'),
        ('error', 'Error')
    ], string='Status', default='pending')

    error_message = fields.Char(string='Error Message')

    status_icon = fields.Char(compute='_compute_status_icon')

    @api.depends('status')
    def _compute_status_icon(self):
        icons = {
            'pending': '⏸',
            'sending': '⏳',
            'sent': '✅',
            'no_email': '📭',
            'error': '❌'
        }
        for result in self:
            result.status_icon = icons.get(result.status, '')
