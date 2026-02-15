# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-02-15

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
| 8 | Comprobante de Pago Compacto | Production | `ueipab_payroll_enhancements` | [Docs](documentation/COMPROBANTE_DE_PAGO.md) |
| 9 | Acuerdo Finiquito Laboral | Production | `ueipab_payroll_enhancements` | [Docs](documentation/FINIQUITO_REPORT.md) |
| 10 | AR-I Portal | Testing | `ueipab_ari_portal` | - |
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](documentation/RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | - |
| 15 | Batch Email Progress Wizard | Production | `ueipab_payroll_enhancements` | [Docs](documentation/BATCH_EMAIL_WIZARD.md) |
| 16 | HRMS Dashboard Ack Widget | Production | `ueipab_hrms_dashboard_ack` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 17 | Cybrosys Module Refactoring | Planned | Multiple | [Docs](documentation/CYBROSYS_MODULE_MODIFICATIONS.md) |
| 18 | Liquidacion Estimation Mode | Production | `ueipab_payroll_enhancements` | - |
| 19 | Payslip Ack Reminder System | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 20 | V2 Payroll Accounting Config | Production | Database config | - |
| 21 | Invoice Currency Rate Bug | Documented | `tdv_multi_currency_account` | [Docs](documentation/INVOICE_CURRENCY_RATE_BUG.md) |
| 22 | Aguinaldos Disbursement Report | Production | `ueipab_payroll_enhancements` | - |
| 23 | Advance Payment System | Production | `ueipab_payroll_enhancements` | [Docs](documentation/ADVANCE_PAYMENT_SYSTEM.md) |
| 24 | WebSocket/Nginx Fix | Production | Infrastructure | [Docs](documentation/WEBSOCKET_NGINX_FIX.md) |
| 25 | Email Bounce Processor | Testing | Script + `ueipab_bounce_log` | [Docs](documentation/BOUNCE_EMAIL_PROCESSOR.md) |
| 26 | AI Agent (WhatsApp + Claude) | Testing | `ueipab_ai_agent` | [Docs](documentation/AI_AGENT_MODULE.md) |
| 27 | Akdemia Data Pipeline | Testing | Script + Cron | [Docs](documentation/AKDEMIA_DATA_PIPELINE.md) |
| 28 | WhatsApp Health Monitor | Testing | Script + `ueipab_ai_agent` | [Docs](documentation/AI_AGENT_MODULE.md) |
| 29 | Resolution Bridge | Testing | Script + Cron | [Docs](documentation/AI_AGENT_MODULE.md) |
| 30 | Freescout API Migration | Planned | Scripts | [Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md) |

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
| Advance Payment | Partial salary disbursement with % multiplier ([details](documentation/ADVANCE_PAYMENT_SYSTEM.md)) |
| Remainder Payment | Linked to original advance batch for reconciliation |

---

## Module Versions

### Testing Environment

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | 17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | 17.0.1.52.2 | 2026-02-13 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_bounce_log | 17.0.1.4.0 | 2026-02-14 |
| ueipab_ai_agent | 17.0.1.13.0 | 2026-02-14 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.52.2 | Current (synced 2026-02-13) |
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

Automated detection and cleanup of bounced emails from Freescout (READ-ONLY source). See [Full Documentation](documentation/BOUNCE_EMAIL_PROCESSOR.md).

**Key components:**
- **Script:** `scripts/daily_bounce_processor.py` (DRY_RUN default, `--live` to apply)
- **Module:** `ueipab_bounce_log` v17.0.1.4.0 — `Contacts > Bounce Log`
- **3-Tier Logic:** CLEAN (permanent failure → auto-remove), FLAG (temporary → review), NOT FOUND (log only)
- **Cron:** `/etc/cron.d/ai_agent_bounce_processor` — daily 05:00 VET, LIVE, TARGET_ENV=testing

### WhatsApp API (MassivaMóvil)

- **Provider:** MassivaMóvil (`whatsapp.massivamovil.com`)
- **Config:** `/opt/odoo-dev/config/whatsapp_massiva.json` (gitignored)
- **Auth:** API secret key param (not OAuth), key name `ueipab1`
- **Primary Account:** +584248944898 | **Backup:** +584148321963
- **Anti-spam:** Min 120s between sends
- **Send:** `POST /api/send/whatsapp` | **Validate:** `GET /api/validate/whatsapp` | **Receive:** `GET /api/get/wa.received`
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Use case:** AI backbone for WhatsApp bounce resolution (~$0.005 per conversation)

---

## AI Agent Module (ueipab_ai_agent)

**Status:** Testing | **Version:** 17.0.1.13.0 | **Installed:** 2026-02-07

Centralized AI-powered WhatsApp agent for automated customer interactions. Uses MassivaMóvil WhatsApp API + Anthropic Claude AI with pluggable "skills". See [Full Documentation](documentation/AI_AGENT_MODULE.md).

### Architecture & Skills

| Skill Code | Name | Source Model | Max Turns |
|-----------|------|-------------|-----------|
| `bounce_resolution` | Resolucion de Rebotes | `mail.bounce.log` | 5 |
| `bill_reminder` | Recordatorio de Factura | `account.move` | 3 |
| `billing_support` | Soporte de Facturacion | `res.partner` | 4 |

**Key models:** `ai.agent.skill`, `ai.agent.conversation`, `ai.agent.message`, `ai.agent.whatsapp.service`, `ai.agent.claude.service`

### Key Features

- **Conversation lifecycle:** draft → active → waiting → resolved/timeout/failed
- **WhatsApp reminders:** 24h interval, 2 max, auto-timeout after 72h
- **Escalation:** `ACTION:ESCALATE:desc` marker → Freescout ticket via bridge script
- **Image support (v1.13.0):** Multimodal — Glenda sees customer screenshots via Claude vision
- **Re-trigger:** `ACTION:ALTERNATIVE_PHONE:04XXX` → pre-fills wizard with new number
- **Email verification:** `ACTION:VERIFY_EMAIL:email` → sends verification email
- **Family email context:** Akdemia data prevents duplicate email proposals
- **Credit Guard:** Kill switch at `ai_agent.credits_ok`, checks WA + Claude spend every 30 min
- **Health Monitor:** Dual-layer SPAM detection + auto-failover to backup number

### Testing Environment Status (2026-02-14)

| Setting | Value |
|---------|-------|
| `ai_agent.dry_run` | `False` (LIVE) |
| `ai_agent.active_db` | `testing` |
| `ai_agent.credits_ok` | `True` |
| Poll cron | active, 5 min |
| Timeout cron | active, 1 hour |
| Credit Guard | active, 30 min |
| Archive Attachments | active, 2 hours |

**System crons (host-level):** escalation (5 min, LIVE), resolution (5 min, LIVE), email checker (15 min, LIVE), bounce processor (daily 05:00, LIVE), WA health (15 min, LIVE), Akdemia pipeline (daily 06:00, LIVE). All 6 system crons are LIVE as of 2026-02-14.

**Contact schedule (VET):** Weekdays 06:30-20:30, Weekends 09:30-19:00.

### Production Migration Checklist

See [Full Checklist](documentation/AI_AGENT_MODULE.md). **BLOCKERs:** bounce_log module in prod, hardcoded API creds in bridge scripts, webhook callback URL, Freescout MySQL access from dev server.

---

## Akdemia Data Pipeline

**Status:** Testing | **Revived:** 2026-02-11

Daily Akdemia scrape → email sync → auto-resolve bounce logs. See [Full Documentation](documentation/AKDEMIA_DATA_PIPELINE.md).

**Key components:**
- **Scraper:** `/var/www/dev/odoo_api_bridge/customer_matching/integrations/akdemia_scraper.py` (Playwright)
- **Orchestrator:** `/var/www/dev/odoo_api_bridge/scripts/customer_matching_daily.py`
- **Email sync:** `scripts/akdemia_email_sync.py` (DRY_RUN default, `--live` to apply)
- **Cron:** `/etc/cron.d/customer_matching` — daily 06:00 VET
- **Sheet:** `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`, tab `Akdemia2526`

**6 bounce resolution paths:** A=Glenda WhatsApp, B=Email verification, C=Akdemia sync, D=Manual, E=Escalation, F=Akdemia auto-resolve.

**Resolution Bridge phases:** 1=Connect, 2a=Refresh in_akdemia, 2b=Auto-confirm akdemia_pending, 2c=Auto-resolve from Akdemia (PATH F), 3=Query resolved BLs, 4=Process BLs (Freescout + Sheets), **5=Sync Customers family emails** (Akdemia → Sheet col J + Odoo partner + MC).

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
- [Advance Payment System](documentation/ADVANCE_PAYMENT_SYSTEM.md)
- [Comprobante de Pago](documentation/COMPROBANTE_DE_PAGO.md)
- [Payslip Acknowledgment System](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md)
- [Batch Email Wizard](documentation/BATCH_EMAIL_WIZARD.md)
- [Email Templates](documentation/EMAIL_TEMPLATES.md)
- [Cybrosys Module Modifications](documentation/CYBROSYS_MODULE_MODIFICATIONS.md)

### AI Agent & Bounce Processing
- [AI Agent Module](documentation/AI_AGENT_MODULE.md)
- [Email Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md)
- [Akdemia Data Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md)
- [Glenda Overview](documentation/GLENDA_AI_AGENT_OVERVIEW.md)

### Infrastructure
- [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md)
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [WebSocket/Nginx Fix](documentation/WEBSOCKET_NGINX_FIX.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)

### Known Issues
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)
- **Contact Data Cleanup (2026-02-15):** All Representante contacts (317/317 both envs) fully synchronized. Fixes applied: (1) Country state remapped from Kenya IDs to Anzoátegui (2171), (2) Emails synced testing→production (22 partners + 23 MCs, 0 diffs verified), (3) Empty states filled, (4) 2 missing contacts created in testing (CHENIANA NOGALES, CARLOS SANCHEZ), (5) ZIP=6050 for all El Tigre contacts (288/288), (6) company_type=Individual for all Representante (317/317), (7) City names normalized ("EL TIGRE"/"EL TGRE"→"El Tigre"). Canonical VE states: IDs 2170-2193 (V01-V24).

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
