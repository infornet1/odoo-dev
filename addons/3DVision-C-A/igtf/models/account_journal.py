from odoo import models, api, fields

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_igtf = fields.Boolean('Is IGTF', default=False)