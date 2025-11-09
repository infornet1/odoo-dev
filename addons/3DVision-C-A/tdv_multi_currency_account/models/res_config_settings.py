from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    second_currency_id = fields.Many2one(related="company_id.second_currency_id", readonly=False)
    fixed_ref = fields.Boolean("Fixed Currency", related="company_id.fixed_ref", readonly=False)
    product_cost_updatable = fields.Boolean(related="company_id.product_cost_updatable", readonly=False)
    show_second_currency_rate = fields.Boolean(related="company_id.show_second_currency_rate", readonly=False)
