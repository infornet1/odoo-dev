# -*- coding: utf-8 -*-
"""
UEIPAB Payroll Enhancements - Payslip Batch (Run) Extensions

This module extends hr.payslip.run with computed fields and enhancements
for better financial control and visibility.

Enhancements:
    1. Total Net Amount: Computed field showing sum of all employee net pay
    2. Print Disbursement List: ICF-compliant PDF report for finance approval
    3. Cancel Workflow: Cancel batches instead of deleting (audit trail policy)
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    """Extend hr.payslip.run with total net amount calculation and cancel workflow."""

    _inherit = 'hr.payslip.run'

    # ========================================
    # FIELDS
    # ========================================

    # Extend state selection to add 'cancel'
    state = fields.Selection(
        selection_add=[('cancel', 'Cancelled')],
        ondelete={'cancel': 'set default'},
        help="Status for Payslip Batches. "
             "Cancelled batches preserve audit trail without deletion."
    )

    total_net_amount = fields.Monetary(
        string='Total Net Payable',
        compute='_compute_total_net_amount',
        store=True,
        currency_field='currency_id',
        help='Sum of all employee net payments in this batch. '
             'Only includes confirmed payslips (done/paid state).'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        help='Currency for total net amount display'
    )

    @api.depends('slip_ids', 'slip_ids.state', 'slip_ids.line_ids', 'slip_ids.line_ids.total')
    def _compute_total_net_amount(self):
        """Calculate total net payable for all payslips in batch.

        Business Logic:
            - Only includes payslips in 'done' or 'paid' state
            - Sums the VE_NET salary rule line from each payslip
            - Ignores cancelled or draft payslips
            - Updates automatically when payslips change

        Technical Implementation:
            - Uses @api.depends for automatic recomputation
            - Stored in database for performance (store=True)
            - Filters payslips by state before calculation
        """
        for batch in self:
            # Get all confirmed payslips (not draft or cancelled)
            valid_slips = batch.slip_ids.filtered(
                lambda s: s.state in ('done', 'paid')
            )

            # Sum the NET line from each payslip
            total = 0.0
            for slip in valid_slips:
                # Find the VE_NET salary rule line
                net_line = slip.line_ids.filtered(
                    lambda l: l.salary_rule_id.code == 'VE_NET'
                )
                if net_line:
                    # Should only be one VE_NET line per payslip
                    total += net_line[0].total

            batch.total_net_amount = total

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_cancel(self):
        """Cancel the payslip batch and all associated payslips.

        Business Policy:
            - Never delete records, only cancel them for audit trail
            - Cancelled batches can be reopened with action_draft
            - All associated payslips are also cancelled
            - Only draft or closed batches can be cancelled

        Technical Implementation:
            - Sets batch state to 'cancel'
            - Calls action_payslip_cancel on all associated payslips
            - Prevents cancellation if batch has confirmed journal entries

        Raises:
            UserError: If batch cannot be cancelled
        """
        for batch in self:
            # Validate batch can be cancelled
            if batch.state == 'cancel':
                raise UserError(
                    _('This batch is already cancelled.')
                )

            # Check for confirmed journal entries
            confirmed_moves = batch.slip_ids.mapped('move_id').filtered(
                lambda m: m.state == 'posted'
            )
            if confirmed_moves:
                raise UserError(
                    _('Cannot cancel batch with posted journal entries. '
                      'Please cancel the journal entries first.')
                )

            # Cancel all associated payslips
            payslips_to_cancel = batch.slip_ids.filtered(
                lambda s: s.state not in ('cancel', 'draft')
            )
            if payslips_to_cancel:
                payslips_to_cancel.action_payslip_cancel()

            # Cancel the batch
            batch.state = 'cancel'

        return True

    def action_draft(self):
        """Set cancelled batch back to draft state.

        Business Logic:
            - Allows reopening cancelled batches
            - Does NOT automatically reopen cancelled payslips
            - User must manually reopen payslips if needed

        Technical Implementation:
            - Sets batch state to 'draft'
            - Only works on cancelled batches

        Raises:
            UserError: If batch is not cancelled
        """
        for batch in self:
            if batch.state != 'cancel':
                raise UserError(
                    _('Only cancelled batches can be set to draft. '
                      'Current state: %s') % dict(batch._fields['state'].selection).get(batch.state)
                )

            batch.state = 'draft'

        return True
