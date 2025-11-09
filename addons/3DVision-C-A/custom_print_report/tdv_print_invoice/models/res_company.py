from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_custom_invoice_format = fields.Boolean(
        string="Enable Custom Invoice Format",
        help="Activar formato de impresión personalizado para cotizaciones"
    )