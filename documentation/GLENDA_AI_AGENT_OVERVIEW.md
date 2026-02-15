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

## Production Readiness Review (2026-02-14)

### Deployment Model

All 7 system cron scripts run on the **dev server** (where Freescout MySQL is local). For production, they STAY on the dev server — only `TARGET_ENV` changes to `production` so they point Odoo XML-RPC at `https://odoo.ueipab.edu.ve` / `DB_UEIPAB`. Freescout/Sheets/WhatsApp connections remain unchanged.

```
                  DEV SERVER (10.124.0.2)                    PROD SERVER (10.124.0.3)
            ┌──────────────────────────────┐            ┌──────────────────────────┐
            │  7 System Cron Scripts       │            │  Odoo 17 (ueipab17)      │
            │  Freescout MySQL (local)     │ ──XML-RPC──│  ueipab_ai_agent module  │
            │  /var/www/dev/odoo_api_bridge│            │  ueipab_bounce_log       │
            │  Google Sheets API           │            │  4 Odoo Crons            │
            │  Akdemia Scraper (Playwright)│            │  Webhook endpoint        │
            └──────────────────────────────┘            └──────────────────────────┘
```

### Gap Analysis

#### GAP 1: Odoo Modules Not Installed in Production

| Module | Required | Status |
|--------|----------|--------|
| `ueipab_bounce_log` v17.0.1.4.0 | Hard dependency | **NOT INSTALLED** |
| `ueipab_ai_agent` v17.0.1.13.0 | Primary module | **NOT INSTALLED** |

**Action:** Copy modules to `/home/vision/ueipab17/addons/`, install `ueipab_bounce_log` first, then `ueipab_ai_agent`.

#### GAP 2: Config Files Missing on Production

| File | Needed By | Location on Dev | Production Path |
|------|-----------|-----------------|-----------------|
| `whatsapp_massiva.json` | Module (post_init_hook) + escalation/health scripts | `/opt/odoo-dev/config/` | `/home/vision/ueipab17/config/` |
| `anthropic_api.json` | Module (post_init_hook) | `/opt/odoo-dev/config/` | `/home/vision/ueipab17/config/` |
| `google_sheets_credentials.json` | Bridge scripts only (dev server) | `/opt/odoo-dev/config/` | **N/A — stays on dev server** |

**Action:** Copy `whatsapp_massiva.json` and `anthropic_api.json` to production. Sheets creds stay on dev.

#### GAP 3: Webhook URL Not Configured

MassivaMóvil webhook callback must point to production Odoo:
- **Current:** Not set (polling-only mode in testing)
- **Required:** `https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp`

**Action:** Configure in MassivaMóvil dashboard. Verify production Nginx passes `/ai-agent/` to Odoo.

#### GAP 4: System Crons — TARGET_ENV and DRY_RUN Flags

