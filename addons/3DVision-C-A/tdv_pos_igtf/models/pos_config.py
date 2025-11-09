from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = "pos.config"

    igtf_percentage = fields.Float("IGTF Percentage", default=3)
    igtf_product_id = fields.Many2one("product.product", "IGTF Product",
        domain=[("type", "=", "service"),("available_in_pos", "=", True)]
    )
