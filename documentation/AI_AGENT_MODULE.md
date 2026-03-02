# AI Agent Module (ueipab_ai_agent)

**Version:** 17.0.1.15.0 | **Status:** Testing | **Installed:** 2026-02-07

## Overview

Centralized AI-powered WhatsApp agent for automated customer interactions. Combines MassivaMóvil WhatsApp API with Anthropic Claude AI through a pluggable "skills" architecture that supports multiple business processes.

## Architecture

```
Customer WhatsApp <-> MassivaMóvil API <-> ueipab_ai_agent <-> Claude AI
                                              |
                                     Skill Handlers
                                    /       |        \
                          Bounce     Bill       Billing
                         Resolution  Reminder   Support
                            |           |          |
                        mail.bounce  account.move  res.partner
                           .log
```

### Components

1. **Skills** — Pluggable handlers defining AI behavior per business process
2. **Conversations** — State-tracked WhatsApp exchanges with customers
3. **Messages** — Full message log (inbound + outbound) with AI token tracking
4. **WhatsApp Service** — Abstract model wrapping MassivaMóvil send/receive/validate APIs
5. **Claude Service** — Abstract model wrapping Anthropic Messages API
6. **Webhook + Cron** — Dual message reception (real-time webhook + 5-min polling fallback)

## Module Structure

```
addons/ueipab_ai_agent/
├── __init__.py                          # Package init + post_init_hook
├── __manifest__.py                      # Module metadata
├── models/
│   ├── ai_agent_skill.py               # Skill configuration model
│   ├── ai_agent_conversation.py         # Conversation tracking + state machine
│   ├── ai_agent_message.py             # Message log
│   ├── whatsapp_service.py             # MassivaMóvil API abstraction
│   ├── claude_service.py               # Anthropic API abstraction
│   └── mail_bounce_log.py             # Extend bounce log with AI link
├── skills/
│   ├── __init__.py                     # Skill registry + decorator
│   ├── bounce_resolution.py            # Bounce email resolution skill
│   ├── bill_reminder.py                # Invoice due date reminder skill
│   └── billing_support.py             # Balance inquiry support skill
├── controllers/
│   └── webhook.py                      # WhatsApp webhook endpoint
├── wizard/
│   ├── start_conversation_wizard.py    # Manual conversation launcher
│   └── start_conversation_wizard_view.xml
├── views/
│   ├── ai_agent_skill_views.xml
│   ├── ai_agent_conversation_views.xml
│   ├── ai_agent_message_views.xml
│   └── menus.xml                       # Menu + bounce log form extension
├── security/
│   ├── security.xml                    # Groups
│   └── ir.model.access.csv            # Access rules
└── data/
    ├── skills_data.xml                 # Default skill records
    └── cron.xml                        # Polling + timeout crons
```

## Models

### ai.agent.skill

Stores configuration for each business process (skill).

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Skill display name |
| `code` | Char | Unique identifier (e.g., `bounce_resolution`) |
| `system_prompt` | Text | Claude AI system prompt |
| `model_name` | Char | AI model (default: `claude-haiku-4-5-20251001`) |
| `max_turns` | Integer | Max customer replies before closing |
| `timeout_hours` | Integer | Hours to wait before timeout |
| `reminder_interval_hours` | Integer | Hours between reminders (default: 24) |
| `max_reminders` | Integer | Max reminders before timeout (default: 2) |
| `source_model` | Char | Linked Odoo model name |
| `greeting_template` | Text | Optional greeting template |

### ai.agent.conversation

Tracks each WhatsApp conversation with a customer.

| Field | Type | Description |
|-------|------|-------------|
| `skill_id` | Many2one | Link to skill configuration |
| `partner_id` | Many2one | Customer contact |
| `phone` | Char | WhatsApp phone number |
| `state` | Selection | draft/active/waiting/resolved/timeout/failed |
| `source_model` | Char | Origin model (generic reference) |
| `source_id` | Integer | Origin record ID |
| `agent_message_ids` | One2many | WhatsApp messages |
| `turn_count` | Integer | Computed: inbound message count |
| `resolution_summary` | Text | Summary when resolved |
| `reminder_count` | Integer | Reminders sent (resets on reply) |
| `last_reminder_date` | Datetime | When last reminder was sent |
| `verification_email_sent_date` | Datetime | When verification email was sent |
| `verification_email_recipient` | Char | Email address being verified |
| `escalation_date` | Datetime | When first escalation was triggered |
| `escalation_reason` | Text | Timestamped escalation descriptions (appended) |
| `escalation_freescout_id` | Integer | Freescout ticket number (set by bridge) |
| `escalation_notified` | Boolean | Whether support group was notified |

