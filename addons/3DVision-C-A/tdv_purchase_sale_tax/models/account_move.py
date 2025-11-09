from odoo import fields, models, api

class AccountMove(models.Model):
  _inherit = 'account.move'

  purchase_tax_ids = fields.Many2many('account.tax','account_move_purchase_tax_rel', string='Retention Vendor',
  domain="[('show_purchase_tax', '=', True)]")
  sale_tax_ids = fields.Many2many('account.tax','account_move_sale_tax_rel', string='Sale Tax',
  domain="[('show_sale_tax', '=', True)]")
  enable_purchase_tax = fields.Boolean(related='company_id.enable_purchase_tax')
  enable_sale_tax = fields.Boolean(related='company_id.enable_sale_tax')
  
  enable_recalculate_prices = fields.Boolean(related='company_id.enable_recalculate_prices')
  recalculate_prices = fields.Boolean(string='Recalcular Precios sin Impuestpos', default=False)

# para factura de cliente 
  @api.onchange('recalculate_prices', 'sale_tax_ids')
  def _onchange_recalculate_prices(self):
    
   if self.recalculate_prices and self.sale_tax_ids:
     total_tax_rate = sum(self.sale_tax_ids.mapped('amount')) / 100

     for line in self.invoice_line_ids:
       if line.price_unit:
         line.price_unit = line.price_unit / (1 + total_tax_rate)
   
    # if self.recalculate_prices:
    #   for line in self.invoice_line_ids:
    #     if line.price_unit:
    #       line.price_unit = line.price_unit / 1.16

  @api.onchange('purchase_tax_ids', 'sale_tax_ids')
  def onchange_tax_id(self):
    if self.move_type == 'in_invoice':
      for line in self.invoice_line_ids:
             line.tax_ids = self.purchase_tax_ids
    elif self.move_type == 'out_invoice':
        for line in self.invoice_line_ids:
          line.tax_ids = self.sale_tax_ids