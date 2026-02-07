from . import models
from . import skills
from . import controllers
from . import wizard


def _load_api_configs(env):
    """Post-init hook: load API configs from JSON files into system parameters."""
    import json
    import os
    import logging

    _logger = logging.getLogger(__name__)
    ICP = env['ir.config_parameter'].sudo()

    # Load WhatsApp config
    wa_config_path = '/opt/odoo-dev/config/whatsapp_massiva.json'
    if os.path.isfile(wa_config_path):
        try:
            with open(wa_config_path, 'r') as f:
                wa_cfg = json.load(f)
            ICP.set_param('ai_agent.whatsapp_api_secret', wa_cfg['api']['secret'])
            accounts = wa_cfg.get('whatsapp_accounts', [])
            primary = next((a for a in accounts if a.get('primary')), accounts[0] if accounts else {})
            ICP.set_param('ai_agent.whatsapp_account_id', primary.get('unique_id', ''))
            ICP.set_param('ai_agent.whatsapp_account_phone', primary.get('phone', ''))
            ICP.set_param('ai_agent.whatsapp_base_url', wa_cfg['api'].get('base_url', ''))
            _logger.info("AI Agent: WhatsApp config loaded from %s", wa_config_path)
        except Exception as e:
            _logger.warning("AI Agent: Could not load WhatsApp config: %s", e)
    else:
        _logger.info("AI Agent: WhatsApp config not found at %s, skipping", wa_config_path)

    # Load Claude config
    claude_config_path = '/opt/odoo-dev/config/anthropic_api.json'
    if os.path.isfile(claude_config_path):
        try:
            with open(claude_config_path, 'r') as f:
                cl_cfg = json.load(f)
            ICP.set_param('ai_agent.claude_api_key', cl_cfg['api']['api_key'])
            ICP.set_param('ai_agent.claude_base_url', cl_cfg['api'].get('base_url', 'https://api.anthropic.com/v1'))
            ICP.set_param('ai_agent.claude_model', cl_cfg.get('model', {}).get('default', 'claude-haiku-4-5-20251001'))
            ICP.set_param('ai_agent.claude_anthropic_version', cl_cfg['api'].get('anthropic_version', '2023-06-01'))
            _logger.info("AI Agent: Claude config loaded from %s", claude_config_path)
        except Exception as e:
            _logger.warning("AI Agent: Could not load Claude config: %s", e)
    else:
        _logger.info("AI Agent: Claude config not found at %s, skipping", claude_config_path)

    # Set dry_run default
    if not ICP.get_param('ai_agent.dry_run'):
        ICP.set_param('ai_agent.dry_run', 'True')