**State Machine:**

```
draft -> waiting (action_start: send greeting)
waiting -> active (incoming reply received, reminder_count reset)
active -> waiting (AI response sent)
active -> waiting (escalation: AI detects off-topic request, logs it, continues)
waiting -> waiting (reminder sent, reminder_count incremented)
waiting -> resolved (skill detects resolution OR email reply detected)
waiting -> timeout (no reply after all reminders exhausted)
active -> failed (max_turns reached)
failed/timeout -> waiting (action_retry)
```

**Reminder Timing (defaults):** 24h wait → reminder 1 → 24h → reminder 2 → 24h → timeout (72h total)

### ai.agent.message

| Field | Type | Description |
|-------|------|-------------|
| `conversation_id` | Many2one | Parent conversation |
| `direction` | Selection | outbound (sent) / inbound (received) |
| `body` | Text | Message content |
| `timestamp` | Datetime | Message timestamp |
| `whatsapp_message_id` | Integer | MassivaMóvil message ID |
| `ai_input_tokens` | Integer | Claude input tokens used |
| `ai_output_tokens` | Integer | Claude output tokens used |
| `attachment_url` | Char | Public URL of attachment from MassivaMóvil |
| `attachment_type` | Selection | image/document/audio/video |
| `attachment_id` | Many2one | Archived local copy (ir.attachment) |

## Skills System

Skills are plain Python classes (not Odoo models) registered via decorator:

```python
from ..skills import register_skill

@register_skill('my_skill_code')
class MySkill:
    def get_context(self, conversation): ...
    def get_system_prompt(self, conversation, context): ...
    def get_greeting(self, conversation, context): ...
    def get_reminder_message(self, conversation, context, reminder_count): ...
    def process_ai_response(self, conversation, ai_response, context): ...
    def on_resolve(self, conversation, resolution_data): ...
```

### Available Skills

| Code | Purpose | Resolution Triggers |
|------|---------|-------------------|
| `bounce_resolution` | Ask for new email when old one bounced. Includes Akdemia family email context to prevent duplicate proposals. | `RESOLVED:email@new.com`, `RESOLVED:RESTORE`, `RESOLVED:DECLINED`, `ACTION:ESCALATE:desc` (intermediate) |
| `bill_reminder` | Friendly invoice due date reminder | `RESOLVED:PAID`, `RESOLVED:EXTENSION` |
| `billing_support` | Balance inquiry and billing Q&A | `RESOLVED:DONE`, `RESOLVED:DISPUTE` |

## System Parameters

| Key | Default | Description |
|-----|---------|-------------|
| `ai_agent.dry_run` | `True` | No real API calls when True |
| `ai_agent.active_db` | (auto: current db) | Only this database processes crons. Prevents double-processing when both testing and production share the same WhatsApp account. |
| `ai_agent.whatsapp_api_secret` | (from config) | MassivaMóvil API secret |
| `ai_agent.whatsapp_account_id` | (from config) | WhatsApp account unique ID |
| `ai_agent.whatsapp_account_phone` | (from config) | Connected phone number |
| `ai_agent.whatsapp_base_url` | (from config) | API base URL |
| `ai_agent.claude_api_key` | (from config) | Anthropic API key |
| `ai_agent.claude_base_url` | (from config) | Anthropic API base URL |
| `ai_agent.claude_model` | `claude-haiku-4-5-20251001` | Default AI model |
| `ai_agent.claude_anthropic_version` | `2023-06-01` | API version header |
| `ai_agent.credits_ok` | `True` | Kill switch — `False` blocks all outbound API calls |
| `ai_agent.wa_sends_threshold` | `50` | Minimum remaining WA sends before alert/kill switch |
| `ai_agent.claude_spend_limit_usd` | `4.50` | Max cumulative USD spend before alert (90% of $5) |
| `ai_agent.claude_input_rate` | `0.000001` | $/token for Haiku 4.5 input ($1/MTok) |
| `ai_agent.claude_output_rate` | `0.000005` | $/token for Haiku 4.5 output ($5/MTok) |

