from odoo import models, api, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    igtf_account_id = fields.Many2one(
        related="company_id.igtf_account_id", readonly=False)
