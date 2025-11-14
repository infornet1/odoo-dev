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

        # Get key values from payslip
        prestaciones_total = self._get_line_value(payslip, 'LIQUID_PRESTACIONES')
        intereses_total = self._get_line_value(payslip, 'LIQUID_INTERESES')
        integral_daily = self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY')
        deduction_base = self._get_line_value(payslip, 'LIQUID_DAILY_SALARY')
        service_months = self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS')

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
        accumulated_prestaciones = 0.0
        accumulated_interest = 0.0
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

            # Update accumulated prestaciones
            accumulated_prestaciones += deposit_amount
            total_days_deposited += deposit_days

            # Monthly interest (proportional distribution)
            # Interest accrues on the balance, but we distribute total interest proportionally
            month_interest = interest_per_month if month_num > 0 else 0.0
            accumulated_interest += month_interest

            # Exchange rate placeholder (would need actual historical rates)
            exchange_rate = self._get_exchange_rate(current_date, currency)

            # Month name
            month_name = current_date.strftime("%b-%y")

            monthly_data.append({
                'month_name': month_name,
                'month_date': current_date,
                'monthly_income': monthly_income,
                'integral_salary': integral_daily,
                'deposit_days': deposit_days,
                'deposit_amount': deposit_amount,
                'advance': 0.0,  # Adelanto - usually 0
                'accumulated_prestaciones': accumulated_prestaciones,
                'exchange_rate': exchange_rate,
                'month_interest': month_interest,
                'interest_canceled': 0.0,  # Usually empty
                'accumulated_interest': accumulated_interest,
            })

            # Move to next month
            current_date = current_date + relativedelta(months=1)
            if current_date > end_date:
                break

        # Calculate totals
        totals = {
            'total_days': total_days_deposited,
            'total_prestaciones': accumulated_prestaciones,
            'total_interest': accumulated_interest,
            'total_advance': 0.0,
        }

        return {
            'monthly_data': monthly_data,
            'totals': totals,
        }

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
            float: Exchange rate or 1.0 for USD
        """
        # For USD, always return 1.0
        if currency.name == 'USD':
            return 1.0

        # For VEB, would need to query actual historical rates
        # Placeholder implementation - return 1.0 for now
        # TODO: Implement actual historical VEB rate lookup
        return 1.0
