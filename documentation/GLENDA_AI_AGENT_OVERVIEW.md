# Glenda — AI Agent Overview

**Version:** 17.0.1.31.0 | **Status:** Testing (Live with real customers) | **Date:** 2026-04-19

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

Glenda's schedule behavior depends on the skill:

| Skill | Schedule |
|-------|----------|
| `bounce_resolution`, `bill_reminder`, `billing_support`, `hr_data_collection`, `payslip_ack_reminder` | Business hours only (see below) |
| `general_inquiry` | **24/7 — no schedule restriction** |

**Business hours (VET, GMT-4):**

| Day | Hours |
|-----|-------|
| Weekdays | 06:30 - 20:30 |
| Weekends & Holidays | 09:30 - 19:00 |

Customer-initiated replies to business-hours skills are also processed anytime (webhook path). The schedule gates cron-driven outbound only.

---

## What Glenda Knows (Context Awareness)

| Area | What She Has Access To | Since |
|------|------------------------|-------|
| **Contact identity** | Name, bounced email, bounce reason, remaining active emails | v1.0.0 |
| **Multi-email awareness** | Adjusts approach if contact has other working emails vs. no emails at all | v1.0.0 |
| **Family context** | All Akdemia-registered parents for this family — names, cedulas, emails, role (Representante/Representante.1). Warns if customer proposes an email already used by another parent | v1.12.0 |
| **Message batching** | Reads ALL customer messages before responding (customers send multiple short WhatsApp messages in rapid succession) | v1.11.0 |
| **Image/screenshot support** | Can see images customers send (screenshots, photos). Uses Claude vision to interpret content. Images archived locally before MassivaMóvil URL expiry | v1.13.0 |
| **2026-2027 enrollment knowledge** | Current rates (until Aug 2026): Inscripción $197,38 · Mensualidad $197,38 · Pronto pago $162,39. Projected from Sep 1, 2026: Inscripción $264,48 · Mensualidad $264,48 · Pronto pago $241,16 (8,816% discount). Additional costs: Seguro $15 · Enc. inglés $30 · Olimpiadas $10 · Enc. digital bach. $36 · Competencia Kurios $10 · MOA inglés $25 (si seleccionado) | v1.29.7–v1.29.9 |
| **PDVSA/Petropiar policy** | Knows 2026-2027 policy: benefit discontinued. Scenario A (new prospect) → informs change, billing handoff. Scenario B (existing distressed family) → empathetic calm, invites Director meeting, fires urgent retention alert to pagos@ | v1.29.7 |
| **Timeout follow-up** | After 24h of silence Glenda sends a gentle follow-up ("¿Pude ayudarte?"). After 48h a final courtesy closing. After 72h conversation auto-closes. `max_turns` for general_inquiry raised to 25 | v1.29.8 |
| **Multi-student quotation** | Asks for number of children (and bachillerato level if applicable). Applies sibling discounts (2nd 5%, 3rd 6%, 4th+ 7% on mensualidad). 4-section quote: mensualidad per child + inscripción total + costos anuales ($55/student: seguro $15, enc. inglés $30, olimpiadas $10; +$36 bachillerato) + TOTAL PRIMER MES (regular and pronto pago). Optional costs excluded. Hands off to billing with full quote | v1.30.0–v1.30.1 |
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

## General Inquiry Skill (v1.26.0+)

Glenda now handles **unsolicited inbound messages** — when an unknown phone sends a WhatsApp to the Glenda number with no active conversation. This uses the `general_inquiry` skill which operates 24/7 (no schedule restriction).

### What She Does

1. Greets the person warmly, introduces herself as an assistant of the school.
2. Identifies the contact in Odoo (by phone number). If recognized, addresses them by name.
3. Answers general questions using institutional knowledge: monthly fees, payment methods, bank accounts, Zelle, Binance, Mercantil portal.
4. Routes complex or personal inquiries to the human team via email handoff.

### Handoff Routing

| Route | Inquiry Type | Routed To |
|-------|-------------|-----------|
| `billing` | Billing / debt / balance / payment adjustments | `pagos@ueipab.edu.ve` (Pagos y Facturación) |
| `support` | Documents, student matters, complaints, general support | `soporte@ueipab.edu.ve` (Soporte) |
| `pdvsa_retention` | Existing 2025-2026 PDVSA/Petropiar family expressing economic hardship | `pagos@ueipab.edu.ve` — **urgent** alert email |

