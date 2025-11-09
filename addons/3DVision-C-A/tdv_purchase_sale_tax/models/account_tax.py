from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = 'account.tax'

    show_purchase_tax = fields.Boolean('Show Provider Retention', default=False)
    show_sale_tax = fields.Boolean('Show Sales Tax',  default=False)
    enable_sale_tax = fields.Boolean(related='company_id.enable_sale_tax')
    enable_purchase_tax = fields.Boolean(related='company_id.enable_purchase_tax')






