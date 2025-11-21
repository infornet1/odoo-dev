# -*- coding: utf-8 -*-
"""
Relación de Liquidación Report Model

Generates detailed breakdown of liquidation calculations with formulas.
"""

from odoo import models, api, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class LiquidacionBreakdownReport(models.AbstractModel):
    """Report model for Relación de Liquidación breakdown."""

    _name = 'report.ueipab_payroll_enhancements.liquidacion_breakdown_report'
    _description = 'Liquidación Breakdown Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Generate report data with formula breakdowns.

        Args:
            docids: List of hr.payslip IDs
            data: Data dict from wizard

        Returns:
            dict: Report data
        """
        # Get payslip IDs from data dict
        payslip_ids = data.get('payslip_ids', []) if data else []

        if not payslip_ids and docids:
            payslip_ids = docids

        payslips = self.env['hr.payslip'].browse(payslip_ids)

        # Get currency
        currency_id = data.get('currency_id') if data else self.env.ref('base.USD').id
        currency = self.env['res.currency'].browse(currency_id)

        # Generate report data for each payslip
        reports = []
        for payslip in payslips:
            report_data = self._generate_breakdown(payslip, currency, data)
            reports.append(report_data)

        return {
            'doc_ids': payslip_ids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'data': data,
            'currency': currency,
            'reports': reports,
        }

    def _generate_breakdown(self, payslip, currency, data=None):
        """Generate complete breakdown for a payslip.

        Args:
            payslip: hr.payslip record
            currency: res.currency record
            data: Optional wizard data with custom rate/date

        Returns:
            dict: Breakdown data
        """
        contract = payslip.contract_id
        employee = payslip.employee_id

        # Get USD currency
        usd = self.env.ref('base.USD')

        # Detect if V1 or V2
        is_v2 = payslip.struct_id.code == 'LIQUID_VE_V2'

        # Get base data (try V2 first, fall back to V1)
        service_months = self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS_V2') or self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS')
        daily_salary = self._get_line_value(payslip, 'LIQUID_DAILY_SALARY_V2') or self._get_line_value(payslip, 'LIQUID_DAILY_SALARY')
        integral_daily = self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY_V2') or self._get_line_value(payslip, 'LIQUID_INTEGRAL_DAILY')

        # Calculate service period
        service_years = int(service_months / 12)
        remaining_months = int(service_months % 12)

        # Get original hire date for seniority calculation
        original_hire = contract.ueipab_original_hire_date if hasattr(contract, 'ueipab_original_hire_date') else contract.date_start
        total_seniority_years = 0.0
        bono_rate = 15.0

        if original_hire:
            total_days = (payslip.date_to - original_hire).days
            total_seniority_years = total_days / 365.0

            # Calculate progressive bono rate
            if total_seniority_years >= 16:
                bono_rate = 30.0
            elif total_seniority_years >= 1:
                bono_rate = min(15.0 + (total_seniority_years - 1), 30.0)

        # Get all benefit values
        vacaciones = self._get_line_value(payslip, 'LIQUID_VACACIONES_V2') or self._get_line_value(payslip, 'LIQUID_VACACIONES')
        bono_vacacional = self._get_line_value(payslip, 'LIQUID_BONO_VACACIONAL_V2') or self._get_line_value(payslip, 'LIQUID_BONO_VACACIONAL')
        utilidades = self._get_line_value(payslip, 'LIQUID_UTILIDADES_V2') or self._get_line_value(payslip, 'LIQUID_UTILIDADES')
        prestaciones = self._get_line_value(payslip, 'LIQUID_PRESTACIONES_V2') or self._get_line_value(payslip, 'LIQUID_PRESTACIONES')
        antiguedad = self._get_line_value(payslip, 'LIQUID_ANTIGUEDAD_V2') or self._get_line_value(payslip, 'LIQUID_ANTIGUEDAD')
        intereses = self._get_line_value(payslip, 'LIQUID_INTERESES_V2') or self._get_line_value(payslip, 'LIQUID_INTERESES')

        # Get deduction values
        faov = self._get_line_value(payslip, 'LIQUID_FAOV_V2') or self._get_line_value(payslip, 'LIQUID_FAOV')
        inces = self._get_line_value(payslip, 'LIQUID_INCES_V2') or self._get_line_value(payslip, 'LIQUID_INCES')
        prepaid = self._get_line_value(payslip, 'LIQUID_VACATION_PREPAID_V2') or self._get_line_value(payslip, 'LIQUID_VACATION_PREPAID')

        # Get net
        net = self._get_line_value(payslip, 'LIQUID_NET_V2') or self._get_line_value(payslip, 'LIQUID_NET')

        # Calculate days for each benefit (approximations for display)
        vacaciones_days = (service_months / 12.0) * 15.0
        bono_days = (service_months / 12.0) * bono_rate
        utilidades_days = (service_months / 12.0) * 30.0
        prestaciones_days = (service_months / 3.0) * 15.0

        # Calculate antiguedad days
        antiguedad_total_days = 0.0
        antiguedad_paid_days = 0.0
        antiguedad_net_days = 0.0

        if original_hire:
            total_months_seniority = (payslip.date_to - original_hire).days / 30.0
            antiguedad_total_days = total_months_seniority * 2.0

            # Check if previous liquidation exists
            if hasattr(contract, 'ueipab_previous_liquidation_date') and contract.ueipab_previous_liquidation_date:
                paid_days_period = (contract.ueipab_previous_liquidation_date - original_hire).days
                paid_months = paid_days_period / 30.0
                antiguedad_paid_days = paid_months * 2.0

            antiguedad_net_days = antiguedad_total_days - antiguedad_paid_days

        # Convert to selected currency
        date_ref = payslip.date_to

        # Get exchange rate parameters from wizard data
        custom_rate = data.get('custom_exchange_rate') if data else None
        custom_date_raw = data.get('rate_date') if data else None
        use_custom = data.get('use_custom_rate', False) if data else False

        # Convert custom_date from string to date object if needed
        custom_date = None
        if custom_date_raw:
            if isinstance(custom_date_raw, str):
                from datetime import datetime
                try:
                    custom_date = datetime.strptime(custom_date_raw, '%Y-%m-%d').date()
                except:
                    custom_date = None
            else:
                custom_date = custom_date_raw

        # Calculate exchange rate for display AND conversion
        exchange_rate = self._get_exchange_rate(date_ref, currency, custom_rate, custom_date)

        # Benefits
        vac_amt = self._convert_currency(vacaciones, usd, currency, date_ref, exchange_rate)
        bono_amt = self._convert_currency(bono_vacacional, usd, currency, date_ref, exchange_rate)
        util_amt = self._convert_currency(utilidades, usd, currency, date_ref, exchange_rate)
        prest_amt = self._convert_currency(prestaciones, usd, currency, date_ref, exchange_rate)
        antig_amt = self._convert_currency(antiguedad, usd, currency, date_ref, exchange_rate)

        # CRITICAL FIX: Use accrual-based calculation for interest (matches Prestaciones report)
        inter_amt = self._calculate_accrued_interest(payslip, currency, data)

        # Convert daily salaries for display in formulas
        daily_salary_display = self._convert_currency(daily_salary, usd, currency, date_ref, exchange_rate)
        integral_daily_display = self._convert_currency(integral_daily, usd, currency, date_ref, exchange_rate)
        prestaciones_display = self._convert_currency(prestaciones, usd, currency, date_ref, exchange_rate)

        # Currency symbol for display
        curr_symbol = currency.symbol

        benefits = [
            {
                'number': 1,
                'name': 'Vacaciones',
                'formula': '15 días por año × salario diario',
                'calculation': f'({service_months:.2f}/12) × 15 días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'detail': f'{vacaciones_days:.1f} días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'amount': vac_amt,
                'amount_formatted': self._format_amount(vac_amt),
            },
            {
                'number': 2,
                'name': 'Bono Vacacional',
                'formula': f'Tasa progresiva: {bono_rate:.1f} días/año ({total_seniority_years:.2f} años de antigüedad)',
                'calculation': f'({service_months:.2f}/12) × {bono_rate:.1f} días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'detail': f'{bono_days:.1f} días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'amount': bono_amt,
                'amount_formatted': self._format_amount(bono_amt),
            },
            {
                'number': 3,
                'name': 'Utilidades',
                'formula': '15 días por año × salario diario',
                'calculation': f'({service_months:.2f}/12) × 15 días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'detail': f'{utilidades_days:.1f} días × {curr_symbol}{self._format_amount(daily_salary_display)}',
                'amount': util_amt,
                'amount_formatted': self._format_amount(util_amt),
            },
            {
                'number': 4,
                'name': 'Prestaciones Sociales',
                'formula': '15 días por trimestre × salario integral',
                'calculation': f'({service_months:.2f}/3) × 15 días × {curr_symbol}{self._format_amount(integral_daily_display)}',
                'detail': f'{prestaciones_days:.1f} días × {curr_symbol}{self._format_amount(integral_daily_display)}',
                'amount': prest_amt,
                'amount_formatted': self._format_amount(prest_amt),
            },
            {
                'number': 5,
                'name': 'Antigüedad',
                'formula': '2 días por mes desde fecha original de ingreso',
                'calculation': f'Total: {antiguedad_total_days:.1f} días - Ya pagados: {antiguedad_paid_days:.1f} días',
                'detail': f'{antiguedad_net_days:.1f} días × {curr_symbol}{self._format_amount(integral_daily_display)}',
                'amount': antig_amt,
                'amount_formatted': self._format_amount(antig_amt),
            },
            {
                'number': 6,
                'name': 'Intereses sobre Prestaciones',
                'formula': '13% anual sobre saldo promedio de prestaciones',
                'calculation': f'Acumulación mensual ({int(service_months)} meses) - Ver reporte "Prestaciones Soc. Intereses"',
                'detail': 'Ver reporte "Prestaciones Soc. Intereses"',
                'amount': inter_amt,
                'amount_formatted': self._format_amount(inter_amt),
            },
        ]

        total_benefits = sum(b['amount'] for b in benefits)

        # Deductions
        deductions = []

        # Convert deduction base amounts for display
        vacaciones_display = self._convert_currency(vacaciones, usd, currency, date_ref, exchange_rate)
        bono_vacacional_display = self._convert_currency(bono_vacacional, usd, currency, date_ref, exchange_rate)
        utilidades_display = self._convert_currency(utilidades, usd, currency, date_ref, exchange_rate)

        if faov != 0:
            faov_amt = self._convert_currency(faov, usd, currency, date_ref, exchange_rate)
            deductions.append({
                'number': 1,
                'name': 'FAOV (Fondo de Ahorro Habitacional)',
                'formula': '1% sobre (Vacaciones + Bono Vacacional + Utilidades)',
                'calculation': f'({curr_symbol}{self._format_amount(vacaciones_display)} + {curr_symbol}{self._format_amount(bono_vacacional_display)} + {curr_symbol}{self._format_amount(utilidades_display)}) × 1%',
                'amount': faov_amt,
                'amount_formatted': self._format_amount(faov_amt),
            })

        if inces != 0:
            inces_amt = self._convert_currency(inces, usd, currency, date_ref, exchange_rate)
            deductions.append({
                'number': 2,
                'name': 'INCES',
                'formula': '0.5% sobre (Utilidades)',
                'calculation': f'({curr_symbol}{self._format_amount(utilidades_display)}) × 0.5%',
                'amount': inces_amt,
                'amount_formatted': self._format_amount(inces_amt),
            })

        if prepaid != 0:
            prepaid_amt = self._convert_currency(prepaid, usd, currency, date_ref, exchange_rate)
            prepaid_date = contract.ueipab_vacation_paid_until if hasattr(contract, 'ueipab_vacation_paid_until') and contract.ueipab_vacation_paid_until else None
            prepaid_detail = f'Período prepagado desde {prepaid_date.strftime("%d/%m/%Y")}' if prepaid_date else 'Deducción por pago adelantado'

            deductions.append({
                'number': 3,
                'name': 'Vacaciones y Bono Prepagadas',
                'formula': 'Deducción por pago adelantado',
                'calculation': prepaid_detail,
                'amount': prepaid_amt,
                'amount_formatted': self._format_amount(prepaid_amt),
            })

        total_deductions = sum(d['amount'] for d in deductions)
        net_amount = self._convert_currency(net, usd, currency, date_ref, exchange_rate)

        # Determine rate source for display
        if use_custom and custom_rate:
            rate_source = f'Personalizada - {date_ref.strftime("%d/%m/%Y")}'
        elif custom_date:
            rate_source = f'Tasa del {custom_date.strftime("%d/%m/%Y")}'
        else:
            rate_source = f'Automática ({date_ref.strftime("%d/%m/%Y")})'

        # Get salary V2 from contract and convert to selected currency
        salary_v2 = contract.ueipab_salary_v2 if hasattr(contract, 'ueipab_salary_v2') else 0.0
        salary_v2_display = self._convert_currency(salary_v2, usd, currency, date_ref, exchange_rate)

        return {
            'payslip': payslip,
            'employee': employee,
            'contract': contract,
            'currency': currency,
            'exchange_rate': exchange_rate,
            'rate_source': rate_source,
            'is_v2': is_v2,
            'structure_name': payslip.struct_id.name,
            'service_years': service_years,
            'service_months': remaining_months,
            'service_months_total': service_months,
            'original_hire_date': original_hire,
            'original_hire_date_str': original_hire.strftime('%d/%m/%Y') if original_hire else '',
            'date_start_str': contract.date_start.strftime('%d/%m/%Y') if contract.date_start else '',
            'date_to_str': payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else '',
            'total_seniority_years': total_seniority_years,
            'bono_rate': bono_rate,
            'daily_salary': daily_salary,
            'daily_salary_formatted': self._format_amount(daily_salary),
            'monthly_salary_formatted': self._format_amount(daily_salary * 30),
            'integral_daily': integral_daily,
            'integral_daily_formatted': self._format_amount(integral_daily),
            'benefits': benefits,
            'deductions': deductions,
            'total_benefits': total_benefits,
            'total_benefits_formatted': self._format_amount(total_benefits),
            'total_deductions': total_deductions,
            'total_deductions_formatted': self._format_amount(abs(total_deductions)),
            'net_amount': net_amount,
            'net_amount_formatted': self._format_amount(net_amount),
            'salary_v2': salary_v2,
            'salary_v2_formatted': self._format_amount(salary_v2_display),
        }

    def _convert_currency(self, amount, from_currency, to_currency, date_ref, exchange_rate=None):
        """Convert amount from one currency to another.

        Args:
            amount: Amount to convert
            from_currency: Source currency (usually USD)
            to_currency: Target currency (USD or VEB)
            date_ref: Reference date for automatic lookup
            exchange_rate: Optional pre-calculated exchange rate (VEB/USD)

        Returns:
            float: Converted amount
        """
        if from_currency == to_currency:
            return amount

        # Use pre-calculated exchange rate if provided (for VEB)
        if exchange_rate and to_currency.name == 'VEB' and from_currency.name == 'USD':
            return amount * exchange_rate

        # Fall back to Odoo's automatic conversion
        return from_currency._convert(
            from_amount=amount,
            to_currency=to_currency,
            company=self.env.company,
            date=date_ref
        )

    def _get_line_value(self, payslip, code):
        """Get value from payslip line by code."""
        line = payslip.line_ids.filtered(lambda l: l.code == code)
        return line.total if line else 0.0

    def _format_amount(self, amount):
        """Format amount with thousand separators.

        Args:
            amount: Number to format

        Returns:
            str: Formatted amount with thousand separators (e.g., "1,234.56")
        """
        return '{:,.2f}'.format(amount)

    def _calculate_accrued_interest(self, payslip, currency, data=None):
        """Calculate interest using month-by-month accrual (matches Prestaciones report).

        Args:
            payslip: hr.payslip record
            currency: res.currency record
            data: Optional wizard data with custom rate/date

        Returns:
            float: Accrued interest amount in target currency
        """
        # Get USD currency
        usd = self.env.ref('base.USD')

        # If USD currency, just return the USD total
        if currency == usd:
            intereses_usd = self._get_line_value(payslip, 'LIQUID_INTERESES_V2') or \
                           self._get_line_value(payslip, 'LIQUID_INTERESES')
            return intereses_usd

        # Get exchange rate override params if provided
        custom_rate = data.get('custom_exchange_rate') if data else None
        custom_date_raw = data.get('rate_date') if data else None
        use_custom = data.get('use_custom_rate', False) if data else False

        # Convert custom_date from string to date object if needed
        custom_date = None
        if custom_date_raw:
            if isinstance(custom_date_raw, str):
                from datetime import datetime
                try:
                    custom_date = datetime.strptime(custom_date_raw, '%Y-%m-%d').date()
                except:
                    custom_date = None
            else:
                custom_date = custom_date_raw

        # Get payslip data
        service_months = self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS_V2') or \
                        self._get_line_value(payslip, 'LIQUID_SERVICE_MONTHS')
        intereses_total = self._get_line_value(payslip, 'LIQUID_INTERESES_V2') or \
                         self._get_line_value(payslip, 'LIQUID_INTERESES')

        if service_months <= 0:
            return 0.0

        # CRITICAL: Interest ALWAYS uses accrual-based calculation
        # Ignores exchange rate override to ensure consistency with Prestaciones report
        # Rationale: Interest accumulated over 23 months at historical rates
        contract = payslip.contract_id
        start_date = contract.date_start
        end_date = payslip.date_to

        interest_per_month = intereses_total / service_months

        # Accumulate VEB month-by-month using historical rates
        accumulated_veb = 0.0
        current_date = start_date

        while current_date <= end_date:
            # Always use current month's historical rate (no override)
            month_rate = self._get_exchange_rate(current_date, currency, None, None)
            month_interest_veb = interest_per_month * month_rate
            accumulated_veb += month_interest_veb

            current_date = current_date + relativedelta(months=1)
            if current_date > end_date:
                break

        return accumulated_veb

    def _get_exchange_rate(self, date_ref, currency, custom_rate=None, custom_date=None):
        """Get exchange rate for display.

        Args:
            date_ref: Reference date from payslip (payslip.date_to)
            currency: Target currency
            custom_rate: Optional custom rate override (VEB/USD)
            custom_date: Optional custom date for rate lookup

        Returns:
            float: Exchange rate (VEB/USD or 1.0 for USD)
        """
        if currency.name == 'USD':
            return 1.0

        if currency.name == 'VEB':
            # USE CUSTOM RATE IF PROVIDED
            if custom_rate and custom_rate > 0:
                return custom_rate

            # USE CUSTOM DATE IF PROVIDED, OTHERWISE USE date_ref
            lookup_date = custom_date if custom_date else date_ref

            rate_record = self.env['res.currency.rate'].search([
                ('currency_id', '=', currency.id),
                ('name', '<=', lookup_date)
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