On handoff, Glenda sends a detailed email to the appropriate team with: customer phone, name, Odoo contact status, inquiry summary, and the full conversation transcript.

For `pdvsa_retention` route, the subject is prefixed with `[URGENTE - Glenda] Familia PDVSA — Riesgo de no renovación` and includes a risk summary and required action prompt.

### PDVSA / Petropiar Policy (v1.29.7)

The 35% credit advance benefit offered in 2025-2026 has been **discontinued for 2026-2027**.

| Scenario | Who | Glenda's Behavior |
|----------|-----|-------------------|
| **A — New prospect** | Employee of PDVSA/Petropiar with no prior enrollment | Explains discontinuation clearly but cordially. 100% upfront at BCV rate. Handoff to `billing` |
| **B — Existing distressed family** | Enrolled in 2025-2026, expressing "no puedo pagar", "voy a salir", etc. | Responds with maximum empathy and calm. Affirms the school values their family. Invites Director meeting. Fires urgent retention alert (`pdvsa_retention`) |

### Promotional Flyers (v1.29.0)

When a customer's question matches a topic covered by a promotional flyer (inscriptions, tuition, extracurricular courses, payment methods), Glenda sends the relevant flyer image via WhatsApp alongside her text reply.

| Flyer Key | Content |
|-----------|---------|
| `inscripcion` | Inscripciones abiertas 2026-2027 — $197.38/año, 17.72% descuento hasta 1 mayo |
| `pronto_pago` | Mensualidad congelada a $162.39 si pagas en los primeros 10 días del mes |
| `tarjeta_credito` | Tarjetas de crédito nacionales e internacionales sin comisiones |
| `english` | MOA School: Cursos de Inglés After School, $38/mes |
| `robotica` | Robótica con Kurios — 2 clases/semana, $52/mes |
| `dibujo` | Curso de Dibujo y Pintura — 3 meses, 4h semanales, $38/mes |
| `bachillerato_virtual` | Bachillerato Virtual 100% online |

Flyer images are hosted at `https://dev.ueipab.edu.ve/flyers/` (nginx-served, public).

> **⚠️ Known Limitation (as of 2026-04-01):** The MassivaMóvil API accepts `type=photo` requests with status 200 and queues them, but images are **not delivered** to the WhatsApp end user. Confirmed through multiple tests. Awaiting MassivaMóvil tech support clarification. The code infrastructure is fully in place — once the API issue is resolved (or a hyperlink-based fallback is implemented), flyer delivery will work automatically.

### Trigger

The 24h cooldown guard prevents re-triggering a general_inquiry conversation too quickly for the same number. After 24h of inactivity, a new inquiry from the same number creates a fresh conversation.

---

## Automated Infrastructure (10 Processes)

### Odoo Crons (Inside the Module)

| Cron | Interval | Purpose |
|------|----------|---------|
| **Poll WhatsApp Messages** | 5 min | Picks up customer WhatsApp replies from MassivaMóvil API |
| **Check Conversation Timeouts** | 1 hour | 24h gentle follow-up, 48h final notice, 72h auto-close |
| **Credit Guard** | 30 min | Monitors WA sends + Claude spend, kill switch if depleted |
| **Archive Attachments** | 2 hours | Downloads and archives WA attachment images before MassivaMóvil URL expiry |
| **Stagger HR Data Collection** | 30 min | Starts draft `hr_data_collection` conversations respecting capacity + schedule |
| **Stagger Payslip Ack Reminders** | 30 min | Starts draft `payslip_ack_reminder` conversations respecting capacity + schedule |
| **Auto-Resolve Ack Reminders** | 30 min | Detects `is_acknowledged=True` on linked payslip → auto-closes conversation |

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

## Active Skills (v1.31.0)

| Skill Code | Name | Source Model | Status | Max Turns | Schedule |
|---|---|---|---|---|---|
| `bounce_resolution` | Resolución de Rebotes | `mail.bounce.log` | Production-ready | 5 | Business hours |
| `bill_reminder` | Recordatorio de Factura | `account.move` | Implemented, not yet used | 3 | Business hours |
| `billing_support` | Soporte de Facturación | `res.partner` | Implemented, not yet used | 4 | Business hours |
| `general_inquiry` | Consulta General | *(inbound)* | Production-ready | 25 | 24/7 |
| `hr_data_collection` | Recolección de Datos HR | `hr.data.collection.request` | Testing | 30 | Business hours |
| `payslip_ack_reminder` | Recordatorio de Conformidad | `hr.payslip` | Testing (v1.31.0) | 4 | Business hours |

