import calendar
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Datetime as OdooDatetime

MONTHS_ES = [
    ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'), ('4', 'Abril'),
    ('5', 'Mayo'), ('6', 'Junio'), ('7', 'Julio'), ('8', 'Agosto'),
    ('9', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
]


class HrAttendanceReportWizard(models.TransientModel):
    _name = 'hr.attendance.report.wizard'
    _description = 'Asistente de Reporte de Asistencia Quincenal'

    # ─── Generation mode ──────────────────────────────────────────────────────
    generation_mode = fields.Selection([
        ('single', 'Quincena específica'),
        ('range',  'Rango de meses (envío masivo)'),
    ], string='Modo', default='single', required=True)

    # ─── Single-quincena fields ───────────────────────────────────────────────
    year = fields.Char(
        string='Año', size=4,
        default=lambda self: str(date.today().year),
    )
    month = fields.Selection(
        MONTHS_ES, string='Mes',
        default=lambda self: str(date.today().month),
    )
    quincena = fields.Selection(
        [('1', '1ra Quincena (días 1–15)'), ('2', '2da Quincena (días 16–fin)')],
        string='Quincena',
        default=lambda self: '1' if date.today().day <= 15 else '2',
    )
    date_from = fields.Date(string='Desde', compute='_compute_single_dates')
    date_to   = fields.Date(string='Hasta', compute='_compute_single_dates')

    # ─── Range fields ─────────────────────────────────────────────────────────
    range_from_month = fields.Selection(
        MONTHS_ES, string='Desde mes',
        default='10',
    )
    range_from_year = fields.Char(
        string='Desde año', size=4, default='2025',
    )
    range_to_month = fields.Selection(
        MONTHS_ES, string='Hasta mes',
        default=lambda self: str(date.today().month),
    )
    range_to_year = fields.Char(
        string='Hasta año', size=4,
        default=lambda self: str(date.today().year),
    )
    range_preview = fields.Char(
        string='Quincenas a generar', compute='_compute_range_preview',
    )

    # ─── Employee selection ───────────────────────────────────────────────────
    filter_mode = fields.Selection([
        ('all',        'Todos los empleados activos'),
        ('department', 'Por departamento'),
        ('manual',     'Selección manual'),
    ], string='Incluir', default='all', required=True)

    department_id = fields.Many2one('hr.department', string='Departamento')

    employee_ids = fields.Many2many(
        'hr.employee', string='Empleados',
        default=lambda self: self.env['hr.employee'].search([('active', '=', True)]),
    )

    employees_info = fields.Char(
        string='Resumen de selección', compute='_compute_employees_info',
    )

    # ─── Send option ──────────────────────────────────────────────────────────
    send_email = fields.Boolean(
        string='Enviar correo inmediatamente al generar',
        default=False,
        help="Envía el correo a cada empleado con email al generar los reportes.",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Compute / onchange
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('year', 'month', 'quincena')
    def _compute_single_dates(self):
        for rec in self:
            if not rec.year or not rec.month or not rec.quincena:
                rec.date_from = rec.date_to = False
                continue
            try:
                m, y = int(rec.month), int(rec.year)
            except (ValueError, TypeError):
                rec.date_from = rec.date_to = False
                continue
            if rec.quincena == '1':
                rec.date_from = date(y, m, 1)
                rec.date_to   = date(y, m, 15)
            else:
                _, last = calendar.monthrange(y, m)
                rec.date_from = date(y, m, 16)
                rec.date_to   = date(y, m, last)

    @api.depends('range_from_month', 'range_from_year',
                 'range_to_month', 'range_to_year', 'generation_mode')
    def _compute_range_preview(self):
        for rec in self:
            if rec.generation_mode != 'range':
                rec.range_preview = ''
                continue
            qs = rec._get_quincenas_in_range()
            if not qs:
                rec.range_preview = 'Sin quincenas en el rango (verifique las fechas).'
            else:
                rec.range_preview = (
                    f"{len(qs)} quincenas  ·  "
                    f"{qs[0]['label']} → {qs[-1]['label']}"
                )

    @api.depends('employee_ids')
    def _compute_employees_info(self):
        for rec in self:
            total = len(rec.employee_ids)
            if not total:
                rec.employees_info = 'Sin empleados seleccionados.'
                continue
            no_email   = sum(1 for e in rec.employee_ids if not e.work_email)
            with_email = total - no_email
            if no_email:
                rec.employees_info = (
                    f'{total} seleccionados  ·  '
                    f'{with_email} con email (recibirán correo)  ·  '
                    f'{no_email} sin email (solo reporte, sin correo)'
                )
            else:
                rec.employees_info = f'{total} seleccionados  ·  todos con email ✓'

    @api.onchange('filter_mode')
    def _onchange_filter_mode(self):
        if self.filter_mode == 'all':
            self.department_id = False
            self.employee_ids = self.env['hr.employee'].search([('active', '=', True)])
        elif self.filter_mode == 'department':
            self.employee_ids = [(5, 0, 0)]
        elif self.filter_mode == 'manual':
            self.employee_ids = [(5, 0, 0)]

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.filter_mode != 'department':
            return
        if self.department_id:
            self.employee_ids = self.env['hr.employee'].search([
                ('active', '=', True),
                ('department_id', '=', self.department_id.id),
            ])
        else:
            self.employee_ids = [(5, 0, 0)]

    @api.onchange('generation_mode')
    def _onchange_generation_mode(self):
        """Reset employee filter to 'all' when switching modes for clean UX."""
        if self.generation_mode == 'range' and self.filter_mode == 'all':
            self.employee_ids = self.env['hr.employee'].search([('active', '=', True)])

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_quincenas_in_range(self):
        """Return list of dicts for every quincena within the selected range.

        Stops at today — future quincenas are never generated.
        """
        if not (self.range_from_month and self.range_from_year and
                self.range_to_month and self.range_to_year):
            return []
        try:
            fm, fy = int(self.range_from_month), int(self.range_from_year)
            tm, ty = int(self.range_to_month),   int(self.range_to_year)
        except (ValueError, TypeError):
            return []

        if (fy, fm) > (ty, tm):
            return []

        today   = date.today()
        months  = dict(MONTHS_ES)
        result  = []
        y, m    = fy, fm

        while (y, m) <= (ty, tm):
            for q in ('1', '2'):
                if q == '1':
                    df = date(y, m, 1)
                    dt = date(y, m, 15)
                else:
                    _, last = calendar.monthrange(y, m)
                    df = date(y, m, 16)
                    dt = date(y, m, last)

                if df > today:
                    return result           # stop at first future quincena

                result.append({
                    'quincena':  q,
                    'month':     m,
                    'year':      y,
                    'date_from': df,
                    'date_to':   dt,
                    'label':     f"Q{q} {months.get(str(m), m)} {y}",
                })

            m += 1
            if m > 12:
                m, y = 1, y + 1

        return result

    def _send_emails(self, report_ids):
        if not report_ids:
            return
        template = self.env.ref(
            'ueipab_attendance_report.email_template_attendance_report',
            raise_if_not_found=True,
        )
        Report = self.env['hr.attendance.report']
        for rid in report_ids:
            rec = Report.browse(rid)
            if rec.employee_id.work_email:
                template.send_mail(rid, force_send=True)
                # Historical records stay 'acknowledged' — don't downgrade to 'sent'
                if not rec.is_historical:
                    rec.write({'state': 'sent', 'sent_date': OdooDatetime.now()})
                else:
                    rec.write({'sent_date': OdooDatetime.now()})

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def action_generate_reports(self):
        self.ensure_one()
        if not self.employee_ids:
            raise UserError(_("Seleccione al menos un empleado."))

        if self.generation_mode == 'range':
            return self._action_generate_range()
        return self._action_generate_single()

    # ── Single quincena ───────────────────────────────────────────────────────

    def _action_generate_single(self):
        if not self.date_from or not self.date_to:
            raise UserError(_("Complete el período antes de continuar."))

        Report     = self.env['hr.attendance.report']
        created_ids = []
        skipped     = 0

        for emp in self.employee_ids:
            if Report.search([
                ('employee_id', '=', emp.id),
                ('date_from',   '=', self.date_from),
                ('date_to',     '=', self.date_to),
            ], limit=1):
                skipped += 1
                continue
            rec = Report.create({
                'employee_id': emp.id,
                'date_from':   self.date_from,
                'date_to':     self.date_to,
                'quincena':    self.quincena,
                'month':       int(self.month),
                'year':        int(self.year),
            })
            created_ids.append(rec.id)

        if not created_ids and skipped:
            raise UserError(
                _("Todos los reportes para este período ya existen (%d omitidos).") % skipped
            )

        if self.send_email:
            self._send_emails(created_ids)

        month_name = dict(MONTHS_ES).get(self.month, self.month)
        return {
            'type': 'ir.actions.act_window',
            'name': f"Asistencia Q{self.quincena} — {month_name} {self.year}",
            'res_model': 'hr.attendance.report',
            'view_mode': 'tree,form',
            'domain': [
                ('date_from', '=', fields.Date.to_string(self.date_from)),
                ('date_to',   '=', fields.Date.to_string(self.date_to)),
            ],
            'context': {'created_count': len(created_ids), 'skipped_count': skipped},
        }

    # ── Range (bulk) ──────────────────────────────────────────────────────────

    def _action_generate_range(self):
        quincenas = self._get_quincenas_in_range()
        if not quincenas:
            raise UserError(_(
                "No hay quincenas en el rango seleccionado. "
                "Verifique que el mes/año de inicio sea anterior al de fin."
            ))

        Report      = self.env['hr.attendance.report']
        created_ids = []
        skipped     = 0

        for q in quincenas:
            for emp in self.employee_ids:
                if Report.search([
                    ('employee_id', '=', emp.id),
                    ('date_from',   '=', q['date_from']),
                    ('date_to',     '=', q['date_to']),
                ], limit=1):
                    skipped += 1
                    continue
                rec = Report.create({
                    'employee_id': emp.id,
                    'date_from':   q['date_from'],
                    'date_to':     q['date_to'],
                    'quincena':    q['quincena'],
                    'month':       q['month'],
                    'year':        q['year'],
                })
                created_ids.append(rec.id)

        if not created_ids and skipped:
            raise UserError(
                _("Todos los reportes del rango ya existen (%d omitidos).") % skipped
            )

        if self.send_email:
            self._send_emails(created_ids)

        from_label = quincenas[0]['label']
        to_label   = quincenas[-1]['label']
        n_emps     = len(self.employee_ids)

        return {
            'type': 'ir.actions.act_window',
            'name': f"Asistencia {from_label} → {to_label} ({n_emps} empl.)",
            'res_model': 'hr.attendance.report',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_ids)],
            'context': {'created_count': len(created_ids), 'skipped_count': skipped},
        }
