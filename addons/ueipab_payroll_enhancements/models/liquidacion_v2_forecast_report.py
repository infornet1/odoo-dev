# -*- coding: utf-8 -*-
"""Report model for Liquidación V2 Forecast PDF."""

from odoo import models, api
from .liquidacion_v2_forecast_wizard import compute_forecast_for_contract, _seniority_annual_rate


class LiquidacionV2ForecastReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.liq_v2_forecast'
    _description = 'Liquidación V2 Forecast Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard_id = (data or {}).get('wizard_id')
        wizard = self.env['liquidacion.v2.forecast.wizard'].browse(wizard_id)

        lines = []
        for line in wizard.forecast_line_ids.sorted(lambda l: l.employee_id.name):
            contract = line.contract_id
            as_of = wizard.as_of_date
            d = compute_forecast_for_contract(contract, as_of)

            lines.append({
                'employee': line.employee_id.name,
                'department': line.employee_id.department_id.name or '',
                'contract_start': line.contract_start,
                'original_hire': line.original_hire,
                'service_months': d['service_months'],
                'seniority_years': d['total_seniority_years'],
                'annual_rate': d['annual_rate'],
                'daily_salary': d['daily_salary'],
                'integral_daily': d['integral_daily'],
                # benefit lines
                'vacation_days': d['vacation_days'],
                'vacaciones': d['vacaciones'],
                'bonus_days': d['bonus_days'],
                'bono_vacacional': d['bono_vacacional'],
                'bono_vacacional_gross': d['bono_vacacional_gross'],
                'utilidades_days': d['utilidades_days'],
                'utilidades': d['utilidades'],
                'utilidades_gross': d['utilidades_gross'],
                'prestaciones_days': d['prestaciones_days'],
                'prestaciones': d['prestaciones'],
                'total_antig_months': d['total_antig_months'],
                'paid_antig_months': d['paid_antig_months'],
                'antiguedad_days': d['antiguedad_days'],
                'antiguedad': d['antiguedad'],
                'intereses': d['intereses'],
                # deductions
                'faov': d['faov'],
                'inces': d['inces'],
                'prepaid': d['prepaid'],
                # totals
                'net': d['net'],
                'net_veb': line.net_veb,
            })

        return {
            'wizard': wizard,
            'as_of_date': wizard.as_of_date,
            'exchange_rate': wizard.exchange_rate,
            'lines': lines,
            'total_net_usd': wizard.total_net_usd,
            'total_net_veb': wizard.total_net_veb,
            'employee_count': wizard.employee_count,
        }
