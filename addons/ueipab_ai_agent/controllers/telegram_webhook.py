import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TelegramWebhookController(http.Controller):

    @http.route(
        '/ai-agent/telegram/webhook',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def telegram_webhook(self, **kwargs):
        """Receive Telegram updates and delegate to the conversation model."""
        try:
            data = request.get_json_data()

            # Telegram sends 'message' for new messages, 'edited_message' for edits
            message = data.get('message') or data.get('edited_message')
            if not message:
                return {}   # other update types (inline_query, etc.) — ignore

            chat_id    = str(message['chat']['id'])
            text       = message.get('text', '').strip()
            first_name = message.get('from', {}).get('first_name', '')
            # photo: list of PhotoSize objects (sorted smallest→largest by Telegram)
            photos   = message.get('photo')
            document = message.get('document')

            _logger.info(
                "Telegram inbound: chat_id=%s name=%r text=%r photo=%s",
                chat_id, first_name, text[:60], bool(photos),
            )

            request.env['ai.agent.conversation'].sudo()._handle_telegram_inbound(
                chat_id   = chat_id,
                text      = text,
                first_name= first_name,
                photos    = photos,
                document  = document,
            )
        except Exception:
            _logger.exception("Telegram webhook unhandled error")

        # Always return 200 OK — Telegram retries on any other status
        return {}
