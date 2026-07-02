# WA Provider Migration — MassivaMóvil → Kapso

**Status:** **Phase 1 deployed (dual-provider, dormant)** — code live in both envs, provider param still `massiva`
**Created:** 2026-07-01
**Module:** `ueipab_ai_agent` v17.0.1.61.0
**Config file:** `/opt/odoo-dev/config/kapso_api.json` (gitignored; prod copy at `/home/vision/ueipab17/config/`)
**Provider dashboard:** https://app.kapso.ai

---

## Why

- The Massiva **dedicated primary +58 414-8321989 has been broken since 2026-05-22** (Massiva support ticket never resolved). All Glenda WA + invoice blasts have been flowing through the **backup +58 424-8944898** since then.
- **CEO decision 2026-07-01:** migrate the primary number off MassivaMóvil to **Kapso** (kapso.ai).
- Kapso = **managed Meta Cloud API** — the official WhatsApp Business API, resold with a byte-compatible Meta Graph proxy:

| Criterion | MassivaMóvil | Kapso |
|-----------|-------------|-------|
| API type | Unofficial (WhatsApp Web bridge) | **Official Meta Cloud API** (managed) |
| Inbound | 5-min poll cron (`_cron_poll_messages`) | **Real-time webhook push**, per-number, HMAC-signed |
| Anti-spam pacing | 120s between sends (ban-avoidance) | **Not needed** (official API) — 3s courtesy default |
| Payloads | form-encoded, `status==200` in body | Meta Cloud API JSON, real HTTP statuses |
| Message IDs | Integer | String `wamid.*` |
| Account health | Fragile (primary broken 40+ days) | Meta-grade |

---

## Architecture — facade dispatch

**Design rule: `ai.agent.whatsapp.service` stays the single entry point for ALL consumers.** One `ir.config_parameter` — `ai_agent.wa_provider` (`'massiva'` default | `'kapso'`) — switches the provider *inside* the facade. **Zero call-site changes** anywhere (module callers, cross-module callers in `ueipab_payroll_enhancements` / `ueipab_enrollment_journey` / `ueipab_attendance_report`, wizards, skills).

```
 Consumers (unchanged)                         Facade                       Providers
 ─────────────────────                 ────────────────────────      ─────────────────────────
 _send_to_user / _notify_ceo    ──►                                  ┌► massiva (in-file legacy
 send_flyer / wizards / dashboards     ai.agent.whatsapp.service ────┤   code, form-encoded POST)
 hr_data_collection / cross-module     _provider() reads             │
 enrollment_s0_blast (XML-RPC)         ai_agent.wa_provider          └► ai.agent.kapso.service
                                       and dispatches at the TOP         POST Kapso Meta proxy
                                       of send_message / send_media           │
                                       / validate_phone /                     ▼
                                       fetch_received                 Meta Cloud API → parent
```

- `whatsapp_service.py` `_provider()` (L30-33): `get_param('ai_agent.wa_provider', 'massiva')`, stripped/lowered.
- Each of the 4 public methods checks `if self._provider() == 'kapso':` as its **first statement** and delegates to `ai.agent.kapso.service` with the identical signature. Fallthrough = the untouched Massiva code.
- `_normalize_phone()` remains the single source (Kapso service delegates back to it), so external callers of the helper are unaffected.

### Outbound (Kapso)

`models/kapso_service.py` — `ai.agent.kapso.service` (AbstractModel, stateless, config from `ir.config_parameter` only):

```
POST https://api.kapso.ai/meta/whatsapp/v23.0/{phone_number_id}/messages
Headers: X-API-Key: <kapso project api key>, Content-Type: application/json
```

Text payload (exact wire):
```json
{"messaging_product": "whatsapp", "recipient_type": "individual",
 "to": "+584141234567", "type": "text", "text": {"body": "Hola"}}
```

Image payload (`send_media` — flyers, link-based):
```json
{"messaging_product": "whatsapp", "recipient_type": "individual",
 "to": "+584141234567", "type": "image",
 "image": {"link": "https://...", "caption": "<=1024 chars"}}
```

Response: `{"messaging_product":"whatsapp","contacts":[{"input":"...","wa_id":"58414..."}],"messages":[{"id":"wamid.XXX","message_status":"accepted"}]}`.

