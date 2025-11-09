from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_custom_invoice_dispatch_guide_format = fields.Boolean(
        string="Enable Custom Invoice Dispatch Guide Format",
        help="Activar formato de impresión personalizado para guia de despacho"
    )