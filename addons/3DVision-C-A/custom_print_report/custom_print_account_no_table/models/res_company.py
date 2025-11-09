from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    custom_header = fields.Html(string="Encabezado Personalizado")
    custom_footer = fields.Html(string="Pie de Página Personalizado")
    rug = fields.Char(string="RUG")
    lae = fields.Char(string="LAE")