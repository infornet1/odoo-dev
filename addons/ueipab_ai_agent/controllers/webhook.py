import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AiAgentWebhook(http.Controller):

    @http.route('/ai-agent/webhook/whatsapp', type='json', auth='none',
                methods=['POST'], csrf=False)
    def whatsapp_webhook(self, **kwargs):
        """Receive incoming WhatsApp messages from MassivaMóvil.

        Expected payload:
            {
                "secret": "...",
                "type": "whatsapp",
                "data": {
                    "id": 123,
                    "wid": "...",
                    "phone": "+58...",
                    "message": "text content",
                    "attachment": null,
                    "timestamp": 1234567890
                }
            }
        """
        try:
            data = request.jsonrequest
        except Exception:
            _logger.warning("WhatsApp webhook: invalid JSON payload")
            return {'status': 'error', 'message': 'Invalid JSON'}

        # Validate secret
        ICP = request.env['ir.config_parameter'].sudo()
        expected_secret = ICP.get_param('ai_agent.whatsapp_api_secret', '')
        incoming_secret = data.get('secret', '')

        if not expected_secret or incoming_secret != expected_secret:
            _logger.warning("WhatsApp webhook: invalid secret")
            return {'status': 'error', 'message': 'Invalid secret'}

        # Check type
        msg_type = data.get('type', '')
        if msg_type != 'whatsapp':
            _logger.info("WhatsApp webhook: ignoring type=%s", msg_type)
            return {'status': 'ok', 'message': 'Ignored non-whatsapp type'}

        # Extract message data
        msg_data = data.get('data', {})
        phone = msg_data.get('phone', '')
        message = msg_data.get('message', '')
        attachment = msg_data.get('attachment')
        wa_id = msg_data.get('id', 0)

        # Image placeholder: if no text but has attachment
        if not message and attachment:
            message = '[El cliente envió una imagen]'

        if not phone or not message:
            _logger.info("WhatsApp webhook: empty phone or message")
            return {'status': 'ok', 'message': 'No phone or message'}

        # Normalize phone
        wa_service = request.env['ai.agent.whatsapp.service'].sudo()
        normalized_phone = wa_service._normalize_phone(phone)

        # Find active conversation for this phone
        Conversation = request.env['ai.agent.conversation'].sudo()
        conversation = Conversation.search([
            ('phone', '=', normalized_phone),
            ('state', 'in', ('waiting', 'active')),
        ], limit=1, order='last_message_date desc')

        if not conversation:
            _logger.info("WhatsApp webhook: no active conversation for %s", normalized_phone)
            return {'status': 'ok', 'message': 'No active conversation'}

        # Check duplicate
        existing = request.env['ai.agent.message'].sudo().search([
            ('whatsapp_message_id', '=', wa_id),
            ('conversation_id', '=', conversation.id),
        ], limit=1)
        if existing:
            _logger.info("WhatsApp webhook: duplicate message %d", wa_id)
            return {'status': 'ok', 'message': 'Duplicate message'}

        # Process reply
        _logger.info("WhatsApp webhook: processing reply for conversation %d from %s",
                      conversation.id, normalized_phone)
        conversation.action_process_reply(message, wa_message_id=wa_id)

        return {'status': 'ok'}
