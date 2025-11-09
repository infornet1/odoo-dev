# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    custom_print_enabled = fields.Boolean(
        string="Impresión Personalizada Habilitada",
        compute="_compute_custom_print_enabled",
        store=False,
    )
    
    @api.depends('company_id')
    def _compute_custom_print_enabled(self):
        """Determina si la impresión personalizada está habilitada en la configuración."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        enabled = ICPSudo.get_param('custom_print.enable_custom_print', False)
        for order in self:
            order.custom_print_enabled = enabled
    
    def action_print_custom_quotation(self):
        """Acción para imprimir la cotización con formato personalizado."""
        self.ensure_one()
        return self.env.ref('custom_print.action_custom_quotation_report').report_action(self)
