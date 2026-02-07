import json
import logging
import re

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppService(models.AbstractModel):
    _name = 'ai.agent.whatsapp.service'
    _description = 'WhatsApp Service (MassivaMóvil)'

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

    def send_message(self, phone, message):
        """Send a WhatsApp message via MassivaMóvil API.

        Returns dict with message_id on success.
        """
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

        _logger.info("WhatsApp message sent successfully to %s", normalized_phone)
        return {'message_id': result.get('data', {}).get('id', 0)}

    def validate_phone(self, phone):
        """Validate a WhatsApp phone number via MassivaMóvil API.

        Returns True if valid, False otherwise.
        """
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

    def fetch_received(self, limit=50, page=1):
        """Fetch received WhatsApp messages via polling API.

        Returns list of message dicts.
        """
        config = self._get_config()
        url = config['base_url'].rstrip('/') + '/get/wa.received'

        params = {
            'secret': config['secret'],
            'limit': limit,
            'page': page,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp fetch received error: %s", e)
            raise UserError(_("Error al consultar mensajes WhatsApp: %s") % str(e))

        if result.get('status') != 200:
            return []

        return result.get('data', {}).get('messages', [])
