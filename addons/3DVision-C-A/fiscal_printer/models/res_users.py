from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    fp_fiscal_group_id = fields.Many2one("fp.fiscal.group", string="Fiscal Group")
