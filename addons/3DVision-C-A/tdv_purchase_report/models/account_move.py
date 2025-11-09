from odoo import models, fields, api
class AccountMove(models.Model):
    _inherit = 'account.move'

    import_plan_number = fields.Char(string='Import Plan Number')
    file_number = fields.Char(string='File Number')
