from odoo import api, fields, models

class PosOrder(models.Model):
  _inherit = 'pos.order'

  def _payment_fields(self, order, ui_paymentline):
    res = super()._payment_fields(order, ui_paymentline)
    res['reference'] = ui_paymentline.get('reference')
    return res