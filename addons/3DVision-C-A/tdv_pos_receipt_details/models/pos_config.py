from odoo import fields, api, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    receipt_partner_details = fields.Boolean("Show Partner Details")
    receipt_partner_name = fields.Boolean("Partner Name")
    receipt_partner_address = fields.Boolean("Partner Address")
    receipt_partner_phone = fields.Boolean("Partner Phone")
    receipt_partner_email = fields.Boolean("Partner Email")
    receipt_partner_vat = fields.Boolean("Partner Vat")

