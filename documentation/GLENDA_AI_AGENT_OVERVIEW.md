# Glenda — AI Agent Overview

**Version:** 17.0.1.13.0 | **Status:** Testing (Live with real customers) | **Date:** 2026-02-14

## What Is Glenda

Glenda is a WhatsApp AI agent (powered by Claude Haiku 4.5) that contacts parents whose emails bounced, resolves the issue via conversation, and triggers automated post-processing across 4 external systems (Odoo, Freescout, Google Sheets, Akdemia).

She operates as "Glenda, asistente de Colegio Andres Bello" — a warm, professional Venezuelan Spanish-speaking assistant.

**Cost:** ~$0.005 per conversation (~1,000 conversations per $5 credit).

---

## Conversation Flow

1. **Initiation** — Operator clicks "Iniciar WhatsApp" on a bounce log record. Glenda sends a personalized greeting in Venezuelan Spanish.
2. **Negotiation** — She explains the email problem, asks for an alternative, handles objections, stays on-topic.
3. **Resolution** — One of 6 possible outcomes (see Resolution Paths below).
4. **Post-processing** — Automated bridge scripts update Freescout, Google Sheets, and flag Akdemia changes.

### Contact Schedule

Glenda only initiates contact during allowed hours (VET, GMT-4):

| Day | Hours |
|-----|-------|
| Weekdays | 06:30 - 20:30 |
| Weekends | 09:30 - 19:00 |

Customer-initiated replies (webhook) are processed anytime.

---

## What Glenda Knows (Context Awareness)

| Area | What She Has Access To | Since |
|------|------------------------|-------|
| **Contact identity** | Name, bounced email, bounce reason, remaining active emails | v1.0.0 |
| **Multi-email awareness** | Adjusts approach if contact has other working emails vs. no emails at all | v1.0.0 |
| **Family context** | All Akdemia-registered parents for this family — names, cedulas, emails, role (Representante/Representante.1). Warns if customer proposes an email already used by another parent | v1.12.0 |
| **Message batching** | Reads ALL customer messages before responding (customers send multiple short WhatsApp messages in rapid succession) | v1.11.0 |
| **Image/screenshot support** | Can see images customers send (screenshots, photos). Uses Claude vision to interpret content. Images archived locally before MassivaMóvil URL expiry | v1.13.0 |
| **Verification email** | Can trigger a real verification email to any address and wait for customer confirmation | v1.8.0 |

---

## Resolution Paths (6 Total)

| Path | Trigger | What Happens | Marker |
|------|---------|--------------|--------|
| **A — New Email** | Customer provides a new email via WhatsApp | Email applied to Odoo contact + mailing contacts | `RESOLVED:nuevo@email.com` |
| **B — Email Verification** | Customer says old email works now (freed space, fixed it) | Verification email sent → customer confirms reception → email restored | `ACTION:VERIFY_EMAIL` → `RESOLVED:RESTORE` |
| **C — Akdemia Sync** | Tech support updated email in Akdemia platform (detected by daily scraper) | Auto-resolved without WhatsApp contact | Script: `akdemia_email_sync.py` |
| **D — Manual** | Staff clicks "Restaurar" or "Aplicar Nuevo" directly in Odoo | Bounce log resolved via UI buttons | Odoo action |
| **E — Escalation** | Customer asks about something off-topic (constancias, invoices, data changes) | Freescout ticket created + WhatsApp group alert. Conversation **continues** (intermediate action) | `ACTION:ESCALATE:description` |
| **F — Akdemia Auto-Resolve** | Bounced email not in Akdemia but a valid alternative exists for the same cedula | Auto-resolved from Akdemia data, no WhatsApp needed | Resolution Bridge Phase 2c |

### Additional Actions (Non-Resolution)

| Action | Trigger | What Happens | Marker |
|--------|---------|--------------|--------|
| **Alternative Phone** | Family member answers, provides different phone for the real contact | Phone saved on conversation, pre-fills wizard on re-trigger | `ACTION:ALTERNATIVE_PHONE:04XXXXXXXXX` |
| **Remove Only** | Contact has other working emails, doesn't want to add another | Bounced email removed, remaining emails kept | `RESOLVED:REMOVE_ONLY` |
| **Declined** | Customer refuses to provide alternative email | Logged, conversation closed, state stays `contacted` | `RESOLVED:DECLINED` |

