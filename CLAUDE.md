# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-06-13 (v40)

## Core Instructions

**CRITICAL RULES:**
- **ALWAYS work locally, NEVER in production environment**
- **NEVER TOUCH DB_UEIPAB without proper authorization**
- Development database: `testing`
- Production database: `DB_UEIPAB` (requires authorization)

---

## Active Features Summary

See [documentation/FEATURES.md](documentation/FEATURES.md) for the full feature list (#1–#74).

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

**Quincena Calculation:** All V2 salary rules use fixed `monthly / 2.0`. AGUINALDOS uses fixed-0.5 separately.

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

**⚠️ Two BCV sync mechanisms — do NOT conflate them:**

| Cron | Script | Destination | Purpose |
|------|--------|-------------|---------|
| `/etc/cron.d/sync_bcv_odoo` (every 30 min) | `sync_bcv_to_odoo.py` | `ir.config_parameter` → `ai_agent.bcv_rate_context` | Glenda AI answers BCV queries |
| `/etc/cron.d/bcv_odoo_currency_sync` (06:00 VET weekdays) | `curl POST /odoo_api_bridge/sync_currency_rate` | `res.currency.rate` | Reports, payroll, accounting |

These are independent — updating one does NOT update the other. Full incident history: memory `patterns-bcv-rate-sync`.

---

## Payslip Batch Features

Date Sync (auto-recomputes), Total Net Payable (V1/V2/Aguinaldos), Exchange Rate Application + Auto-Population (BCV/last batch), Email Template Selector, Advance Payment (% multiplier, [details](documentation/ADVANCE_PAYMENT_SYSTEM.md)), Remainder Payment (linked to advance batch).

---

## Module Versions

**Odoo base:** `odoo:17.0` build `17.0-20260504` (commit `d66bb0d7`) — both envs as of 2026-05-10.
**Last sync verified:** 2026-06-13 — see memory `project-module-versions` for current state.

| Module | Version | Notes |
|--------|---------|-------|
| hr_payroll_community | 17.0.1.0.0 | testing only |
| ueipab_payroll_enhancements | 17.0.1.74.1 | both — `is_advance_payment` on individual payslips + `has_period_advance` double-pay guard + amber email banner + invoice-reminder wizard: `all` segment + `override_pdvsa_rule` toggle (2026-06-23). ⚠️ populate-on-open via server action was REVERTED in v1.74.1 — mounting the form with rows present re-triggers the Owl `this.fiber.bdom is null` crash; list must fill post-mount via onchange |
| ueipab_hr_contract | 17.0.2.0.0 | both |
| ueipab_bounce_log | 17.0.1.4.0 | both |
| ueipab_ai_agent | 17.0.1.59.4 | both — ⚠️ **Banco de Venezuela UNAVAILABLE** (2026-06-23): Glenda's MEDIOS DE PAGO knowledge no longer offers BdV (0102); see note below. + ACTION:QUOTE + live pricing ground truth (2026-06-11) |
| ueipab_attendance_report | 17.0.1.6.27 | both — hr.leave CC fix: RRHH notified immediately on approve/refuse |
| ueipab_hr_employee | 17.0.1.3.0 | both |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | both |
| ueipab_ari_portal | 17.0.1.5.0 | both |
| ohrms_loan + ohrms_loan_accounting | 17.0.1.0.0 | testing only |
| ueipab_sales | 17.0.1.2.2 | both — quotation engine + T&C annex page 2 + QR verification seal `/verify-quote/<token>` on Acuerdo PDF (see UEIPAB_SALES_QUOTATION_PLAN.md) |
| ueipab_enrollment_journey | 17.0.0.4.3 | testing only — 9-step 3-block timeline (🏛️ Inscripción Formal / 💻 Activación Plataformas / 📁 Cierre Administrativo), hard Block 1 gate, contract escrow step 3, Glenda bubble, QWeb PDF CSE-2627-XXXX + QR seal all pages `/verify-contract/<token>` — see ENROLLMENT_JOURNEY_WIZARD.md |

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

### Closed-Contract Payslip (terminated employee mid-batch)

See [PAYROLL_PROCEDURES.md](documentation/PAYROLL_PROCEDURES.md) for the full 7-step fix procedure (re-open contract, pro-rate salary fields, compute sheet, restore contract state) + cesta ticket pro-ration formula.

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
- **`_EMAIL_CONFIRM_KEYS`:** `ari_guide_2026_v1` → sends confirmation email to employee + CC recursoshumanos@ on ACK click

### AR-I Portal Guide Page (v1.5.0)

**Module:** `ueipab_ari_portal` | **Controller:** `controllers/ari_guide.py`

| Route | Auth | Description |
|-------|------|-------------|
| `/ari-guide/<token>` | public | Full 6-section guide + ACK button (links to `/notice-ack/<token>`). Shows "ya confirmaste" if already acknowledged. |
| `/ari-guide/` | public | Generic guide without ACK tracking (for employees with no blast token) |

**Portal banner** (`/my/ari`): injected in `portal_templates.xml` — pending ACK → blue "Ver Guía →" button; acknowledged → green "✅ Guía confirmada · Releer →".

**HR Monitor:** `Employees → AR-I Portal → Confirmaciones de Guía` (action id prod=TBD, testing=969) — filtered `hr.notice.acknowledgment` list for `ari_guide_2026_v1`. Smart: form view sends to that employee only; list view sends to all pending.

**Blast script:** `scripts/create_ari_portal_guide_email.py --env production --bulk` — 43 employees sent 2026-05-28 (RAMON BELLO id=608 excluded). `_EXCLUDE_EMP_IDS = {608}`.

### Freescout REST API (api_key + hybrid pattern)

See [FREESCOUT_API_MIGRATION_PLAN.md](documentation/FREESCOUT_API_MIGRATION_PLAN.md) for full reference.
- **Config:** `ir.config_parameter` keys `ai_agent.freescout_api_url` + `ai_agent.freescout_api_key`. File `/opt/odoo-dev/config/freescout_api.json` = dev-only fallback. All Odoo model methods use param lookup first.
- **Auth:** `X-FreeScout-API-Key` header; Conversation ID = DB primary key, NOT display number
- **`PUT /api/conversations/{id}`** — status must be **string**; `byUser` (int) **required** on status changes
- **`POST /api/conversations/{id}/threads`** — note: `{"type":"note","text":"<html>","user":<int>}`; `user` required
- **Hybrid:** API for writes; SQL for reads + `threads.body` search

### Absence Notification (Feature #58) + School Account Help (Feature #59)

- **Absence:** `ACTION:NOTIFY_ABSENCE:name|grade|reason` OR email→soporte@ → Freescout conv → `absence_processor.py` cron assigns Josefina (user_id=8), CCs teachers via `control_asistencias` DB lookup. Marker: `[AUSENCIA]` prefix.
- **School account:** `ACTION:SCHOOL_ACCOUNT_HELP:cedula|student_name|grade` → 3-factor verify (partner/cédula/directory fuzzy match). `scripts/sync_google_directory.py --live`; 224 accounts.

See [GLENDA_TECHNICAL_PATTERNS.md](documentation/GLENDA_TECHNICAL_PATTERNS.md) for full patterns.

### Telegram Channel (ai.agent.telegram.service)

See [GLENDA_TELEGRAM_CHANNEL.md](documentation/GLENDA_TELEGRAM_CHANNEL.md) for full deployment docs. Critical gotchas:
- PostgreSQL tables: `discuss_channel` / `discuss_channel_member` (NOT `mail_channel`). ORM: `discuss.channel` / `discuss.channel.member`.
- Webhook cursor abort: wrap CEO notify calls with `with self.env.cr.savepoint():`
- Token lookup: `@ormcache` throws `KeyError` mid-transaction → direct SQL fallback in `_token()`
- `address_home_id` not searchable in Odoo 17 → use `user_id.partner_id` for partner→employee lookups
- Monitoring: AI Agent → filter Canal=Telegram (action=830 in prod)
- Identity ring v57.20: `res.partner.telegram_chat_id` is authoritative. See memory `glenda-identity-ring`.

### Glenda Family Billing Enrichment (Feature #69)

**Cache:** `school.family_billing_json` (199 families); `scripts/sync_family_billing.py --live` — cron 07:30 VET. Lookup: phone → fuzzy student name. Injected block includes monthly, discount, forecast, annual costs (qty × $111.58 hasta 31 jul / $116.58 desde 1 ago = seguro $30.58 + inglés $35/$40 + olimpiadas $10 + enciclopedia $36).

**Glenda AI Supervisor (Feature #70):** `scripts/glenda_supervisor.py`; scores 1–5; CEO email + OdooBot DM + WA if critical. Cron every 2h weekdays 07:00–21:00 VET (`REVIEW_WINDOW_HOURS=2` must match cadence).

**Pricing Ground Truth (single source, 2026-06-11):** `sale.order.get_pricing_ground_truth()` (ueipab_sales) composes canonical 2026-2027 rates from `UEIPAB_LLAMADOS` + live product prices. Consumers: Glenda prompt, `glenda_supervisor.py`, `pagos_faq_email_checker.py`. **A price change = edit the product in Odoo; never re-type prices into prompts.**

### Freescout Pagos@ Bridge (Feature #74)

`pagos_faq_email_checker.py` — 100% REST API. Never replies to customers directly; posts internal notes only (`[FAQ-AI]` prefix for drafts, `[FAQ-AI][ESCALAR]` for escalations). `pagos_receipt_processor.py`: email lookup via `ilike`, Sheet fallback, advance payment via `action_post()`. UI: AI Agent → Operaciones → Pagos Freescout (`ai.agent.freescout.task`).

See [GLENDA_TECHNICAL_PATTERNS.md](documentation/GLENDA_TECHNICAL_PATTERNS.md) for full patterns (`_parse_monto()`, `_load_fs_config()`, `action_reprocess()`, etc.).

### Glenda Technical Patterns

See [GLENDA_TECHNICAL_PATTERNS.md](documentation/GLENDA_TECHNICAL_PATTERNS.md) for full reference on: Silent Timeout/Quiet Hours, OdooBot Bridge (Discuss), Auto Draft Payment / Journal Map, BCV Rate Context, Invoice Balance Query, Daily Executive Digest, Quotation Engine & Enrollment info, Pagos Bridge patterns, Absence Notification, School Account Help.

### Leave Notification System (Features #76–#78)

`scripts/leave_notification.py` (confirm/validate1 emails every 15 min to recursoshumanos@) + `scripts/hr_leave_attendance_digest.py` (daily 08:00 VET digest: pending approvals + 30-day activity + high-issue employees). Leave cross-check in morning attendance alert injects green/yellow context block (flag still raised).

See [LEAVE_NOTIFICATION_SYSTEM.md](documentation/LEAVE_NOTIFICATION_SYSTEM.md) for leave type validation matrix, state file details, work schedule (07:00 VET start).

### Attendance Daily Alert + check_out Auto-fill

`scripts/attendance_daily_alert.py`; morning 11:30 VET (recap yesterday) + evening 23:30 VET (WiFi-based check_out auto-fill via Mikrotik Router 2 at `172.28.10.10`). Special-schedule employees 571/606/610 skipped. State: `attendance_daily_alert_state.json`. Correction button injects `/attendance-fix/<token>` link.

See [ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) Appendix A for cron schedule, WiFi fallback, source tracing (`in_mode`/`out_mode` fields).

### Attendance Correction Wizard + Biweekly Report

Rejection wizard (v6.21): `hr.attendance.rejection.wizard`; CC policy (v6.22): all events CC `recursoshumanos@` + `arcides.arzola@`; double-submit guard (v6.23): JS disables on first click. Biweekly wizard: `force_send=False` (mail queue, no HTTP timeout); ORM fields are `date_from`/`date_to`/`month`/`year`/`quincena` (NOT `period_start`/`period_end`); exclude test accounts ids 574 and 764.

See [ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) Appendix B–C for full patterns.

### WA & Email Invoice Reminder

See [WA_INVOICE_REMINDER_PLAN.md](documentation/WA_INVOICE_REMINDER_PLAN.md) for full technical reference.
- **Wizard:** Accounting → Customers → Recordatorio de Saldo; Tags REP=25 / PDVSA=26 / VIP=30 (excluded)
- **WA cron:** weekdays 07:00 VET; state file `scripts/wa_invoice_reminder_state.json`
- **v70.5 (2026-06-01):** Fixed Owl rendering crash — removed `line_ids` from `default_get`; onchange is now the single population path.
- **⚠️ Pending enhancements (2026-06-01):** See PENDING section below — 2 fixes needed before next bulk send.

### CEO Command Center (wa_monitor)

See [CEO_COMMAND_CENTER.md](documentation/CEO_COMMAND_CENTER.md) for full reference.
- Params: `wa_monitor.ceo_email` / `wa_monitor.ceo_phone` / `wa_monitor.tertiary_notified_ids`
- **OdooBot DM** = primary (no throttle); **WA backup** = 120s anti-spam throttle

### DMARC Report Processor

See [CEO_COMMAND_CENTER.md](documentation/CEO_COMMAND_CENTER.md). Script: `scripts/dmarc_report_processor.py`; cron 10:30 UTC daily. Source: FreeScout `finanzas@` (mailbox_id=5).

**⚠️ DMARC `p=none` since 2026-05-20 (DO record id=1818865872):** Akdemia SendGrid sends FROM `@ueipab.edu.ve` without DKIM; SPF misaligned. Monitor-only until fix: Akdemia admin → Domain Auth → 3 CNAMEs → DigitalOcean → revert to `p=reject`. **DO NOT set SPF `-all` until DKIM live.**

### HTML Email / WA Broadcast Templates (ad-hoc)

Sent via `mail.mail` XML-RPC (`state='outgoing'`, trigger queue cron id=3 with `method_direct_trigger`).

**⚠️ Logo URL pattern for HTML emails:**
- ✅ USE: `https://odoo.ueipab.edu.ve/web/image/res.company/1/logo` — **1080×1080 square**, renders correctly in circular frames
- ❌ AVOID: `https://dev.ueipab.edu.ve/flyers/ueipab_logo.png` — **291×120 landscape rectangle**, distorts in circular/square frames

### mail.template body_html — multilingual JSONB (critical)

See [EMAIL_TEMPLATES.md](documentation/EMAIL_TEMPLATES.md) for full details and Adelanto template IDs.
- Always write via **direct SQL** updating **both** `en_US` and `es_VE` keys — ORM only updates current lang
- `UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s` with `json.dumps({'en_US': body, 'es_VE': body})`
- Use QWeb `<t t-out="..."/>` syntax — Jinja2 `{{ }}` does NOT work with `render_engine='qweb'`

---

## Production Environment

See [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md) for full details.

**Quick Reference:**
- Server: `10.124.0.3` | User: `root` | Password: in `config/production.json` → `server.password`
- Container: `ueipab17`
- Database: `DB_UEIPAB`
- Module Path: `/home/vision/ueipab17/addons`

---

## Dev Server Configuration

**Host:** `freescout.ueipab.edu.ve` | RAM: 3.8 GB | Swap: 2 GB | Disk: 48 GB
**NTP:** Both droplets sync to `time.cloudflare.com`. Config: `/etc/systemd/timesyncd.conf.d/ntp.conf`.

| Setting | Value | File |
|---------|-------|------|
| Odoo workers | **3** (reduced from 4 on 2026-05-23 — RAM pressure) | `/opt/odoo-dev/config/odoo.conf` |
| Odoo Docker image | `odoo:17.0` build `17.0-20260504` | `docker-compose.yml` |

**⚠️ Swap exhausted (2026-05-23)** — OOM resolved by reducing workers to 3. Upgrade droplet if RAM pressure returns.

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
- **Freescout source:** REST API only (no MySQL) — scans soporte@ mailbox for DSN conversations
- **3-tier logic:** CLEAN (Representante + permanent failure) → FLAG (temporary or non-Representante) → NOT FOUND
- **Google Sheets** (`1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`): `Customers!J` removes+flags 🔴 bounced email (TIER 1); `BounceEmail` tab logs Date/Customer/Email/Source/Status.
- **Creds:** `config/google_sheets_credentials.json`

### WhatsApp API (MassivaMóvil)

- **Provider:** MassivaMóvil (`whatsapp.massivamovil.com`)
- **Config:** `/opt/odoo-dev/config/whatsapp_massiva.json` (gitignored)
- **Auth:** API secret key param (not OAuth), key name `ueipab1`
- **Primary Account (dedicated):** +584148321989 | **Backup:** +584248944898 | **Tertiary (emergency):** +584148321963
- **⚠️ BACKUP active** (+584248944898) since 2026-05-22; `dry_run=True` — WA paused, Telegram active. See PENDING section for restore steps.
- **Anti-spam:** Min 120s between sends
- **Send:** `POST /api/send/whatsapp` | **Validate:** `GET /api/validate/whatsapp` | **Receive:** `GET /api/get/wa.received`
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Retry policy (v48.0):** 2 retries on HTTP 429 — delays 3s, 6s — then OpenAI fallback
- **OpenAI fallback:** `gpt-4o-mini` via `requests`. Params: `ai_agent.openai_fallback_enabled/api_key/model`.
- **Zero new dependencies:** both providers use `requests` only — no `openai` or `anthropic` SDK in container

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

**`_send_to_user(text)`** — channel dispatcher on `ai.agent.conversation`. **`channel` field** — `Selection([('whatsapp','WhatsApp'),('telegram','Telegram')])`. Telegram convs have `phone=''` and `telegram_chat_id` set.

### Key Features + Live Flags

See [AI_AGENT_MODULE.md](documentation/AI_AGENT_MODULE.md) for the full feature list. Critical runtime state:
- **`dry_run=True`** (WA paused); **`ai_agent.credits_ok`** (Claude kill switch); **`ai_agent.wa_credits_ok`** (WA sends kill switch — split after 2026-06-09 incident)
- **Credit Guard (v58.0):** Two independent kill switches checked every 30 min. `credits_ok=False` mutes ALL channels; `wa_credits_ok=False` mutes WA only.
- **Identity ring (v57.20):** Turn 1 for unverified contacts → identification prompt, no Claude call until identified
- **Re-trigger stuck conv:** `env['ai.agent.conversation'].browse(ID).action_process_reply(message_text='...', wa_message_id=0); env.cr.commit()`
- **Production:** Hours VET weekdays 06:30-20:30, weekends 09:30-19:00. `general_inquiry` exempt (24/7). Kill Telegram: `ai_agent.telegram_enabled=False`.
- **⚠️ Banco de Venezuela UNAVAILABLE (2026-06-23):** BdV (0102) cannot receive payments. Glenda's MEDIOS DE PAGO block in `skills/general_inquiry.py` (`_INSTITUTIONAL_KNOWLEDGE`) now states this explicitly and offers only the alternatives — TRANSFERENCIAS (Plaza/BanPlus/Mercantil/Bancamiga), PAGO MÓVIL (Opción A `0414-1906296`, B `0414-2337463`, C `0414-4375222`), DIVISAS (Zelle `pagos@`, Binance `383 867 49`). Verified live (v1.59.4). **When BdV is restored, revert this block.** Same content drove the 2026-06-22 payment-notice email blast (`scripts/send_payment_notice_email.py`).

> **⚠️ PROD DEPLOY MECHANISM:** prod addons (`/home/vision/ueipab17/addons`) is a **separate git repo** (`3DVision-CA/ueipab17-cm`), NOT this dev repo. `git pull` on prod does NOT carry dev commits — **scp changed files** to prod (back up first), then `docker exec ueipab17 odoo -u <module> -d DB_UEIPAB --stop-after-init` + `docker restart ueipab17`, then verify `installed_version` via XML-RPC. This is why prod silently lags the repo.

---

## Akdemia Data Pipeline

See [Full Documentation](documentation/AKDEMIA_DATA_PIPELINE.md). Scraper: `akdemia_scraper.py` (Playwright); cron daily 06:00 VET; phases 2a–5 (Freescout + Sheets sync).

---

## Documentation Index

**Payroll/Liquidation:** [V2 Impl](documentation/LIQUIDATION_V2_IMPLEMENTATION.md) · [V2 Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) · [V2 Payroll](documentation/V2_PAYROLL_IMPLEMENTATION.md) · [Procedures](documentation/PAYROLL_PROCEDURES.md) · [Disbursement](documentation/PAYROLL_DISBURSEMENT_REPORT.md) · [Prestaciones](documentation/PRESTACIONES_INTEREST_REPORT.md) · [Relacion](documentation/RELACION_BREAKDOWN_REPORT.md) · [Finiquito](documentation/FINIQUITO_REPORT.md) · [V1 Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md) · [V2 Migration](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md) · [Requisition Est.](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md) · [Utilidades V2 Research ⚠️](documentation/LIQUID_UTILIDADES_V2_RESEARCH.md)

**Features:** [Advance Payment](documentation/ADVANCE_PAYMENT_SYSTEM.md) · [Adelanto PS Ack](documentation/ADELANTO_PRESTACIONES_PAYMENT_RECEIPT_ACK.md) · [Comprobante](documentation/COMPROBANTE_DE_PAGO.md) · [Payslip Ack](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) · [Ack Status](documentation/PAYSLIP_ACK_STATUS_REPORT.md) · [Batch Wizard](documentation/BATCH_EMAIL_WIZARD.md) · [Email Templates](documentation/EMAIL_TEMPLATES.md) · [Cybrosys Mods](documentation/CYBROSYS_MODULE_MODIFICATIONS.md) · [Employee Info](documentation/EMPLOYEE_INFO_REQUEST.md) · [Leave Notifications](documentation/LEAVE_NOTIFICATION_SYSTEM.md)

**AI Agent / Glenda:** [UX Improvement](documentation/GLENDA_UX_IMPROVEMENT_PLAN.md) · [Module](documentation/AI_AGENT_MODULE.md) · [Technical Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) · [Overview](documentation/GLENDA_AI_AGENT_OVERVIEW.md) · [HR Data](documentation/GLENDA_HR_DATA_COLLECTION.md) · [Telegram](documentation/GLENDA_TELEGRAM_CHANNEL.md) · [CEO Center](documentation/CEO_COMMAND_CENTER.md) · [WA Invoice Reminder](documentation/WA_INVOICE_REMINDER_PLAN.md) · [Ack Reminder Glenda](documentation/PAYSLIP_ACK_REMINDER_GLENDA.md)

**Ops/Infra:** [Meta WA Migration](documentation/META_CLOUD_API_MIGRATION_PLAN.md) · [Production](documentation/PRODUCTION_ENVIRONMENT.md) · [WebSocket/Nginx](documentation/WEBSOCKET_NGINX_FIX.md) · [Finanzas Spoofing](documentation/FINANZAS_EMAIL_SPOOFING_FIX.md) · [Combined Fix](documentation/COMBINED_FIX_PROCEDURE.md) · [Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md) · [Bounce Cleanup](documentation/BOUNCE_EMAIL_CLEANUP_PROCEDURE.md) · [Akdemia Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md) · [Freescout Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md)

**Attendance:** [Smart Alert Plan](documentation/ATTENDANCE_SMART_ALERT_PLAN.md) · [Biweekly Plan](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) (incl. daily alert, correction wizard, biweekly report wizard patterns)

**Sales / Quotations:** [UEIPAB Sales Quotation Plan](documentation/UEIPAB_SALES_QUOTATION_PLAN.md) — **DEPLOYED TO PRODUCTION 2026-06-11**; 17 products + 12 templates; smoke test $973.20 exact.

**Enrollment:** [Enrollment Journey Wizard](documentation/ENROLLMENT_JOURNEY_WIZARD.md) — `ueipab_enrollment_journey` v0.4.3 testing; 9-step 3-block customer timeline + QWeb contract PDF (CSE-2627-XXXX) + QR seal on all pages (`/verify-contract/<token>`).

**Campaigns/School:** [PDVSA Campaign](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) · [Representante Campaign](documentation/REPRESENTANTE_CONTINUITY_CAMPAIGN.md) · [Notice ACK](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md) · [Calibration](documentation/GLENDA_CALIBRATION_PROGRAMME.md) · [Budget Vote](documentation/BUDGET_VOTE_EMAIL.md) · [Attendance Plan](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) · [Control Asistencia](documentation/CONTROL_ASISTENCIA_BRIDGE.md)

**Ad-hoc / Legal:** [PDVSA Tag Check](documentation/QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) · [Salario Mínimo Mayo 2026](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md) · [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md) · [Freescout Phone Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) · [Invoice Currency Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)

### Known Issues

**FIXED:** See [CHANGELOG.md](documentation/CHANGELOG.md) for full history of resolved issues.

**FIXED 2026-05-28:** `hr_org_chart` patch (`/tmp/patch_org_chart.py` on both hosts) — **re-apply if containers rebuilt** (`(kw.get('context') or {}).get('key')` pattern). Work schedule 07:00 VET start (calendar_id=1). See [CHANGELOG.md](documentation/CHANGELOG.md).

**PENDING — Code / Infrastructure:**
- **`LIQUID_UTILIDADES_V2` rate inconsistency (2026-06-05):** See [PAYROLL_PROCEDURES.md](documentation/PAYROLL_PROCEDURES.md) and CHANGELOG 2026-06-05. Decision needed: 60 days (company policy) or 15 days (LOTTT min); fix period to current fiscal year only.
- **Invoice Reminder Wizard (2026-06-01 enh.):** See [WA_INVOICE_REMINDER_PLAN.md](documentation/WA_INVOICE_REMINDER_PLAN.md#pending-enhancements-2026-06-01). ✅ **Fix 1 RESOLVED 2026-06-23 (v1.74.0, both envs)** — `PDVSA_ADVANCE_PAID` is now bypassable via the `override_pdvsa_rule` toggle (kept as opt-in, not removed; toggle also bypasses `fiscal_check`). New `all` segment surfaces untagged AR customers, so **Fix 2 (assign missing REP/PDVSA tags) is now optional for sending** — still nice-to-have for segmentation. ⚠️ **Still open:** MARIA MARTIN duplicate partner (ids 3658 and 2666) — merge/deactivate the blank one.
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md) — `tdv_multi_currency_account`; both envs
- [Freescout Phone Conversation Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) — `Undefined array key 0`; fixed upstream, update Freescout on next release
- **MassivaMóvil Webhook wrong Content-Type** — controller uses `type='json'` but MassivaMóvil sends form-encoded POST. Fix: change to `type='http'`, parse `request.httprequest.form.get()`, `json.loads(data)`.
- **Internal number guard** — Gustavo's +584142337463 triggers `general_inquiry`. Fix: add `ai_agent.general_inquiry_blocked_phones` param.
- **Glenda supervisor brevity criterion** — split from tone (criterion 4); add avg char_count. See [UX Plan](documentation/GLENDA_UX_IMPROVEMENT_PLAN.md).

**PENDING — Data / Contract:**
- **Josefina Phase 2** — `LIQUID_OTHER_DED_V2` rule to deduct $420.87 overpayment. See `documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md`.

**PENDING — External / Infrastructure:**
- **WA Primary +584148321989 broken** (2026-05-22) — Massiva support ticket open. Once fixed: reconnect → restore config params → clear flagged_phone. Restore Glenda WA: set `ai_agent.dry_run=False` in prod.
- **`/etc/cron.d/wa_primary_relay`** — fires every 5 min in DRY_RUN (no `--live`). Remove or re-add `--live` once Massiva fixes primary.

**PENDING — Refactor:**
- **`partner.communication.ack` misplaced in `ueipab_attendance_report`** — belongs in `ueipab_ai_agent`/`ueipab_campaigns`. Requires DB migration. Low urgency. See [ACK_FORM_UX_IMPROVEMENTS.md](documentation/ACK_FORM_UX_IMPROVEMENTS.md).

**BLOCKED — Waiting on external trigger:**
- **Representante Continuity Campaign** — script ready, blocked until LETTER_URL + BULLET_1-3 + EMAIL_HEADLINE provided.
- **Banco Plaza API** — QA/eval phase; credentials pending from Banco Plaza team.

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
