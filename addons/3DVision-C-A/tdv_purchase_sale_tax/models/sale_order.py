from odoo import fields, models, api

class SaleOrder(models.Model):
  _inherit = 'sale.order'

  sale_tax_id = fields.Many2many('account.tax', 
    string='Sale Tax',
    domain="[('type_tax_use', '=', 'sale'),('show_sale_tax', '=', True)]")
  enable_sale_tax = fields.Boolean(related='company_id.enable_sale_tax')

  
  @api.onchange('sale_tax_id')
  def onchange_sale_tax_id(self):
      for order in self.order_line:
        order.tax_id = self.sale_tax_id
    