- **Return contract:** `{'message_id': 0, 'wamid': 'wamid.XXX'}` — `message_id` keeps the Massiva integer contract for existing callers; the string wamid rides separately.
- **Retry:** the Kapso client has NO built-in retry, so `_post_message()` retries **once** on network error, HTTP 429 (honors `Retry-After`, capped 30s) and 5xx. 4xx parses the Meta `{"error":{"message"}}` shape into a `UserError`.
- **Throttle:** same module-global `_last_send_time` pattern as Massiva, but default **3s** (`ai_agent.kapso_send_interval`); `<=0` disables.
- **Kill switch:** `_check_kill_switch()` raises `UserError` when `ai_agent.wa_credits_ok=False` — same guard, same Spanish message, checked in both `send_message` and `send_media`.
- `validate_phone()`: Kapso/Meta has no cheap validation endpoint → soft E.164 plausibility check only (`+`, len ≥ 12).

### Inbound (Kapso) — webhook push, not polling

`controllers/kapso_webhook.py` — `POST /ai-agent/kapso/webhook`, **`type='http'`**, `auth='public'`, `csrf=False`:

1. Reads the **raw body** (`request.httprequest.get_data()`) and verifies **HMAC-SHA256 of the raw body** against the `X-Webhook-Signature` header (also accepts `X-Hub-Signature-256` `sha256=<hex>` for kind='meta' webhooks). Enforced **only when `ai_agent.kapso_webhook_secret` is set** (voice_webhook pattern). Bad signature → 401.
2. Parses the Kapso **v2 flat envelope** (`{"message": {...}, "conversation": {...}}`), a defensive buffered `{"messages": [...]}` list, and the Meta-shaped `{object, entry:[{changes:[{value:{messages}}]}]}` passthrough. Skips `kapso.direction != 'inbound'` echoes; status/conversation events ACK quietly.
3. Delegates each inbound message to `ai.agent.conversation._handle_kapso_inbound(phone, text, wamid, media_url, contact_name)`.
4. **Always returns 200** on processing errors — wamid dedup makes Kapso redeliveries safe; a retry storm helps nobody.

`_handle_kapso_inbound` (ai_agent_conversation.py ~L3000) — the push-mode mirror of the poll cron's Phase-2 handoff:

- **Gate:** processes only when `wa_provider='kapso'` **or** `ai_agent.kapso_inbound_enabled=True` (parallel/sandbox testing while Massiva is still primary); plus `_is_active_environment()` + **`ai_agent.dry_run`** (gates the WA leg exactly like the poll cron).
- Normalizes phone, rejects group JIDs, **global dedup on `ai.agent.message.kapso_message_id`** (new indexed `Char` field for the string wamid — `whatsapp_message_id` is an Integer and cannot store it).
- Conversation lookup: existing waiting/active by phone, else `_get_or_create_general_inquiry_conversation(phone)` (same as the poll cron — this webhook DOES create conversations, unlike the dead Massiva webhook).
- Per-skill `respect_schedule` gate → `'deferred'` (see Known gaps).
- `action_process_reply(text, wa_message_id=0, kapso_message_id=wamid, attachment_url=media_url)` inside a **savepoint**; on failure, orphan hygiene unlinks a brand-new empty conversation (same cleanup as the poll cron).

**Massiva poll cron under Kapso:** `fetch_received()` dispatches to the Kapso service, which returns `[]` — `_cron_poll_messages` becomes a harmless no-op. No cron change needed at flip time.

---

## Config & parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `ai_agent.wa_provider` | `massiva` | **The switch.** `'kapso'` flips all 4 facade methods |
| `ai_agent.kapso_api_key` | — (required) | Kapso project API key (X-API-Key). Currently a **test** key |
| `ai_agent.kapso_phone_number_id` | — (required) | Meta phone_number_id — in the **URL path only**. Currently the sandbox number |
| `ai_agent.kapso_proxy_base_url` | `https://api.kapso.ai/meta/whatsapp` | Meta proxy base (SENDS) |
| `ai_agent.kapso_graph_version` | `v23.0` | Required URL segment on the proxy |
| `ai_agent.kapso_platform_base_url` | `https://api.kapso.ai/platform/v1` | Platform API (webhook CRUD, history — **GET-only for messages**) |
| `ai_agent.kapso_webhook_secret` | — | HMAC secret for `/ai-agent/kapso/webhook`; empty = signature not enforced |
| `ai_agent.kapso_send_interval` | `3` | Seconds between sends (module-global throttle); `<=0` disables |
| `ai_agent.kapso_inbound_enabled` | `False` | Process inbound webhooks while provider is still `massiva` (testing) |

