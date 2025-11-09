# -*- coding: utf-8 -*-

from odoo import models, fields, api

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    amount_in_ves = fields.Monetary(
        string='Monto en moneda secundaria',
        compute='_compute_amount_in_ves',
        store=True
    )
    conversion_currency_id = fields.Many2one(
        'res.currency', 
        string='Moneda de conversión',
        related='payslip_id.company_id.currency_conversion_id',
        readonly=True
    )

    @api.depends('amount', 'payslip_id.company_id.currency_id', 'payslip_id.company_id.currency_conversion_id')
    def _compute_amount_in_ves(self):
        for worked_days in self:
            if not worked_days.payslip_id.company_id.currency_conversion_id:
                worked_days.amount_in_ves = 0.0
                continue
                
            company_currency = worked_days.payslip_id.company_id.currency_id
            conversion_currency = worked_days.payslip_id.company_id.currency_conversion_id
            
            if company_currency and conversion_currency:
                worked_days.amount_in_ves = company_currency._convert(
                    worked_days.amount,
                    conversion_currency,
                    worked_days.payslip_id.company_id,
                    fields.Date.today()
                )
            else:
                worked_days.amount_in_ves = 0.0

