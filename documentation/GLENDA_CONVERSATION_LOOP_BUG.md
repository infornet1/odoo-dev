# Glenda Conversation Loop Bug — Repeated Greetings + Telegram Invites

**Discovered:** 2026-06-24 | **Reported by:** Gustavo (CEO) | **Customer:** RAIZA RENDON (partner id=2791)
**Module:** `ueipab_ai_agent` | **Fixed in:** v17.0.1.59.6 (symptoms) + **v17.0.1.59.7 (true root cause)** + **v17.0.1.59.8 (orphan hardening)**

---

## ⭐ TL;DR — the real engine (found 2026-06-24 via prod logs)

A **`NameError: '_TD_LABEL' is not defined`** in the payment-receipt email builder
(`_notify_pagos_payment_receipt`) fired *after* Glenda had already sent her WhatsApp reply.
The error unwound the poll-cron savepoint, **rolling back the inbound + outbound message log**.
Next poll cycle the WA-id dedup found no record → **re-processed and re-sent the same reply** →
duplicate-message loop, plus an empty orphaned conversation each time. RAIZA sent payment-receipt
images, so the broken path fired on every turn.

Production log, conv 308 (identical for 310, 312):
```
19:38:50  WhatsApp send to +584148136529 (664 chars)          ← reply SENT (irreversible)
19:38:51  WhatsApp message sent successfully
19:38:54  Receipt (structured): banco=BANCO MERCANTIL monto=84326.2 VES ref=000861971294
19:38:55  ERROR Error processing conversation 308 (RAIZA RENDON): name '_TD_LABEL' is not defined
```

**Fixes (v17.0.1.59.7):**
1. `_TD_LABEL` / `_TD_VAL` are class attributes — referenced as bare names inside the method.
   Changed the 3 uses to `self._TD_LABEL` / `self._TD_VAL`.
2. Wrapped the entire receipt block in `action_process_reply` in its own
   `with self.env.cr.savepoint(): ... except Exception` so receipt bookkeeping can **never again**
   roll back the message log or trigger a resend. The WA reply is already out; receipt failure is
   logged and swallowed.

v17.0.1.59.6 (below) fixed the two *amplifying* symptoms (recreation + per-conv footer); 59.7 fixes
the actual trigger. Both ship together.

---

## Symptom

During a single live WhatsApp exchange, Glenda sent the customer the **same style of message
several times** — a fresh greeting + a payment-receipt acknowledgment + the Telegram
cross-channel invite footer, repeated on each customer message. Example of one such message
(reconstructed from the customer report):

```
¡Hola Raiza! 👋

Veo que realizaste un pago por PagómóvilBDV a Banco Mercantil. El comprobante muestra:
*84.326,20 Bs* (equivalente a aproximadamente *$136,53 USD* a tasa BCV actual)
Fecha: 17/06/2026

Perfecto. Por favor, *notifica este pago a pagos@ueipab.edu.ve* ...

📲 Por cierto, también puede escribirme por Telegram (@GlendaUeipabBot) ... https://t.me/GlendaUeipabBot
```

The repeated **`¡Hola Raiza! 👋` greeting** and the repeated **Telegram footer** are the tells:
both should appear *once* per contact, not on every message.

---

## Evidence (production, DB_UEIPAB)

Querying `ai.agent.conversation` for partner 2791 on 2026-06-24:

| Conv | Channel | State | turn_count | Created | Note |
|------|---------|-------|-----------|---------|------|
| 308 | whatsapp | resolved | 0 | 19:38:44 | **empty** |
| 309 | telegram | resolved | 5 | 19:43:08 | real exchange (BCV, mensualidad, "Gracias") |
| 310 | whatsapp | resolved | 0 | 19:44:33 | **empty** |
| 311 | telegram | resolved | 1 | 19:47:18 | pronto pago |
| 312 | whatsapp | resolved | 0 | 19:49:09 | **empty** |
| 313 | whatsapp | resolved | 2 | 19:53:46 | 2 receipt images, **no outbound logged** |

