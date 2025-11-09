from odoo import models, fields, api

class PosPayment(models.Model):
  _inherit = 'pos.payment'

  reference = fields.Char('Reference Payment', help="Reference entered for payment", default=False)
