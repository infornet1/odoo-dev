# -*- coding: utf-8 -*-
"""
Relación de Liquidación Wizard

Generates detailed breakdown report showing all formula calculations
for employee liquidation benefits and deductions.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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

    use_custom_rate = fields.Boolean(
        string='Use Custom Exchange Rate',
        default=False,
        help='Override automatic rate with custom rate for VEB currency'
    )

    custom_exchange_rate = fields.Float(
        string='Custom VEB Rate',
        digits=(12, 4),
        help='Custom VEB/USD exchange rate (e.g., 234.8715)\n'
             'Only used when "Use Custom Exchange Rate" is enabled and VEB currency selected'
    )

    rate_date = fields.Date(
        string='Rate Date',
        help='Date for automatic exchange rate lookup (defaults to payslip date_to)\n'
             'Use this to get rate from a different date (e.g., actual payment date)'
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
            'use_custom_rate': self.use_custom_rate,
            'custom_exchange_rate': self.custom_exchange_rate if self.use_custom_rate else None,
            'rate_date': self.rate_date,
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
            'url': f'/liquidacion/breakdown/xlsx/{self.id}',
            'target': 'new',
        }

    @api.onchange('currency_id')
    def _onchange_currency(self):
        """Validate currency selection and reset custom rate."""
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

            # Reset custom rate fields when switching away from VEB
            if self.currency_id.name != 'VEB':
                self.use_custom_rate = False
                self.custom_exchange_rate = 0.0
                self.rate_date = False

    @api.constrains('custom_exchange_rate', 'use_custom_rate')
    def _check_custom_rate(self):
        """Validate custom exchange rate."""
        for wizard in self:
            if wizard.use_custom_rate and wizard.currency_id.name == 'VEB':
                if not wizard.custom_exchange_rate or wizard.custom_exchange_rate <= 0:
                    raise ValidationError(
                        _('Custom exchange rate must be greater than 0')
                    )
                if wizard.custom_exchange_rate > 1000:
                    raise ValidationError(
                        _('Exchange rate seems too high (>1000). Please verify the value.')
                    )
