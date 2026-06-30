"""Config loader for the voice gateway.

Reads JSON config from ../config (same convention as anthropic_api.json etc.),
with environment-variable overrides so the container can be configured without
baking secrets into the image.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_CONFIG_DIR = os.path.normpath(os.path.join(_HERE, "..", "config"))


def _load(name: str) -> dict:
    path = os.path.join(_CONFIG_DIR, name)
    try:
        with open(path) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


def get_openai_key() -> str:
    """OpenAI API key — env wins, else reuse config/openai_api.json (Glenda's key)."""
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    cfg = _load("openai_api.json")
    return (cfg.get("api") or {}).get("api_key", "")


def get_twilio() -> dict:
    """Twilio credentials from config/twilio_api.json (or env).

    Supports two auth styles:
      * API Key (recommended): api_key_sid (SK…) + api_key_secret + account_sid (AC…)
      * Legacy: account_sid + auth_token
    """
    cfg = _load("twilio_api.json").get("api", {})
    return {
        "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", cfg.get("account_sid", "")),
        "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", cfg.get("auth_token", "")),
        "api_key_sid": os.environ.get("TWILIO_API_KEY_SID", cfg.get("api_key_sid", "")),
        "api_key_secret": os.environ.get("TWILIO_API_KEY_SECRET", cfg.get("api_key_secret", "")),
        "from_number": os.environ.get("TWILIO_FROM_NUMBER", cfg.get("from_number", "")),
    }


def twilio_client():
    """Build a Twilio REST client from whichever auth style is configured.

    API Key:  Client(api_key_sid, api_key_secret, account_sid)
    Legacy:   Client(account_sid, auth_token)
    """
    from twilio.rest import Client  # local import so config_loader stays import-light
    tw = get_twilio()
    if tw["api_key_sid"] and tw["api_key_secret"]:
        return Client(tw["api_key_sid"], tw["api_key_secret"], tw["account_sid"]), tw
    return Client(tw["account_sid"], tw["auth_token"]), tw


def get_settings() -> dict:
    """Gateway runtime settings from config/twilio_api.json -> "gateway" block (or env)."""
    return _load("twilio_api.json").get("gateway", {})


def get_public_base_url() -> str:
    """Public base URL Twilio should reach (https://host).

    Priority: live cloudflared quick-tunnel URL (.tunnel_url file) > configured
    gateway.public_host. Returns '' if neither is set.
    """
    tunnel_file = os.path.join(_HERE, ".tunnel_url")
    try:
        with open(tunnel_file) as fh:
            url = fh.read().strip()
            if url:
                return url.rstrip("/")
    except FileNotFoundError:
        pass
    host = get_settings().get("public_host", "")
    return f"https://{host}".rstrip("/") if host else ""
