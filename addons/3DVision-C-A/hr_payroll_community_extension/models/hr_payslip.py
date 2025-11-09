# -*- coding: utf-8 -*-

from odoo import models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def print_payslip_custom(self):
        """Print payslip custom reports - temporary implementation"""
        return self.env.ref('hr_payroll_community.hr_payslip_new_report_action').report_action(self)