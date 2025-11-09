from odoo import models, fields, api

class HrSalaryRuleParameter(models.Model):
    _inherit = "hr.rule.parameter"

    is_contractual = fields.Boolean(default=False)