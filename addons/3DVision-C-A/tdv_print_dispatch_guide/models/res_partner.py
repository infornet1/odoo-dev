from odoo import models, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def create(self, vals):
        if self.env.context.get('is_chofer'):
            category = self.env.ref('tdv_print_dispatch_guide.category_chofer', raise_if_not_found=False)
            if category:
                if 'category_id' in vals and vals['category_id']:
                    if isinstance(vals['category_id'], list):
                        vals['category_id'].append(category.id)
                    else:
                        vals['category_id'] = [vals['category_id'], category.id]
                else:
                    vals['category_id'] = [(6, 0, [category.id])]
        return super().create(vals) 