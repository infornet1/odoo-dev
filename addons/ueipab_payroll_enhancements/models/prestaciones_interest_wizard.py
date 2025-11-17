# -*- coding: utf-8 -*-
"""
Prestaciones Sociales Interest Report Wizard

This wizard allows users to generate monthly breakdown reports showing
how prestaciones and interest accumulate over the contract period.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PrestacionesInterestWizard(models.TransientModel):
    """Wizard for generating Prestaciones Sociales Interest reports."""

    _name = 'prestaciones.interest.wizard'
    _description = 'Prestaciones Sociales Interest Report Wizard'

    # ========================================
    # FIELDS
    # ========================================

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Liquidation Payslips',
        required=True,
        domain="[('struct_id.name', 'in', ['Liquidación Venezolana', 'Liquidación Venezolana V2']), ('state', 'in', ['draft', 'done'])]",
        help='Select one or more liquidation payslips to generate interest breakdown reports (V1 or V2)'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.ref('base.USD'),
        help='Currency for report display (USD or VEB)'
    )

    payslip_count = fields.Integer(
        string='Selected Payslips',
        compute='_compute_payslip_count',
        help='Number of payslips selected'
    )

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        """Count selected payslips."""
        for wizard in self:
            wizard.payslip_count = len(wizard.payslip_ids)

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_print_report(self):
        """Generate and print the Prestaciones Interest reports.

        Generates one report per selected payslip.

        Returns:
            dict: Report action

        Raises:
            UserError: If no payslips selected
        """
        self.ensure_one()

        if not self.payslip_ids:
            raise UserError(_('Please select at least one liquidation payslip.'))

        # Prepare report data
        data = {
            'wizard_id': self.id,
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
            'payslip_ids': self.payslip_ids.ids,
        }

        # Generate PDF report
        report = self.env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')

        # Call report_action with docids keyword (same pattern as working Payroll Disbursement wizard)
        return report.report_action(docids=self.payslip_ids.ids, data=data)

    @api.onchange('currency_id')
    def _onchange_currency(self):
        """Validate currency selection."""
        if self.currency_id:
            # Only allow USD or VEB
            valid_currencies = ['USD', 'VEB']
            if self.currency_id.name not in valid_currencies:
                return {
                    'warning': {
                        'title': _('Invalid Currency'),
                        'message': _('Please select either USD or VEB currency.')
                    }
                }
