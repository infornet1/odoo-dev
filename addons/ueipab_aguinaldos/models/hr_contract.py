# -*- coding: utf-8 -*-

from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    ueipab_monthly_salary = fields.Monetary(
        string='Monthly Salary (Spreadsheet)',
        help='Total monthly salary from payroll spreadsheet (Column K in USD). '
             'Used for Aguinaldos, year-end bonuses, and other special calculations. '
             'This field tracks the official salary independent of the 70/25/5 distribution '
             'used for regular payroll. Synced from Google Sheets using '
             'sync-monthly-salary-from-spreadsheet.py script.',
        currency_field='currency_id',
    )

    ueipab_salary_notes = fields.Text(
        string='Salary Notes (Audit Trail)',
        help='Complete audit trail for ueipab_monthly_salary including:\n'
             '- Source spreadsheet and date\n'
             '- Column reference\n'
             '- Original VEB amount\n'
             '- Exchange rate used\n\n'
             'Format: "From payroll sheet {date}, Column K ({veb} VEB) @ {rate} VEB/USD"\n\n'
             'Example: "From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"\n\n'
             'This provides complete traceability and allows verification of calculations at any time.',
    )