### `payslip_ack_reminder` skill (v1.31.0)

- **Trigger:** HR opens payslip batch → "Recolección de Datos" wizard Tab 2 → selects unacknowledged payslips → creates draft conversations
- **Greeting:** Identifies Glenda as *"la agente de asistencia virtual"* (virtual agent, not real staff), payslip number + period + net VEB amount, directs to institutional email — **no direct portal link**
- **Escalation:** Any employee concern → `ACTION:ESCALATE:desc` → email to `recursoshumanos@ueipab.edu.ve` with conversation transcript + Odoo link → conversation auto-closes
- **Auto-resolve:** `_cron_check_ack_acknowledged()` detects `is_acknowledged=True` on linked payslip, closes conversation automatically
- **Timeout:** 48h, 1 reminder at 24h

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

## Production Readiness Review (Updated 2026-04-19)

### Deployment Model

All 7 system cron scripts run on the **dev server** (where Freescout MySQL is local). For production, they STAY on the dev server — only `TARGET_ENV` changes to `production` so they point Odoo XML-RPC at `https://odoo.ueipab.edu.ve` / `DB_UEIPAB`. Freescout/Sheets/WhatsApp connections remain unchanged.

```
                  DEV SERVER (10.124.0.2)                    PROD SERVER (10.124.0.3)
            ┌──────────────────────────────┐            ┌──────────────────────────┐
            │  7 System Cron Scripts       │            │  Odoo 17 (ueipab17)      │
            │  Freescout MySQL (local)     │ ──XML-RPC──│  ueipab_ai_agent module  │
            │  /var/www/dev/odoo_api_bridge│            │  ueipab_bounce_log       │
            │  Google Sheets API           │            │  ueipab_hr_employee      │
            │  Akdemia Scraper (Playwright)│            │  5 Odoo Crons            │
            │                              │ ←─Webhook──│  Webhook endpoint        │
            └──────────────────────────────┘            └──────────────────────────┘
```

### Gap Analysis

#### GAP 0: Hardcoded Credentials in Bridge Scripts — SECURITY CRITICAL BLOCKER *(NEW 2026-04-19)*

`ai_agent_escalation_bridge.py` and `ai_agent_resolution_bridge.py` (and `ai_agent_email_checker.py`) contain production Odoo XML-RPC passwords and Freescout MySQL password hardcoded as default fallback values in source code:

```python
ODOO_CONFIGS = {
    'production': {
        'password': 'f69330e5bd6ae043320f054e9df9fcbbb34522db',  # ← EXPOSED
    }
}
FREESCOUT_DB_PASSWORD = os.environ.get('FREESCOUT_DB_PASSWORD', '1gczp1S@3!')  # ← EXPOSED
```

**Required fixes before production go-live:**
1. Remove all hardcoded credential fallbacks — raise `RuntimeError` if env var missing
2. Create `/root/.odoo_agent_env_prod` (chmod 600) on dev server with production credentials
3. Update all crontab entries to source this file before script execution
4. Rotate both production Odoo user API key and Freescout MySQL password
5. Audit git history — revoke any compromised credentials

**Crontab pattern (after fix):**
```bash
*/5 * * * * root . /root/.odoo_agent_env_prod && python3 /opt/odoo-dev/scripts/ai_agent_escalation_bridge.py >> /var/log/ai_agent_escalation_prod.log 2>&1
```

---

#### GAP 1: Odoo Modules Not Installed in Production — BLOCKER

Three modules must be installed in order (dependency chain):

| Module | Version | Required By | Prod Status |
|--------|---------|-------------|-------------|
| `ueipab_hr_employee` | (latest) | `ueipab_ai_agent` depends | **NOT FOUND** on prod addons path |
| `ueipab_bounce_log` | 17.0.1.4.0 | `ueipab_ai_agent` depends | **NOT FOUND** on prod addons path |
| `ueipab_ai_agent` | 17.0.1.31.0 | Primary module | **NOT FOUND** on prod addons path |

**Already installed in prod (no action):** `contacts`, `mail`, `mass_mailing`, `account`, `hr`, `hr_payroll_community`.

**Action:** Copy all 3 modules to `/home/vision/ueipab17/addons/`. Install in order: `ueipab_hr_employee` → `ueipab_bounce_log` → `ueipab_ai_agent`.

