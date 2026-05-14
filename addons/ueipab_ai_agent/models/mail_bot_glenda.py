import logging
import re
from html import unescape

from odoo import models

_logger = logging.getLogger(__name__)

# Number of previous channel messages to include as conversation history
_MAX_HISTORY = 10


class MailBotGlenda(models.AbstractModel):
    _inherit = 'mail.bot'

    def _get_answer(self, record, body, values, command):
        # Only intercept private direct-message channels (the OdooBot 1-on-1 chat)
        if not (hasattr(record, 'channel_type') and record.channel_type == 'chat'):
            return super()._get_answer(record, body, values, command)

        # Respect dry_run — skip real Claude calls in test mode
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('ai_agent.dry_run', 'True').lower() == 'true':
            return super()._get_answer(record, body, values, command)

        plain = _strip_html(body)
        if not plain:
            return super()._get_answer(record, body, values, command)

        try:
            system_prompt = self._glenda_system_prompt()
            messages = self._glenda_history(record, plain)
            result = self.env['ai.agent.claude.service'].generate_response(
                system_prompt=system_prompt,
                messages=messages,
            )
            reply = (result.get('content') or '').strip()
            if reply:
                _logger.info(
                    "Glenda/OdooBot: user=%s channel=%s reply=%d chars",
                    self.env.user.login, record.id, len(reply),
                )
                return reply
        except Exception:
            _logger.exception("Glenda OdooBot bridge failed — falling back to default OdooBot")

        return super()._get_answer(record, body, values, command)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _glenda_system_prompt(self):
        # Import the shared institutional knowledge block from the skill
        from odoo.addons.ueipab_ai_agent.skills.general_inquiry import _INSTITUTIONAL_KNOWLEDGE

        user_name = self.env.user.name
        return (
            "Eres Glenda, asistente virtual del Instituto Privado Andrés Bello, "
            "respondiendo preguntas del personal interno a través del chat de Odoo Discuss.\n\n"
            f"Estás hablando con {user_name}, miembro del equipo del colegio.\n"
            "Responde siempre en español venezolano, de forma clara y profesional.\n"
            "Eres útil para resolver dudas sobre tarifas, inscripciones, políticas del colegio, "
            "costos anuales, descuentos por hermanos y cualquier información institucional.\n"
            "No uses marcadores ACTION: ni menciones WhatsApp — estás en el chat interno de Odoo.\n"
            "Responde solo con texto plano, sin markdown ni asteriscos de formato.\n\n"
            + _INSTITUTIONAL_KNOWLEDGE
        )

    def _glenda_history(self, channel, current_body):
        """Build the Claude messages list from channel history + current message."""
        bot_partner_id = self.env.ref('base.partner_root').id

        # Fetch recent messages newest-first, then reverse to chronological
        msgs = self.env['mail.message'].search([
            ('res_id', '=', channel.id),
            ('model', '=', 'discuss.channel'),
            ('message_type', 'in', ('comment', 'email')),
            ('body', '!=', False),
        ], order='id desc', limit=_MAX_HISTORY + 1)

        # Reverse to chronological; drop the last (= current message, already in current_body)
        msgs = list(reversed(msgs))
        if msgs:
            msgs = msgs[:-1]

        history = []
        for msg in msgs:
            plain = _strip_html(msg.body)
            if not plain:
                continue
            role = 'assistant' if msg.author_id.id == bot_partner_id else 'user'
            history.append({'role': role, 'content': plain})

        # Claude requires the conversation to start with 'user'
        while history and history[0]['role'] == 'assistant':
            history.pop(0)

        # Merge consecutive same-role messages (Claude API requires strict alternation)
        merged = []
        for entry in history:
            if merged and merged[-1]['role'] == entry['role']:
                merged[-1]['content'] += '\n' + entry['content']
            else:
                merged.append(dict(entry))

        merged.append({'role': 'user', 'content': current_body})
        return merged


def _strip_html(html):
    """Strip HTML tags and decode entities, returning clean plain text."""
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    return ' '.join(unescape(text).split())
