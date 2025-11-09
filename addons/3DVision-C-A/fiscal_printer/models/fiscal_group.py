from odoo import fields, models


class FiscalGroup(models.Model):
    _name = "fp.fiscal.group"
    _description = "Fiscal Group"

    name = fields.Char("Name", required=True)
    description = fields.Char("Description", required=False)
    user_ids = fields.One2many(
        "res.users", "fp_fiscal_group_id", string="Related Partners"
    )
    company_id = fields.Many2one("res.company", string="Company")
