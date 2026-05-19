import logging
import re as _re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from ..skills import get_skill

_logger = logging.getLogger(__name__)

# Phrases that signal the customer is ending the conversation.
# Used by general_inquiry to auto-resolve instead of staying 'waiting'.
_FAREWELL_PHRASES = frozenset([
    'gracias', 'muchas gracias', 'mil gracias', 'muchas gracias igual',
    'hasta luego', 'hasta pronto', 'hasta la próxima', 'hasta la proxima',
    'nos vemos', 'adiós', 'adios', 'chao', 'ciao', 'bye',
    'feliz día', 'feliz dia', 'buen día', 'buen dia',
    'buenas noches', 'buenas tardes', 'buenos días', 'buenos dias',
    'que tengas', 'que tenga', 'igualmente',
    'no es todo', 'eso es todo', 'eso seria todo', 'eso sería todo',
    'ya es todo', 'con eso es todo', 'es todo por ahora',
    'listo gracias', 'ok gracias', 'okey gracias', 'okay gracias',
    'perfecto gracias', 'excelente gracias', 'genial gracias',
    'de nada', 'con gusto', 'entendido gracias', 'claro gracias',
    # "I'm done / no more questions" patterns
    'no tengo más preguntas', 'no tengo preguntas',
    'no tengo más dudas', 'no tengo dudas',
    'no tengo nada más', 'no tengo nada mas',
    'no hay más preguntas', 'no hay nada más',
    'nada más', 'nada mas', 'por ahora nada más', 'por ahora nada mas',
    'era todo', 'era lo que necesitaba', 'con eso me basta',
    'sin más preguntas', 'sin preguntas', 'sin dudas',
    'es todo lo que necesitaba', 'es lo que necesitaba',
    'ya entendí', 'ya entendi', 'ya quedó claro', 'ya quedo claro',
])

# Words that may accompany a farewell without indicating a new request
_FAREWELL_FILLER = frozenset([
    'ok', 'okey', 'okay', 'listo', 'ya', 'si', 'sí', 'bien',
    'bueno', 'claro', 'y', 'e', 'muy', 'igual',
    'más', 'mas', 'nada', 'ninguna', 'ningún', 'ningun',
    'todo', 'por', 'perfecto', 'excelente', 'genial', 'fantástico', 'fantastico',
])


def _is_farewell_message(text):
    """Return True if the customer message is a farewell with no pending request.

    Strategy: strip all known farewell phrases and filler words from the message.
    If nothing meaningful remains, it is a farewell. A question mark anywhere
    always blocks auto-resolve.
    """
    if not text:
        return False
    clean = text.lower().strip().rstrip('.,!¡¿')
    if '?' in text:
        return False
    # Quick exact match
    if clean in _FAREWELL_PHRASES:
        return True
    # Only analyse short-to-medium messages to avoid false positives
    if len(clean) > 80:
        return False
    # Strip farewell phrases (longest first to avoid partial clobbering)
    remainder = clean
    for phrase in sorted(_FAREWELL_PHRASES, key=len, reverse=True):
        remainder = remainder.replace(phrase, ' ')
    # Remove punctuation and split into words; discard filler words
    meaningful = [
        w for w in _re.sub(r'[^\w\s]', ' ', remainder).split()
        if w not in _FAREWELL_FILLER and len(w) > 1
    ]
    return len(meaningful) == 0


