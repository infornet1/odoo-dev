# -*- coding: utf-8 -*-
"""
ARC Annual Withholding Certificate (Comprobante ARC)

Generates SENIAT-style annual ISLR withholding certificate per employee.
Covers Jan-Dec of the selected fiscal year.
Missing payslip periods are simulated using contract rates and historical
BCV exchange rates.
"""

import base64
import calendar
import os
from datetime import date, timedelta

VET_OFFSET = timedelta(hours=-4)  # Venezuela Time = UTC−4

from odoo import api, models

MONTH_NAMES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

# V2 rule codes (preferred) with V1 fallback where applicable
SALARY_CODES = ['VE_SALARY_V2', 'VE_SALARY']
EXTRABONUS_CODES = ['VE_EXTRABONUS_V2', 'VE_EXTRABONUS']
BONUS_CODES = ['VE_BONUS_V2', 'VE_BONUS']
SSO_CODES = ['VE_SSO_DED_V2', 'VE_SSO_DED']
FAOV_CODES = ['VE_FAOV_DED_V2', 'VE_FAOV_DED']
PARO_CODES = ['VE_PARO_DED_V2', 'VE_INCES_DED_V2', 'VE_PARO_DED']
ARI_CODES = ['VE_ARI_DED_V2', 'VE_ARI_DED', 'VE_ISLR_DED']

# Liquidation structures to exclude from monthly income sums
LIQUIDATION_CODES = ['LIQUID_VE', 'LIQUID_VE_V2']


