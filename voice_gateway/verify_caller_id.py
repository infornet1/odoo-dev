"""Register a Venezuelan (Movistar) number as a Twilio Verified Caller ID — Option A.

Twilio can't sell +58 numbers, but a number you OWN can be verified and then used as
the outbound `from_` caller ID. Flow:

    1. python verify_caller_id.py +584141234567
       → Twilio places a CALL to that number and reads/expects a 6-digit code.
    2. Answer the Movistar phone and key in the code this script prints.
    3. python verify_caller_id.py --list        # confirm it shows as verified
    4. python verify_caller_id.py --set +584141234567   # write it as from_number in config

⚠️ You must genuinely control the number (legal requirement — no spoofing).
⚠️ VE Voice Geographic Permission must be enabled (already done 2026-06-30) so Twilio
   can dial the verification call.
NOTE: Venezuelan carriers may still override the displayed caller ID on internationally
   originated calls — place ONE real test call afterwards to confirm it shows locally.
"""

import json
import sys

from config_loader import twilio_client

CONFIG = "/opt/odoo-dev/config/twilio_api.json"


def list_verified():
    client, _ = twilio_client()
    ids = client.outgoing_caller_ids.list()
    if not ids:
        print("No verified caller IDs yet.")
    for c in ids:
        print(f"  {c.phone_number}  name={c.friendly_name!r}  sid={c.sid}")


def set_from(number):
    d = json.load(open(CONFIG))
    d["api"]["from_number"] = number
    json.dump(d, open(CONFIG, "w"), indent=2)
    print(f"from_number set to {number} in {CONFIG}")


def start_verification(number):
    client, _ = twilio_client()
    req = client.validation_requests.create(
        friendly_name="Movistar VE - Glenda", phone_number=number,
    )
    print("=" * 56)
    print(f"  Twilio is now CALLING {number}")
    print(f"  Answer it and key in this code:   >>> {req.validation_code} <<<")
    print("=" * 56)
    print("After it succeeds, run:  python verify_caller_id.py --list")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: verify_caller_id.py <+58number> | --list | --set <+58number>")
    arg = sys.argv[1]
    if arg == "--list":
        list_verified()
    elif arg == "--set":
        set_from(sys.argv[2])
    else:
        start_verification(arg)


if __name__ == "__main__":
    main()
