"""Place ONE outbound test call to Gustavo and bridge it to Glenda (POC).

Usage:
    python place_call.py                       # calls the configured test number
    python place_call.py +584142337463         # explicit destination
    python place_call.py +584142337463 "Llamada de prueba del sistema de voz"

Requires config/twilio_api.json (account_sid, auth_token, from_number) and a
reachable PUBLIC_HOST (the gateway must already be running and publicly reachable).

⚠️ Test-routing rule: voice tests go to Gustavo's number only — never a parent.
"""

import sys

from config_loader import get_public_base_url, get_settings, twilio_client

# Default test target = Gustavo (per project test-routing rule). Override via argv.
DEFAULT_TEST_NUMBER = "+584142337463"


def main():
    client, tw = twilio_client()
    settings = get_settings()
    base_url = get_public_base_url()  # live cloudflared tunnel URL > configured public_host

    has_auth = (tw["api_key_sid"] and tw["api_key_secret"] and tw["account_sid"]) or \
               (tw["account_sid"] and tw["auth_token"])
    if not (has_auth and tw["from_number"]):
        sys.exit("Missing Twilio creds — fill config/twilio_api.json (api_key_sid/secret + account_sid, and from_number).")
    if not base_url:
        sys.exit("No public URL — start the tunnel (glenda-voice-tunnel.service writes .tunnel_url) "
                 "or set gateway.public_host in config/twilio_api.json.")

    to_number = sys.argv[1] if len(sys.argv) > 1 else settings.get("test_number", DEFAULT_TEST_NUMBER)
    reason = sys.argv[2] if len(sys.argv) > 2 else ""

    twiml_url = f"{base_url}/twiml"

    call = client.calls.create(
        to=to_number,
        from_=tw["from_number"],
        url=twiml_url,
        # Optional: record=True,  # enable only with consent + retention policy decided
    )
    print(f"Placed call SID={call.sid}  to={to_number}  from={tw['from_number']}")
    print(f"TwiML endpoint: {twiml_url}")
    if reason:
        print(f"NOTE: per-call reason via argv is POC-only; wire it through TwiML <Parameter> "
              f"or the gateway's CALL_REASONS map for real use. Reason={reason!r}")


if __name__ == "__main__":
    main()
