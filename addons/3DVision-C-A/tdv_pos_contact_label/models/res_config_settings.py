from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_restrict_partner_by_tag = fields.Boolean(
        related='pos_config_id.restrict_partner_by_tag',
        string="Restrict Partners by Tag in POS",
        readonly=False,
    )
    pos_allowed_partner_tag_ids = fields.Many2many(
        related='pos_config_id.allowed_partner_tag_ids',
        string="Allowed Partner Tags in POS",
        readonly=False,
    ) 