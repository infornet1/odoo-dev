# Glenda Voice Call — POC (Outbound, Twilio ↔ OpenAI Realtime)

**Status:** ✅ **POC LIVE — first successful call 2026-06-30** | **Created:** 2026-06-30 | **Owner:** dev

## POC RESULT (2026-06-30)

First end-to-end live call succeeded — Glenda held a real spoken Spanish conversation with
Gustavo (`+584142337463`) over PSTN. Chain proven: Twilio outbound → Media Streams → gateway
(g711 µ-law passthrough) → **OpenAI Realtime GA** → back to the phone. Call SID `CA88332f…`.

Two fixes were needed during the first test:
1. **`python-multipart`** — FastAPI needs it to parse Twilio's form-encoded POST to `/twiml`
   (first call 530'd with `AssertionError: python-multipart must be installed`). Added to requirements.
2. **OpenAI Realtime Beta → GA migration** — the beta event shape was rejected
   (`beta_api_shape_disabled`). GA changes applied in `gateway.py`:
   - Drop the `OpenAI-Beta: realtime=v1` header.
   - `session.update` audio config nests under `session.audio.input` / `session.audio.output`;
     add `session.type:"realtime"` + `output_modalities:["audio"]`.
   - g711 µ-law format = `{"type":"audio/pcmu"}` (was `input/output_audio_format:"g711_ulaw"`).
   - Output audio event renamed `response.audio.delta` → **`response.output_audio.delta`**.

**Twilio account:** `AC2799…f7da` (active), API-Key auth (`SKc941…`). Numbers: `+15093843032`
(from_number) + `+12564721168`, both US/voice. ⚠️ Balance was **$2.81 USD** at test time —
top up before any volume. Venezuela geo-permission enabled 2026-06-30.

**Voice / accent tuning:** OpenAI has NO accent-locked Spanish voices — accent is steered by the
persona prompt (`glenda_instructions.py` now mandates Venezuelan/Caracas accent + usted-form).
`gateway.voice` and `gateway.realtime_model` are **hot-swappable** — edit `config/twilio_api.json`
and redial, no restart (gateway re-reads both per call). Valid voices: alloy, ash, ballad, coral,
echo, sage, shimmer, verse, marin, cedar (female-leaning: coral/sage/shimmer/marin/ballad).
**CHOSEN DEFAULT (2026-06-30): `sage` + `gpt-realtime-2`** (gpt-realtime-2 follows accent instructions
more strongly). Locked in config, example template, and code fallback. A/B tested coral/sage/shimmer/ballad.

Adds real **voice calls** to Glenda. Phase 1 scope (decided with CEO 2026-06-30):

| Decision | Choice |
|----------|--------|
| Direction | **Outbound only** (Glenda calls parents) |
| Channel | **PSTN via Twilio** Programmable Voice + Media Streams |
| Brain | **OpenAI Realtime API** (speech-to-speech), Glenda persona injected |

Inbound, WhatsApp-voice, and Odoo wiring are explicitly out of scope for the POC.

---

## Architecture

```
Odoo (later: ai.agent.voice.call queue)        ← NOT in POC
        │  place_call.py (POC: one call to Gustavo)
        ▼
Twilio REST  POST /Calls (Url → gateway /twiml)
        │
Parent phone (PSTN, +58)  ◄──►  Twilio Voice
        │  Media Streams — WebSocket, base64 g711_µlaw 8kHz
        ▼
VOICE GATEWAY  (voice_gateway/, async Python, OWN container — never an Odoo worker)
        │  PASSTHROUGH: relays base64 audio frames, no transcoding
        ▼
OpenAI Realtime API  wss://api.openai.com/v1/realtime?model=gpt-realtime
        • session.instructions = Glenda voice persona + MEDIOS DE PAGO
        • input/output_audio_format = g711_ulaw  ← matches Twilio, zero transcode
        • server VAD + barge-in (Twilio "clear" on speech_started)
```

**Why this combo is small:** Twilio Media Streams and OpenAI Realtime *both* speak
`g711_ulaw`, so the gateway never decodes/encodes audio — it shuttles base64 between
two WebSockets. That is the entire trick.

---

## Files (`voice_gateway/`)

| File | Purpose |
|------|---------|
| `gateway.py` | FastAPI app. `POST /twiml` → `<Connect><Stream>`; `WS /media` → Twilio↔OpenAI bridge; `/health`. |
| `glenda_instructions.py` | Voice persona + `MEDIOS DE PAGO` (mirror of `general_inquiry.py`; **Banco de Venezuela excluded**). `build_instructions(call_reason, extra_context)`. |
| `config_loader.py` | Reads `config/twilio_api.json` + reuses `config/openai_api.json` key; env-var overrides. |
| `place_call.py` | Places ONE outbound test call (default = Gustavo `+584142337463`). |
| `requirements.txt` | fastapi, uvicorn[standard], websockets, twilio. |
| `Dockerfile` | python:3.12-slim, runs uvicorn on :8090. |
| `config/twilio_api.json.example` | Config template (copy to `twilio_api.json`, gitignored). |

Persona/payment data is mirrored from
`addons/ueipab_ai_agent/skills/general_inquiry.py` — keep in lock-step.

---

## Setup

### 1. Twilio account access (see "Full Twilio API access" below)
Fill `config/twilio_api.json` (`account_sid`, `auth_token`, `from_number`).

### 2. OpenAI Realtime
Reuses the existing `config/openai_api.json` key (`ai_agent.openai_api_key`).
Confirm the account/key is enabled for the **Realtime** model (`gpt-realtime`).

### 3. Run the gateway
```bash
cd voice_gateway
pip install -r requirements.txt
uvicorn gateway:app --host 0.0.0.0 --port 8090
```

### 4. Make it publicly reachable (Twilio must reach it over HTTPS/WSS)

**DEPLOYED ON `ueipab2` (64.23.157.121) via systemd + cloudflared quick tunnel — 2026-06-30.**

| Unit | Role | State |
|------|------|-------|
| `glenda-voice.service` | uvicorn gateway on `:8090` (venv `voice_gateway/.venv`) | enabled + active |
| `glenda-voice-tunnel.service` | `run_tunnel.sh` → cloudflared quick tunnel → writes `.tunnel_url` | enabled + active |

- The gateway derives its public host from the inbound request `Host` header, so the
  **ephemeral** `*.trycloudflare.com` URL works with no config edit. `place_call.py` reads
  `.tunnel_url` for the TwiML URL.
- ⚠️ **Quick-tunnel URL changes on every tunnel restart** — fine for POC, not for production.
- ⚠️ **DO Cloud Firewall fix (required):** `ueipab-fw` (id `1871d446-…`) is default-deny
  outbound with an allowlist; cloudflared needs **outbound 7844**. Added `tcp/7844` + `udp/7844`
  via DO API on 2026-06-30 (`POST /v2/firewalls/{id}/rules`). Without this the tunnel returns HTTP 530.

**Production (stable hostname) — recommended next:** this host already serves nginx/443 with
Let's Encrypt (dev + freescout). Add DNS `A voice.ueipab.edu.ve → 64.23.157.121` (DigitalOcean),
an nginx server block proxying `:8090` with WebSocket upgrade headers, and certbot. Then set
`gateway.public_host=voice.ueipab.edu.ve` and the quick tunnel can be retired. Needs only inbound
443 (already open) — no 7844 dependency.

### 5. Place the test call
```bash
cd voice_gateway
python place_call.py                 # → Gustavo
python place_call.py +584142337463 "Recordatorio de saldo pendiente"
```

---

## Full Twilio API access (what to give the dev / set up)

To let the gateway place calls + stream media, the Twilio account needs:

1. **Account SID + Auth Token** — Twilio Console → top-right account menu → *Account → API keys & tokens*.
   - `Account SID` (starts `AC…`) and the primary `Auth Token`.
   - **Better practice:** create a *Standard API Key* (SID `SK…` + secret) and use that instead of the
     primary auth token, so it can be revoked independently. The Twilio SDK accepts
     `Client(api_key_sid, api_key_secret, account_sid)`. (POC code uses account SID + auth token; swap if you prefer.)
2. **A voice-capable phone number** (`from_number`) — Console → *Phone Numbers → Manage → Buy a number*,
   with **Voice** capability. A US number is fine for the POC (caller-ID caveat below).
3. **Outbound geo-permissions to Venezuela** — Console → *Voice → Settings → Geographic Permissions* →
   enable **Venezuela** (and mobile/landline as needed). Calls to +58 fail silently until this is on.
4. **(Optional) Media Streams** — no special toggle; it's TwiML `<Connect><Stream>`, available by default.
5. **Billing** — a funded balance or active subscription; outbound to VE is per-minute.

**Minimum to hand the dev:** `Account SID`, `Auth Token` (or API Key SID+secret), and the
purchased `from_number`. Everything else is console configuration above.

> Sharing tip: put them straight into `config/twilio_api.json` on the dev box (gitignored), or send
> via a secure channel — never commit them. The example file shows the exact shape.

---

## Test checklist

- [ ] `config/twilio_api.json` filled; `/health` returns ok.
- [ ] Gateway publicly reachable (tunnel or nginx); `https://<host>/twiml` returns XML.
- [ ] VE geo-permission enabled in Twilio.
- [ ] `place_call.py` → Gustavo's phone rings.
- [ ] Glenda **speaks first**, in Spanish, identifies as automated assistant.
- [ ] **Barge-in** works (interrupting cuts her off).
- [ ] Latency acceptable; Spanish (Venezuela) quality acceptable → pick `voice` (`marin`/`cedar`/…).
- [ ] Note answer-rate reality with a foreign caller ID.

---

## Caveats (carry into the go/no-go after the POC)

1. **Caller ID** — a Twilio US number → low pickup for VE parents. Biggest ROI risk.
   Mitigation: WhatsApp/SMS heads-up before calling.
2. **Cost** — Twilio per-min to VE **+** OpenAI Realtime audio (~$0.50–$1+ for 2–3 min).
   Targeted use only (overdue balances, enrollment confirmations); never mass-call.
3. **Disclosure/consent** — opens as automated assistant; honor opt-out; reuse quiet hours / VET work hours.
4. **Recording** — off by default; enable only with a retention/privacy decision.
5. **Concurrency/RAM** — each call holds a persistent WS; cap concurrency, keep gateway off the dev Odoo box.

---

## Odoo integration (ueipab_ai_agent v17.0.1.60.0 — testing 2026-06-30)

UI to **track calls** + **manage settings**, wired to the gateway both directions.

**Model `ai.agent.voice.call`** (`models/ai_agent_voice_call.py`): partner, phone, direction,
call_reason, status, twilio_sid, caller_id, voice, realtime_model, duration, price, transcript,
disposition, recording_url, started/ended, error, notes. Button **📞 Llamar ahora** =
`action_place_call()` → `POST {gateway}/place-call`. `ingest_callback()` applies gateway updates.

**Settings** (`res.config.settings`, app block "Glenda Voz", menu *Configuracion → Ajustes de Voz*),
all in `ir.config_parameter`: `voice_call.enabled` / `caller_id` / `voice` / `realtime_model` /
`gateway_url` / `callback_base` / `callback_token`.

**Controller** `/ai-agent/voice/callback` (type=json, public, token-checked) → `ingest_callback`.

**Gateway endpoints added:** `POST /place-call` (Odoo→gateway, stores per-CallSid context, dials
Twilio with `status_callback`), `POST /call-status` (Twilio→gateway→Odoo: status+duration),
transcript captured live (`response.output_audio_transcript.done` = Glenda,
`conversation.item.input_audio_transcription.completed` = Cliente) and POSTed to Odoo on hangup.

**Networking (testing):** Odoo (Docker) → gateway = `http://172.18.0.1:8090` (container's bridge gw);
gateway (host) → Odoo = `http://localhost:8069`. Menu: *AI Agent → Operaciones → Llamadas de Voz*.

**Verified 2026-06-30:** module upgrades clean; model/actions/menus registered; settings seeded;
container→gateway `/place-call` reachable; gateway→Odoo `/callback` updates the record (status,
duration, transcript, token-checked). NOT yet exercised: a real ring through the UI button.

## Function tools (live data — 2026-06-30)

Glenda can pull LIVE Odoo data mid-call (static facts stay in the voice prompt). GA realtime
`session.tools` + `tool_choice:auto`; on `response.function_call_arguments.done` the gateway POSTs
`{name,arguments,callback_token}` to Odoo `/ai-agent/voice/tool` (token-checked) → model method
`ai.agent.voice.call.voice_tool()`, then feeds the result back via `function_call_output` + `response.create`.

| Tool | Returns | Source |
|------|---------|--------|
| `get_pricing` | 2026-2027 tarifas + **fechas de inscripción** (llamados) | `sale.order.get_pricing_ground_truth()` (live catalog) |
| `get_balance(cedula)` | saldo pendiente del representante | posted `out_invoice` residual by VAT |

Prompt now mandates using get_pricing for prices/dates (fixes the earlier "no tengo la fecha" deferral).
✅ Both tool endpoints verified returning real data 2026-06-30. ⏳ Not yet observed firing in a live
answered call (demo to Alvaro/Dawere +584241522298 = no-answer).

## Next steps (post-POC)

1. **See a tool fire live** — answered call where the parent asks price/enrollment → get_pricing.
2. **Disposition auto-tagging** — add `log_call_outcome(...)` so Glenda sets `disposition`.
4. **Campaign queue** — reuse invoice-reminder segmentation to mass-create `ai.agent.voice.call` rows.
5. **Production deploy** — stable `voice.ueipab.edu.ve` (nginx) replacing the ephemeral tunnel; gateway
   creds stay in the file (out of Odoo); concurrency cap + quiet hours.

---

## Related

- `documentation/META_CLOUD_API_MIGRATION_PLAN.md` — if WhatsApp voice is ever preferred over PSTN.
- `addons/ueipab_ai_agent/skills/general_inquiry.py` — source of truth for Glenda persona + MEDIOS DE PAGO.
- `documentation/WA_INVOICE_REMINDER_PLAN.md` — segmentation to reuse for outbound call lists.
