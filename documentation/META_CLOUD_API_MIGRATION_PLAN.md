# WhatsApp Migration: MassivaMóvil → Meta Cloud API

**Status:** Planning | **Created:** 2026-05-23 | **Priority:** Medium

## Background

Current setup uses MassivaMóvil as a Business Solution Provider (BSP) reselling access to
Meta's WhatsApp Business Platform. As of 2026-05-22, the primary number (+584148321989) is
banned at the WA delivery level (Massiva support ticket open). Glenda WA is paused (`dry_run=True`);
Telegram is the active channel.

This document outlines what a direct Meta Cloud API migration would look like — cutting out
MassivaMóvil and connecting Odoo directly to Meta's infrastructure.

---

## Why Migrate

| Pain point (MassivaMóvil) | Meta Cloud API |
|--------------------------|----------------|
| Monthly subscription regardless of volume | Pay-per-conversation (~$0.06/conv after 1k free) |
| Primary number banned, slow support response | Number managed directly with Meta |
| API reliability depends on Massiva's uptime | Meta's own infrastructure |
| Limited visibility into delivery failures | Full delivery webhooks from Meta |
| Undocumented API changes | Stable versioned API (`/v20.0/`) with changelog |

---

## Key Concept: No Bot Accounts on WhatsApp

Unlike Telegram (`@GlendaUeipabBot` = a token-based bot with no phone number), **every
WhatsApp Business API connection requires a real phone number**. That number is exclusively
consumed by the API — it cannot simultaneously run a regular WhatsApp app.

The "bot" behaviour is implemented server-side (Odoo + Claude). From the parent's perspective
they are messaging a verified business number.

---

## Architecture: Current vs Target

```
CURRENT
Parent → WhatsApp → MassivaMóvil API → Odoo webhook / 5-min poll cron
                                              ↓
                                        ai.agent.conversation
                                              ↓
                                        Claude (Haiku 4.5)
                                              ↓
                                   MassivaMóvil /api/send/whatsapp

TARGET
Parent → WhatsApp → Meta Cloud API → Odoo webhook (real-time, no poll)
                                           ↓
                                     ai.agent.conversation   ← no change
                                           ↓
                                     Claude (Haiku 4.5)      ← no change
                                           ↓
                          Meta Cloud API graph.facebook.com/messages
```

Only two Odoo files change: `whatsapp_service.py` (send) and the webhook controller.
All skills, conversation logic, and Claude integration stay identical.

---

## Prerequisites

### 1. Meta Business Manager account
- URL: `business.facebook.com`
- Linked to a personal Facebook account (super admin — use a permanent school account)
- Business email: `gustavo.perdomo@ueipab.edu.ve`

### 2. Business Verification
Required before Meta approves WhatsApp access.

Documents accepted (pick one):
- **RIF** (Registro de Información Fiscal) — recommended, Venezuela's standard business ID
- Utility bill in school's name (last 3 months)
- Bank statement in school's name

Timeline: 1–5 business days. Venezuela is not a restricted country — no extra hurdles.

### 3. Dedicated Phone Number
- New Venezuelan SIM: +58414 or +58424 prefix
- **Must never have had WhatsApp installed** — if it did, delete WA account, wait 30 days
- SIM only needs to receive one OTP SMS/call during registration; no data plan needed after
- Suggested label: "Glenda WA API" — document the number in `config/production.json`

### 4. International Payment Method
- Visa/Mastercard with international purchases enabled
- Meta bills in USD monthly (credit card or prepaid balance)
- A US-issued card or any card that can charge foreign merchants works

---

## Registration Steps

### Step 1 — Create Meta Business Manager
```
business.facebook.com → Create Account
  Business name: Instituto Privado Colegio Andrés Bello
  Admin email:   gustavo.perdomo@ueipab.edu.ve
```

### Step 2 — Verify Business
```
Business Manager → Settings → Business Info → Start Verification
  Upload: RIF document
  Match:  business name + address must match document exactly
```

### Step 3 — Create WhatsApp Business Account (WABA)
```
Business Manager → Accounts → WhatsApp Accounts → Add
  Name:     Colegio Andrés Bello
  Timezone: America/Caracas
  Currency: USD
```

### Step 4 — Create Meta Developer App
```
developers.facebook.com → Create App
  Type:     Business
  Name:     Glenda WA Bot
  Business: UEIPAB (your verified Business Manager)

App Dashboard → Add Product → WhatsApp → Set Up
  → Links app to WABA, reveals phone_number_id
```

### Step 5 — Register Phone Number
```
WABA → Phone Numbers → Add Phone Number
  Number:       +584XXXXXXXXX (new dedicated SIM)
  Display name: Colegio Andrés Bello   ← what parents see
  Category:     Education
  OTP method:   SMS
```
Display name goes through Meta review (usually same day).

