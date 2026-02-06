# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MailBounceLog(models.Model):
    _name = 'mail.bounce.log'
    _description = 'Email Bounce Log'
    _inherit = ['mail.thread']
    _order = 'bounce_date desc'

    # Core bounce info
    bounce_date = fields.Datetime(
        'Fecha de Rebote', default=fields.Datetime.now, required=True)
    bounced_email = fields.Char(
        'Email Rebotado', required=True, tracking=True)
    bounce_reason = fields.Selection([
        ('mailbox_full', 'Buzon Lleno'),
        ('invalid_address', 'Direccion Invalida'),
        ('domain_not_found', 'Dominio No Encontrado'),
        ('rejected', 'Rechazado por Servidor'),
        ('other', 'Otro'),
    ], string='Razon', tracking=True)
    bounce_detail = fields.Text('Detalle Tecnico')

    # Links to Odoo records
    partner_id = fields.Many2one(
        'res.partner', string='Contacto', index=True)
    mailing_contact_id = fields.Many2one(
        'mailing.contact', string='Contacto Mailing', index=True)
    partner_email = fields.Char(
        'Email Actual del Contacto', related='partner_id.email', readonly=True)

    # Resolution workflow
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('notified', 'Soporte Notificado'),
        ('contacted', 'Cliente Contactado'),
        ('resolved', 'Resuelto'),
    ], default='pending', string='Estado', tracking=True)

    # Resolution fields
    new_email = fields.Char('Email Nuevo')
    resolved_date = fields.Datetime('Fecha Resolucion', readonly=True)
    resolved_by = fields.Many2one(
        'res.users', string='Resuelto Por', readonly=True)

    # Source tracking
    freescout_conversation_id = fields.Integer('Freescout Conversation ID')
    freescout_url = fields.Char(
        'Freescout Link', compute='_compute_freescout_url', store=False)
    action_tier = fields.Selection([
        ('clean', 'Limpiado'),
        ('flag', 'Revision'),
        ('not_found', 'No Encontrado'),
    ], string='Accion del Script')

    # Future: WhatsApp agent fields
    whatsapp_contacted = fields.Boolean('Contactado por WhatsApp')
    whatsapp_contact_date = fields.Datetime('Fecha Contacto WhatsApp')

    _sql_constraints = [
        ('unique_freescout_bounce',
         'UNIQUE(freescout_conversation_id, bounced_email)',
         'Ya existe un registro de rebote para esta conversacion y email.'),
    ]

    @api.depends('freescout_conversation_id')
    def _compute_freescout_url(self):
        for rec in self:
            if rec.freescout_conversation_id:
                rec.freescout_url = (
                    f'https://freescout.ueipab.edu.ve/conversation/'
                    f'{rec.freescout_conversation_id}'
                )
            else:
                rec.freescout_url = False

    def _append_email_to_field(self, record, field_name, email):
        """Append an email to a multi-email field using ; separator."""
        current = (record[field_name] or '').strip()
        if current:
            emails = [e.strip() for e in current.split(';') if e.strip()]
            if email.strip().lower() not in [e.lower() for e in emails]:
                emails.append(email.strip())
            record[field_name] = ';'.join(emails)
        else:
            record[field_name] = email.strip()

    def _resolve_record(self, email_to_add):
        """Common resolution logic for both restore and apply actions."""
        self.ensure_one()
        if self.state == 'resolved':
            raise UserError(_('Este registro ya fue resuelto.'))

        # Update partner
        if self.partner_id:
            self._append_email_to_field(self.partner_id, 'email', email_to_add)
            self.partner_id.message_post(
                body=_(
                    '<strong>Bounce Log - Email actualizado</strong><br/>'
                    'Email agregado: <code>%(email)s</code><br/>'
                    'Bounce original: <code>%(bounced)s</code><br/>'
                    'Razon del rebote: %(reason)s<br/>'
                    'Resuelto por: %(user)s',
                    email=email_to_add,
                    bounced=self.bounced_email,
                    reason=dict(self._fields['bounce_reason'].selection).get(
                        self.bounce_reason, 'N/A'),
                    user=self.env.user.name,
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        # Update mailing contact
        if self.mailing_contact_id:
            self._append_email_to_field(
                self.mailing_contact_id, 'email', email_to_add)

        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now(),
            'resolved_by': self.env.uid,
        })

    def action_restore_original(self):
        """Re-add the original bounced email back to the contact."""
        self.ensure_one()
        self._resolve_record(self.bounced_email)

    def action_apply_new_email(self):
        """Apply a new email provided by the customer."""
        self.ensure_one()
        if not self.new_email:
            raise UserError(_(
                'Debe ingresar el email nuevo antes de aplicar.'))
        self._resolve_record(self.new_email)

    def action_mark_notified(self):
        """Mark as support team notified."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Solo se puede notificar desde estado Pendiente.'))
        self.state = 'notified'

    def action_mark_contacted(self):
        """Mark as customer contacted."""
        self.ensure_one()
        if self.state not in ('pending', 'notified'):
            raise UserError(_(
                'Solo se puede marcar contactado desde Pendiente o Notificado.'))
        self.state = 'contacted'
