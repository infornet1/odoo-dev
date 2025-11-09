# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    enable_custom = fields.Boolean(  
        string="Activar Formato Personalizado",
        help="Activar formato de impresión personalizado para cotizaciones",
    )
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            enable_custom=ICPSudo.get_param('custom_print.enable_custom', False),  
        )
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('custom_print.enable_custom', self.enable_custom)  