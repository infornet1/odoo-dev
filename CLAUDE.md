# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-02-09

## Core Instructions

**CRITICAL RULES:**
- **ALWAYS work locally, NEVER in production environment**
- **NEVER TOUCH DB_UEIPAB without proper authorization**
- Development database: `testing`
- Production database: `DB_UEIPAB` (requires authorization)

---

## Active Features Summary

| # | Feature | Status | Module | Documentation |
|---|---------|--------|--------|---------------|
| 1 | Payroll Disbursement Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYROLL_DISBURSEMENT_REPORT.md) |
| 2 | Venezuelan Liquidation V1/V2 | Production | `ueipab_payroll_enhancements` | [V2 Impl](documentation/LIQUIDATION_V2_IMPLEMENTATION.md) |
| 3 | Prestaciones Interest Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PRESTACIONES_INTEREST_REPORT.md) |
| 4 | Venezuelan Payroll V2 | Production | `ueipab_payroll_enhancements` | [V2 Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) |
| 5 | Relacion Liquidacion Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/RELACION_BREAKDOWN_REPORT.md) |
| 6 | Payslip Email Delivery | Production | `hr_payslip_monthly_report` | [Docs](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md) |
| 7 | Batch Email Template Selector | Production | `ueipab_payroll_enhancements` | - |
| 8 | Comprobante de Pago Compacto | Production | `ueipab_payroll_enhancements` | - |
| 9 | Acuerdo Finiquito Laboral | Production | `ueipab_payroll_enhancements` | [Docs](documentation/FINIQUITO_REPORT.md) |
| 10 | AR-I Portal | Testing | `ueipab_ari_portal` | - |
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](documentation/RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | See below |
| 15 | Batch Email Progress Wizard | Production | `ueipab_payroll_enhancements` | [Docs](documentation/BATCH_EMAIL_WIZARD.md) |
| 16 | HRMS Dashboard Ack Widget | Production | `ueipab_hrms_dashboard_ack` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 17 | Cybrosys Module Refactoring | Planned | Multiple | [Docs](documentation/CYBROSYS_MODULE_MODIFICATIONS.md) |
| 18 | Liquidacion Estimation Mode | Production | `ueipab_payroll_enhancements` | See below |
| 19 | Payslip Ack Reminder System | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 20 | V2 Payroll Accounting Config | Production | Database config | See below |
| 21 | Invoice Currency Rate Bug | Documented | `tdv_multi_currency_account` | [Docs](documentation/INVOICE_CURRENCY_RATE_BUG.md) |
| 22 | Aguinaldos Disbursement Report | Production | `ueipab_payroll_enhancements` | See below |
| 23 | Advance Payment System (Pago Adelanto) | Production | `ueipab_payroll_enhancements` | See below |
| 24 | WebSocket/Nginx Fix (Email Marketing) | Production | Infrastructure | [Docs](documentation/WEBSOCKET_NGINX_FIX.md) |
| 25 | Email Bounce Processor | Testing | Script + `ueipab_bounce_log` | [Docs](documentation/BOUNCE_EMAIL_PROCESSOR.md) |
| 26 | AI Agent (WhatsApp + Claude) | Testing | `ueipab_ai_agent` | [Docs](documentation/AI_AGENT_MODULE.md) |
| 27 | Akdemia Data Pipeline | In Progress | Script + Cron | See below |
| 28 | WhatsApp Health Monitor | Testing | Script + `ueipab_ai_agent` | See below |
| 29 | Resolution Bridge | Testing | Script + Cron | See below |
| 30 | Freescout API Migration | Planned | Scripts | [Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md) |

---

## Advance Payment System (Pago Adelanto)

**Status:** Production | **Version:** 17.0.1.52.1 | **Deployed:** 2026-01-14

Allows partial salary disbursement when company needs to pay employees in installments due to financial constraints.

### Business Use Case

When company cannot pay full salary at once:
1. **Advance Batch (e.g., 50%)**: Pay partial salary now
2. **Remainder Batch (e.g., 50%)**: Pay remaining balance later

Each batch:
- Computes payslips with multiplied earnings
- Deductions recalculate on reduced amounts
- Posts with its own exchange rate
- Clean, independent journal entries

### Batch Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_advance_payment` | Boolean | Checkbox "Es Pago Adelanto" |
| `advance_percentage` | Float | Percentage to pay (e.g., 50.0) |
| `advance_total_amount` | Computed | Total advance amount |
| `is_remainder_batch` | Boolean | Marks as remainder payment |
| `advance_batch_id` | Many2one | Link to original advance batch |

### Payslip Fields

| Field | Type | Description |
|-------|------|-------------|
| `advance_amount` | Computed | Individual advance amount |

### Salary Rules Behavior

When `is_advance_payment = True` OR `is_remainder_batch = True`:
```python
# Earnings multiplied by advance_percentage
VE_SALARY_V2 = contract.salary * (batch.advance_percentage / 100)
VE_EXTRABONUS_V2 = contract.extrabonus * (batch.advance_percentage / 100)
VE_BONUS_V2 = contract.bonus * (batch.advance_percentage / 100)
# Deductions auto-recalculate on reduced gross
```

### Email Templates (Synced to Production 2026-01-08)

| Template | Purpose | Prod ID |
|----------|---------|---------|
| Payslip Email - Advance Payment - Employee Delivery | Full detailed advance notification | 44 |
| Payslip Email - Remainder Payment - Reconciliation | Shows advance + remainder + total | 45 |

### Accounting Treatment

Each batch posts independently with its exchange rate:
```
Advance Batch (50% at rate 298):
  DR 5.1.01.10.001  Bs. 14,900
     CR 1.1.01.02.001  Bs. 14,900

Remainder Batch (50% at rate 310):
  DR 5.1.01.10.001  Bs. 15,500
     CR 1.1.01.02.001  Bs. 15,500
```

No provisions or exchange difference accounts needed.

---

## Aguinaldos Disbursement Report

**Status:** Production | **Deployed:** 2025-12-19 | **Version:** v1.49.1

Generate disbursement report for Aguinaldos (Christmas Bonus) payslips with PDF/Excel export, currency selection (USD/VEB), and batch filtering.

**Access:** Payroll -> Reports -> Aguinaldos Disbursement Report

---

## Planned: Duplicate Payslip Warning

**Status:** Planned | **Priority:** Medium

Warning wizard before generating payslips to detect duplicates (same employee/overlapping period). Options: Skip Duplicates, Create All, Cancel.

---

## Liquidacion Estimation Mode

**Status:** Production | **Version:** 17.0.1.46.0

Adds "Modo Estimacion" to Relacion de Liquidacion wizard (VEB only). Applies configurable % reduction with projection watermark, hidden signatures.

---

## Venezuelan Liquidation System (V1 vs V2)

| Aspect | V1 (Legacy) | V2 (Current) |
|--------|-------------|--------------|
| Structure Code | LIQUID_VE | LIQUID_VE_V2 |
| Salary Field | `ueipab_deduction_base` | `ueipab_salary_v2` |
| Accounting | 5.1.01.10.002 | 5.1.01.10.010 |

**V2 Contract Fields:** `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`, `ueipab_vacation_prepaid_amount`, `ueipab_other_deductions`

---

## Venezuelan Payroll V2 Deductions

| Deduction | Rate | Applies To |
|-----------|------|------------|
| SSO (IVSS) | 4% | Salary, Vacaciones, Bono Vac., Utilidades |
| FAOV | 1% | Salary, Vacaciones, Bono Vac., Utilidades |
| INCES (PARO) | 0.5% | Utilidades ONLY |
| ARI | Variable % | From contract field |
| Otras Deducciones | Fixed USD | From contract field |

---

## V2 Payroll Accounting Configuration

**Status:** Production | **Updated:** 2026-01-10

| Purpose | Debit Account | Credit Account |
|---------|---------------|----------------|
| V2 Payroll (NOMINA_VE_V2) | 5.1.01.10.001 (Nomina) | 1.1.01.02.001 (Banco Venezuela) |
| V2 Liquidation (LIQUID_VE_V2) | 5.1.01.10.010 (Prestaciones) | 2.1.01.10.005 (Provision Prestaciones) |
| AGUINALDOS | 5.1.01.10.001 (Nomina) | 1.1.01.02.001 (Banco Venezuela) |

**Design Pattern:** Only deductions and NET create journal entries. Earnings rules do NOT post to accounting.

**Important:** At minimum, the `*_NET_*` rule in each structure MUST have both debit and credit accounts configured, otherwise payslips cannot be confirmed (error: "choose Debit and Credit account for at least one salary rule").

---

## Report Exchange Rate System

**3-Priority System for VEB Reports:**
1. Custom rate (wizard) -> "Tasa personalizada"
2. Rate date lookup (wizard) -> "Tasa del DD/MM/YYYY"
3. Latest available / Payslip rate -> "Tasa automatica"

**Interest Calculation:** Always uses accrual method (ignores override)

---

## Payslip Batch Features

| Feature | Description |
|---------|-------------|
| Date Sync | Syncs batch dates to draft payslips, auto-recomputes |
| Total Net Payable | Includes draft payslips, supports V1/V2/Aguinaldos |
| Exchange Rate Application | Applies rate to all payslips in batch |
| Email Sending | Template selector, notification popup |
| Exchange Rate Auto-Population | From latest BCV rate or last batch |
| Advance Payment | Partial salary disbursement with % multiplier |
| Remainder Payment | Linked to original advance batch for reconciliation |

---

## Module Versions

### Testing Environment

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | 17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | 17.0.1.52.1 | 2026-01-08 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_bounce_log | 17.0.1.2.0 | 2026-02-08 |
| ueipab_ai_agent | 17.0.1.8.0 | 2026-02-09 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.52.1 | Current (synced 2026-01-19) |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | 17.0.1.0.2 | Installed (2025-12-21) |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | Installed (2025-12-21) |

---

## Key Technical Patterns

### Odoo safe_eval (Salary Rules)
```python
# FORBIDDEN: imports, hasattr
# ALLOWED: Direct arithmetic, try/except
```

### Odoo 17 View Syntax
```xml
<!-- OLD --> <div attrs="{'invisible': [('field', '=', 0)]}">
<!-- NEW --> <div invisible="field == 0">
```

### Report Development
- Use `web.basic_layout` for UTF-8 support
- Model naming: `report.<module>.<template_id>` (exact match)
- TransientModel wizards need security access rules

---

## Production Environment

See [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md) for full details.

**Quick Reference:**
- Server: `10.124.0.3`
- Container: `0ef7d03db702_ueipab17`
- Database: `DB_UEIPAB`
- Module Path: `/home/vision/ueipab17/addons`

---

## Quick Commands

```bash
# Run script in testing
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py

# Restart Odoo
docker restart odoo-dev-web
```

---

## Email Bounce Processor

**Status:** Testing | **Type:** Phase 1 (Script) + Phase 2 (Odoo Module)

Automated detection and cleanup of bounced emails from Freescout (READ-ONLY source). Freescout database is never modified.

### Phase 1 - Standalone Script (Current Priority)

- **Script:** `scripts/daily_bounce_processor.py` (cron daily)
- **Source:** Freescout MySQL (read-only) for bounce detection
- **Target:** Production Odoo via XML-RPC (`res.partner` + `mailing.contact`)
- **Log:** `scripts/bounce_logs/bounce_log.csv` (queryable history)
- **State:** `scripts/bounce_state.json` (tracks last processed ID)

**3-Tier Logic (reason + tag based):**
- CLEAN: Representante + permanent failure (`invalid_address`, `domain_not_found`) → auto-remove email
- FLAG: Temporary failure (`mailbox_full`, `rejected`, `other`) or non-Representante → manual review
- NOT FOUND: CSV log only

**Scope:** Last 180 days. Only permanent failures are auto-cleaned (temporary = customer may fix it).

**Multi-email handling:** Contacts with multiple emails separated by `;` are handled surgically -- only the bounced email is removed, the rest are preserved.

### Phase 2 - Odoo Module (Installed in Testing)

- **Module:** `ueipab_bounce_log` v17.0.1.2.0 (extends Contacts app, not a standalone app)
- **Menu:** `Contacts > Bounce Log` (direct submenu)
- **Model:** `mail.bounce.log` with resolution workflow
- **New fields (v1.1.0):**
  - `action_tier` -- Selection (Limpiado/Revision/No Encontrado) showing script tier action
  - `freescout_url` -- Computed clickable link to Freescout conversation
- **Resolution:** Two actions per bounce record:
  - "Restaurar Email Original" -- re-enable old email (temporary issue fixed)
  - "Aplicar Nuevo Email" -- apply customer's new email
- **Script integration:** Script auto-creates `mail.bounce.log` records via XML-RPC with tier, partner link, and Freescout conversation ID
- **Freescout post-processing:** Script updates Freescout conversations with `[LIMPIADO]`/`[REVISION]`/`[NO ENCONTRADO]` prefix, internal note with bidirectional Odoo links, and status change
- **WhatsApp Integration:** Implemented via `ueipab_ai_agent` module. "Iniciar WhatsApp" button on bounce log form launches AI-powered conversation to resolve bounced emails. See [AI Agent Module](documentation/AI_AGENT_MODULE.md).

See [Full Documentation](documentation/BOUNCE_EMAIL_PROCESSOR.md) for complete details.

### Contact Data Sync Fix (2026-02-08)

Cross-reference analysis of Odoo, Freescout, Customers sheet, and Akdemia revealed sync inconsistencies. Fixed via `scripts/contact_data_sync_fix.py`:

- **7 not-found bounce logs** linked to correct partners (bounced email existed in Sheets but Odoo had different email)
- **MIGUEL MARIN #3663:** Added mother's email (`susanaquijada102@gmail.com`) as secondary in Odoo + Customers sheet
- **SORELIS MAITA #3669:** Flagged for manual mobile lookup (no phone in any source)
- **Perdomo duplicates:** 3 bounce logs deleted, 2 duplicate partners archived (#3612, #3676)
- **8 orphan bounces:** No match in any source, left as `not_found`

**Post-fix stats:** 37 bounce logs, 29 linked to partners, 8 orphans. Comparison script: `scripts/contact_sync_comparison.py`.

### WhatsApp API (MassivaMóvil)

- **Provider:** MassivaMóvil (`whatsapp.massivamovil.com`)
- **Config:** `/opt/odoo-dev/config/whatsapp_massiva.json` (gitignored)
- **Auth:** API secret key param (not OAuth), key name `ueipab1`
- **Primary Account:** +584248944898 (Glenda customer contact)
- **Backup Account:** +584148321963 (switch if primary flagged as SPAM)
- **Anti-spam:** Min 120s, max 140s between sends (MassivaMóvil recommended to avoid WhatsApp SPAM flag)
- **Send:** `POST /api/send/whatsapp` (multipart/form-data) - `secret`, `account`, `recipient`, `message`
- **Validate:** `GET /api/validate/whatsapp` - `secret`, `unique`, `phone`
- **Receive:** `GET /api/get/wa.received` (polling) or webhook (POST to callback URL)
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`
- **Full API docs:** OpenAPI spec at `GET /api` (requires dashboard session cookie)

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **API Key:** `sk-ant-api03-*` (stored in config file)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Use case:** AI backbone for WhatsApp bounce resolution agent (~$0.005 per conversation)
- **Status:** Active ($5 credit loaded 2026-02-07)
- **Billing:** $5 covers ~1,000 bounce conversations with Haiku 4.5

---

## AI Agent Module (ueipab_ai_agent)

**Status:** Testing | **Version:** 17.0.1.4.0 | **Installed:** 2026-02-07

Centralized AI-powered WhatsApp agent for automated customer interactions. Uses MassivaMóvil WhatsApp API + Anthropic Claude AI with pluggable "skills" for different business processes.

### Architecture

- **Skills:** Pluggable handlers for different business processes (bounce resolution, bill reminders, billing support)
- **Conversations:** Track WhatsApp exchanges with customers, linked to source records
- **Services:** Abstract models wrapping MassivaMóvil WhatsApp API and Anthropic Claude API
- **Webhook/Cron:** Receive incoming WhatsApp messages via webhook or 5-min polling cron

### Skills

| Skill Code | Name | Source Model | Max Turns | Timeout | Reminder |
|-----------|------|-------------|-----------|---------|----------|
| `bounce_resolution` | Resolucion de Rebotes | `mail.bounce.log` | 5 | 48h | 24h / 2 |
| `bill_reminder` | Recordatorio de Factura | `account.move` | 3 | 72h | 24h / 2 |
| `billing_support` | Soporte de Facturacion | `res.partner` | 4 | 24h | 24h / 2 |

### Key Models

| Model | Description |
|-------|-------------|
| `ai.agent.skill` | Skill configuration (prompt, model, limits) |
| `ai.agent.conversation` | Conversation tracking with state machine |
| `ai.agent.message` | Message log (sent + received) |
| `ai.agent.whatsapp.service` | MassivaMóvil API abstraction |
| `ai.agent.claude.service` | Anthropic API abstraction |

### Production Architecture (v1.2.0)

Scripts (`ai_agent_email_checker.py`, `daily_bounce_processor.py`) MUST run on dev server (where Freescout MySQL lives). They reach production Odoo via XML-RPC (`TARGET_ENV=production`). Config files searched in order: env var `AI_AGENT_CONFIG_DIR`, `/opt/odoo-dev/config/`, `/home/vision/ueipab17/config/`.

**Environment safeguard:** `ai_agent.active_db` parameter prevents double-processing when both environments share the same WhatsApp account. Set to the database name that should process crons (e.g., `DB_UEIPAB` for production). The other environment's crons self-skip.

### Testing Environment Status (2026-02-08)

| Setting | Value | Notes |
|---------|-------|-------|
| `ai_agent.dry_run` | `True` | Flip to `False` for live testing |
| `ai_agent.active_db` | `testing` | Crons run in this env |
| `ai_agent.credits_ok` | `True` | Kill switch (auto-managed by Credit Guard) |
| Poll WhatsApp Messages cron | `active=True` | Processes customer replies every 5 min |
| Check Conversation Timeouts cron | `active=False` | No auto-reminders, no auto-timeouts |
| Credit Guard cron | `active=True` | Checks WA + Claude credits every 30 min |
| Escalation bridge cron | Running (system) | `/etc/cron.d/ai_agent_escalation`, every 5 min, DRY_RUN=True |
| Resolution bridge cron | Running (system) | `/etc/cron.d/ai_agent_resolution`, every 5 min, DRY_RUN=True |

**Operational model:** Conversations are started **manually** via "Iniciar WhatsApp" button on bounce log records. Customer replies are processed automatically by the poll cron. Credit Guard monitors API credit levels continuously. No unsolicited outbound messages (reminders/timeouts) are sent while the timeout cron is disabled.

**Bounce logs ready:** 30 with partner + mobile, 0 active conversations. All stale test conversations cleaned up.

### Contact Schedule

Glenda only initiates contact during allowed hours (VET, GMT-4):
- Weekdays: 06:30 - 20:30
- Weekends: 09:30 - 19:00
- Cron-initiated outbound (reminders, timeouts, polls) blocked outside schedule
- Customer-initiated replies (webhook) processed anytime

### Conversation Features (v1.1.0)

**WhatsApp Reminders:** Automatic follow-ups when customer doesn't reply.
- Configurable per skill: `reminder_interval_hours` (default 24h), `max_reminders` (default 2)
- Effective total wait = (max_reminders + 1) x interval (default: 72h)
- Two tones per skill: gentle follow-up → final notice
- `reminder_count` resets on customer reply

**Freescout Email Verification Detection:** Bridge script detects email replies.
- Script: `scripts/ai_agent_email_checker.py` (cron every 15 min)
- Queries Freescout for customer replies to verification emails
- Auto-resolves conversations + triggers bounce log restore
- Sends farewell WhatsApp to customer
- Freescout post-processing: `[RESUELTO-AI]` prefix, internal note with Odoo links, close conversation

### Escalation Feature (v1.4.0)

**Off-topic request handling:** When customer asks about something outside bounce resolution (constancias, invoices, data changes), Glenda:
1. Acknowledges the request politely (visible to customer)
2. Includes `ACTION:ESCALATE:description` marker (invisible to customer)
3. Module saves `escalation_date` + `escalation_reason` on conversation
4. Conversation continues in `waiting` state (intermediate action, not terminal)

**Escalation Bridge:** `scripts/ai_agent_escalation_bridge.py`
- Queries Odoo for conversations with `escalation_date` but no Freescout ticket
- Creates Freescout support ticket via direct MySQL (unassigned, for team pickup)
- Sends WhatsApp notification to "ueipab soporte" group (`1594720028@g.us`)
- Updates Odoo with Freescout ticket number
- `DRY_RUN=True` by default, same safety pattern as other bridge scripts
- Multiple escalations in same conversation: appended with timestamps, subsequent ones add notes to existing ticket
- **Cron:** `/etc/cron.d/ai_agent_escalation` — every 5 min, logs to `scripts/logs/escalation_bridge.log`

### Resolution Bridge (v1.8.0)

**Problem:** When Glenda resolves a bounce via WhatsApp, Odoo is updated but Freescout conversations remain open and Google Sheets "Customers" tab still shows the bounced email.

**Script:** `scripts/ai_agent_resolution_bridge.py`
**Cron:** `/etc/cron.d/ai_agent_resolution` — every 5 min, logs to `scripts/logs/resolution_bridge.log`

**Flow for each resolved bounce log with Freescout conversation:**
1. Check if already processed (subject starts with `[RESUELTO-AI]`) → skip primary, but still run related cleanup
2. Check Akdemia2526 tab for bounced email
3. Update Freescout conversation:
   - **Email IN Akdemia:** Subject = `[RESUELTO-AI] Se requiere actualización de correo electrónico en Akdemia`, assign to Alejandra Lopez (user_id=6), keep Active
   - **Email NOT in Akdemia:** Subject = `[RESUELTO-AI] {original}`, status = Closed
   - Internal note with resolution summary, Odoo links
4. **Reassign DSN conversation customer:** DSN bounce conversations have `customer_email=mailer-daemon@googlemail.com` (Customer #29 "Mail Delivery Subsystem"). Bridge looks up real customer via Freescout `emails` table and reassigns the conversation to the actual parent before closing.
5. **Close related conversations:** search `threads.body` for bounced email across ALL active Freescout conversations — DSN conversations use `customer_email=mailer-daemon@googlemail.com`, so the bounced address only appears in thread body. Each related conversation gets `[RESUELTO-AI]` prefix, closed, customer reassigned (if DSN), and internal note added.
6. Update Customers tab (Google Sheets): remove bounced email from semicolon-separated list in column J

**Key details:**
- `DRY_RUN=True` by default, `--live` to apply, `--skip-sheets` to skip Google Sheets, `--id N` to target a single bounce log
- Idempotent: checks `[RESUELTO-AI]` prefix to skip already-processed conversations
- Alejandra (Freescout user_id=6): assigned when bounced email exists in Akdemia for manual platform cleanup
- Customers tab matching: column A = partner VAT, column J = email (semicolon-separated)
- Related cleanup catches all DSN Delay + Failure conversations for the same bounced email (e.g., ANALY had 6 extra besides the linked one)
- **DSN customer reassignment:** Uses Freescout `emails` table (email → customer_id) to find real customer, then updates `customer_id` + `customer_email` on conversation. Backfill: 16 conversations reassigned from "Mail Delivery Subsystem" to actual parents.

### WhatsApp Health Monitor (v1.7.0)

**Problem:** WhatsApp platform can flag sender numbers as SPAM, unlinking them for ~24h. MassivaMóvil notifies via email to Freescout.

**Solution:** Dual-layer detection + automatic failover to backup number.

**Script:** `scripts/ai_agent_wa_health_monitor.py`
**Cron:** `/etc/cron.d/ai_agent_wa_health` — every 15 min, DRY_RUN by default

**Detection Layer 1 (API):** `GET /validate/whatsapp` on active sender number. If `status != 200`, number is flagged.
**Detection Layer 2 (Freescout):** Scan inbox for subject `"¡Tu cuenta de WhatsApp ha sido desvinculada!"`.

**Failover:** Either signal → switch `ai_agent.whatsapp_account_id` + `_phone` to backup → alert soporte WA group.
**Recovery:** After 24h cooldown → validate flagged number via API → if valid, switch back + alert.

**Manual override:** `python3 ai_agent_wa_health_monitor.py --force-switch backup --live`
**Dashboard:** "Cambiar Cuenta" button under Cuenta WhatsApp section.

**Accounts:**
| | Phone | Unique ID |
|---|---|---|
| Primary | +584248944898 | `17537021528e296a067a37563370ded05f5a3bf3ec68875f083d7d0` |
| Backup | +584148321963 | `17457894218e296a067a37563370ded05f5a3bf3ec680ea1ed6c305` |

### System Parameters

| Key | Description |
|-----|-------------|
| `ai_agent.dry_run` | `True` (default) = no real API calls |
| `ai_agent.active_db` | Database name authorized to run crons (prevents double-processing) |
| `ai_agent.whatsapp_api_secret` | MassivaMóvil API secret |
| `ai_agent.whatsapp_account_id` | Active WhatsApp account unique ID (switched by health monitor) |
| `ai_agent.whatsapp_account_phone` | Active WhatsApp phone number (switched by health monitor) |
| `ai_agent.whatsapp_base_url` | MassivaMóvil API base URL |
| `ai_agent.whatsapp_send_interval` | Anti-spam interval in seconds between sends (default 120) |
| `ai_agent.whatsapp_primary_phone` | Primary sender phone |
| `ai_agent.whatsapp_primary_unique_id` | Primary MassivaMóvil unique ID |
| `ai_agent.whatsapp_backup_phone` | Backup sender phone |
| `ai_agent.whatsapp_backup_unique_id` | Backup MassivaMóvil unique ID |
| `ai_agent.whatsapp_active_account` | `primary` or `backup` (current active) |
| `ai_agent.whatsapp_flagged_phone` | Phone currently flagged (empty if none) |
| `ai_agent.whatsapp_flagged_date` | When flagging was detected |
| `ai_agent.claude_api_key` | Anthropic API key |
| `ai_agent.claude_model` | Default Claude model |
| `ai_agent.credits_ok` | Kill switch — `False` blocks all outbound API calls |
| `ai_agent.wa_sends_threshold` | Min remaining WA sends before alert (default 50) |
| `ai_agent.claude_spend_limit_usd` | Max cumulative USD spend before alert (default 4.50) |
| `ai_agent.claude_input_rate` | $/token for input (default 0.000001) |
| `ai_agent.claude_output_rate` | $/token for output (default 0.000005) |

### Menu Location

`Contactos > AI Agent > Panel de Control / Conversaciones / Configuracion de Skills`

### Integration with Bounce Log

- `mail.bounce.log` extended with `ai_conversation_id` field
- "Iniciar WhatsApp" button on bounce log form → opens wizard → creates conversation
- Conversation resolution triggers bounce log actions (apply new email, restore original)

See [Full Documentation](documentation/AI_AGENT_MODULE.md) for complete details.

---

## Akdemia Data Pipeline

**Status:** In Progress | **Type:** Script + Cron

Daily automated extraction of student/parent data from Akdemia student management system, with email change detection to auto-resolve AI agent conversations.

### Existing Infrastructure (odoo_api_bridge)

| Component | Location | Status |
|-----------|----------|--------|
| Akdemia Scraper | `/var/www/dev/odoo_api_bridge/customer_matching/integrations/akdemia_scraper.py` | Playwright-based, working |
| Cron Wrapper | `/var/www/dev/odoo_api_bridge/scripts/customer_matching_wrapper.sh` | Configured, daily 6AM VET |
| Cron Job | `/etc/cron.d/customer_matching` | Active |
| Daily Script | `scripts/customer_matching_daily.py` | **NOT YET CREATED** |
| Downloads Dir | `/var/www/dev/odoo_api_bridge/akdemia_downloads/` | Empty (last run Sep 2025) |
| Historical XLS | `customer_matching/data/xls_uploads/2025/09/` | 10+ files from Sep 2025 |

### Akdemia Scraper Details

- **Platform:** `https://edge.akdemia.com` (Playwright headless Chromium)
- **Credentials:** `gustavo.perdomo@ueipab.edu.ve` (hardcoded in scraper)
- **Output:** Excel file `lista_de_estudiantes{date}-{hash}.xls`
- **Data:** Student name, cedula, grade, section, parent name/email/phone, payment status, balance
- **Google Sheets target:** Currently PVT2526, needs to also update Akdemia2526

### Akdemia2526 Sheet Structure

- **Spreadsheet:** `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA` (Customer Database Odoo)
- **Tab:** `Akdemia2526` (227 rows, headers in row 3)
- **Key email columns:** AU = `Correo electrónico de Representante` (parent 1), BX = same (parent 2)
- **Key name columns:** AB/AE = parent 1 name/surname, BE/BH = parent 2 name/surname
- **Key cedula columns:** AH = parent 1 cedula, BK = parent 2 cedula
- **Data starts:** Row 4 (rows 1-2 are school name/year)

### Akdemia Email Sync Script (Implemented 2026-02-08)

**Script:** `scripts/akdemia_email_sync.py`
**Safety:** `DRY_RUN=True`, `TARGET_ENV=testing` by default. Use `--live` to apply.

Daily pipeline after Akdemia scrape — closes the loop when tech support updates an email in Akdemia without Glenda knowing:

1. **Phase 1:** Get XLS (`--file` manual, or latest from downloads/historical dir)
2. **Phase 2:** Parse XLS → parent email map by cedula (287 parents, 3 parent sets per student)
3. **Phase 3:** Compare with unresolved `mail.bounce.log` records (match `partner.vat` → Akdemia cedula)
4. **Phase 4:** Auto-resolve: `action_apply_new_email()` on bounce log + `action_resolve()` on AI conversation + update `mailing.contact` by email match
5. **Phase 5:** Update Akdemia2526 Google Sheet tab with fresh XLS data

**Dry run results (Sep 2025 XLS):** 14 email changes detected (PDVSA domains → gmail/hotmail)

**Usage:**
```bash
python3 scripts/akdemia_email_sync.py                    # dry run
python3 scripts/akdemia_email_sync.py --live              # apply changes
python3 scripts/akdemia_email_sync.py --file /path.xls    # specific file
python3 scripts/akdemia_email_sync.py --skip-sheets       # skip Google Sheets
```

**Bounce log resolution paths (4 total):**
- PATH A: Glenda WhatsApp → customer gives new email
- PATH B: Email verification checker → customer replies to verification email
- PATH C: Akdemia sync → tech support updated email in Akdemia
- PATH D: Manual → staff clicks "Restaurar" or "Aplicar Nuevo" in Odoo
- PATH E: Escalation → customer asks off-topic, Freescout ticket created, conversation continues

### Mailing Contact Sync (v1.2.0)

**Gap discovered 2026-02-08:** Bounce resolution updated `res.partner.email` but NOT `mailing.contact`. Production has 350 mailing contacts across 3 lists (Toda la comunidad=239, Grupo1=110, Newsletter=1). 28 of 37 bounced emails exist in `mailing.contact` — campaigns would re-bounce to stale emails.

**Fix (3 parts):**
- **Part A (Module):** `ueipab_bounce_log` `_resolve_record()` now searches `mailing.contact` by bounced email and updates/removes as needed
- **Part B (Script):** `akdemia_email_sync.py` also updates `mailing.contact` via XML-RPC during resolution
- **Part C (Testing sync):** Import production mailing lists/contacts into testing for parity

**CRITICAL:** Never touch `todalacomunidad@ueipab.edu.ve` — that email holds all `@ueipab.edu.ve` institutional users, not parents.

### Production Mailing Lists

| List | ID | Contacts | Purpose |
|------|----|----------|---------|
| Toda la comunidad | 2 | 239 | All parent emails for school campaigns |
| Grupo1 | 3 | 110 | Subset of parents (specific grade group) |
| Newsletter | 1 | 1 | General newsletter |

---

## Documentation Index

### Core Systems
- [V2 Implementation](documentation/LIQUIDATION_V2_IMPLEMENTATION.md)
- [V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)
- [V2 Payroll Implementation](documentation/V2_PAYROLL_IMPLEMENTATION.md)

### Reports
- [Payroll Disbursement](documentation/PAYROLL_DISBURSEMENT_REPORT.md)
- [Prestaciones Interest](documentation/PRESTACIONES_INTEREST_REPORT.md)
- [Relacion Breakdown](documentation/RELACION_BREAKDOWN_REPORT.md)
- [Finiquito Report](documentation/FINIQUITO_REPORT.md)

### Features
- [Payslip Acknowledgment System](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md)
- [Batch Email Wizard](documentation/BATCH_EMAIL_WIZARD.md)
- [Email Templates](documentation/EMAIL_TEMPLATES.md)
- [Cybrosys Module Modifications](documentation/CYBROSYS_MODULE_MODIFICATIONS.md)

### Infrastructure
- [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md)
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [Email Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md)
- [AI Agent Module](documentation/AI_AGENT_MODULE.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)

### Known Issues
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