---

## Automated Infrastructure (10 Processes)

### Odoo Crons (Inside the Module)

| Cron | Interval | Purpose |
|------|----------|---------|
| **Poll WhatsApp Messages** | 5 min | Picks up customer WhatsApp replies from MassivaMóvil API |
| **Check Conversation Timeouts** | Active | 24h gentle follow-up, 48h final notice, 72h auto-close |
| **Credit Guard** | 30 min | Monitors WA sends + Claude spend, kill switch if depleted |

### System Crons (Scripts on Dev Server)

| Cron | Interval | Script | Purpose |
|------|----------|--------|---------|
| **Escalation Bridge** | 5 min | `ai_agent_escalation_bridge.py` | Creates Freescout tickets + WA group alerts for off-topic requests |
| **Resolution Bridge** | 5 min | `ai_agent_resolution_bridge.py` | Post-processes resolved BLs → Freescout close/assign, Sheets update, DSN cleanup, Akdemia check, family context |
| **Email Checker** | 15 min | `ai_agent_email_checker.py` | Detects when customer replies to verification email in Freescout |
| **WA Health Monitor** | 15 min | `ai_agent_wa_health_monitor.py` | Detects SPAM flagging, auto-switches to backup WhatsApp number |
| **Bounce Processor** | Daily 05:00 | `daily_bounce_processor.py` | Detects new bounces from Freescout, creates bounce logs in Odoo |
| **Akdemia Pipeline** | Daily 06:00 | `customer_matching_daily.py` | Scrapes fresh parent data from Akdemia, detects email changes, auto-resolves matches |
| **Akdemia Email Sync** | (part of pipeline) | `akdemia_email_sync.py` | Compares Akdemia XLS with bounce logs, auto-resolves where emails changed |

---

## Systems Glenda Touches

| System | How | What Changes |
|--------|-----|--------------|
| **Odoo** (res.partner) | Direct (module) | Bounced email removed, new email added, chatter audit trail |
| **Odoo** (mailing.contact) | Direct (module) | Email updated across all mailing lists (Toda la comunidad, Grupo1) |
| **Odoo** (mail.bounce.log) | Direct (module) | State transitions, resolution data, family context JSON |
| **Freescout** | MySQL (bridge script) | Conversation subject prefix `[RESUELTO-AI]`, internal notes, close/assign, DSN customer reassignment |
| **Google Sheets** | API (bridge script) | Customers tab: remove bounced email from column J |
| **WhatsApp** | MassivaMóvil API | Send/receive messages, group alerts |
| **Akdemia** | Read-only (scraper) | Data source for family context, email change detection, auto-resolve |

---

## Safety Mechanisms

| Mechanism | Description |
|-----------|-------------|
| **dry_run mode** | Default on. Read-only toggle in dashboard with confirmation buttons to prevent accidental activation |
| **active_db safeguard** | Only the database matching `ai_agent.active_db` parameter processes crons. Prevents double-processing when testing and production share the same WhatsApp account |
| **Credit Guard** | Auto-blocks outbound API calls when WA sends or Claude spend approach limits. Auto-recovers on next passing check. API errors = treat as depleted (fail-safe) |
| **Contact schedule** | Cron-initiated outbound blocked outside business hours |
| **Anti-spam interval** | Minimum 120-140 seconds between WhatsApp sends (MassivaMóvil recommended) |
| **WA health monitor** | Dual-layer detection (API validation + Freescout email scan) with automatic failover to backup number |
| **Kill switch** | `ai_agent.credits_ok` parameter — when False, all outbound WhatsApp + Claude calls are blocked |
| **Deduplication** | `whatsapp_message_id` prevents processing the same incoming message twice |
| **Known-bounced cross-check** | Akdemia auto-resolve skips emails that are themselves in the bounced list |

---

## Results (as of 2026-02-14)

