# -*- coding: utf-8 -*-
"""
ARC Employee Certificate

Permanent record per (employee, fiscal year) tracking:
  - When the ARC was sent and to which email
  - Whether the employee acknowledged receipt via the portal link
  - Two-stage workflow: notified → acknowledged (signed PDF sent on confirm)
"""
import base64
import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ArcEmployeeCertificate(models.Model):
    """Tracks ARC delivery and employee acknowledgment per year."""

    _name = 'arc.employee.certificate'
    _description = 'ARC Employee Certificate'
    _order = 'year desc, employee_id'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', required=True, ondelete='cascade', index=True,
    )
    year = fields.Char(string='Ejercicio Fiscal', required=True)

    access_token = fields.Char(string='Token', copy=False, readonly=True)

    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('notified', 'Notificado'),
        ('acknowledged', 'Confirmado'),
    ], string='Estado', default='pending')

    sent_date = fields.Datetime(string='Fecha de Envío', readonly=True)
    sent_email = fields.Char(string='Correo Destino', readonly=True)

    is_acknowledged = fields.Boolean(
        string='Recibido', default=False,
    )
    acknowledged_date = fields.Datetime(string='Fecha de Confirmación', readonly=True)
    acknowledged_ip = fields.Char(string='IP', readonly=True)
    acknowledged_user_agent = fields.Char(string='Dispositivo', readonly=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)
    certificate_number = fields.Char(compute='_compute_certificate_number')

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'ARC %s — %s' % (rec.year, rec.employee_id.name or '')

    @api.depends('year')
    def _compute_certificate_number(self):
        for rec in self:
            rec.certificate_number = 'ARC-%s-%05d' % (rec.year or '0000', rec.id or 0)

    # ------------------------------------------------------------------

    @api.model
    def get_or_create(self, employee_id, year):
        """Return existing certificate or create a new one with a fresh token."""
        cert = self.search([
            ('employee_id', '=', employee_id),
            ('year', '=', str(year)),
        ], limit=1)
        if not cert:
            cert = self.create({
                'employee_id': employee_id,
                'year': str(year),
                'access_token': str(uuid.uuid4()),
            })
        elif not cert.access_token:
            cert.access_token = str(uuid.uuid4())
        return cert

    def _get_ack_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        db = self.env.cr.dbname
        # Route through /arc/ack/init/ which sets session.db before redirecting
        # to the actual auth='public' route. Needed for multi-database setups
        # where no active session exists (e.g. employee clicking from email).
        return '%s/arc/ack/init/%s/%s?db=%s' % (base_url, self.id, self.access_token, db)

    def action_send_final_pdf(self):
        """Stage 2: generate signed PDF (employer seal + digital ack block) and email to employee.

        Called automatically by the portal controller after the employee confirms receipt.
        The PDF is generated fresh so it includes the employer signature image and the
        employee's digital acknowledgment details (timestamp, IP, device).
        """
        self.ensure_one()
        employee = self.employee_id
        year = int(self.year)

        try:
            report_model = self.env['ir.actions.report']
            pdf_bytes, _ = report_model.sudo()._render_qweb_pdf(
                'ueipab_payroll_enhancements.arc_annual_report',
                res_ids=[employee.id],
                data={'employee_ids': [employee.id], 'year': year},
            )

            filename = 'ARC_%s_%s_Firmado.pdf' % (self.year, employee.name.replace(' ', '_'))
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_bytes).decode(),
                'mimetype': 'application/pdf',
                'res_model': self._name,
                'res_id': self.id,
            })

            tmpl = self.env.ref(
                'ueipab_payroll_enhancements.email_template_arc_final_pdf',
                raise_if_not_found=False,
            )
            if tmpl:
                # Render fields individually (same pattern as the Stage 1 wizard)
                # to avoid send_mail's internal pipeline stripping email_to.
                subject = tmpl._render_field('subject', [self.id])[self.id]
                body_html = tmpl._render_field('body_html', [self.id])[self.id]
                email_from = tmpl._render_field('email_from', [self.id])[self.id]
                email_to = self.sent_email or employee.work_email or ''
                mail = self.env['mail.mail'].sudo().create({
                    'subject': subject or 'ARC %s — PDF Firmado' % self.year,
                    'email_from': email_from or '"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>',
                    'email_to': email_to,
                    'email_cc': 'recursoshumanos@ueipab.edu.ve',
                    'body_html': body_html,
                    'attachment_ids': [(4, attachment.id)],
                })
                mail.sudo().send()
            else:
                _logger.warning('ARC final PDF template not found; skipping final email for cert %s', self.id)

        except Exception:
            _logger.exception('action_send_final_pdf failed for cert %s (employee %s)', self.id, employee.name)

    def action_reset_acknowledgment(self):
        self.write({
            'is_acknowledged': False,
            'acknowledged_date': False,
            'acknowledged_ip': False,
            'acknowledged_user_agent': False,
            'state': 'pending',
        })
