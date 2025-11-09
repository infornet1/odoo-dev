from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    ruc = fields.Char("RUC")
    taxpayer_license = fields.Char("LAE")
    ced_rif = fields.Char("Document/RIF")
    is_legal_entity = fields.Boolean("Is Legal Entity", default=False)