**Config file** `/opt/odoo-dev/config/kapso_api.json` (gitignored, mode 600) — seeded into params by the post-init hook `_load_api_configs(env)` in `ueipab_ai_agent/__init__.py` (L86-109) on module install/upgrade. Same search order as the other config files (`$AI_AGENT_CONFIG_DIR`, `/opt/odoo-dev/config`, `/etc/odoo`, `/home/vision/ueipab17/config`) — so **the file must also exist at `/home/vision/ueipab17/config/` on the prod host**. Shape (secrets redacted):

```json
{
  "provider": "Kapso",
  "dashboard": "https://app.kapso.ai",
  "api_base_url": "https://api.kapso.ai/platform/v1",
  "auth_header": "X-API-Key",
  "api_key": "<REDACTED>",
  "api_key_kind": "test",
  "phone_number_id": "597907523413541",
  "proxy_base_url": "https://api.kapso.ai/meta/whatsapp",
  "graph_version": "v23.0",
  "webhook_secret": "<REDACTED>"
}
```

The hook seeds `api_key` → `kapso_api_key`, `phone_number_id` → `kapso_phone_number_id`, `webhook_secret` → `kapso_webhook_secret`, `proxy_base_url` → `kapso_proxy_base_url`, and defaults `ai_agent.wa_provider='massiva'` if unset. As with Massiva: **editing the JSON does nothing at runtime** — `ir.config_parameter` is the truth; re-seed via `-u ueipab_ai_agent` or manual `set_param`.

**Kill switches that still apply under Kapso:**

- `ai_agent.wa_credits_ok` — checked inside the Kapso service too (both send methods). Flipped by the Credit Guard cron.
- `ai_agent.dry_run` — gates `_handle_kapso_inbound` (returns `'dry_run'`) AND the `_send_to_user` WA leg, exactly as under Massiva.
- **Credit Guard:** `_check_whatsapp_credits()` short-circuits to **healthy** when `_provider()=='kapso'` — Kapso has no Massiva `/get/subscription` endpoint, so without this the guard would false-trip `wa_credits_ok=False` after 2 failed checks.

---

## Current state (2026-07-01)

