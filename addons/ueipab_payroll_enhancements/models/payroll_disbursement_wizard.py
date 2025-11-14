# -*- coding: utf-8 -*-
"""
Payroll Disbursement Detail Report Wizard

This wizard allows users to generate detailed payroll disbursement reports
with flexible filtering options (batch or date range).
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PayrollDisbursementWizard(models.TransientModel):
    """Wizard for generating Payroll Disbursement Detail reports."""

    _name = 'payroll.disbursement.wizard'
    _description = 'Payroll Disbursement Detail Report Wizard'

    # ========================================
    # FILTER SELECTION
    # ========================================

    filter_type = fields.Selection([
        ('batch', 'Specific Batch'),
        ('date_range', 'Date Range'),
    ], string='Filter By', required=True, default='batch',
       help='Select how to filter payslips: by specific batch or by date range')

    # Batch selection (when filter_type = 'batch')
    batch_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        help='Select specific payslip batch to generate report for'
    )

    # Date range selection (when filter_type = 'date_range')
    date_from = fields.Date(
        string='Date From',
        default=lambda self: fields.Date.today().replace(day=1),
        help='Start date for payslip date range filter'
    )

    date_to = fields.Date(
        string='Date To',
        default=fields.Date.today,
        help='End date for payslip date range filter'
    )

    # Additional filters (apply to both modes)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Filter specific employees (leave empty for all employees)'
    )

    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter specific departments (leave empty for all departments)'
    )

    # Currency selection
    currency_id = fields.Many2one(
        'res.currency',
        string='Display Currency',
        required=True,
        default=lambda self: self.env.ref('base.USD'),
        help='Currency for report display (USD or VEB)'
    )

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    payslip_count = fields.Integer(
        string='Payslips Found',
        compute='_compute_payslip_count',
        help='Number of payslips matching current filter criteria (excludes cancelled payslips)'
    )

    @api.depends('filter_type', 'batch_id', 'date_from', 'date_to',
                 'employee_ids', 'department_ids')
    def _compute_payslip_count(self):
        """Count payslips matching current filter criteria."""
        for wizard in self:
            payslips = wizard._get_filtered_payslips()
            wizard.payslip_count = len(payslips)

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def _get_filtered_payslips(self):
        """Get payslips matching wizard filter criteria.

        Returns:
            recordset: hr.payslip records matching filters
        """
        self.ensure_one()

        # Include all payslips except cancelled ones
        # This allows reporting on draft, verify, done, and paid payslips
        domain = [('state', '!=', 'cancel')]

        # Filter by batch or date range
        if self.filter_type == 'batch':
            if not self.batch_id:
                return self.env['hr.payslip']
            domain.append(('payslip_run_id', '=', self.batch_id.id))
        else:  # date_range
            if self.date_from:
                domain.append(('date_from', '>=', self.date_from))
            if self.date_to:
                domain.append(('date_to', '<=', self.date_to))

        # Additional filters
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))

        # Find matching payslips
        payslips = self.env['hr.payslip'].search(domain)

        # Sort by employee name (can't use order='employee_id.name' in Odoo 17)
        return payslips.sorted(lambda p: p.employee_id.name or '')

    def action_print_report(self):
        """Generate and print the Payroll Disbursement Detail report.

        Returns:
            dict: Report action

        Raises:
            UserError: If no payslips match the filter criteria
        """
        self.ensure_one()

        # Validate filters
        if self.filter_type == 'batch' and not self.batch_id:
            raise UserError(_('Please select a payslip batch.'))

        if self.filter_type == 'date_range':
            if not self.date_from or not self.date_to:
                raise UserError(_('Please specify both start and end dates.'))
            if self.date_from > self.date_to:
                raise UserError(_('Start date must be before end date.'))

        # Get filtered payslips
        payslips = self._get_filtered_payslips()

        if not payslips:
            raise UserError(_(
                'No payslips found matching the selected criteria.\n\n'
                'Please ensure:\n'
                '- Payslips are not cancelled\n'
                '- Filter criteria are correct\n'
                '- Selected batch/date range contains payslips'
            ))

        # Get payslip IDs and ensure we have a fresh recordset
        # This is necessary because wizard is a TransientModel
        payslip_ids = payslips.ids

        # Prepare report data context
        data = {
            'wizard_id': self.id,
            'filter_type': self.filter_type,
            'batch_name': self.batch_id.name if self.batch_id else None,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_count': len(payslips.mapped('employee_id')),
            'payslip_count': len(payslips),
            'payslip_ids': payslip_ids,  # Store IDs in data for debugging
            'currency_id': self.currency_id.id,
            'currency_name': self.currency_id.name,
        }

        # Generate PDF report using the report's _render method directly
        report = self.env.ref('ueipab_payroll_enhancements.action_report_payroll_disbursement_detail')

        # Use report_action with explicit docids parameter
        return report.report_action(docids=payslip_ids, data=data)

    def action_preview(self):
        """Preview payslips that will be included in the report.

        Opens a tree view showing which payslips match the current filters.
        Useful for verifying selection before printing.

        Returns:
            dict: Action to display payslip list
        """
        self.ensure_one()

        payslips = self._get_filtered_payslips()

        return {
            'name': _('Payslips to Include in Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', payslips.ids)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
        }
