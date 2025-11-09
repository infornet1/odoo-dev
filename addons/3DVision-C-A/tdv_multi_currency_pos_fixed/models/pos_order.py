from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PosOrder(models.Model):
  _inherit = 'pos.order'

  def _payment_fields(self, order, ui_paymentline):
    res = super()._payment_fields(order, ui_paymentline)
    res['amount_full_precision'] = ui_paymentline.get('amount')

    print("POS ORDER NUEVO ADDON: ",res)
    return res

  @api.constrains('payment_ids', 'amount_total')
  def _check_payment_amount(self):
    """Validar que el monto pagado coincida exactamente con el total de la orden"""
    for order in self:
      if order.state in ['paid', 'done', 'invoiced']:
        total_paid = sum(payment.amount for payment in order.payment_ids)
        total_with_tax = order.amount_total
        # Usar una tolerancia muy pequeña para evitar problemas de redondeo
        tolerance = 0.001
        if abs(total_paid - total_with_tax) > tolerance:
          raise ValidationError(
            f"El monto pagado ({total_paid:.2f}) no coincide con el total de la orden ({total_with_tax:.2f}). "
            f"Diferencia: {abs(total_paid - total_with_tax):.2f}"
          )