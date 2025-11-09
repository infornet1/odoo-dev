from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    original_price = fields.Float(string="Original Price", compute='_compute_original_price', store=True)

    @api.depends('price_unit')
    def _compute_original_price(self):
        for line in self:
            if line.move_id.state == 'draft' and not line.original_price:
                line.original_price = line.price_unit