# -*- coding: utf-8 -*-

from odoo import models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def print_payslip_custom(self):
        """Print payslip custom reports for Venezuelan compliance"""
        # For now, return the standard payslip report
        # We'll enhance this with custom reports later
        return self.env.ref('hr_payroll_community.hr_payslip_new_report_action').report_action(self)