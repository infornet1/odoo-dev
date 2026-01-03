# -*- coding: utf-8 -*-
"""
Batch Email Progress Wizard

Provides real-time feedback when sending payslips by email from batch.
Shows progress, success/failure status per employee, and error details.

Enhanced: Allow user to select which employees to send emails to before starting.
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
        ('select', 'Select Employees'),
        ('confirm', 'Confirm'),
        ('sending', 'Sending'),
        ('done', 'Complete')
    ], string='State', default='select')

    # Selection lines (for selecting employees)
    selection_ids = fields.One2many(
        'hr.payslip.batch.email.selection',
        'wizard_id',
        string='Employee Selection'
    )

    # Progress tracking
    total_count = fields.Integer(string='Total Payslips', compute='_compute_counts', store=False)
    selected_count = fields.Integer(string='Selected', compute='_compute_counts', store=False)
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
    # DEFAULT VALUES
    # ========================================

    @api.model
    def default_get(self, fields_list):
        """Initialize wizard with selection lines for all employees."""
        res = super().default_get(fields_list)

        # Get batch from context
        batch_id = self.env.context.get('default_payslip_run_id')
        if batch_id:
            batch = self.env['hr.payslip.run'].browse(batch_id)

            # Get default template from batch or fallback
            if batch.email_template_id:
                res['email_template_id'] = batch.email_template_id.id

            # Always populate selection_ids (even if not in fields_list)
            # This ensures the selection lines are created when wizard opens
            selection_vals = []
            for slip in batch.slip_ids.sorted(lambda s: s.employee_id.name):
                has_email = bool(slip.employee_id.work_email)
                selection_vals.append((0, 0, {
                    'payslip_id': slip.id,
                    'payslip_id_int': slip.id,  # Store as integer for reliability
                    'employee_name': slip.employee_id.name,
                    'payslip_number': slip.number or 'N/A',
                    'employee_email': slip.employee_id.work_email or '',
                    'has_email': has_email,
                    'selected': has_email,  # Pre-select only those with email
                }))

            res['selection_ids'] = selection_vals

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure selection lines are populated."""
        records = super().create(vals_list)

        for record in records:
            # If no selection lines were created via default_get, create them now
            if not record.selection_ids and record.payslip_run_id:
                selection_vals = []
                for slip in record.payslip_run_id.slip_ids.sorted(lambda s: s.employee_id.name):
                    has_email = bool(slip.employee_id.work_email)
                    selection_vals.append({
                        'wizard_id': record.id,
                        'payslip_id': slip.id,
                        'payslip_id_int': slip.id,  # Store as integer for reliability
                        'employee_name': slip.employee_id.name,
                        'payslip_number': slip.number or 'N/A',
                        'employee_email': slip.employee_id.work_email or '',
                        'has_email': has_email,
                        'selected': has_email,
                    })
                if selection_vals:
                    self.env['hr.payslip.batch.email.selection'].create(selection_vals)

        return records

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    @api.depends('selection_ids', 'selection_ids.selected')
    def _compute_counts(self):
        for wizard in self:
            wizard.total_count = len(wizard.selection_ids)
            wizard.selected_count = len(wizard.selection_ids.filtered(lambda s: s.selected))

    @api.depends('processed_count', 'selected_count')
    def _compute_progress(self):
        for wizard in self:
            if wizard.selected_count > 0:
                wizard.progress_percent = (wizard.processed_count / wizard.selected_count) * 100
            else:
                wizard.progress_percent = 0

    @api.depends('state')
    def _compute_show_results(self):
        for wizard in self:
            wizard.show_results = wizard.state in ('sending', 'done')

    # ========================================
    # SELECTION ACTIONS
    # ========================================

    def action_select_all(self):
        """Select all employees with valid email."""
        self.ensure_one()
        self.selection_ids.filtered(lambda s: s.has_email).write({'selected': True})
        return self._get_wizard_action()

    def action_deselect_all(self):
        """Deselect all employees."""
        self.ensure_one()
        self.selection_ids.write({'selected': False})
        return self._get_wizard_action()

    def action_select_with_email(self):
        """Select only employees that have email configured."""
        self.ensure_one()
        self.selection_ids.write({'selected': False})
        self.selection_ids.filtered(lambda s: s.has_email).write({'selected': True})
        return self._get_wizard_action()

    def action_proceed_to_confirm(self):
        """Move from select state to confirm state."""
        self.ensure_one()

        if self.selected_count == 0:
            raise UserError(_("Please select at least one employee to send email to."))

        self.write({'state': 'confirm'})
        return self._get_wizard_action()

    def action_back_to_select(self):
        """Go back to selection state."""
        self.ensure_one()
        self.write({'state': 'select'})
        return self._get_wizard_action()

    # ========================================
    # SENDING ACTIONS
    # ========================================

    def action_start_sending(self):
        """Start the email sending process for selected employees only.

        This method now sends all selected emails immediately (no extra click needed).
        """
        self.ensure_one()

        if not self.email_template_id:
            raise UserError(_("Please select an email template."))

        # Get only selected employees
        selected = self.selection_ids.filtered(lambda s: s.selected)

        if not selected:
            raise UserError(_("No employees selected to send emails to."))

        # Initialize results for selected payslips only
        # Use payslip_id_int for reliable storage across form submissions
        result_vals = []

        # Build a lookup map from employee name to payslip for fallback
        payslip_map = {}
        for slip in self.payslip_run_id.slip_ids:
            payslip_map[slip.employee_id.name] = slip

        for sel in selected:
            # Get payslip ID from integer field (more reliable) or Many2one
            slip_id = sel.payslip_id_int or (sel.payslip_id.id if sel.payslip_id else False)

            # Fallback: if slip_id is still missing, look up from batch using employee name
            if not slip_id and sel.employee_name:
                fallback_slip = payslip_map.get(sel.employee_name)
                if fallback_slip:
                    slip_id = fallback_slip.id
                    _logger.info(f"Fallback: Found payslip {slip_id} for {sel.employee_name}")

            result_vals.append({
                'wizard_id': self.id,
                'payslip_id': slip_id,
                'payslip_id_int': slip_id,  # Store as integer for reliability
                'employee_name': sel.employee_name,
                'payslip_number': sel.payslip_number,
                'employee_email': sel.employee_email,
                'status': 'pending',
            })

        self.env['hr.payslip.batch.email.result'].create(result_vals)

        # Update wizard state
        self.write({
            'state': 'sending',
            'processed_count': 0,
            'sent_count': 0,
            'failed_count': 0,
            'no_email_count': 0,
        })

        # Commit to show the sending state
        self.env.cr.commit()

        # Now actually send all emails
        return self.action_process_all()

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
            # Use payslip_id_int for reliable payslip lookup
            slip_id = result.payslip_id_int or (result.payslip_id.id if result.payslip_id else False)
            slip = self.env['hr.payslip'].browse(slip_id) if slip_id else False

            # Use stored employee_email from result (more reliable than relationship)
            email_to = result.employee_email

            self.write({'current_employee': result.employee_name})
            result.write({'status': 'sending'})

            try:
                if not email_to:
                    result.write({
                        'status': 'no_email',
                        'error_message': _('Employee has no work email configured')
                    })
                    self.write({
                        'processed_count': self.processed_count + 1,
                        'no_email_count': self.no_email_count + 1,
                    })
                elif not slip or not slip.exists():
                    result.write({
                        'status': 'error',
                        'error_message': _('Payslip not found (ID: %s)') % slip_id
                    })
                    self.write({
                        'processed_count': self.processed_count + 1,
                        'failed_count': self.failed_count + 1,
                    })
                else:
                    self.email_template_id.send_mail(
                        slip.id,
                        force_send=True,
                        email_values={'email_to': email_to}
                    )
                    result.write({'status': 'sent'})
                    self.write({
                        'processed_count': self.processed_count + 1,
                        'sent_count': self.sent_count + 1,
                    })

            except Exception as e:
                error_msg = str(e)
                _logger.error(f"Failed to send email for {result.employee_name}: {error_msg}")
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


class BatchEmailSelection(models.TransientModel):
    """Employee selection for batch email wizard."""

    _name = 'hr.payslip.batch.email.selection'
    _description = 'Batch Email Employee Selection'
    _order = 'employee_name'

    wizard_id = fields.Many2one(
        'hr.payslip.batch.email.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    payslip_id_int = fields.Integer(string='Payslip ID (stored)')  # Reliable storage
    employee_name = fields.Char(string='Employee')
    payslip_number = fields.Char(string='Payslip #')
    employee_email = fields.Char(string='Email')
    has_email = fields.Boolean(string='Has Email')
    selected = fields.Boolean(string='Send Email', default=True)

    email_status = fields.Char(compute='_compute_email_status', string='Status')

    @api.depends('has_email', 'employee_email')
    def _compute_email_status(self):
        for sel in self:
            if sel.has_email:
                sel.email_status = '✅ ' + sel.employee_email
            else:
                sel.email_status = '❌ No email configured'


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
    payslip_id_int = fields.Integer(string='Payslip ID (stored)')  # Reliable storage
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
