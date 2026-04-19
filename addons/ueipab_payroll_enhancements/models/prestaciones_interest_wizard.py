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

    show_exchange_rate = fields.Boolean(
        compute='_compute_show_exchange_rate',
        string='Show Exchange Rate',
    )

    exchange_rate = fields.Float(
        string='Tasa VEB/USD',
        digits=(12, 4),
        help='Tipo de cambio VEB por 1 USD. Se auto-completa con la tasa más reciente del BCV.'
    )

    exchange_rate_date = fields.Date(
        string='Fecha de Tasa',
        readonly=True,
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
        for wizard in self:
            wizard.payslip_count = len(wizard.payslip_ids)

    @api.depends('currency_id')
    def _compute_show_exchange_rate(self):
        for wizard in self:
            wizard.show_exchange_rate = wizard.currency_id.name == 'VEB' if wizard.currency_id else False

    # ========================================
    # ONCHANGE
    # ========================================

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id and self.currency_id.name == 'VEB':
            rate_rec = self.env['res.currency.rate'].search(
                [('currency_id', '=', self.currency_id.id)],
                limit=1, order='name desc'
            )
            if rate_rec:
                self.exchange_rate = rate_rec.company_rate
                self.exchange_rate_date = rate_rec.name
            else:
                self.exchange_rate = 0.0
                self.exchange_rate_date = False
        else:
            self.exchange_rate = 1.0
            self.exchange_rate_date = False

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def _get_rate_source_label(self):
        """Return display label for the exchange rate source."""
        self.ensure_one()
        if self.currency_id.name != 'VEB':
            return 'USD'
        if self.exchange_rate_date:
            return 'BCV al %s' % self.exchange_rate_date.strftime('%d/%m/%Y')
        rate_rec = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_id.id)],
            limit=1, order='name desc'
        )
        if rate_rec:
            return 'BCV al %s' % rate_rec.name.strftime('%d/%m/%Y')
        return 'Tasa personalizada'

    def action_print_report(self):
        """Generate and print the Prestaciones Interest reports."""
        self.ensure_one()

        if not self.payslip_ids:
            raise UserError(_('Please select at least one liquidation payslip.'))

        is_veb = self.currency_id.name == 'VEB'
        wizard_rate = self.exchange_rate if is_veb and self.exchange_rate > 0 else 1.0

        data = {
            'wizard_id': self.id,
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
            'payslip_ids': self.payslip_ids.ids,
            'exchange_rate': wizard_rate,
            'exchange_rate_date': str(self.exchange_rate_date) if self.exchange_rate_date else None,
            'exchange_rate_label': self._get_rate_source_label(),
        }

        report = self.env.ref('ueipab_payroll_enhancements.action_report_prestaciones_interest')
        return report.report_action(docids=self.payslip_ids.ids, data=data)

    @api.onchange('currency_id')
    def _onchange_currency(self):
        if self.currency_id:
            valid_currencies = ['USD', 'VEB']
            if self.currency_id.name not in valid_currencies:
                return {
                    'warning': {
                        'title': _('Invalid Currency'),
                        'message': _('Please select either USD or VEB currency.')
                    }
                }
