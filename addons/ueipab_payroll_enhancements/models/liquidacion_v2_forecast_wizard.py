# -*- coding: utf-8 -*-
"""
Liquidación V2 Forecast Wizard

Estimates future liquidation costs for ALL active employees with a
LIQUID_VE_V2 contract, projected to a user-specified as-of date.
No payslips are required — formulas are computed directly from contracts.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
import base64
from io import BytesIO
import xlsxwriter


# ─── helpers shared with the report model ────────────────────────────────────

def _seniority_annual_rate(total_seniority_years):
    """Return progressive annual rate (days/year) for Vacaciones & Bono Vac."""
    if total_seniority_years >= 16:
        return 30.0
    elif total_seniority_years >= 1:
        return min(15.0 + (total_seniority_years - 1), 30.0)
    return 15.0


def compute_forecast_for_contract(contract, as_of_date):
    """
    Replicate all LIQUID_VE_V2 salary rule formulas in plain Python.

    Returns a dict with all line amounts (in USD, same unit as contract salary).
    Negative values = deductions.
    """
    d = as_of_date

    # ── base dates ───────────────────────────────────────────────────────────
    contract_start = contract.date_start
    original_hire = (
        contract.ueipab_original_hire_date
        if contract.ueipab_original_hire_date
        else contract_start
    )
    previous_liquidation = contract.ueipab_previous_liquidation_date or False

    # ── service months (from contract start, not original hire) ──────────────
    service_months = (d - contract_start).days / 30.0

    # ── daily salary base ────────────────────────────────────────────────────
    base_salary = contract.ueipab_salary_v2 or 0.0
    daily_salary = base_salary / 30.0

    # ── integral daily salary ────────────────────────────────────────────────
    util_daily = daily_salary * (60.0 / 360.0)
    bono_daily = daily_salary * (15.0 / 360.0)
    integral_daily = daily_salary + util_daily + bono_daily

    # ── seniority from original hire date ───────────────────────────────────
    total_seniority_days = (d - original_hire).days
    total_seniority_years = total_seniority_days / 365.0
    annual_rate = _seniority_annual_rate(total_seniority_years)

    # ── LIQUID_VACACIONES_V2 ─────────────────────────────────────────────────
    vacation_days = (service_months / 12.0) * annual_rate
    vacaciones = vacation_days * daily_salary

    # ── LIQUID_BONO_VACACIONAL_V2 — excluded from forecast (always pre-paid) ──
    bonus_days = (service_months / 12.0) * annual_rate
    bono_vacacional_gross = bonus_days * daily_salary
    bono_vacacional = 0.0  # pre-paid: not owed at liquidation time

    # ── LIQUID_UTILIDADES_V2 — excluded from forecast (always pre-paid) ──────
    if service_months < 12:
        utilidades_days = (service_months / 12.0) * 15.0
    else:
        utilidades_days = 15.0
    utilidades_gross = utilidades_days * daily_salary
    utilidades = 0.0  # pre-paid: not owed at liquidation time

    # ── LIQUID_PRESTACIONES_V2 (15 days/quarter integral) ───────────────────
    quarters = service_months / 3.0
    prestaciones_days = quarters * 15.0
    prestaciones = prestaciones_days * integral_daily

    # ── LIQUID_INTERESES_V2 (13% annual on average prestaciones balance) ────
    average_balance = prestaciones * 0.5
    intereses = average_balance * 0.13 * (service_months / 12.0)

    # ── LIQUID_ANTIGUEDAD_V2 ─────────────────────────────────────────────────
    if service_months < 1.03:
        antiguedad = 0.0
        antiguedad_days = 0.0
        total_antig_months = 0.0
        paid_antig_months = 0.0
    else:
        total_antig_months = (d - original_hire).days / 30.0

        if previous_liquidation and previous_liquidation > original_hire:
            paid_days = (previous_liquidation - original_hire).days
            paid_antig_months = paid_days / 30.0
            net_months = total_antig_months - paid_antig_months
            antiguedad_days = net_months * 2 if net_months > 0 else 0.0
        else:
            paid_antig_months = 0.0
            antiguedad_days = total_antig_months * 2

        antiguedad = antiguedad_days * integral_daily

    # ── deductions — FAOV only on vacaciones (bono+util excluded as pre-paid)
    faov = -1 * vacaciones * 0.01
    inces = 0.0  # 0.5% of utilidades — zero since utilidades excluded

    prepaid_amount = contract.ueipab_vacation_prepaid_amount or 0.0
    prepaid = -1 * prepaid_amount if prepaid_amount > 0 else 0.0

    # ── NET ──────────────────────────────────────────────────────────────────
    net = (
        vacaciones + bono_vacacional + utilidades
        + prestaciones + antiguedad + intereses
        + faov + inces + prepaid
    )

    return {
        'service_months': service_months,
        'daily_salary': daily_salary,
        'integral_daily': integral_daily,
        'total_seniority_years': total_seniority_years,
        'annual_rate': annual_rate,
        # benefits
        'vacation_days': vacation_days,
        'vacaciones': vacaciones,
        'bonus_days': bonus_days,
        'bono_vacacional': bono_vacacional,         # always 0 in forecast
        'bono_vacacional_gross': bono_vacacional_gross,  # reference amount
        'utilidades_days': utilidades_days,
        'utilidades': utilidades,                   # always 0 in forecast
        'utilidades_gross': utilidades_gross,            # reference amount
        'prestaciones_days': prestaciones_days,
        'prestaciones': prestaciones,
        'intereses': intereses,
        # antiguedad detail
        'total_antig_months': total_antig_months if service_months >= 1.03 else 0.0,
        'paid_antig_months': paid_antig_months if service_months >= 1.03 else 0.0,
        'antiguedad_days': antiguedad_days if service_months >= 1.03 else 0.0,
        'antiguedad': antiguedad,
        # deductions
        'faov': faov,
        'inces': inces,
        'prepaid': prepaid,
        # total
        'net': net,
    }


# ─── TransientModel: one line per employee ───────────────────────────────────

class LiquidacionV2ForecastLine(models.TransientModel):
    _name = 'liquidacion.v2.forecast.line'
    _description = 'Línea de Pronóstico Liquidación V2'
    _order = 'net desc'

    wizard_id = fields.Many2one('liquidacion.v2.forecast.wizard', required=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Departamento', readonly=True)
    contract_id = fields.Many2one('hr.contract', string='Contrato', readonly=True)
    contract_start = fields.Date(string='Inicio Contrato', readonly=True)
    original_hire = fields.Date(string='Ingreso Original', readonly=True)

    service_months = fields.Float(string='Meses Servicio', digits=(8, 2), readonly=True)
    seniority_years = fields.Float(string='Antigüedad (años)', digits=(8, 2), readonly=True)
    daily_salary = fields.Float(string='Salario Diario', digits=(12, 4), readonly=True)
    integral_daily = fields.Float(string='Salario Integral', digits=(12, 4), readonly=True)

    vacaciones = fields.Float(string='Vacaciones', digits=(12, 2), readonly=True)
    bono_vacacional = fields.Float(string='Bono Vac.', digits=(12, 2), readonly=True)
    utilidades = fields.Float(string='Utilidades', digits=(12, 2), readonly=True)
    prestaciones = fields.Float(string='Prestaciones', digits=(12, 2), readonly=True)
    antiguedad = fields.Float(string='Antigüedad', digits=(12, 2), readonly=True)
    intereses = fields.Float(string='Intereses', digits=(12, 2), readonly=True)
    faov = fields.Float(string='FAOV', digits=(12, 2), readonly=True)
    inces = fields.Float(string='INCES', digits=(12, 2), readonly=True)
    prepaid = fields.Float(string='Adelanto Vac.', digits=(12, 2), readonly=True)
    net = fields.Float(string='NETO USD', digits=(12, 2), readonly=True)
    net_veb = fields.Float(string='NETO VEB', digits=(16, 2), readonly=True)


# ─── TransientModel: main wizard ─────────────────────────────────────────────

class LiquidacionV2ForecastWizard(models.TransientModel):
    _name = 'liquidacion.v2.forecast.wizard'
    _description = 'Pronóstico Liquidación V2 por Empleado'

    as_of_date = fields.Date(
        string='Proyectar al',
        required=True,
        default=lambda self: date(2026, 7, 31),
        help='Fecha hipotética de liquidación. Las fórmulas calculan antigüedad y prestaciones hasta esta fecha.',
    )

    exchange_rate = fields.Float(
        string='Tasa VEB/USD',
        digits=(12, 4),
        default=0.0,
        help='Tasa de cambio BCV. Déjela en 0 para usar la última tasa disponible en Odoo.',
    )

    forecast_line_ids = fields.One2many(
        'liquidacion.v2.forecast.line',
        'wizard_id',
        string='Pronóstico por Empleado',
        readonly=True,
    )

    total_net_usd = fields.Float(string='Total Neto USD', digits=(14, 2), readonly=True)
    total_net_veb = fields.Float(string='Total Neto VEB', digits=(18, 2), readonly=True)
    employee_count = fields.Integer(string='Empleados', readonly=True)
    computed = fields.Boolean(default=False)

    excel_file = fields.Binary(string='Excel', readonly=True, attachment=False)
    excel_filename = fields.Char(readonly=True)

    # ── exchange rate helpers ─────────────────────────────────────────────────

    def _get_effective_rate(self):
        """Return the VEB/USD exchange rate (how many VEB = 1 USD)."""
        if self.exchange_rate and self.exchange_rate > 0:
            return self.exchange_rate
        veb = self.env['res.currency'].search([('name', '=', 'VEB')], limit=1)
        if not veb:
            return 1.0
        rate_rec = self.env['res.currency.rate'].search(
            [('currency_id', '=', veb.id)],
            order='name desc',
            limit=1,
        )
        if rate_rec and rate_rec.company_rate:
            return rate_rec.company_rate
        return 1.0

    # ── main compute action ───────────────────────────────────────────────────

    def action_compute(self):
        """Find all active V2 contracts for employees tagged 'Empleado'."""
        as_of = self.as_of_date

        # Delete existing lines
        self.forecast_line_ids.unlink()

        rate = self._get_effective_rate()

        # Resolve the "Empleado" tag from res.partner.category (contact-level tag)
        empleado_tag = self.env['res.partner.category'].search(
            [('name', '=', 'Empleado')], limit=1
        )

        # Build contract domain: open + employee linked to a partner with the tag
        domain = [('state', '=', 'open')]
        if empleado_tag:
            # Query partner IDs with the tag via SQL (category_ids not ORM-searchable here)
            self.env.cr.execute(
                "SELECT partner_id FROM res_partner_res_partner_category_rel WHERE category_id = %s",
                (empleado_tag.id,)
            )
            tagged_partner_ids = [r[0] for r in self.env.cr.fetchall()]

            # Emails of tagged partners (to catch employees without an Odoo user)
            self.env.cr.execute(
                "SELECT email FROM res_partner WHERE id = ANY(%s) AND email IS NOT NULL",
                (tagged_partner_ids,)
            )
            tagged_emails = [r[0] for r in self.env.cr.fetchall()]

            # User IDs whose partner has the tag
            tagged_user_ids = self.env['res.users'].search(
                [('partner_id', 'in', tagged_partner_ids)]
            ).ids

            # Match employees via user account OR work email
            domain += [
                '|',
                ('employee_id.user_id', 'in', tagged_user_ids),
                ('employee_id.work_email', 'in', tagged_emails),
            ]

        contracts = self.env['hr.contract'].search(domain)

        # Filter further to V2 (ueipab_salary_v2 > 0 and LIQUID_VE_V2 exists)
        v2_contracts = contracts.filtered(
            lambda c: c.employee_id and _has_liquid_v2(self.env, c)
        )

        lines_vals = []
        total_net_usd = 0.0
        total_net_veb = 0.0

        for contract in v2_contracts.sorted(lambda c: c.employee_id.name):
            try:
                data = compute_forecast_for_contract(contract, as_of)
            except Exception:
                continue

            net_usd = data['net']
            net_veb = net_usd * rate
            total_net_usd += net_usd
            total_net_veb += net_veb

            lines_vals.append({
                'wizard_id': self.id,
                'employee_id': contract.employee_id.id,
                'contract_id': contract.id,
                'contract_start': contract.date_start,
                'original_hire': (
                    contract.ueipab_original_hire_date
                    or contract.date_start
                ),
                'service_months': data['service_months'],
                'seniority_years': data['total_seniority_years'],
                'daily_salary': data['daily_salary'],
                'integral_daily': data['integral_daily'],
                'vacaciones': data['vacaciones'],
                'bono_vacacional': data['bono_vacacional'],
                'utilidades': data['utilidades'],
                'prestaciones': data['prestaciones'],
                'antiguedad': data['antiguedad'],
                'intereses': data['intereses'],
                'faov': data['faov'],
                'inces': data['inces'],
                'prepaid': data['prepaid'],
                'net': net_usd,
                'net_veb': net_veb,
            })

        self.env['liquidacion.v2.forecast.line'].create(lines_vals)
        self.write({
            'total_net_usd': total_net_usd,
            'total_net_veb': total_net_veb,
            'employee_count': len(lines_vals),
            'computed': True,
            'exchange_rate': rate,
        })

        # Re-open same wizard so the user sees the computed lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'liquidacion.v2.forecast.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_pdf(self):
        """Generate PDF report from computed lines."""
        if not self.forecast_line_ids:
            raise UserError(_('Primero calcule el pronóstico con el botón "Calcular".'))
        return self.env.ref(
            'ueipab_payroll_enhancements.action_liquidacion_v2_forecast_report'
        ).report_action(self, data={'wizard_id': self.id})

    def action_export_excel(self):
        """Generate Excel (.xlsx) with one row per employee, all rule columns."""
        if not self.forecast_line_ids:
            raise UserError(_('Primero calcule el pronóstico con el botón "Calcular".'))

        output = BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Pronóstico Liq V2')

        # ── formats ──────────────────────────────────────────────────────────
        navy = '#1a2c5b'
        fmt_title = wb.add_format({
            'bold': True, 'font_size': 13, 'color': navy,
            'align': 'center', 'valign': 'vcenter',
        })
        fmt_header = wb.add_format({
            'bold': True, 'bg_color': navy, 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'font_size': 8,
        })
        fmt_ded_header = wb.add_format({
            'bold': True, 'bg_color': '#6b2131', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'font_size': 8,
        })
        fmt_net_header = wb.add_format({
            'bold': True, 'bg_color': '#145a2c', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'font_size': 8,
        })
        fmt_text = wb.add_format({'border': 1, 'font_size': 8, 'valign': 'vcenter'})
        fmt_num = wb.add_format({
            'border': 1, 'num_format': '#,##0.00', 'font_size': 8,
            'align': 'right', 'valign': 'vcenter',
        })
        fmt_num_green = wb.add_format({
            'border': 1, 'num_format': '#,##0.00', 'font_size': 8,
            'align': 'right', 'valign': 'vcenter',
            'bold': True, 'font_color': '#145a2c',
        })
        fmt_num_veb = wb.add_format({
            'border': 1, 'num_format': '#,##0', 'font_size': 8,
            'align': 'right', 'valign': 'vcenter', 'font_color': '#4a3a00',
        })
        fmt_total = wb.add_format({
            'bold': True, 'bg_color': '#1a2c5b', 'font_color': 'white',
            'border': 1, 'num_format': '#,##0.00', 'align': 'right',
            'font_size': 9,
        })
        fmt_total_veb = wb.add_format({
            'bold': True, 'bg_color': '#4a3a00', 'font_color': 'white',
            'border': 1, 'num_format': '#,##0', 'align': 'right',
            'font_size': 9,
        })
        fmt_sub = wb.add_format({
            'italic': True, 'font_size': 7, 'font_color': '#666666',
            'align': 'center',
        })

        # ── title rows ───────────────────────────────────────────────────────
        as_of_str = self.as_of_date.strftime('%d/%m/%Y') if self.as_of_date else ''
        ws.merge_range('A1:S1',
                       'PRONÓSTICO DE LIQUIDACIÓN V2 POR EMPLEADO', fmt_title)
        ws.merge_range('A2:S2',
                       'Proyectado al %s  |  Tasa VEB/USD: %.2f  |  %d empleados (tag "Empleado")' % (
                           as_of_str, self.exchange_rate, self.employee_count),
                       fmt_sub)

        # ── column headers ───────────────────────────────────────────────────
        fmt_pre_header = wb.add_format({
            'bold': True, 'bg_color': '#999999', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'font_size': 8,
        })
        fmt_pre = wb.add_format({
            'border': 1, 'num_format': '#,##0.00', 'font_size': 8,
            'align': 'right', 'valign': 'vcenter',
            'font_color': '#aaaaaa', 'bg_color': '#f5f5f5',
            'font_strikeout': True,
        })

        headers = [
            ('#',                fmt_header,     4),
            ('Empleado',         fmt_header,     28),
            ('Departamento',     fmt_header,     18),
            ('Inicio\nContrato', fmt_header,     11),
            ('Ingreso\nOriginal',fmt_header,     11),
            ('Meses\nServ.',     fmt_header,     8),
            ('Antig.\n(años)',   fmt_header,     8),
            ('Sal.\nDiario',     fmt_header,     10),
            # benefits in NET
            ('Vacaciones',       fmt_header,     12),
            ('Prestaciones',     fmt_header,     12),
            ('Antigüedad',       fmt_header,     12),
            ('Intereses',        fmt_header,     10),
            # pre-paid reference (greyed, not in NET)
            ('Bono Vac. ⓟ\n(pre-pagado)', fmt_pre_header, 13),
            ('Utilidades ⓟ\n(pre-pagado)', fmt_pre_header, 13),
            # deductions
            ('FAOV',             fmt_ded_header, 10),
            ('Adel.\nVac.',      fmt_ded_header, 10),
            # net
            ('NETO USD',         fmt_net_header, 12),
            ('NETO VEB',         fmt_net_header, 14),
        ]

        row = 2
        for col, (label, fmt, width) in enumerate(headers):
            ws.write(row, col, label, fmt)
            ws.set_column(col, col, width)
        ws.set_row(row, 30)

        # ── data rows ────────────────────────────────────────────────────────
        fmt_date = wb.add_format({
            'border': 1, 'num_format': 'dd/mm/yyyy', 'font_size': 8,
            'align': 'center', 'valign': 'vcenter',
        })

        row = 3
        for idx, line in enumerate(
            self.forecast_line_ids.sorted(lambda l: l.employee_id.name)
        ):
            ws.write(row, 0, idx + 1, fmt_text)
            ws.write(row, 1, line.employee_id.name, fmt_text)
            ws.write(row, 2, line.employee_id.department_id.name or '', fmt_text)
            ws.write_datetime(row, 3, line.contract_start, fmt_date) if line.contract_start else ws.write(row, 3, '', fmt_text)
            ws.write_datetime(row, 4, line.original_hire, fmt_date) if line.original_hire else ws.write(row, 4, '', fmt_text)
            ws.write(row, 5, line.service_months, fmt_num)
            ws.write(row, 6, line.seniority_years, fmt_num)
            ws.write(row, 7, line.daily_salary, fmt_num)
            # benefits in NET
            ws.write(row, 8, line.vacaciones, fmt_num)
            ws.write(row, 9, line.prestaciones, fmt_num)
            ws.write(row, 10, line.antiguedad, fmt_num)
            ws.write(row, 11, line.intereses, fmt_num)
            # pre-paid reference (strikethrough, grey)
            d = compute_forecast_for_contract(line.contract_id, self.as_of_date)
            ws.write(row, 12, d['bono_vacacional_gross'], fmt_pre)
            ws.write(row, 13, d['utilidades_gross'], fmt_pre)
            # deductions
            ws.write(row, 14, line.faov, fmt_num)
            ws.write(row, 15, line.prepaid, fmt_num)
            # net
            ws.write(row, 16, line.net, fmt_num_green)
            ws.write(row, 17, line.net_veb, fmt_num_veb)
            row += 1

        # ── totals row ───────────────────────────────────────────────────────
        ws.merge_range(row, 0, row, 15,
                       'TOTAL (%d empleados)' % self.employee_count,
                       wb.add_format({'bold': True, 'bg_color': '#1a2c5b',
                                      'font_color': 'white', 'border': 1,
                                      'align': 'right', 'font_size': 9}))
        ws.write(row, 16, self.total_net_usd, fmt_total)
        ws.write(row, 17, self.total_net_veb, fmt_total_veb)

        # ── notes row ────────────────────────────────────────────────────────
        ws.merge_range(row + 2, 0, row + 2, 17,
                       'ⓟ Bono Vac. y Utilidades excluidos del NETO (pre-pagados, política UEIPAB) — mostrados tachados como referencia. '
                       'FAOV = 1% solo sobre Vacaciones. INCES = $0. '
                       'Fórmulas: vac progresivo 15+1d/año, prest 15d/trim salario integral, antig 2d/mes desde ingreso original, intereses 13% anual.',
                       wb.add_format({'italic': True, 'font_size': 7,
                                      'font_color': '#888888', 'text_wrap': True}))
        ws.set_row(row + 2, 24)

        ws.freeze_panes(3, 2)

        wb.close()
        xlsx_data = base64.b64encode(output.getvalue())
        filename = 'Pronostico_Liquidacion_V2_%s.xlsx' % (
            self.as_of_date.strftime('%Y%m%d') if self.as_of_date else 'export'
        )
        self.write({'excel_file': xlsx_data, 'excel_filename': filename})

        # Re-open wizard so the download widget appears
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'liquidacion.v2.forecast.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


# ─── helper: detect V2 contract ──────────────────────────────────────────────

def _has_liquid_v2(env, contract):
    """Return True if there is a LIQUID_VE_V2 structure in the system and the
    contract uses ueipab_salary_v2 (proxy: field is non-zero).  We can't link
    contract→structure directly; finance wants everyone whose payslip would use V2."""
    struct = env['hr.payroll.structure'].search(
        [('code', '=', 'LIQUID_VE_V2')], limit=1
    )
    if not struct:
        return False
    salary = contract.ueipab_salary_v2 or 0.0
    return salary > 0
