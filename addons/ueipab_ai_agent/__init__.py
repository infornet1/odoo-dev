from . import models
from . import skills
from . import controllers
from . import wizard


def _load_api_configs(env):
    """Post-init hook: load API configs from JSON files into system parameters.

    Searches for config files in multiple locations:
    1. AI_AGENT_CONFIG_DIR environment variable (if set)
    2. /opt/odoo-dev/config/ (dev server)
    3. /home/vision/ueipab17/config/ (production server)
    """
    import json
    import os
    import logging

    _logger = logging.getLogger(__name__)
    ICP = env['ir.config_parameter'].sudo()

    # Config directory search order
    config_dirs = []
    env_dir = os.environ.get('AI_AGENT_CONFIG_DIR')
    if env_dir:
        config_dirs.append(env_dir)
    config_dirs.extend([
        '/opt/odoo-dev/config',
        '/home/vision/ueipab17/config',
    ])

    def _find_config(filename):
        """Find a config file in the first available directory."""
        for d in config_dirs:
            path = os.path.join(d, filename)
            if os.path.isfile(path):
                _logger.info("AI Agent: Found %s at %s", filename, path)
                return path
        _logger.info("AI Agent: %s not found in any config directory: %s",
                     filename, ', '.join(config_dirs))
        return None

    # Load WhatsApp config
    wa_config_path = _find_config('whatsapp_massiva.json')
    if wa_config_path:
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

    # Load Claude config
    claude_config_path = _find_config('anthropic_api.json')
    if claude_config_path:
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

    # Set dry_run default
    if not ICP.get_param('ai_agent.dry_run'):
        ICP.set_param('ai_agent.dry_run', 'True')

    # Set active_db default (environment safeguard)
    if not ICP.get_param('ai_agent.active_db'):
        db_name = env.cr.dbname
        ICP.set_param('ai_agent.active_db', db_name)
        _logger.info("AI Agent: active_db set to '%s' (current database)", db_name)
