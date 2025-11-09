from odoo import models, fields, api

class PosOrderDraft(models.Model):
    _name = 'pos.order.draft'
    _description = 'POS Order Draft'
 
    uid = fields.Char('Order UID', required=True, index=True)
    data = fields.Json('Order Data', required=True)
    session_id = fields.Many2one('pos.session', string='POS Session')
    user_id = fields.Many2one('res.users', string='User')
    last_update = fields.Datetime('Last Update', default=fields.Datetime.now) 