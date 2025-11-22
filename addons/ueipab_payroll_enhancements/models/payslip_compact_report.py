# -*- coding: utf-8 -*-
"""
Comprobante de Pago (Compact) Report Model

Generates single-page compact payslip with currency conversion support.
"""

from odoo import models, api, _
from datetime import date


class PayslipCompactReport(models.AbstractModel):
    """Report model for Comprobante de Pago (Compact)."""

    _name = 'report.ueipab_payroll_enhancements.report_payslip_compact'
    _description = 'Payslip Compact Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate compact payslip report data.

        Args:
            docids: List of hr.payslip IDs
            data: Data dict from wizard with currency and exchange rate options

        Returns:
            dict: Report data
        """
        # Get payslip IDs from data dict (matching Liquidación pattern)
        payslip_ids = data.get('payslip_ids', []) if data else []

        if not payslip_ids and docids:
            payslip_ids = docids

        payslips = self.env['hr.payslip'].browse(payslip_ids)

        # Get currency
        if data and data.get('currency_id'):
            currency = self.env['res.currency'].browse(data['currency_id'])
        else:
            currency = self.env.company.currency_id  # Default to USD

        # Get exchange rate options from data
        use_custom_rate = data.get('use_custom_rate', False) if data else False
        custom_exchange_rate = data.get('custom_exchange_rate', 0.0) if data else 0.0
        rate_date = None
        if data and data.get('rate_date'):
            if isinstance(data['rate_date'], str):
                rate_date = date.fromisoformat(data['rate_date'])
            else:
                rate_date = data['rate_date']

        # Generate report data for each payslip
        reports = []
        for payslip in payslips:
            # Get exchange rate
            exchange_rate, rate_source_date = self._get_exchange_rate(
                payslip,
                currency,
                use_custom_rate,
                custom_exchange_rate,
                rate_date
            )

            # Prepare report data
            report_data = self._prepare_report_data(
                payslip,
                currency,
                exchange_rate,
                rate_source_date,
                use_custom_rate,
                custom_exchange_rate
            )
            reports.append(report_data)

        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'currency': currency,
            'reports': reports,
        }

    def _get_exchange_rate(self, payslip, currency, use_custom, custom_rate, rate_date):
        """Get exchange rate for currency conversion.

        Args:
            payslip: hr.payslip record
            currency: res.currency record
            use_custom: Boolean, whether to use custom rate
            custom_rate: Float, custom exchange rate (VEB/USD)
            rate_date: Date, date for automatic rate lookup

        Returns:
            tuple: (exchange_rate, rate_source_date)
                - exchange_rate (float): The exchange rate value
                - rate_source_date (date): The date of the rate record (or None)
        """
        if currency.name == 'USD':
            return 1.0, None

        if currency.name == 'VEB':
            # PRIORITY 1: USE CUSTOM RATE IF PROVIDED
            if use_custom and custom_rate and custom_rate > 0:
                return custom_rate, None  # No source date for custom rate

            # PRIORITY 2: USE CUSTOM DATE IF PROVIDED
            if rate_date:
                lookup_date = rate_date
            else:
                # PRIORITY 3: USE LATEST AVAILABLE RATE
                lookup_date = None

            # Lookup rate
            if lookup_date:
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id),
                    ('name', '<=', lookup_date)
                ], limit=1, order='name desc')
            else:
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id)
                ], limit=1, order='name desc')

            if rate_record:
                rate_value = None
                if hasattr(rate_record, 'company_rate'):
                    rate_value = rate_record.company_rate
                elif rate_record.rate > 0:
                    rate_value = 1.0 / rate_record.rate

                if rate_value:
                    return rate_value, rate_record.name

        # Fallback
        return 1.0, None

    def _convert_amount(self, amount_usd, exchange_rate):
        """Convert USD amount to target currency.

        Args:
            amount_usd: Amount in USD
            exchange_rate: Conversion rate (VEB per USD)

        Returns:
            float: Converted amount
        """
        return amount_usd * exchange_rate

    def _format_amount(self, amount, currency):
        """Format amount with thousand separators and currency symbol.

        Args:
            amount: Amount to format
            currency: res.currency record

        Returns:
            str: Formatted amount (e.g., "$1,234.56" or "Bs. 44,566.78")
        """
        formatted = "{:,.2f}".format(abs(amount))

        if currency.name == 'USD':
            return f"${formatted}"
        else:
            return f"Bs. {formatted}"

    def _prepare_report_data(self, payslip, currency, exchange_rate, rate_source_date,
                            use_custom_rate, custom_rate):
        """Prepare all data for report template.

        Args:
            payslip: hr.payslip record
            currency: res.currency record
            exchange_rate: Exchange rate value
            rate_source_date: Date of rate record (or None)
            use_custom_rate: Boolean, whether custom rate is used
            custom_rate: Custom exchange rate value

        Returns:
            dict: Complete report data
        """
        contract = payslip.contract_id
        employee = payslip.employee_id

        # Format rate source text
        if currency.name != 'VEB':
            rate_source = None
        elif use_custom_rate and custom_rate:
            rate_source = "Tasa personalizada"
        elif rate_source_date:
            rate_source = f"Tasa del {rate_source_date.strftime('%d/%m/%Y')}"
        else:
            rate_source = "Tasa automática"

        # Exchange info
        exchange_info = {
            'currency': currency,
            'rate_value': exchange_rate,
            'rate_source': rate_source,
            'display_rate': currency.name == 'VEB'  # Only show for VEB
        }

        # Employee info
        employee_info = {
            'name': employee.name,
            'identification_id': employee.identification_id or '',
            'job': employee.job_id.name if employee.job_id else '',
            'department': employee.department_id.name if employee.department_id else '',
            'bank': employee.bank_account_id.acc_number if employee.bank_account_id else '',
            'date_start': contract.date_start.strftime('%d/%m/%Y') if contract.date_start else '',
            'period': f"{payslip.date_from.strftime('%d/%m/%Y')} - {payslip.date_to.strftime('%d/%m/%Y')}"
        }

        # Salary (convert)
        salary_usd = contract.wage
        salary_converted = self._convert_amount(salary_usd, exchange_rate)

        # Process earnings
        earnings = []
        earnings_total = 0.0
        earnings_categories = ['ALW', 'BASIC', 'GROSS', 'COMP']

        for line in payslip.line_ids.filtered(lambda l: l.category_id.code in earnings_categories and l.total > 0):
            amount_usd = line.total
            amount_converted = self._convert_amount(amount_usd, exchange_rate)

            earnings.append({
                'number': len(earnings) + 1,
                'name': line.name,
                'code': line.code,
                'quantity': line.quantity,
                'amount': amount_converted,
                'amount_formatted': self._format_amount(amount_converted, currency)
            })
            earnings_total += amount_converted

        # Process deductions
        deductions = []
        deductions_total = 0.0
        deduction_categories = ['DED', 'NET']

        for line in payslip.line_ids.filtered(lambda l: l.category_id.code in deduction_categories and l.total < 0):
            amount_usd = abs(line.total)
            amount_converted = self._convert_amount(amount_usd, exchange_rate)

            # Get rate percentage if available
            rate_text = f"{line.rate:.1f}%" if line.rate else ""

            deductions.append({
                'number': len(deductions) + 1,
                'name': line.name,
                'code': line.code,
                'rate': rate_text,
                'amount': amount_converted,
                'amount_formatted': self._format_amount(amount_converted, currency)
            })
            deductions_total += amount_converted

        # Calculate net
        net_pay = earnings_total - deductions_total

        return {
            'payslip': payslip,
            'employee': employee_info,
            'exchange': exchange_info,
            'salary': salary_converted,
            'salary_formatted': self._format_amount(salary_converted, currency),
            'earnings': earnings,
            'earnings_total': earnings_total,
            'earnings_total_formatted': self._format_amount(earnings_total, currency),
            'deductions': deductions,
            'deductions_total': deductions_total,
            'deductions_total_formatted': self._format_amount(deductions_total, currency),
            'net_pay': net_pay,
            'net_pay_formatted': self._format_amount(net_pay, currency),
            'currency': currency
        }
