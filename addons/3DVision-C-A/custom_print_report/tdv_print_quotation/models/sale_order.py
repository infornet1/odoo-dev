# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):  
    _inherit = 'sale.order'
    
    enable_custom_quotation_print = fields.Boolean(related="company_id.enable_custom_quotation_print")

    def action_print_custom_quotation(self):
        return self.env.ref("tdv_print_quotation.action_custom_quotation_report").report_action(self)
    
    def action_print_custom_quotation_free(self):
        return self.env.ref("tdv_print_quotation.action_custom_quotation_report_free").report_action(self)