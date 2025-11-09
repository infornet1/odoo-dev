from odoo import models, fields, api

class HrPayslipLine(models.Model):
    _inherit = "hr.payslip.line"

    state = fields.Selection(related="slip_id.state", store=True)
    employee_identificacion = fields.Char(related="employee_id.identification_id", store=True)
    employee_bank_account_id = fields.Many2one(related="employee_id.bank_account_id", store=True)
    payslip_run_id = fields.Many2one(related="slip_id.payslip_run_id", store=True)