#### GAP 2: Config Files Missing on Production

| File | Needed By | Location on Dev | Production Path |
|------|-----------|-----------------|-----------------|
| `whatsapp_massiva.json` | Module (post_init_hook) + escalation/health scripts | `/opt/odoo-dev/config/` | `/home/vision/ueipab17/config/` |
| `anthropic_api.json` | Module (post_init_hook) | `/opt/odoo-dev/config/` | `/home/vision/ueipab17/config/` |
| `google_sheets_credentials.json` | Bridge scripts only (dev server) | `/opt/odoo-dev/config/` | **N/A — stays on dev server** |

**Note:** Config files no longer exist on dev filesystem (deleted after initial load). Values are stored in `ir.config_parameter`. For production, either: (a) recreate JSON files temporarily for `post_init_hook`, or (b) manually set ~30 `ai_agent.*` system parameters after install.

**Action:** Recreate JSON config files on production server before module install. Remove after `post_init_hook` loads values.

#### GAP 3: Webhook — Enhancement for Real-Time Response — NEW

**Current state:** Testing uses **polling-only** mode (cron every 1 minute). No webhook configured.

**Production plan:** Enable MassivaMóvil webhook for **near-instant** message processing (~1-3s vs up to 60s polling delay). Keep polling cron as fallback.

**Architecture with webhook enabled:**
```
Customer sends WA msg
        │
        ├──► MassivaMóvil ──webhook POST──► Odoo /ai-agent/webhook/whatsapp
        │                                        │
        │                                   Process immediately
        │                                   (Claude + reply in ~3s)
        │
        └──► Poll cron (1 min) ──GET /api/get/wa.received──► Dedup catches it
                                                              (already processed)
```

**Benefits:**
- Customer gets reply in ~3 seconds instead of up to 60 seconds
- Better conversation flow (feels like real-time chat)
- Polling cron serves as safety net only (catches any webhook failures)
- Global dedup (v1.19.0) ensures no double-processing between webhook + poll

**Requirements:**
- Production Nginx must route `/ai-agent/` to Odoo backend (currently returns **404**)
- MassivaMóvil dashboard: Tools → Webhooks → set callback URL
- Webhook URL: `https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp`
- `ai_agent.whatsapp_api_secret` must be set (webhook validates secret)

**Action:**
1. Add Nginx location block for `/ai-agent/` → proxy to Odoo container
2. Configure callback URL in MassivaMóvil dashboard
3. Test with a curl POST to verify 200 response
4. Poll cron stays active as fallback (can reduce interval to 5 min)

#### GAP 4: System Crons — TARGET_ENV and DRY_RUN Flags

| Cron File | Script | Current TARGET_ENV | Current DRY_RUN | Production Change Needed |
|-----------|--------|-------------------|-----------------|--------------------------|
| `ai_agent_bounce_processor` | `daily_bounce_processor.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_email_checker` | `ai_agent_email_checker.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_escalation` | `ai_agent_escalation_bridge.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_resolution` | `ai_agent_resolution_bridge.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `ai_agent_wa_health` | `ai_agent_wa_health_monitor.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |
| `customer_matching` | `customer_matching_daily.py` | testing | **LIVE** (`--live`) | Change `TARGET_ENV=production` |

**Status:** All 6 crons are LIVE. Only `TARGET_ENV` switch needed for production.

**Note:** `ai_agent_email_checker` and `ai_agent_hr_email_checker` both lack `TARGET_ENV` in their cron — they read Odoo config from JSON (which has hardcoded `testing` db). Must update JSON or add `TARGET_ENV` support.

#### GAP 5: Akdemia Pipeline Path Dependencies

Not a blocker — all scripts run on dev server. Only `TARGET_ENV` switch needed. See [Akdemia Data Pipeline](AKDEMIA_DATA_PIPELINE.md).

#### ~~GAP 6: Escalation Bridge & Email Checker are DRY_RUN~~ RESOLVED (2026-02-14)

Both scripts switched to **LIVE** on 2026-02-14.

#### GAP 7: Freescout API Migration (Optional)

Not a blocker. Direct MySQL works. See [Freescout API Migration Plan](FREESCOUT_API_MIGRATION_PLAN.md).

#### GAP 8: Credit Guard Production Calibration

