from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    second_currency_id = fields.Many2one("res.currency", "Second Currency")
    fixed_ref = fields.Boolean("Fixed Currency", default=False)
    product_cost_updatable = fields.Boolean("Product Cost Update", default=False)
    show_second_currency_rate = fields.Boolean("Show Currency Rate", default=False)
