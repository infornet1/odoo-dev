# -*- coding: utf-8 -*-
"""
Aguinaldos Disbursement Report Parser

Simple report for Christmas bonus (Aguinaldos) disbursement.
Shows employee list with aguinaldo amounts for finance approval.
"""

from odoo import models, api


class AguinaldosDisbursementReport(models.AbstractModel):
    """Custom report parser for Aguinaldos Disbursement Report."""

    _name = 'report.ueipab_payroll_enhancements.aguinaldos_disbursement_doc'
    _description = 'Aguinaldos Disbursement Report Parser'

    def _get_report_values(self, docids, data=None):
        """Build report data for QWeb template.

        Args:
            docids (list): List of payslip IDs (usually None from wizard)
            data (dict): Data dict from wizard containing payslip_ids

        Returns:
            dict: Context dictionary for QWeb template
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

        # Get currency from wizard data
        usd = self.env.ref('base.USD')
        currency_id = data.get('currency_id') if data else usd.id
        currency = self.env['res.currency'].browse(currency_id)

        # Calculate exchange rate for VEB (if applicable)
        exchange_rate = 1.0
        exchange_rate_source = 'USD (no conversion)'

        if currency != usd and payslips:
            # Try to get exchange rate from batch first
            batch = payslips[0].payslip_run_id if payslips else None

            if batch and batch.exchange_rate and batch.exchange_rate > 0:
                exchange_rate = batch.exchange_rate
                exchange_rate_source = f'Batch ({batch.name})'
            elif payslips[0].exchange_rate_used and payslips[0].exchange_rate_used > 0:
                exchange_rate = payslips[0].exchange_rate_used
                exchange_rate_source = 'Payslip (exchange_rate_used)'
            else:
                # Fallback to date-based currency lookup
                latest_date = max(payslips.mapped('date_to'))
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id),
                    ('name', '<=', latest_date)
                ], limit=1, order='name desc')
                if rate_record:
                    exchange_rate = rate_record.company_rate
                    exchange_rate_source = f'Date lookup ({latest_date})'

        # Build employee data list with aguinaldo amounts
        employee_data = []
        total_aguinaldo = 0.0
        total_salary_ref = 0.0

        for payslip in payslips:
            # Get AGUINALDOS line amount
            aguinaldo_line = payslip.line_ids.filtered(
                lambda l: l.salary_rule_id.code == 'AGUINALDOS'
            )
            aguinaldo_amount = aguinaldo_line[0].total if aguinaldo_line else 0.0

            # Get salary reference from contract (V2 salary)
            salary_ref = payslip.contract_id.ueipab_salary_v2 or 0.0

            employee_data.append({
                'employee': payslip.employee_id,
                'payslip': payslip,
                'cedula': payslip.employee_id.identification_id or 'N/A',
                'name': payslip.employee_id.name,
                'salary_ref': salary_ref,
                'aguinaldo': aguinaldo_amount,
            })

            total_aguinaldo += aguinaldo_amount
            total_salary_ref += salary_ref

        # Return context for QWeb template
        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'employee_data': employee_data,
            'currency': currency,
            'exchange_rate': exchange_rate,
            'exchange_rate_source': exchange_rate_source,
            'total_aguinaldo': total_aguinaldo,
            'total_salary_ref': total_salary_ref,
            'employee_count': len(employee_data),
        }
