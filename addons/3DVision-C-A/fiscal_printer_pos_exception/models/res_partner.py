from odoo import models, api

class Partner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create_from_ui(self, partner):
        if partner.get('country_id'):
            partner['country_id'] = int(partner.get('country_id'))       
        if partner.get('city_id'):
            city_id = int(partner.get('city_id'))
            partner['city_id'] = city_id
            City = self.env['res.city']
            city = City.browse(city_id)
            if city.exists():
                partner['city'] = city.name
            else:
                partner['city'] = ''

        return super().create_from_ui(partner)