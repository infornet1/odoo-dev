from odoo import models, fields, api

class PosPaymentMethod(models.Model):
  _inherit = 'pos.payment.method'

  is_ref_payment = fields.Boolean(string="Is Ref Payment", default=False, help="If it is marked, this payment method will require a reference at the point of sale")