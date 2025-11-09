from odoo import models, fields, api

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    @api.model_create_multi
    def create(self, vals):
        res = super().create(vals)
        for slip in res:
            slip.input_line_ids |= self.env['hr.payslip.input'].create([{
                "name": input_type.name,
                "input_type_id": input_type.id,
                "payslip_id": slip.id,
                "contract_id": slip.contract_id.id,
                "amount": 0.0
            } for input_type in self.env["hr.payslip.input.type"].search([])])
        return res
