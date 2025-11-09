# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'account.move'
    
    enable_custom_invoice_format = fields.Boolean(related="company_id.enable_custom_invoice_format")

    def action_print_custom_invoice(self):
        return self.env.ref("tdv_print_invoice.action_custom_invoice_report").report_action(self)
    
    def action_print_custom_invoice_free(self):
        return self.env.ref("tdv_print_invoice.action_custom_invoice_report_free").report_action(self)