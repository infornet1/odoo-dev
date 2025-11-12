# -*- coding: utf-8 -*-
"""
Liquidation Forms Wizard (PLACEHOLDER)

This wizard will generate final settlement forms for departing employees
Status: Under Development
"""

from odoo import models, fields, _
from odoo.exceptions import UserError


class LiquidationWizard(models.TransientModel):
    """Wizard for generating Employee Liquidation forms."""

    _name = 'liquidation.wizard'
    _description = 'Liquidation Forms Wizard'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        help='Select employee who is leaving the company'
    )

    departure_date = fields.Date(
        string='Departure Date',
        required=True,
        default=fields.Date.today,
        help='Last working day'
    )

    departure_reason = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('retirement', 'Retirement'),
        ('contract_end', 'Contract End'),
    ], string='Departure Reason', required=True)

    def action_print_report(self):
        """Generate Liquidation Form."""
        raise UserError(_(
            'Liquidation Forms - Under Development\n\n'
            'This report will calculate:\n'
            '• Severance pay (Venezuelan labor law)\n'
            '• Unused vacation days payout\n'
            '• Proportional Aguinaldos\n'
            '• End-of-service benefits\n'
            '• Legal compliance forms\n\n'
            'Coming soon in next update!'
        ))
