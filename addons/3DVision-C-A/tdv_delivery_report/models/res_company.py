from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_custom_delivery_print = fields.Boolean(
        string="Enable Custom Delivery Print",
        help="Activar formato de impresión personalizado para Entregas",
    )   