- **Test API key** + **Kapso SANDBOX number** (`phone_number_id=597907523413541`). Sandbox sends require an active sandbox session (dashboard: WhatsApp → Sandbox → Add Test Number → 6-char code from the phone) — **session active for 584148321989**.
- **Live send test delivered 2026-07-02 01:49 UTC** via the sandbox number.
- **Webhook CRUD verified** against the platform API (create/list/delete round-trip on `/whatsapp/phone_numbers/{pnid}/webhooks`).
- Dedicated number +58 414-8321989 **NOT yet on Kapso** (still parked broken on Massiva's WABA).
- **Prod deploy = dormant**: module code ships everywhere, `ai_agent.wa_provider` stays `massiva`, `kapso_inbound_enabled=False`. Nothing changes in behavior until the flip.

---

## Cutover runbook

Each step gates the next. **ROLLBACK at any point after step 7 = set `ai_agent.wa_provider='massiva'` — single param, instant** (Massiva code path is untouched).

1. **Release +58 414-8321989 from the Massiva WABA** (Massiva support request — the number must be free before Meta/Kapso can claim it).
2. **Connect it as a dedicated number in Kapso** (`kapso setup --no-provision-phone-number`, then link the number). Record the **new `phone_number_id`**.
3. **Create a PRODUCTION API key** in the Kapso dashboard (current key is `api_key_kind: "test"`).
4. **Update `kapso_api.json` on BOTH hosts** (`/opt/odoo-dev/config/` + `/home/vision/ueipab17/config/`): new `api_key`, `phone_number_id`, `webhook_secret`. **Re-seed params** — module upgrade (`-u ueipab_ai_agent`) or manual `set_param` for the three values.
5. **Register the webhook via the platform API** (note the `whatsapp_webhook` body wrapper):
   ```
   POST {platform_base_url}/whatsapp/phone_numbers/{pnid}/webhooks
   {"whatsapp_webhook": {
      "url": "https://odoo.ueipab.edu.ve/ai-agent/kapso/webhook",
      "kind": "kapso", "payload_version": "v2",
      "events": ["whatsapp.message.received"],
      "secret_key": "<same value as ai_agent.kapso_webhook_secret>",
      "active": true}}
   ```
6. **Smoke test inbound while provider is still `massiva`:** set `ai_agent.kapso_inbound_enabled=True`, send a test message to the number, verify round-trip (webhook 200 → conversation → Glenda reply via facade). Then set it back to `False` (it becomes redundant after the flip anyway).
7. **FLIP:** `ai_agent.wa_provider = 'kapso'` in prod. Poll cron auto-degrades to no-op; all facade sends now route to Kapso.
8. **Update the published number:** `ai_agent.whatsapp_primary_phone` param + public `wa.me` links — Annual Report page `web/reporte-anual-2025-2026/index.html`: `wa.me/584248944898` → `wa.me/584148321989`.
9. **Retire Massiva-era crons:** delete `/etc/cron.d/ai_agent_wa_health` and `/etc/cron.d/wa_primary_relay`; **keep** `/etc/cron.d/wa_invoice_reminder_poller` (provider-agnostic — launches whichever `wa_invoice_reminder.py` variant exists).

---

## Host-script cutover inventory

Direct-Massiva host scripts (all load `whatsapp_massiva.json` + POST `{base}/send/whatsapp`). Everything going through `ai.agent.whatsapp.service` (in-module or via XML-RPC) gets Kapso **for free** at the flip — this list is only the direct-API callers.

| Script | Verdict | Notes |
|--------|---------|-------|
| `wa_invoice_reminder.py` | **PORT** | Needs a Kapso send helper (`send_whatsapp()` ~L499-508). ⚠️ Looks retired (`/etc/cron.d/wa_invoice_reminder` fully commented) but is **LIVE** via wizard → trigger-param → poller → `--adhoc`. Revisit the 120-140s pacing (Massiva-only). |
| `ai_agent_escalation_bridge.py` | **PORT** | Send-helper swap only (CEO WA escalation notify, L134) |
| `glenda_supervisor.py` | **PORT** | Send-helper swap only (critical-score CEO WA alert, L348) |
| `pagos_receipt_processor.py` | **PORT** | Send-helper swap only (L260). ⚠️ Has a prod-host fallback config path — drop `kapso_api.json` on BOTH hosts |
| `ai_agent_wa_health_monitor.py` | **RETIRE** | Entirely Massiva multi-account semantics (validate + primary↔backup param switching). Kapso health = new design if ever needed |
| `wa_primary_relay.py` | **RETIRE** | Exists only because the Massiva primary is broken. Delete + its cron. ⚠️ Reads config from Odoo params (`ai_agent.whatsapp_base_url`), not the JSON — config-file sweeps miss it |
| `send_contingencia_wa.py` | **RETIRE** | Closed campaign (contingencia survey, closed 2026-07-01) |
| `contingencia_voice_batch.py` | **RETIRE** | Closed campaign |
| `send_vote_wa_reminder.py` | **RETIRE** | Closed campaign (budget vote closed 2026-05-26) |
| `wa_invoice_reminder_poller.py` | **NO CHANGE** | Pure XML-RPC + subprocess launcher; provider-agnostic |
| `enrollment_s0_blast.py` | **NO CHANGE** | WA fallback goes through `ai.agent.whatsapp.service` over XML-RPC — cutover happens inside the module |

Ready-to-copy Kapso send helper for host scripts:

```python
import json
import requests

def _load_kapso_config():
    for path in ('/opt/odoo-dev/config/kapso_api.json',
                 '/home/vision/ueipab17/config/kapso_api.json'):
        try:
            with open(path) as f:
                return json.load(f)
        except FileNotFoundError:
            continue
    raise RuntimeError("kapso_api.json not found")

def send_whatsapp_kapso(phone, message):
    """phone must be E.164 ('+58414...'). Returns the wamid string."""
    cfg = _load_kapso_config()
    url = "%s/%s/%s/messages" % (
        cfg.get('proxy_base_url', 'https://api.kapso.ai/meta/whatsapp').rstrip('/'),
        cfg.get('graph_version', 'v23.0'),
        cfg['phone_number_id'])
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': phone,
        'type': 'text',
        'text': {'body': message},
    }
    resp = requests.post(url, json=payload,
                         headers={'X-API-Key': cfg['api_key']}, timeout=30)
    resp.raise_for_status()
    return resp.json()['messages'][0]['id']   # 'wamid.XXX'
```

---

## Known gaps / Phase 2

- **Schedule-deferred inbound messages are lost:** `_handle_kapso_inbound` returns `'deferred'` with HTTP 200, and Kapso does not retry an ACKed delivery (the Massiva poll model retried them on the next 5-min pass). **Accepted for now** — `general_inquiry`, the only auto-created skill, is 24/7 exempt from the schedule; other skills' conversations rarely receive off-hours inbound. Phase 2 option: queue deferred payloads for replay.
- **Kapso `media_url` auth semantics unverified** for inbound attachments — `_handle_kapso_inbound` passes `kapso.media_url` straight into `attachment_url`; whether the URL is public/expiring/needs the API key has not been tested with a live inbound image.
- **Status events not consumed:** `whatsapp.message.sent/delivered/read/failed` are ACKed and discarded (`no_inbound_messages`). Delivery-status tracking on `ai.agent.message` = Phase 2.
- **Host scripts still Massiva** until the cutover PORT step (table above).
- **voice_gateway / Twilio unaffected** — Glenda voice calls are a separate stack. **Telegram unaffected** — separate channel/service entirely.

---

## Gotchas

- **The platform API `/whatsapp/messages` is GET-only** (history). Sends go to the separate **Meta proxy** base: `POST https://api.kapso.ai/meta/whatsapp/{graph_version}/{phone_number_id}/messages`. Do NOT POST to the platform base.
- **The graph version segment (`v23.0`) is REQUIRED** in the proxy URL path.
- **`phone_number_id` lives only in the URL path** — never in the body or query.
- **The wire is snake_case** (`messaging_product`, `recipient_type`, `preview_url`); the camelCase seen in Kapso SDK/CLI output is client-side camelization. Writing raw JSON from Python: use snake_case.
- **No SDK-style retry exists** in the Kapso client — our `_post_message()` retries exactly once (network / 429-with-Retry-After / 5xx). Anything more = caller's problem.
- **wamid is a string** (`wamid.XXX`) → the new `ai.agent.message.kapso_message_id` `Char` (indexed) dedup field, because the legacy `whatsapp_message_id` is an **Integer** and cannot hold it. Kapso sends return `{'message_id': 0, 'wamid': ...}` to preserve the integer contract for old callers.
- **Webhook create bodies are wrapped:** `{"whatsapp_webhook": {...}}` — a bare payload is rejected. `secret_key` is auto-generated (64 hex) if omitted; kind=`kapso` defaults events to `["whatsapp.message.received"]`; kind=`meta` REJECTS events/buffering options.
- **Why the Kapso controller is `type='http'`:** the old Massiva webhook controller was **doubly broken** — `type='json'` (Odoo 17 expects a JSON-RPC envelope; Massiva POSTs form-encoded) AND it used `request.jsonrequest`, removed in Odoo 17. The Kapso route reads the raw body itself (`type='http'` + `json.loads`), which is also mandatory for HMAC verification over the exact raw bytes.
- **HMAC is enforced only when `ai_agent.kapso_webhook_secret` is set** — the same "enforce iff configured" pattern as `voice_webhook.py`. Set the param AND the webhook `secret_key` to the same value, or you run open.
- **Throttle state is a module-level global per Odoo worker** (same caveat as Massiva): 3 workers can each send within the interval of each other. Fine at 3s; do not rely on it for strict rate limiting.
- **`dry_run` is enforced in callers, not in the send service** (unchanged from Massiva): `_send_to_user` and `_handle_kapso_inbound` gate it; a new direct caller of `send_message` bypasses `dry_run` — only `wa_credits_ok` is enforced in-service.

---

## File inventory (Phase 1)

| File | Change |
|------|--------|
| `models/kapso_service.py` | NEW — `ai.agent.kapso.service` provider (send_message / send_media / validate_phone / fetch_received) |
| `controllers/kapso_webhook.py` | NEW — `POST /ai-agent/kapso/webhook` (type='http', HMAC) |
| `models/whatsapp_service.py` | `_provider()` + dispatch at the top of the 4 public methods |
| `models/ai_agent_conversation.py` | `_handle_kapso_inbound()` + `_check_whatsapp_credits()` kapso short-circuit + `kapso_message_id` kwarg on `action_process_reply` |
| `models/ai_agent_message.py` | `kapso_message_id` Char field (indexed) |
| `__init__.py` | `_load_api_configs`: seed `ai_agent.kapso_*` from `kapso_api.json` + `wa_provider` default |
| `__manifest__.py` | version → 17.0.1.61.0 |
| `config/kapso_api.json` | NEW (gitignored) — test key + sandbox number |

---

## Security & correctness review (2026-07-01)

A multi-agent adversarial review (4 review dimensions × per-finding refutation) ran against the Phase-1 diff. **13 findings confirmed, 2 refuted.** Fixes applied in v17.0.1.61.0:

| # | Finding | Fix applied |
|---|---------|-------------|
| 1 | Webhook fails **open** when `kapso_webhook_secret` unset while Kapso inbound is active (forged messages → Claude token burn, spoofed convs) | **Fail closed**: reject 401 when `wa_provider='kapso'` OR `kapso_inbound_enabled=True` and no secret is set. Dormant state still passes (handler no-ops). |
| 2 | SSRF via attacker-controlled inbound `media_url` fetched server-side | `_is_safe_media_url()` — https-only + rejects private/loopback/link-local/reserved resolved IPs; unsafe URL dropped (text kept). Applied on the Kapso inbound path. |
| 4/10 | wamid dedup was check-then-create with no DB constraint (concurrency race on redelivery) | `UNIQUE(kapso_message_id)` `_sql_constraints` on `ai.agent.message` (Postgres ignores NULL → Massiva/Telegram unaffected). Losing racer raises inside the savepoint. |
| 7 | 4xx error extraction crashed (`AttributeError`) on non-dict `error` body | `except (ValueError, AttributeError)` → falls back to raw response text. |
| 8 | `send_message` raised on missing wamid **after** a 2xx accept → retrying caller double-sends | Warn + stamp throttle + return (mirrors `send_media`); no raise after acceptance. |
| 11 | Webhook ACKed processing failures with HTTP 200 → transient Claude 429 / DB error = permanent message loss | Return **502** on `'error'` results so Kapso redelivers; wamid dedup makes redelivery idempotent. `skipped`/`deferred`/`dry_run`/`duplicate` stay 200. |
| 14 | Inbound media type discarded → extension-guess default `'image'` mistypes voice notes / receipts | Propagate Meta `message.type` → `attachment_type_hint` via `_KAPSO_MEDIA_TYPE_MAP`; falls back to extension only when absent. |
| 15 | Reactions/locations/unsupported types → empty Claude turn (assistant-prefill continuation) | Empty-content guard: skip when no text and no media (mirrors poll cron). |

**Refuted (no change):** "dormant deploy needs a DB upgrade" (that is the normal Odoo contract — `-u` is in the runbook); "own-phone self-loop guard is Massiva-only" (cutover migrates the *same* number, so it stays in the phone params).

### ⚠️ Remaining pre-cutover hardening (Phase 2 — do BEFORE flipping `wa_provider='kapso'`)

These only bite once Kapso is the **live inbound** provider (gated on the dedicated-number connection that is not yet done), so they do not block the dormant Phase-1 deploy — but they MUST be closed before step 7 of the cutover runbook:

- **Deferred / dry_run message persistence (findings #6, #13):** when an inbound hits the per-skill schedule gate (`respect_schedule` + outside window) or `dry_run=True`, the handler returns `'deferred'`/`'dry_run'` and the message is **not persisted** — the webhook 200s and Kapso will not redeliver, so it is dropped. The poll-cron model left such messages queued for the next run. Impact is narrow today (auto-created inbounds are `general_inquiry`, which is 24/7 `respect_schedule=False`; prod `dry_run=False`), but before cutover add a holding row (persist the inbound `ai.agent.message` with `kapso_message_id` set, dedup-safe) + a drain step in `_cron_poll_messages` when the window opens.
- **Full SSRF helper across shared sinks:** `_is_safe_media_url()` guards the Kapso inbound entry, but the downstream fetchers (`_transcribe_audio`, `_extract_payment_receipt`, `_convert_pdf_to_image`, `_cron_archive_attachments`) are shared with the Massiva path and still fetch any stored `attachment_url`. Consider centralizing egress validation in those sinks.
