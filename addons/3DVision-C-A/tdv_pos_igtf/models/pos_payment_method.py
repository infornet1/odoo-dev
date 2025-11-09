from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_igtf = fields.Boolean(related="journal_id.is_igtf", readonly=False)
