# -*- coding: utf-8 -*-
"""
ARC Employee Certificate

Permanent record per (employee, fiscal year) tracking:
  - When the ARC was sent and to which email
  - Whether the employee acknowledged receipt via the portal link
"""
import uuid

from odoo import api, fields, models


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

    sent_date = fields.Datetime(string='Fecha de Envío', readonly=True)
    sent_email = fields.Char(string='Correo Destino', readonly=True)

    is_acknowledged = fields.Boolean(
        string='Recibido', default=False, tracking=True,
    )
    acknowledged_date = fields.Datetime(string='Fecha de Confirmación', readonly=True)
    acknowledged_ip = fields.Char(string='IP', readonly=True)
    acknowledged_user_agent = fields.Char(string='Dispositivo', readonly=True)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = 'ARC %s — %s' % (rec.year, rec.employee_id.name or '')

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

    def action_reset_acknowledgment(self):
        self.write({
            'is_acknowledged': False,
            'acknowledged_date': False,
            'acknowledged_ip': False,
            'acknowledged_user_agent': False,
        })
