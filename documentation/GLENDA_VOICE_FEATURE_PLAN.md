# Glenda Voice Capabilities — Research & Implementation Plan

**Status:** Research complete | **Created:** 2026-05-10 | **Priority:** Deferred

---

## Research Summary

### MassivaMóvil limitations

MassivaMóvil is strictly a **WhatsApp messaging platform**, not a telephony provider.

| Feature | Status |
|---------|--------|
| Text messages | ✅ Full |
| Audio file (`type=audio`, `type=voice`, `type=ptt`) | ✅ API accepts it |
| Video, image, document | ✅ Accepted |
| `/send/call`, `/make/call`, IVR, TTS phone calls | ❌ "Invalid API Endpoint" |
| WhatsApp voice notes (PTT) | ✅ Sendable as audio file |

WhatsApp Business API (which MassivaMóvil implements) **cannot initiate voice calls** — calls are P2P and encrypted. MassivaMóvil has no telephony product.

**Audio type delivery note:** `type=photo` had a confirmed delivery bug (messages queued but not delivered). `type=audio` may have the same issue — must be tested before committing to Option A.

---

## Three Options

### Option A — WhatsApp Voice Notes (TTS → PTT)

Glenda generates a text response → TTS engine converts to MP3 → MassivaMóvil `type=audio` delivers it as a WhatsApp voice note.

**Flow:**
```
Claude generates text
    → TTS engine (ElevenLabs / OpenAI TTS / Google TTS)
    → MP3 file (hosted publicly or uploaded)
    → MassivaMóvil type=audio → customer receives WA voice note
```

**Providers:**

| Provider | Cost | Quality | Notes |
|----------|------|---------|-------|
| OpenAI TTS | $0.015 / 1k chars | Good | Simplest — already using Anthropic SDK pattern |
| ElevenLabs | $0.30 / 1k chars | Excellent | Most natural Venezuelan Spanish |
| Google TTS | Free tier (1M chars/mo) | Good | Requires GCP credentials |

**Pros:**
- No extra phone infrastructure
- Stays within WhatsApp — familiar to Venezuelan families
- Natural escalation: text for quick queries, voice note for summaries/urgent messages

**Cons:**
- One-way: Glenda speaks, customer replies in text
- Audio delivery may be broken (same issue as `type=photo` — must verify first)
- Requires public URL to serve audio files (nginx `/var/www/dev/audio/`)

**Implementation effort:** Medium (1–2 days)
- New `send_voice_note(conversation, text)` in `whatsapp_service.py`
- TTS API call (OpenAI recommended — already have Anthropic pattern)
- Nginx rule to serve audio from `/var/www/dev/audio/`
- `ACTION:SEND_VOICE:text_to_speak` marker in skills

---

### Option B — Outbound Phone Calls (Twilio / Vonage)

Glenda initiates an actual phone call, plays a TTS message, handles keypad input.

**Flow:**
```
Odoo triggers Twilio
    → Twilio calls customer phone number
    → TTS plays Claude-generated message
    → Customer presses 1 (confirm) / 2 (callback) / hangs up
    → Webhook → Odoo records outcome
```

**Providers:**

| Provider | Cost | Notes |
|----------|------|-------|
| Twilio Voice | ~$0.013/min outbound + DID | Industry standard, excellent docs |
| Vonage (Nexmo) | Similar pricing | Alternative |
| Telnyx | ~$0.005/min | Cheaper, good API |

**Venezuelan numbers:** Need a Venezuelan DID (+58) or use Twilio international. Local carriers may block calls from non-local originators — requires testing.

**Pros:**
- Reaches people who don't respond to WhatsApp
- Best for: overdue account reminders, PDVSA retention, urgent escalations
- Full IVR possible (press 1 to confirm, 2 to speak with staff)

**Cons:**
- New infrastructure and account
- Venezuelan telephony quality unpredictable
- More intrusive than WhatsApp
- Compliance: must respect no-call hours (CONATEL regulations)

**Implementation effort:** High (3–5 days)
- Twilio account + Venezuelan DID
- New Odoo model `ai.agent.call` for call tracking
- TwiML webhook endpoint in Odoo
- Integration with conversation state machine

---

### Option C — Hybrid (WhatsApp-first + Call Fallback)

Keep WhatsApp primary. If conversation times out (72h no reply) → trigger an automated outbound call as last resort.

**Call script example:**
> *"Hola, le llama el sistema del Instituto Andrés Bello. Le hemos enviado un mensaje de WhatsApp al +58 414 832 1989 que requiere su atención. Por favor revise su WhatsApp. Gracias."*

**Trigger points:**
- Bounce resolution: customer ignored 2 WA reminders → call
- Overdue invoices: balance > $X and no WA response after 48h
- PDVSA retention: high-priority cases only

**Pros:** Most customers reply on WA — calls only as true last resort; lower volume = lower cost

**Cons:** Two providers to manage; more complex state machine (call outcome → back to WA)

**Implementation effort:** High (4–6 days, builds on Option B)

---

## Recommended Approach

**Phase 1 (quick win):** Test `type=audio` delivery with MassivaMóvil.
- Send a test MP3 to a real WA number
- If delivered → implement Option A (voice notes) — 1–2 days
- If not delivered → skip Option A, go directly to Option B

**Phase 2 (escalation path):** Implement Option B for specific high-value triggers:
- Bounce resolution 72h timeout → call
- Overdue balance reminders (billing skill)

**Phase 3:** Combine into Option C hybrid once both channels are stable.

---

## Open Questions

1. Does MassivaMóvil `type=audio` actually deliver to end users? (tech support pending for the `type=photo` issue — same answer likely applies to audio)
2. What Venezuelan DID options does Twilio offer? Do local carriers block international call originators?
3. For voice notes: what language/voice persona matches Glenda's brand? (warm, professional, Venezuelan Spanish)
4. CONATEL compliance: are there time restrictions on automated outbound calls in Venezuela?
5. For Option A: should the voice note replace or accompany the text message?

---

## Related Files

- `addons/ueipab_ai_agent/models/whatsapp_service.py` — `send_media()` (extend for audio)
- `addons/ueipab_ai_agent/skills/general_inquiry.py` — `ACTION:SEND_VOICE` would go here
- `config/whatsapp_massiva.json` — WA API credentials
- `documentation/AI_AGENT_MODULE.md` — full Glenda architecture
- `documentation/GLENDA_AI_AGENT_OVERVIEW.md` — production readiness and skill list
