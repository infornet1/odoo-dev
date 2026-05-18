from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StartConversationWizard(models.TransientModel):
    _name = 'ai.agent.start.conversation.wizard'
    _description = 'Start AI Agent Conversation'

    skill_id = fields.Many2one('ai.agent.skill', required=True, string='Skill')
    partner_id = fields.Many2one('res.partner', required=True, string='Contacto')
    phone = fields.Char('Telefono WhatsApp', required=True)
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

    def _prepare_conversation_vals(self):
        wa_service = self.env['ai.agent.whatsapp.service']
        normalized_phone = wa_service._normalize_phone(self.phone)

        # Guard: existing active conversation
        existing = self.env['ai.agent.conversation'].search([
            ('partner_id', '=', self.partner_id.id),
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
            'partner_id': self.partner_id.id,
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
