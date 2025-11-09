from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    report_currency_selection = fields.Selection(related="pos_config_id.report_currency_selection", readonly=False)