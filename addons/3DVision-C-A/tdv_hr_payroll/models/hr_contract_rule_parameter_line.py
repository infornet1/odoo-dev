from odoo import models, fields, api

class HrContractRuleParameterLine(models.Model):
    _name = "hr.contract.rule.parameter.line"
    _description = "Lines between a contract and a rule parameter"

    contract_id = fields.Many2one("hr.contract")
    rule_parameter_id = fields.Many2one(
        comodel_name="hr.rule.parameter",
        string="Rule Parameter",
        domain="[('is_contractual', '=', True)]"
    )
    name = fields.Char("Description")
    value = fields.Text()

    @api.onchange("rule_parameter_id")
    def onchange_rule_parameter(self):
        for contract in self:
            contract.name = contract.rule_parameter_id.name
            rule_parameter = self.env["hr.rule.parameter.value"].search([
                ("code", "=", contract.rule_parameter_id.code),
                ("date_from", "<=", fields.Date.today()),], limit=1
            )

            contract.value = rule_parameter.parameter_value if rule_parameter else None