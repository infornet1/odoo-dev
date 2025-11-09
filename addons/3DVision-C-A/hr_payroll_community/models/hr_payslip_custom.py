# -*- coding: utf-8 -*-

from odoo import models

class HrPayslipCustom(models.Model):
    _inherit = 'hr.payslip'

    def print_payslip_custom(self):
        """Print payslip custom reports - emergency fix"""
        return self.env.ref('hr_payroll_community.hr_payslip_new_report_action').report_action(self)