## Credit Guard (v1.5.0)

Automatic monitoring of API credit levels with kill switch to prevent mid-conversation failures when credits are exhausted.

### Problem

Both external APIs have finite credits:
- **MassivaMóvil** (WhatsApp): Plan 500 sends/month, subscription-based
- **Anthropic** (Claude AI): Prepaid credit ($5 loaded), usage-based

Without monitoring, Glenda could exhaust credits mid-conversation, leaving customers hanging with no response.

### How It Works

```
Cron (every 30 min) → _cron_check_credits()
    │
    ├─ 1. Check MassivaMóvil: GET /api/get/subscription
    │     → remaining = wa_send.limit - wa_send.used
    │     → alert if remaining < threshold (default 50)
    │
    ├─ 2. Check Anthropic: aggregate ai.agent.message tokens → calculate USD
    │     → Haiku 4.5: $0.000001/input_tok + $0.000005/output_tok
    │     → alert if spend > limit (default $4.50 of $5.00)
    │
    ├─ 3. If either depleted (transition OK → NOT OK):
    │     → Set ai_agent.credits_ok = False (kill switch)
    │     → Send email alert to soporte + gustavo
    │
    └─ 4. If both OK and currently disabled (transition NOT OK → OK):
          → Set ai_agent.credits_ok = True (auto-recover)
```

### Kill Switch Enforcement

Checked at service level in every API call, blocking ALL paths (manual, webhook, cron):

- `whatsapp_service.send_message()` → raises `UserError` if `credits_ok=False`
- `claude_service.generate_response()` → raises `UserError` if `credits_ok=False`

### Email Alert

Sent only on OK → NOT OK transition (not repeated every 30 min):
- **To:** `soporte@ueipab.edu.ve`
- **CC:** `gustavo.perdomo@ueipab.edu.ve`
- **Subject:** `[UEIPAB] AI Agent — Creditos Agotados`
- **Body:** Lists which service is depleted with remaining/limit details

### Design Decisions

1. **Fail-safe:** If MassivaMóvil API errors during check, treat as depleted (block outbound rather than risk sending with no credits)
2. **Auto-recover:** When credits are replenished and next cron check passes, `credits_ok` flips back to `True` automatically
3. **One alert per transition:** Email sent only on state change, not every check cycle
4. **No schedule check:** Credit monitoring runs 24/7 (not restricted to contact hours)

### Important: Cumulative Claude Spend

Claude spend is calculated by summing ALL `ai.agent.message` tokens across ALL conversations. This is a **cumulative lifetime total**, not per-billing-cycle.

**When topping up credits:** If you add more Anthropic credit (e.g., $5 more → $10 total), you MUST increase `ai_agent.claude_spend_limit_usd` proportionally (e.g., from `4.50` to `9.50`). Otherwise the old spend still counts toward the old limit.

## Cron Jobs

### Odoo Module Crons (inside Docker)

| Cron | Interval | Active (testing) | Purpose |
|------|----------|-------------------|---------|
| AI Agent: Poll WhatsApp Messages | 5 min | Yes | Fetch new received messages (fallback to webhook) |
| AI Agent: Check Conversation Timeouts | 1 hour | **No** | Send reminders or timeout waiting conversations |
| AI Agent: Credit Guard | 30 min | Yes | Check WA + Claude credit levels, kill switch + email alert |
| AI Agent: Archive Attachments | 2 hours | Yes | Download image attachments to ir.attachment before MassivaMóvil URL expiry |

**Operational model:** Poll cron processes customer replies automatically. Timeout cron handles reminders and auto-close. Credit Guard runs continuously to monitor API credit levels. Archive cron downloads customer-sent images to local storage before MassivaMóvil URLs expire. Conversations are started manually via "Iniciar WhatsApp" button.

### System Crons (dev server /etc/cron.d/)

| Cron | Interval | Purpose |
|------|----------|---------|
| `ai_agent_escalation` | 5 min | Bridge: creates Freescout tickets + WhatsApp group notifications for escalated conversations |

## Security

| Group | Permissions |
|-------|------------|
| AI Agent User | Read-only on skills, conversations, messages |
| AI Agent Manager | Full CRUD + skill configuration |

Admin users are added to Manager group by default.

## Menu Structure

