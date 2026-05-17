import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

_TG_API = "https://api.telegram.org/bot{token}/{method}"


class AiAgentTelegramService(models.AbstractModel):
    _name = 'ai.agent.telegram.service'
    _description = 'Telegram Bot API Service'

    # ── Internal ────────────────────────────────────────────────────────────

    def _token(self):
        try:
            return self.env['ir.config_parameter'].sudo().get_param(
                'ai_agent.telegram_bot_token', '')
        except Exception:
            # ORM cache can crash mid-transaction in webhook contexts (cursor state).
            # Fall back to a direct SQL read — always safe.
            try:
                self.env.cr.execute(
                    "SELECT value FROM ir_config_parameter WHERE key = %s",
                    ['ai_agent.telegram_bot_token'])
                row = self.env.cr.fetchone()
                return row[0] if row else ''
            except Exception:
                return ''

    def _api(self, method, payload=None, timeout=15):
        token = self._token()
        if not token:
            _logger.warning("Telegram: bot token not configured (ai_agent.telegram_bot_token)")
            return {}
        url = _TG_API.format(token=token, method=method)
        try:
            r = requests.post(url, json=payload or {}, timeout=timeout)
            data = r.json()
            if not data.get('ok'):
                _logger.warning("Telegram API error [%s]: %s", method, data)
            return data
        except Exception as exc:
            _logger.error("Telegram API call failed [%s]: %s", method, exc)
            return {}

    # ── Sending ─────────────────────────────────────────────────────────────

    def send_message(self, chat_id, text, parse_mode='HTML'):
        """Send a text message. Silently strips unsupported HTML tags."""
        # Telegram HTML allows only <b>, <i>, <u>, <s>, <code>, <pre>, <a href>
        # WA replies are plain text so parse_mode=HTML is safe as-is.
        return self._api('sendMessage', {
            'chat_id':    chat_id,
            'text':       text,
            'parse_mode': parse_mode,
        })

    def send_chat_action(self, chat_id, action='typing'):
        """Show 'Glenda is typing…' indicator while Claude processes."""
        return self._api('sendChatAction', {'chat_id': chat_id, 'action': action})

    # ── Files ────────────────────────────────────────────────────────────────

    def get_file(self, file_id):
        """Retrieve Telegram file metadata (file_path)."""
        return self._api('getFile', {'file_id': file_id})

    def get_file_url(self, file_id):
        """Return a direct download URL for a Telegram file_id (valid ~1 h)."""
        token = self._token()
        if not token:
            return None
        data = self.get_file(file_id)
        file_path = (data.get('result') or {}).get('file_path')
        if not file_path:
            return None
        return f"https://api.telegram.org/file/bot{token}/{file_path}"

    # ── Webhook management ──────────────────────────────────────────────────

    def set_webhook(self, url):
        """Register the webhook URL with Telegram. Call once per deploy."""
        result = self._api('setWebhook', {
            'url':                  url,
            'allowed_updates':      ['message'],
            'drop_pending_updates': True,
        })
        _logger.info("Telegram setWebhook → %s: %s", url, result)
        return result

    def delete_webhook(self):
        """Remove the webhook (useful during debugging)."""
        return self._api('deleteWebhook', {'drop_pending_updates': False})

    def get_webhook_info(self):
        """Return current webhook status from Telegram."""
        return self._api('getWebhookInfo')

    def get_me(self):
        """Verify token and return bot info."""
        return self._api('getMe')
