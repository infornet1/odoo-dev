import logging
import time

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Module-level last-send timestamp for throttling (per worker process),
# same pattern as whatsapp_service.py.
_last_send_time = 0.0


class KapsoService(models.AbstractModel):
    """WhatsApp provider: Kapso (Meta Cloud API proxy).

    Drop-in send-side replacement for ai.agent.whatsapp.service
    (MassivaMóvil). Consumers must NOT call this model directly — they keep
    calling ai.agent.whatsapp.service, which dispatches here when
    ir.config_parameter ai_agent.wa_provider = 'kapso'.

    Sends go to the Kapso Meta proxy (byte-compatible Meta Graph Cloud API):
        POST {proxy_base_url}/{graph_version}/{phone_number_id}/messages
    with X-API-Key auth and Meta-style snake_case JSON bodies.

    Inbound is PUSH (webhook /ai-agent/kapso/webhook), not polling —
    fetch_received() has no Kapso equivalent.

    See documentation/WA_PROVIDER_MIGRATION_KAPSO.md.
    """
    _name = 'ai.agent.kapso.service'
    _description = 'WhatsApp Service (Kapso)'

    # ── Config ────────────────────────────────────────────────────────────

    def _get_config(self):
        """Load Kapso API config from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        config = {
            'api_key': ICP.get_param('ai_agent.kapso_api_key', ''),
            'phone_number_id': ICP.get_param('ai_agent.kapso_phone_number_id', ''),
            'proxy_base_url': ICP.get_param(
                'ai_agent.kapso_proxy_base_url', 'https://api.kapso.ai/meta/whatsapp'),
            'graph_version': ICP.get_param('ai_agent.kapso_graph_version', 'v23.0'),
            'platform_base_url': ICP.get_param(
                'ai_agent.kapso_platform_base_url', 'https://api.kapso.ai/platform/v1'),
        }
        if not config['api_key'] or not config['phone_number_id']:
            raise UserError(_(
                "Kapso API no configurado. Verifique los parametros "
                "ai_agent.kapso_api_key y ai_agent.kapso_phone_number_id."))
        return config

    def _normalize_phone(self, phone):
        """Same normalization as the MassivaMóvil service (single source)."""
        return self.env['ai.agent.whatsapp.service']._normalize_phone(phone)

    def _get_send_interval(self):
        """Anti-spam interval between sends, in seconds.

        Kapso rides the official Meta Cloud API, so the Massiva-style 120s
        pacing is unnecessary; default is a light 3s spacing. Tune via
        ai_agent.kapso_send_interval.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        return int(ICP.get_param('ai_agent.kapso_send_interval', '3'))

    def _throttle_send(self):
        global _last_send_time
        interval = self._get_send_interval()
        if interval <= 0:
            return
        elapsed = time.time() - _last_send_time
        if elapsed < interval:
            wait = interval - elapsed
            _logger.info("Kapso throttle: waiting %.1fs (interval=%ds)", wait, interval)
            time.sleep(wait)

    def _check_kill_switch(self):
        """Same WA kill switch as MassivaMóvil (ai_agent.wa_credits_ok)."""
        wa_credits_ok = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.wa_credits_ok', 'True').lower() == 'true'
        if not wa_credits_ok:
            _logger.warning("Credit Guard: Kapso send blocked — WA sends disabled")
            raise UserError(_("Envios WhatsApp desactivados: creditos WhatsApp "
                              "insuficientes. Contacte soporte@ueipab.edu.ve."))

    # ── HTTP ──────────────────────────────────────────────────────────────

    def _messages_url(self, config):
        return "%s/%s/%s/messages" % (
            config['proxy_base_url'].rstrip('/'),
            config['graph_version'],
            config['phone_number_id'],
        )

    def _post_message(self, payload, config):
        """POST a message payload to the Kapso Meta proxy.

        The Kapso client has no built-in retry, so we retry ONCE on network
        error, HTTP 429 (honoring Retry-After, capped 30s) and 5xx.
        Returns the parsed JSON response; raises UserError on failure.
        """
        url = self._messages_url(config)
        headers = {'X-API-Key': config['api_key']}
        last_error = ''
        for attempt in (1, 2):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                _logger.warning("Kapso API network error (attempt %d): %s", attempt, e)
                if attempt == 1:
                    time.sleep(2)
                    continue
                raise UserError(_("Error al enviar mensaje WhatsApp (Kapso): %s") % last_error)

            if response.status_code == 429 or response.status_code >= 500:
                retry_after = 2.0
                try:
                    retry_after = min(float(response.headers.get('Retry-After', 2)), 30.0)
                except (TypeError, ValueError):
                    pass
                last_error = "HTTP %s: %s" % (response.status_code, response.text[:200])
                _logger.warning("Kapso API transient error (attempt %d): %s", attempt, last_error)
                if attempt == 1:
                    time.sleep(retry_after)
                    continue
                raise UserError(_("Error de Kapso API: %s") % last_error)

            if response.status_code >= 400:
                # Meta Graph error shape: {"error": {"message", "code", ...}}.
                # Some errors return {"error": "string"} or a non-dict body —
                # fall back to the raw text rather than crashing on .get().
                try:
                    err = response.json().get('error', {})
                    detail = err.get('message') or response.text[:200]
                except (ValueError, AttributeError):
                    detail = response.text[:200]
                _logger.error("Kapso API error %s: %s", response.status_code, detail)
                raise UserError(_("Error de Kapso API: %s") % detail)

            try:
                return response.json()
            except ValueError:
                raise UserError(_("Respuesta invalida de Kapso API"))
        raise UserError(_("Error de Kapso API: %s") % last_error)  # unreachable guard

    # ── Public send API (mirrors ai.agent.whatsapp.service) ─────────────

    def send_message(self, phone, message):
        """Send a WhatsApp text message via Kapso.

        Returns {'message_id': 0, 'wamid': 'wamid.XXX'} — message_id keeps
        the MassivaMóvil integer contract for existing callers (their IDs
        are ints; Kapso wamids are strings, carried separately).
        """
        global _last_send_time
        self._check_kill_switch()
        config = self._get_config()
        normalized_phone = self._normalize_phone(phone)

        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': normalized_phone,
            'type': 'text',
            'text': {'body': message},
        }

        self._throttle_send()
        _logger.info("Kapso WA send to %s (%d chars)", normalized_phone, len(message or ''))
        result = self._post_message(payload, config)

        wamid = ''
        messages = result.get('messages') or []
        if messages and isinstance(messages, list):
            wamid = (messages[0] or {}).get('id') or ''
        # The message was ACCEPTED (2xx) — do NOT raise on a missing wamid, or
        # a retrying caller would double-send an already-delivered message.
        # Stamp the throttle and return like send_media does.
        if not wamid:
            _logger.warning("Kapso send: 2xx but no wamid in response: %s", result)

        _last_send_time = time.time()
        _logger.info("Kapso WA message sent to %s (%s)", normalized_phone, wamid or 'no-wamid')
        return {'message_id': 0, 'wamid': wamid}

    def send_media(self, phone, url, caption=''):
        """Send a WhatsApp image (by public link) via Kapso.

        Mirrors MassivaMóvil send_media (used for flyers — images only).
        Returns {'message_id': 0, 'wamid': 'wamid.XXX'}.
        """
        global _last_send_time
        self._check_kill_switch()
        config = self._get_config()
        normalized_phone = self._normalize_phone(phone)

        image = {'link': url}
        if caption:
            image['caption'] = caption[:1024]
        payload = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': normalized_phone,
            'type': 'image',
            'image': image,
        }

        self._throttle_send()
        _logger.info("Kapso WA media send to %s: %s", normalized_phone, url)
        result = self._post_message(payload, config)

        wamid = ''
        messages = result.get('messages') or []
        if messages and isinstance(messages, list):
            wamid = (messages[0] or {}).get('id') or ''
        _last_send_time = time.time()
        _logger.info("Kapso WA media sent to %s (%s)", normalized_phone, wamid or 'no-wamid')
        return {'message_id': 0, 'wamid': wamid}

    def validate_phone(self, phone):
        """Kapso/Meta has no cheap number-validation endpoint.

        Returns True when the number normalizes to a plausible E.164 mobile —
        callers use this as a soft pre-check only.
        """
        normalized = self._normalize_phone(phone)
        return bool(normalized) and normalized.startswith('+') and len(normalized) >= 12

    def fetch_received(self, limit=50, page=1, account_id=None):
        """No polling under Kapso — inbound arrives via the webhook
        (/ai-agent/kapso/webhook). Returns [] so _cron_poll_messages is a
        harmless no-op if it runs while provider='kapso'.
        """
        _logger.debug("Kapso fetch_received(): inbound is webhook-push; returning []")
        return []