```
Contactos (existing)
├── Bounce Log (existing)
├── AI Agent
│   ├── Conversaciones
│   └── Configuracion de Skills (Manager only)
```

## Integration with Bounce Log

The module extends `mail.bounce.log` with:
- `ai_conversation_id` field (Many2one to conversation)
- `ai_conversation_state` related field (with badge widget)
- "Iniciar WhatsApp" button in form header

Button flow:
1. Click "Iniciar WhatsApp" on bounce log record
2. Wizard opens pre-filled (skill=bounce_resolution, partner, phone)
3. Click "Iniciar Conversacion"
4. Conversation created, greeting sent via WhatsApp (or logged in dry run)
5. When resolved, bounce log is updated automatically

## Webhook Endpoint

**URL:** `/ai-agent/webhook/whatsapp`
**Method:** POST (JSON)
**Auth:** Secret validation (matches `ai_agent.whatsapp_api_secret`)

Configure this URL as the callback in MassivaMóvil Dashboard > Tools > Webhooks.

## Dry Run Mode

By default, `ai_agent.dry_run = True`. In this mode:
- No WhatsApp messages are actually sent
- No Claude API calls are made
- All actions are logged to Odoo server log with `DRY_RUN:` prefix
- Conversations still transition through states normally
- Messages are recorded with placeholder content

Set `ai_agent.dry_run = False` in System Parameters to enable live mode.

## Contact Schedule

Glenda only initiates outbound WhatsApp messages during allowed hours (Venezuela, GMT-4):

| Day | Start | End |
|-----|-------|-----|
| Monday - Friday | 06:30 | 20:30 |
| Saturday - Sunday | 09:30 | 19:00 |
| Public Holidays | 09:30 | 19:00 |

**Holiday support (v1.15.0):** Venezuelan public holidays automatically use the weekend schedule (09:30-19:00) even when they fall on weekdays. Holidays are stored as comma-separated `MM-DD` values in `ai_agent.holidays` and editable from the Dashboard Configuracion tab.

**Behavior:**
- **Cron-initiated outbound** (reminders, timeouts, poll processing): Blocked outside schedule. Crons skip silently and retry next run.
- **Customer-initiated replies** (webhook): Glenda responds anytime. If the customer is messaging, they're awake.
- **Edge case**: Glenda sends reminder at 20:20, customer replies at 20:45 (after cutoff). Webhook processes the reply immediately -- conversation continues. But if the customer doesn't reply and the next cron fires at 21:00, it skips until morning.

**Configurable via System Parameters:**

| Key | Default | Description |
|-----|---------|-------------|
| `ai_agent.schedule_weekday_start` | `06:30` | Weekday start (HH:MM, VET) |
| `ai_agent.schedule_weekday_end` | `20:30` | Weekday end (HH:MM, VET) |
| `ai_agent.schedule_weekend_start` | `09:30` | Weekend start (HH:MM, VET) |
| `ai_agent.schedule_weekend_end` | `19:00` | Weekend end (HH:MM, VET) |
| `ai_agent.holidays` | *(empty)* | Public holidays as MM-DD CSV (use weekend schedule) |

## WhatsApp Reminders

When a customer doesn't reply, the system sends periodic reminders before giving up:

1. Initial greeting sent → wait `reminder_interval_hours` (default: 24h)
2. No reply → send reminder 1 (gentle follow-up) → wait again
3. No reply → send reminder 2 (final notice) → wait again
4. No reply → timeout (conversation closed)

Each skill provides two reminder tones via `get_reminder_message()`:
- **First reminder** (count=0): gentle follow-up ("Le escribimos nuevamente...")
- **Last reminder** (count=1+): final notice ("Le contactamos por ultima vez...")

When a customer replies at any point, `reminder_count` resets to 0.

## Freescout Email Verification Detection

Bridge script that detects when customers reply to verification emails in Freescout and auto-resolves conversations.

**Script:** `scripts/ai_agent_email_checker.py`

**Flow:**
1. Query Odoo for conversations with `verification_email_sent_date` set + state=`waiting`
2. Query Freescout threads WHERE `from` LIKE `%recipient_email%` AND `type=1` (customer reply) AND `created_at > verification_date`
3. For matches → call `action_resolve_via_email()` via XML-RPC
4. Resolution sends farewell WhatsApp + triggers bounce log restore
5. Post-process Freescout conversation (see below)

