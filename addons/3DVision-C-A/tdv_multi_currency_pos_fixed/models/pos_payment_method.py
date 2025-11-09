from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    currency_id = fields.Many2one(related="journal_id.currency_id")