### Step 6 — Create System User + Permanent Token
```
Business Manager → System Users → Add System User
  Name:  glenda-api
  Role:  Admin

System User → Assign Assets → WhatsApp Accounts → UEIPAB WABA → Full Control

System User → Generate Token
  App:         Glenda WA Bot
  Permissions: whatsapp_business_messaging, whatsapp_business_management
  Expiry:      Never   ← critical — regular user tokens expire in 60 days
```
Store the token in `config/whatsapp_meta.json` (same pattern as `whatsapp_massiva.json`).

### Step 7 — Configure Webhook
```
App Dashboard → WhatsApp → Configuration → Webhook
  Callback URL:  https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp-meta
  Verify token:  <choose a secret string, store in config>
  Subscriptions: messages   ← the only field needed
```
Meta sends a GET challenge to verify the endpoint before activating.

### Step 8 — Add Payment Method
```
Business Manager → Billing → Payment Methods → Add Card
```
First 1,000 user-initiated conversations/month are free. Billing starts after that.

---

## Pricing Estimate

| Scenario | Conversations/month | Cost/month |
|----------|--------------------:|----------:|
| Free tier | ≤ 1,000 | $0.00 |
| All 225 families active | ~225 | $0.00 (within free tier) |
| 1,500 conversations | 1,500 | ~$31 (500 × $0.0623) |
| MassivaMóvil current | fixed subscription | higher than above |

Venezuela falls in Meta's **Latin America pricing tier**: ~$0.0623 per user-initiated
conversation (24-hour session window). Business-initiated (templates) are priced separately,
slightly higher (~$0.0857).

---

## Conversation Window Rules (same as current)

- **User-initiated:** parent messages first → 24-hour free-form window opens → Glenda replies freely
- **Business-initiated:** Glenda messages first → requires a pre-approved **Message Template**
- After 24h of silence, the window closes → next outbound must use a template

This is identical to the current MassivaMóvil/WhatsApp behaviour. No workflow changes needed.

---

## Message Templates Needed

These replace the current MassivaMóvil template system. Submit during setup; approval takes 1–24h.

### invoice_reminder_es
```
Category: UTILITY
Language: es (Spanish)

Hola {{1}}, te recordamos que tienes un saldo pendiente de *${{2}}* 
en el Colegio Andrés Bello. Para consultas o para registrar un pago, 
escríbenos aquí mismo.
```
Variables: `{{1}}` = parent first name, `{{2}}` = balance amount

### absence_notification_es
```
Category: UTILITY
Language: es

Hola {{1}}, recibimos la notificación de ausencia de {{2}} ({{3}}). 
Nuestro equipo de coordinación ya fue notificado. Ante cualquier duda escríbenos.
```
Variables: `{{1}}` = parent name, `{{2}}` = student name, `{{3}}` = grade

### payslip_reminder_es (employee-facing)
```
Category: UTILITY
Language: es

Hola {{1}}, tienes un comprobante de pago pendiente de confirmación 
en el portal del Colegio Andrés Bello. Por favor revísalo a la brevedad.
```

---

## Code Changes Required

### New file: `config/whatsapp_meta.json`
```json
{
  "phone_number_id": "1234567890",
  "waba_id": "9876543210",
  "access_token": "EAAxxxxx...",
  "verify_token": "ueipab_meta_verify_2026",
  "api_version": "v20.0",
  "base_url": "https://graph.facebook.com"
}
```
Loaded into `ir.config_parameter` on startup — same pattern as `whatsapp_massiva.json`.

### Modified: `models/whatsapp_service.py`
Replace MassivaMóvil HTTP calls with Meta Graph API calls.

**Send message (current vs target):**
```python
# CURRENT — MassivaMóvil
POST https://whatsapp.massivamovil.com/api/send/whatsapp
data: {secret, account, recipient, type, message}

# TARGET — Meta Cloud API
POST https://graph.facebook.com/v20.0/{phone_number_id}/messages
headers: {Authorization: Bearer {token}, Content-Type: application/json}
json: {
  "messaging_product": "whatsapp",
  "to": "+58414XXXXXXX",
  "type": "text",
  "text": {"body": "message text", "preview_url": false}
}
```

**Receive messages (current vs target):**
```python
# CURRENT — polling every 5 min
GET https://whatsapp.massivamovil.com/api/get/wa.received

# TARGET — real-time webhook POST to /ai-agent/webhook/whatsapp-meta
# Meta pushes each message instantly — no poll cron needed
```

**Send template (business-initiated):**
```python
POST .../messages
json: {
  "messaging_product": "whatsapp",
  "to": "+58414XXXXXXX",
  "type": "template",
  "template": {
    "name": "invoice_reminder_es",
    "language": {"code": "es"},
    "components": [{
      "type": "body",
      "parameters": [
        {"type": "text", "text": "María"},
        {"type": "text", "text": "185.00"}
      ]
    }]
  }
}
```

