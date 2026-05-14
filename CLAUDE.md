# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-05-11 (v3)

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
| 39 | Control Asistencia → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CHANGELOG.md) |
| 40 | Mikrotik Hotspot → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CHANGELOG.md) |
| 41 | Gestión Control Asistencia — Guía Visual | Production | `mail.template` + Stories PNG | [Docs](documentation/CHANGELOG.md) |
| 42 | Notice Acknowledgment System | Production | `ueipab_attendance_report` | [Docs](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md) |
| 43 | Glenda Calibration Programme | Production | `ueipab_attendance_report` + `ueipab_ai_agent` | [Docs](documentation/GLENDA_CALIBRATION_PROGRAMME.md) — notice_key=glenda_calibracion_v1; 20 enrolled; deadline 2026-05-30 |
| 44 | Glenda BCV Rate Context | Production | `ueipab_ai_agent` + Script + Cron | param: `ai_agent.bcv_rate_context`; `sync_bcv_to_odoo.py` every 30 min |
| 45 | Glenda Invoice Balance Query | Production | `ueipab_ai_agent` | ACTION:QUERY_BALANCE — see Key Technical Patterns |
| 46 | Glenda Daily Executive Digest | Production | Script + Cron | `glenda_daily_digest.py` daily 07:00 VET |
| 47 | Employee Private Info Request | Production | `ueipab_hr_employee` | [Docs](documentation/EMPLOYEE_INFO_REQUEST.md) |
| 48 | Liquidación V2 Forecast | Production | `ueipab_payroll_enhancements` | Nómina→Reports→Pronóstico Liquidación V2; PDF + Excel |
| 49 | PDVSA Continuity Campaign | Testing | `ueipab_attendance_report` | [Docs](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) — deadline 08-Jun-2026; **Pending:** Cap.2 WA + Cap.3 Glenda |
| 50 | Representante Continuity Campaign | Pending (letter not ready) | `ueipab_attendance_report` | [Docs](documentation/REPRESENTANTE_CONTINUITY_CAMPAIGN.md) — blocked until 5 TODO constants filled |
| 51 | Glenda Auto Draft Payment (WA) | Production | `ueipab_ai_agent` | OCR → draft `account.payment`; config: `ai_agent.payment_journal_map` |
| 52 | Pagos@ Email Receipt Processor | Testing (no cron yet) | Script | `scripts/pagos_receipt_processor.py` — unassigned Freescout pagos@ convs |
| 53 | WA Invoice Reminder | Ready — first live send 2026-05-15 | Script | `scripts/wa_invoice_reminder.py` — daily Representante + PDVSA balance blast; [Plan](documentation/WA_INVOICE_REMINDER_PLAN.md) |
| 54 | Glenda OdooBot Bridge | Production | `ueipab_ai_agent` | `models/mail_bot_glenda.py` — internal staff chat Glenda via Odoo Discuss OdooBot; zero WA credits; dry_run guarded |

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
| ueipab_payroll_enhancements | 17.0.1.68.2 | 2026-05-11 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_bounce_log | 17.0.1.4.0 | 2026-02-14 |
| ueipab_ai_agent | 17.0.1.41.1 | 2026-05-14 |
| ueipab_attendance_report | 17.0.1.6.0 | 2026-05-11 |
| ueipab_hr_employee | 17.0.1.3.0 | 2026-05-13 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.68.2 | Deployed 2026-05-11 |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | 17.0.1.0.2 | Installed |
| ueipab_attendance_report | 17.0.1.6.0 | Deployed 2026-05-13 — **Pending:** PDVSA bulk send (71 partners), [runbook](documentation/PDVSA_DEPLOY_FRIDAY_20260515.md) Steps 6–8 |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | Installed |
| ueipab_hr_employee | 17.0.1.3.0 | Deployed 2026-05-13 |
| ueipab_bounce_log | 17.0.1.4.0 | Deployed 2026-05-10 |
| ueipab_ai_agent | 17.0.1.41.1 | Deployed 2026-05-14 — farewell auto-resolve (P1) · Cashea proactive (P3) · Bachillerato Ciencias y Tecnología knowledge (P2C) |

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

### Notice Acknowledgment System (hr.notice.acknowledgment)

