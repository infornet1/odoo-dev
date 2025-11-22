# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PayslipCompactWizard(models.TransientModel):
    _name = 'payslip.compact.wizard'
    _description = 'Payslip Compact Report Wizard'

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Payslips',
        required=True,
        domain="[('state', '!=', 'cancel')]",
        help='Select payslips to generate compact report for. A separate report will be generated for each selected payslip.'
    )

    payslip_count = fields.Integer(
        string='Payslips Count',
        compute='_compute_payslip_count',
        help='Number of payslips selected'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        domain=[('name', 'in', ['USD', 'VEB'])],
        help='Select currency for report display (USD or VEB)'
    )

    # Exchange Rate Override Options
    use_custom_rate = fields.Boolean(
        string='Use Custom Exchange Rate',
        default=False,
        help='Override automatic exchange rate lookup with a custom rate'
    )

    custom_exchange_rate = fields.Float(
        string='Custom Rate (VEB/USD)',
        digits=(12, 4),
        help='Custom exchange rate to use (e.g., 236.4601). Only used if "Use Custom Exchange Rate" is checked.'
    )

    rate_date = fields.Date(
        string='Rate Date (Auto Lookup)',
        help='Automatically lookup exchange rate for this date. Leave empty to use payslip date.'
    )

    exchange_rate_display = fields.Char(
        string='Exchange Rate Info',
        compute='_compute_exchange_rate_display',
        readonly=True,
        help='Displays the exchange rate that will be used for conversion'
    )

    @api.depends_context('active_ids')
    def _compute_payslip_count(self):
        """Compute number of payslips selected"""
        for wizard in self:
            wizard.payslip_count = len(wizard.payslip_ids)

    @api.depends('currency_id', 'use_custom_rate', 'custom_exchange_rate', 'rate_date', 'payslip_ids')
    def _compute_exchange_rate_display(self):
        """Display the exchange rate that will be used"""
        for wizard in self:
            if wizard.currency_id.name != 'VEB':
                wizard.exchange_rate_display = 'No conversion needed (USD)'
                continue

            if wizard.use_custom_rate and wizard.custom_exchange_rate:
                wizard.exchange_rate_display = f'Custom: {wizard.custom_exchange_rate:.4f} VEB/USD'
                continue

            # Determine date for rate lookup
            if wizard.rate_date:
                lookup_date = wizard.rate_date
            elif wizard.payslip_ids and len(wizard.payslip_ids) == 1:
                lookup_date = wizard.payslip_ids[0].date_to
            else:
                wizard.exchange_rate_display = 'Select payslip(s) to see rate'
                continue

            # Lookup rate
            veb_currency = wizard.env['res.currency'].search([('name', '=', 'VEB')], limit=1)
            if veb_currency:
                rate_record = wizard.env['res.currency.rate'].search([
                    ('currency_id', '=', veb_currency.id),
                    ('name', '<=', lookup_date)
                ], order='name desc', limit=1)

                if rate_record and rate_record.company_rate:
                    wizard.exchange_rate_display = (
                        f'Auto: {rate_record.company_rate:.4f} VEB/USD '
                        f'(Rate of {rate_record.name.strftime("%d/%m/%Y")})'
                    )
                else:
                    wizard.exchange_rate_display = f'No rate found for {lookup_date.strftime("%d/%m/%Y")}'
            else:
                wizard.exchange_rate_display = 'VEB currency not found in system'

    def action_generate_report(self):
        """Generate compact payslip report with selected currency"""
        self.ensure_one()

        if not self.payslip_ids:
            from odoo.exceptions import UserError
            raise UserError('Please select at least one payslip to generate the report.')

        # Prepare data for report
        data = {
            'payslip_ids': self.payslip_ids.ids,
            'currency_id': self.currency_id.id,
            'use_custom_rate': self.use_custom_rate,
            'custom_exchange_rate': self.custom_exchange_rate,
            'rate_date': self.rate_date.isoformat() if self.rate_date else False,
        }

        # Return report action
        return self.env.ref('ueipab_payroll_enhancements.action_report_payslip_compact').report_action(
            self.payslip_ids,
            data=data
        )
