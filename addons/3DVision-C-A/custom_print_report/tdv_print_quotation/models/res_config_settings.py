# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    enable_custom_quotation_print = fields.Boolean(related="company_id.enable_custom_quotation_print", readonly=False)