class ArcAnnualReport(models.AbstractModel):
    """AbstractModel report for the ARC annual withholding certificate."""

    _name = 'report.ueipab_payroll_enhancements.arc_annual_report'
    _description = 'ARC Annual Withholding Certificate'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        employee_ids = data.get('employee_ids') or docids or []
        year = data.get('year') or (date.today().year - 1)

        employees = self.env['hr.employee'].browse(employee_ids)

        # Pre-fetch acknowledgment certificates for these employees + year
        certs = self.env['arc.employee.certificate'].sudo().search([
            ('employee_id', 'in', list(employee_ids)),
            ('year', '=', str(year)),
        ])
        cert_map = {c.employee_id.id: c for c in certs}

        reports = []
        for employee in employees:
            report = self._compute_employee_arc(employee, year)
            cert = cert_map.get(employee.id)
            if cert and cert.is_acknowledged:
                ack_date_vet = (cert.acknowledged_date + VET_OFFSET) if cert.acknowledged_date else None
                report['ack_info'] = {
                    'is_acknowledged': True,
                    'acknowledged_date': ack_date_vet,
                    'acknowledged_ip': cert.acknowledged_ip or '',
                    'acknowledged_user_agent': cert.acknowledged_user_agent or '',
                }
            else:
                report['ack_info'] = {'is_acknowledged': False}
            reports.append(report)

        # Embed employer signature image as base64 data URI so wkhtmltopdf
        # doesn't need an outbound HTTP request (avoids failures in Docker).
        signature_src = ''
        try:
            img_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'static', 'img', 'firma_sello_gp.jpg',
            )
            with open(img_path, 'rb') as fh:
                signature_src = 'data:image/jpeg;base64,' + base64.b64encode(fh.read()).decode()
        except Exception:
            pass

        company = self.env.company
        company_logo_src = ''
        if company.logo:
            company_logo_src = 'data:image/png;base64,' + company.logo.decode('utf-8')

        return {
            'doc_ids': employee_ids,
            'doc_model': 'hr.employee',
            'docs': employees,
            'data': data,
            'reports': reports,
            'year': year,
            'company': company,
            'signature_src': signature_src,
            'company_logo_src': company_logo_src,
        }

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute_employee_arc(self, employee, year):
        """Build the full ARC data dict for one employee and one fiscal year.

        Per Decreto 1808 (SENIAT):
        - No minimum months — ARC required for any compensation received during the year.
        - Mid-year hires: only months from contract.date_start onward are included.
        - Ended contracts: only months up to contract.date_end are included.
        - 0% ARI employees: still included (shows Bs. 0 withheld).
        """
        veb = self.env['res.currency'].search([('name', '=', 'VEB')], limit=1)

        # Most recent contract active during the requested year
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['open', 'close']),
            ('date_start', '<=', '%s-12-31' % year),
        ], limit=1, order='date_start desc')

        # Determine effective window within the fiscal year
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        today = date.today()

        if contract:
            effective_start = max(year_start, contract.date_start)
            # date_end is None when contract is still open
            contract_end = contract.date_end or year_end
            effective_end = min(year_end, contract_end, today)
        else:
            effective_start = year_start
            effective_end = min(year_end, today)

        months_data = []
        has_estimates = False

        for month_num in range(1, 13):
            month_first = date(year, month_num, 1)
            month_last = date(year, month_num, calendar.monthrange(year, month_num)[1])

            # Skip months entirely outside the employee's active window
            if month_last < effective_start or month_first > effective_end:
                months_data.append(self._empty_month(month_num))
                continue

            # Find confirmed regular payslips in this month (exclude liquidations)
            payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '>=', month_first.strftime('%Y-%m-%d')),
                ('date_from', '<=', month_last.strftime('%Y-%m-%d')),
                ('state', '=', 'done'),
                ('struct_id.code', 'not in', LIQUIDATION_CODES),
            ])

            historical_rate = self._get_exchange_rate(month_first, veb)

            if payslips:
                row = self._row_from_payslips(payslips, historical_rate)
            elif contract:
                row = self._row_simulated(contract, month_first, historical_rate)
                has_estimates = True
            else:
                months_data.append(self._empty_month(month_num))
                continue

            row['month_num'] = month_num
            row['month_name'] = MONTH_NAMES_ES[month_num]
            months_data.append(row)

        totals = {
            'gross_ves': sum(m.get('gross_ves', 0.0) for m in months_data),
            'sso_ves': sum(m.get('sso_ves', 0.0) for m in months_data),
            'faov_ves': sum(m.get('faov_ves', 0.0) for m in months_data),
            'paro_ves': sum(m.get('paro_ves', 0.0) for m in months_data),
            'net_taxable_ves': sum(m.get('net_taxable_ves', 0.0) for m in months_data),
            'ari_ves': sum(m.get('ari_ves', 0.0) for m in months_data),
        }

        return {
            'employee': employee,
            'contract': contract,
            'year': year,
            'months': months_data,
            'totals': totals,
            'has_estimates': has_estimates,
            'company': self.env.company,
        }

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    def _row_from_payslips(self, payslips, historical_rate):
        """Build a month row from real confirmed payslip data."""
        # Determine exchange rate: prefer batch rate, fallback to historical
        rate = historical_rate
        for p in payslips:
            if p.payslip_run_id and p.payslip_run_id.exchange_rate:
                rate = p.payslip_run_id.exchange_rate
                break

        def total_usd(codes):
            return sum(self._get_lines_total(p, codes) for p in payslips)

        salary_usd = total_usd(SALARY_CODES)
        extrabonus_usd = total_usd(EXTRABONUS_CODES)
        bonus_usd = total_usd(BONUS_CODES)
        sso_usd = abs(total_usd(SSO_CODES))
        faov_usd = abs(total_usd(FAOV_CODES))
        paro_usd = abs(total_usd(PARO_CODES))
        ari_usd = abs(total_usd(ARI_CODES))

        gross_ves = (salary_usd + extrabonus_usd + bonus_usd) * rate
        sso_ves = sso_usd * rate
        faov_ves = faov_usd * rate
        paro_ves = paro_usd * rate
        ari_ves = ari_usd * rate
        net_taxable_ves = gross_ves - sso_ves - faov_ves - paro_ves

        return {
            'gross_ves': gross_ves,
            'sso_ves': sso_ves,
            'faov_ves': faov_ves,
            'paro_ves': paro_ves,
            'net_taxable_ves': net_taxable_ves,
            'ari_ves': ari_ves,
            'exchange_rate': rate,
            'is_estimated': False,
            'is_empty': False,
        }

    def _row_simulated(self, contract, month_first, rate):
        """Simulate a month row using contract rates and historical BCV rate."""
        salary_usd = contract.ueipab_salary_v2 or 0.0
        extrabonus_usd = getattr(contract, 'ueipab_extrabonus_v2', 0.0) or 0.0
        bonus_usd = getattr(contract, 'ueipab_bonus_v2', 0.0) or 0.0
        ari_pct = (getattr(contract, 'ueipab_ari_withholding_rate', 0.0) or 0.0) / 100.0

        gross_ves = (salary_usd + extrabonus_usd + bonus_usd) * rate
        salary_ves = salary_usd * rate

        # SSO 4%, FAOV 1%, PARO 0.5% — applied on taxable salary VES
        sso_ves = salary_ves * 0.04
        faov_ves = salary_ves * 0.01
        paro_ves = salary_ves * 0.005
        net_taxable_ves = gross_ves - sso_ves - faov_ves - paro_ves
        ari_ves = salary_ves * ari_pct

        return {
            'gross_ves': gross_ves,
            'sso_ves': sso_ves,
            'faov_ves': faov_ves,
            'paro_ves': paro_ves,
            'net_taxable_ves': net_taxable_ves,
            'ari_ves': ari_ves,
            'exchange_rate': rate,
            'is_estimated': True,
            'is_empty': False,
        }

    def _empty_month(self, month_num):
        return {
            'month_num': month_num,
            'month_name': MONTH_NAMES_ES[month_num],
            'gross_ves': 0.0,
            'sso_ves': 0.0,
            'faov_ves': 0.0,
            'paro_ves': 0.0,
            'net_taxable_ves': 0.0,
            'ari_ves': 0.0,
            'exchange_rate': 0.0,
            'is_estimated': False,
            'is_empty': True,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_lines_total(self, payslip, codes):
        """Sum totals for the first matching rule code in the payslip lines."""
        for code in codes:
            lines = payslip.line_ids.filtered(lambda l, c=code: l.code == c)
            if lines:
                return sum(l.total for l in lines)
        return 0.0

    def _get_exchange_rate(self, ref_date, veb_currency):
        """Return VES/USD rate for the closest date <= ref_date, or earliest available."""
        if not veb_currency:
            return 1.0

        rate_rec = self.env['res.currency.rate'].search([
            ('currency_id', '=', veb_currency.id),
            ('name', '<=', ref_date),
        ], limit=1, order='name desc')

        if not rate_rec:
            rate_rec = self.env['res.currency.rate'].search([
                ('currency_id', '=', veb_currency.id),
            ], limit=1, order='name asc')

        if rate_rec:
            if hasattr(rate_rec, 'company_rate') and rate_rec.company_rate:
                return rate_rec.company_rate
            if rate_rec.rate > 0:
                return 1.0 / rate_rec.rate

        return 1.0