**Four separate WhatsApp conversations created for one phone (+584148136529) in 15 minutes.**
That fragmentation is the fingerprint of the bug.

---

## Root Cause (two compounding defects)

### 1. Resolved → new-conversation recreation
`_get_or_create_general_inquiry_conversation()` (poll cron / webhook entry point) used to
treat a `resolved` conversation as "done — start a fresh one":

```python
# OLD
# state == 'resolved': customer engaged and completed — allow new conv
```

`general_inquiry` **auto-resolves on any farewell phrase** (`_is_farewell_message`, e.g. a bare
"Gracias", "Listo", "Ok"). So in a live back-and-forth the conversation resolved repeatedly, and
**every subsequent customer message spawned a brand-new conversation** instead of continuing the
existing one.

### 2. Per-conversation Telegram-footer guard
The Telegram cross-channel invite was appended "once on the very first WA reply," guarded by:

```python
# OLD — per-conversation
and not self.agent_message_ids.filtered(lambda m: m.direction == 'outbound')
```

Because each freshly-spawned conversation had **zero outbound messages of its own**, the guard
read "first reply" again → the Telegram footer was re-appended on every new conversation.

### Why the greeting also repeated
Each new conversation starts with **empty message history**. Claude, seeing no prior context,
opens with a fresh `¡Hola Raiza! 👋` greeting every time — so the customer perceived Glenda as
"restarting" the conversation over and over.

### Combined effect
```
customer msg → conv resolves (farewell) → next msg → NEW conv (empty history)
   → Claude re-greets ("¡Hola Raiza!")  → footer guard sees 0 outbound → Telegram invite re-sent
   → repeat …
```

---

## Fix (v17.0.1.59.6)

Both changes in `models/ai_agent_conversation.py`.

### Fix 1 — Reuse recently-resolved conversations
In `_get_or_create_general_inquiry_conversation()`, a `resolved` conversation whose
`last_message_date` is within a configurable window is **re-opened and reused** instead of
spawning a new one:

```python
reopen_window = int(icp.get_param('ai_agent.reopen_resolved_window_min', '30') or '30')
reopen_cutoff = fields.Datetime.now() - timedelta(minutes=reopen_window)
if existing.last_message_date and existing.last_message_date >= reopen_cutoff:
    existing.write({'state': 'active', 'last_sender': 'customer',
                    'last_message_date': fields.Datetime.now()})
    return existing
# resolved long ago → allow a genuinely fresh conversation
```

Result: the whole live exchange stays in **one** conversation, history is preserved (no
re-greeting), and a genuinely new inquiry days later still gets a clean conversation.

### Fix 2 — Per-contact (per-phone) Telegram-invite guard
The footer is now appended **at most once per phone, ever** — idempotent across however many
conversations exist:

```python
and self.phone
and not self.env['ai.agent.message'].sudo().search_count([
    ('conversation_id.phone', '=', self.phone),
    ('direction', '=', 'outbound'),
    ('body', 'ilike', 't.me/'),
])
```

---

## New System Parameter

| Key | Default | Description |
|-----|---------|-------------|
| `ai_agent.reopen_resolved_window_min` | `30` | Minutes within which a resolved `general_inquiry` conversation is re-opened and reused instead of creating a new one. |

(Existing `ai_agent.telegram_invite_enabled` still gates the footer entirely.)

---

## Deployment

Standard prod deploy (see CLAUDE.md "PROD DEPLOY MECHANISM"):

```bash
# scp the changed file to prod (back up first), then:
docker exec ueipab17 odoo -u ueipab_ai_agent -d DB_UEIPAB --stop-after-init
docker restart ueipab17
# verify installed_version == 17.0.1.59.6 via XML-RPC
```

---

## Empty-conversation investigation (RESOLVED — it was the NameError)

