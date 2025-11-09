from odoo import fields, models


FISCAL_TYPE_SEL = [("0", "EXENTO"), ("1", "IVAG"), ("2", "IVAR"), ("3", "IVAL")]


class AccountTax(models.Model):
    _inherit = "account.tax"

    x_tipo_alicuota = fields.Selection([
        ("exento", "Exento"),
        ("general", "General"),
        ("reducido", "Reducido"),
        ("adicional", "Adicional"),
    ], "Tipo de alícuota", default="general")
