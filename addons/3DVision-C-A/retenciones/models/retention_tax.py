from odoo import models, fields, api

RETENTION_TYPES = [
    ("iva", "IVA"),
    ("islr", "ISLR"),
    ("iae", "IAE"),
]


class RetentionTax(models.Model):
    _name = "retention.tax"
    _description = "Retention percentage applied"
    _rec_names_search = ["name", "code"]

    tax_name = fields.Char("Tax name", required=True)
    name = fields.Char("Name")
    tax = fields.Float("Retention rate", required=True)
    code = fields.Char("Code", default="")
    type = fields.Selection(RETENTION_TYPES, "Retention type", required=True)
    decrement = fields.Monetary(
        string="Decrement (ISLR)",
        currency_field="currency_id"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id
    )
