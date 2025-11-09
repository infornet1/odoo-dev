from odoo import fields, models

class ResConfigSettings(models.TransientModel):
  _inherit = 'res.config.settings'

  enable_purchase_tax = fields.Boolean(related="company_id.enable_purchase_tax", readonly=False)
  enable_sale_tax = fields.Boolean(related="company_id.enable_sale_tax", readonly=False)
  enable_recalculate_prices = fields.Boolean(related="company_id.enable_recalculate_prices", readonly=False)
