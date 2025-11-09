from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    igtf_account_id = fields.Many2one('account.account', 'IGTF account')