| Metric | Value |
|--------|-------|
| Total bounce logs | 37 |
| Resolved | 22 (59%) |
| Akdemia pending | 4 (11%) |
| Active conversations | 5 (14%) |
| Pending (not contacted) | 5 (14%) |
| Orphans (no partner match) | 8 |
| Auto-resolved via Akdemia (no WhatsApp) | ~17 |
| First full live resolution | BL#39 DAYANA PERDOMO (11 messages, 8 related DSN convs closed) |
| Message batching verified | BL#42 EDDA RODRIGUEZ |
| Family context populated | 11 bounce logs with Akdemia family data |

---

## Planned Skills (Not Yet Active)

| Skill | Purpose | Key Capability Needed |
|-------|---------|----------------------|
| `bill_reminder` | Friendly invoice due date reminders | Access to `account.move`, payment status |
| `billing_support` | Balance inquiry, payment confirmation, billing Q&A | Payment receipt screenshot reading (now possible with v1.13.0 image support) — extract amount, date, reference, match against open invoices |

---

## Current Limitations

| Limitation | Impact | Potential Enhancement |
|------------|--------|----------------------|
| **Manual initiation only** | Operator must click "Iniciar WhatsApp" for each bounce log | Batch initiation wizard with smart scheduling |
| **Generic bounce reason greeting** | Same greeting regardless of whether bounce is mailbox_full vs. domain_not_found | Tailored greetings per bounce reason |
| **No conversation analytics** | No dashboard with turns-to-resolution, response times, resolution type distribution | Analytics tab in dashboard |
| **No retry for timed-out conversations** | Failed conversations (72h no reply) are not retried | Auto-retry after 1-2 weeks with different approach |
| **No proactive email suggestion** | Even when Akdemia shows the same parent has a different (working) email, Glenda doesn't suggest it | Use family context to proactively offer the Akdemia email |

---

## Architecture Diagram

```
                          ┌─────────────────────┐
                          │   OPERATOR (Odoo)    │
                          │  "Iniciar WhatsApp"  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  ai.agent.conversation│
                          │  (Odoo module)       │
                          └──────────┬──────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
           ┌────────▼───────┐ ┌─────▼──────┐ ┌──────▼──────┐
           │  WhatsApp API  │ │ Claude API │ │   Skills    │
           │ (MassivaMóvil) │ │ (Haiku 4.5)│ │  (Python)   │
           └────────┬───────┘ └─────┬──────┘ └──────┬──────┘
                    │               │               │
                    │     ┌─────────▼─────────┐     │
                    │     │  System Prompt +   │     │
                    │     │  Family Context +  │     │
                    │     │  Conversation Hist │     │
                    │     └───────────────────┘     │
                    │                               │
           ┌────────▼───────────────────────────────▼──────┐
           │              BRIDGE SCRIPTS                    │
           │  (Resolution, Escalation, Health, Email Check) │
           └────────┬───────────────┬──────────────┬───────┘
                    │               │              │
           ┌────────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
           │   Freescout   │ │  Google   │ │   Akdemia   │
           │   (MySQL)     │ │  Sheets   │ │  (Scraper)  │
           └───────────────┘ └───────────┘ └─────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `addons/ueipab_ai_agent/` | Odoo module (models, views, skills, controllers) |
| `addons/ueipab_bounce_log/` | Bounce log module (model, resolution workflow) |
| `addons/ueipab_ai_agent/skills/bounce_resolution.py` | Bounce resolution skill (prompt, context, actions) |
| `addons/ueipab_ai_agent/models/ai_agent_conversation.py` | Conversation state machine, message processing, crons |
| `addons/ueipab_ai_agent/models/claude_service.py` | Anthropic API integration |
| `addons/ueipab_ai_agent/models/whatsapp_service.py` | MassivaMóvil WhatsApp API |
| `addons/ueipab_ai_agent/controllers/webhook.py` | WhatsApp webhook endpoint |
| `scripts/ai_agent_resolution_bridge.py` | Freescout + Sheets + Akdemia post-processing |
| `scripts/ai_agent_escalation_bridge.py` | Freescout ticket + WA group for escalations |
| `scripts/ai_agent_email_checker.py` | Verification email detection in Freescout |
| `scripts/ai_agent_wa_health_monitor.py` | WhatsApp number health + failover |
| `scripts/daily_bounce_processor.py` | Bounce detection from Freescout |
| `scripts/akdemia_email_sync.py` | Akdemia email change detection |