### New controller: `controllers/webhook_meta.py`
Handles Meta's two request types:

```python
# GET — webhook verification challenge (one-time during setup)
# POST — incoming messages / delivery status updates

@http.route('/ai-agent/webhook/whatsapp-meta', type='http', auth='public',
            methods=['GET', 'POST'], csrf=False)
def whatsapp_meta_webhook(self, **kwargs):
    if request.httprequest.method == 'GET':
        # Meta challenge verification
        hub_mode      = request.params.get('hub.mode')
        hub_challenge = request.params.get('hub.challenge')
        hub_verify    = request.params.get('hub.verify_token')
        if hub_mode == 'subscribe' and hub_verify == VERIFY_TOKEN:
            return hub_challenge
        return Response(status=403)

    # POST — incoming message
    data = request.get_json_data()
    # parse entry → changes → value → messages[0]
    # delegate to ai.agent.conversation._cron_poll_messages equivalent
```

Meta's webhook payload structure differs from MassivaMóvil's but the same
`_handle_inbound_message()` logic applies after parsing.

### Removed: poll cron
The 5-minute `_cron_poll_messages` WA cron becomes unnecessary — Meta pushes messages
in real-time via webhook (same as Telegram today). The cron entry in `data/cron.xml`
can be disabled.

### Unchanged
- `ai_agent_conversation.py` — all skill logic, Claude calls, conversation state
- `ai_agent_claude.py` — Claude service
- `ai_agent_telegram.py` — Telegram channel unaffected
- All skill handlers (`general_inquiry.py`, `billing_support.py`, etc.)
- All Odoo models, views, reports

---

## Migration Cutover Plan

### Phase 1 — Setup (no downtime, ~1 week)
1. Complete Meta Business Manager registration
2. Verify UEIPAB business
3. Register new dedicated Venezuelan number
4. Create app, system user, permanent token
5. Store credentials in `config/whatsapp_meta.json`

### Phase 2 — Development (parallel, ~2–3 days dev)
1. Implement `whatsapp_service.py` Meta adapter
2. Implement `webhook_meta.py` controller
3. Test in `testing` db with real Meta sandbox number
4. Test template sends and inbound webhook

### Phase 3 — Cutover (zero downtime)
1. Deploy new code to production
2. Register webhook URL with Meta app
3. Set `ai_agent.dry_run=False` in production
4. Monitor first 24h of real conversations
5. Decommission MassivaMóvil subscription once stable

### Rollback
If Meta API has issues post-cutover: set `ai_agent.dry_run=True` (WA off, Telegram stays active).
MassivaMóvil credentials remain in config as fallback during transition period.

---

## Config Parameters (new keys)

| Key | Value | Notes |
|-----|-------|-------|
| `ai_agent.wa_provider` | `meta` | New: `massiva` or `meta` |
| `ai_agent.meta_phone_number_id` | `{id}` | From app dashboard |
| `ai_agent.meta_access_token` | `EAAxxxx` | System user permanent token |
| `ai_agent.meta_verify_token` | `{secret}` | Webhook verification |
| `ai_agent.meta_api_version` | `v20.0` | Upgrade annually |

Existing `ai_agent.whatsapp_*` params for MassivaMóvil remain until decommission.

---

## Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Business verification delayed | Medium | Start early; have RIF ready; use BM live chat support |
| Display name rejected by Meta | Low | Use exact legal school name; avoid marketing language |
| New number blocked by parents (unknown sender) | Medium | Send intro template before going live; announce via email |
| Meta API downtime | Very low | Telegram remains active as backup channel (proven 2026-05-22) |
| Template rejection | Low | Keep templates factual/utility-focused; avoid promotional language |

---

## Decision: When to Start

| Trigger | Recommendation |
|---------|---------------|
| MassivaMóvil resolves primary ban | Continue on MassivaMóvil temporarily; start Meta Phase 1 in parallel |
| MassivaMóvil ban unresolved > 2 weeks | Prioritise Meta migration; request number release from Massiva |
| MassivaMóvil announces price increase | Accelerate migration |
| Backup number (+584248944898) also fails | Emergency: start Meta registration immediately |

---

## References

- [Meta Cloud API docs](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Message Templates guide](https://developers.facebook.com/docs/whatsapp/message-templates)
- [Webhook setup](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks)
- [Pricing by region](https://developers.facebook.com/docs/whatsapp/pricing)
- Current AI Agent module: [AI_AGENT_MODULE.md](AI_AGENT_MODULE.md)
- Current WA config: `config/whatsapp_massiva.json` (gitignored)