**Freescout Post-Processing (per resolved conversation):**
- **Subject prefix:** `[RESUELTO-AI]` prepended to conversation subject
- **Internal note:** HTML note with links to Odoo contact, bounce log, and AI conversation
- **Status:** Closed (3) — Odoo is the single resolution workspace
- Skips conversations already prefixed with `[LIMPIADO]`, `[REVISION]`, `[NO ENCONTRADO]`, or `[RESUELTO-AI]`

**Execution:**
```bash
# Manual
python3 /opt/odoo-dev/scripts/ai_agent_email_checker.py

# Cron (every 15 minutes)
*/15 * * * * python3 /opt/odoo-dev/scripts/ai_agent_email_checker.py >> /var/log/ai_agent_email_checker.log 2>&1
```

**Configuration:** Same as `daily_bounce_processor.py` (Odoo XML-RPC + Freescout MySQL credentials via pymysql). `DRY_RUN=True` by default.

## Escalation (v1.4.0)

When a customer asks Glenda about something outside bounce resolution (constancias, invoices, data changes, etc.), the system escalates gracefully without ending the conversation.

### Flow

```
Customer: "Necesito una constancia de estudios"
    │
    ├─ 1. Claude includes ACTION:ESCALATE:Solicita constancia in response
    │     (visible text tells customer "he registrado su solicitud")
    │
    ├─ 2. Odoo module (immediate, during action_process_reply):
    │     - Parse marker, extract description
    │     - Save escalation_date + escalation_reason on conversation
    │     - Send visible response to customer via WhatsApp
    │     - Conversation stays in 'waiting' (Glenda continues bounce resolution)
    │
    └─ 3. Bridge script (cron every 5 min on dev server):
          - Query Odoo for conversations with escalation_date but no freescout ticket
          - Create Freescout conversation via direct MySQL
          - Send WhatsApp to "ueipab soporte" group with ticket details
          - Update Odoo conversation with Freescout ticket number
```

### Marker Format

```
ACTION:ESCALATE:description text here (free-form, single line, captured to end of line)
```

**Key behavior:** Intermediate action — conversation stays in `waiting`, Glenda continues bounce resolution. Multiple escalations in the same conversation are appended with timestamps.

### Bridge Script

**Script:** `scripts/ai_agent_escalation_bridge.py`

| Setting | Default | Description |
|---------|---------|-------------|
| `DRY_RUN` | `True` | No real API calls when True |
| `TARGET_ENV` | `testing` | Target Odoo environment |
| `WA_GROUP_ID` | `584142337463-1586178983@g.us` | "ueipab soporte" WhatsApp group |

**Execution:**
```bash
# Manual dry run
python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py

# Cron (every 5 minutes)
*/5 * * * * python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py >> /var/log/ai_agent_escalation_bridge.log 2>&1
```

**WhatsApp group message format:**
```
📋 *Nuevo Ticket de Soporte #NNN*
Cliente: PARTNER_NAME
Telefono: +58XXXXXXXXXX
Motivo: escalation description
🔗 Freescout: https://soporte.ueipab.edu.ve/conversation/NNN
🔗 Odoo: ODOO_URL/web#id=XXX&model=ai.agent.conversation
```

### Bounce Log Resolution Paths (5 total)

| Path | Trigger | Action |
|------|---------|--------|
| A | Glenda WhatsApp → customer gives new email | `RESOLVED:new@email.com` |
| B | Email verification checker → customer replies to verification email | `RESOLVED:RESTORE` via bridge |
| C | Akdemia sync → tech support updated email in Akdemia | Auto-resolve via script |
| D | Manual → staff clicks "Restaurar" or "Aplicar Nuevo" in Odoo | Direct action |
| E | Escalation → customer asks off-topic question | `ACTION:ESCALATE:desc` (intermediate, Freescout ticket created) |
| F | Akdemia Auto-Resolve → valid alternative email exists for same cedula | Auto-resolve from Akdemia data |

## Production Deployment Architecture

### Split-Server Design

The AI Agent system spans two servers. This is by design.

