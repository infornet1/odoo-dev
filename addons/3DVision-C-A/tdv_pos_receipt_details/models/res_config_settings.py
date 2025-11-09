from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    receipt_partner_details = fields.Boolean(related="pos_config_id.receipt_partner_details", readonly=False)
    receipt_partner_name = fields.Boolean(related="pos_config_id.receipt_partner_name", readonly=False)
    receipt_partner_address = fields.Boolean(related="pos_config_id.receipt_partner_address", readonly=False)
    receipt_partner_phone = fields.Boolean(related="pos_config_id.receipt_partner_phone", readonly=False)
    receipt_partner_email = fields.Boolean(related="pos_config_id.receipt_partner_email", readonly=False)
    receipt_partner_vat = fields.Boolean(related="pos_config_id.receipt_partner_vat", readonly=False)