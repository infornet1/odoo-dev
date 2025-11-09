from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_igtf_percentage = fields.Float(related="pos_config_id.igtf_percentage", readonly=False)
    pos_igtf_product_id = fields.Many2one(related="pos_config_id.igtf_product_id", readonly=False)