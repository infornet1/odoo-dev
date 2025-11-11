# -*- coding: utf-8 -*-
"""
UEIPAB Payroll Enhancements - Payslip Extensions

This module extends hr.payslip to maintain state integrity with parent batch.

Enhancement:
    - Prevents setting cancelled payslips to draft when batch is cancelled
    - Maintains parent-child state relationship
    - Follows business policy: batch state controls child payslip states
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    """Extend hr.payslip with batch state control."""

    _inherit = 'hr.payslip'

    # ========================================
    # FIELDS
    # ========================================

    payslip_run_state = fields.Selection(
        related='payslip_run_id.state',
        string='Batch Status',
        readonly=True,
        store=False,
        help='State of the parent payslip batch. '
             'Used to control button visibility and prevent state changes '
             'when batch is cancelled.'
    )

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_payslip_draft(self):
        """Override to prevent setting to draft if batch is cancelled.

        Business Policy:
            - Individual payslips cannot be reopened when batch is cancelled
            - Maintains parent-child state integrity
            - User must reopen batch first, then reopen payslips

        Correct Workflow:
            1. If batch was cancelled by mistake: Reopen batch first
            2. Then individual payslips can be set to draft
            3. This maintains state consistency

        Technical Implementation:
            - Checks if payslip belongs to a batch
            - If batch exists and is cancelled, raises UserError
            - Otherwise, calls parent method normally

        Raises:
            UserError: If payslip belongs to a cancelled batch
        """
        for payslip in self:
            # Check if payslip belongs to a cancelled batch
            if payslip.payslip_run_id and payslip.payslip_run_id.state == 'cancel':
                raise UserError(
                    _('Cannot set payslip to draft.\n\n'
                      'This payslip belongs to the cancelled batch "%s".\n\n'
                      'To reopen this payslip:\n'
                      '1. Open the batch: %s\n'
                      '2. Click "Set to Draft" on the batch\n'
                      '3. Then you can reopen individual payslips') % (
                          payslip.payslip_run_id.name,
                          payslip.payslip_run_id.name
                      )
                )

        # If validation passes, call parent method
        return super(HrPayslip, self).action_payslip_draft()
