import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VoiceWebhook(http.Controller):
    """Receives call status + transcript updates from the voice gateway.

    type='json' → Odoo unwraps the JSON-RPC ``params`` into kwargs, so the
    gateway's payload fields arrive directly as ``kw``.
    """

    @http.route('/ai-agent/voice/callback', type='json', auth='public',
                methods=['POST'], csrf=False)
    def voice_callback(self, **kw):
        # Shared-secret check (enforced only if a token is configured).
        icp = request.env['ir.config_parameter'].sudo()
        expected = icp.get_param('voice_call.callback_token')
        if expected and kw.get('callback_token') != expected:
            _logger.warning("voice callback: bad token")
            return {'ok': False, 'error': 'unauthorized'}

        call_id = request.env['ai.agent.voice.call'].sudo().ingest_callback(kw)
        return {'ok': bool(call_id), 'call_id': call_id}

    @http.route('/ai-agent/voice/tool', type='json', auth='public',
                methods=['POST'], csrf=False)
    def voice_tool(self, **kw):
        """Realtime function-tool execution: {name, arguments, callback_token}."""
        icp = request.env['ir.config_parameter'].sudo()
        expected = icp.get_param('voice_call.callback_token')
        if expected and kw.get('callback_token') != expected:
            return {'error': 'unauthorized'}
        return request.env['ai.agent.voice.call'].sudo().voice_tool(
            kw.get('name'), kw.get('arguments') or {})
