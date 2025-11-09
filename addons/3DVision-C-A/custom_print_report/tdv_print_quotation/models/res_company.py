from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_custom_quotation_print = fields.Boolean(
        string="Enable Custom Quotation Print",
        help="Activar formato de impresión personalizado para cotizaciones"
    )   