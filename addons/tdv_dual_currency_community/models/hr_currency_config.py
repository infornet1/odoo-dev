from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    currency_conversion_id = fields.Many2one(
        "res.currency",
        string="Moneda de Conversión",
        related="company_id.currency_conversion_id",  # Usar related para sincronizar con res.company
        readonly=False,
        help="Moneda a la que se convertirá el salario en las nóminas.",
    )

    custom_payslip_report = fields.Boolean(
        string="Impresión personalizada para recibos",
        related="company_id.custom_payslip_report",
        readonly=False,
    )

    def set_values(self):
        # Guardar valores en res.company (currency_conversion_id ya está relacionado)
        super().set_values()
        # No es necesario guardar currency_conversion_id en ir.config_parameter

    @api.model
    def get_values(self):
        res = super().get_values()
        # El campo related ya maneja la sincronización con res.company
        return res


class ResCompany(models.Model):
    _inherit = "res.company"

    currency_conversion_id = fields.Many2one(
        "res.currency",
        string="Moneda de Conversión",
        help="Moneda a la que se convertirá el salario en las nóminas.",
    )

    custom_payslip_report = fields.Boolean(
        string="Impresión personalizada para recibos",
        help="Habilita la impresión personalizada de recibos de nómina.",
    )
