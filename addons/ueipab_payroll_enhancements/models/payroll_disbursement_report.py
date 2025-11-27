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

        # Get currency from wizard data
        usd = self.env.ref('base.USD')
        currency_id = data.get('currency_id') if data else usd.id
        currency = self.env['res.currency'].browse(currency_id)

        # Calculate exchange rate for VEB (if applicable)
        # DO NOT MODIFY PAYSLIP DATA - just pass the rate to template
        # Priority: 1) Batch exchange_rate, 2) Payslip exchange_rate_used, 3) Date-based lookup
        exchange_rate = 1.0
        exchange_rate_source = 'USD (no conversion)'

        if currency != usd and payslips:
            # Try to get exchange rate from batch first
            batch = payslips[0].payslip_run_id if payslips else None

            if batch and batch.exchange_rate and batch.exchange_rate > 0:
                # Priority 1: Use batch's custom exchange rate
                exchange_rate = batch.exchange_rate
                exchange_rate_source = f'Batch ({batch.name})'
            elif payslips[0].exchange_rate_used and payslips[0].exchange_rate_used > 0:
                # Priority 2: Use payslip's exchange_rate_used field
                exchange_rate = payslips[0].exchange_rate_used
                exchange_rate_source = 'Payslip (exchange_rate_used)'
            else:
                # Priority 3: Fallback to date-based currency lookup
                latest_date = max(payslips.mapped('date_to'))
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id),
                    ('name', '<=', latest_date)
                ], limit=1, order='name desc')
                if rate_record:
                    exchange_rate = rate_record.company_rate
                    exchange_rate_source = f'Date lookup ({latest_date})'

        # Return context for QWeb template
        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,  # UNCHANGED - keeps USD values from database
            'data': data,      # Additional wizard data
            'currency': currency,  # Pass currency for dynamic symbol display
            'exchange_rate': exchange_rate,  # Pass rate for template to multiply
            'exchange_rate_source': exchange_rate_source,  # For debugging/display
        }

    def _convert_payslip_values(self, payslips, target_currency):
        """Convert all payslip line amounts to target currency.

        Note: This modifies the in-memory values only, not the database.
        Each payslip line total is converted using the exchange rate
        in effect on the payslip's end date.

        Args:
            payslips: hr.payslip recordset
            target_currency: res.currency record

        Returns:
            recordset: Same payslips with converted line amounts
        """
        usd = self.env.ref('base.USD')

        for payslip in payslips:
            # Get conversion date from payslip (use date_to as per user requirement)
            conversion_date = payslip.date_to or payslip.date_from

            # Convert each payslip line amount
            for line in payslip.line_ids:
                if line.total != 0:
                    line.total = self._convert_currency(
                        line.total, usd, target_currency, conversion_date
                    )

        return payslips

    def _convert_currency(self, amount, from_currency, to_currency, date_ref):
        """Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency (res.currency)
            to_currency: Target currency (res.currency)
            date_ref: Date for exchange rate lookup

        Returns:
            float: Converted amount
        """
        if from_currency == to_currency:
            return amount

        return from_currency._convert(
            from_amount=amount,
            to_currency=to_currency,
            company=self.env.company,
            date=date_ref
        )