Initially suspected a webhook + poll-cron creation race. **It was not.** The webhook controller
(`controllers/webhook.py`) only *finds* existing `waiting`/`active` conversations — it never
creates them — so it cannot spawn empties. The mechanism is entirely the `_TD_LABEL` rollback:

1. Poll cron Phase 1 creates the conversation (committed, outside the Phase-2 savepoint).
2. Phase 2 `action_process_reply` logs the inbound msg, calls Claude, **sends the WA reply**,
   logs the outbound msg, runs receipt OCR — then `_notify_pagos_payment_receipt` raises
   `NameError`.
3. The Phase-2 savepoint rolls back → inbound + outbound rows vanish. The Phase-1 conversation
   row survives → **empty conversation**, stuck `active`.
4. ~3.5 min later it shows as `resolved` (a later poll cycle / cleanup transitions it; the blank
   chatter line is just the `state` field-tracking notification).
5. Dedup gone → next cycle re-sends → new empty conversation → repeat.

The v59.7 savepoint+swallow around the receipt block closes this for good: even if receipt
processing throws, the message log (and therefore the dedup) survives, so there is no resend and
no orphaned empty conversation.

## Orphan hardening (v17.0.1.59.8 — 2026-06-24)

Defense-in-depth so a future exception (or a worker OOM/kill) before the first message is logged
can never again leave an empty `active` conversation. Two complementary guards in
`_cron_poll_messages`:

1. **Immediate per-conversation cleanup.** Phase 1 records the IDs of conversations *created* this
   run (`newly_created_ids` = returned conv with zero messages). If that conversation's Phase-2
   processing throws, the `except` handler unlinks it when it still has no messages — the orphan
   is gone in the same poll cycle that created it.

   ```python
   if conv_id in newly_created_ids:
       orphan = self.sudo().browse(conv_id)
       if orphan.exists() and not orphan.agent_message_ids:
           orphan.unlink()
   ```

2. **Catch-all sweep.** `_sweep_empty_conversations()` runs at the end of every poll cron (under
   the same advisory lock) and removes any `active`/`waiting` `general_inquiry` conversation with
   **zero messages** whose `create_date` is older than `ai_agent.reopen_resolved_window_min`
   (default 30 min). The age gate guarantees a genuinely in-flight conversation — created seconds
   ago, about to be processed — is never touched. This catches orphans the per-conv handler can't
   reach (worker death mid-run, any path that bypasses the Phase-2 `except`).

   ```python
   orphans = self.sudo().search([
       ('skill_id.code', '=', 'general_inquiry'),
       ('state', 'in', ('active', 'waiting')),
       ('create_date', '<', cutoff),
       ('agent_message_ids', '=', False),
   ])
   orphans.unlink()
   ```

Tested on `testing`: a backdated empty conv is swept, a freshly-created one is spared. Deployed to
both envs; prod (`DB_UEIPAB`) `installed_version 17.0.1.59.8`, 0 orphans at deploy time.

## Remaining follow-ups (low priority)

1. ✅ **RESOLVED (v59.8).** Phase-1 creation outside the Phase-2 savepoint is now covered by the
   immediate cleanup + sweep above — empty orphans no longer survive a failed turn.
2. **Messages arriving on the tertiary number (+584148321963).** Logs show RAIZA's images also
   landed on the tertiary/emergency account and were correctly ignored (account guard). Worth a
   glance at why traffic reaches tertiary at all (see WA number config memory).
3. **Farewell auto-resolve is aggressive.** A bare "Gracias" mid-flow resolves the conversation.
   With the v59.6 reopen fix this is harmless (re-opens on the next message), but consider not
   auto-resolving when the last activity is only seconds old.

---

## Related

- `documentation/AI_AGENT_MODULE.md` → "Poll Cron Transaction Rollback Bug (2026-03-02)" — the
  earlier recursive-duplicate incident; same family of symptom (repeated WA sends).
- `documentation/GLENDA_TELEGRAM_CHANNEL.md` — Telegram cross-channel invite.
