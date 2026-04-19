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
        """Generate report data with monthly breakdown."""
        payslip_ids = data.get('payslip_ids', []) if data else []
        if not payslip_ids and docids:
            payslip_ids = docids

        payslips = self.env['hr.payslip'].browse(payslip_ids)

        currency_id = data.get('currency_id') if data else self.env.ref('base.USD').id
        currency = self.env['res.currency'].browse(currency_id)

        # Wizard-supplied rate (used for interest amounts so total matches email template)
        wizard_rate = data.get('exchange_rate', 1.0) if data else 1.0
        exchange_rate_label = data.get('exchange_rate_label', '') if data else ''

        reports = []
        for payslip in payslips:
            report_data = self._generate_monthly_breakdown(payslip, currency, wizard_rate)
            report_data['exchange_rate'] = wizard_rate
            report_data['exchange_rate_label'] = exchange_rate_label
            reports.append(report_data)

        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'currency': currency,
            'reports': reports,
        }

    def _generate_monthly_breakdown(self, payslip, currency, wizard_rate=1.0):
        """Generate month-by-month breakdown for a payslip.

        wizard_rate: single VEB/USD rate from the wizard, used for interest
                     amounts so they are consistent with the email template net.
        """
        contract = payslip.contract_id
        if not contract:
            return {
                'payslip': payslip,
                'employee': payslip.employee_id,
                'contract': contract,
                'currency': currency,
                'monthly_data': [],
                'totals': {},
            }

        usd = self.env.ref('base.USD')

        prestaciones_total = self._get_line_value(payslip, 'LIQUID_PRESTACIONES_V2') or self._get_line_value(payslip, 'LIQUID_PRESTACIONES')
        intereses_total = self._get_line_value(payslip, 'LIQUID_INTERESES_V2') or self._get_line_value(payslip, 'LIQUID_INTERESES')
        integral_daily = self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY_V2') or self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY')
        deduction_base = self._get_line_value(payslip, 'LIQUID_DAILY_SALARY_V2') or self._get_line_value(payslip, 'LIQUID_DAILY_SALARY')
        service_months = self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS_V2') or self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS')

        monthly_income = deduction_base * 30

        start_date = contract.date_start
        end_date = payslip.date_to

        quarterly_deposit = integral_daily * 15

        monthly_data = []
        current_date = start_date
        month_num = 0
        accumulated_prestaciones_usd = 0.0
        accumulated_interest_converted = 0.0
        total_days_deposited = 0

        months_count = int(service_months)
        interest_per_month_usd = (intereses_total / service_months) if months_count > 0 else 0.0

        while current_date <= end_date:
            month_num += 1

            is_deposit_month = (month_num >= 3 and (month_num - 3) % 3 == 0)
            deposit_days = 15 if is_deposit_month else 0
            deposit_amount = quarterly_deposit if is_deposit_month else 0.0

            accumulated_prestaciones_usd += deposit_amount
            total_days_deposited += deposit_days

            # Historical rate for display in "Tasa del Mes" column (informational only)
            historical_rate = self._get_historical_exchange_rate(current_date, currency)

            # Interest amount: use wizard rate for consistency with email template
            month_interest_converted = interest_per_month_usd * wizard_rate
            accumulated_interest_converted += month_interest_converted

            monthly_income_converted = self._convert_currency(monthly_income, usd, currency, current_date)
            integral_daily_converted = self._convert_currency(integral_daily, usd, currency, current_date)
            deposit_amount_converted = self._convert_currency(deposit_amount, usd, currency, current_date)
            accumulated_prestaciones_converted = self._convert_currency(accumulated_prestaciones_usd, usd, currency, current_date)

            monthly_data.append({
                'month_name': current_date.strftime("%b-%y"),
                'month_date': current_date,
                'monthly_income': monthly_income_converted,
                'integral_salary': integral_daily_converted,
                'deposit_days': deposit_days,
                'deposit_amount': deposit_amount_converted,
                'advance': 0.0,
                'accumulated_prestaciones': accumulated_prestaciones_converted,
                'exchange_rate': historical_rate,  # display only
                'month_interest': month_interest_converted,
                'interest_canceled': 0.0,
                'accumulated_interest': accumulated_interest_converted,
            })

            current_date = current_date + relativedelta(months=1)
            if current_date > end_date:
                break

        total_prestaciones_converted = self._convert_currency(accumulated_prestaciones_usd, usd, currency, end_date)
        # Total interest = intereses_total_usd × wizard_rate (matches email template)
        total_interest_converted = intereses_total * wizard_rate if currency.name == 'VEB' else intereses_total

        # Reconcile last row: int(service_months) drops the fractional month, leaving a
        # remainder in the running total. Assign the correct final total to the last row
        # so the accumulated column reaches the same figure as the footer total.
        if monthly_data:
            monthly_data[-1]['accumulated_interest'] = total_interest_converted

        totals = {
            'total_days': total_days_deposited,
            'total_prestaciones': total_prestaciones_converted,
            'total_interest': total_interest_converted,
            'total_advance': 0.0,
        }

        return {
            'payslip': payslip,
            'employee': payslip.employee_id,
            'contract': contract,
            'currency': currency,
            'monthly_data': monthly_data,
            'totals': totals,
        }

    def _convert_currency(self, amount, from_currency, to_currency, date_ref):
        if from_currency == to_currency:
            return amount
        return from_currency._convert(
            from_amount=amount,
            to_currency=to_currency,
            company=self.env.company,
            date=date_ref
        )

    def _get_line_value(self, payslip, code):
        line = payslip.line_ids.filtered(lambda l: l.code == code)
        return line.total if line else 0.0

    def _get_historical_exchange_rate(self, date_ref, currency):
        """Return historical BCV rate for a date (used for display in Tasa del Mes column)."""
        if currency.name == 'USD':
            return 1.0
        if currency.name == 'VEB':
            rate_record = self.env['res.currency.rate'].search([
                ('currency_id', '=', currency.id),
                ('name', '<=', date_ref)
            ], limit=1, order='name desc')
            if not rate_record:
                rate_record = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id)
                ], limit=1, order='name asc')
            if rate_record and hasattr(rate_record, 'company_rate'):
                return rate_record.company_rate
            elif rate_record and rate_record.rate > 0:
                return 1.0 / rate_record.rate
        return 1.0
