import json
import uuid
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Venezuela Time = UTC - 4
VET_OFFSET = timedelta(hours=-4)

DAYS_ES = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles',
    3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo',
}

# (icon, row-bg, text-color)
STATUS_CFG = {
    'ok':           ('✅', '#ffffff', '#155724'),
    'missing_exit': ('⚠️',  '#fff3cd', '#856404'),
    'absent':       ('❌', '#fde8e8', '#721c24'),
    'weekend':      ('─',  '#f8f9fa', '#6c757d'),
    'holiday':      ('📅', '#e8f4f8', '#1a2c5b'),
    'dayoff':       ('─',  '#f0f4fa', '#8a9dc0'),  # special schedule — scheduled rest day
}


class HrAttendanceReport(models.Model):
    _name = 'hr.attendance.report'
    _description = 'Reporte de Asistencia Quincenal'
    _order = 'year desc, month desc, quincena desc, employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True,
        ondelete='cascade', index=True,
    )
    date_from = fields.Date(string='Desde', required=True)
    date_to = fields.Date(string='Hasta', required=True)
    quincena = fields.Selection(
        [('1', '1ra (1–15)'), ('2', '2da (16–fin)')],
        string='Quincena', required=True,
    )
    month = fields.Integer(string='Mes')
    year = fields.Integer(string='Año')

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviado'),
        ('acknowledged', 'Confirmado'),
    ], default='draft', string='Estado')

    # Historical flag: set on periods that closed before the current month.
    # Historical reports are auto-acknowledged and the email shows an
    # informational footer instead of the ACK button — no action required
    # from the employee.
    is_historical = fields.Boolean(
        string='Período histórico', default=False,
        help="Período cerrado antes del mes en curso. "
             "Confirmación automática, sin botón de acuse en el correo.",
    )

    sent_date = fields.Datetime(string='Fecha de Envío', readonly=True)
    ack_date = fields.Datetime(string='Fecha de Confirmación', readonly=True)
    ack_ip = fields.Char(string='IP de Confirmación', readonly=True)
    ack_token = fields.Char(
        string='Token ACK',
        default=lambda self: uuid.uuid4().hex,
        readonly=True, copy=False,
    )

    # Summary stats (computed on demand — no store to avoid stale cache)
    workday_count = fields.Integer(string='Días Hábiles', compute='_compute_summary')
    complete_days = fields.Integer(string='Días Completos', compute='_compute_summary')
    absent_days = fields.Integer(string='Ausencias', compute='_compute_summary')
    missing_exit_days = fields.Integer(string='Sin Salida', compute='_compute_summary')
    holiday_days = fields.Integer(string='Feriados', compute='_compute_summary')
    total_worked_hours = fields.Float(
        string='Horas Trabajadas', compute='_compute_summary', digits=(6, 2),
    )

    # Special schedule flag (maintenance/security staff with non-standard hours)
    is_special_schedule = fields.Boolean(
        string='Horario especial', compute='_compute_is_special_schedule',
    )

    # HTML preview rendered in form view
    attendance_table_html = fields.Html(
        string='Detalle de Asistencia',
        compute='_compute_html_table',
        sanitize=False,
    )

    _sql_constraints = [
        ('unique_employee_period',
         'UNIQUE(employee_id, date_from, date_to)',
         'Ya existe un reporte para este empleado en este período.'),
    ]

    @classmethod
    def _historical_cutoff(cls):
        """First day of current month — periods ending before this are historical."""
        from datetime import date
        today = date.today()
        return today.replace(day=1)

    def _get_special_schedule_employees(self):
        """Return set of employee IDs with special/rotating schedules.

        Key: attendance_report.special_schedule_employees
        Format: comma-separated employee IDs, e.g. "571,606,610"
        Admin manages via Settings > Technical > Parameters.
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'attendance_report.special_schedule_employees', ''
        )
        result = set()
        for part in param.split(','):
            part = part.strip()
            if part.isdigit():
                result.add(int(part))
        return result

    @api.depends('employee_id')
    def _compute_is_special_schedule(self):
        special = self._get_special_schedule_employees()
        for rec in self:
            rec.is_special_schedule = rec.employee_id.id in special

    @api.model_create_multi
    def create(self, vals_list):
        cutoff = self._historical_cutoff()
        now = fields.Datetime.now()
        for vals in vals_list:
            date_to = vals.get('date_to')
            if date_to:
                if isinstance(date_to, str):
                    from datetime import date as date_cls
                    date_to = date_cls.fromisoformat(date_to)
                if date_to < cutoff:
                    vals['is_historical'] = True
                    vals['state'] = 'acknowledged'
                    vals['ack_date'] = now
                    vals['ack_ip'] = 'auto-histórico'
        return super().create(vals_list)

    def name_get(self):
        result = []
        for rec in self:
            name = f"{rec.employee_id.name or ''} | Q{rec.quincena} {rec.month}/{rec.year}"
            result.append((rec.id, name))
        return result

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_summary(self):
        special = self._get_special_schedule_employees()
        for rec in self:
            days = rec.get_attendance_days()
            is_special = rec.employee_id.id in special

            if is_special:
                # Mon-Fri non-holiday count as reference (includes dayoff days)
                rec.workday_count = sum(
                    1 for d in days if not d['is_weekend'] and d['status'] != 'holiday'
                )
                # Count ALL days (incl. weekends) they actually worked
                rec.complete_days = sum(1 for d in days if d['status'] == 'ok')
                rec.missing_exit_days = sum(1 for d in days if d['status'] == 'missing_exit')
                rec.absent_days = 0  # no absence penalty for special schedules
            else:
                workdays = [d for d in days if not d['is_weekend'] and d['status'] != 'holiday']
                rec.workday_count = len(workdays)
                rec.complete_days = sum(1 for d in workdays if d['status'] == 'ok')
                rec.absent_days = sum(1 for d in workdays if d['status'] == 'absent')
                rec.missing_exit_days = sum(1 for d in workdays if d['status'] == 'missing_exit')

            rec.holiday_days = sum(1 for d in days if d['status'] == 'holiday')
            rec.total_worked_hours = sum(d['worked_hours'] for d in days)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_html_table(self):
        for rec in self:
            rec.attendance_table_html = rec._build_html_table()

    # -------------------------------------------------------------------------
    # Core data method (used by both form view and email template Phase 2)
    # -------------------------------------------------------------------------

    def _get_holiday_dates(self):
        """Return {date: name} for public holidays from ir.config_parameter.

        Parameter key: attendance_report.holidays
        Format: JSON array of {"date": "YYYY-MM-DD", "name": "..."} objects.
        Admin can edit via Settings > Technical > Parameters > System Parameters.
        """
        param = self.env['ir.config_parameter'].sudo().get_param(
            'attendance_report.holidays', '[]'
        )
        try:
            entries = json.loads(param)
        except (ValueError, TypeError):
            return {}
        from datetime import date as date_cls
        result = {}
        for entry in entries:
            try:
                if isinstance(entry, dict):
                    d = date_cls.fromisoformat(entry['date'])
                    result[d] = entry.get('name', 'Feriado')
                else:
                    d = date_cls.fromisoformat(str(entry))
                    result[d] = 'Feriado'
            except (ValueError, KeyError):
                continue
        return result

    def get_attendance_days(self):
        """Return list of dicts — one per calendar day in the period.

        Each dict keys:
            date, date_str, weekday_name, is_weekend,
            is_holiday, holiday_name,
            check_in_str, check_out_str,
            worked_hours (float), worked_hours_str,
            status: 'ok' | 'missing_exit' | 'absent' | 'weekend' | 'holiday'

        Holiday logic: if a weekday has no attendance and falls in the
        attendance_report.holidays config param, it's marked 'holiday' (not 'absent').
        If attendance IS recorded on a holiday, actual data takes precedence.
        """
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return []

        # Fetch all attendance records for the employee within the period.
        # check_in stored in UTC; we compare against period boundaries in UTC
        # covering full local days (VET = UTC-4, so UTC range adds 4h buffer).
        period_end = self.date_to + timedelta(days=1)
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', f'{self.date_from} 00:00:00'),
            ('check_in', '<', f'{period_end} 04:00:00'),
        ]
        attendances = self.env['hr.attendance'].search(domain, order='check_in asc')

        # Group by local (VET) date
        by_date = defaultdict(list)
        for att in attendances:
            local_date = (att.check_in + VET_OFFSET).date()
            by_date[local_date].append(att)

        holiday_map = self._get_holiday_dates()
        is_special = self.employee_id.id in self._get_special_schedule_employees()

        result = []
        current = self.date_from
        while current <= self.date_to:
            weekday = current.weekday()
            is_weekend = weekday >= 5

            entry = {
                'date': current,
                'date_str': current.strftime('%d/%m'),
                'weekday_name': DAYS_ES.get(weekday, ''),
                'is_weekend': is_weekend,
                'is_holiday': False,
                'holiday_name': '',
                'check_in_str': '─',
                'check_out_str': '─',
                'worked_hours': 0.0,
                'worked_hours_str': '─',
                'status': 'weekend' if is_weekend else 'absent',
            }

            # Show actual attendance if present.
            # Special employees: weekends also shown (they work non-standard days).
            # Regular employees: weekends always stay '─ No hábil'.
            if current in by_date and (not is_weekend or is_special):
                recs = by_date[current]
                first_in_local = recs[0].check_in + VET_OFFSET
                last_rec = recs[-1]
                total_hours = sum(r.worked_hours for r in recs)
                entry['check_in_str'] = first_in_local.strftime('%H:%M')
                entry['worked_hours'] = total_hours
                if last_rec.check_out:
                    last_out_local = last_rec.check_out + VET_OFFSET
                    entry['check_out_str'] = last_out_local.strftime('%H:%M')
                    entry['worked_hours_str'] = f'{total_hours:.2f}h'
                    entry['status'] = 'ok'
                else:
                    entry['status'] = 'missing_exit'
            elif is_weekend:
                pass  # stays 'weekend'
            elif current in holiday_map:
                entry['status'] = 'holiday'
                entry['is_holiday'] = True
                entry['holiday_name'] = holiday_map[current]
            elif is_special:
                # Weekday with no attendance for special employee → neutral day off,
                # not an absence (rotating schedule may account for it)
                entry['status'] = 'dayoff'
            # else: stays 'absent'

            result.append(entry)
            current += timedelta(days=1)

        return result

    def _build_html_table(self):
        """Build the HTML attendance table for form view preview."""
        days = self.get_attendance_days()
        if not days:
            return '<p style="color:#666;font-family:Arial,sans-serif;padding:10px;">Sin registros de asistencia en este período.</p>'

        # Group consecutive days by ISO week number
        week_groups = []
        current_wk_days = []
        current_wk = None
        for day in days:
            wk = day['date'].isocalendar()[1]
            if current_wk is None:
                current_wk = wk
            if wk != current_wk:
                if current_wk_days:
                    week_groups.append(current_wk_days)
                current_wk_days = []
                current_wk = wk
            current_wk_days.append(day)
        if current_wk_days:
            week_groups.append(current_wk_days)

        parts = [
            '<div style="font-family:Arial,sans-serif;font-size:13px;">',
            '<table style="width:100%;border-collapse:collapse;">',
            '<thead>',
            '<tr style="background:#1a2c5b;color:white;">',
            '<th style="padding:8px 10px;text-align:left;white-space:nowrap;">Fecha</th>',
            '<th style="padding:8px 10px;text-align:left;">Día</th>',
            '<th style="padding:8px 10px;text-align:center;white-space:nowrap;">Entrada</th>',
            '<th style="padding:8px 10px;text-align:center;white-space:nowrap;">Salida</th>',
            '<th style="padding:8px 10px;text-align:center;white-space:nowrap;">Horas</th>',
            '<th style="padding:8px 10px;text-align:center;">Estado</th>',
            '</tr>',
            '</thead><tbody>',
        ]

        for wi, wk_days in enumerate(week_groups, 1):
            wk_start = wk_days[0]['date'].strftime('%d/%m')
            wk_end = wk_days[-1]['date'].strftime('%d/%m')
            wk_hours = sum(d['worked_hours'] for d in wk_days)

            parts.append(
                f'<tr><td colspan="6" style="background:#2471a3;color:white;'
                f'padding:6px 10px;font-weight:600;font-size:12px;">'
                f'Semana {wi} &mdash; {wk_start} al {wk_end}</td></tr>'
            )

            for day in wk_days:
                icon, bg, color = STATUS_CFG.get(day['status'], ('─', '#fff', '#333'))
                if day.get('is_holiday'):
                    parts.append(
                        f'<tr style="background:{bg};">'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #c8ddf0;color:{color};white-space:nowrap;font-size:13px;">{day["date_str"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #c8ddf0;color:{color};font-size:13px;">{day["weekday_name"]}</td>'
                        f'<td colspan="3" style="padding:7px 10px;border-bottom:1px solid #c8ddf0;text-align:center;color:#2471a3;font-size:13px;font-style:italic;">📅 {day["holiday_name"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #c8ddf0;text-align:center;font-size:15px;">{icon}</td>'
                        '</tr>'
                    )
                elif day['status'] == 'dayoff':
                    parts.append(
                        f'<tr style="background:{bg};">'
                        f'<td style="padding:6px 10px;border-bottom:1px solid #e0e8f4;color:{color};white-space:nowrap;font-size:13px;">{day["date_str"]}</td>'
                        f'<td style="padding:6px 10px;border-bottom:1px solid #e0e8f4;color:{color};font-size:13px;">{day["weekday_name"]}</td>'
                        f'<td colspan="3" style="padding:6px 10px;border-bottom:1px solid #e0e8f4;text-align:center;color:{color};font-size:12px;font-style:italic;">Día libre</td>'
                        f'<td style="padding:6px 10px;border-bottom:1px solid #e0e8f4;text-align:center;color:{color};font-size:13px;">{icon}</td>'
                        '</tr>'
                    )
                else:
                    parts.append(
                        f'<tr style="background:{bg};">'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;color:{color};white-space:nowrap;">{day["date_str"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;color:{color};">{day["weekday_name"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;text-align:center;color:{color};">{day["check_in_str"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;text-align:center;color:{color};">{day["check_out_str"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;text-align:center;color:{color};">{day["worked_hours_str"]}</td>'
                        f'<td style="padding:7px 10px;border-bottom:1px solid #e8e8e8;text-align:center;font-size:15px;">{icon}</td>'
                        '</tr>'
                    )

            parts.append(
                f'<tr style="background:#e8f0fe;">'
                f'<td colspan="4" style="padding:7px 10px;text-align:right;'
                f'font-weight:600;color:#1a2c5b;font-size:12px;">Sub-total Semana {wi}:</td>'
                f'<td style="padding:7px 10px;text-align:center;font-weight:700;color:#1a2c5b;">'
                f'{wk_hours:.2f}h</td>'
                f'<td></td></tr>'
            )

        parts.append('</tbody></table>')

        # Legend
        parts.append(
            '<div style="margin-top:12px;padding:10px;background:#f8f9fa;'
            'border-radius:4px;font-size:12px;color:#555;">'
            '<strong>Leyenda:</strong>&nbsp;&nbsp;'
            '✅ Registro completo &nbsp;|&nbsp; '
            '⚠️ Sin salida registrada &nbsp;|&nbsp; '
            '❌ Sin registro (ausencia) &nbsp;|&nbsp; '
            '📅 Feriado oficial &nbsp;|&nbsp; '
            '─ Día libre (horario especial)'
            '</div>'
        )
        parts.append('</div>')

        return ''.join(parts)

    # -------------------------------------------------------------------------
    # Phase 2 — Email + ACK methods
    # -------------------------------------------------------------------------

    _MONTH_NAMES = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
    ]

    def get_period_label(self):
        """Human-readable period string used in email header/subject."""
        self.ensure_one()
        month_name = self._MONTH_NAMES[self.month - 1] if 1 <= self.month <= 12 else str(self.month)
        q_label = '1ra' if self.quincena == '1' else '2da'
        date_range = (
            f"{self.date_from.strftime('%d')} al "
            f"{self.date_to.strftime('%d')} de {month_name} {self.year}"
        )
        return f"{q_label} Quincena: {date_range}"

    def get_attendance_weeks(self):
        """Return attendance days grouped by week — used by email QWeb template."""
        self.ensure_one()
        days = self.get_attendance_days()
        weeks = []
        current_days = []
        current_wk = None

        for day in days:
            wk = day['date'].isocalendar()[1]
            if current_wk is None:
                current_wk = wk
            if wk != current_wk:
                if current_days:
                    weeks.append(current_days)
                current_days = []
                current_wk = wk
            current_days.append(day)
        if current_days:
            weeks.append(current_days)

        result = []
        for i, wk_days in enumerate(weeks, 1):
            result.append({
                'week_num': i,
                'week_start': wk_days[0]['date'].strftime('%d/%m'),
                'week_end': wk_days[-1]['date'].strftime('%d/%m'),
                'week_hours': sum(d['worked_hours'] for d in wk_days),
                'week_hours_str': '%.2f' % sum(d['worked_hours'] for d in wk_days),
                'days': wk_days,
            })
        return result

    def get_status_info(self):
        """Return banner config dict for email template status section."""
        self.ensure_one()
        if self.employee_id.id in self._get_special_schedule_employees():
            return {
                'status': 'special',
                'icon': '⭐',
                'bg': '#e8f4f8',
                'border': '#2471a3',
                'color': '#1a2c5b',
                'message': (
                    'Este empleado tiene un horario especial (mantenimiento/seguridad). '
                    'Los fines de semana trabajados están incluidos en el resumen. '
                    'La asistencia es revisada directamente por Recursos Humanos.'
                ),
            }
        if self.absent_days == 0 and self.missing_exit_days == 0:
            return {
                'status': 'ok',
                'icon': '✅',
                'bg': '#d4edda',
                'border': '#28a745',
                'color': '#155724',
                'message': (
                    'Su asistencia quincenal está conforme. '
                    'No se detectaron incidencias en este período.'
                ),
            }
        elif self.absent_days == 0:
            s = 's' if self.missing_exit_days > 1 else ''
            return {
                'status': 'warning',
                'icon': '⚠️',
                'bg': '#fff3cd',
                'border': '#ffc107',
                'color': '#856404',
                'message': (
                    f'Su registro presenta {self.missing_exit_days} salida{s} sin registrar. '
                    'Si algún registro es incorrecto comuníquese con RRHH para su corrección.'
                ),
            }
        else:
            total = self.absent_days + self.missing_exit_days
            return {
                'status': 'danger',
                'icon': '❌',
                'bg': '#fde8e8',
                'border': '#dc3545',
                'color': '#721c24',
                'message': (
                    f'Su registro actual presenta un total de {total} incidencia{"s" if total > 1 else ""} '
                    f'({self.absent_days} ausencia{"s" if self.absent_days != 1 else ""}'
                    + (f' y {self.missing_exit_days} salida{"s" if self.missing_exit_days != 1 else ""} sin registrar' if self.missing_exit_days else '')
                    + '). '
                    'Le recordamos que las inasistencias no justificadas o que presenten inconsistencias '
                    'sin informar podrían generar descuentos automáticos. '
                    'Este nuevo mecanismo de control entrará en vigor de manera efectiva '
                    'a partir del 1 de junio de 2026.'
                ),
            }

    def _get_ack_url(self):
        """Acknowledgment URL embedded in the email body."""
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return f"{base}/attendance-ack/{self.ack_token}"

    def _get_fix_url(self):
        """Correction request URL — same token, different route."""
        self.ensure_one()
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return f"{base}/attendance-fix/{self.ack_token}"

    def action_send_email(self):
        self.ensure_one()
        if not self.employee_id.work_email:
            raise UserError(_("El empleado no tiene correo de trabajo configurado."))
        template = self.env.ref(
            'ueipab_attendance_report.email_template_attendance_report',
            raise_if_not_found=True,
        )
        template.send_mail(self.id, force_send=True)
        vals = {'sent_date': fields.Datetime.now()}
        if not self.is_historical:
            vals['state'] = 'sent'
        self.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Correo enviado'),
                'message': _('Reporte enviado a %s') % self.employee_id.work_email,
                'type': 'success',
                'sticky': False,
            },
        }
