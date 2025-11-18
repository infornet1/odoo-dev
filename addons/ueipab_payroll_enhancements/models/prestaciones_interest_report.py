# -*- coding: utf-8 -*-
"""
Prestaciones Sociales Interest Report Model

Generates month-by-month breakdown of prestaciones and interest calculations.
"""

from odoo import models, api, _
from dateutil.relativedelta import relativedelta
from datetime import date


class PrestacionesInterestReport(models.AbstractModel):
    """Report model for Prestaciones Sociales Interest breakdown."""

    _name = 'report.ueipab_payroll_enhancements.prestaciones_interest'
    _description = 'Prestaciones Interest Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate report data with monthly breakdown.

        Args:
            docids: List of hr.payslip IDs (usually None from wizard)
            data: Data dict from wizard containing payslip_ids

        Returns:
            dict: Report data
        """
        # Get payslip IDs from data dict (passed by wizard) - SAME AS WORKING REPORT
        payslip_ids = data.get('payslip_ids', []) if data else []

        # If no IDs in data, try to use docids parameter
        if not payslip_ids and docids:
            payslip_ids = docids

        # Build payslip recordset from IDs
        payslips = self.env['hr.payslip'].browse(payslip_ids)

        # Get currency
        currency_id = data.get('currency_id') if data else self.env.ref('base.USD').id
        currency = self.env['res.currency'].browse(currency_id)

        # Generate report data for each payslip
        reports = []
        for payslip in payslips:
            report_data = self._generate_monthly_breakdown(payslip, currency)
            reports.append({
                'payslip': payslip,
                'employee': payslip.employee_id,
                'contract': payslip.contract_id,
                'currency': currency,
                'monthly_data': report_data['monthly_data'],
                'totals': report_data['totals'],
            })

        return {
            'doc_ids': payslip_ids,  # Use the IDs we actually got from data
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,  # Pass through wizard data
            'currency': currency,
            'reports': reports,
        }

    def _generate_monthly_breakdown(self, payslip, currency):
        """Generate month-by-month breakdown for a payslip.

        Args:
            payslip: hr.payslip record
            currency: res.currency record

        Returns:
            dict: Monthly data and totals
        """
        contract = payslip.contract_id
        if not contract:
            return {'monthly_data': [], 'totals': {}}

        # Get USD currency (payslip amounts are always in USD)
        usd = self.env.ref('base.USD')

        # Get key values from payslip (all in USD)
        # Try V2 codes first, fall back to V1 for backward compatibility
        prestaciones_total = self._get_line_value(payslip, 'LIQUID_PRESTACIONES_V2') or self._get_line_value(payslip, 'LIQUID_PRESTACIONES')
        intereses_total = self._get_line_value(payslip, 'LIQUID_INTERESES_V2') or self._get_line_value(payslip, 'LIQUID_INTERESES')
        integral_daily = self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY_V2') or self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY')
        deduction_base = self._get_line_value(payslip, 'LIQUID_DAILY_SALARY_V2') or self._get_line_value(payslip, 'LIQUID_DAILY_SALARY')
        service_months = self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS_V2') or self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS')

        # Calculate monthly income (monthly salary)
        monthly_income = deduction_base * 30  # Daily to monthly

        # Date range
        start_date = contract.date_start
        end_date = payslip.date_to

        # Quarterly deposit amount (15 days per quarter)
        quarterly_deposit = integral_daily * 15

        # Generate month-by-month breakdown
        monthly_data = []
        current_date = start_date
        month_num = 0
        accumulated_prestaciones_usd = 0.0
        accumulated_interest_usd = 0.0
        accumulated_interest_veb = 0.0  # NEW: Properly accumulate VEB amounts
        total_days_deposited = 0

        # Interest distribution: proportional to months
        # Total interest needs to be distributed across all months
        months_count = int(service_months)
        if months_count > 0:
            interest_per_month = intereses_total / service_months
        else:
            interest_per_month = 0.0

        while current_date <= end_date:
            month_num += 1

            # Determine if this is a deposit month (every 3 months starting from month 3)
            is_deposit_month = (month_num >= 3 and (month_num - 3) % 3 == 0)

            deposit_days = 15 if is_deposit_month else 0
            deposit_amount = quarterly_deposit if is_deposit_month else 0.0

            # Update accumulated prestaciones (USD)
            accumulated_prestaciones_usd += deposit_amount
            total_days_deposited += deposit_days

            # Monthly interest (proportional distribution) in USD
            # Interest accrues on the balance, but we distribute total interest proportionally
            month_interest_usd = interest_per_month if month_num > 0 else 0.0
            accumulated_interest_usd += month_interest_usd

            # Get exchange rate for this month
            exchange_rate = self._get_exchange_rate(current_date, currency)

            # Month name
            month_name = current_date.strftime("%b-%y")

            # Convert all monetary values to selected currency
            monthly_income_converted = self._convert_currency(
                monthly_income, usd, currency, current_date
            )
            integral_daily_converted = self._convert_currency(
                integral_daily, usd, currency, current_date
            )
            deposit_amount_converted = self._convert_currency(
                deposit_amount, usd, currency, current_date
            )
            accumulated_prestaciones_converted = self._convert_currency(
                accumulated_prestaciones_usd, usd, currency, current_date
            )

            # CRITICAL FIX: Convert THIS month's interest at THIS month's rate, then accumulate VEB
            month_interest_converted = self._convert_currency(
                month_interest_usd, usd, currency, current_date
            )
            accumulated_interest_veb += month_interest_converted  # Accumulate VEB properly

            accumulated_interest_converted = accumulated_interest_veb  # Use properly accumulated VEB

            monthly_data.append({
                'month_name': month_name,
                'month_date': current_date,
                'monthly_income': monthly_income_converted,
                'integral_salary': integral_daily_converted,
                'deposit_days': deposit_days,
                'deposit_amount': deposit_amount_converted,
                'advance': 0.0,  # Adelanto - usually 0
                'accumulated_prestaciones': accumulated_prestaciones_converted,
                'exchange_rate': exchange_rate,
                'month_interest': month_interest_converted,
                'interest_canceled': 0.0,  # Usually empty
                'accumulated_interest': accumulated_interest_converted,
            })

            # Move to next month
            current_date = current_date + relativedelta(months=1)
            if current_date > end_date:
                break

        # Calculate totals
        # CRITICAL FIX: Use properly accumulated VEB amounts (already converted month-by-month)
        total_prestaciones_converted = self._convert_currency(
            accumulated_prestaciones_usd, usd, currency, end_date
        )
        total_interest_converted = accumulated_interest_veb  # Already accumulated in VEB

        totals = {
            'total_days': total_days_deposited,
            'total_prestaciones': total_prestaciones_converted,
            'total_interest': total_interest_converted,
            'total_advance': 0.0,
        }

        return {
            'monthly_data': monthly_data,
            'totals': totals,
        }

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

    def _get_line_value(self, payslip, code):
        """Get value from payslip line by code.

        Args:
            payslip: hr.payslip record
            code: Salary rule code

        Returns:
            float: Line amount or 0.0
        """
        line = payslip.line_ids.filtered(lambda l: l.code == code)
        return line.total if line else 0.0

    def _get_exchange_rate(self, date_ref, currency):
        """Get exchange rate for a specific date.

        Args:
            date_ref: Date for exchange rate
            currency: res.currency record

        Returns:
            float: Exchange rate (VEB/USD) for display, or 1.0 for USD

        Note:
            For dates before the earliest rate in database, returns the
            earliest available rate (matching Odoo's _convert() behavior)
        """
        # For USD, always return 1.0
        if currency.name == 'USD':
            return 1.0

        # For VEB, get actual historical rate
        if currency.name == 'VEB':
            # Try to get rate for the specific date (or latest before it)
            rate_record = self.env['res.currency.rate'].search([
                ('currency_id', '=', currency.id),
                ('name', '<=', date_ref)
            ], limit=1, order='name desc')

            # If no rate found for date, use earliest available rate
            # (matches Odoo's _convert() logic)
            if not rate_record:
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id)
                ], limit=1, order='name asc')

            if rate_record and hasattr(rate_record, 'company_rate'):
                # company_rate is VEB/USD (e.g., 231.09)
                return rate_record.company_rate
            elif rate_record and rate_record.rate > 0:
                # Fallback: calculate from rate field (1/rate gives VEB/USD)
                return 1.0 / rate_record.rate

        # Default fallback
        return 1.0
