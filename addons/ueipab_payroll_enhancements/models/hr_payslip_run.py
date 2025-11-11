# -*- coding: utf-8 -*-
"""
UEIPAB Payroll Enhancements - Payslip Batch (Run) Extensions

This module extends hr.payslip.run with computed fields and enhancements
for better financial control and visibility.

Enhancements:
    1. Total Net Amount: Computed field showing sum of all employee net pay
"""

from odoo import models, fields, api


class HrPayslipRun(models.Model):
    """Extend hr.payslip.run with total net amount calculation."""

    _inherit = 'hr.payslip.run'

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
