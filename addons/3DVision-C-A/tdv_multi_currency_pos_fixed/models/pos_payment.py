from odoo import models, fields, api

class PosPayment(models.Model):
  _inherit = 'pos.payment'

  payment_method_currency_id  = fields.Many2one ('res.currency', compute='_compute_currency_id', string='Moneda del Método de Pago')
  converted_amount = fields.Monetary('Payment Amount', compute='_compute_converted_amount', currency_field='payment_method_currency_id', store=True)
  amount_full_precision = fields.Float('Monto con decimales completos',digits=(16, 8))


  @api.depends('payment_method_currency_id', 'company_id')
  def _compute_currency_id(self):
    for payment in self:
      if payment.payment_method_id and payment.payment_method_id.currency_id:
        payment.payment_method_currency_id = payment.payment_method_id.currency_id
      else:
        payment.payment_method_currency_id = payment.company_id.currency_id

      payment.amount = payment.amount_full_precision
      print("\n\nFuncion 1 ADDON NUEVO: ")
      print ("Monto redondeado: ", payment.amount)
      print("Monto con decimales completos: ",payment.amount_full_precision)


  @api.depends('payment_method_currency_id', 'currency_id','amount')
  def _compute_converted_amount(self):
    for payment in self:
      company_currency = payment.company_id.currency_id
      if payment.payment_method_currency_id:
        payment.converted_amount = payment.currency_id._convert(
          from_amount=payment.amount_full_precision,
          to_currency=payment.payment_method_currency_id, 
          company=payment.company_id,
          date=payment.payment_date,
          round=False,
        )

      payment.amount = payment.amount_full_precision
      print("\n\nFuncion 2 ADDON NUEVO: ")
      print("Monto convertido: ",payment.converted_amount)
      print("Monto con redondeo:",payment.amount)
      print("Monto con decimales completos: ",payment.amount_full_precision)