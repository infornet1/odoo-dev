import json
import logging
import re
import time

import requests

from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Module-level last-send timestamp for anti-spam throttling.
# Shared across all service instances within the same worker process.
_last_send_time = 0.0


class WhatsAppService(models.AbstractModel):
    """WhatsApp send/receive facade.

    Historically MassivaMóvil-only; now dispatches per provider via
    ir.config_parameter ai_agent.wa_provider ('massiva' default | 'kapso').
    ALL consumers (conversations, skills, wizards, other modules) keep
    calling this model — the provider swap happens here, in one place.
    See documentation/WA_PROVIDER_MIGRATION_KAPSO.md.
    """
    _name = 'ai.agent.whatsapp.service'
    _description = 'WhatsApp Service (MassivaMóvil)'

    def _provider(self):
        """Active WA provider: 'massiva' (default) or 'kapso'."""
        return (self.env['ir.config_parameter'].sudo()
                .get_param('ai_agent.wa_provider', 'massiva') or 'massiva').strip().lower()

    def _get_config(self):
        """Load WhatsApp API config from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        config = {
            'secret': ICP.get_param('ai_agent.whatsapp_api_secret', ''),
            'account_id': ICP.get_param('ai_agent.whatsapp_account_id', ''),
            'account_phone': ICP.get_param('ai_agent.whatsapp_account_phone', ''),
            'base_url': ICP.get_param('ai_agent.whatsapp_base_url', 'https://whatsapp.massivamovil.com/api'),
        }
        if not config['secret']:
            raise UserError(_("WhatsApp API secret no configurado. Verifique los parametros del sistema."))
        return config

    def _normalize_phone(self, phone):
        """Normalize Venezuelan phone formats to E.164 (+58...)."""
        if not phone:
            return ''
        # Remove all non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', phone)
        # Handle various formats
        if cleaned.startswith('+'):
            return cleaned
        if cleaned.startswith('58'):
            return '+' + cleaned
        if cleaned.startswith('0'):
            return '+58' + cleaned[1:]
        if len(cleaned) == 10:
            # Assume Venezuelan: 4XX-XXXXXXX
            return '+58' + cleaned
        return '+' + cleaned

    def _get_send_interval(self):
        """Get anti-spam send interval in seconds from config.

        MassivaMóvil recommends 120-140 second intervals between sends
        to avoid WhatsApp flagging the phone number as SPAM.
        Returns the minimum interval (default 120s).
        """
        ICP = self.env['ir.config_parameter'].sudo()
        return int(ICP.get_param('ai_agent.whatsapp_send_interval', '120'))

    def _throttle_send(self):
        """Wait if needed to respect the anti-spam send interval.

        Uses module-level timestamp so throttling works across all
        send_message() calls within the same Odoo worker process.
        """
        global _last_send_time
        interval = self._get_send_interval()
        if interval <= 0:
            return

        now = time.time()
        elapsed = now - _last_send_time
        if elapsed < interval:
            wait = interval - elapsed
            _logger.info(
                "WhatsApp throttle: waiting %.0fs (interval=%ds, elapsed=%.0fs)",
                wait, interval, elapsed)
            time.sleep(wait)

    def send_message(self, phone, message):
        """Send a WhatsApp message via MassivaMóvil API.

        Respects anti-spam throttling interval between sends.
        Returns dict with message_id on success.
        """
        if self._provider() == 'kapso':
            return self.env['ai.agent.kapso.service'].send_message(phone, message)

        # Credit guard kill switch — WA leg only (Telegram/OdooBot unaffected)
        wa_credits_ok = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.wa_credits_ok', 'True').lower() == 'true'
        if not wa_credits_ok:
            _logger.warning("Credit Guard: WhatsApp send blocked — WA credits depleted")
            raise UserError(_("Envios WhatsApp desactivados: creditos WhatsApp insuficientes. "
                              "Contacte soporte@ueipab.edu.ve."))

        global _last_send_time
        config = self._get_config()
        url = config['base_url'].rstrip('/') + '/send/whatsapp'
        normalized_phone = self._normalize_phone(phone)

        data = {
            'secret': config['secret'],
            'account': config['account_id'],
            'recipient': normalized_phone,
            'type': 'text',
            'message': message,
        }

        # Anti-spam throttle: wait if last send was too recent
        self._throttle_send()

        _logger.info("WhatsApp send to %s (%d chars)", normalized_phone, len(message))

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp API error: %s", e)
            raise UserError(_("Error al enviar mensaje WhatsApp: %s") % str(e))

        if result.get('status') != 200:
            error_msg = result.get('message', 'Unknown error')
            _logger.error("WhatsApp API returned error: %s", error_msg)
            raise UserError(_("Error de WhatsApp API: %s") % error_msg)

        # Record send time for throttling
        _last_send_time = time.time()

        _logger.info("WhatsApp message sent successfully to %s", normalized_phone)
        return {'message_id': result.get('data', {}).get('id', 0)}

    def send_media(self, phone, url, caption=''):
        """Send a WhatsApp image/media message via MassivaMóvil API.

        Args:
            phone: Recipient phone number (any Venezuelan format)
            url: Publicly accessible URL of the image/media file
            caption: Optional text caption displayed below the image
        Returns dict with message_id on success.
        """
        if self._provider() == 'kapso':
            return self.env['ai.agent.kapso.service'].send_media(phone, url, caption=caption)

        wa_credits_ok = self.env['ir.config_parameter'].sudo().get_param(
            'ai_agent.wa_credits_ok', 'True').lower() == 'true'
        if not wa_credits_ok:
            _logger.warning("Credit Guard: WhatsApp send blocked — WA credits depleted")
            raise UserError(_("Envios WhatsApp desactivados: creditos WhatsApp insuficientes. "
                              "Contacte soporte@ueipab.edu.ve."))

        global _last_send_time
        config = self._get_config()
        api_url = config['base_url'].rstrip('/') + '/send/whatsapp'
        normalized_phone = self._normalize_phone(phone)

        data = {
            'secret': config['secret'],
            'account': config['account_id'],
            'recipient': normalized_phone,
            'type': 'photo',
            'url': url,
            'message': caption or 'Informacion adicional',
        }

        self._throttle_send()

        _logger.info("WhatsApp media send to %s: %s", normalized_phone, url)

        try:
            response = requests.post(api_url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp media API error: %s", e)
            raise UserError(_("Error al enviar imagen WhatsApp: %s") % str(e))

        if result.get('status') != 200:
            error_msg = result.get('message', 'Unknown error')
            _logger.error("WhatsApp media API returned error: %s", error_msg)
            raise UserError(_("Error de WhatsApp API (media): %s") % error_msg)

        _last_send_time = time.time()
        _logger.info("WhatsApp media sent successfully to %s", normalized_phone)
        data = result.get('data') or {}
        msg_id = data.get('messageId') or data.get('id') or 0
        return {'message_id': int(msg_id) if str(msg_id).isdigit() else 0}

    def validate_phone(self, phone):
        """Validate a WhatsApp phone number via MassivaMóvil API.

        Returns True if valid, False otherwise.
        """
        if self._provider() == 'kapso':
            return self.env['ai.agent.kapso.service'].validate_phone(phone)

        config = self._get_config()
        url = config['base_url'].rstrip('/') + '/validate/whatsapp'
        normalized_phone = self._normalize_phone(phone)

        params = {
            'secret': config['secret'],
            'unique': config['account_id'],
            'phone': normalized_phone,
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp validate error: %s", e)
            return False

        return result.get('status') == 200

    def fetch_received(self, limit=50, page=1, account_id=None):
        """Fetch received WhatsApp messages via polling API.

        Args:
            account_id: MassivaMóvil unique_id for a specific WA account.
                        When provided the API filters to that account only,
                        preventing messages from other linked accounts
                        (backup / tertiary) from leaking in.

        Returns list of message dicts.
        """
        if self._provider() == 'kapso':
            # Kapso inbound is webhook-push (/ai-agent/kapso/webhook);
            # nothing to poll — the poll cron becomes a harmless no-op.
            return self.env['ai.agent.kapso.service'].fetch_received(
                limit=limit, page=page, account_id=account_id)

        config = self._get_config()
        url = config['base_url'].rstrip('/') + '/get/wa.received'

        params = {
            'secret': config['secret'],
            'limit': limit,
            'page': page,
        }
        if account_id:
            params['account'] = account_id

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp fetch received error: %s", e)
            raise UserError(_("Error al consultar mensajes WhatsApp: %s") % str(e))

        if result.get('status') != 200:
            return []

        data = result.get('data', [])
        # API returns data as a list of messages directly
        if isinstance(data, list):
            return data
        # Fallback for dict format
        return data.get('messages', [])