- Claude spend is **cumulative (lifetime)**, not monthly
- Default `claude_spend_limit_usd = 4.50` (90% of initial $5 credit)
- When topping up credits, MUST increase this limit proportionally
- WA sends checked against MassivaMóvil Plan 500 subscription

**Action:** Set appropriate `claude_spend_limit_usd` based on actual Anthropic credit balance at go-live.

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

Initial analysis (2026-02-14) showed 19 partner + 22 MC diffs. Most resolved by Phase 5 sync. Recent sync (2026-03-04): 3 employee contacts synced (Daniel Bongianni, Rafael Pérez, Lorena Reyes).

**Status:** Not a blocker. Production will catch up when Phase 5 runs against production data.

#### GAP 12: Odoo Cron Configuration *(updated 2026-04-19)*

Testing has **7 Odoo crons** (inside the module):

| Cron | Testing Interval | Production Recommendation | Activate Day 1? |
|------|-----------------|--------------------------|-----------------|
| Poll WhatsApp Messages | 1 min | **5 min** (webhook handles real-time; polling is fallback only) | ✓ Yes |
| Check Conversation Timeouts | 1 hour | 1 hour | After 48h stable |
| Credit Guard | 30 min | 30 min | ✓ Yes |
| Archive Attachments | 2 hours | 2 hours | ✓ Yes |
| Stagger HR Data Collection | 30 min | 30 min | Phase 2 (after HR data collection launch) |
| Stagger Payslip Ack Reminders | 30 min | 30 min | ✓ Yes (if payslip ack skill active) |
| Auto-Resolve Ack Reminders | 30 min | 30 min | ✓ Yes (if payslip ack skill active) |

**Action:** After webhook is live, set poll cron to 5 min. Enable crons per column above — do not activate timeouts until system is stable for 48h.

#### GAP 13: HR Data Collection Skill

The `hr_data_collection` skill depends on `ueipab_hr_employee` module (GAP 1) and has its own Stagger cron.

**Consideration:** Enable in Phase 2 (after core system is stable in production). Requires HR employee records to be populated before launching batch collection campaigns.

#### GAP 14: Payslip Ack Reminder Skill (New — v1.31.0) *(NEW 2026-04-19)*

The `payslip_ack_reminder` skill is new (v1.31.0, 2026-04-19). It requires:
- `hr.payslip.is_acknowledged` field on payslips (from `ueipab_payroll_enhancements`, already in prod)
- `hr.payslip._get_acknowledgment_url()` method (from `ueipab_payroll_enhancements`, already in prod)
- Two new crons: Stagger Payslip Ack Reminders + Auto-Resolve Ack Reminders

**Consideration:** Can be activated from day 1 alongside core module. No additional module dependencies beyond what's already deployed in production.

### Production Migration Sequence *(updated 2026-04-19)*

