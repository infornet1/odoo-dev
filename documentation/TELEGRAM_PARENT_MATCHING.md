# Telegram Parent Matching & Opt-in Campaign

**Status:** Phase 1 complete (testing) | Phase 2 dry run complete | Phase 3–5 pending  
**Created:** 2026-05-21  
**Business driver:** WA primary number disabled by Meta after 49 sends during Budget Vote blast — Telegram as spam-free blast channel for future campaigns

---

## Business Case

WhatsApp/Meta blast vulnerabilities exposed during Budget Vote 2026-2027:

| Blast | Number | Sends | Issue |
|---|---|---|---|
| Blast 1 | +584148321989 (primary) | 49 | Disabled by Meta — spam flag |
| Blast 2 | +584248944898 (backup) | 30 | Capped — anti-spam risk |
| Blast 3 | +584148321963 (tertiary) | 30 | Capped — anti-spam risk |
| Blast 4 | +584248944898 (backup) | 9 | Remaining |
| **Total** | 3 numbers rotated | **118** | Over 4 sessions / ~5 hours |

**Telegram advantages for bulk campaigns:**
- No per-number send limits — 178 messages in seconds, not hours
- Free API — zero cost per message
- No Meta throttling or spam detection
- Instant delivery — no 120s anti-spam intervals
- Complements WA — opt-in only, never replaces WA for non-Telegram parents

---

## Current State

**Telegram conversations in production (2026-05-21):**
- Total conversations: 61
- Unique `chat_id`s: 39
- Identified (linked to real Representante partner): **0**
- All 39 are anonymous "Consulta Telegram" stubs — parents contacted Glenda cold with no deep-link

**Key gap:** No `telegram_chat_id` field exists on `res.partner` — there is nowhere to store a matched Telegram ID against a real contact.

---

## Phases

### Phase 1 — `telegram_chat_id` field on `res.partner` ✅ Complete (testing v57.0)
**Module:** `ueipab_ai_agent` (owns Telegram infrastructure)

- Add `telegram_chat_id = fields.Char('Telegram Chat ID')` to `res.partner` via `_inherit`
- Visible in contact form under a new "Canales digitales" group
- Read-only (auto-populated, never typed manually)
- Applies to: Representante (tag 25), Representante PDVSA (tag 26), Empleado contacts

**Note:** `ai.agent.conversation` already has `telegram_chat_id` on the conversation record. Phase 1 moves the link to the canonical `res.partner` so it survives across conversations and is available to blast scripts.

---

### Phase 2 — Dry preliminary match analysis ✅ Complete (2026-05-21)

**Result: 0/61 conversations matched retroactively.**

**Method:** Scanned 162 inbound Telegram messages across 61 conversations for:
- Phone numbers (Venezuelan format) → normalized 10-digit lookup against `res.partner` mobile/phone
- Name keywords (≥4 chars, ≥2 matching words) → fuzzy match against 300 Representante partners

**Findings:**
- Parents used Telegram first names/nicknames only ("Gaby", "Lucy", "Audrey", "Iván", etc.)
- No phone numbers shared in any conversation
- 0 retroactive matches possible

**Conclusion:** Opt-in WA blast (Phase 4) is the only viable path to capture parent Telegram IDs. No shortcuts available.

---

### Phase 3 — FAM_ deep-link handler ⏳ Pending
**Module:** `ueipab_ai_agent` — new handler in `telegram_webhook.py`

**Flow:**
1. Parent receives: `t.me/GlendaUeipabBot?start=FAM_{ack_token}`
2. Clicks link → Telegram sends `start=FAM_{token}` to Glenda webhook
3. Handler looks up `partner.communication.ack` by token → gets `partner_id`
4. Writes `partner.telegram_chat_id = chat_id` on the real `res.partner`
5. Links conversation `partner_id` to real contact (replaces anonymous stub)
6. Glenda replies: *"¡Hola [nombre]! Tu cuenta Telegram quedó vinculada. De ahora en adelante puedo enviarte información importante directamente por aquí."*

**Token reuse:** The existing `partner.communication.ack` token (already unique per parent per campaign) is used as the deep-link payload. No new token infrastructure needed.

**Multiple campaigns:** Each campaign has its own `notice_key` and token. The handler matches whichever campaign token is active and always writes `telegram_chat_id` to the partner regardless of campaign.

---

### Phase 4 — WA opt-in blast campaign ⏳ Pending
**Goal:** Drive parents to click the FAM_ deep-link so their Telegram chat_id gets captured.

**Script:** New `send_telegram_optin_blast.py`

**Message template (WA):**
```
¡Hola [nombre]! 👋

Glenda, la asistente virtual del colegio, ahora también está disponible en Telegram — sin limitaciones y de forma instantánea.

Únete haciendo clic aquí:
👉 t.me/GlendaUeipabBot?start=FAM_[token]

Una vez vinculado, te enviaremos recordatorios, novedades y comunicados importantes directamente por Telegram.

— UEIPAB
```

**Targets:** All 178 Representante partners with `bounce_wa_sent` eligible (skip bounced emails, use WA).  
**Anti-spam:** 120s intervals (same as vote blast) — but this is a one-time opt-in push, not a recurring blast.  
**Fallback:** Parents without WA → receive link via email instead.

---

### Phase 5 — Blast script: Telegram-first channel ⏳ Pending
**Script:** Update `send_vote_wa_reminder.py` + future campaign scripts

**Logic:**
```python
if partner.telegram_chat_id:
    # Send via Telegram — instant, free, no anti-spam wait
    send_telegram(chat_id=partner.telegram_chat_id, text=message)
else:
    # Fallback to WhatsApp — 120s anti-spam interval applies
    send_whatsapp(phone=partner.phone, text=message)
```

**Expected blast performance after opt-in campaign:**
- ~60%+ parents via Telegram (seconds total)
- Remaining via WA (120s intervals, but far fewer)
- Zero risk of Meta disabling a number

---

## Open Questions

1. **Retroactive match rate** — Phase 2 dry run will quantify this. If > 10 parents can be matched, worth doing retroactively before opt-in blast.
2. **opt-in blast timing** — After vote results (May 26)? Or now to maximize coverage before any follow-up vote blasts?
3. **Token per campaign vs. universal token** — Using budget vote ACK token works now, but future campaigns (PDVSA, Representante) have different `notice_key`s. A universal `FAM_{partner_id}` token (without campaign dependency) may be cleaner long-term.
4. **Employee matching** — `EMP_{id}` deep-link already exists for employees. Phase 1 field also covers employees — populate from existing employee Telegram conversations.

---

## Match Log

| Date | Method | Matched | Total Targets | Notes |
|---|---|---|---|---|
| 2026-05-21 | Dry run analysis | **0/61** | 61 Telegram convs | Phase 2 complete — 0 retroactive matches; nicknames only, no phones shared |
| — | FAM_ opt-in blast | TBD | 178 Representantes | Phase 4 pending — WA blast required |
