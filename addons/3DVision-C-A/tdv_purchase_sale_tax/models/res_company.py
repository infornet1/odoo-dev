from odoo import models, fields, api

class ResCompany(models.Model):
  _inherit = 'res.company'

  enable_purchase_tax = fields.Boolean(string='Purchase Taxes', default=False)
  enable_sale_tax = fields.Boolean(string='Sale Taxes', default=False)
  enable_recalculate_prices = fields.Boolean(string='Recalculate price without tax customer invoice', default=False)