```
Dev Server (Freescout host)                   Production Server (10.124.0.3)
├── Freescout MySQL (localhost)                ├── Odoo (Docker: ueipab17)
├── Scripts (crontab)                          │   ├── ueipab_ai_agent module
│   ├── daily_bounce_processor.py              │   ├── Crons (poll + timeouts)
│   └── ai_agent_email_checker.py              │   ├── Webhook endpoint
│       ├── reads Freescout (localhost)         │   ├── WhatsApp API → MassivaMóvil
│       └── calls Odoo ── XML-RPC ────────────→│   └── Claude API → Anthropic
│       └── writes Freescout (post-processing) │
└── Config files (/opt/odoo-dev/config/)       └── Config: /home/vision/ueipab17/config/
```

**Key rule:** Scripts ALWAYS run on the dev server (where Freescout is hosted). They reach production Odoo via XML-RPC (`TARGET_ENV=production`). They CANNOT run on the production server because Freescout MySQL is not accessible from there.

### Config File Loading

The `_load_api_configs` post-init hook searches for config files in order:

1. `AI_AGENT_CONFIG_DIR` environment variable (if set)
2. `/opt/odoo-dev/config/` (dev server)
3. `/home/vision/ueipab17/config/` (production server)

For production deployment, copy config files to `/home/vision/ueipab17/config/` on the production server before installing/upgrading the module.

### Environment Safeguard (`ai_agent.active_db`)

Both testing and production share the same WhatsApp account (+584148321963). To prevent double-processing (duplicate reminders, polls racing for messages):

- `ai_agent.active_db` system parameter stores the database name authorized to run crons
- Auto-set to current database on first install
- All three module crons (`_cron_poll_messages`, `_cron_check_timeouts`, `_cron_check_credits`) check this before processing
- If mismatch → skip with warning log, zero processing

**When going live in production:**
1. Set `ai_agent.active_db = 'DB_UEIPAB'` on production Odoo
2. Set `ai_agent.active_db = ''` (empty) or leave as `'testing'` on testing Odoo — crons will self-skip
3. Set `ai_agent.dry_run = 'False'` on production only
4. Update scripts: `TARGET_ENV=production` in crontab

**To return to testing:** reverse the `active_db` values.

### Production Migration Checklist

> **Full gap analysis and 3-phase migration sequence:** See [Glenda Overview — Production Readiness Review](GLENDA_AI_AGENT_OVERVIEW.md#production-readiness-review-2026-02-14)
>
> Covers 11 identified gaps: modules, config files, webhook, cron flags, Akdemia paths, escalation/email-checker DRY status, Freescout API, Credit Guard calibration, initial bounce load, testing lockout, and data drift.

## Known Issues

### Poll Cron Transaction Rollback Bug (2026-03-02)

**Status:** Open — Identified during HR data collection testing with Rafael Perez and Lorena Reyes.

**Symptom:** Customer receives recursive/duplicate WhatsApp messages from Glenda with the same content. Inbound messages are NOT logged in Odoo despite being present in the MassivaMóvil received API.

**Root Cause:** `_cron_poll_messages()` (line 829-853) processes all conversation batches in a single transaction with **no error isolation**. If `action_process_reply()` raises an exception for ANY conversation:
1. The entire cron transaction rolls back (all Odoo records lost)
2. But Claude API calls and WhatsApp sends already executed (irreversible external calls)
3. Next cron cycle: dedup check fails (records were rolled back) → same messages re-processed → recursive

**Evidence (Conv #30 — Rafael Perez):** 12 inbound WA messages in MassivaMóvil API (IDs 205945-205973), zero logged in Odoo. Poll cron running every 1 minute, conversation in `waiting` state for ~2 hours.

**Secondary Issue — Duplicate Conversations (Conv #31/#32 — Lorena Reyes):** Two active conversations for the same phone. Dedup check is per-conversation (`conversation_id = X`), so the same WA message (#205917) was processed by both conversations → double Claude calls, double WA sends.

**Recommended Fixes:**
1. **Critical:** Wrap each conversation processing in `try/except` with `cr.savepoint()` for error isolation
2. **Important:** Make WA message dedup global (not per-conversation) to prevent cross-conversation duplicates
3. **Important:** Add wizard validation to prevent creating duplicate active conversations for the same phone

---

## Cost Estimates

Using Claude Haiku 4.5 at $1/$5 per MTok:
- Average bounce resolution: ~3 messages, ~$0.005 per conversation
- $5 credit covers ~1,000 conversations
- WhatsApp: limited by MassivaMóvil Plan 500 (500 sends/month)
- Credit Guard alerts at 90% spend ($4.50) or <50 WA sends remaining
