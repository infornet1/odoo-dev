from odoo import fields, api, models

class HrEmployee(models.Model):
    _inherit = "hr.contract"

    def _default_rule_parameter_line(self):
        DOMAIN = [("is_contractual", "=", True)]
        Lines = self.env["hr.contract.rule.parameter.line"]
        rules = self.env["hr.rule.parameter"].search(DOMAIN)

        lines = Lines.create([{"rule_parameter_id": p.id } for p in rules])
        lines.onchange_rule_parameter()
        return lines

    rule_parameter_line_ids = fields.One2many(
        comodel_name="hr.contract.rule.parameter.line",
        inverse_name="contract_id",
        string="Parameter rules",
        default=_default_rule_parameter_line
    )

    # @api.model
    # def create(self, *args, **kwargs):
    #     res = super().create(*args, **kwargs)
    #     res.write({
    #         "rule_parameter_line_ids": [(0, 0, {
    #             "rule_parameter_id": rule_parameter.id
    #         }) for rule_parameter in self.env["hr.rule.parameter"].search([])]
    #     })
    #     return res