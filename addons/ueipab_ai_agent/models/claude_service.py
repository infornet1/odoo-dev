import json
import logging

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ClaudeService(models.AbstractModel):
    _name = 'ai.agent.claude.service'
    _description = 'Claude AI Service (Anthropic)'

    def _get_config(self):
        """Load Claude API config from system parameters."""
        ICP = self.env['ir.config_parameter'].sudo()
        config = {
            'api_key': ICP.get_param('ai_agent.claude_api_key', ''),
            'base_url': ICP.get_param('ai_agent.claude_base_url', 'https://api.anthropic.com/v1'),
            'model': ICP.get_param('ai_agent.claude_model', 'claude-haiku-4-5-20251001'),
            'anthropic_version': ICP.get_param('ai_agent.claude_anthropic_version', '2023-06-01'),
        }
        if not config['api_key']:
            raise UserError(_("Claude API key no configurado. Verifique los parametros del sistema."))
        return config

    def generate_response(self, system_prompt, messages, model=None):
        """Generate a response using Claude Messages API.

        Args:
            system_prompt: System prompt string
            messages: List of {"role": "user"/"assistant", "content": "..."}
            model: Override model name (optional)

        Returns:
            dict with 'content', 'input_tokens', 'output_tokens'
        """
        config = self._get_config()
        url = config['base_url'].rstrip('/') + '/messages'

        headers = {
            'x-api-key': config['api_key'],
            'anthropic-version': config['anthropic_version'],
            'content-type': 'application/json',
        }

        payload = {
            'model': model or config['model'],
            'max_tokens': 1024,
            'system': system_prompt,
            'messages': messages,
        }

        _logger.info("Claude API call: model=%s, messages=%d", payload['model'], len(messages))

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.HTTPError as e:
            error_body = ''
            try:
                error_body = e.response.json().get('error', {}).get('message', str(e))
            except Exception:
                error_body = str(e)
            _logger.error("Claude API HTTP error: %s", error_body)
            raise UserError(_("Error de Claude API: %s") % error_body)
        except requests.exceptions.RequestException as e:
            _logger.error("Claude API request error: %s", e)
            raise UserError(_("Error de conexion con Claude API: %s") % str(e))

        # Extract response content
        content_blocks = result.get('content', [])
        content = ''
        for block in content_blocks:
            if block.get('type') == 'text':
                content += block.get('text', '')

        usage = result.get('usage', {})

        _logger.info(
            "Claude API response: %d chars, tokens in=%d out=%d",
            len(content),
            usage.get('input_tokens', 0),
            usage.get('output_tokens', 0),
        )

        return {
            'content': content,
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
        }
