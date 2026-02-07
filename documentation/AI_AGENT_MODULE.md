# AI Agent Module (ueipab_ai_agent)

**Version:** 17.0.1.2.0 | **Status:** Testing | **Installed:** 2026-02-07

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

**State Machine:**

```
draft -> waiting (action_start: send greeting)
waiting -> active (incoming reply received, reminder_count reset)
active -> waiting (AI response sent)
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
| `bounce_resolution` | Ask for new email when old one bounced | `RESOLVED:email@new.com`, `RESOLVED:RESTORE`, `RESOLVED:DECLINED` |
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

## Cron Jobs

| Cron | Interval | Purpose |
|------|----------|---------|
| AI Agent: Poll WhatsApp Messages | 5 min | Fetch new received messages (fallback to webhook) |
| AI Agent: Check Conversation Timeouts | 1 hour | Send reminders or timeout waiting conversations |

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
- Both `_cron_poll_messages` and `_cron_check_timeouts` check this before processing
- If mismatch → skip with warning log, zero processing

**When going live in production:**
1. Set `ai_agent.active_db = 'DB_UEIPAB'` on production Odoo
2. Set `ai_agent.active_db = ''` (empty) or leave as `'testing'` on testing Odoo — crons will self-skip
3. Set `ai_agent.dry_run = 'False'` on production only
4. Update scripts: `TARGET_ENV=production` in crontab

**To return to testing:** reverse the `active_db` values.

### Production Migration Checklist (DO NOT EXECUTE - reference only)

```
Pre-deployment:
[ ] Copy config files to production: /home/vision/ueipab17/config/
    - whatsapp_massiva.json
    - anthropic_api.json
[ ] Ensure ueipab_bounce_log module is installed on production
[ ] Sync ueipab_ai_agent module to production addons path

Module installation:
[ ] Install/upgrade ueipab_ai_agent on production Odoo
[ ] Verify ir.config_parameter values loaded (WhatsApp + Claude keys)
[ ] Set ai_agent.dry_run = 'True' (keep dry until verified)
[ ] Set ai_agent.active_db = 'DB_UEIPAB'

Webhook setup:
[ ] Configure MassivaMóvil webhook: https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp

Testing environment lockout:
[ ] Set ai_agent.active_db = '' on testing Odoo (disable crons)
[ ] Verify testing crons log "Skipping cron processing" warning

Script deployment:
[ ] Update ai_agent_email_checker.py: TARGET_ENV='production'
[ ] Update daily_bounce_processor.py: TARGET_ENV='production' (if not already)
[ ] Add crontab entries on dev server

Go live:
[ ] Set ai_agent.dry_run = 'False' on production
[ ] Monitor first conversations end-to-end
```

## Cost Estimates

Using Claude Haiku 4.5 at $1/$5 per MTok:
- Average bounce resolution: ~3 messages, ~$0.005 per conversation
- $5 credit covers ~1,000 conversations
- WhatsApp: limited by MassivaMóvil plan (currently 67 sends remaining on Plan 500)
