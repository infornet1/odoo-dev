from odoo import models, fields, api

class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input"

    employee_id = fields.Many2one(related="payslip_id.employee_id", store=True)
    state = fields.Selection(related="payslip_id.state", store=True)
    payslip_run_id = fields.Many2one(related="payslip_id.payslip_run_id", store=True)
    # contract_id = fields.Many2one(store=True)