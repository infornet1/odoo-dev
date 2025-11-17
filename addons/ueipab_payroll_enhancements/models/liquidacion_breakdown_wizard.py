# -*- coding: utf-8 -*-
"""
Relación de Liquidación Wizard

Generates detailed breakdown report showing all formula calculations
for employee liquidation benefits and deductions.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LiquidacionBreakdownWizard(models.TransientModel):
    """Wizard for generating Relación de Liquidación reports."""

    _name = 'liquidacion.breakdown.wizard'
    _description = 'Relación de Liquidación Wizard'

    # ========================================
    # FIELDS
    # ========================================

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Liquidation Payslips',
        required=True,
        domain="[('struct_id.name', 'in', ['Liquidación Venezolana', 'Liquidación Venezolana V2']), ('state', 'in', ['done', 'paid'])]",
        help='Select liquidation payslips to generate breakdown reports (V1 or V2)'
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

    def action_print_pdf(self):
        """Generate and print PDF reports.

        Returns:
            dict: PDF report action
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
        report = self.env.ref('ueipab_payroll_enhancements.action_report_liquidacion_breakdown')
        return report.report_action(docids=self.payslip_ids.ids, data=data)

    def action_export_xlsx(self):
        """Export report to Excel format.

        Returns:
            dict: Excel download action
        """
        self.ensure_one()

        if not self.payslip_ids:
            raise UserError(_('Please select at least one liquidation payslip.'))

        # Generate Excel file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/xlsx/liquidacion_breakdown/{self.id}',
            'target': 'new',
        }

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
