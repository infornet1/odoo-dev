import re as _re

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StartConversationWizard(models.TransientModel):
    _name = 'ai.agent.start.conversation.wizard'
    _description = 'Start AI Agent Conversation'

    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
    ], string='Canal', default='whatsapp', required=True)
    skill_id = fields.Many2one('ai.agent.skill', required=True, string='Skill')
    partner_id = fields.Many2one(
        'res.partner', string='Contacto',
        help='Opcional para WhatsApp (se crea un contacto provisional si se deja vacío). '
             'Obligatorio para enviar invitación de Telegram.')
    phone = fields.Char('Teléfono WhatsApp', required=True)
    initial_message = fields.Text(
        'Mensaje del representante',
        help='Opcional: pega aquí el mensaje que el representante envió por otro canal '
             '(correo, WA distinto, presencial). Glenda lo procesará al iniciar, '
             'saltándose el saludo genérico.')
    source_model = fields.Char('Modelo Origen')
    source_id = fields.Integer('ID Origen')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.env.context.get('default_phone'):
                self.phone = self.partner_id.mobile or self.partner_id.phone or ''

    def _get_or_create_placeholder_partner(self, normalized_phone):
        """Find an existing partner for this phone or create a placeholder lead."""
        all_digits = _re.sub(r'[^\d]', '', normalized_phone)
        candidates = []
        if len(all_digits) == 12 and all_digits.startswith('58'):
            local10 = all_digits[2:]
            area, num = local10[:3], local10[3:]
            candidates = [
                f'+58 {area} {num}',
                f'0{local10}',
                normalized_phone,
            ]
        else:
            candidates = [normalized_phone]

        _NO_PLACEHOLDER = ('name', 'not like', 'Consulta WhatsApp')
        partner = None
        for cand in candidates:
            partner = self.env['res.partner'].sudo().search(
                ['&', _NO_PLACEHOLDER, '|', ('phone', '=', cand), ('mobile', '=', cand)],
                limit=1,
            )
            if partner:
                break

        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': f'Consulta WhatsApp {normalized_phone}',
                'mobile': normalized_phone,
                'customer_rank': 1,
            })
        return partner

    def _prepare_conversation_vals(self):
        wa_service = self.env['ai.agent.whatsapp.service']
        normalized_phone = wa_service._normalize_phone(self.phone)

        # Resolve partner: use selected contact or auto-create a placeholder lead
        partner = self.partner_id or self._get_or_create_placeholder_partner(normalized_phone)

        # Guard: existing active conversation for this partner+skill
        existing = self.env['ai.agent.conversation'].search([
            ('partner_id', '=', partner.id),
            ('skill_id', '=', self.skill_id.id),
            ('state', 'in', ('draft', 'active', 'waiting')),
        ], limit=1)
        if existing:
            if not existing.escalation_date:
                raise UserError(_(
                    "Ya existe una conversacion activa para este contacto y skill (%s). "
                    "Cierre o resuelva la conversacion existente primero."
                ) % existing.name)
            existing.write({'state': 'failed'})

        # Guard: duplicate phone
        phone_dup = self.env['ai.agent.conversation'].search([
            ('phone', '=', normalized_phone),
            ('state', 'in', ('draft', 'active', 'waiting')),
            ('id', '!=', existing.id if existing else 0),
        ], limit=1)
        if phone_dup:
            raise UserError(_(
                "Ya existe una conversacion activa con este numero (%s) para %s. "
                "Cierre o resuelva primero."
            ) % (normalized_phone, phone_dup.partner_id.name))

        return {
            'skill_id': self.skill_id.id,
            'partner_id': partner.id,
            'phone': normalized_phone,
            'initial_message': self.initial_message.strip() if self.initial_message else False,
            'source_model': self.source_model or '',
            'source_id': self.source_id or 0,
        }

    def _link_bounce_log(self, conversation):
        if self.source_model == 'mail.bounce.log' and self.source_id:
            bounce_log = self.env['mail.bounce.log'].browse(self.source_id)
            if bounce_log.exists():
                bounce_log.write({
                    'ai_conversation_id': conversation.id,
                    'whatsapp_contacted': True,
                    'whatsapp_contact_date': fields.Datetime.now(),
                })

    def _open_conversation(self, conversation):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Conversacion AI',
            'res_model': 'ai.agent.conversation',
            'res_id': conversation.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_save_draft(self):
        """Create conversation in draft state and open form for review — no WA sent."""
        self.ensure_one()
        if not self.phone:
            raise UserError(_("Debe indicar un numero de telefono WhatsApp."))
        vals = self._prepare_conversation_vals()
        conversation = self.env['ai.agent.conversation'].create(vals)
        self._link_bounce_log(conversation)
        if self.initial_message:
            conversation.message_post(body=_(
                "📋 Borrador creado. Mensaje del representante guardado. "
                "Revisa los datos y haz clic en 'Iniciar Conversacion' cuando estés listo."
            ))
        return self._open_conversation(conversation)

    def action_start(self):
        """Create conversation and fire immediately (send greeting or process initial_message)."""
        self.ensure_one()
        if not self.phone:
            raise UserError(_("Debe indicar un numero de telefono WhatsApp."))
        vals = self._prepare_conversation_vals()
        conversation = self.env['ai.agent.conversation'].create(vals)
        self._link_bounce_log(conversation)
        conversation.action_start()
        return self._open_conversation(conversation)

    def action_send_telegram_invite(self):
        """Send the parent a WhatsApp message with the Telegram bot deep-link."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_("Seleccione un contacto para enviar la invitación de Telegram."))
        if not self.phone:
            raise UserError(_("El contacto no tiene teléfono WhatsApp registrado."))

        partner = self.partner_id
        if partner.telegram_chat_id:
            raise UserError(_(
                "%s ya tiene Telegram vinculado. No es necesario enviar la invitación."
            ) % partner.name)

        icp = self.env['ir.config_parameter'].sudo()

        # Reuse existing opt-in token or create one
        ack = self.env['partner.communication.ack'].sudo().search([
            ('notice_key', '=', 'telegram_optin_glenda'),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not ack:
            ack = self.env['partner.communication.ack'].sudo().create({
                'notice_key': 'telegram_optin_glenda',
                'notice_label': 'Invitación Telegram Glenda',
                'partner_id': partner.id,
                'partner_phone': self.phone,
            })

        bot_username = icp.get_param('ai_agent.telegram_bot_username', 'GlendaUeipabBot')
        deep_link = f"https://t.me/{bot_username}?start=FAM_{ack.token}"

        first_name = partner.name.split()[0] if partner.name else partner.name
        msg = (
            f"📲 ¡Hola, {first_name}! Te invitamos a escribirle a Glenda, "
            f"el asistente virtual de UEIPAB, también por Telegram.\n\n"
            f"Es instantáneo, sin la restricción de 24 horas de WhatsApp y "
            f"completamente gratuito.\n\n"
            f"Toca este enlace para vincular tu cuenta:\n{deep_link}\n\n"
            f"Solo pulsa *Iniciar* y Glenda te recibirá de inmediato. 🤖"
        )

        wa_service = self.env['ai.agent.whatsapp.service']
        wa_service.send_message(self.phone, msg)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invitación enviada'),
                'message': _('Invitación de Telegram enviada a %s por WhatsApp.') % partner.name,
                'type': 'success',
                'sticky': False,
            },
        }
