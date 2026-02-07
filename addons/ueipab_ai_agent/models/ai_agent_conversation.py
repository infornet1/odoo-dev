import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..skills import get_skill

_logger = logging.getLogger(__name__)


class AiAgentConversation(models.Model):
    _name = 'ai.agent.conversation'
    _description = 'AI Agent Conversation'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    skill_id = fields.Many2one('ai.agent.skill', required=True, string='Skill', ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Contacto', required=True)
    phone = fields.Char('Telefono WhatsApp', required=True)

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('waiting', 'Esperando Respuesta'),
        ('resolved', 'Resuelta'),
        ('timeout', 'Timeout'),
        ('failed', 'Fallida'),
    ], default='draft', tracking=True, string='Estado')

    # Source record (generic link)
    source_model = fields.Char('Modelo Origen')
    source_id = fields.Integer('ID Origen')

    # Agent Messages (not mail.thread message_ids)
    agent_message_ids = fields.One2many('ai.agent.message', 'conversation_id', string='Mensajes')
    turn_count = fields.Integer('Turnos', compute='_compute_turn_count')

    # Resolution
    resolved_date = fields.Datetime('Fecha Resolucion', readonly=True)
    resolution_summary = fields.Text('Resumen Resolucion')

    # WhatsApp tracking
    last_message_date = fields.Datetime('Ultimo Mensaje')
    last_sender = fields.Selection([('agent', 'Agente'), ('customer', 'Cliente')], string='Ultimo Remitente')

    @api.depends('skill_id.name', 'partner_id.name')
    def _compute_name(self):
        for rec in self:
            skill_name = rec.skill_id.name or 'AI'
            partner_name = rec.partner_id.name or 'Sin contacto'
            rec.name = f"{skill_name} - {partner_name}"

    def _compute_turn_count(self):
        for rec in self:
            rec.turn_count = len(rec.agent_message_ids.filtered(lambda m: m.direction == 'inbound'))

    def _get_conversation_history(self):
        """Format messages as Claude API conversation history."""
        self.ensure_one()
        messages = []
        for msg in self.agent_message_ids.sorted('timestamp'):
            role = 'assistant' if msg.direction == 'outbound' else 'user'
            messages.append({'role': role, 'content': msg.body})
        return messages

    def _is_dry_run(self):
        return self.env['ir.config_parameter'].sudo().get_param('ai_agent.dry_run', 'True').lower() == 'true'

    def action_start(self):
        """Send greeting message and activate conversation."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se puede iniciar una conversacion en estado Borrador."))

        skill_handler = get_skill(self.skill_id.code)
        if not skill_handler:
            raise UserError(_("No se encontro el handler para el skill '%s'.") % self.skill_id.code)

        # Get greeting from skill handler with context
        context = skill_handler.get_context(self)
        greeting = skill_handler.get_greeting(self, context)

        # Send via WhatsApp
        wa_service = self.env['ai.agent.whatsapp.service']
        dry_run = self._is_dry_run()

        if dry_run:
            _logger.info("DRY_RUN: Would send WhatsApp to %s: %s", self.phone, greeting[:100])
            wa_msg_id = 0
        else:
            result = wa_service.send_message(self.phone, greeting)
            wa_msg_id = result.get('message_id', 0)

        # Log message
        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'outbound',
            'body': greeting,
            'whatsapp_message_id': wa_msg_id,
        })

        self.write({
            'state': 'waiting',
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'agent',
        })

        self.message_post(body=_("Conversacion iniciada. Saludo enviado por WhatsApp%s.") % (
            " (DRY RUN)" if dry_run else ""
        ))

    def action_process_reply(self, message_text, wa_message_id=0):
        """Process an incoming customer reply using Claude AI."""
        self.ensure_one()
        if self.state not in ('waiting', 'active'):
            _logger.warning("Conversation %s: ignoring reply in state %s", self.id, self.state)
            return

        # Log inbound message
        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'inbound',
            'body': message_text,
            'whatsapp_message_id': wa_message_id,
        })

        self.write({
            'state': 'active',
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'customer',
        })

        # Check turn limit
        skill = self.skill_id
        if self.turn_count >= skill.max_turns:
            self.write({'state': 'failed'})
            self.message_post(body=_("Conversacion cerrada: se alcanzo el limite de %d turnos.") % skill.max_turns)
            return

        # Get skill handler
        skill_handler = get_skill(skill.code)
        if not skill_handler:
            _logger.error("No skill handler for code: %s", skill.code)
            return

        # Build conversation for Claude
        context = skill_handler.get_context(self)
        system_prompt = skill_handler.get_system_prompt(self, context)
        history = self._get_conversation_history()

        # Generate AI response
        dry_run = self._is_dry_run()
        claude_service = self.env['ai.agent.claude.service']

        if dry_run:
            ai_content = "[DRY_RUN] Respuesta simulada del AI"
            input_tokens = 0
            output_tokens = 0
            _logger.info("DRY_RUN: Would call Claude API for conversation %s", self.id)
        else:
            ai_result = claude_service.generate_response(
                system_prompt=system_prompt,
                messages=history,
                model=skill.model_name,
            )
            ai_content = ai_result['content']
            input_tokens = ai_result.get('input_tokens', 0)
            output_tokens = ai_result.get('output_tokens', 0)

        # Let skill handler process AI response (may trigger resolution)
        action = skill_handler.process_ai_response(self, ai_content, context)

        if action.get('resolve'):
            self.action_resolve(action.get('summary', ''), action.get('resolution_data'))
            return

        # Send AI response via WhatsApp
        response_text = action.get('message', ai_content)

        if dry_run:
            _logger.info("DRY_RUN: Would send WhatsApp to %s: %s", self.phone, response_text[:100])
            wa_msg_id = 0
        else:
            wa_service = self.env['ai.agent.whatsapp.service']
            result = wa_service.send_message(self.phone, response_text)
            wa_msg_id = result.get('message_id', 0)

        # Log outbound message
        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'outbound',
            'body': response_text,
            'whatsapp_message_id': wa_msg_id,
            'ai_input_tokens': input_tokens,
            'ai_output_tokens': output_tokens,
        })

        self.write({
            'state': 'waiting',
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'agent',
        })

    def action_resolve(self, summary='', resolution_data=None):
        """Mark conversation as resolved and trigger skill callback."""
        self.ensure_one()
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now(),
            'resolution_summary': summary,
        })

        # Trigger skill-specific resolution callback
        skill_handler = get_skill(self.skill_id.code)
        if skill_handler and resolution_data:
            try:
                skill_handler.on_resolve(self, resolution_data)
            except Exception as e:
                _logger.error("Skill on_resolve error for conversation %s: %s", self.id, e)

        self.message_post(body=_("Conversacion resuelta: %s") % (summary or 'Sin resumen'))

    def action_timeout(self):
        """Mark conversation as timed out."""
        self.ensure_one()
        self.write({'state': 'timeout'})
        self.message_post(body=_("Conversacion cerrada por timeout (sin respuesta del cliente)."))

    def action_force_resolve(self):
        """Manual resolve button for managers."""
        self.ensure_one()
        self.action_resolve(summary='Resuelto manualmente')

    def action_retry(self):
        """Reset a failed/timeout conversation to waiting state."""
        self.ensure_one()
        if self.state not in ('failed', 'timeout'):
            raise UserError(_("Solo se puede reintentar conversaciones en estado Fallida o Timeout."))
        self.write({'state': 'waiting'})
        self.message_post(body=_("Conversacion reabierta para reintento."))

    @api.model
    def _cron_poll_messages(self):
        """Cron: poll WhatsApp API for incoming messages (fallback to webhook)."""
        wa_service = self.env['ai.agent.whatsapp.service']
        dry_run = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.dry_run', 'True'
        ).lower() == 'true'

        if dry_run:
            _logger.info("DRY_RUN: Would poll WhatsApp for new messages")
            return

        try:
            messages = wa_service.fetch_received(limit=50)
        except Exception as e:
            _logger.error("Failed to poll WhatsApp messages: %s", e)
            return

        for msg in messages:
            phone = wa_service._normalize_phone(msg.get('phone', ''))
            body = msg.get('message', '')
            wa_id = msg.get('id', 0)

            if not phone or not body:
                continue

            # Find active conversation for this phone
            conversation = self.search([
                ('phone', '=', phone),
                ('state', 'in', ('waiting', 'active')),
            ], limit=1, order='last_message_date desc')

            if not conversation:
                _logger.info("No active conversation for phone %s, ignoring message", phone)
                continue

            # Check if message already processed
            existing = self.env['ai.agent.message'].search([
                ('whatsapp_message_id', '=', wa_id),
                ('conversation_id', '=', conversation.id),
            ], limit=1)
            if existing:
                continue

            conversation.action_process_reply(body, wa_message_id=wa_id)

    @api.model
    def _cron_check_timeouts(self):
        """Cron: check for conversations that have timed out."""
        conversations = self.search([
            ('state', '=', 'waiting'),
        ])

        now = fields.Datetime.now()
        for conv in conversations:
            timeout_hours = conv.skill_id.timeout_hours or 48
            if conv.last_message_date:
                from datetime import timedelta
                deadline = conv.last_message_date + timedelta(hours=timeout_hours)
                if now > deadline:
                    conv.action_timeout()
