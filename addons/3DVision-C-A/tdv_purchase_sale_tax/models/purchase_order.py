from odoo import fields, models, api

class PurchaseOrder(models.Model):
  _inherit = 'purchase.order'

  purchase_tax_ids = fields.Many2many('account.tax', 
                      string='Retention Vendor', 
                    domain="[('type_tax_use', '=', 'purchase'), ('show_purchase_tax', '=', True)]")
  enable_purchase_tax = fields.Boolean(related='company_id.enable_purchase_tax')

  @api.onchange('purchase_tax_ids')
  def onchange_purchase_tax_ids(self):
    for line in self.order_line:
      line.taxes_id = self.purchase_tax_ids
        
# 