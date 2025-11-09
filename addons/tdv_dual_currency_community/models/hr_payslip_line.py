from odoo import models, fields, api

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    wage_in_ves = fields.Monetary(
        string='Monto de conversion',
        compute='_compute_amounts_in_ves',
        currency_field='conversion_currency_id',  # Clave para el símbolo
        store=True
    )
    total_in_ves = fields.Monetary(
        string='Total de conversion',
        compute='_compute_amounts_in_ves',
        currency_field='conversion_currency_id',  # Clave para el símbolo
        store=True
    )
    conversion_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de conversión',
        related='slip_id.contract_id.conversion_currency_id',  # Relación directa con el contrato
        readonly=True
    )

    @api.depends('amount', 'total', 'conversion_currency_id')
    def _compute_amounts_in_ves(self):
        for line in self:
            contract = line.slip_id.contract_id
            if not contract or not contract.conversion_currency_id:
                line.wage_in_ves = 0.0
                line.total_in_ves = 0.0
                continue
            
            company_currency = contract.company_id.currency_id
            conversion_currency = contract.conversion_currency_id
            
            line.wage_in_ves = company_currency._convert(
                line.amount,
                conversion_currency,
                contract.company_id,
                fields.Date.today()
            )
            line.total_in_ves = company_currency._convert(
                line.total,
                conversion_currency,
                contract.company_id,
                fields.Date.today()
            )