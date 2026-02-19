import logging

import requests

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

    # Escalation tracking
    escalation_date = fields.Datetime('Fecha Escalacion')
    escalation_reason = fields.Text('Razon Escalacion')
    escalation_freescout_id = fields.Integer('Freescout Ticket #')
    escalation_notified = fields.Boolean('Equipo Notificado', default=False)

    # Alternative contact info (captured when a family member provides a different number)
    alternative_phone = fields.Char('Telefono Alternativo')

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
            msg_vals['attachment_url'] = attachment_url
            msg_vals['attachment_type'] = self._detect_attachment_type(attachment_url)
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
        """Cron: poll WhatsApp API for incoming messages (fallback to webhook).

        Groups multiple messages from the same conversation into a single
        batch to avoid cascading misinterpretation by Claude when a customer
        sends several rapid messages.
        """
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

            if not phone or (not body and not attachment):
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

        # Phase 2: Process each conversation batch
        for conv_id, data in conv_groups.items():
            conv = data['conversation']
            items = data['items']
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

        Sets ai_agent.credits_ok = False if either service is low,
        sends email alert to soporte + gustavo.
        """
        if not self._is_active_environment():
            return

        ICP = self.env['ir.config_parameter'].sudo()
        wa_ok, wa_detail = self._check_whatsapp_credits()
        claude_ok, claude_detail = self._check_claude_credits()

        credits_ok = wa_ok and claude_ok
        was_ok = ICP.get_param('ai_agent.credits_ok', 'True').lower() == 'true'

        if not credits_ok and was_ok:
            # Transition OK → NOT OK: kill switch + alert
            ICP.set_param('ai_agent.credits_ok', 'False')
            self._send_credit_alert(wa_ok, wa_detail, claude_ok, claude_detail)
            _logger.warning("Credit Guard: KILL SWITCH activated — outbound disabled")
        elif credits_ok and not was_ok:
            # Transition NOT OK → OK: auto-recover
            ICP.set_param('ai_agent.credits_ok', 'True')
            _logger.info("Credit Guard: credits restored, re-enabling AI Agent")

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

    def _send_credit_alert(self, wa_ok, wa_detail, claude_ok, claude_detail):
        """Send email alert when credits are low."""
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