See [Docs](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md). Model in `ueipab_attendance_report`.
- **Route:** `/notice-ack/<token>` (`auth='public'`); generic keys = one-click ACK; `_WA_FORM_KEYS` (e.g. `glenda_calibracion_v1`) → WA form → POST `/glenda-calibracion/<token>`
- **ACK button:** `<a t-att-href="object._get_ack_url()">` — stored via **SQL** to bypass ORM sanitizer; CC `recursoshumanos@ueipab.edu.ve` on every send
- **WA mismatch:** auto-update `employee.mobile_phone` + HR alert to `recursoshumanos@ueipab.edu.ve`
- **Future campaigns:** change `notice_key` only; add to `_WA_FORM_KEYS` in controller if WA capture needed
- **IDs:** Testing attendance_guide=84, prod=58; calibration template testing=86

### Freescout REST API (api_key + hybrid pattern)

- **Config:** `/opt/odoo-dev/config/freescout_api.json` (gitignored) — `api_url`, `api_key`, `webhook_secret`
- **Auth:** `X-FreeScout-API-Key` header — no OAuth, single static key
- **Conversation ID in URL:** DB primary key (`conversations.id`) — NOT the display number (`conversations.number`)
- **`PUT /api/conversations/{id}`** — updates subject/status/assignTo/customerId; status must be **string** (`"active"`, `"closed"`); `byUser` (int user_id) **required** alongside any status change; API auto-manages `folder_id`, `closed_at`, `user_updated_at`
- **`POST /api/conversations/{id}/threads`** — add note: `{"type":"note","text":"<html>","user":<int>}`; `user` is **required** (field name, not `userId`); returns 201
- **Hybrid pattern:** API for writes (proper ORM handling), SQL kept for reads and `threads.body` search (no API equivalent)
- **Helper functions** in `ai_agent_resolution_bridge.py`: `fs_api_update_conversation(conv_db_id, payload, by_user_id=1)` and `fs_api_add_note(conv_db_id, html_body, user_id=1)` — config loaded lazily from `freescout_api.json`
- **Phase 2 complete (2026-05-13):** Resolution bridge primary writes migrated; `close_related_conversations()` stays SQL (thread body search)

### Glenda OdooBot Bridge (Discuss)

- **File:** `addons/ueipab_ai_agent/models/mail_bot_glenda.py` — `_inherit = 'mail.bot'`
- **Hook:** overrides `_get_answer()` — fires only on `channel_type == 'chat'` (private OdooBot DM)
- **Guards:** `ai_agent.dry_run = True` → skips; `credits_ok = False` → blocked; any exception → falls back to default OdooBot silently
- **Knowledge:** imports `_INSTITUTIONAL_KNOWLEDGE` from `general_inquiry.py` at call time — same pricing/policies as WA Glenda
- **History:** fetches last 10 `mail.message` records from channel; builds alternating user/assistant list; merges consecutive same-role turns
- **Cost:** zero MassivaMóvil credits — never touches `whatsapp_service.py`; Claude Haiku only (~$0.001–0.003/conv)
- **Frontend next step:** install `im_livechat` (Odoo Community module, free) + extend `_get_answer` to also handle `channel_type == 'livechat'` → floating chat bubble on school website for customers
- **Announcement script:** `scripts/send_glenda_odoobot_announcement.py` — sends HTML email to all 52 internal users (set `DRY_RUN = False` to send)

### Glenda Auto Draft Payment — Payment Journal Map

- **Config key:** `ai_agent.payment_journal_map` (JSON `ir.config_parameter`) — set in prod param id=71, testing param id=87
- **Schema:** `{"keywords": {"venezuela": {"VES": 162, "USD": 159}, ...}, "fallback_veb": 162, "fallback_usd": 158}`
- **10 banks mapped:** venezuela, mercantil, plaza, banplus, provincial/bbva (→ Banplus journal id=164), bancamiga, cashea, zelle, bicentenario
- **Currency ids:** USD=1, VEB=2 (used in all VEB journals); VES from OCR normalised to VEB
- **Matching:** VES amounts converted via BCV rate → USD for invoice comparison; exact ±2% tolerance; partial fallback (oldest-first)
- **Dedup:** last-4 digits of referencia, 30-day window, same partner — blocks draft creation entirely
- **Draft creation:** `account.payment` state=draft, never auto-posts; `payment_method_line_id` from journal's first inbound line
- **pagos@ email:** Odoo deep link + BCV conversion line + invoice match info + duplicate/no-match warning block
- **`pagos_receipt_processor.py`:** standalone script for Freescout unassigned convs; same pipeline via XML-RPC; image from `_embedded.attachments[].fileUrl` or body `<img>` regex; Freescout API `POST /conversations/{id}/threads` for note; subject prefix `[GLENDA]`

### Glenda BCV Rate Context

