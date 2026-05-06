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

    # -------------------------------------------------------------------------
    # Period fields
    # -------------------------------------------------------------------------
    year = fields.Integer(
        string='Año',
        default=lambda self: date.today().year,
        required=True,
    )
    month = fields.Selection(
        MONTHS_ES, string='Mes', required=True,
        default=lambda self: str(date.today().month),
    )
    quincena = fields.Selection(
        [('1', '1ra Quincena (días 1–15)'), ('2', '2da Quincena (días 16–fin)')],
        string='Quincena', required=True,
        default=lambda self: '1' if date.today().day <= 15 else '2',
    )
    date_from = fields.Date(string='Desde', compute='_compute_dates')
    date_to = fields.Date(string='Hasta', compute='_compute_dates')

    # -------------------------------------------------------------------------
    # Employee selection fields
    # -------------------------------------------------------------------------
    filter_mode = fields.Selection([
        ('all',        'Todos los empleados activos'),
        ('department', 'Por departamento'),
        ('manual',     'Selección manual'),
    ], string='Incluir', default='all', required=True)

    department_id = fields.Many2one(
        'hr.department', string='Departamento',
    )

    employee_ids = fields.Many2many(
        'hr.employee', string='Empleados',
        default=lambda self: self.env['hr.employee'].search([('active', '=', True)]),
    )

    employees_info = fields.Char(
        string='Resumen de selección',
        compute='_compute_employees_info',
    )

    # -------------------------------------------------------------------------
    # Send option
    # -------------------------------------------------------------------------
    send_email = fields.Boolean(
        string='Enviar correo inmediatamente al generar',
        default=False,
        help="Envía el correo de notificación a cada empleado con email al generar el reporte.",
    )

    # -------------------------------------------------------------------------
    # Compute / onchange
    # -------------------------------------------------------------------------

    @api.depends('year', 'month', 'quincena')
    def _compute_dates(self):
        for rec in self:
            if not rec.year or not rec.month or not rec.quincena:
                rec.date_from = rec.date_to = False
                continue
            m = int(rec.month)
            y = rec.year
            if rec.quincena == '1':
                rec.date_from = date(y, m, 1)
                rec.date_to = date(y, m, 15)
            else:
                _, last_day = calendar.monthrange(y, m)
                rec.date_from = date(y, m, 16)
                rec.date_to = date(y, m, last_day)

    @api.depends('employee_ids')
    def _compute_employees_info(self):
        for rec in self:
            total = len(rec.employee_ids)
            if not total:
                rec.employees_info = 'Sin empleados seleccionados.'
                continue
            no_email = sum(1 for e in rec.employee_ids if not e.work_email)
            with_email = total - no_email
            if no_email:
                rec.employees_info = (
                    f'{total} seleccionados  ·  '
                    f'{with_email} con email (recibirán correo)  ·  '
                    f'{no_email} sin email (solo reporte, sin correo)'
                )
            else:
                rec.employees_info = (
                    f'{total} seleccionados  ·  todos con email ✓'
                )

    @api.onchange('filter_mode')
    def _onchange_filter_mode(self):
        if self.filter_mode == 'all':
            self.department_id = False
            self.employee_ids = self.env['hr.employee'].search([('active', '=', True)])
        elif self.filter_mode == 'department':
            # Clear employees — will repopulate when department is chosen
            self.employee_ids = [(5, 0, 0)]
        elif self.filter_mode == 'manual':
            # Clear for fresh manual pick
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

    # -------------------------------------------------------------------------
    # Action
    # -------------------------------------------------------------------------

    def action_generate_reports(self):
        self.ensure_one()
        if not self.employee_ids:
            raise UserError(_("Seleccione al menos un empleado."))
        if not self.date_from or not self.date_to:
            raise UserError(_("Complete el período antes de continuar."))

        Report = self.env['hr.attendance.report']
        created_ids = []
        skipped = 0

        for emp in self.employee_ids:
            existing = Report.search([
                ('employee_id', '=', emp.id),
                ('date_from', '=', self.date_from),
                ('date_to', '=', self.date_to),
            ], limit=1)
            if existing:
                skipped += 1
                continue
            rec = Report.create({
                'employee_id': emp.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'quincena': self.quincena,
                'month': int(self.month),
                'year': self.year,
                'state': 'draft',
            })
            created_ids.append(rec.id)

        if not created_ids and skipped:
            raise UserError(
                _("Todos los reportes para este período ya existen (%d omitidos).") % skipped
            )

        # Optionally send emails immediately
        if self.send_email and created_ids:
            template = self.env.ref(
                'ueipab_attendance_report.email_template_attendance_report',
                raise_if_not_found=True,
            )
            for rec_id in created_ids:
                rec = Report.browse(rec_id)
                if rec.employee_id.work_email:
                    template.send_mail(rec_id, force_send=True)
                    rec.write({
                        'state': 'sent',
                        'sent_date': OdooDatetime.now(),
                    })

        month_name = dict(MONTHS_ES).get(self.month, self.month)
        action_name = f"Asistencia Q{self.quincena} — {month_name} {self.year}"

        return {
            'type': 'ir.actions.act_window',
            'name': action_name,
            'res_model': 'hr.attendance.report',
            'view_mode': 'tree,form',
            'domain': [
                ('date_from', '=', fields.Date.to_string(self.date_from)),
                ('date_to', '=', fields.Date.to_string(self.date_to)),
            ],
            'context': {
                'created_count': len(created_ids),
                'skipped_count': skipped,
            },
        }
