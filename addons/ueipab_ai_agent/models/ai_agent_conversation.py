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

    # Reminder tracking
    reminder_count = fields.Integer('Recordatorios Enviados', default=0)
    last_reminder_date = fields.Datetime('Ultimo Recordatorio')

    # Verification email tracking
    verification_email_sent_date = fields.Datetime('Verificacion Enviada')
    verification_email_recipient = fields.Char('Email Verificado')

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

    @api.model
    def _is_active_environment(self):
        """Check if this database is the active environment for AI Agent processing.

        Prevents double-processing when both testing and production share the
        same WhatsApp account. If ai_agent.active_db is set and doesn't match
        the current database name, all cron processing is skipped.
        """
        active_db = self.env['ir.config_parameter'].sudo().get_param('ai_agent.active_db', '')
        if not active_db:
            return True  # Not configured = allow processing
        current_db = self.env.cr.dbname
        if active_db != current_db:
            _logger.warning(
                "AI Agent: active_db='%s' but current db='%s'. "
                "Skipping cron processing to prevent double-processing. "
                "Set ai_agent.active_db='%s' in System Parameters to enable.",
                active_db, current_db, current_db)
            return False
        return True

    @api.model
    def _is_within_schedule(self):
        """Check if current Venezuela time is within the allowed contact schedule.

        Schedule (configurable via system parameters):
        - Weekdays (Mon-Fri): 06:30 - 20:30
        - Weekends (Sat-Sun): 09:30 - 19:00

        Cron jobs skip processing outside this window so Glenda never
        initiates contact when customers are likely sleeping.
        """
        from datetime import datetime, timezone, timedelta

        VE_TZ = timezone(timedelta(hours=-4))
        now_ve = datetime.now(VE_TZ)
        current_time = now_ve.strftime('%H:%M')
        weekday = now_ve.weekday()  # 0=Monday, 6=Sunday

        ICP = self.env['ir.config_parameter'].sudo()

        if weekday < 5:  # Monday-Friday
            start = ICP.get_param('ai_agent.schedule_weekday_start', '06:30')
            end = ICP.get_param('ai_agent.schedule_weekday_end', '20:30')
        else:  # Saturday-Sunday
            start = ICP.get_param('ai_agent.schedule_weekend_start', '09:30')
            end = ICP.get_param('ai_agent.schedule_weekend_end', '19:00')

        if start <= current_time <= end:
            return True

        day_name = now_ve.strftime('%A')
        _logger.info(
            "AI Agent: Outside schedule (%s %s, allowed %s-%s VET). "
            "Skipping cron processing.",
            day_name, current_time, start, end)
        return False

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
            'reminder_count': 0,
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
            # Send farewell message before resolving
            farewell = action.get('farewell_message')
            if farewell:
                if dry_run:
                    _logger.info("DRY_RUN: Would send farewell WhatsApp to %s: %s",
                                 self.phone, farewell[:100])
                    wa_msg_id = 0
                else:
                    wa_service = self.env['ai.agent.whatsapp.service']
                    result = wa_service.send_message(self.phone, farewell)
                    wa_msg_id = result.get('message_id', 0)

                self.env['ai.agent.message'].create({
                    'conversation_id': self.id,
                    'direction': 'outbound',
                    'body': farewell,
                    'whatsapp_message_id': wa_msg_id,
                    'ai_input_tokens': input_tokens,
                    'ai_output_tokens': output_tokens,
                })

            self.action_resolve(action.get('summary', ''), action.get('resolution_data'))
            return

        # Handle intermediate actions (e.g., send verification email)
        if action.get('send_verification_email'):
            self._send_verification_email(action['send_verification_email'])

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

    def _send_verification_email(self, recipient_email):
        """Send a verification email to check if the customer's email is working."""
        self.ensure_one()
        icp = self.env['ir.config_parameter'].sudo()
        dry_run = self._is_dry_run()

        email_from = icp.get_param(
            'ai_agent.verification_email_from',
            'Colegio Andrés Bello - Soporte <soporte@ueipab.edu.ve>',
        )
        institution = icp.get_param('ai_agent.institution_display_name', 'UEIPAB')
        first_name = (self.partner_id.name or '').split()[0] if self.partner_id.name else 'Estimado/a'

        subject = f'{institution} - Correo de verificación'
        body_html = (
            f'<p>Hola {first_name},</p>'
            f'<p>Este es un correo de verificación enviado desde {institution} para '
            f'confirmar que su correo electrónico está recibiendo nuestros mensajes correctamente.</p>'
            f'<p>Si recibe este correo, por favor confírmenos por WhatsApp que lo recibió.</p>'
            f'<p>Saludos cordiales,<br/>{institution} - Soporte</p>'
        )

        if dry_run:
            _logger.info("DRY_RUN: Would send verification email to %s from %s",
                         recipient_email, email_from)
        else:
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_from': email_from,
                'email_to': recipient_email,
                'auto_delete': True,
            })
            mail.send()
            _logger.info("Verification email sent to %s for conversation %s",
                         recipient_email, self.id)

        self.write({
            'verification_email_sent_date': fields.Datetime.now(),
            'verification_email_recipient': recipient_email,
        })

        self.message_post(body=_(
            "Correo de verificación enviado a %s%s."
        ) % (recipient_email, " (DRY RUN)" if dry_run else ""))

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

    def _send_reminder(self):
        """Send a WhatsApp reminder to the customer."""
        self.ensure_one()
        skill_handler = get_skill(self.skill_id.code)
        if not skill_handler:
            _logger.error("No skill handler for code: %s", self.skill_id.code)
            return

        context = skill_handler.get_context(self)
        reminder_text = skill_handler.get_reminder_message(self, context, self.reminder_count)

        dry_run = self._is_dry_run()
        wa_service = self.env['ai.agent.whatsapp.service']

        if dry_run:
            _logger.info("DRY_RUN: Would send reminder WhatsApp to %s: %s",
                         self.phone, reminder_text[:100])
            wa_msg_id = 0
        else:
            result = wa_service.send_message(self.phone, reminder_text)
            wa_msg_id = result.get('message_id', 0)

        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'outbound',
            'body': reminder_text,
            'whatsapp_message_id': wa_msg_id,
        })

        self.write({
            'reminder_count': self.reminder_count + 1,
            'last_reminder_date': fields.Datetime.now(),
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'agent',
        })

        self.message_post(body=_(
            "Recordatorio %d/%d enviado por WhatsApp%s."
        ) % (self.reminder_count, self.skill_id.max_reminders or 2,
             " (DRY RUN)" if dry_run else ""))

    def action_resolve_via_email(self, email_body_preview=''):
        """Resolve conversation because customer replied to verification email.

        Called via XML-RPC from the email checker bridge script.
        Returns True if resolved, False if conversation was not eligible.
        """
        self.ensure_one()
        if self.state != 'waiting' or not self.verification_email_sent_date:
            return False

        # Send farewell WhatsApp
        skill_handler = get_skill(self.skill_id.code)
        context = skill_handler.get_context(self) if skill_handler else {}
        first_name = context.get('first_name', 'estimado/a')
        institution = context.get('institution', 'UEIPAB')

        farewell = (
            f"{first_name}, hemos recibido su respuesta por correo electronico. "
            f"Su direccion de correo ha sido verificada exitosamente. "
            f"Gracias por su colaboracion. Saludos desde {institution}."
        )

        dry_run = self._is_dry_run()
        wa_service = self.env['ai.agent.whatsapp.service']

        if dry_run:
            _logger.info("DRY_RUN: Would send farewell WhatsApp to %s: %s",
                         self.phone, farewell[:100])
            wa_msg_id = 0
        else:
            result = wa_service.send_message(self.phone, farewell)
            wa_msg_id = result.get('message_id', 0)

        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'outbound',
            'body': farewell,
            'whatsapp_message_id': wa_msg_id,
        })

        summary = 'Cliente respondio al correo de verificacion.'
        if email_body_preview:
            summary += f' Preview: {email_body_preview[:200]}'

        self.action_resolve(
            summary=summary,
            resolution_data={'action': 'restore'},
        )

        self.message_post(body=_(
            "Conversacion resuelta automaticamente: respuesta detectada en correo electronico%s."
        ) % (" (DRY RUN)" if dry_run else ""))

        return True

    @api.model
    def _cron_poll_messages(self):
        """Cron: poll WhatsApp API for incoming messages (fallback to webhook)."""
        if not self._is_active_environment():
            return
        if not self._is_within_schedule():
            return

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
        """Cron: check waiting conversations for reminders or timeout.

        Logic per conversation:
        1. If last_message_date + reminder_interval < now AND reminder_count < max_reminders
           → send a reminder
        2. If reminder_count >= max_reminders AND last_message_date + reminder_interval < now
           → timeout
        """
        if not self._is_active_environment():
            return
        if not self._is_within_schedule():
            return

        from datetime import timedelta
        conversations = self.search([
            ('state', '=', 'waiting'),
        ])

        now = fields.Datetime.now()
        for conv in conversations:
            skill = conv.skill_id
            interval_hours = skill.reminder_interval_hours or 24
            max_reminders = skill.max_reminders if skill.max_reminders >= 0 else 2

            if not conv.last_message_date:
                continue

            deadline = conv.last_message_date + timedelta(hours=interval_hours)
            if now <= deadline:
                continue

            if conv.reminder_count < max_reminders:
                conv._send_reminder()
            else:
                conv.action_timeout()
