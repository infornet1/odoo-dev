import logging
import time

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_CLAUDE_MAX_RETRIES = 2
_CLAUDE_RETRY_DELAYS = [3, 6]   # seconds between retry attempts on 429


class ClaudeService(models.AbstractModel):
    _name = 'ai.agent.claude.service'
    _description = 'Claude AI Service with retry and OpenAI fallback'

    # ── Config ────────────────────────────────────────────────────────────────

    def _get_claude_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('ai_agent.claude_api_key', '')
        if not api_key:
            raise UserError(_("Claude API key no configurado (ai_agent.claude_api_key)."))
        return {
            'api_key':           api_key,
            'base_url':          ICP.get_param('ai_agent.claude_base_url', 'https://api.anthropic.com/v1'),
            'model':             ICP.get_param('ai_agent.claude_model', 'claude-haiku-4-5-20251001'),
            'anthropic_version': ICP.get_param('ai_agent.claude_anthropic_version', '2023-06-01'),
        }

    def _get_openai_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'api_key':  ICP.get_param('ai_agent.openai_api_key', ''),
            'base_url': ICP.get_param('ai_agent.openai_base_url', 'https://api.openai.com/v1'),
            'model':    ICP.get_param('ai_agent.openai_model', 'gpt-4o-mini'),
            'enabled':  ICP.get_param('ai_agent.openai_fallback_enabled', 'False').lower() == 'true',
        }

    # ── Provider calls ────────────────────────────────────────────────────────

    def _call_claude(self, cfg, system_prompt, messages, model=None):
        """Single raw HTTP call to Claude. Returns requests.Response."""
        url = cfg['base_url'].rstrip('/') + '/messages'
        return requests.post(
            url,
            headers={
                'x-api-key':         cfg['api_key'],
                'anthropic-version': cfg['anthropic_version'],
                'content-type':      'application/json',
            },
            json={
                'model':      model or cfg['model'],
                'max_tokens': 1024,
                'system':     system_prompt,
                'messages':   messages,
            },
            timeout=60,
        )

    def _call_openai(self, system_prompt, messages, model=None):
        """Call OpenAI Chat Completions. Returns normalized result dict."""
        cfg = self._get_openai_config()
        if not cfg['api_key']:
            raise UserError(_("OpenAI API key no configurado (ai_agent.openai_api_key)."))

        oai_messages = [{'role': 'system', 'content': system_prompt}] + messages
        _logger.info("OpenAI fallback call: model=%s msgs=%d", model or cfg['model'], len(messages))

        try:
            resp = requests.post(
                cfg['base_url'].rstrip('/') + '/chat/completions',
                headers={
                    'Authorization': f"Bearer {cfg['api_key']}",
                    'Content-Type':  'application/json',
                },
                json={
                    'model':      model or cfg['model'],
                    'max_tokens': 1024,
                    'messages':   oai_messages,
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.HTTPError as e:
            try:
                msg = e.response.json().get('error', {}).get('message', str(e))
            except Exception:
                msg = str(e)
            _logger.error("OpenAI HTTP error: %s", msg)
            raise UserError(_("Error de OpenAI API: %s") % msg)
        except requests.exceptions.RequestException as e:
            _logger.error("OpenAI request error: %s", e)
            raise UserError(_("Error de conexion con OpenAI API: %s") % str(e))

        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        usage   = result.get('usage', {})
        _logger.info(
            "OpenAI response: %d chars tokens in=%d out=%d",
            len(content), usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0),
        )
        return {
            'content':       content,
            'input_tokens':  usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'provider':      'openai',
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def generate_response(self, system_prompt, messages, model=None):
        """Generate a response using Claude with retry and optional OpenAI fallback.

        Retry policy: up to 2 retries on HTTP 429 (3s, 6s delays).
        OpenAI fallback: activated when ai_agent.openai_fallback_enabled=True and:
          - Claude 429 persists after all retries, OR
          - ai_agent.credits_ok=False (credits exhausted)

        Returns dict: {'content', 'input_tokens', 'output_tokens'}
        """
        ICP = self.env['ir.config_parameter'].sudo()
        credits_ok = ICP.get_param('ai_agent.credits_ok', 'True').lower() == 'true'

        if not credits_ok:
            _logger.warning("Credit Guard: credits depleted — trying OpenAI fallback")
            oai = self._get_openai_config()
            if oai['enabled'] and oai['api_key']:
                return self._call_openai(system_prompt, messages, model)
            raise UserError(_(
                "AI Agent desactivado: creditos insuficientes. "
                "Contacte soporte@ueipab.edu.ve."
            ))

        cfg = self._get_claude_config()
        _logger.info("Claude API call: model=%s msgs=%d", model or cfg['model'], len(messages))

        rate_limited = False
        last_error   = None

        for attempt in range(_CLAUDE_MAX_RETRIES + 1):
            try:
                resp = self._call_claude(cfg, system_prompt, messages, model)

                if resp.status_code == 429:
                    rate_limited = True
                    if attempt < _CLAUDE_MAX_RETRIES:
                        delay = _CLAUDE_RETRY_DELAYS[attempt]
                        _logger.warning(
                            "Claude rate limit (429) — retry %d/%d in %ds",
                            attempt + 1, _CLAUDE_MAX_RETRIES, delay,
                        )
                        time.sleep(delay)
                        continue
                    last_error = f"rate limit after {_CLAUDE_MAX_RETRIES + 1} attempts"
                    break

                resp.raise_for_status()
                result = resp.json()

            except requests.exceptions.HTTPError as e:
                try:
                    last_error = e.response.json().get('error', {}).get('message', str(e))
                except Exception:
                    last_error = str(e)
                _logger.error("Claude HTTP error: %s", last_error)
                break

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                _logger.error("Claude request error: %s", e)
                break

            else:
                content = ''.join(
                    b.get('text', '')
                    for b in result.get('content', [])
                    if b.get('type') == 'text'
                )
                usage = result.get('usage', {})
                _logger.info(
                    "Claude response: %d chars tokens in=%d out=%d",
                    len(content),
                    usage.get('input_tokens', 0),
                    usage.get('output_tokens', 0),
                )
                return {
                    'content':       content,
                    'input_tokens':  usage.get('input_tokens', 0),
                    'output_tokens': usage.get('output_tokens', 0),
                }

        # Claude exhausted — try OpenAI fallback if rate-limited and configured
        if rate_limited:
            oai = self._get_openai_config()
            if oai['enabled'] and oai['api_key']:
                _logger.warning("Claude rate limit exhausted — switching to OpenAI fallback")
                return self._call_openai(system_prompt, messages, model)
            raise UserError(_("Claude API rate limit. Intente nuevamente en unos minutos."))

        raise UserError(_("Error de Claude API: %s") % (last_error or 'unknown'))
