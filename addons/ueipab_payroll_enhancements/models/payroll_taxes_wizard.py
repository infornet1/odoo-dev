# -*- coding: utf-8 -*-
"""
Payroll Taxes Report Wizard (PLACEHOLDER)

This wizard will generate tax withholding reports (ARI, Social Security, etc.)
Status: Under Development
"""

from odoo import models, fields, _
from odoo.exceptions import UserError


class PayrollTaxesWizard(models.TransientModel):
    """Wizard for generating Payroll Taxes reports."""

    _name = 'payroll.taxes.wizard'
    _description = 'Payroll Taxes Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )

    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Filter specific employees (leave empty for all)'
    )

    def action_print_report(self):
        """Generate Payroll Taxes report."""
        raise UserError(_(
            'Payroll Taxes Report - Under Development\n\n'
            'This report will show:\n'
            '• ARI (Income Tax) withholdings by employee\n'
            '• Social Security contributions (IVSS, BANAVIH, INCES)\n'
            '• Tax summary by period\n'
            '• Exportable for tax filing\n\n'
            'Coming soon in next update!'
        ))