```
Phase 0 — Security Hardening (MUST complete before any other phase)
  [ ] Rotate production Odoo user API key/password (tdv.devs@gmail.com)
  [ ] Rotate Freescout MySQL password (free297)
  [ ] Remove hardcoded credential fallbacks from bridge scripts (GAP 0)
  [ ] Create /root/.odoo_agent_env_prod on dev server (chmod 600):
        ODOO_URL=https://odoo.ueipab.edu.ve
        ODOO_DB=DB_UEIPAB
        ODOO_USER=tdv.devs@gmail.com
        ODOO_PASSWORD=<rotated-password>
        FREESCOUT_DB_HOST=localhost
        FREESCOUT_DB_USER=free297
        FREESCOUT_DB_PASSWORD=<rotated-password>
        FREESCOUT_DB_NAME=free297
  [ ] Update crontab entries to source /root/.odoo_agent_env_prod
  [ ] Verify scripts still work against TESTING using new env file

Phase A — Prepare (no user impact)
  [ ] Backup production database: pg_dump DB_UEIPAB > /backup/DB_UEIPAB_<date>.sql
  [ ] Generate webhook secret: python3 -c "import secrets; print(secrets.token_hex(32))"
  [ ] Copy ueipab_hr_employee to /home/vision/ueipab17/addons/
  [ ] Copy ueipab_bounce_log to /home/vision/ueipab17/addons/
  [ ] Copy ueipab_ai_agent (v1.31.0) to /home/vision/ueipab17/addons/
  [ ] Create /home/vision/ueipab17/config/ directory
  [ ] Copy whatsapp_massiva.json to production config/ — UPDATE:
        webhook.secret = <generated-secret>
        webhook.callback_url = https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp
  [ ] Copy anthropic_api.json to production config/
  [ ] Install modules in order: ueipab_hr_employee → ueipab_bounce_log → ueipab_ai_agent
  [ ] Verify ir.config_parameter values loaded (~30 ai_agent.* params)
  [ ] Set ai_agent.dry_run = True (safety first — change to False only in Phase D)
  [ ] Set ai_agent.active_db = 'DB_UEIPAB' (verify auto-set by post_init_hook)
  [ ] Set ai_agent.claude_spend_limit_usd = appropriate value (match Anthropic credit balance)
  [ ] Verify 6 skills loaded: Contactos → AI Agent → Configuración de Skills
  [ ] Verify 7 crons created: Settings → Automation → Scheduled Actions → Search "AI Agent"

Phase B — Webhook & Nginx Setup (enables real-time <1s responses)
  [ ] Add Nginx location block on production server:
        location /ai-agent/ {
            proxy_pass http://localhost:8069;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
  [ ] Reload nginx: nginx -s reload
  [ ] Test endpoint reachable (expect JSON error, NOT 404):
        curl -X POST https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp \
          -H "Content-Type: application/json" \
          -d '{"secret":"wrong","type":"whatsapp","data":{"id":1,"phone":"+58000","message":"test"}}'
  [ ] Configure MassivaMóvil dashboard: Tools → Webhooks:
        Callback URL: https://odoo.ueipab.edu.ve/ai-agent/webhook/whatsapp
        Secret: <generated-secret from Phase A>
  [ ] Verify webhook secret matches ai_agent.whatsapp_api_secret param in Odoo
  [ ] Set poll cron interval to 5 min (webhook is primary; poll is fallback only)

Phase C — Configure & Dry Test (no user impact)
  [ ] Update all host cron scripts TARGET_ENV=production (keep --live flags)
  [ ] Run bounce processor DRY against production → verify Freescout bounces detected
  [ ] Run resolution bridge DRY → verify it sees resolved BLs in prod DB
  [ ] Run escalation bridge DRY → verify it detects escalations in prod DB
  [ ] Run email checker DRY → verify it scans Freescout conversations
  [ ] Run WA health monitor DRY → verify active number check
  [ ] Set ai_agent.active_db = '' on TESTING Odoo (testing crons self-skip)
  [ ] Restart testing Odoo, confirm logs show "active_db mismatch, skipping"

Phase D — Go Live (staged)
  [ ] Set ai_agent.dry_run = False on PRODUCTION Odoo
  [ ] Activate Odoo crons (Day 1 set):
        ✓ Poll WhatsApp Messages (5 min)
        ✓ Credit Guard (30 min)
        ✓ Archive Attachments (2 hours)
        ✓ Stagger Payslip Ack Reminders (30 min)
        ✓ Auto-Resolve Ack Reminders (30 min)
        ✗ Check Conversation Timeouts — enable AFTER 48h stable
        ✗ Stagger HR Data Collection — enable in Phase 2
  [ ] Run bounce processor LIVE → creates initial bounce log records in prod
  [ ] Enable host crons LIVE: resolution bridge, bounce processor, WA health
  [ ] Monitor: trigger first Glenda conversation end-to-end
        → Verify webhook path (<3s) AND poll fallback
        → Verify Claude AI response logged + tokens charged in Anthropic console
        → Verify WhatsApp message appears in MassivaMóvil dashboard
  [ ] Enable host crons LIVE: escalation bridge, email checker
  [ ] Enable host cron LIVE: customer_matching (Akdemia pipeline)
  [ ] Monitor Credit Guard for 48h (ai_agent.credits_ok stays True)
  [ ] After 48h stable: enable Check Conversation Timeouts cron

Phase E — Post-Launch Optimization
  [ ] Confirm webhook response times (<5s end-to-end measured)
  [ ] Confirm poll cron + webhook coexist without duplicate messages (check global dedup logs)
  [ ] Launch HR Data Collection in production (Phase 2):
        → Enable Stagger HR Data Collection cron (30 min)
        → Create first batch collection requests for HR team
  [ ] Schedule Credit Guard limit review (align with Anthropic credit top-ups)
        → Claude spend is cumulative (lifetime) — must raise claude_spend_limit_usd on top-up
  [ ] Consider nginx rate limiting on webhook route to guard against floods:
        limit_req_zone $binary_remote_addr zone=webhook:10m rate=10r/s;
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
