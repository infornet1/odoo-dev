# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked.days'

    amount_in_ves = fields.Monetary(
        string='Monto en moneda secundaria',
        compute='_compute_amount_in_ves',
        store=True,
        currency_field='conversion_currency_id'
    )
    conversion_currency_id = fields.Many2one(
        'res.currency', 
        string='Moneda de conversión',
        related='payslip_id.company_id.currency_conversion_id',
        readonly=True
    )

    @api.depends('number_of_hours', 'payslip_id.company_id.currency_id', 'payslip_id.company_id.currency_conversion_id')
    def _compute_amount_in_ves(self):
        for worked_days in self:
            if not worked_days.payslip_id.company_id.currency_conversion_id:
                worked_days.amount_in_ves = 0.0
                continue

            company_currency = worked_days.payslip_id.company_id.currency_id
            conversion_currency = worked_days.payslip_id.company_id.currency_conversion_id

            # Calculate base amount from hours (simple calculation)
            base_amount = worked_days.number_of_hours * 100  # Basic hourly rate estimation

            if company_currency and conversion_currency:
                worked_days.amount_in_ves = company_currency._convert(
                    base_amount,
                    conversion_currency,
                    worked_days.payslip_id.company_id,
                    fields.Date.today()
                )
            else:
                worked_days.amount_in_ves = 0.0