| Cron File | Script | Current TARGET_ENV | Current DRY_RUN | Production Change Needed |
|-----------|--------|-------------------|-----------------|--------------------------|
| `ai_agent_bounce_processor` | `daily_bounce_processor.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_email_checker` | `ai_agent_email_checker.py` | testing | **LIVE** (`--live`, switched 2026-02-14) | Change `TARGET_ENV=production` |
| `ai_agent_escalation` | `ai_agent_escalation_bridge.py` | testing | **LIVE** (`--live`, switched 2026-02-14) | Change `TARGET_ENV=production` |
| `ai_agent_resolution` | `ai_agent_resolution_bridge.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_wa_health` | `ai_agent_wa_health_monitor.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `customer_matching` | `customer_matching_daily.py` | testing | **DRY** (no override) | Change `TARGET_ENV=production`, add `--live` |

**Action:** Update all 6 cron files in `/etc/cron.d/`. Recommend phased: first switch TARGET_ENV in DRY mode, verify logs, then enable `--live`.

#### GAP 5: Akdemia Pipeline Path Dependencies

The Akdemia scraper and orchestrator live under `/var/www/dev/odoo_api_bridge/` on the dev server. This is **NOT a blocker** — these scripts always run on the dev server (Playwright/Chrome is installed there). They reach Odoo via XML-RPC.

| Path | Used By | Runs On | Production Impact |
|------|---------|---------|-------------------|
| `/var/www/dev/odoo_api_bridge/scripts/customer_matching_daily.py` | customer_matching cron | dev server | None — stays on dev |
| `/var/www/dev/odoo_api_bridge/customer_matching/integrations/akdemia_scraper.py` | orchestrator | dev server | None — stays on dev |
| `/var/www/dev/odoo_api_bridge/akdemia_downloads/` | scraper output | dev server | None — stays on dev |
| `/opt/odoo-dev/scripts/akdemia_email_sync.py` | orchestrator (subprocess) | dev server | TARGET_ENV must be `production` |

**Status:** No path changes needed. Only TARGET_ENV switch.

#### ~~GAP 6: Escalation Bridge & Email Checker are DRY_RUN~~ RESOLVED (2026-02-14)

Both scripts switched to **LIVE** on 2026-02-14:
- **Escalation bridge** — `--live` added to `/etc/cron.d/ai_agent_escalation`. Freescout tickets + WA group alerts now created for real.
- **Email checker** — `--live` argparse flag added to script + cron updated in `/etc/cron.d/ai_agent_email_checker`. Customer verification email replies now auto-resolve conversations.

#### GAP 7: Freescout API Migration (Optional but Recommended)

Current scripts use **direct MySQL** for Freescout operations. This works but:
- Bypasses Laravel event system (must manually set `user_updated_at=NOW()`)
- Fragile if Freescout schema changes
- No API purchase yet ([plan](FREESCOUT_API_MIGRATION_PLAN.md))

**Status:** Not a blocker. Direct SQL works. API migration is a future improvement.

#### GAP 8: Credit Guard Production Calibration

- Claude spend is **cumulative (lifetime)**, not monthly
- Default `claude_spend_limit_usd = 4.50` (90% of initial $5 credit)
- When topping up credits, MUST increase this limit proportionally
- WA sends checked against MassivaMóvil Plan 500 subscription

**Action:** Set appropriate `claude_spend_limit_usd` based on actual credit balance at go-live.

#### GAP 9: Bounce Log Data (Initial Load)

Production has NO bounce logs yet. The `daily_bounce_processor.py` script will create them from Freescout data on first run.

**Action:** Run bounce processor against production first (DRY to preview, then LIVE). This creates the bounce log records that Glenda will work from.

#### GAP 10: Testing Environment Lockout

When production goes live, testing must stop processing to avoid double-sending WhatsApp messages (both envs share the same MassivaMóvil account).

**Action:**
1. Set `ai_agent.active_db = 'DB_UEIPAB'` on production
2. Set `ai_agent.active_db = ''` on testing (Odoo crons self-skip)
3. Update all cron scripts: `TARGET_ENV=production`

#### GAP 11: Partner/MC Data Drift (prod vs test)

Dry-run sync comparison (2026-02-14) showed:
- **19 partners** where testing has extra family emails (Phase 5 enrichment)
- **22 mailing contacts** with same extra emails
- **9 partners** in production but not testing (new enrollments)
- **0 emails** only in production (testing is superset)

**Status:** Not a blocker. Production will catch up when Phase 5 runs against production data. New enrollments will be picked up by bounce processor.

### Production Migration Sequence

```
Phase A — Prepare (no user impact)
  [ ] Backup production database
  [ ] Copy ueipab_bounce_log + ueipab_ai_agent to /home/vision/ueipab17/addons/
  [ ] Copy whatsapp_massiva.json + anthropic_api.json to /home/vision/ueipab17/config/
  [ ] Install ueipab_bounce_log on production
  [ ] Install ueipab_ai_agent on production
  [ ] Verify ir.config_parameter values loaded
  [ ] Set ai_agent.dry_run = True (safety first)
  [ ] Set ai_agent.active_db = 'DB_UEIPAB'
  [ ] Set ai_agent.claude_spend_limit_usd = appropriate value

Phase B — Configure & Dry Test (no user impact)
  [ ] Configure MassivaMóvil webhook → https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp
  [ ] Verify Nginx passes /ai-agent/ to Odoo
  [ ] Update all 6 cron files: TARGET_ENV=production (keep DRY_RUN)
  [ ] Run bounce processor DRY → verify it detects bounces from Freescout
  [ ] Run resolution bridge DRY → verify it sees resolved BLs
  [ ] Run escalation bridge DRY → verify it detects escalations
  [ ] Run email checker DRY → verify it scans Freescout conversations
  [ ] Run WA health monitor DRY → verify it checks active number
  [ ] Set ai_agent.active_db = '' on TESTING (disable testing crons)

Phase C — Go Live (staged)
  [ ] Run bounce processor LIVE → creates initial bounce log records
  [ ] Enable cron --live flags: resolution bridge, bounce processor, WA health
  [ ] Set ai_agent.dry_run = False on production
  [ ] Monitor: first Glenda conversation end-to-end
  [ ] Enable cron --live flags: escalation bridge, email checker
  [ ] Enable cron --live: customer_matching (Akdemia pipeline)
  [ ] Monitor Credit Guard for 48h (check ai_agent.credits_ok stays True)
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
