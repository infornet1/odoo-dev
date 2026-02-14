# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Institutional email — must NEVER be modified by bounce resolution
PROTECTED_EMAILS = {'todalacomunidad@ueipab.edu.ve'}


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
        ('akdemia_pending', 'Pendiente Akdemia'),
        ('resolved', 'Resuelto'),
    ], default='pending', string='Estado', tracking=True)

    # Akdemia tracking
    in_akdemia = fields.Boolean(
        'Email en Akdemia', default=False, tracking=True,
        help='Indica si el email rebotado fue encontrado en la plataforma Akdemia')
    akdemia_confirmed_date = fields.Datetime(
        'Fecha Confirmacion Akdemia', readonly=True)
    akdemia_confirmed_by = fields.Many2one(
        'res.users', string='Confirmado por', readonly=True)
    akdemia_family_emails = fields.Text(
        'Contexto Familiar Akdemia',
        help='JSON con informacion de correos de otros familiares registrados en Akdemia. '
             'Actualizado automaticamente por el Resolution Bridge.')

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

    def _remove_email_from_field(self, record, field_name, email_to_remove):
        """Remove a specific email from a multi-email field (;-separated)."""
        current = (record[field_name] or '').strip()
        if not current:
            return
        emails = [e.strip() for e in current.split(';') if e.strip()]
        remaining = [e for e in emails if e.lower() != email_to_remove.strip().lower()]
        record[field_name] = ';'.join(remaining)

    def _resolve_record(self, email_to_add):
        """Common resolution logic for both restore and apply actions.

        Updates: res.partner, linked mailing.contact (if any), and ALL
        mailing.contact records that match the bounced email by search.

        Target state depends on in_akdemia flag:
        - in_akdemia=True + new email → akdemia_pending (Akdemia needs manual update)
        - in_akdemia=True + restore (same email) → resolved (no Akdemia change needed)
        - in_akdemia=False → resolved
        """
        self.ensure_one()
        if self.state in ('resolved', 'akdemia_pending'):
            raise UserError(_('Este registro ya fue resuelto o esta pendiente de Akdemia.'))

        # Update partner
        if self.partner_id:
            is_new_email = email_to_add.strip().lower() != (self.bounced_email or '').strip().lower()
            if is_new_email:
                # New email: remove bounced + add new
                self._remove_email_from_field(self.partner_id, 'email', self.bounced_email)
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

        # Update directly linked mailing contact (if any)
        if self.mailing_contact_id:
            self._append_email_to_field(
                self.mailing_contact_id, 'email', email_to_add)

        # Search and update ALL mailing.contact records with the bounced email
        self._sync_mailing_contacts(email_to_add)

        # Determine target state: akdemia_pending if email changed and in Akdemia
        is_new_email = email_to_add.strip().lower() != (self.bounced_email or '').strip().lower()
        if self.in_akdemia and is_new_email:
            target_state = 'akdemia_pending'
        else:
            target_state = 'resolved'

        self.write({
            'state': target_state,
            'resolved_date': fields.Datetime.now(),
            'resolved_by': self.env.uid,
        })

    def _sync_mailing_contacts(self, new_email):
        """Find all mailing.contact records with the bounced email and update them.

        For 'apply new email': replaces bounced email with new email.
        For 'restore original': re-adds the bounced email (no-op if already there).
        Skips protected institutional emails.
        """
        self.ensure_one()
        bounced = self.bounced_email
        if not bounced:
            return

        # Skip if bounced email is protected
        if bounced.strip().lower() in PROTECTED_EMAILS:
            return

        MailingContact = self.env['mailing.contact'].sudo()
        mc_records = MailingContact.search([('email', 'ilike', bounced)])

        if not mc_records:
            return

        is_new_email = new_email.strip().lower() != bounced.strip().lower()
        already_linked = self.mailing_contact_id.id if self.mailing_contact_id else False
        updated_ids = []

        for mc in mc_records:
            # Skip protected emails
            if mc.email and mc.email.strip().lower() in PROTECTED_EMAILS:
                continue
            # Skip if already handled above via direct link
            if mc.id == already_linked:
                continue

            # Verify the bounced email actually appears in this contact
            mc_emails = [e.strip().lower() for e in (mc.email or '').split(';') if e.strip()]
            if bounced.strip().lower() not in mc_emails:
                continue

            if is_new_email:
                # Replace bounced email with new one
                self._remove_email_from_field(mc, 'email', bounced)
                self._append_email_to_field(mc, 'email', new_email)
            else:
                # Restore: just ensure it's present (already there = no-op)
                self._append_email_to_field(mc, 'email', new_email)

            updated_ids.append(mc.id)

        if updated_ids:
            _logger.info(
                "Bounce log #%d: updated %d mailing.contact(s) %s: %s → %s",
                self.id, len(updated_ids), updated_ids, bounced, new_email)

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

    def action_confirm_akdemia(self):
        """Confirm that Akdemia has been updated with the new email."""
        self.ensure_one()
        if self.state != 'akdemia_pending':
            raise UserError(_(
                'Solo se puede confirmar desde estado Pendiente Akdemia.'))
        self.write({
            'state': 'resolved',
            'akdemia_confirmed_date': fields.Datetime.now(),
            'akdemia_confirmed_by': self.env.uid,
        })
        self.message_post(
            body=_(
                '<strong>Akdemia actualizado</strong><br/>'
                'El correo ha sido confirmado en la plataforma Akdemia.<br/>'
                'Confirmado por: %(user)s',
                user=self.env.user.name,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