- **Param:** `ai_agent.bcv_rate_context` — set by `scripts/sync_bcv_to_odoo.py` every 30 min (`/etc/cron.d/sync_bcv_odoo`) from BCV MySQL (`exchange_rates_bcv.bcv_rates`, user `bcv_script`)
- **JSON shape:** `{"current": {"rate": N, "date": "YYYY-MM-DD"}, "history": [{date, rate, min_rate, max_rate}, ...]}` — last 30 days
- **Skill:** `general_inquiry.get_context()` → `_build_bcv_block()` injected into system prompt; host-side sync required (Docker can't reach host MySQL/Flask)
- **Fallback:** if param missing → "no disponible, consulta bcv.gob.ve" — degrades gracefully

### Glenda Invoice Balance Query (ACTION:QUERY_BALANCE)

- **Trigger:** `ACTION:QUERY_BALANCE:FOUND` (phone match) or `ACTION:QUERY_BALANCE:V-XXXXXXXX` (cédula)
- **Handler:** `_handle_balance_action()` → `_query_partner_balance()` → posted out_invoices, not_paid/partial, partner + children
- **Delivery:** `action_process_reply()` sends breakdown as separate WA message; partner balance pre-loaded into system prompt context when partner found by phone
- **Security:** only shows balance for identified partner; cédula not found → error message to customer

### Glenda Daily Executive Digest (glenda_daily_digest.py)

- **Cron:** `/etc/cron.d/glenda_daily_digest` daily 07:00 VET (`0 11 * * *` UTC) → `gustavo.perdomo@ueipab.edu.ve`
- **5 sections:** KPIs, by-skill table, topic frequency (12 categories), escalations, suspicious activity (same phone >3 convs / tokens >600 / 01:00-05:00 VET / turns >18)
- **Manual run:** `python3 scripts/glenda_daily_digest.py --env production [--date YYYY-MM-DD] [--dry-run]`
- **Delivery:** `mail.mail` state=outgoing — Odoo scheduler sends within minutes

### mail.template body_html — multilingual JSONB (critical pattern)

`body_html` uses `render_engine='qweb'` and stores as JSONB with per-language keys.

**Rules:**
- Always write via **direct SQL** updating **both** `en_US` and `es_VE` keys — ORM write only updates the current lang key; if `es_VE` is stale, the ORM reads the wrong version
- SQL pattern: `UPDATE mail_template SET body_html = %s::jsonb WHERE id = %s` with `json.dumps({'en_US': body, 'es_VE': body})`
- Subject field is also JSONB — same pattern required
- Use `<t t-out="object.field"/>` or `<t t-att-href="object.method()"/>` (QWeb syntax, stored via SQL)
- `{{ object.field }}` Jinja2 syntax does NOT work — `render_engine='qweb'` ignores it
- For multilingual fix via XML-RPC (no direct DB access): call `write({'body_html': body}, context={'lang': 'es_VE'})` then again with `'en_US'`

### Adelanto de Prestaciones Sociales Email Template
- **Testing:** `mail_template` id=71 | **Production:** id=50
- Body managed via **direct SQL only** — ORM `Html` field sanitizer strips custom QWeb method calls (`object.get_liq_veb(...)`) on every `tmpl.write({'body_html': ...})`
- Always use: `env.cr.execute("UPDATE mail_template SET body_html = jsonb_set(body_html, '{en_US}', %s::jsonb) WHERE id=?", [json.dumps(body)])`
- Subject field is also `jsonb` — same SQL pattern required
- After SQL update, **restart Odoo** to flush ORM cache before sending test emails
- Production sync via psycopg2 inside Odoo container: `psycopg2.connect(host='postgres', dbname='DB_UEIPAB', user='odoo', password='odoo8069')`
- Color scheme: navy blue only — `#1a2c5b` (dark) / `#2471a3` (medium) / `#f0f4fa` (light bg). No red (`#c0392b`, `#7b1a1a`)

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

**Status:** Testing | **Version:** 17.0.1.28.0 | **Installed:** 2026-02-07

Centralized AI-powered WhatsApp agent for automated customer interactions. Uses MassivaMóvil WhatsApp API + Anthropic Claude AI with pluggable "skills". See [Full Documentation](documentation/AI_AGENT_MODULE.md).

### Architecture & Skills

| Skill Code | Name | Source Model | Max Turns | 24/7 |
|-----------|------|-------------|-----------|------|
| `bounce_resolution` | Resolucion de Rebotes | `mail.bounce.log` | 5 | No |
| `bill_reminder` | Recordatorio de Factura | `account.move` | 3 | No |
| `billing_support` | Soporte de Facturacion | `res.partner` | 4 | No |
| `hr_data_collection` | Recoleccion de Datos HR | `hr.data.collection.request` | 30 | No |
| `general_inquiry` | Consulta General | *(inbound)* | 10 | **Yes** |

**Key models:** `ai.agent.skill`, `ai.agent.conversation`, `ai.agent.message`, `ai.agent.whatsapp.service`, `ai.agent.claude.service`

### Key Features

- **Conversation lifecycle:** draft → active → waiting → resolved/timeout/failed
- **WhatsApp reminders:** 24h interval, 2 max, auto-timeout after 72h
- **Escalation:** `ACTION:ESCALATE:desc` → Freescout ticket via bridge script
- **Image support:** Multimodal — Glenda sees customer screenshots via Claude vision
- **Re-trigger:** `ACTION:ALTERNATIVE_PHONE:04XXX` → pre-fills wizard with new number
- **Email verification:** `ACTION:VERIFY_EMAIL:email` → sends verification email
- **Family email context:** Akdemia data prevents duplicate email proposals
- **Credit Guard:** Kill switch `ai_agent.credits_ok`, checks WA + Claude spend every 30 min; fail-threshold `ai_agent.credits_fail_threshold` (default 2)
- **Health Monitor:** Dual-layer SPAM detection + auto-failover to backup number
- **Holiday schedule:** Public holidays use weekend hours (09:30-19:00) via `ai_agent.holidays` param
- **Per-skill schedule:** `respect_schedule` on `ai.agent.skill` — `False` = 24/7; `general_inquiry` is always 24/7
- **General Inquiry:** Handles unsolicited inbound WA — auto-creates conversation, identifies contact, routes to `pagos@` (billing) or `soporte@` (general)
- **Billing routing:** `ACTION:HANDOFF:name|summary|billing` → `pagos@ueipab.edu.ve`; `|support` → `soporte@ueipab.edu.ve`
- **Flyer/Audio:** **⚠️ NOT delivered** — MassivaMóvil `type=photo/audio/voice` queues but never delivers to end user. Glenda receives audio (Whisper transcription) but replies text only.
- **2026-2027 enrollment:** Costos anuales $101,58/alumno (Seguro $30,58 + Guía Inglés $25 + Olimpiadas $10 + Enciclopedia $36 — aplica a todos los niveles). Pago vía acuerdo especial may-jul. REQUISITO: 2025-2026 completamente saldado — no puede inscribir con deuda. PDVSA benefit discontinued — new prospect → billing handoff.
- **Farewell:** `resolved` conv → new conv allowed within 24h; `timeout`/`failed` → blocked
- **Quotation engine:** mensualidad + inscripción + costos anuales ($101,58/alumno) + TOTAL PRIMER MES. Sibling discounts: 1st 5%, 2nd 8%, 3rd+ 11%. Enciclopedia $36 aplica a todos los niveles (ya incluida en $101,58).
- **Tarifas 2025-2026 (hasta 31 ago):** $197,38 regular / $162,39 pronto pago (10 primeros días)
- **Tarifas 2026-2027 (inscripción anticipada hasta 31 jul):** inscripción $187,51 / mensualidad sep $197,38; puede prepagar meses adicionales a $197,38 c/u con descuentos hermanos
- **Nueva mensualidad desde 1 sep 2026:** $218,88 regular / $207,93 pronto pago (5% dto) — preliminar

### WA Poll Cron — Account Filter Note

As of 2026-03-30, primary switched to dedicated number +584148321989. Poll cron temporarily uses `account_id=None` (all accounts) to catch replies to the old number from pre-switch waiting conversations. **TODO:** restore `account_id=primary_account_id` filter once pre-switch conversations drain.

### Production Environment Status (2026-05-10)

| Setting | Value |
|---------|-------|
| `ai_agent.dry_run` | `False` (LIVE) |
| `ai_agent.active_db` | `DB_UEIPAB` |
| `ai_agent.credits_ok` | `True` |
| `ai_agent.claude_spend_limit_usd` | `4.15` (~$4.61 remaining after testing usage) |
| Poll cron | active, 5 min |
| Timeout cron | **inactive** — enable after 48h stable |
| Credit Guard | active, 30 min |
| Archive Attachments | active, 2 hours |
| Stagger Payslip Ack Reminders | active, 30 min |
| Auto-Resolve Ack Reminders | active, 30 min |
| Stagger HR Data Collection | **inactive** — Phase 2 |

**System crons (host-level, all targeting production via `/root/.odoo_agent_env_prod`):** escalation (5 min), resolution (5 min), email checker (15 min), bounce processor (daily 05:00), WA health (15 min), Akdemia pipeline (daily 06:00, via `/var/www/dev/.odoo_agent_env_prod`). All switched to production 2026-05-10.

**Testing lockout:** `ai_agent.active_db='DB_UEIPAB'` on testing Odoo — crons see `DB_UEIPAB ≠ testing` and self-skip. ⚠️ Empty string `''` does NOT lock (code treats it as "unconfigured = allow"). Must be set to the production DB name.

**Contact schedule (VET):** Weekdays 06:30-20:30, Weekends/holidays 09:30-19:00. `general_inquiry` exempt (24/7).

**WhatsApp accounts:** Primary +584148321989 (dedicated), Backup +584248944898, Tertiary +584148321963 (manual only).

### Testing Environment Status (2026-05-14)

| Setting | Value |
|---------|-------|
| `ai_agent.dry_run` | `False` |
| `ai_agent.active_db` | `'DB_UEIPAB'` (locked — crons see DB_UEIPAB≠testing → self-skip) |

> **Fixed 2026-05-14:** Previously set to `''` which the code treats as "allow" — testing was double-processing all live WA messages with stale code. See [Changelog](documentation/CHANGELOG.md).

### Production Migration Checklist

**COMPLETE as of 2026-05-10.** See [AI_AGENT_MODULE.md](documentation/AI_AGENT_MODULE.md).

### HR Loan Module Production Migration Checklist

**Status:** Ready for deployment | **Scripts:** `setup_loan_rules.py` + `deploy_loan_templates_prod.py`

| Step | Action | Script/Method |
|---|---|---|
| A | Backup DB_UEIPAB | `pg_dump` |
| B | Copy `ohrms_loan` + `ohrms_loan_accounting` to prod addons | `scp` |
| C | Copy `ueipab_payroll_enhancements` v1.65.0 to prod | `scp` |
| D | Install ohrms_loan + ohrms_loan_accounting | Odoo `-i` |
| E | Upgrade ueipab_payroll_enhancements | Odoo `-u` |
| F | Create loan salary rules + patch NET formulas | `setup_loan_rules.py` via Odoo shell |
| G | Deploy email templates (create id=75 equiv, patch id=37+50) | `deploy_loan_templates_prod.py` |
| H | Restart + smoke test | `docker restart ueipab17` |

**Production template IDs:** Payslip Email=37, Adelanto Prestaciones=50, Adelanto Salario=52

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

### Ad-hoc Queries
- [QueryRepresentantePDVSAFalseTagCheck](documentation/QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) — Receivables report for Representante PDVSA customers segmented by fiscal_check flag, with quantity and amount due
- [Decreto Salario Mínimo Mayo 2026](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md) — Impact analysis vs $240 decree: LUIS RODRIGUEZ & NIDYA LIRA below threshold, cestaticket $40 unchanged, monthly adjustment $59.96

### Planned / Testing Reports
- [Payroll Requisition Estimation Report](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md) — Preliminary payroll cost estimate from active contracts (no payslips needed), single currency per run, auto-populated BCV rate

### Features
- [Advance Payment System](documentation/ADVANCE_PAYMENT_SYSTEM.md)
- [Adelanto Prestaciones Payment Receipt Ack](documentation/ADELANTO_PRESTACIONES_PAYMENT_RECEIPT_ACK.md) — Deferred: two-phase ack design for LIQUID_VE_V2 (consent + payment receipt), pending bank integration
- [Comprobante de Pago](documentation/COMPROBANTE_DE_PAGO.md)
- [Payslip Acknowledgment System](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md)
- [Payslip Ack Status Report](documentation/PAYSLIP_ACK_STATUS_REPORT.md)
- [Batch Email Wizard](documentation/BATCH_EMAIL_WIZARD.md)
- [Email Templates](documentation/EMAIL_TEMPLATES.md)
- [Cybrosys Module Modifications](documentation/CYBROSYS_MODULE_MODIFICATIONS.md)

### AI Agent & Bounce Processing
- [AI Agent Module](documentation/AI_AGENT_MODULE.md)
- [Email Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md)
- [Akdemia Data Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md)
- [Glenda Overview](documentation/GLENDA_AI_AGENT_OVERVIEW.md)
- [HR Data Collection (Glenda)](documentation/GLENDA_HR_DATA_COLLECTION.md)

### Infrastructure
- [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md)
- [Finanzas Email Spoofing Fix](documentation/FINANZAS_EMAIL_SPOOFING_FIX.md) — SPF/DMARC added 2026-05-13; backscatter from gosportrotaryclub.org spoofing finanzas@; DKIM was already present
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
