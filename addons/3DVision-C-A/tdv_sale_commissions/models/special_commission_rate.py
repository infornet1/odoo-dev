from odoo import fields, models


class SpecialCommissionRate(models.Model):
    _name = 'special.commission.rate'
    _description = 'special commission rate'

    partner_id = fields.Many2one(string='partner', comodel_name='res.partner')
    related_partner = fields.Many2one(
        string='client', comodel_name='res.partner'
    )
    service_rate = fields.Float(string='service', default=0.0)
    sale_rate = fields.Float(string='sale', default=0.0)
