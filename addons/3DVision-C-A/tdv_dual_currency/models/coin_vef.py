from odoo import models, fields, api

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    wage_in_ves = fields.Monetary(
        string="Salario en Moneda de Conversión",
        compute="_compute_wage_in_ves",
        store=False,
        help="Salario convertido a la moneda de conversión configurada (opcional).",
        currency_field="conversion_currency_id"  # Asociar el campo con la moneda de conversión
    )

    conversion_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de Conversión",
        compute="_compute_conversion_currency",
        help="Moneda de conversión configurada en la compañía."
    )

    @api.depends('company_id.currency_conversion_id')
    def _compute_conversion_currency(self):
        for payslip in self:
            payslip.conversion_currency_id = payslip.company_id.currency_conversion_id

    @api.depends('net_wage', 'currency_id', 'conversion_currency_id')
    def _compute_wage_in_ves(self):
        for payslip in self:
            conversion_currency = payslip.conversion_currency_id
            if not conversion_currency:
                payslip.wage_in_ves = 0.0
                continue  # Salir del bucle para este payslip

            if payslip.currency_id and conversion_currency:
                payslip.wage_in_ves = payslip.currency_id._convert(
                    payslip.net_wage,
                    conversion_currency,
                    payslip.company_id or self.env.company,
                    fields.Date.today()
                )
            else:
                payslip.wage_in_ves = 0.0

