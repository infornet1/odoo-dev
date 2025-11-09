from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        # Si el contexto viene de la creación de chofer, asignar la categoría por XML ID
        if self.env.context.get('is_chofer'):

            category = self.env.ref('tdv_delivery_report.category_chofer', raise_if_not_found=False)
            
            if category:
                # Si ya hay categorías, las sumamos
                if 'category_id' in vals and vals['category_id']:
                    if isinstance(vals['category_id'], list):
                        vals['category_id'].append(category.id)
                    else:
                        vals['category_id'] = [vals['category_id'], category.id]
                else:
                    vals['category_id'] = [(6, 0, [category.id])]
        return super().create(vals)
