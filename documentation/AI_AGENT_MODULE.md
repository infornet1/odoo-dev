# AI Agent Module (ueipab_ai_agent)

**Version:** 17.0.1.0.0 | **Status:** Testing | **Installed:** 2026-02-07

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

**State Machine:**

```
draft -> waiting (action_start: send greeting)
waiting -> active (incoming reply received)
active -> waiting (AI response sent)
waiting -> resolved (skill detects resolution)
waiting -> timeout (no reply after timeout_hours)
active -> failed (max_turns reached)
failed/timeout -> waiting (action_retry)
```

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
| AI Agent: Check Conversation Timeouts | 1 hour | Mark waiting conversations as timeout |

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

## Cost Estimates

Using Claude Haiku 4.5 at $1/$5 per MTok:
- Average bounce resolution: ~3 messages, ~$0.005 per conversation
- $5 credit covers ~1,000 conversations
- WhatsApp: limited by MassivaMóvil plan (currently 67 sends remaining on Plan 500)
