# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'account.move'
    
    enable_custom_invoice_dispatch_guide_format = fields.Boolean(related="company_id.enable_custom_invoice_dispatch_guide_format")
    vehicle_id = fields.Many2one(comodel_name="vehicle", string="Vehículo")
    chofer_id = fields.Many2one(comodel_name="res.partner", string="Chofer", domain="[('category_id.name', 'ilike', 'chofer')]")

    def action_print_custom_invoice_dispatch_guide(self):
        return self.env.ref("tdv_print_dispatch_guide.action_custom_invoice_report").report_action(self)