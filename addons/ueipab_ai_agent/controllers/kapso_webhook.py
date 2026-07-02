import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class KapsoWebhookController(http.Controller):
    """Inbound WhatsApp webhook for the Kapso provider.

    Kapso POSTs plain JSON (NOT JSON-RPC) with an HMAC-SHA256 signature of
    the raw body in the X-Webhook-Signature header (kind='kapso' webhooks),
    so this route is type='http' and reads/verifies the raw payload itself —
    unlike the Telegram/voice controllers (type='json').

    v2 payload (whatsapp.message.received):
        {"message": {"id": "wamid.X", "from": "58414...", "type": "text",
                     "text": {"body": "..."},
                     "kapso": {"direction": "inbound", "media_url": ...}},
         "conversation": {"phone_number": "...", "kapso": {"contact_name": ...}},
         "is_new_conversation": true, "phone_number_id": "..."}

    A Meta-shaped envelope ({object, entry:[{changes:[{value:{messages}}]}]})
    is also accepted defensively (kind='meta' webhooks / future changes).

    Security: HMAC verification is enforced only when
    ir.config_parameter ai_agent.kapso_webhook_secret is set (voice_webhook
    pattern). Always returns 200 on processing errors — dedup on wamid makes
    Kapso redeliveries safe, and a retry storm helps nobody.

    See documentation/WA_PROVIDER_MIGRATION_KAPSO.md.
    """

    @http.route('/ai-agent/kapso/webhook', type='http', auth='public',
                methods=['POST'], csrf=False)
    def kapso_webhook(self, **kw):
        raw = request.httprequest.get_data() or b''

        icp = request.env['ir.config_parameter'].sudo()
        secret = (icp.get_param('ai_agent.kapso_webhook_secret') or '').strip()
        if not secret:
            # Fail CLOSED: if Kapso inbound is active but no secret is
            # configured, reject rather than accept forged, unauthenticated
            # messages (auth='public' route). Only the dormant state — provider
            # still 'massiva' and inbound not explicitly enabled — is allowed
            # through unsigned (and _handle_kapso_inbound then no-ops anyway).
            provider = (icp.get_param('ai_agent.wa_provider', 'massiva')
                        or 'massiva').strip().lower()
            inbound_enabled = (icp.get_param(
                'ai_agent.kapso_inbound_enabled', 'False') or '').strip().lower() == 'true'
            if provider == 'kapso' or inbound_enabled:
                _logger.error("Kapso webhook: inbound ACTIVE but "
                              "ai_agent.kapso_webhook_secret unset — rejecting")
                return request.make_json_response(
                    {'error': 'webhook secret not configured'}, status=401)
        elif not self._verify_signature(raw, secret):
            _logger.warning("Kapso webhook: invalid signature from %s",
                            request.httprequest.remote_addr)
            return request.make_json_response(
                {'error': 'invalid signature'}, status=401)

        try:
            payload = json.loads(raw.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            _logger.warning("Kapso webhook: unparseable body (%d bytes)", len(raw))
            return request.make_json_response({'error': 'bad json'}, status=400)

        try:
            results = self._process_payload(payload)
        except Exception:
            _logger.exception("Kapso webhook: unexpected processing error")
            results = ['error']

        # Return 5xx on genuine processing failure so Kapso REDELIVERS the
        # event — wamid dedup makes redelivery idempotent, so a transient
        # Claude 429 / DB serialization error is retried instead of lost.
        # 'skipped'/'deferred'/'dry_run'/'duplicate' are deliberate no-ops → 200.
        if any(r == 'error' for r in results):
            return request.make_json_response(
                {'ok': False, 'results': results}, status=502)
        return request.make_json_response({'ok': True, 'results': results})

    @staticmethod
    def _verify_signature(raw, secret):
        """HMAC-SHA256 of the raw body vs X-Webhook-Signature (kapso kind).

        Also accepts X-Hub-Signature-256 ('sha256=<hex>', meta kind) so a
        kind='meta' webhook pointed here still verifies.
        """
        headers = request.httprequest.headers
        provided = (headers.get('X-Webhook-Signature')
                    or headers.get('X-Hub-Signature-256') or '').strip()
        if provided.lower().startswith('sha256='):
            provided = provided[7:]
        if not provided:
            return False
        expected = hmac.new(secret.encode('utf-8'), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided.lower(), expected.lower())

    def _process_payload(self, payload):
        Conversation = request.env['ai.agent.conversation'].sudo()
        results = []
        for message, conv_info in self._iter_messages(payload):
            kapso = message.get('kapso') or {}
            direction = kapso.get('direction') or 'inbound'
            if direction != 'inbound':
                results.append('skipped_outbound')
                continue

            wamid = message.get('id') or ''
            phone = message.get('from') or (conv_info or {}).get('phone_number') or ''
            text = ((message.get('text') or {}).get('body')
                    or kapso.get('content') or '')
            media_url = kapso.get('media_url') or None
            media_type = message.get('type') or None
            contact_name = ((conv_info or {}).get('kapso') or {}).get('contact_name')

            if not phone:
                results.append('skipped_no_phone')
                continue

            result = Conversation._handle_kapso_inbound(
                phone=phone, text=text, wamid=wamid,
                media_url=media_url, contact_name=contact_name,
                media_type=media_type)
            results.append(result)
        if not results:
            # Status/conversation events (message.sent/delivered/read/failed,
            # conversation.*) carry no inbound message — acknowledge quietly.
            results.append('no_inbound_messages')
        return results

    @staticmethod
    def _iter_messages(payload):
        """Yield (message, conversation) pairs from any supported envelope."""
        if not isinstance(payload, dict):
            return
        # Kapso v2 flat envelope: one message per delivery
        if isinstance(payload.get('message'), dict):
            yield payload['message'], payload.get('conversation') or {}
            return
        # Defensive: buffered deliveries as a message list
        if isinstance(payload.get('messages'), list):
            conv_info = payload.get('conversation') or {}
            for message in payload['messages']:
                if isinstance(message, dict):
                    yield message, conv_info
            return
        # Meta-shaped envelope (kind='meta' passthrough)
        for entry in payload.get('entry') or []:
            if not isinstance(entry, dict):
                continue
            for change in entry.get('changes') or []:
                if not isinstance(change, dict):
                    continue
                value = change.get('value') or {}
                for message in value.get('messages') or []:
                    if isinstance(message, dict):
                        yield message, {}
