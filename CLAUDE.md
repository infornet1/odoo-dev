# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-05-17 (v7)

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
| 25 | Email Bounce Processor | Production | Script + `ueipab_bounce_log` | [Docs](documentation/BOUNCE_EMAIL_PROCESSOR.md) |
| 26 | AI Agent (WhatsApp + Claude) | Production | `ueipab_ai_agent` | [Docs](documentation/AI_AGENT_MODULE.md) |
| 27 | Akdemia Data Pipeline | Production | Script + Cron | [Docs](documentation/AKDEMIA_DATA_PIPELINE.md) |
| 28 | WhatsApp Health Monitor | Production | Script + `ueipab_ai_agent` | [Docs](documentation/AI_AGENT_MODULE.md) |
| 29 | Resolution Bridge | Production | Script + Cron | [Docs](documentation/AI_AGENT_MODULE.md) |
| 30 | Freescout API Migration | Production (Phase 2+3) | Scripts | [Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md) |
| 31 | HR Data Collection (Glenda) | Production | `ueipab_ai_agent` + `ueipab_hr_employee` | [Docs](documentation/GLENDA_HR_DATA_COLLECTION.md) |
| 32 | Payslip Ack Confirmation Email | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 33 | Payroll Requisition Estimation Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md) |
| 34 | Adelanto de Prestaciones Sociales Email | Production | `ueipab_payroll_enhancements` | [Changelog](documentation/CHANGELOG.md) |
| 35 | Payslip Ack Reminder via Glenda (WA) | Production | `ueipab_ai_agent` | [Docs](documentation/PAYSLIP_ACK_REMINDER_GLENDA.md) |
| 36 | HR Salary Advance / Loan System | Testing | `ueipab_payroll_enhancements` + `ohrms_loan` + `ohrms_loan_accounting` | [Docs](documentation/HR_SALARY_ADVANCE_LOAN.md) |
| 37 | Attendance Biweekly Email Report | Production | `ueipab_attendance_report` | [Plan](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) |
| 38 | Bono Día de las Madres 2026 | Production | `ueipab_payroll_enhancements` | [Docs](documentation/BONO_MADRES_2026.md) |
| 39 | Control Asistencia → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CONTROL_ASISTENCIA_BRIDGE.md) |
| 40 | Mikrotik Hotspot → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CHANGELOG.md) |
| 41 | Gestión Control Asistencia — Guía Visual | Production | `mail.template` + Stories PNG | [Docs](documentation/CHANGELOG.md) |
| 42 | Notice Acknowledgment System | Production | `ueipab_attendance_report` | [Docs](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md) |
| 43 | Glenda Calibration Programme | Production | `ueipab_attendance_report` + `ueipab_ai_agent` | [Docs](documentation/GLENDA_CALIBRATION_PROGRAMME.md) |
| 44 | Glenda BCV Rate Context | Production | `ueipab_ai_agent` + Script + Cron | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 45 | Glenda Invoice Balance Query | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 46 | Glenda Daily Executive Digest | Production | Script + Cron | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 47 | Employee Private Info Request | Production | `ueipab_hr_employee` | [Docs](documentation/EMPLOYEE_INFO_REQUEST.md) |
| 48 | Liquidación V2 Forecast | Production | `ueipab_payroll_enhancements` | Nómina→Reports→Pronóstico Liquidación V2; PDF + Excel |
| 49 | PDVSA Continuity Campaign | Testing | `ueipab_attendance_report` | [Docs](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) — deadline 08-Jun-2026 |
| 50 | Representante Continuity Campaign | Pending (letter not ready) | `ueipab_attendance_report` | [Docs](documentation/REPRESENTANTE_CONTINUITY_CAMPAIGN.md) |
| 51 | Glenda Auto Draft Payment (WA) | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 52 | Pagos@ Email Receipt Processor | Production | Script | `scripts/pagos_receipt_processor.py` — [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 53 | WA Invoice Reminder | Production | Script + Wizard | [Plan](documentation/WA_INVOICE_REMINDER_PLAN.md) |
| 54 | Glenda OdooBot Bridge | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 55 | Glenda Silent Timeout + Quiet Hours | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 56 | DMARC Report Processor | Production | Script + Cron | `scripts/dmarc_report_processor.py` — [CEO](documentation/CEO_COMMAND_CENTER.md) |
| 57 | Glenda Telegram Channel | Production | `ueipab_ai_agent` | [Docs](documentation/GLENDA_TELEGRAM_CHANNEL.md) — `@GlendaUeipabBot`; webhook `odoo.ueipab.edu.ve`; deep-link `EMP_{id}`; WA invite on 1st reply |

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

**Quincena Calculation:** All V2 salary rules use fixed `monthly / 2.0` for quincena amounts (fixed 2026-02-25). Previously used `period_days / 30.0` which caused February 2nd quincena to pay only 13/30 instead of 15/30. AGUINALDOS rule retained its own fixed-0.5 logic separately.

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

### Odoo Base Container

| Environment | Image | Build | Odoo Commit | Updated |
|-------------|-------|-------|-------------|---------|
| Testing | `odoo:17.0` | `17.0-20260504` | `d66bb0d7` | 2026-05-10 |
| Production | `odoo:17.0` | `17.0-20260504` | `d66bb0d7` | 2026-05-10 |

### Testing Environment

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | 17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | 17.0.1.70.0 | 2026-05-16 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_bounce_log | 17.0.1.4.0 | 2026-02-14 |
| ueipab_ai_agent | 17.0.1.45.0 | 2026-05-17 |
| ueipab_attendance_report | 17.0.1.6.0 | 2026-05-11 |
| ueipab_hr_employee | 17.0.1.3.0 | 2026-05-13 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.70.0 | Deployed 2026-05-16 |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | 17.0.1.0.2 | Installed |
| ueipab_attendance_report | 17.0.1.6.0 | Deployed 2026-05-13 — **Pending:** PDVSA bulk send (71 partners), [runbook](documentation/PDVSA_DEPLOY_FRIDAY_20260515.md) Steps 6–8 |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | Installed |
| ueipab_hr_employee | 17.0.1.3.0 | Deployed 2026-05-13 |
| ueipab_bounce_log | 17.0.1.4.0 | Deployed 2026-05-10 |
| ueipab_ai_agent | 17.0.1.45.0 | Deployed 2026-05-17 — Telegram channel, DMARC, CEO supervision, channel badge UI, farewell detection fix |

---

## Key Technical Patterns

### Odoo safe_eval (Salary Rules)
```python
# FORBIDDEN: imports, hasattr
# ALLOWED: Direct arithmetic, try/except
```

**`payslip` in salary rule context is a `Payslips(BrowsableObject)` wrapper — NOT the ORM record.**
- `payslip.dict` → actual `hr.payslip` record (use this to access One2many fields)
- `payslip.input_line_ids` → goes through `BrowsableObject.__getattr__` → returns `0.0` (WRONG)
- Always use `payslip.dict.input_line_ids` to iterate input lines in salary rules

**Conditional salary rules referenced in NET formulas must use `condition_select='none'`.**
- If condition is `python` and evaluates to `False`, the rule is skipped and its code is never added to `localdict`
- Any NET/GROSS formula that references that code by name will raise `NameError` → "Wrong python code defined"
- Fix: set `condition_select='none'` + let the amount formula return `0.0` when the rule shouldn't fire
- The payslip report template already filters `total_in_ves > 0`, so zero-amount lines are invisible

### Odoo 17 View Syntax
```xml
<!-- OLD --> <div attrs="{'invisible': [('field', '=', 0)]}">
<!-- NEW --> <div invisible="field == 0">
```

### Report Development
- Use `web.basic_layout` for UTF-8 support
- Model naming: `report.<module>.<template_id>` (exact match)
- TransientModel wizards need security access rules

### Notice Acknowledgment System (hr.notice.acknowledgment)

See [Docs](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md). Model in `ueipab_attendance_report`.
- **Route:** `/notice-ack/<token>` (`auth='public'`); generic keys = one-click ACK; `_WA_FORM_KEYS` (e.g. `glenda_calibracion_v1`) → WA form → POST `/glenda-calibracion/<token>`
- **ACK button:** stored via **SQL** to bypass ORM sanitizer; CC `recursoshumanos@ueipab.edu.ve` on every send
- **IDs:** Testing attendance_guide=84, prod=58; calibration template testing=86

### Freescout REST API (api_key + hybrid pattern)

See [FREESCOUT_API_MIGRATION_PLAN.md](documentation/FREESCOUT_API_MIGRATION_PLAN.md) for full reference.
- **Config:** `/opt/odoo-dev/config/freescout_api.json` — `api_url`, `api_key`, `webhook_secret`
- **Auth:** `X-FreeScout-API-Key` header; Conversation ID = DB primary key, NOT display number
- **`PUT /api/conversations/{id}`** — status must be **string**; `byUser` (int) **required** on status changes
- **`POST /api/conversations/{id}/threads`** — note: `{"type":"note","text":"<html>","user":<int>}`; `user` required
- **Hybrid:** API for writes; SQL for reads + `threads.body` search

### Telegram Channel (ai.agent.telegram.service)

See [GLENDA_TELEGRAM_CHANNEL.md](documentation/GLENDA_TELEGRAM_CHANNEL.md) for full deployment docs.

**Critical Odoo 17 rename:** PostgreSQL tables are `discuss_channel` / `discuss_channel_member` (not `mail_channel`). Any raw SQL in `_notify_ceo_discuss()` or similar must use the new names. ORM model names are `discuss.channel` / `discuss.channel.member`.

**Webhook cursor abort pattern:** `_notify_ceo_discuss()` raw SQL failure inside a webhook request aborts the PostgreSQL cursor via uncaught exception (Python try/except catches it but PG stays aborted → all subsequent queries fail). Fix: wrap all CEO notification calls with `with self.env.cr.savepoint():` so failures roll back to savepoint only.

**Token lookup in webhook context:** `ir.config_parameter` `@ormcache` can throw `KeyError` mid-transaction after a `create()`. `_token()` in `ai_agent_telegram_service.py` has a direct SQL fallback: `env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", [key])`.

**`address_home_id` not searchable:** In Odoo 17 HR, `hr.employee.address_home_id` is group-restricted and cannot be used in ORM search domains. Use `user_id.partner_id` only for partner→employee lookups.

**No anti-spam on Telegram:** `_send_to_user()` skips `whatsapp_service._throttle_send()` entirely for `channel='telegram'`. Replies are instant (only Claude latency ~1–5s).

**Monitoring URL:** `https://odoo.ueipab.edu.ve/web#action=830&cids=1&menu_id=569` → filter by Canal=Telegram; group by Canal available.

### Glenda Technical Patterns

See [GLENDA_TECHNICAL_PATTERNS.md](documentation/GLENDA_TECHNICAL_PATTERNS.md) for full reference on: Silent Timeout/Quiet Hours, OdooBot Bridge (Discuss), Auto Draft Payment / Journal Map, BCV Rate Context, Invoice Balance Query, Daily Executive Digest, Quotation Engine & Enrollment info.

### WA & Email Invoice Reminder

See [WA_INVOICE_REMINDER_PLAN.md](documentation/WA_INVOICE_REMINDER_PLAN.md) for full technical reference.
- **Wizard:** Accounting → Customers → Recordatorio de Saldo; Tags REP=25 / PDVSA=26 / VIP=30 (excluded)
- **WA cron:** weekdays 07:00 VET; state file `scripts/wa_invoice_reminder_state.json`

### CEO Command Center (wa_monitor)

See [CEO_COMMAND_CENTER.md](documentation/CEO_COMMAND_CENTER.md) for full reference.
- Params: `wa_monitor.ceo_email` / `wa_monitor.ceo_phone` / `wa_monitor.tertiary_notified_ids`
- **OdooBot DM** = primary (no throttle); **WA backup** = 120s anti-spam throttle

### DMARC Report Processor

- **Script:** `scripts/dmarc_report_processor.py` — runs live daily
- **Cron:** `/etc/cron.d/dmarc_processor` — 10:30 UTC daily
- **Source:** FreeScout `finanzas@` mailbox (mailbox_id=5); finds active conversations whose subject matches `Report domain: ueipab.edu.ve*`
- **Flow:** parse ZIP/GZ XML attachments → classify IPs → post HTML note to each conversation → close conversation → send digest email → OdooBot DM alert (critical only)
- **IP classes:** `good` (Google Workspace + UEIPAB server) / `third_party` (known misaligned senders, e.g. Akdemia SendGrid `50.31.44.87`) / `unknown`
- **Alert threshold:** only `unknown` IPs where `dkim=pass OR spf=pass` trigger `⚠️` alert + OdooBot DM. Unknown IPs that failed auth but were delivered anyway by the receiving MTA (disposition=none override) show as `🔍` — informational, not alarming.
- **DKIM:** only `google` selector published for `ueipab.edu.ve` (Google Workspace). No other authorized signers.
- **Akdemia note:** `em.akdemia.com` (SendGrid subdomain, PTR `o1.em.akdemia.com`) sends with `From: *@ueipab.edu.ve` but MAIL FROM `em.akdemia.com` → DMARC misalign, blocked. Expected and classified as `third_party`.
- **SPF:** currently `~all` (softfail); planned upgrade to `-all` ~2026-05-27 once delivery confirmed stable.

### mail.template body_html — multilingual JSONB (critical)

See [EMAIL_TEMPLATES.md](documentation/EMAIL_TEMPLATES.md) for full details and Adelanto template IDs.
- Always write via **direct SQL** updating **both** `en_US` and `es_VE` keys — ORM only updates current lang
- `UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s` with `json.dumps({'en_US': body, 'es_VE': body})`
- Use QWeb `<t t-out="..."/>` syntax — Jinja2 `{{ }}` does NOT work with `render_engine='qweb'`

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

See [Full Documentation](documentation/BOUNCE_EMAIL_PROCESSOR.md).
- **Script:** `scripts/daily_bounce_processor.py` (DRY_RUN default, `--live` to apply)
- **Cron:** `/etc/cron.d/ai_agent_bounce_processor` — daily 05:00 VET, LIVE, TARGET_ENV=testing

### WhatsApp API (MassivaMóvil)

- **Provider:** MassivaMóvil (`whatsapp.massivamovil.com`)
- **Config:** `/opt/odoo-dev/config/whatsapp_massiva.json` (gitignored)
- **Auth:** API secret key param (not OAuth), key name `ueipab1`
- **Primary Account (dedicated):** +584148321989 | **Backup:** +584248944898 | **Tertiary (emergency):** +584148321963
- **Anti-spam:** Min 120s between sends
- **Send:** `POST /api/send/whatsapp` | **Validate:** `GET /api/validate/whatsapp` | **Receive:** `GET /api/get/wa.received`
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Use case:** AI backbone for WhatsApp bounce resolution (~$0.005 per conversation)

---

## AI Agent Module (ueipab_ai_agent)

See [Full Documentation](documentation/AI_AGENT_MODULE.md) and [Glenda Technical Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md).

### Architecture & Skills

| Skill Code | Name | Source Model | Max Turns | 24/7 |
|-----------|------|-------------|-----------|------|
| `bounce_resolution` | Resolucion de Rebotes | `mail.bounce.log` | 5 | No |
| `bill_reminder` | Recordatorio de Factura | `account.move` | 3 | No |
| `billing_support` | Soporte de Facturacion | `res.partner` | 4 | No |
| `hr_data_collection` | Recoleccion de Datos HR | `hr.data.collection.request` | 30 | No |
| `general_inquiry` | Consulta General | *(inbound)* | 10 | **Yes** |

**Key models:** `ai.agent.skill`, `ai.agent.conversation`, `ai.agent.message`, `ai.agent.whatsapp.service`, `ai.agent.telegram.service`, `ai.agent.claude.service`

### Channels

| Channel | Entry point | Anti-spam | Real-time |
|---------|------------|-----------|-----------|
| WhatsApp | `_cron_poll_messages()` (5 min cron) | 120s between sends | No |
| Telegram | `telegram_webhook.py` POST `/ai-agent/telegram/webhook` | None | **Yes** |
| OdooBot/Discuss | `mail_bot_glenda.py` `_get_answer()` | None | Yes |

**`_send_to_user(text)`** — channel dispatcher on `ai.agent.conversation`; replaces all 7 direct `wa_service.send_message()` callsites. Returns WA message_id or 0 for Telegram.

**`channel` field** — `Selection([('whatsapp','WhatsApp'),('telegram','Telegram')])` on `ai.agent.conversation`. Default `whatsapp`. Telegram convs have `phone=''` and `telegram_chat_id` set.

### Key Features

- **Conversation lifecycle:** draft → active → waiting → resolved/timeout/failed
- **WhatsApp reminders:** 24h interval, 2 max, auto-timeout after 72h
- **Telegram:** `@GlendaUeipabBot` — webhook instantáneo, sin throttle, sin ventana 24h, gratis
- **Telegram deep-link:** `t.me/GlendaUeipabBot?start=EMP_{emp_id}` → auto-identifica empleado; handler `_handle_telegram_employee_start()`
- **WA→Telegram invite:** first WA general_inquiry reply appends Telegram bot link; toggle `ai_agent.telegram_invite_enabled`
- **Escalation:** `ACTION:ESCALATE:desc` → Freescout ticket via bridge script
- **Image support:** Multimodal — Glenda sees screenshots (WA: MassivaMóvil URL; Telegram: `file_id → get_file_url()`)
- **Re-trigger:** `ACTION:ALTERNATIVE_PHONE:04XXX` → pre-fills wizard with new number
- **Email verification:** `ACTION:VERIFY_EMAIL:email` → sends verification email
- **Credit Guard:** Kill switch `ai_agent.credits_ok`, checks WA + Claude spend every 30 min
- **Health Monitor:** Dual-layer SPAM detection + auto-failover to backup number
- **General Inquiry:** Handles unsolicited inbound (WA + Telegram) — identifies contact, routes to `pagos@` or `soporte@`
- **Flyer/Audio:** **⚠️ WA only** — skipped on Telegram (`channel != 'whatsapp'` guard in `_send_flyer()`)
- **Farewell:** `resolved` conv → new conv allowed within 24h; `timeout`/`failed` → blocked
- **Calibration:** WA + Telegram conversations both count toward bonus; feedback linked via `user_id.partner_id`

### WA Poll Cron — Account Filter Note

As of 2026-03-30, primary switched to dedicated number +584148321989. Poll cron temporarily uses `account_id=None` (all accounts) to catch replies to the old number. **TODO:** restore `account_id=primary_account_id` once pre-switch conversations drain.

### Environment Status

**Production (2026-05-17):** `dry_run=False`, `active_db=DB_UEIPAB`, v44.9. WA poll 5min active. Telegram webhook live on `odoo.ueipab.edu.ve`. Contact schedule VET: Weekdays 06:30-20:30, Weekends/holidays 09:30-19:00. `general_inquiry` exempt (24/7).

**Testing:** `dry_run=False`, `active_db=DB_UEIPAB` (locked — crons self-skip). Telegram webhook on `dev.ueipab.edu.ve` (switches if you re-run `set_webhook`).

**Telegram kill switch:** `ai_agent.telegram_enabled = False` in ir.config_parameter → stops all Telegram immediately.

**HR Loan Migration:** Ready — checklist in [HR_SALARY_ADVANCE_LOAN.md](documentation/HR_SALARY_ADVANCE_LOAN.md).

---

## Akdemia Data Pipeline

See [Full Documentation](documentation/AKDEMIA_DATA_PIPELINE.md).
- **Scraper:** `/var/www/dev/odoo_api_bridge/customer_matching/integrations/akdemia_scraper.py` (Playwright)
- **Cron:** `/etc/cron.d/customer_matching` — daily 06:00 VET
- **Resolution Bridge phases:** 2a=refresh in_akdemia, 2b=auto-confirm akdemia_pending, 2c=auto-resolve (PATH F), 3=query, 4=process (Freescout + Sheets), 5=sync Customers family emails

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

### Ad-hoc Queries
- [QueryRepresentantePDVSAFalseTagCheck](documentation/QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) — Receivables report for Representante PDVSA customers segmented by fiscal_check flag
- [Decreto Salario Mínimo Mayo 2026](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md) — LUIS RODRIGUEZ & NIDYA LIRA below $240 threshold

### Planned / Testing Reports
- [Payroll Requisition Estimation Report](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md)

### Features
- [Advance Payment System](documentation/ADVANCE_PAYMENT_SYSTEM.md)
- [Adelanto Prestaciones Payment Receipt Ack](documentation/ADELANTO_PRESTACIONES_PAYMENT_RECEIPT_ACK.md)
- [Comprobante de Pago](documentation/COMPROBANTE_DE_PAGO.md)
- [Payslip Acknowledgment System](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md)
- [Payslip Ack Status Report](documentation/PAYSLIP_ACK_STATUS_REPORT.md)
- [Batch Email Wizard](documentation/BATCH_EMAIL_WIZARD.md)
- [Email Templates](documentation/EMAIL_TEMPLATES.md)
- [Cybrosys Module Modifications](documentation/CYBROSYS_MODULE_MODIFICATIONS.md)

### AI Agent & Glenda
- [AI Agent Module](documentation/AI_AGENT_MODULE.md)
- [Glenda Telegram Channel](documentation/GLENDA_TELEGRAM_CHANNEL.md) — `@GlendaUeipabBot`; Fase 1+2 live; announcement script; deep-link EMP_{id}
- [Glenda Technical Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md)
- [Glenda Overview](documentation/GLENDA_AI_AGENT_OVERVIEW.md)
- [HR Data Collection (Glenda)](documentation/GLENDA_HR_DATA_COLLECTION.md)
- [CEO Command Center](documentation/CEO_COMMAND_CENTER.md)
- [WA Invoice Reminder Plan](documentation/WA_INVOICE_REMINDER_PLAN.md)

### Bounce Processing & Pipelines
- [Email Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md)
- [Akdemia Data Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md)
- [Freescout API Migration Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md)

### Infrastructure
- [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md)
- [Finanzas Email Spoofing Fix](documentation/FINANZAS_EMAIL_SPOOFING_FIX.md)
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [WebSocket/Nginx Fix](documentation/WEBSOCKET_NGINX_FIX.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)

### Known Issues

**FIXED:** See [CHANGELOG.md](documentation/CHANGELOG.md) for full history of resolved issues.

**PENDING:**
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)
- [Freescout Phone Conversation Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) — `Undefined array key 0` in `SendReplyToCustomer.php:76`; fixed upstream, update Freescout on next release
- **Decreto Ingreso Mínimo $240 (2026-04-30):** LUIS RODRIGUEZ ($191.37, gap +$48.63) y NIDYA LIRA ($228.67, gap +$11.33) — incrementar `ueipab_bonus_v2` en contratos. Ver [Análisis](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md).

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
