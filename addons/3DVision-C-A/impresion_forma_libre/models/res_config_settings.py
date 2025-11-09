from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_freeform_selection = fields.Selection(related='company_id.invoice_freeform_selection', readonly=False, required=True)