# -*- coding: utf-8 -*-
"""
ARC Annual Withholding Certificate Wizard (Stage 1)

Standalone wizard accessible from Payroll > Reports.
Allows HR to:
  1. Select fiscal year and employees.
  2. Preview a multi-employee PDF.
  3. Send Stage 1 notice emails in batch (no PDF attached).

Two-stage workflow:
  Stage 1 (Wizard): notice email with portal confirmation link. Cert state → notified.
  Stage 2 (Portal): employee clicks confirm → signed PDF generated (employer seal +
                    digital ack block) and emailed automatically. Cert state → acknowledged.
"""

import logging
from datetime import date, datetime

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

REPORT_REF = 'ueipab_payroll_enhancements.action_report_arc_annual'


class ArcReportWizard(models.TransientModel):
    """Wizard for generating and distributing ARC annual certificates."""

    _name = 'arc.report.wizard'
    _description = 'Comprobante ARC - Asistente'

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------

    year = fields.Char(
        string='Ejercicio Fiscal',
        required=True,
        default=lambda self: str(date.today().year - 1),
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Filtrar por empleado(s)',
        help='Deje vacío para incluir todos los empleados con contrato activo. '
             'Seleccione uno o más para limitar el reporte.',
    )

    employee_count = fields.Integer(
        string='Empleados seleccionados',
        compute='_compute_employee_count',
    )

    email_template_id = fields.Many2one(
        'mail.template',
        string='Plantilla de Correo',
        domain="[('model', '=', 'hr.employee')]",
        help='Plantilla usada para el cuerpo del correo. El PDF ARC se adjunta automáticamente.',
    )

    state = fields.Selection([
        ('select', 'Seleccionar'),
        ('sending', 'Enviando'),
        ('done', 'Completado'),
    ], default='select', string='Estado')

    # Progress counters
    total_count = fields.Integer(string='Total', readonly=True, default=0)
    processed_count = fields.Integer(string='Procesados', readonly=True, default=0)
    sent_count = fields.Integer(string='Enviados', readonly=True, default=0)
    failed_count = fields.Integer(string='Fallidos', readonly=True, default=0)
    no_email_count = fields.Integer(string='Sin Email', readonly=True, default=0)
    progress_percent = fields.Float(string='Progreso %', compute='_compute_progress')
    current_employee = fields.Char(string='Empleado actual', readonly=True)

    result_ids = fields.One2many(
        'arc.report.wizard.result',
        'wizard_id',
        string='Resultados',
    )

    # ------------------------------------------------------------------
    # Computed
    # ------------------------------------------------------------------

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for wiz in self:
            wiz.employee_count = len(wiz._get_selected_employees())

    @api.depends('processed_count', 'total_count')
    def _compute_progress(self):
        for wiz in self:
            wiz.progress_percent = (
                (wiz.processed_count / wiz.total_count * 100)
                if wiz.total_count else 0.0
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_employees(self):
        if self.employee_ids:
            return self.employee_ids
        # Default: all employees with an active (open) contract
        contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        return contracts.mapped('employee_id')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_preview_pdf(self):
        """Open a multi-employee PDF preview (one page per employee)."""
        self.ensure_one()
        employees = self._get_selected_employees()
        if not employees:
            raise UserError(_('No hay empleados seleccionados.'))

        data = {
            'employee_ids': employees.ids,
            'year': int(self.year),
        }
        report = self.env.ref(REPORT_REF)
        return report.report_action(docids=employees.ids, data=data)

    def action_start_sending(self):
        """Initialise result lines and transition to sending state."""
        self.ensure_one()
        if not self.email_template_id:
            raise UserError(_('Seleccione una plantilla de correo antes de enviar.'))

        employees = self._get_selected_employees()
        if not employees:
            raise UserError(_('No hay empleados seleccionados.'))

        # Create one result record per employee
        result_vals = []
        for emp in employees:
            result_vals.append({
                'wizard_id': self.id,
                'employee_id': emp.id,
                'employee_name': emp.name,
                'employee_email': emp.work_email or '',
                'has_email': bool(emp.work_email),
                'status': 'pending',
            })
        self.env['arc.report.wizard.result'].create(result_vals)

        self.write({
            'state': 'sending',
            'total_count': len(employees),
            'processed_count': 0,
            'sent_count': 0,
            'failed_count': 0,
            'no_email_count': 0,
        })
        return self.action_process_all()

    def action_process_all(self):
        """Stage 1: send notice email to each pending employee, committing after each.

        No PDF is attached at this stage. The signed PDF (with employer seal and
        digital acknowledgment block) is generated and emailed automatically in
        Stage 2 when the employee confirms receipt via the portal link.
        """
        self.ensure_one()

        for result in self.result_ids.filtered(lambda r: r.status == 'pending'):
            employee = result.employee_id
            self.current_employee = employee.name
            result.status = 'sending'
            self.env.cr.commit()

            if not result.has_email:
                result.write({'status': 'no_email', 'error_message': 'Sin dirección de email'})
                self.no_email_count += 1
            else:
                try:
                    # 1. Create/update acknowledgment certificate and get ack URL
                    cert = self.env['arc.employee.certificate'].sudo().get_or_create(
                        employee.id, self.year
                    )
                    cert.sudo().write({
                        'sent_date': datetime.utcnow(),
                        'sent_email': result.employee_email,
                        'state': 'notified',
                    })
                    ack_url = cert._get_ack_url()

                    # 2. Render template fields individually (Odoo 17 API)
                    tmpl = self.email_template_id
                    subject   = tmpl._render_field('subject',   [employee.id])[employee.id]
                    body_html = tmpl._render_field('body_html', [employee.id])[employee.id]
                    email_from = tmpl._render_field('email_from', [employee.id])[employee.id]

                    # 3. Compute ARC data and build summary table
                    arc_summary = self._build_arc_summary_html(employee, int(self.year))

                    # 4. Inject ARC summary + acknowledgment button into email body.
                    # Stage 1 notice: no PDF — the signed PDF arrives in Stage 2
                    # after the employee confirms via the portal link below.
                    ack_block = Markup('''
                        <div style="text-align:center;margin:28px 0 10px;">
                            <a href="%s"
                               style="display:inline-block;background:linear-gradient(135deg,#1a237e,#283593);
                                      color:white;padding:14px 32px;border-radius:8px;font-size:15px;
                                      font-weight:bold;text-decoration:none;letter-spacing:0.3px;">
                                &#x2705; Confirmar Recepci&#xF3;n del ARC
                            </a>
                            <p style="font-size:11px;color:#999;margin-top:8px;">
                                &#x1F512; Al confirmar recibir&#xe1; el PDF firmado con sello patronal.
                            </p>
                        </div>''') % ack_url
                    body_with_ack = (body_html or Markup('')) + arc_summary + ack_block

                    # 4. Send Stage 1 notice (no PDF attachment)
                    mail = self.env['mail.mail'].sudo().create({
                        'subject': subject or 'Comprobante ARC %s' % self.year,
                        'email_from': email_from or '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
                        'email_to': result.employee_email,
                        'email_cc': 'recursoshumanos@ueipab.edu.ve',
                        'body_html': body_with_ack,
                    })
                    mail.sudo().send()

                    result.write({'status': 'sent'})
                    self.sent_count += 1

                except Exception as exc:
                    _logger.exception('ARC email failed for employee %s', employee.name)
                    result.write({'status': 'error', 'error_message': str(exc)[:250]})
                    self.failed_count += 1

            self.processed_count += 1
            self.env.cr.commit()

        self.write({'state': 'done', 'current_employee': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


    def _build_arc_summary_html(self, employee, year):
        """Build an HTML ARC summary table for inclusion in the Stage 1 email."""
        arc_model = self.env['report.ueipab_payroll_enhancements.arc_annual_report']
        data = arc_model._compute_employee_arc(employee, year)
        months = data.get('months', [])
        totals = data.get('totals', {})
        contract = data.get('contract')
        ari_pct = (getattr(contract, 'ueipab_ari_withholding_rate', 0.0) or 0.0) if contract else 0.0
        cedula = employee.identification_id or employee.ssnid or 'N/D'

        def fmt(val):
            return '{:,.2f}'.format(val or 0.0)

        # Month rows — only non-empty months
        rows_html = ''
        for i, m in enumerate(months):
            if m.get('is_empty'):
                continue
            bg = '#f5f5f5' if i % 2 else '#ffffff'
            rows_html += (
                '<tr style="background:%s;">'
                '<td style="padding:5px 8px;border:1px solid #ddd;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;">%s</td>'
                '<td style="padding:5px 8px;border:1px solid #ddd;text-align:right;font-weight:bold;">%s</td>'
                '</tr>'
            ) % (
                bg, m.get('month_name', ''),
                fmt(m.get('gross_ves')), fmt(m.get('sso_ves')),
                fmt(m.get('faov_ves')), fmt(m.get('paro_ves')),
                fmt(m.get('net_taxable_ves')), fmt(m.get('ari_ves')),
            )

        html = Markup(
            '<div style="margin:24px 0;font-family:Arial,sans-serif;font-size:12px;">'
            '<table style="width:100%;border-collapse:collapse;margin-bottom:12px;'
            'background:#e8eaf6;border-radius:6px;overflow:hidden;">'
            '<tr><td style="padding:8px 14px;color:#1a237e;font-weight:bold;font-size:13px;">'
            'Resumen ARC &#8212; Ejercicio Fiscal {year}'
            '</td></tr>'
            '<tr><td style="padding:4px 14px 10px;color:#555;">'
            '<strong>Empleado:</strong> {name} &nbsp;&nbsp;'
            '<strong>C&#xe9;dula:</strong> {cedula} &nbsp;&nbsp;'
            '<strong>Tasa AR-I Retenida:</strong> {ari_pct}%'
            '</td></tr>'
            '</table>'
            '<table style="width:100%;border-collapse:collapse;font-size:11px;">'
            '<thead><tr style="background:#1a237e;color:white;text-align:center;">'
            '<th style="padding:6px 8px;border:1px solid #aaa;">Mes</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">Remun. Gravable (Bs.)</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">SSO (Bs.)</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">FAOV (Bs.)</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">PARO (Bs.)</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">Base Imponible (Bs.)</th>'
            '<th style="padding:6px 8px;border:1px solid #aaa;">ISLR Retenido (Bs.)</th>'
            '</tr></thead>'
            '<tbody>{rows}</tbody>'
            '<tfoot><tr style="background:#1a237e;color:white;font-weight:bold;text-align:right;">'
            '<td style="padding:6px 8px;border:1px solid #aaa;text-align:left;">TOTAL</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_gross}</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_sso}</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_faov}</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_paro}</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_net}</td>'
            '<td style="padding:6px 8px;border:1px solid #aaa;">{t_ari}</td>'
            '</tr></tfoot>'
            '</table>'
            '<p style="font-size:10px;color:#888;margin-top:6px;">'
            '* Todas las cifras en Bol&#xed;vares (Bs.) al tipo de cambio BCV de cada per&#xed;odo. '
            'Base Imponible = Remun. Gravable &#8722; SSO &#8722; FAOV &#8722; PARO.'
            '</p></div>'
        ).format(
            year=year,
            name=employee.name,
            cedula=cedula,
            ari_pct='{:.1f}'.format(ari_pct),
            rows=Markup(rows_html),
            t_gross=fmt(totals.get('gross_ves')),
            t_sso=fmt(totals.get('sso_ves')),
            t_faov=fmt(totals.get('faov_ves')),
            t_paro=fmt(totals.get('paro_ves')),
            t_net=fmt(totals.get('net_taxable_ves')),
            t_ari=fmt(totals.get('ari_ves')),
        )
        return html


class ArcReportWizardResult(models.TransientModel):
    """Per-employee result row for the ARC batch email wizard."""

    _name = 'arc.report.wizard.result'
    _description = 'ARC Wizard - Resultado por Empleado'

    wizard_id = fields.Many2one('arc.report.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=True)
    employee_name = fields.Char(string='Nombre', readonly=True)
    employee_email = fields.Char(string='Correo', readonly=True)
    has_email = fields.Boolean(readonly=True)

    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('sending', 'Enviando'),
        ('sent', 'Enviado'),
        ('no_email', 'Sin Email'),
        ('error', 'Error'),
    ], string='Estado', default='pending')

    error_message = fields.Char(string='Detalle del error', readonly=True)

    status_icon = fields.Char(string='', compute='_compute_status_icon')

    @api.depends('status')
    def _compute_status_icon(self):
        icons = {
            'pending': '⏳',
            'sending': '📤',
            'sent': '✅',
            'no_email': '⚠️',
            'error': '❌',
        }
        for rec in self:
            rec.status_icon = icons.get(rec.status, '')