class AiAgentConversation(models.Model):
    _name = 'ai.agent.conversation'
    _description = 'AI Agent Conversation'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char('Referencia', compute='_compute_name', store=True)
    skill_id = fields.Many2one('ai.agent.skill', required=True, string='Skill', ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Contacto', required=True)
    phone = fields.Char('Telefono WhatsApp')
    channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('telegram', 'Telegram'),
    ], default='whatsapp', required=True, string='Canal')
    telegram_chat_id = fields.Char('Telegram Chat ID', index=True)

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
    initial_message = fields.Text(
        'Mensaje del representante',
        help='Mensaje recibido por otro canal. Glenda lo procesará al iniciar, '
             'saltándose el saludo genérico. Se borra tras el envío.')

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

    # Escalation tracking
    escalation_date = fields.Datetime('Fecha Escalacion')
    escalation_reason = fields.Text('Razon Escalacion')
    escalation_freescout_id = fields.Char('Freescout Ticket #')
    escalation_freescout_url = fields.Char(
        'Ticket Freescout', compute='_compute_escalation_freescout_url')
    escalation_notified = fields.Boolean('Equipo Notificado', default=False)

    # Alternative contact info (captured when a family member provides a different number)
    alternative_phone = fields.Char('Telefono Alternativo')

    # Manual silence — suppresses all outbound replies and reminders
    silent = fields.Boolean('Silenciada', default=False)

    # Placeholder flag — partner was auto-created from an unknown phone (lead not yet identified)
    is_placeholder = fields.Char(
        'Lead',
        compute='_compute_is_placeholder',
        store=True,
    )

    @api.depends('partner_id.name')
    def _compute_is_placeholder(self):
        for rec in self:
            name = rec.partner_id.name or ''
            rec.is_placeholder = 'Desconocido' if name.startswith('Consulta WhatsApp') else ''

    @api.depends('skill_id.name', 'partner_id.name')
    def _compute_name(self):
        for rec in self:
            skill_name = rec.skill_id.name or 'AI'
            partner_name = rec.partner_id.name or 'Sin contacto'
            rec.name = f"{skill_name} - {partner_name}"

    @api.depends('escalation_freescout_id')
    def _compute_escalation_freescout_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.freescout_base_url', 'https://freescout.ueipab.edu.ve')
        for rec in self:
            if rec.escalation_freescout_id:
                rec.escalation_freescout_url = (
                    f"{base}/conversation/{rec.escalation_freescout_id}")
            else:
                rec.escalation_freescout_url = False

    def _compute_turn_count(self):
        for rec in self:
            # Only count inbound messages with actual content — empty records are
            # dedup-only markers and must not inflate the turn limit counter.
            rec.turn_count = len(rec.agent_message_ids.filtered(
                lambda m: m.direction == 'inbound' and (m.body or m.attachment_url)))

    def _get_conversation_history(self):
        """Format messages as Claude API conversation history.

        Supports multimodal content (text + images). When images are present,
        uses content block format. Falls back to simple string for text-only.
        """
        self.ensure_one()
        messages = []
        for msg in self.agent_message_ids.sorted('timestamp'):
            if not msg.body and not msg.attachment_url:
                continue  # Skip empty dedup records

            role = 'assistant' if msg.direction == 'outbound' else 'user'

            # Build content blocks for this message
            SUPPORTED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
            blocks = []
            if msg.attachment_url and msg.attachment_type == 'image':
                if msg.attachment_id and msg.attachment_id.datas:
                    mime = msg.attachment_id.mimetype or 'image/jpeg'
                    if mime in SUPPORTED_IMAGE_TYPES:
                        blocks.append({
                            'type': 'image',
                            'source': {
                                'type': 'base64',
                                'media_type': mime,
                                'data': msg.attachment_id.datas.decode('utf-8'),
                            },
                        })
                    else:
                        _logger.warning(
                            "Skipping unsupported image mimetype %s for msg %d",
                            mime, msg.id)
                        blocks.append({
                            'type': 'text',
                            'text': '(Imagen en formato no soportado)',
                        })
                else:
                    # Validate URL extension before sending to Claude
                    url_ext = msg.attachment_url.lower().split('?')[0].rsplit('.', 1)[-1]
                    if url_ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                        blocks.append({
                            'type': 'image',
                            'source': {'type': 'url', 'url': msg.attachment_url},
                        })
                    else:
                        _logger.warning(
                            "Skipping non-image URL extension .%s for msg %d",
                            url_ext, msg.id)
                        blocks.append({
                            'type': 'text',
                            'text': '(Archivo adjunto no soportado para vision)',
                        })
            elif msg.attachment_url and msg.attachment_type == 'document':
                # Convert PDF first page to image for Claude Vision
                pdf_image = self._convert_pdf_to_image(msg)
                if pdf_image:
                    blocks.append({
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/png',
                            'data': pdf_image,
                        },
                    })
                    if not msg.body:
                        blocks.append({
                            'type': 'text',
                            'text': '(Documento PDF enviado)',
                        })
            if msg.body:
                blocks.append({'type': 'text', 'text': msg.body})

            # Merge with previous if same role
            if messages and messages[-1]['role'] == role:
                prev = messages[-1]['content']
                if isinstance(prev, str):
                    messages[-1]['content'] = [{'type': 'text', 'text': prev}]
                messages[-1]['content'].extend(blocks)
            else:
                if len(blocks) == 1 and blocks[0].get('type') == 'text':
                    content = blocks[0]['text']
                else:
                    content = blocks
                messages.append({'role': role, 'content': content})

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

        # Check if today is a holiday (uses weekend schedule)
        holidays_str = ICP.get_param('ai_agent.holidays', '')
        holidays = {d.strip() for d in holidays_str.split(',') if d.strip()}
        current_date = now_ve.strftime('%m-%d')
        is_holiday = current_date in holidays

        if weekday < 5 and not is_holiday:  # Regular weekday
            start = ICP.get_param('ai_agent.schedule_weekday_start', '06:30')
            end = ICP.get_param('ai_agent.schedule_weekday_end', '20:30')
        else:  # Weekend OR holiday
            start = ICP.get_param('ai_agent.schedule_weekend_start', '09:30')
            end = ICP.get_param('ai_agent.schedule_weekend_end', '19:00')

        if start <= current_time <= end:
            return True

        day_name = now_ve.strftime('%A')
        reason = "feriado" if is_holiday else day_name
        _logger.info(
            "AI Agent: Outside schedule (%s %s, allowed %s-%s VET). "
            "Skipping cron processing.",
            reason, current_time, start, end)
        return False

    @api.model
    def _in_proactive_quiet_hours(self):
        """Return True during the proactive quiet window (20:30–07:30 VET by default).

        Only blocks CRON-initiated proactive WA sends (reminders). Reactive replies
        to incoming customer messages are always allowed and not gated here.
        Configurable via ir.config_parameter:
          ai_agent.proactive_quiet_start  (default '20:30')
          ai_agent.proactive_quiet_end    (default '07:30')
        """
        from datetime import datetime, timezone, timedelta
        VE_TZ = timezone(timedelta(hours=-4))
        t = datetime.now(VE_TZ).strftime('%H:%M')
        icp = self.env['ir.config_parameter'].sudo()
        q_start = icp.get_param('ai_agent.proactive_quiet_start', '20:30')
        q_end = icp.get_param('ai_agent.proactive_quiet_end', '07:30')
        # Overnight range: start > end means the window wraps midnight
        if q_start > q_end:
            return t >= q_start or t < q_end
        return q_start <= t < q_end

    def action_refresh(self):
        """Reload the conversation form to show latest messages and state."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_start(self):
        """Send greeting message (or process initial_message directly) and activate conversation."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Solo se puede iniciar una conversacion en estado Borrador."))

        skill_handler = get_skill(self.skill_id.code)
        if not skill_handler:
            raise UserError(_("No se encontro el handler para el skill '%s'.") % self.skill_id.code)

        if self.initial_message and self.initial_message.strip():
            # Skip generic greeting — respond directly to the representative's message
            msg = self.initial_message.strip()
            self.write({
                'state': 'waiting',
                'last_message_date': fields.Datetime.now(),
                'last_sender': 'agent',
                'initial_message': False,
            })
            self.message_post(body=_(
                "Conversacion iniciada con mensaje del representante. "
                "Respondiendo directamente (sin saludo genérico)."
            ))
            self.action_process_reply(message_text=msg, wa_message_id=0)
            return

        # Normal flow — send greeting and wait for reply
        context  = skill_handler.get_context(self)
        greeting = skill_handler.get_greeting(self, context)

        dry_run   = self._is_dry_run()
        wa_msg_id = self._send_to_user(greeting)

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

    def action_process_reply(self, message_text, wa_message_id=0, extra_wa_ids=None,
                             attachment_url=None, extra_attachments=None):
        """Process an incoming customer reply using Claude AI.

        Args:
            message_text: The customer message (may be combined from multiple messages).
            wa_message_id: WhatsApp message ID of the first/only message.
            extra_wa_ids: List of additional WA message IDs when batching multiple
                messages. Creates empty dedup records so they won't be re-processed.
            attachment_url: URL of attachment from the first/only message.
            extra_attachments: List of dicts {'url': ..., 'wa_id': ...} for
                additional attachments from batched messages.
        """
        self.ensure_one()
        if self.state not in ('waiting', 'active'):
            _logger.warning("Conversation %s: ignoring reply in state %s", self.id, self.state)
            return

        # Log inbound message
        msg_vals = {
            'conversation_id': self.id,
            'direction': 'inbound',
            'body': message_text or '',
            'whatsapp_message_id': wa_message_id,
        }
        if attachment_url:
            att_type = self._detect_attachment_type(attachment_url)
            msg_vals['attachment_url'] = attachment_url
            msg_vals['attachment_type'] = att_type
            # Transcribe audio — always mark with prefix so Claude knows it was a voice note.
            # If WA already auto-transcribed (message_text present), use that and mark it.
            # If no text, call Whisper; fall back to '[audio sin transcripción]' only on failure.
            if att_type == 'audio':
                if message_text:
                    # WhatsApp platform already transcribed the voice note — mark it so Claude
                    # knows this is audio content (may have minor transcription errors).
                    message_text = f"[Audio transcrito]: {message_text}"
                else:
                    transcription = self._transcribe_audio(attachment_url)
                    if transcription:
                        message_text = f"[Audio transcrito]: {transcription}"
                    else:
                        message_text = '[audio sin transcripción]'
                msg_vals['body'] = message_text
        self.env['ai.agent.message'].create(msg_vals)

        # Create separate records for extra attachments (batched images)
        if extra_attachments:
            for att in extra_attachments:
                self.env['ai.agent.message'].create({
                    'conversation_id': self.id,
                    'direction': 'inbound',
                    'body': '',
                    'whatsapp_message_id': att.get('wa_id', 0),
                    'attachment_url': att['url'],
                    'attachment_type': self._detect_attachment_type(att['url']),
                })

        # Create dedup-only records for extra WA IDs (empty body, won't appear in history)
        if extra_wa_ids:
            for extra_id in extra_wa_ids:
                self.env['ai.agent.message'].create({
                    'conversation_id': self.id,
                    'direction': 'inbound',
                    'body': '',
                    'whatsapp_message_id': extra_id,
                })

        now_dt = fields.Datetime.now()
        prev_last_msg = self.last_message_date

        self.write({
            'state': 'active',
            'last_message_date': now_dt,
            'last_sender': 'customer',
            'reminder_count': 0,
        })

        # Tier-1 bot detection — skipped if already manually silenced
        if not self.silent:
            # Speed check: consecutive CUSTOMER messages < 2s apart = bot-like.
            # Only fires when prev sender was also 'customer' — never on agent-initiated
            # conversations where action_start() just set last_message_date moments ago.
            # Also skipped on turn_count <= 1: the conversation is brand-new and
            # last_message_date reflects creation time, not a prior customer message.
            prev_sender_was_customer = (self.last_sender == 'customer')
            if (prev_last_msg
                    and prev_sender_was_customer
                    and self.turn_count > 1
                    and (now_dt - prev_last_msg).total_seconds() < 2):
                gap = (now_dt - prev_last_msg).total_seconds()
                _logger.warning("Conv %d: bot-speed detected (%.1fs gap) — silencing", self.id, gap)
                self.write({'silent': True})
                self.message_post(body=_(
                    "⚠️ Bot detectado: mensajes con %.1fs de intervalo. Silenciada automáticamente."
                ) % gap)

        if not self.silent and (self.phone or self.telegram_chat_id):
            # Rate limit: max 30 inbound per contact in a rolling 24h window
            from datetime import timedelta
            cutoff = now_dt - timedelta(hours=24)
            contact_domain = [('phone', '=', self.phone)] if self.phone \
                else [('telegram_chat_id', '=', self.telegram_chat_id)]
            conv_ids = self.search(contact_domain).ids
            if conv_ids:
                inbound_count = self.env['ai.agent.message'].search_count([
                    ('conversation_id', 'in', conv_ids),
                    ('direction', '=', 'inbound'),
                    ('timestamp', '>=', cutoff),
                ])
                if inbound_count > 30:
                    _logger.warning(
                        "Conv %d: rate limit hit (%d inbound/24h) — silencing",
                        self.id, inbound_count)
                    self.write({'silent': True})
                    self.message_post(body=_(
                        "⚠️ Límite de mensajes: %d mensajes en 24h. Silenciada automáticamente."
                    ) % inbound_count)

        if self.silent:
            _logger.info("Conv %d silenced — inbound logged, reply suppressed", self.id)
            return

        # Check turn limit
        skill = self.skill_id
        if self.turn_count >= skill.max_turns:
            self.write({'state': 'failed'})
            self.message_post(body=_("Conversacion cerrada: se alcanzo el limite de %d turnos.") % skill.max_turns)
            return

        # Moderation check — reject abusive/inappropriate messages before hitting Claude
        if message_text:
            flagged, flag_categories = self._check_moderation(message_text)
            if flagged:
                _logger.warning(
                    "Conversation %d: message flagged by moderation [%s]: %s...",
                    self.id, ', '.join(flag_categories), message_text[:80]
                )
                self.message_post(body=_(
                    "⚠️ Mensaje bloqueado por moderación: [%s]"
                ) % ', '.join(flag_categories))
                if not self._is_dry_run():
                    self._send_to_user(
                        "No puedo procesar ese tipo de mensaje. "
                        "Si tienes una consulta sobre el colegio, con gusto te ayudo."
                    )
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
                wa_msg_id = self._send_to_user(farewell)

                self.env['ai.agent.message'].create({
                    'conversation_id': self.id,
                    'direction': 'outbound',
                    'body': farewell,
                    'whatsapp_message_id': wa_msg_id,
                    'ai_input_tokens': input_tokens,
                    'ai_output_tokens': output_tokens,
                })

            # Send flyer if requested (after farewell text, before resolving)
            flyer_key = action.get('resolution_data', {}).get('flyer_key')
            if flyer_key and hasattr(skill_handler, 'send_flyer'):
                skill_handler.send_flyer(self, flyer_key)

            # CEO monitoring: alert on handoff
            resolution_data = action.get('resolution_data', {})
            if resolution_data.get('action') == 'handoff':
                route = resolution_data.get('route', 'support')
                dest = 'Pagos' if route == 'billing' else ('PDVSA Ret.' if route == 'pdvsa_retention' else 'Soporte')
                self._notify_ceo(
                    f"📋 Handoff → {dest}\n"
                    f"👤 {self.partner_id.name or self.phone}\n"
                    f"📝 {resolution_data.get('summary', '')[:120]}"
                )

            self.action_resolve(action.get('summary', ''), action.get('resolution_data'))
            return

        # Handle intermediate actions (e.g., send verification email, escalation)
        if action.get('send_verification_email'):
            self._send_verification_email(action['send_verification_email'])

        # Check BEFORE _handle_escalation sets escalation_date
        is_first_escalation = not self.escalation_date
        if action.get('escalate'):
            self._handle_escalation(action['escalate'])

        if action.get('send_escalation_email'):
            # Only send one escalation email per conversation to avoid duplicates
            if is_first_escalation:
                self._send_escalation_email(action['send_escalation_email'])
            else:
                _logger.info("Conversation %d: skipping duplicate escalation email", self.id)

        if action.get('alternative_phone'):
            self.write({'alternative_phone': action['alternative_phone']})

        # Handle absence notification (WA/Telegram → create Freescout soporte@ conversation)
        if action.get('notify_absence') and not dry_run:
            try:
                with self.env.cr.savepoint():
                    self._handle_glenda_absence_notification(action['notify_absence'])
            except Exception as exc:
                _logger.warning("Absence notification failed: %s", exc)

        # Handle school account help (forgot student email / Akdemia access)
        if action.get('school_account_help') and not dry_run:
            try:
                with self.env.cr.savepoint():
                    followup = self._handle_school_account_help(action['school_account_help'])
                    if followup:
                        action['_school_followup'] = followup
            except Exception as exc:
                _logger.warning("School account help failed: %s", exc)

        # Send AI response via configured channel
        response_text = action.get('message', ai_content)

        # Telegram cross-channel invite — appended once on the very first WA reply
        # for general_inquiry only. If the customer ignores it, WA conversation continues normally.
        icp = self.env['ir.config_parameter'].sudo()
        if (self.channel == 'whatsapp'
                and self.skill_id.code == 'general_inquiry'
                and not self.agent_message_ids.filtered(lambda m: m.direction == 'outbound')
                and icp.get_param('ai_agent.telegram_invite_enabled', 'True') == 'True'):
            bot_username = icp.get_param('ai_agent.telegram_bot_username', 'GlendaUeipabBot')
            response_text += (
                f"\n\n📲 Por cierto, también puede escribirme por Telegram "
                f"(@{bot_username}) para respuestas al instante: "
                f"https://t.me/{bot_username} — "
                f"Si prefiere seguir por WhatsApp, con gusto le atiendo aquí también."
            )

        wa_msg_id = self._send_to_user(response_text)

        # Log outbound message
        self.env['ai.agent.message'].create({
            'conversation_id': self.id,
            'direction': 'outbound',
            'body': response_text,
            'whatsapp_message_id': wa_msg_id,
            'ai_input_tokens': input_tokens,
            'ai_output_tokens': output_tokens,
        })

        # Send flyer after text reply if Claude requested one
        flyer_key = action.get('flyer_key')
        if flyer_key and hasattr(skill_handler, 'send_flyer'):
            skill_handler.send_flyer(self, flyer_key)

        # Payment receipt OCR — structured extraction + auto draft payment
        if attachment_url and self._detect_attachment_type(attachment_url) == 'image':
            receipt = self._extract_payment_receipt(attachment_url)
            if receipt:
                partner = self.partner_id
                payment_id, odoo_url, matched_info, duplicate = None, None, None, None

                if partner:
                    duplicate = self._check_duplicate_payment(
                        partner.id, receipt.get('referencia'))
                    if not duplicate:
                        bcv_rate = self._get_bcv_rate_for_payment()
                        journal_id = self._resolve_journal_for_payment(
                            receipt.get('banco'), receipt.get('moneda'))
                        matched_info = self._match_invoice_for_payment(
                            partner, receipt.get('monto'), receipt.get('moneda'), bcv_rate)
                        payment_id, odoo_url = self._create_draft_payment(
                            partner, receipt, journal_id, matched_info)

                self._notify_pagos_payment_receipt(
                    receipt, partner, self.phone,
                    payment_id=payment_id, odoo_url=odoo_url,
                    matched_invoice_info=matched_info, duplicate_payment=duplicate,
                )
                draft_tag = f" — Borrador #{payment_id}" if payment_id else ""
                dup_tag = " — ⚠️ DUPLICADO" if duplicate else ""
                self.message_post(body=_(
                    "🧾 Comprobante: %s %s %s%s%s"
                ) % (receipt.get('banco', ''), receipt.get('monto', ''),
                     receipt.get('moneda', ''), draft_tag, dup_tag))

        # Send school account help follow-up (student email found / not found)
        school_followup = action.get('_school_followup')
        if school_followup:
            try:
                self._send_to_user(school_followup)
                self.env['ai.agent.message'].sudo().create({
                    'conversation_id': self.id,
                    'direction':       'outbound',
                    'body':            school_followup,
                })
            except Exception as exc:
                _logger.warning("School account follow-up send failed: %s", exc)

        # Send balance breakdown as a separate WA message if present
        balance_msg = action.get('balance_message')
        if balance_msg:
            try:
                self._send_to_user(balance_msg)
                self.env['ai.agent.message'].sudo().create({
                    'conversation_id': self.id,
                    'direction':       'outbound',
                    'body':            balance_msg,
                })
                _logger.info("Balance breakdown sent to %s", self.phone)
            except Exception as e:
                _logger.warning("Failed to send balance breakdown to %s: %s", self.phone, e)

        # P1: Auto-resolve when customer sent a farewell (general_inquiry only).
        # Claude already replied with a single closing line per the prompt rules.
        # Resolving now prevents the 72h timeout and stops reminder messages.
        if skill.code == 'general_inquiry' and _is_farewell_message(message_text):
            _logger.info(
                "Conversation %d: farewell detected in '%s...' — auto-resolving",
                self.id, (message_text or '')[:40],
            )
            self.action_resolve("Conversación concluida por despedida del cliente")
            return

        self.write({
            'state': 'waiting',
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'agent',
        })

    @staticmethod
    def _detect_attachment_type(url):
        """Detect attachment type from URL file extension."""
        if not url:
            return None
        url_lower = url.lower().split('?')[0]
        if any(url_lower.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return 'image'
        if any(url_lower.endswith(ext) for ext in ('.pdf', '.doc', '.docx')):
            return 'document'
        if any(url_lower.endswith(ext) for ext in ('.mp3', '.ogg', '.opus', '.m4a', '.aac', '.wav')):
            return 'audio'
        if any(url_lower.endswith(ext) for ext in ('.mp4', '.mov', '.avi', '.3gp')):
            return 'video'
        return 'image'  # Default for MassivaMóvil (most common)

    def _convert_pdf_to_image(self, msg):
        """Convert a PDF attachment's first page to base64 PNG for Claude Vision.

        Tries archived binary first, falls back to URL download.
        Returns base64 string (no prefix) or None if conversion fails.
        """
        import base64
        try:
            import fitz  # PyMuPDF
        except ImportError:
            _logger.warning("PyMuPDF not installed — cannot convert PDF for Vision")
            return None

        try:
            pdf_bytes = None
            if msg.attachment_id and msg.attachment_id.datas:
                pdf_bytes = base64.b64decode(msg.attachment_id.datas)
            elif msg.attachment_url:
                resp = requests.get(msg.attachment_url, timeout=30)
                resp.raise_for_status()
                pdf_bytes = resp.content

            if not pdf_bytes:
                return None

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[0]
            # 2x resolution for readability
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            png_data = pix.tobytes("png")
            doc.close()

            return base64.b64encode(png_data).decode('utf-8')
        except Exception as e:
            _logger.warning("Failed to convert PDF to image for msg %d: %s", msg.id, e)
            return None

    def _extract_payment_receipt(self, url):
        """Use GPT-4o-mini Vision with Structured Outputs to extract payment receipt data.

        Returns a dict with typed fields (monto guaranteed float), or None if not a receipt.
        Uses OpenAI json_schema response_format — no markdown fence stripping needed.
        """
        import base64, json as _json
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('ai_agent.openai_api_key', '')
        if not api_key:
            return None

        try:
            img_resp = requests.get(url, timeout=20)
            img_resp.raise_for_status()
            img_b64 = base64.b64encode(img_resp.content).decode('utf-8')
            mime = img_resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
        except Exception as e:
            _logger.warning("Receipt OCR: failed to download image: %s", e)
            return None

        schema = {
            'type': 'object',
            'properties': {
                'is_receipt':     {'type': 'boolean'},
                'banco':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
                'monto':          {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                'moneda':         {'anyOf': [{'type': 'string', 'enum': ['VES', 'USD', 'EUR']}, {'type': 'null'}]},
                'referencia':     {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
                'fecha':          {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
                'titular_origen': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
                'cuenta_destino': {'anyOf': [{'type': 'string'}, {'type': 'null'}]},
                'tipo_pago':      {'anyOf': [{'type': 'string',
                                              'enum': ['pago_movil', 'transferencia', 'zelle',
                                                       'biopago', 'cashea', 'otro']},
                                             {'type': 'null'}]},
            },
            'required': ['is_receipt', 'banco', 'monto', 'moneda', 'referencia',
                         'fecha', 'titular_origen', 'cuenta_destino', 'tipo_pago'],
            'additionalProperties': False,
        }

        prompt = (
            "Analiza esta imagen. Si es un comprobante de pago venezolano "
            "(transferencia, pago móvil, Zelle, biopago, Cashea, depósito, app bancaria), "
            "extrae los datos. El campo 'monto' debe ser número decimal puro "
            "(p.ej. 35134.12, no texto). "
            "Si NO es comprobante de pago, responde con is_receipt=false y el resto en null."
        )

        try:
            resp = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-4o-mini',
                    'max_tokens': 400,
                    'response_format': {
                        'type': 'json_schema',
                        'json_schema': {'name': 'payment_receipt', 'strict': True, 'schema': schema},
                    },
                    'messages': [{'role': 'user', 'content': [
                        {'type': 'image_url',
                         'image_url': {'url': f'data:{mime};base64,{img_b64}', 'detail': 'low'}},
                        {'type': 'text', 'text': prompt},
                    ]}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = _json.loads(resp.json()['choices'][0]['message']['content'])
            if not data.get('is_receipt'):
                return None
            _logger.info("Receipt (structured): banco=%s monto=%s %s ref=%s",
                         data.get('banco'), data.get('monto'), data.get('moneda'),
                         data.get('referencia'))
            return data
        except Exception as e:
            _logger.warning("Receipt OCR structured extraction failed: %s", e)
            return None

    # ── Channel dispatch ────────────────────────────────────────────────────

    def _send_to_user(self, text):
        """Send text to the user via their channel (WhatsApp or Telegram).

        Handles dry_run internally. Returns WA message_id (int) or 0.
        """
        if self._is_dry_run():
            _logger.info(
                "DRY_RUN [%s → %s]: %s",
                self.channel, self.telegram_chat_id or self.phone, text[:80],
            )
            return 0
        if self.channel == 'telegram':
            resp = self.env['ai.agent.telegram.service'].send_message(
                self.telegram_chat_id, text)
            if not resp.get('ok'):
                err = resp.get('description', 'unknown error')
                _logger.warning("Telegram send failed chat_id=%s: %s", self.telegram_chat_id, err)
                try:
                    partner = self.partner_id.name or f"chat {self.telegram_chat_id}"
                    self._notify_ceo_discuss(
                        f"⚠️ [Telegram] Error al enviar mensaje a {partner}\n"
                        f"chat_id: {self.telegram_chat_id} | Error: {err}",
                        self.env['ir.config_parameter'].sudo().get_param(
                            'wa_monitor.ceo_email', ''),
                    )
                except Exception:
                    pass
            return 0
        result = self.env['ai.agent.whatsapp.service'].send_message(self.phone, text)
        return result.get('message_id', 0)

    # ── Telegram inbound entry point ────────────────────────────────────────

    @api.model
    def _handle_glenda_absence_notification(self, absence_data):
        """Create a FreeScout soporte@ conversation when a parent reports absence via WA/Telegram.

        The absence_processor.py cron picks it up in the next 10-min cycle and handles
        Josefina assignment, director/subdirector email, and OdooBot DM.
        """
        import requests as _req
        import json as _json
        from datetime import datetime as _dt

        student = absence_data.get('student_name', 'Alumno/a')
        grade   = absence_data.get('grade_raw', '—')
        reason  = absence_data.get('reason', '—')
        today   = _dt.now().strftime('%d/%m/%Y')
        channel = self.channel

        # Get parent contact info from conversation partner
        partner = self.partner_id
        parent_email = (partner.email or '') if partner else ''
        parent_name  = (partner.name or 'Representante') if partner else 'Representante'
        phone_or_id  = self.phone or self.telegram_chat_id or ''

        icp = self.env['ir.config_parameter'].sudo()
        try:
            fs_config = _json.load(open('/opt/odoo-dev/config/freescout_api.json'))
        except Exception:
            _logger.error("Absence notify: cannot read freescout_api.json")
            return

        fs_api_url = fs_config['api_url']
        fs_api_key = fs_config['api_key']
        headers = {'X-FreeScout-API-Key': fs_api_key, 'Content-Type': 'application/json'}

        channel_label = 'WhatsApp' if channel == 'whatsapp' else 'Telegram'
        subject = f'[{channel_label}] Ausencia {student} — {grade} — {today}'

        body_html = (
            f'<p><strong>Notificación de ausencia recibida vía {channel_label}</strong></p>'
            f'<p><strong>Alumno/a:</strong> {student}<br/>'
            f'<strong>Nivel/Año:</strong> {grade}<br/>'
            f'<strong>Motivo:</strong> {reason}</p>'
            f'<p><strong>Representante:</strong> {parent_name}<br/>'
            f'<strong>Contacto:</strong> {phone_or_id}</p>'
            f'<p><em>Registrado automáticamente por Glenda AI — {today}</em></p>'
        )

        payload = {
            'type':      1,
            'mailboxId': 3,  # soporte@ueipab.edu.ve
            'subject':   subject,
            'status':    'active',
            'customer':  {'email': parent_email or 'glenda-noreply@ueipab.edu.ve',
                          'firstName': parent_name.split()[0] if parent_name else ''},
            'threads':   [{'type': 'customer', 'text': body_html}],
        }

        r = _req.post(f'{fs_api_url}/conversations', json=payload, headers=headers, timeout=15)
        if r.ok:
            conv_id = r.json().get('id')
            _logger.info(
                "Absence FreeScout conversation created: id=%s student=%s grade=%s",
                conv_id, student, grade
            )
        else:
            _logger.warning("Absence FreeScout creation failed: %s %s", r.status_code, r.text[:200])

    def _handle_school_account_help(self, data):
        """Look up a student email from the Google Directory cache and create a FS support ticket.

        Returns a follow-up message string to send to the customer, or None on failure.
        The ticket is created UNASSIGNED so the support team can follow up.
        """
        import json as _json
        import unicodedata
        import requests as _req

        cedula       = data.get('cedula', '').strip()
        student_name = data.get('student_name', '').strip()
        grade_raw    = data.get('grade_raw', '').strip()

        def _norm(s):
            """Lowercase, strip accents, collapse whitespace."""
            s = unicodedata.normalize('NFD', s)
            s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
            return ' '.join(s.lower().split())

        # --- 1. Verify cédula matches the identified partner ---
        partner = self.partner_id
        partner_identified = partner and not partner.name.startswith('Consulta WhatsApp')
        if partner_identified and cedula:
            partner_vat = _norm(partner.vat or '').replace('-', '').replace(' ', '')
            given_vat   = _norm(cedula).replace('-', '').replace(' ', '').lstrip('vejgp')
            stored_vat  = partner_vat.lstrip('vejgp')
            if stored_vat and given_vat and stored_vat != given_vat:
                _logger.warning(
                    "School account help: cédula mismatch conv=%d partner=%s given=%s stored=%s",
                    self.id, partner.name, cedula, partner.vat,
                )
                return (
                    "No pude verificar tu identidad con la cédula proporcionada. "
                    "Por favor, escribe a soporte@ueipab.edu.ve para que el equipo te ayude directamente."
                )

        # --- 2. Load Google Directory cache ---
        icp = self.env['ir.config_parameter'].sudo()
        directory_json = icp.get_param('school.student_directory_json', '')
        if not directory_json:
            _logger.warning("School account help: school.student_directory_json param not set")
            self._create_school_account_fs_ticket(cedula, student_name, grade_raw, email_found=None)
            return (
                "Nuestro directorio estudiantil no está disponible en este momento. "
                "He notificado al equipo de soporte (soporte@ueipab.edu.ve) para que te "
                "asistan con los datos de acceso de tu hijo/a."
            )

        try:
            directory = _json.loads(directory_json)
            students  = directory.get('students', [])
        except Exception:
            students = []

        # --- 3. Fuzzy name match ---
        target = _norm(student_name)
        # Split target into words for partial matching
        target_words = set(target.split())
        best_match = None
        best_score = 0

        for s in students:
            sname = _norm(s.get('name', ''))
            # Exact match wins immediately
            if sname == target:
                best_match = s
                break
            # Word-overlap score
            swords = set(sname.split())
            overlap = len(target_words & swords)
            if overlap > best_score and overlap >= min(2, len(target_words)):
                best_score = overlap
                best_match = s

        # --- 4. Build response and create FS ticket ---
        if best_match:
            email = best_match.get('email', '')
            grade = best_match.get('grade', grade_raw)
            _logger.info(
                "School account help: found student=%s email=%s grade=%s conv=%d",
                best_match.get('name'), email, grade, self.id,
            )
            self._create_school_account_fs_ticket(cedula, student_name, grade_raw, email_found=email)
            return (
                f"Encontré la cuenta institucional:\n"
                f"Alumno/a: {best_match.get('name')}\n"
                f"Nivel: {grade}\n"
                f"Correo institucional: {email}\n\n"
                f"Para recuperar la contraseña de Akdemia, usa este enlace:\n"
                f"https://edge.akdemia.com/login#resetPasswordModal\n\n"
                f"El equipo de soporte también ha sido notificado para seguimiento."
            )
        else:
            _logger.warning(
                "School account help: no match for '%s' in directory (conv=%d)",
                student_name, self.id,
            )
            self._create_school_account_fs_ticket(cedula, student_name, grade_raw, email_found=None)
            return (
                f"No encontré un alumno registrado con el nombre '{student_name}' "
                f"en nuestro directorio. He notificado al equipo de soporte "
                f"(soporte@ueipab.edu.ve) para que te asistan personalmente. "
                f"Puedes también escribirles directamente con el nombre completo del alumno/a."
            )

    def _create_school_account_fs_ticket(self, cedula, student_name, grade_raw, email_found=None):
        """Create an UNASSIGNED FreeScout soporte@ ticket for school account help follow-up."""
        import json as _json
        import requests as _req
        from datetime import datetime as _dt

        try:
            fs_config = _json.load(open('/opt/odoo-dev/config/freescout_api.json'))
        except Exception:
            _logger.error("School account FS ticket: cannot read freescout_api.json")
            return

        fs_api_url = fs_config['api_url']
        headers    = {'X-FreeScout-API-Key': fs_config['api_key'], 'Content-Type': 'application/json'}

        partner = self.partner_id
        parent_name  = (partner.name if partner and not partner.name.startswith('Consulta WhatsApp')
                        else 'Representante desconocido')
        parent_email = (partner.email or '') if partner else ''
        channel_lbl  = 'WhatsApp' if self.channel == 'whatsapp' else 'Telegram'
        contact_ref  = self.phone or self.telegram_chat_id or ''
        today        = _dt.now().strftime('%d/%m/%Y %H:%M')

        if email_found:
            status_line = f'<p><strong>Correo encontrado:</strong> {email_found}</p>'
            subject_tag = '[RESUELTO]'
        else:
            status_line = '<p><strong>Estado:</strong> Alumno/a NO encontrado en directorio — requiere verificación manual</p>'
            subject_tag = '[PENDIENTE]'

        subject   = f'[Glenda/{channel_lbl}] {subject_tag} Cuenta escolar — {student_name}'
        body_html = (
            f'<p><strong>Solicitud de ayuda con cuenta escolar recibida vía {channel_lbl}</strong></p>'
            f'<p><strong>Representante:</strong> {parent_name}<br/>'
            f'<strong>Contacto:</strong> {contact_ref}<br/>'
            f'<strong>Cédula proporcionada:</strong> {cedula}</p>'
            f'<p><strong>Alumno/a:</strong> {student_name}<br/>'
            f'<strong>Nivel/Año:</strong> {grade_raw}</p>'
            f'{status_line}'
            f'<p><em>Registrado automáticamente por Glenda AI — {today}</em></p>'
        )

        payload = {
            'type':      1,
            'mailboxId': 3,  # soporte@ueipab.edu.ve
            'subject':   subject,
            'status':    'active',
            'customer':  {
                'email':     parent_email or 'glenda-noreply@ueipab.edu.ve',
                'firstName': parent_name.split()[0] if parent_name else '',
            },
            'threads': [{'type': 'customer', 'text': body_html}],
        }

        r = _req.post(f'{fs_api_url}/conversations', json=payload, headers=headers, timeout=15)
        if r.ok:
            _logger.info("School account FS ticket created: id=%s student=%s", r.json().get('id'), student_name)
        else:
            _logger.warning("School account FS ticket failed: %s %s", r.status_code, r.text[:200])

    @api.model
    def _handle_telegram_inbound(self, chat_id, text, first_name='', photos=None, document=None):
        """Webhook entry point for Telegram messages. Analogous to _cron_poll_messages for WA."""
        icp = self.env['ir.config_parameter'].sudo()
        if icp.get_param('ai_agent.telegram_enabled', 'False').lower() != 'true':
            _logger.info("Telegram: disabled via ai_agent.telegram_enabled param")
            return
        dry_run = icp.get_param('ai_agent.dry_run', 'True').lower() == 'true'
        if dry_run:
            _logger.info("DRY_RUN: Telegram inbound chat_id=%s text=%r", chat_id, text[:60])

        # Handle /start command — may carry employee deep-link token (EMP_123)
        if text.startswith('/start'):
            payload = text[len('/start'):].strip()
            if payload.startswith('EMP_'):
                self._handle_telegram_employee_start(chat_id, payload, first_name, dry_run)
                return
            # Plain /start (no token) — send welcome and fall through to normal conversation

        # Build attachment if user sent a photo (e.g. payment receipt)
        extra_attachments = []
        if photos:
            tg = self.env['ai.agent.telegram.service']
            file_id = photos[-1]['file_id']   # Telegram sorts smallest→largest
            url = tg.get_file_url(file_id)
            if url:
                extra_attachments.append({'url': url, 'wa_id': 0})

        conv = self._get_or_create_telegram_conversation(chat_id, first_name)
        if not conv:
            return

        # Show typing indicator while Claude thinks — cosmetic, must never block reply
        if not dry_run:
            try:
                self.env['ai.agent.telegram.service'].send_chat_action(chat_id)
            except Exception:
                pass

        conv.action_process_reply(
            message_text=text or ('[foto]' if photos else '[documento]'),
            wa_message_id=0,
            extra_attachments=extra_attachments or None,
        )

    @api.model
    def _handle_telegram_employee_start(self, chat_id, payload, first_name, dry_run=False):
        """Handle /start EMP_123 deep-link — identify employee and send personalised welcome."""
        tg = self.env['ai.agent.telegram.service']
        try:
            emp_id = int(payload[4:])   # strip 'EMP_'
        except ValueError:
            tg.send_message(chat_id, "¡Hola! Puedes escribirme cualquier consulta sobre el colegio.")
            return

        emp = self.env['hr.employee'].sudo().browse(emp_id)
        if not emp.exists() or not emp.active:
            _logger.warning("Telegram /start EMP_%s: employee not found", emp_id)
            tg.send_message(chat_id,
                "¡Hola! No pude identificarte automáticamente. "
                "Escríbeme tu número de cédula para continuar.")
            return

        # Resolve partner — use Odoo user's partner (most reliable)
        partner = None
        if emp.user_id:
            partner = emp.user_id.partner_id
        if not partner:
            partner = self.env['res.partner'].sudo().search(
                [('email', '=', emp.work_email)], limit=1)

        if partner:
            # Link any existing placeholder conversations for this chat_id to the real partner
            placeholders = self.search([
                ('telegram_chat_id', '=', chat_id),
                ('partner_id.comment', 'like', f'telegram_chat_id:{chat_id}'),
            ])
            if placeholders:
                placeholders.sudo().write({'partner_id': partner.id})
                _logger.info(
                    "Telegram /start EMP_%s: linked %d conversations to partner %s",
                    emp_id, len(placeholders), partner.name,
                )

        first = emp.name.split()[0].title()
        _logger.info("Telegram /start EMP_%s → employee=%s chat_id=%s", emp_id, emp.name, chat_id)

        # Silent CEO alert — savepoint so a SQL failure doesn't abort the cursor
        try:
            icp = self.env['ir.config_parameter'].sudo()
            ceo_email = icp.get_param('wa_monitor.ceo_email', '')
            if ceo_email and not dry_run:
                with self.env.cr.savepoint():
                    self._notify_ceo_discuss(
                        f"📱 [Telegram] {emp.name} abrió @GlendaUeipabBot (identificado/a automáticamente)",
                        ceo_email,
                    )
        except Exception as exc:
            _logger.debug("Telegram employee CEO notify skipped: %s", exc)

        if dry_run:
            _logger.info("DRY_RUN: Would send welcome to %s (chat_id=%s)", emp.name, chat_id)
            return

        tg.send_message(chat_id,
            f"¡Hola, {first}! 👋\n\n"
            f"Soy <b>Glenda</b>, tu asistente virtual del Instituto Privado Andrés Bello. "
            f"Te identifiqué correctamente en el sistema.\n\n"
            f"Puedo ayudarte con:\n"
            f"• Tarifas e inscripciones 2026-2027\n"
            f"• Costos anuales y descuentos por hermanos\n"
            f"• Medios de pago\n"
            f"• Políticas del colegio\n"
            f"• Y cualquier consulta institucional\n\n"
            f"¿En qué te puedo ayudar hoy?"
        )

    @api.model
    def _get_or_create_telegram_conversation(self, chat_id, first_name=''):
        """Find or create a general_inquiry conversation for a Telegram chat_id."""
        from datetime import timedelta

        # Reuse an active conversation for this chat_id in the last 24 h
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        existing = self.search([
            ('telegram_chat_id', '=', chat_id),
            ('skill_id.code', '=', 'general_inquiry'),
            ('create_date', '>=', cutoff),
        ], limit=1, order='create_date desc')

        if existing:
            if existing.state in ('active', 'waiting'):
                return existing
            if existing.state in ('timeout', 'failed'):
                return None   # unresponsive — don't re-open within 24 h
            # resolved: allow a new conversation

        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'general_inquiry')], limit=1)
        if not skill:
            _logger.error("Telegram: general_inquiry skill not found")
            return None

        # Re-use partner from a previous Telegram conversation for this chat_id
        prev = self.search([('telegram_chat_id', '=', chat_id)],
                           limit=1, order='create_date desc')
        if prev and prev.partner_id:
            partner = prev.partner_id
        else:
            # Create a placeholder partner; the skill will identify them during the conversation
            name = first_name or f'Telegram {chat_id}'
            partner = self.env['res.partner'].sudo().create({
                'name':          name,
                'customer_rank': 1,
                'comment':       f'telegram_chat_id:{chat_id}',
            })
            _logger.info(
                "Telegram: new placeholder partner %d (%s) for chat_id=%s",
                partner.id, name, chat_id,
            )

        conv = self.sudo().create({
            'skill_id':         skill.id,
            'partner_id':       partner.id,
            'channel':          'telegram',
            'telegram_chat_id': chat_id,
            'phone':            '',
            'state':            'active',
        })
        _logger.info(
            "Telegram: created conversation %d for chat_id=%s partner=%s",
            conv.id, chat_id, partner.name,
        )

        # CEO alert — wrapped in savepoint so a SQL failure inside _notify_ceo
        # does NOT abort the PostgreSQL cursor and kill the subsequent reply flow.
        try:
            with self.env.cr.savepoint():
                conv._notify_ceo(
                    f"📱 [Telegram] {partner.name} inició chat — @GlendaUeipabBot"
                )
        except Exception as exc:
            _logger.debug("Telegram CEO notify skipped: %s", exc)

        return conv

    def _notify_ceo_telegram_event(self, event_label, detail=''):
        """Post a silent OdooBot DM to the CEO for Telegram conversation events.

        Only fires for channel='telegram'. No WA credit used.
        event_label examples: '✅ Resuelta', '⏱️ Timeout', '⚠️ Error'.
        """
        if self.channel != 'telegram':
            return
        try:
            icp = self.env['ir.config_parameter'].sudo()
            ceo_email = icp.get_param('wa_monitor.ceo_email', '')
            if not ceo_email:
                return
            partner = self.partner_id.name or f"Telegram {self.telegram_chat_id}"
            skill = self.skill_id.name or 'general_inquiry'
            msg = (
                f"📱 [Telegram] {event_label}\n"
                f"👤 {partner} | 🔧 {skill} | 💬 {self.turn_count} turnos\n"
            )
            if detail:
                msg += f"📝 {detail[:150]}"
            with self.env.cr.savepoint():
                self._notify_ceo_discuss(msg, ceo_email)
        except Exception as exc:
            _logger.debug("_notify_ceo_telegram_event failed: %s", exc)

    def _notify_ceo(self, message):
        """Send CEO monitoring alert via Odoo Discuss (OdooBot DM) + WA.

        Discuss is the primary channel (instant, no throttle).
        WA is secondary (may be delayed 120s by anti-spam throttle).
        Both channels are optional — controlled by ir.config_parameter:
          wa_monitor.ceo_email  → Discuss delivery
          wa_monitor.ceo_phone  → WA delivery
        """
        icp = self.env['ir.config_parameter'].sudo()
        dry_run = icp.get_param('ai_agent.dry_run', 'True').lower() == 'true'

        if dry_run:
            _logger.info("[CEO_NOTIFY dry_run] %s", message[:120])
            return

        # 1. Discuss (OdooBot DM) — primary, immediate
        ceo_email = icp.get_param('wa_monitor.ceo_email', '')
        if ceo_email:
            try:
                self._notify_ceo_discuss(message, ceo_email)
            except Exception as exc:
                _logger.warning("CEO Discuss notify failed: %s", exc)

        # 2. WA — secondary, subject to 120s anti-spam throttle
        ceo_phone = icp.get_param('wa_monitor.ceo_phone', '')
        if ceo_phone:
            try:
                self.env['ai.agent.whatsapp.service'].send_message(ceo_phone, message)
                _logger.info("CEO WA notify sent to %s", ceo_phone)
            except Exception as exc:
                _logger.warning("CEO WA notify failed: %s", exc)

    def _notify_ceo_tertiary(self, phone, body, wa_id):
        """Notify CEO once per message received on the tertiary WA number (+584148321963)."""
        import json as _json
        icp = self.env['ir.config_parameter'].sudo()

        # Dedup: track already-notified wa_ids in a rolling set (last 500)
        try:
            notified = set(_json.loads(icp.get_param('wa_monitor.tertiary_notified_ids', '[]')))
        except Exception:
            notified = set()

        if wa_id in notified:
            return

        notified.add(wa_id)
        if len(notified) > 500:
            notified = set(list(notified)[-500:])
        icp.set_param('wa_monitor.tertiary_notified_ids', _json.dumps(list(notified)))

        # Look up partner name
        partner = self.env['res.partner'].sudo().search([('mobile', '=', phone)], limit=1)
        name = partner.name if partner else phone

        self._notify_ceo(
            f"📞 Msg en terciario (+58 414-832-1963)\n"
            f"👤 {name}\n"
            f"📱 {phone}\n"
            f"💬 {body[:120]}"
        )

    def _notify_ceo_discuss(self, message, ceo_email):
        """Post message to CEO's OdooBot Discuss DM channel."""
        ceo_user = self.env['res.users'].sudo().search(
            [('email', '=', ceo_email)], limit=1)
        if not ceo_user:
            _logger.warning("CEO Discuss: user not found for email %s", ceo_email)
            return

        odoobot = self.env.ref('base.partner_root', raise_if_not_found=False)
        if not odoobot:
            return

        ceo_partner_id = ceo_user.partner_id.id
        bot_partner_id = odoobot.id

        # Find existing DM channel between CEO and OdooBot
        # Odoo 17: tables renamed mail_channel→discuss_channel, mail_channel_member→discuss_channel_member
        self.env.cr.execute("""
            SELECT c.id FROM discuss_channel c
            JOIN discuss_channel_member m1 ON m1.channel_id = c.id AND m1.partner_id = %s
            JOIN discuss_channel_member m2 ON m2.channel_id = c.id AND m2.partner_id = %s
            WHERE c.channel_type = 'chat'
            LIMIT 1
        """, [ceo_partner_id, bot_partner_id])
        row = self.env.cr.fetchone()

        if not row:
            # Channel doesn't exist yet — create it (Odoo 17: discuss.channel)
            channel = self.env['discuss.channel'].sudo().create({
                'channel_type': 'chat',
                'name': '',
            })
            self.env['discuss.channel.member'].sudo().create([
                {'channel_id': channel.id, 'partner_id': ceo_partner_id},
                {'channel_id': channel.id, 'partner_id': bot_partner_id},
            ])
            channel_id = channel.id
            _logger.info("CEO Discuss: created new OdooBot DM channel %d for %s", channel_id, ceo_email)
        else:
            channel_id = row[0]

        channel = self.env['discuss.channel'].sudo().browse(channel_id)
        html_body = message.replace('\n', '<br/>')
        channel.message_post(
            body=html_body,
            author_id=bot_partner_id,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )
        _logger.info("CEO Discuss notify sent to channel #%d (%s)", channel_id, ceo_email)

    def _notify_pagos_payment_receipt(self, receipt, partner, phone,
                                       payment_id=None, odoo_url=None,
                                       matched_invoice_info=None, duplicate_payment=None):
        """Send structured payment receipt email to pagos@ueipab.edu.ve.

        Includes draft payment deep link, invoice match result, and duplicate warning.
        partner: res.partner record or None.
        """
        icp = self.env['ir.config_parameter'].sudo()
        pagos_email = 'pagos@ueipab.edu.ve'
        from_email = icp.get_param('ai_agent.verification_email_from',
                                   'Glenda — Colegio Andrés Bello <recursoshumanos@ueipab.edu.ve>')
        partner_name = partner.name if partner else None
        banco  = receipt.get('banco') or '—'
        monto  = receipt.get('monto')
        moneda = receipt.get('moneda') or '—'
        ref    = receipt.get('referencia') or '—'

        # Format monto with thousands separator if it's a number
        monto_str = f"{float(monto):,.2f}" if monto is not None else '—'

        # BCV conversion line
        bcv_line = ''
        if moneda in ('VES', 'VEB') and monto:
            bcv_rate = self._get_bcv_rate_for_payment()
            if bcv_rate > 0:
                monto_usd = float(monto) / bcv_rate
                bcv_line = (f'<tr><td style="{_TD_LABEL}">Equiv. USD</td>'
                            f'<td style="{_TD_VAL}">'
                            f'<b>${monto_usd:,.2f}</b> '
                            f'<span style="color:#888;font-size:12px">(BCV {bcv_rate:,.2f})</span>'
                            f'</td></tr>')

        receipt_rows = ''.join(
            f'<tr><td style="{_TD_LABEL}">{k}</td><td style="{_TD_VAL}">{v}</td></tr>'
            for k, v in [
                ('Banco / Plataforma', banco),
                ('Tipo de pago',       receipt.get('tipo_pago') or '—'),
                ('Monto',              f'{monto_str} {moneda}'),
                ('Referencia',         ref),
                ('Fecha',              receipt.get('fecha') or '—'),
                ('Titular origen',     receipt.get('titular_origen') or '—'),
                ('Cuenta destino',     receipt.get('cuenta_destino') or '—'),
            ]
        ) + bcv_line

        # --- Status block ---
        if duplicate_payment:
            status_bg = '#fff3e0'
            status_color = '#e65100'
            status_icon = '⚠️'
            status_msg = (
                f'Referencia ya registrada — <b>{duplicate_payment.name}</b>. '
                f'No se creó borrador. Verificar si es envío duplicado.'
            )
        elif payment_id and odoo_url:
            inv_line = ''
            if matched_invoice_info:
                inv = matched_invoice_info['invoice']
                mtype = matched_invoice_info['match_type']
                mtype_label = {'exact': 'Coincidencia exacta', 'partial': 'Pago parcial'}.get(mtype, mtype)
                inv_line = (f'<br/><span style="color:#555;font-size:12px">'
                            f'Factura: <b>{inv.name}</b> · Pendiente: '
                            f'<b>${float(inv.amount_residual_signed):,.2f}</b> · {mtype_label}</span>')
            status_bg = '#e8f5e9'
            status_color = '#2e7d32'
            status_icon = '✅'
            status_msg = (
                f'Borrador creado: <b>#{payment_id}</b>{inv_line}<br/>'
                f'<a href="{odoo_url}" style="color:#1a2c5b;font-weight:bold">'
                f'→ Abrir y validar en Odoo</a>'
            )
        else:
            status_bg = '#f5f5f5'
            status_color = '#555'
            status_icon = 'ℹ️'
            reason = 'cliente no identificado' if not partner else 'sin factura activa'
            status_msg = f'No se creó borrador automático ({reason}). Registrar manualmente.'

        customer_line = (f'<b>Cliente:</b> {partner_name} · ' if partner_name else '')
        body = (
            f'<div style="font-family:Arial,sans-serif;max-width:580px">'
            f'<div style="background:#1a2c5b;padding:16px 20px;border-radius:8px 8px 0 0">'
            f'<h2 style="color:#fff;margin:0;font-size:18px">🧾 Comprobante de Pago — Glenda</h2>'
            f'<p style="color:rgba(255,255,255,0.75);margin:4px 0 0;font-size:13px">'
            f'Detectado automáticamente vía WhatsApp</p></div>'
            f'<div style="background:#f8fafc;padding:12px 20px;font-size:13px;color:#555">'
            f'{customer_line}<b>Teléfono:</b> {phone}</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:14px">'
            f'<tbody>{receipt_rows}</tbody></table>'
            f'<div style="background:{status_bg};padding:14px 20px;font-size:13px;'
            f'color:{status_color};border-top:1px solid #e0e0e0">'
            f'{status_icon} {status_msg}</div>'
            f'</div>'
        )

        subject = f'[Glenda] Pago — {phone} — {banco} {monto_str} {moneda}'.strip()
        try:
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'email_from': from_email,
                'email_to': pagos_email,
                'body_html': body,
                'auto_delete': True,
            })
            mail.send()
            _logger.info("Receipt notification sent to %s (payment_id=%s)", pagos_email, payment_id)
        except Exception as e:
            _logger.warning("Failed to send receipt notification: %s", e)

    # -------------------------------------------------------------------------
    # Payment receipt helpers
    # -------------------------------------------------------------------------

    # CSS shortcuts used in email tables
    _TD_LABEL = "padding:6px 12px;font-weight:bold;color:#1a2c5b;white-space:nowrap"
    _TD_VAL   = "padding:6px 12px"

    def _get_bcv_rate_for_payment(self):
        """Return current BCV rate (float) from ir.config_parameter."""
        import json as _j
        raw = self.env['ir.config_parameter'].sudo().get_param('ai_agent.bcv_rate_context', '')
        if not raw:
            return 0.0
        try:
            return float(_j.loads(raw).get('current', {}).get('rate', 0.0))
        except Exception:
            return 0.0

    def _resolve_journal_for_payment(self, banco, moneda):
        """Map bank name + currency to a journal_id.

        Config key: ai_agent.payment_journal_map (JSON).
        Fallback: Banco Venezuela VEB (id=162).
        """
        import json as _j
        fallback_veb = 162
        fallback_usd = 158
        if not banco:
            return fallback_usd if (moneda or '').upper() == 'USD' else fallback_veb

        raw = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.payment_journal_map', '')
        if not raw:
            return fallback_veb
        try:
            config = _j.loads(raw)
        except Exception:
            return fallback_veb

        banco_lower = banco.lower()
        moneda_key = (moneda or 'VES').upper()
        for keyword, currency_map in config.get('keywords', {}).items():
            if keyword in banco_lower:
                jid = currency_map.get(moneda_key) or currency_map.get('VES')
                if jid:
                    return jid
        return config.get('fallback_usd', fallback_usd) if moneda_key == 'USD' \
            else config.get('fallback_veb', fallback_veb)

    def _match_invoice_for_payment(self, partner, monto, moneda, bcv_rate):
        """Find best matching outstanding invoice for this payment.

        Converts VES amount to USD via BCV rate for comparison.
        Returns {'invoice': record, 'residual': float, 'match_type': str} or None.
        match_type: 'exact' (within 2%) | 'partial' (monto_usd < residual)
        """
        if not partner or not monto or float(monto) <= 0:
            return None

        if (moneda or '').upper() in ('VES', 'VEB') and bcv_rate > 0:
            monto_usd = float(monto) / bcv_rate
        else:
            monto_usd = float(monto)

        Move = self.env['account.move'].sudo()
        partner_ids = [partner.id] + list(partner.child_ids.ids)
        invoices = Move.search([
            ('partner_id', 'in', partner_ids),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('amount_residual_signed', '>', 0),
        ], order='invoice_date asc')

        best = None
        for inv in invoices:
            residual = float(inv.amount_residual_signed)
            if residual <= 0:
                continue
            if abs(monto_usd - residual) / residual <= 0.02:
                return {'invoice': inv, 'residual': residual, 'match_type': 'exact'}
            if monto_usd < residual and best is None:
                best = {'invoice': inv, 'residual': residual, 'match_type': 'partial'}
        return best

    def _check_duplicate_payment(self, partner_id, referencia):
        """Return existing inbound payment matching partner + last 4 ref digits (30-day window).

        Returns account.payment record or None.
        """
        import re
        from datetime import datetime, timedelta
        if not referencia:
            return None
        digits = re.sub(r'\D', '', str(referencia))
        last4 = digits[-4:] if len(digits) >= 4 else digits
        if not last4:
            return None
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        result = self.env['account.payment'].sudo().search([
            ('partner_id', '=', partner_id),
            ('ref', 'ilike', last4),
            ('date', '>=', cutoff),
            ('payment_type', '=', 'inbound'),
        ], limit=1)
        return result or None

    def _create_draft_payment(self, partner, receipt, journal_id, matched_invoice_info):
        """Create a draft account.payment from OCR receipt data.

        Stays in draft — accountant validates in Odoo (one click).
        Returns (payment_id, odoo_url) or (None, None) on failure.
        """
        from datetime import datetime
        import re

        monto  = receipt.get('monto') or 0.0
        moneda = (receipt.get('moneda') or 'VES').upper()
        ref    = receipt.get('referencia') or ''
        banco  = receipt.get('banco') or ''
        tipo   = receipt.get('tipo_pago') or ''
        fecha  = receipt.get('fecha') or ''

        currency_id = 2 if moneda in ('VES', 'VEB') else 1  # VEB=2, USD=1

        payment_date = datetime.now().strftime('%Y-%m-%d')
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
            try:
                payment_date = datetime.strptime(fecha[:10], fmt).strftime('%Y-%m-%d')
                break
            except (ValueError, TypeError):
                continue

        # Build ref field: bank reference + context
        parts = [ref] if ref else []
        parts += [p for p in [banco, tipo, f"WA {self.phone}"] if p]
        if matched_invoice_info:
            parts.append(f"Factura {matched_invoice_info['invoice'].name}")
        ref_field = ' | '.join(parts)[:190]  # account.payment ref field limit

        journal = self.env['account.journal'].sudo().browse(journal_id)
        method_line = journal.inbound_payment_method_line_ids[:1]

        vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id':   partner.id,
            'amount':       float(monto),
            'currency_id':  currency_id,
            'journal_id':   journal_id,
            'date':         payment_date,
            'ref':          ref_field,
        }
        if method_line:
            vals['payment_method_line_id'] = method_line.id

        try:
            payment = self.env['account.payment'].sudo().create(vals)
            base_url = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', 'https://odoo.ueipab.edu.ve')
            odoo_url = (f"{base_url}/web#id={payment.id}"
                        f"&model=account.payment&view_type=form")
            _logger.info("Draft payment #%d created: %s %s %s journal=%d",
                         payment.id, monto, moneda, partner.name, journal_id)
            return payment.id, odoo_url
        except Exception as e:
            _logger.error("Failed to create draft payment: %s", e)
            return None, None

    def _transcribe_audio(self, url):
        """Download an audio attachment and transcribe it via OpenAI Whisper API.

        Requires ir.config_parameter 'ai_agent.openai_api_key' to be set.
        Returns Spanish transcription string, or None on failure/no key.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('ai_agent.openai_api_key', '')
        if not api_key:
            _logger.info("Audio transcription skipped: ai_agent.openai_api_key not configured")
            return None

        try:
            audio_resp = requests.get(url, timeout=30)
            audio_resp.raise_for_status()
            audio_bytes = audio_resp.content
        except Exception as e:
            _logger.warning("Failed to download audio for transcription: %s", e)
            return None

        # Detect filename/extension for Whisper (must know the format)
        url_path = url.split('?')[0]
        ext = url_path.rsplit('.', 1)[-1].lower() if '.' in url_path else 'ogg'
        filename = f'audio.{ext}'

        try:
            whisper_resp = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers={'Authorization': f'Bearer {api_key}'},
                files={'file': (filename, audio_bytes, f'audio/{ext}')},
                data={'model': 'whisper-1', 'language': 'es'},
                timeout=60,
            )
            whisper_resp.raise_for_status()
            result = whisper_resp.json()
            transcription = result.get('text', '').strip()
            if transcription:
                _logger.info("Audio transcribed (%d chars): %s...", len(transcription), transcription[:60])
            return transcription or None
        except Exception as e:
            _logger.warning("Whisper transcription failed: %s", e)
            return None

    def _check_moderation(self, text):
        """Check message text against OpenAI Moderation API (free endpoint).

        Returns (flagged: bool, categories: list[str]).
        If no API key or request fails, returns (False, []) — fail open.
        """
        icp = self.env['ir.config_parameter'].sudo()
        api_key = icp.get_param('ai_agent.openai_api_key', '')
        if not api_key:
            return False, []

        try:
            resp = requests.post(
                'https://api.openai.com/v1/moderations',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'input': text, 'model': 'omni-moderation-latest'},
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json().get('results', [{}])[0]
            flagged = result.get('flagged', False)
            categories = [cat for cat, hit in result.get('categories', {}).items() if hit]
            return flagged, categories
        except Exception as e:
            _logger.warning("Moderation check failed (fail-open): %s", e)
            return False, []

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
        first_name = (self.partner_id.name or '').split()[0].title() if self.partner_id.name else 'Estimado/a'

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

    def _handle_escalation(self, reason):
        """Log escalation for bridge script to create Freescout ticket + notify group."""
        self.ensure_one()
        # Append if multiple escalations in same conversation
        existing = self.escalation_reason or ''
        timestamp = fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
        new_entry = f"[{timestamp}] {reason}"
        updated = f"{existing}\n{new_entry}".strip() if existing else new_entry

        vals = {'escalation_reason': updated}
        if not self.escalation_date:
            vals['escalation_date'] = fields.Datetime.now()
            vals['escalation_notified'] = False
        self.write(vals)

        self.message_post(body=_(
            "Escalacion registrada: %s. Pendiente creacion de ticket en Freescout."
        ) % reason)
        _logger.info("Conversation %s: escalation — %s", self.id, reason)

        self._notify_ceo(
            f"⚠️ Escalación Glenda\n"
            f"👤 {self.partner_id.name or self.phone}\n"
            f"📋 {reason[:120]}"
        )

    def _send_escalation_email(self, email_data):
        """Send an escalation email to HR or another department.

        Args:
            email_data: dict with keys:
                - to: recipient email address
                - subject: email subject
                - body_html: HTML body content
                - from_name: (optional) sender display name
        """
        self.ensure_one()
        dry_run = self._is_dry_run()
        icp = self.env['ir.config_parameter'].sudo()

        default_from = icp.get_param(
            'ai_agent.escalation_email_from',
            'UEIPAB - Glenda AI <soporte@ueipab.edu.ve>',
        )
        email_from = email_data.get('from_name', default_from)
        email_to = email_data['to']
        subject = email_data['subject']
        body_html = email_data['body_html']

        if dry_run:
            _logger.info(
                "DRY_RUN: Would send escalation email to %s — Subject: %s",
                email_to, subject)
        else:
            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_from': email_from,
                'email_to': email_to,
                'auto_delete': True,
            })
            mail.send()
            _logger.info(
                "Escalation email sent to %s for conversation %s — Subject: %s",
                email_to, self.id, subject)

        self.message_post(body=_(
            "Escalacion enviada por correo a %s: %s%s"
        ) % (email_to, subject, " (DRY RUN)" if dry_run else ""))

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
        self._notify_ceo_telegram_event('✅ Resuelta', summary)

    def action_timeout(self):
        """Mark conversation as timed out."""
        self.ensure_one()
        self.write({'state': 'timeout'})
        self.message_post(body=_("Conversacion cerrada por timeout (sin respuesta del cliente)."))
        self._notify_ceo_telegram_event('⏱️ Timeout', 'Sin respuesta del empleado')

    def action_force_resolve(self):
        """Manual resolve — works from form button or list server action."""
        for conv in self:
            if conv.state in ('active', 'waiting'):
                conv.action_resolve(summary='Resuelto manualmente')

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

        wa_msg_id = self._send_to_user(reminder_text)

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

        wa_msg_id = self._send_to_user(farewell)

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
    def _get_or_create_general_inquiry_conversation(self, phone, sender_account=''):
        """Return an active general_inquiry conversation for an unknown inbound phone.

        Creates a new conversation (and a placeholder partner if needed) when
        the message arrives on the dedicated primary WA account, the phone is not
        a group ID, and hasn't been seen in the last 24 hours.
        Returns None if the message should be ignored.

        Args:
            phone: normalized customer phone number
            sender_account: raw 'account' field from MassivaMóvil API (the WA
                account that received the message)
        """
        import re as _re
        from datetime import timedelta

        icp = self.env['ir.config_parameter'].sudo()
        wa_service = self.env['ai.agent.whatsapp.service']

        # Reject group IDs (contain '@')
        if '@' in phone:
            return None

        primary_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_primary_phone', '')
        )

        # Only handle messages arriving on the dedicated primary number.
        # The MassivaMóvil API returns the receiving account as a phone number
        # in the message's 'account' field — compare normalized against primary_phone.
        if sender_account:
            normalized_account = wa_service._normalize_phone(sender_account)
            if normalized_account != primary_phone:
                return None

        # Skip messages from our own WA account phones (avoid self-loops)
        backup_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_backup_phone', '')
        )
        tertiary_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_tertiary_phone', '')
        )
        own_phones = {p for p in (primary_phone, backup_phone, tertiary_phone) if p}
        if phone in own_phones:
            return None

        # If a general_inquiry conversation already exists for this phone in the
        # last 24h, return it if still open; otherwise skip (avoid re-triggering).
        cutoff = fields.Datetime.now() - timedelta(hours=24)
        existing = self.search([
            ('phone', '=', phone),
            ('skill_id.code', '=', 'general_inquiry'),
            ('create_date', '>=', cutoff),
        ], limit=1, order='create_date desc')
        if existing:
            if existing.state in ('active', 'waiting'):
                return existing
            if existing.state in ('timeout', 'failed'):
                return None  # unresponsive or broken conv — don't re-open within 24h
            # state == 'resolved': customer engaged and completed — allow new conv
            # (e.g. farewell "Gracias" after a handoff deserves an acknowledgment)

        # Locate the skill record
        skill = self.env['ai.agent.skill'].sudo().search(
            [('code', '=', 'general_inquiry')], limit=1
        )
        if not skill:
            _logger.warning("general_inquiry skill not found — cannot create conversation for %s", phone)
            return None

        # Find an Odoo partner matching this phone.
        # Odoo stores VE phones with spaces (+58 414 2337463) while the API
        # returns them in E.164 (+584142337463).  Build a set of candidate
        # values covering both formats and skip placeholder partners.
        all_digits = _re.sub(r'[^\d]', '', phone)  # e.g. '584142337463'
        phone_candidates = []
        if len(all_digits) == 12 and all_digits.startswith('58'):
            local10 = all_digits[2:]  # '4142337463'
            area, num = local10[:3], local10[3:]
            # Prioritize formatted (Odoo-standard) before raw E.164
            phone_candidates = [
                f'+58 {area} {num}',  # '+58 414 2337463'
                f'0{local10}',        # '04142337463'
                phone,                # '+584142337463' (E.164 fallback)
            ]
        else:
            phone_candidates = [phone]
        _NO_PLACEHOLDER = ('name', 'not like', 'Consulta WhatsApp')
        partner = None
        for cand in phone_candidates:
            partner = self.env['res.partner'].sudo().search(
                ['&', _NO_PLACEHOLDER, '|', ('phone', '=', cand), ('mobile', '=', cand)],
                limit=1,
            )
            if partner:
                break
        if not partner and len(all_digits) >= 7:
            # Last-resort: match on last 7 digits (local number without area code)
            last7 = all_digits[-7:]
            partner = self.env['res.partner'].sudo().search([
                '&', _NO_PLACEHOLDER,
                '|', ('phone', 'like', last7), ('mobile', 'like', last7),
            ], limit=1)

        if not partner:
            partner = self.env['res.partner'].sudo().create({
                'name': f'Consulta WhatsApp {phone}',
                'mobile': phone,
                'customer_rank': 1,
            })
            _logger.info("Created placeholder partner for unknown WA contact: %s", phone)

        conversation = self.sudo().create({
            'skill_id': skill.id,
            'partner_id': partner.id,
            'phone': phone,
            'state': 'active',
            'last_message_date': fields.Datetime.now(),
            'last_sender': 'customer',
        })
        _logger.info(
            "Created general_inquiry conversation %d for phone %s (partner: %s)",
            conversation.id, phone, partner.name,
        )

        # CEO monitoring: alert when a known debtor contacts Glenda
        if partner.customer_rank:
            balance = sum(self.env['account.move'].sudo().search([
                ('partner_id', 'in', [partner.id] + partner.child_ids.ids),
                ('move_type', 'in', ['out_invoice', 'out_receipt']),
                ('state', '=', 'posted'),
                ('payment_state', 'not in', ['paid', 'reversed']),
            ]).mapped('amount_residual'))
            if balance >= 1.0:
                conversation._notify_ceo(
                    f"📱 Cliente contactó a Glenda\n"
                    f"👤 {partner.name}\n"
                    f"💰 Saldo: ${balance:,.2f} USD pendiente\n"
                    f"📞 {phone}"
                )

        return conversation

    @api.model
    def _cron_poll_messages(self):
        """Cron: poll WhatsApp API for incoming messages (fallback to webhook).

        Groups multiple messages from the same conversation into a single
        batch to avoid cascading misinterpretation by Claude when a customer
        sends several rapid messages.
        """
        if not self._is_active_environment():
            return

        # Prevent concurrent cron runs from re-processing the same messages.
        # Without this, a slow run (Claude API + 120s WA cooldowns) can overlap
        # with the next scheduled run. The second run reads an empty
        # ai.agent.message table (uncommitted by the first) and duplicates every
        # conversation. pg_try_advisory_xact_lock is released automatically on
        # transaction commit/rollback, so no cleanup needed.
        self.env.cr.execute("SELECT pg_try_advisory_xact_lock(941489421)")  # arbitrary unique int
        if not self.env.cr.fetchone()[0]:
            _logger.info("Poll cron: another instance is still running — skipping this run")
            return

        # Schedule is enforced per-conversation based on skill.respect_schedule.
        # Skills with respect_schedule=False (e.g. general_inquiry) are always
        # processed; critical business skills are gated by the contact window.
        within_schedule = self._is_within_schedule()

        wa_service = self.env['ai.agent.whatsapp.service']
        dry_run = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.dry_run', 'True'
        ).lower() == 'true'

        if dry_run:
            _logger.info("DRY_RUN: Would poll WhatsApp for new messages")
            return

        # Poll primary account only. MassivaMóvil API ignores the 'account'
        # filter param and returns messages from ALL linked accounts, so we
        # enforce the primary-account restriction ourselves per-message below.
        icp = self.env['ir.config_parameter'].sudo()
        primary_account_id = icp.get_param('ai_agent.whatsapp_account_id', '') or ''
        primary_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_primary_phone', '')
        )
        backup_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_backup_phone', '')
        )
        tertiary_phone = wa_service._normalize_phone(
            icp.get_param('ai_agent.whatsapp_tertiary_phone', '')
        )
        own_phones = {p for p in (primary_phone, backup_phone, tertiary_phone) if p}

        try:
            messages = wa_service.fetch_received(limit=50, account_id=primary_account_id or None)
        except Exception as e:
            _logger.error("Failed to poll WhatsApp messages: %s", e)
            return

        # Phase 1: Collect and group messages by conversation
        from collections import OrderedDict
        conv_groups = OrderedDict()  # conv_id -> {'conversation': conv, 'items': [{'body', 'wa_id'}]}

        for msg in messages:
            # API uses 'recipient' for the other party's phone, 'phone' from webhook
            raw_phone = msg.get('recipient') or msg.get('phone', '')
            phone = wa_service._normalize_phone(raw_phone)
            body = msg.get('message', '')
            wa_id = msg.get('id', 0)
            attachment = msg.get('attachment')
            sender_account = msg.get('account', '')

            if not phone or (not body and not attachment):
                continue

            # Reject group IDs early (before searching conversations)
            if '@' in raw_phone:
                continue

            # Account guard: only process messages received on the primary number.
            # The API returns messages from ALL linked accounts regardless of the
            # filter param. Check both phone and UUID formats since the API may
            # return either. Applied before any conversation lookup so existing
            # waiting/active conversations cannot be fed from backup/tertiary numbers.
            if sender_account:
                normalized_sa = wa_service._normalize_phone(sender_account)
                if normalized_sa != primary_phone and sender_account != primary_account_id:
                    # CEO monitoring: alert on messages received on the tertiary number
                    if normalized_sa == tertiary_phone and wa_id and phone not in own_phones:
                        self._notify_ceo_tertiary(phone, body or '[imagen/audio]', wa_id)
                    _logger.info(
                        "Ignoring message from %s: received on non-primary account (%s)",
                        phone, sender_account)
                    continue

            # Dedup check FIRST — if this message was already processed, skip
            # entirely before doing any conversation lookup or creation.
            if self.env['ai.agent.message'].search([
                ('whatsapp_message_id', '=', wa_id),
            ], limit=1):
                continue

            # Find active conversation for this phone
            conversation = self.search([
                ('phone', '=', phone),
                ('state', 'in', ('waiting', 'active')),
            ], limit=1, order='last_message_date desc')

            if not conversation:
                conversation = self._get_or_create_general_inquiry_conversation(
                    phone, sender_account=sender_account
                )
                if not conversation:
                    _logger.info("No active conversation for phone %s, ignoring message", phone)
                    continue
                _logger.info("General inquiry conversation %d created for phone %s", conversation.id, phone)

            # Enforce schedule per skill: skip scheduled skills outside contact window
            if conversation.skill_id.respect_schedule and not within_schedule:
                _logger.info(
                    "Outside schedule: deferring reply for skill '%s' (conv %d, %s)",
                    conversation.skill_id.code, conversation.id, phone)
                continue

            if conversation.id not in conv_groups:
                conv_groups[conversation.id] = {
                    'conversation': conversation,
                    'items': [],
                }
            conv_groups[conversation.id]['items'].append({
                'body': body or '',
                'wa_id': wa_id,
                'attachment': attachment if attachment else None,
            })

        # Phase 2: Process each conversation batch (isolated per conversation)
        for conv_id, data in conv_groups.items():
            conv = data['conversation']
            items = data['items']
            try:
                with self.env.cr.savepoint():
                    if len(items) == 1:
                        item = items[0]
                        conv.action_process_reply(
                            item['body'], wa_message_id=item['wa_id'],
                            attachment_url=item.get('attachment'),
                        )
                    else:
                        combined = '\n'.join(item['body'] for item in items if item['body'])
                        _logger.info(
                            "Conversation %d: batching %d messages into single interaction",
                            conv_id, len(items))
                        first_att = items[0].get('attachment')
                        extra_atts = [{'url': i['attachment'], 'wa_id': i['wa_id']}
                                      for i in items[1:] if i.get('attachment')]
                        extra_ids = [i['wa_id'] for i in items[1:] if not i.get('attachment')]
                        conv.action_process_reply(
                            combined,
                            wa_message_id=items[0]['wa_id'],
                            extra_wa_ids=extra_ids or None,
                            attachment_url=first_att,
                            extra_attachments=extra_atts or None,
                        )
            except Exception as e:
                _logger.error(
                    "Error processing conversation %d (%s): %s",
                    conv_id, conv.partner_id.name, e)

    @api.model
    def _cron_check_timeouts(self):
        """Cron: check waiting conversations for reminders or timeout.

        Logic per conversation:
        1. If skill.send_reminders is False → close silently after one interval (no WA).
        2. If currently in proactive quiet hours (20:30–07:30 VET) → defer reminder
           send until the window ends; silent timeouts (no WA) still proceed.
        3. If reminder_count < max_reminders → send reminder WA.
        4. If reminder_count >= max_reminders → timeout silently.
        """
        if not self._is_active_environment():
            return

        from datetime import timedelta
        within_schedule = self._is_within_schedule()
        in_quiet = self._in_proactive_quiet_hours()
        conversations = self.search([('state', '=', 'waiting')])

        now = fields.Datetime.now()
        for conv in conversations:
            skill = conv.skill_id
            # Skip reminders/timeouts outside schedule for skills that respect it
            if skill.respect_schedule and not within_schedule:
                continue
            interval_hours = skill.reminder_interval_hours or 24
            max_reminders = skill.max_reminders if skill.max_reminders >= 0 else 2

            if not conv.last_message_date:
                continue

            if conv.silent:
                continue

            deadline = conv.last_message_date + timedelta(hours=interval_hours)
            if now <= deadline:
                continue

            try:
                with self.env.cr.savepoint():
                    if not skill.send_reminders:
                        # Silent mode: no reminder WA — close after first interval
                        conv.action_timeout()
                    elif in_quiet and conv.reminder_count < max_reminders:
                        # Proactive quiet hours: defer WA reminder, check again later
                        _logger.info(
                            "Timeout cron: quiet hours — deferring reminder for conv %d (%s)",
                            conv.id, conv.partner_id.name or conv.phone)
                    elif conv.reminder_count < max_reminders:
                        conv._send_reminder()
                    else:
                        conv.action_timeout()
            except Exception as e:
                _logger.error(
                    "Timeout cron: error processing conversation %d (%s skill): %s",
                    conv.id, conv.skill_id.code, e)

    @api.model
    def _cron_archive_attachments(self):
        """Cron: download image/document attachments to ir.attachment before URL expiry."""
        if not self._is_active_environment():
            return

        import base64
        from datetime import timedelta
        now = fields.Datetime.now()
        min_age = now - timedelta(minutes=10)
        max_age = now - timedelta(hours=72)

        messages = self.env['ai.agent.message'].search([
            ('attachment_url', '!=', False),
            ('attachment_id', '=', False),
            ('attachment_type', 'in', ('image', 'document')),
            ('timestamp', '<=', min_age),
            ('timestamp', '>=', max_age),
        ], limit=20)

        for msg in messages:
            try:
                resp = requests.get(msg.attachment_url, timeout=30)
                resp.raise_for_status()
                content_type = resp.headers.get('Content-Type', 'image/jpeg')
                filename = msg.attachment_url.split('/')[-1].split('?')[0] or 'attachment.jpg'
                attachment = self.env['ir.attachment'].sudo().create({
                    'name': 'WA_%d_%s' % (msg.whatsapp_message_id, filename),
                    'type': 'binary',
                    'datas': base64.b64encode(resp.content),
                    'mimetype': content_type,
                    'res_model': 'ai.agent.message',
                    'res_id': msg.id,
                })
                msg.write({'attachment_id': attachment.id})
                _logger.info("Archived attachment for msg %d: %s (%d bytes)",
                             msg.id, filename, len(resp.content))
            except Exception as e:
                _logger.warning("Failed to archive attachment for msg %d: %s", msg.id, e)

    @api.model
    def _cron_check_credits(self):
        """Cron: check MassivaMóvil + Anthropic credit levels.

        Uses a consecutive-failure counter (ai_agent.credits_fail_count) to
        avoid false-positive alerts from transient network timeouts.
        Kill switch + alert only fires after N consecutive failures
        (ai_agent.credits_fail_threshold, default 2).
        """
        if not self._is_active_environment():
            return

        ICP = self.env['ir.config_parameter'].sudo()
        wa_ok, wa_detail = self._check_whatsapp_credits()
        claude_ok, claude_detail = self._check_claude_credits()

        credits_ok = wa_ok and claude_ok
        was_ok = ICP.get_param('ai_agent.credits_ok', 'True').lower() == 'true'
        threshold = int(ICP.get_param('ai_agent.credits_fail_threshold', '2'))
        fail_count = int(ICP.get_param('ai_agent.credits_fail_count', '0'))

        if credits_ok:
            # Clean check — reset counter
            if fail_count > 0:
                ICP.set_param('ai_agent.credits_fail_count', '0')
                _logger.info("Credit Guard: transient issue cleared (was %d/%d fails)", fail_count, threshold)
            if not was_ok:
                # Recovery: NOT OK → OK
                ICP.set_param('ai_agent.credits_ok', 'True')
                _logger.info("Credit Guard: credits restored, re-enabling AI Agent")
        else:
            new_count = fail_count + 1
            ICP.set_param('ai_agent.credits_fail_count', str(new_count))
            _logger.warning(
                "Credit Guard: consecutive failure %d/%d — WA: %s | Claude: %s",
                new_count, threshold, wa_detail, claude_detail,
            )
            if new_count >= threshold and was_ok:
                # Confirmed failure: kill switch + alert
                ICP.set_param('ai_agent.credits_ok', 'False')
                self._send_credit_alert(wa_ok, wa_detail, claude_ok, claude_detail, new_count, threshold)
                _logger.warning(
                    "Credit Guard: KILL SWITCH activated after %d consecutive failures", new_count
                )

    def _check_whatsapp_credits(self):
        """Check MassivaMóvil subscription remaining sends.

        Returns (ok: bool, detail: str).
        """
        ICP = self.env['ir.config_parameter'].sudo()
        threshold = int(ICP.get_param('ai_agent.wa_sends_threshold', '50'))
        try:
            wa_service = self.env['ai.agent.whatsapp.service']
            config = wa_service._get_config()
            url = config['base_url'].rstrip('/') + '/get/subscription'
            resp = requests.get(url, params={'secret': config['secret']}, timeout=15)
            resp.raise_for_status()
            data = resp.json().get('data', {})
            usage = data.get('usage', {}).get('wa_send', {})
            used = int(usage.get('used', 0))
            limit = int(usage.get('limit', 0))
            remaining = limit - used
            detail = f"WhatsApp: {remaining}/{limit} envios restantes (umbral: {threshold})"
            return (remaining >= threshold, detail)
        except Exception as e:
            detail = f"WhatsApp: error al consultar suscripcion — {e}"
            _logger.error("Credit Guard: %s", detail)
            return (False, detail)  # Fail-safe: treat error as depleted

    def _check_claude_credits(self):
        """Check Anthropic spend by aggregating token usage from ai.agent.message.

        Returns (ok: bool, detail: str).
        """
        ICP = self.env['ir.config_parameter'].sudo()
        spend_limit = float(ICP.get_param('ai_agent.claude_spend_limit_usd', '4.50'))
        input_rate = float(ICP.get_param('ai_agent.claude_input_rate', '0.000001'))
        output_rate = float(ICP.get_param('ai_agent.claude_output_rate', '0.000005'))

        # Aggregate all token usage
        self.env.cr.execute("""
            SELECT COALESCE(SUM(ai_input_tokens), 0),
                   COALESCE(SUM(ai_output_tokens), 0)
            FROM ai_agent_message
            WHERE ai_input_tokens > 0 OR ai_output_tokens > 0
        """)
        total_in, total_out = self.env.cr.fetchone()
        spend = (total_in * input_rate) + (total_out * output_rate)

        detail = (f"Claude: ${spend:.4f} USD gastados "
                  f"(limite: ${spend_limit:.2f}, "
                  f"tokens: {total_in:,} in / {total_out:,} out)")
        return (spend < spend_limit, detail)

    def _send_credit_alert(self, wa_ok, wa_detail, claude_ok, claude_detail, fail_count=1, threshold=1):
        """Send email alert when credits are confirmed low (after N consecutive failures)."""
        problems = []
        if not wa_ok:
            problems.append(wa_detail)
        if not claude_ok:
            problems.append(claude_detail)

        items_html = ''.join(f'<li>{p}</li>' for p in problems)
        body_html = (
            '<h3>AI Agent — Alerta de Creditos</h3>'
            '<p>El sistema de AI Agent ha sido <strong>desactivado automaticamente</strong> '
            'por creditos insuficientes:</p>'
            f'<ul>{items_html}</ul>'
            f'<p><em>Confirmado tras {fail_count} chequeos consecutivos fallidos '
            f'(umbral: {threshold}). No es una alerta transitoria.</em></p>'
            '<p>Todas las conversaciones de WhatsApp y consultas a Claude AI '
            'han sido pausadas hasta que se recarguen los creditos.</p>'
            '<p><strong>Accion requerida:</strong> Recargar creditos en el servicio '
            'afectado. El sistema se reactivara automaticamente en el proximo chequeo (30 min).</p>'
        )

        mail = self.env['mail.mail'].sudo().create({
            'subject': '[UEIPAB] AI Agent — Creditos Agotados',
            'body_html': body_html,
            'email_from': 'soporte@ueipab.edu.ve',
            'email_to': 'soporte@ueipab.edu.ve',
            'email_cc': 'gustavo.perdomo@ueipab.edu.ve',
            'auto_delete': True,
        })
        mail.send()
        _logger.warning("Credit Guard: ALERT sent — %s", '; '.join(problems))

    @api.model
    def _cron_start_ack_reminders(self):
        """Stagger-start draft payslip_ack_reminder conversations.

        Shares the same capacity limits as HR data collection:
        - ai_agent.stagger_batch_size (default 2)
        - ai_agent.stagger_max_active (default 10)
        """
        if not self._is_active_environment():
            return

        ICP = self.env['ir.config_parameter'].sudo()
        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'payslip_ack_reminder')], limit=1)
        if not skill:
            return

        batch_size = int(ICP.get_param('ai_agent.stagger_batch_size', '2'))
        max_active = int(ICP.get_param('ai_agent.stagger_max_active', '10'))
        active_count = self.search_count([('state', 'in', ('active', 'waiting'))])

        if active_count >= max_active:
            _logger.info("Ack reminder stagger: at capacity (%d/%d active), skipping.",
                         active_count, max_active)
            return

        to_start = min(batch_size, max_active - active_count)
        drafts = self.search([
            ('skill_id', '=', skill.id),
            ('state', '=', 'draft'),
        ], order='create_date asc', limit=to_start)

        if not drafts:
            return

        _logger.info("Ack reminder stagger: starting %d draft conversations (active=%d/%d)",
                     len(drafts), active_count, max_active)

        for conv in drafts:
            try:
                conv.action_start()
                self.env.cr.commit()
                _logger.info("Ack reminder stagger: started conv #%d (%s)",
                             conv.id, conv.partner_id.name)
            except Exception:
                self.env.cr.rollback()
                _logger.exception("Ack reminder stagger: failed to start conv #%d", conv.id)

    @api.model
    def _cron_check_ack_acknowledged(self):
        """Auto-resolve payslip_ack_reminder conversations when payslip is acknowledged.

        Runs every 30 min. Checks active/waiting conversations where the linked
        payslip's is_acknowledged flag is now True, and resolves them automatically.
        """
        if not self._is_active_environment():
            return

        skill = self.env['ai.agent.skill'].search(
            [('code', '=', 'payslip_ack_reminder')], limit=1)
        if not skill:
            return

        conversations = self.search([
            ('skill_id', '=', skill.id),
            ('source_model', '=', 'hr.payslip'),
            ('state', 'in', ('active', 'waiting')),
        ])

        resolved = 0
        for conv in conversations:
            if not conv.source_id:
                continue
            payslip = self.env['hr.payslip'].browse(conv.source_id)
            if not payslip.exists():
                continue
            if payslip.is_acknowledged:
                try:
                    with self.env.cr.savepoint():
                        conv.action_resolve(
                            summary='Conformidad recibida — empleado confirmó via portal')
                        resolved += 1
                        _logger.info(
                            "Ack reminder: conv #%d auto-resolved (payslip #%d acknowledged)",
                            conv.id, payslip.id)
                except Exception:
                    _logger.exception(
                        "Ack reminder: failed to auto-resolve conv #%d", conv.id)
