# -*- coding: utf-8 -*-
"""
Payroll Disbursement Detail Report Parser

This AbstractModel customizes the report rendering to properly receive
payslip IDs from the wizard and build the docs recordset for the template.
"""

from odoo import models


class PayrollDisbursementReport(models.AbstractModel):
    """Custom report parser for Payroll Disbursement Detail report."""

    _name = 'report.ueipab_payroll_enhancements.disbursement_detail_doc'
    _description = 'Payroll Disbursement Detail Report Parser'

    def _get_report_values(self, docids, data=None):
        """Build report data for QWeb template.

        This method is called by Odoo's report engine to prepare data
        for the QWeb template. It receives the docids and data passed
        from the wizard and builds the proper context.

        Args:
            docids (list): List of payslip IDs (usually None from wizard)
            data (dict): Data dict from wizard containing payslip_ids

        Returns:
            dict: Context dictionary for QWeb template with 'docs' recordset
        """
        # Get payslip IDs from data dict (passed by wizard)
        payslip_ids = data.get('payslip_ids', []) if data else []

        # If no IDs in data, try to use docids parameter
        if not payslip_ids and docids:
            payslip_ids = docids

        # Build payslip recordset from IDs
        payslips = self.env['hr.payslip'].browse(payslip_ids)

        # Sort payslips by employee name
        payslips = payslips.sorted(lambda p: p.employee_id.name or '')

        # Return context for QWeb template
        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,  # This is what the template uses!
            'data': data,      # Additional wizard data
        }
