# -*- coding: utf-8 -*-
"""
Payroll Requisition Estimation Wizard

Generates a preliminary payroll cost estimate directly from active contracts,
without requiring any payslip to be created or computed first.

Useful for Finance to prepare bank requisitions or accounting provisions
before HR starts the payroll workflow.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO
import xlsxwriter
from datetime import date
import calendar


class PayrollRequisitionWizard(models.TransientModel):
    """Wizard for generating a preliminary payroll requisition estimate."""

    _name = 'payroll.requisition.wizard'
    _description = 'Requisición Preliminar de Nómina'

    # ========================================
    # PERIOD SELECTION
    # ========================================

    period_type = fields.Selection([
        ('q1', 'Quincena 1 (días 1–15)'),
        ('q2', 'Quincena 2 (días 16–fin de mes)'),
    ], string='Período', required=True, default='q1')

    period_month = fields.Date(
        string='Mes / Año',
        required=True,
        default=lambda self: date.today().replace(day=1),
        help='Seleccione cualquier día del mes objetivo. Se usará el mes completo.'
    )

    # ========================================
    # CURRENCY & EXCHANGE RATE
    # ========================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.ref('base.USD'),
        domain=[('name', 'in', ['USD', 'VEB'])],
    )

    exchange_rate = fields.Float(
        string='Tasa de Cambio (VEB/USD)',
        digits=(12, 4),
        help='Tasa BCV auto-cargada desde el último registro disponible. Puede editar manualmente.'
    )

    exchange_rate_date = fields.Date(
        string='Fecha de Tasa',
        help='Fecha del registro de tasa utilizado para el auto-llenado.'
    )

    exchange_rate_source = fields.Char(
        string='Fuente de Tasa',
        default='',
    )

    show_exchange_rate = fields.Boolean(
        compute='_compute_show_exchange_rate',
    )

    # ========================================
    # OPTIONAL: ADVANCE PAYMENT
    # ========================================

    is_advance = fields.Boolean(
        string='Es Adelanto',
        default=False,
        help='Activar si este es un pago de adelanto parcial.'
    )

    advance_percentage = fields.Float(
        string='Porcentaje de Adelanto (%)',
        default=50.0,
        help='Porcentaje del neto a pagar como adelanto (ej. 50 = 50%).'
    )

    # ========================================
    # FILTERS
    # ========================================

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados',
        help='Filtrar empleados específicos. Dejar vacío = todos los activos.'
    )

    department_ids = fields.Many2many(
        'hr.department',
        string='Departamentos',
        help='Filtrar por departamento. Dejar vacío = todos.'
    )

    # ========================================
    # OUTPUT FORMAT
    # ========================================

    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel (.xlsx)'),
    ], string='Formato', required=True, default='pdf')

    # ========================================
    # COMPUTED PREVIEW
    # ========================================

    employee_count = fields.Integer(
        string='Empleados encontrados',
        compute='_compute_employee_count',
    )

    # ========================================
    # COMPUTE / ONCHANGE
    # ========================================

    @api.depends('currency_id')
    def _compute_show_exchange_rate(self):
        usd = self.env.ref('base.USD')
        for w in self:
            w.show_exchange_rate = w.currency_id and w.currency_id != usd

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        """Auto-populate exchange rate when VEB is selected."""
        usd = self.env.ref('base.USD')
        if not self.currency_id or self.currency_id == usd:
            self.exchange_rate = 0.0
            self.exchange_rate_date = False
            self.exchange_rate_source = ''
            return

        rate_record = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_id.id)],
            limit=1, order='name desc'
        )
        if rate_record:
            self.exchange_rate = rate_record.company_rate
            self.exchange_rate_date = rate_record.name
            self.exchange_rate_source = 'BCV al %s' % rate_record.name.strftime('%d/%m/%Y')
        else:
            self.exchange_rate = 0.0
            self.exchange_rate_date = False
            self.exchange_rate_source = 'No se encontró tasa disponible'

    @api.depends('employee_ids', 'department_ids')
    def _compute_employee_count(self):
        for w in self:
            contracts = w._get_filtered_contracts()
            w.employee_count = len(contracts)

    # ========================================
    # BUSINESS LOGIC
    # ========================================

    def _get_filtered_contracts(self):
        """Return active (running) contracts matching optional filters."""
        self.ensure_one()
        domain = [('state', '=', 'open')]  # 'open' = running in Odoo HR
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        if self.department_ids:
            domain.append(('employee_id.department_id', 'in', self.department_ids.ids))
        contracts = self.env['hr.contract'].search(domain)
        return contracts.sorted(lambda c: c.employee_id.name or '')

    _MONTHS_ES = {
        1: 'ENERO', 2: 'FEBRERO', 3: 'MARZO', 4: 'ABRIL',
        5: 'MAYO', 6: 'JUNIO', 7: 'JULIO', 8: 'AGOSTO',
        9: 'SEPTIEMBRE', 10: 'OCTUBRE', 11: 'NOVIEMBRE', 12: 'DICIEMBRE',
    }

    def _get_period_label(self):
        """Return human-readable period label, e.g. 'Quincena 1 — MAYO 2026'."""
        self.ensure_one()
        month_name = '%s %s' % (self._MONTHS_ES[self.period_month.month], self.period_month.year)
        q = 'Quincena 1 (1–15)' if self.period_type == 'q1' else 'Quincena 2 (16–fin)'
        return '%s — %s' % (q, month_name)

    def _get_effective_rate(self):
        """Return the exchange rate to apply (1.0 for USD)."""
        self.ensure_one()
        usd = self.env.ref('base.USD')
        if self.currency_id == usd:
            return 1.0
        return self.exchange_rate or 1.0

    def _get_rate_source_label(self):
        """
        Derive the exchange rate source label at export time.

        We re-query res.currency.rate rather than relying on exchange_rate_source
        being persisted, because Odoo 17 web_save drops invisible fields from the
        payload (exchange_rate_source is invisible when USD is selected at form open).
        """
        self.ensure_one()
        usd = self.env.ref('base.USD')
        if self.currency_id == usd:
            return 'USD'
        # If exchange_rate_date was persisted, use it directly
        if self.exchange_rate_date:
            return 'BCV al %s' % self.exchange_rate_date.strftime('%d/%m/%Y')
        # Otherwise re-query the latest available rate record
        rate_record = self.env['res.currency.rate'].search(
            [('currency_id', '=', self.currency_id.id)],
            limit=1, order='name desc'
        )
        if rate_record:
            return 'BCV al %s' % rate_record.name.strftime('%d/%m/%Y')
        return 'Tasa personalizada'

    def _compute_contract_data(self, contract):
        """
        Compute estimated payroll figures for one contract.

        Returns a dict with all monetary values in USD (pre-rate).
        Caller applies the exchange rate for display.
        """
        # Salary and bonus from V2 contract fields
        salary = contract.ueipab_salary_v2 or 0.0
        if salary <= 0:
            # V1 fallback: use wage
            salary = contract.wage or 0.0

        extrabonus = contract.ueipab_extrabonus_v2 or 0.0
        bonus_v2 = contract.ueipab_bonus_v2 or 0.0
        cesta = contract.cesta_ticket_usd or 0.0
        bonus = extrabonus + bonus_v2 + cesta

        # Quincena proration: always monthly / 2.0 (fixed 2026-02-25)
        salary_q = salary / 2.0
        bonus_q = bonus / 2.0
        gross_q = salary_q + bonus_q

        # Deductions — applied on salary portion only (bonus exempt)
        ari_rate = (contract.ueipab_ari_withholding_rate or 0.0) / 100.0
        ari = salary_q * ari_rate
        sso = salary_q * 0.04    # 4%
        faov = salary_q * 0.01   # 1%
        # PARO (0.5%) only for Utilidades — skip in quincena estimation

        total_deductions = ari + sso + faov
        net = gross_q - total_deductions

        # Advance amount (if applicable)
        advance_pct = self.advance_percentage / 100.0 if self.is_advance else 1.0
        advance_amt = net * advance_pct

        return {
            'employee_name': contract.employee_id.name,
            'identification_id': contract.employee_id.identification_id or '',
            'work_email': contract.employee_id.work_email or '',
            'salary': salary_q,
            'bonus': bonus_q,
            'gross': gross_q,
            'ari': ari,
            'ari_rate_pct': contract.ueipab_ari_withholding_rate or 0.0,
            'sso': sso,
            'faov': faov,
            'total_deductions': total_deductions,
            'net': net,
            'advance_amt': advance_amt,
        }

    def _get_all_employee_data(self):
        """Compute data for all filtered contracts. Returns list of dicts."""
        self.ensure_one()
        contracts = self._get_filtered_contracts()
        if not contracts:
            raise UserError(_(
                'No se encontraron contratos activos con los filtros seleccionados.'
            ))
        return [self._compute_contract_data(c) for c in contracts]

    # ========================================
    # ACTION METHODS
    # ========================================

    def action_generate_report(self):
        """Route to PDF or Excel based on output_format."""
        self.ensure_one()

        usd = self.env.ref('base.USD')
        if self.currency_id != usd and (not self.exchange_rate or self.exchange_rate <= 0):
            raise UserError(_(
                'La tasa de cambio es requerida y debe ser mayor que cero cuando se selecciona VEB.'
            ))
        if self.is_advance and (self.advance_percentage <= 0 or self.advance_percentage > 100):
            raise UserError(_('El porcentaje de adelanto debe estar entre 1 y 100.'))

        if self.output_format == 'excel':
            return self._action_export_excel()
        return self._action_export_pdf()

    def _action_export_pdf(self):
        """Generate PDF via QWeb report."""
        self.ensure_one()
        employee_data = self._get_all_employee_data()
        rate = self._get_effective_rate()

        # Pre-compute totals for the template
        totals = {
            'salary': sum(r['salary'] for r in employee_data) * rate,
            'bonus': sum(r['bonus'] for r in employee_data) * rate,
            'gross': sum(r['gross'] for r in employee_data) * rate,
            'ari': sum(r['ari'] for r in employee_data) * rate,
            'sso': sum(r['sso'] for r in employee_data) * rate,
            'faov': sum(r['faov'] for r in employee_data) * rate,
            'total_deductions': sum(r['total_deductions'] for r in employee_data) * rate,
            'net': sum(r['net'] for r in employee_data) * rate,
            'advance_amt': sum(r['advance_amt'] for r in employee_data) * rate,
        }
        totals['tax_9pct'] = totals['net'] * 0.09

        # Apply rate to each employee row
        for row in employee_data:
            for key in ('salary', 'bonus', 'gross', 'ari', 'sso', 'faov',
                        'total_deductions', 'net', 'advance_amt'):
                row[key + '_display'] = row[key] * rate

        data = {
            'wizard_id': self.id,
            'period_label': self._get_period_label(),
            'currency_name': self.currency_id.name,
            'currency_symbol': self.currency_id.symbol,
            'exchange_rate': rate,
            'exchange_rate_source': self._get_rate_source_label(),
            'is_advance': self.is_advance,
            'advance_percentage': self.advance_percentage,
            'employees': employee_data,
            'totals': totals,
            'employee_count': len(employee_data),
            'report_date': fields.Date.today().strftime('%d/%m/%Y'),
        }

        report = self.env.ref(
            'ueipab_payroll_enhancements.action_report_payroll_requisition'
        )
        return report.report_action(docids=[self.id], data=data)

    def _action_export_excel(self):
        """Generate Excel (.xlsx) export."""
        self.ensure_one()
        employee_data = self._get_all_employee_data()
        rate = self._get_effective_rate()
        cur_sym = self.currency_id.symbol
        cur_name = self.currency_id.name

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Requisicion Preliminar')

        # ---- Formats ----
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 13, 'align': 'center', 'valign': 'vcenter',
        })
        subtitle_fmt = workbook.add_format({
            'italic': True, 'font_size': 9, 'align': 'center', 'font_color': '#CC0000',
        })
        meta_fmt = workbook.add_format({
            'font_size': 9, 'align': 'center', 'font_color': '#555555',
        })
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
        })
        text_fmt = workbook.add_format({'align': 'left'})
        num_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        total_label_fmt = workbook.add_format({'bold': True, 'align': 'left'})
        total_num_fmt = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00', 'align': 'right', 'top': 1,
        })
        net_fmt = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00', 'align': 'right',
            'font_color': '#0066CC',
        })
        advance_fmt = workbook.add_format({
            'bold': True, 'num_format': '#,##0.00', 'align': 'right',
            'bg_color': '#FFF3E0', 'font_color': '#E65100',
        })

        # ---- Column widths ----
        worksheet.set_column('A:A', 30)   # Employee
        worksheet.set_column('B:B', 14)   # ID
        worksheet.set_column('C:C', 30)   # Email
        worksheet.set_column('D:D', 13)   # Salary
        worksheet.set_column('E:E', 13)   # Bonus
        worksheet.set_column('F:F', 13)   # Gross
        worksheet.set_column('G:G', 10)   # ARI %
        worksheet.set_column('H:H', 13)   # ARI amt
        worksheet.set_column('I:I', 13)   # SSO 4%
        worksheet.set_column('J:J', 13)   # FAOV 1%
        worksheet.set_column('K:K', 13)   # Total Ded
        worksheet.set_column('L:L', 14)   # Net
        last_col = 'L'
        if self.is_advance:
            worksheet.set_column('M:M', 14)
            last_col = 'M'

        # ---- Title rows ----
        worksheet.set_row(0, 22)
        worksheet.merge_range(
            f'A1:{last_col}1',
            'REQUISICIÓN PRELIMINAR DE NÓMINA  [ESTIMADO]',
            title_fmt
        )
        worksheet.merge_range(
            f'A2:{last_col}2',
            self._get_period_label(),
            subtitle_fmt
        )
        rate_label = (
            'Tasa: %s  |  Fuente: %s' % (
                '{:,.4f}'.format(rate) + ' VEB/USD', self._get_rate_source_label()
            ) if self.currency_id.name == 'VEB'
            else 'Moneda: USD'
        )
        worksheet.merge_range(f'A3:{last_col}3', rate_label, meta_fmt)
        worksheet.merge_range(
            f'A4:{last_col}4',
            'Generado: %s  |  Empleados: %d' % (
                fields.Date.today().strftime('%d/%m/%Y'), len(employee_data)
            ),
            meta_fmt
        )

        # ---- Headers ----
        headers = [
            'Empleado', 'Cédula', 'Email',
            f'Salario ({cur_sym})', f'Bono ({cur_sym})', f'Bruto ({cur_sym})',
            'ARI %',
            f'ARI ({cur_sym})', f'SSO 4% ({cur_sym})', f'FAOV 1% ({cur_sym})',
            f'Total Ded. ({cur_sym})', f'Neto ({cur_sym})',
        ]
        if self.is_advance:
            headers.append(f'Adelanto {int(self.advance_percentage)}% ({cur_sym})')

        for col, h in enumerate(headers):
            worksheet.write(5, col, h, header_fmt)

        # ---- Data rows ----
        row = 6
        totals = {k: 0.0 for k in ('salary', 'bonus', 'gross', 'ari', 'sso',
                                    'faov', 'total_deductions', 'net', 'advance_amt')}
        for emp in employee_data:
            s = emp['salary'] * rate
            b = emp['bonus'] * rate
            g = emp['gross'] * rate
            ari = emp['ari'] * rate
            sso = emp['sso'] * rate
            faov = emp['faov'] * rate
            td = emp['total_deductions'] * rate
            net = emp['net'] * rate
            adv = emp['advance_amt'] * rate

            worksheet.write(row, 0, emp['employee_name'], text_fmt)
            worksheet.write(row, 1, emp['identification_id'], text_fmt)
            worksheet.write(row, 2, emp['work_email'], text_fmt)
            worksheet.write(row, 3, s, num_fmt)
            worksheet.write(row, 4, b, num_fmt)
            worksheet.write(row, 5, g, num_fmt)
            worksheet.write(row, 6, emp['ari_rate_pct'], workbook.add_format(
                {'num_format': '0.00"%"', 'align': 'right'}))
            worksheet.write(row, 7, ari, num_fmt)
            worksheet.write(row, 8, sso, num_fmt)
            worksheet.write(row, 9, faov, num_fmt)
            worksheet.write(row, 10, td, num_fmt)
            worksheet.write(row, 11, net, net_fmt)
            if self.is_advance:
                worksheet.write(row, 12, adv, advance_fmt)

            for k, v in zip(
                ('salary', 'bonus', 'gross', 'ari', 'sso', 'faov',
                 'total_deductions', 'net', 'advance_amt'),
                (s, b, g, ari, sso, faov, td, net, adv)
            ):
                totals[k] += v
            row += 1

        # ---- Totals row ----
        worksheet.write(row, 0, 'TOTAL', total_label_fmt)
        worksheet.write(row, 1, '', text_fmt)
        worksheet.write(row, 2, '', text_fmt)
        worksheet.write(row, 3, totals['salary'], total_num_fmt)
        worksheet.write(row, 4, totals['bonus'], total_num_fmt)
        worksheet.write(row, 5, totals['gross'], total_num_fmt)
        worksheet.write(row, 6, '', text_fmt)
        worksheet.write(row, 7, totals['ari'], total_num_fmt)
        worksheet.write(row, 8, totals['sso'], total_num_fmt)
        worksheet.write(row, 9, totals['faov'], total_num_fmt)
        worksheet.write(row, 10, totals['total_deductions'], total_num_fmt)
        worksheet.write(row, 11, totals['net'], workbook.add_format({
            'bold': True, 'num_format': '#,##0.00', 'align': 'right',
            'top': 1, 'font_color': '#0066CC',
        }))
        if self.is_advance:
            worksheet.write(row, 12, totals['advance_amt'], workbook.add_format({
                'bold': True, 'num_format': '#,##0.00', 'align': 'right',
                'top': 1, 'bg_color': '#FFF3E0', 'font_color': '#E65100',
            }))

        # ---- Summary block ----
        row += 2
        tax_9 = totals['net'] * 0.09
        summary = [
            (f'Total Bruto ({cur_name})', totals['gross']),
            (f'Total Deducciones ({cur_name})', totals['total_deductions']),
            (f'Total Neto ({cur_name})', totals['net']),
            (f'Impuesto 9% s/Neto ({cur_name})', tax_9),
        ]
        if self.is_advance:
            summary.append(
                (f'Total Adelanto {int(self.advance_percentage)}% ({cur_name})',
                 totals['advance_amt'])
            )
        for label, val in summary:
            worksheet.write(row, 10, label, total_label_fmt)
            worksheet.write(row, 11, val, total_num_fmt)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Build filename
        period_str = self.period_month.strftime('%Y-%m')
        q = 'Q1' if self.period_type == 'q1' else 'Q2'
        filename = 'Requisicion_Preliminar_%s_%s_%s.xlsx' % (period_str, q, cur_name)

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }
