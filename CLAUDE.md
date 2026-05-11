# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-05-10 (v2)

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
| 30 | Freescout API Migration | Planned | Scripts | [Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md) |
| 31 | HR Data Collection (Glenda) | Production | `ueipab_ai_agent` + `ueipab_hr_employee` | [Docs](documentation/GLENDA_HR_DATA_COLLECTION.md) |
| 32 | Payslip Ack Confirmation Email | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 33 | Payroll Requisition Estimation Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md) |
| 34 | Adelanto de Prestaciones Sociales Email | Production | `ueipab_payroll_enhancements` | [Changelog](documentation/CHANGELOG.md) |
| 35 | Payslip Ack Reminder via Glenda (WA) | Production | `ueipab_ai_agent` | [Docs](documentation/PAYSLIP_ACK_REMINDER_GLENDA.md) |
| 36 | HR Salary Advance / Loan System | Testing | `ueipab_payroll_enhancements` + `ohrms_loan` + `ohrms_loan_accounting` | [Docs](documentation/HR_SALARY_ADVANCE_LOAN.md) |
| 37 | Attendance Biweekly Email Report | Production | `ueipab_attendance_report` | [Plan](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) — v17.0.1.5.2: holidays + special schedule + self-service correction + resend buttons + **Notice ACK system** + **Glenda calibration WA-ACK** |
| 38 | Bono Día de las Madres 2026 | Production | `ueipab_payroll_enhancements` | [Docs](documentation/BONO_MADRES_2026.md) |
| 39 | Control Asistencia → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CHANGELOG.md) — daily sync teacher activity from control_asistencias MySQL → hr.attendance |
| 40 | Mikrotik Hotspot → Odoo Bridge | Production | Script + Cron | [Docs](documentation/CHANGELOG.md) — daily WiFi presence sync for admin/maintenance staff, confidence-based |
| 41 | Gestión Control Asistencia — Guía Visual | Production | `mail.template` + Stories PNG | [Docs](documentation/CHANGELOG.md) — 4 Instagram stories + email template carousel para empleados; jerarquía Kiosko→Dashboard Odoo→Control Asist.→WiFi |
| 42 | Notice Acknowledgment System | Production | `ueipab_attendance_report` | [Docs](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md) — hr.notice.acknowledgment model, /notice-ack/ public route, ACK button in email, HR tracking view |
| 43 | Glenda Calibration Programme | Production | `ueipab_attendance_report` + `mail.template` + Stories PNG | — notice_key=glenda_calibracion_v1; WA-number form at /glenda-calibracion/<token>; mismatch → HR alert; 4 Instagram stories; mail.template id=86 (testing) |
| 44 | Glenda BCV Rate Context | Production | `ueipab_ai_agent` + Script + Cron | — `sync_bcv_to_odoo.py` every 30 min; queries BCV MySQL → `ir.config_parameter` ai_agent.bcv_rate_context; Glenda answers tasa BCV + USD↔VEB conversions |
| 45 | Glenda Invoice Balance Query | Production | `ueipab_ai_agent` | — ACTION:QUERY_BALANCE:FOUND/CEDULA; queries account.move; sends breakdown as separate WA msg; VEB conversion at BCV rate |
| 46 | Glenda Daily Executive Digest | Production | Script + Cron | — `glenda_daily_digest.py` daily 07:00 VET; 5-section HTML email: KPIs, by-skill, topics, escalations, suspicious activity |
| 47 | Employee Private Info Request | Production | `ueipab_hr_employee` | [Docs](documentation/EMPLOYEE_INFO_REQUEST.md) — token-based self-service form; 14 private fields; Fase 1 campaign sent to 44 employees 2026-05-11; auto-reminders day 3+7 |
| 48 | Liquidación V2 Forecast | Testing | `ueipab_payroll_enhancements` | — wizard at Nómina→Reports→Pronóstico Liquidación V2; as-of date (default 2026-07-31); all 46 V2 active employees; full rule breakdown (vac/bono/util/prest/antig/int/deducciones); screen tree + PDF; v17.0.1.68.1 |
| 48 | PDVSA Continuity Campaign | Testing | `ueipab_attendance_report` | [Docs](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) — `partner.communication.ack`; YES/NO links; `/partner-ack/<token>/si\|no`; votacion@; deadline 08-Jun-2026; **Pending:** Cap.2 WA reminders + Cap.3 Glenda stats |

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
| ueipab_payroll_enhancements | 17.0.1.68.1 | 2026-05-11 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_bounce_log | 17.0.1.4.0 | 2026-02-14 |
| ueipab_ai_agent | 17.0.1.31.4 | 2026-05-10 |
| ueipab_attendance_report | 17.0.1.6.0 | 2026-05-11 |
| ueipab_hr_employee | 17.0.1.2.0 | 2026-05-11 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.67.6 | **Deployed 2026-05-08** (Bono Día de las Madres + disbursement report fixes + bank account column + 4 employee date columns in disbursement report) |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | 17.0.1.0.2 | Installed (2025-12-21) |
| ueipab_attendance_report | 17.0.1.5.2 | **Deployed 2026-05-10** — Glenda calibration WA-ACK: wa_number field, /glenda-calibracion/<token> route, WA mismatch HR alert, notice_key=glenda_calibracion_v1 |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | Installed (2025-12-21) |
| ueipab_hr_employee | 17.0.1.2.0 | **Deployed 2026-05-11** — Employee Private Info Request (token form, 14 fields, Fase 1 campaign 44 empl, auto-reminders, logo + Fase 1 badge) |
| ueipab_bounce_log | 17.0.1.4.0 | **Deployed 2026-05-10** — Glenda dependency |
| ueipab_ai_agent | 17.0.1.31.4 | **Deployed 2026-05-10** — Glenda LIVE + BCV rate context + ACTION:QUERY_BALANCE invoice breakdown + daily digest script |

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

- **Module:** `ueipab_attendance_report` v17.0.1.5.2 | **Testing attendance_guide id=84**, **Production id=58**
- **Model:** `hr.notice.acknowledgment` — one record per employee per `notice_key`; fields: `notice_key`, `notice_label`, `employee_id`, `token`, `state`, `sent_date`, `ack_date`, `ack_ip`, `wa_number`
- **Token:** UUID auto-generated on `create()`, used in public URL
- **Public route:** `/notice-ack/<token>` — `auth='public'`; for generic keys: one-click ACK; for `_WA_FORM_KEYS` (e.g. `glenda_calibracion_v1`): shows WA-number form first
- **Glenda calibration flow:** GET `/notice-ack/<token>` → WA form (pre-filled from `employee.mobile_phone`) → POST `/glenda-calibracion/<token>` → saves `wa_number`, updates `employee.mobile_phone` if empty; if number differs from Odoo record → auto-update + HR alert email
- **WA mismatch alert:** sent to `recursoshumanos@ueipab.edu.ve` with old/new number, employee name, timestamp
- **Email template model:** `hr.notice.acknowledgment` — `object.employee_id.name`, `object._get_ack_url()` for button; CC `recursoshumanos@ueipab.edu.ve` on every send
- **ACK button in body:** `<a t-att-href="object._get_ack_url()">` — stored via SQL to bypass ORM sanitizer
- **Menu:** Payroll → Reports → Notice Acknowledgments (WA Calibración column shows confirmed number)
- **Future campaigns:** change `notice_key` only — add key to `_WA_FORM_KEYS` in controller if WA capture needed
- **Infrastructure:** `/notice-ack/` + `/glenda-calibracion/` added to nginx Odoo proxy; `dbfilter=^DB_UEIPAB$` on prod; `web.base.url=https://odoo.ueipab.edu.ve`
- **Glenda calibration notice_key:** `glenda_calibracion_v1` | Testing mail.template id=86 | Production mail.template id=TBD

### Glenda BCV Rate Context

- **Param:** `ai_agent.bcv_rate_context` (JSON) — set by `scripts/sync_bcv_to_odoo.py` every 30 min via `/etc/cron.d/sync_bcv_odoo`
- **Source:** BCV MySQL `exchange_rates_bcv.bcv_rates` (host `127.0.0.1`, user `bcv_script`) — same DB used by `/var/www/dev/bcv/` Flask app (gunicorn on `:5001`)
- **JSON shape:** `{"current": {"rate": 499.86, "date": "YYYY-MM-DD", "updated_at": "YYYY-MM-DD HH:MM"}, "history": [{"date": ..., "rate": ..., "min_rate": ..., "max_rate": ...}, ...]}`
- **History:** last 30 days of daily rates (AVG/MIN/MAX per day)
- **Skill:** `general_inquiry.get_context()` reads param → passes `bcv` key in context dict → `_build_bcv_block()` formats it into the system prompt between `_INSTITUTIONAL_KNOWLEDGE` and `CONTEXTO`
- **Why host-side sync:** Odoo Docker container cannot reach host `127.0.0.1:5001` (Flask) or `127.0.0.1:3306` (MySQL); XML-RPC push from host is the established pattern
- **Glenda can answer:** ¿Cuál es la tasa BCV hoy? / ¿Cuánto son $X en bolívares? / ¿Cuál era la tasa el [fecha en historial]? — if date not in history, directs to `bcv.gob.ve`
- **Fallback:** if param missing/empty, `_build_bcv_block()` returns a "no disponible, consulta bcv.gob.ve" message — Glenda degrades gracefully

### Glenda Invoice Balance Query (ACTION:QUERY_BALANCE)

- **Trigger:** Claude appends `ACTION:QUERY_BALANCE:FOUND` (partner identified by phone) or `ACTION:QUERY_BALANCE:V-XXXXXXXX` (cédula provided by customer) to its response
- **Handler:** `general_inquiry._handle_balance_action()` → resolves partner → `_query_partner_balance()` → `account.move` ORM query (posted out_invoices, payment_state in not_paid/partial, amount_residual_signed > 0, partner + children)
- **Output:** `_format_balance_message()` — WA-friendly breakdown with per-invoice bullets (ref, date, residual, description from line_ids, partial flag) + BCV VEB conversion
- **Delivery:** `ai_agent_conversation.action_process_reply()` checks `action.get('balance_message')` → sends as separate WA message + logs in `ai.agent.message`
- **Context pre-load:** when partner found by phone, `get_context()` runs `_query_partner_balance()` immediately — total + count injected into system prompt so Claude can answer without waiting for ACTION resolution
- **Security:** only shows balance for the identified partner — never for a different contact
- **Fallback:** cédula not found → "no encontré cuenta con esa cédula" message to customer

### Glenda Daily Executive Digest (glenda_daily_digest.py)

- **Script:** `scripts/glenda_daily_digest.py` | **Cron:** `/etc/cron.d/glenda_daily_digest` — daily 07:00 VET (`0 11 * * *` UTC), sources `/root/.odoo_agent_env_prod`
- **Target:** `gustavo.perdomo@ueipab.edu.ve` | **From:** `recursoshumanos@ueipab.edu.ve`
- **Data window:** previous calendar day, UTC-adjusted (VET = UTC-4: 04:00 UTC start)
- **Queries:** `ai.agent.conversation` (created OR last_message in window) + `ai.agent.message` (for token counts) via XML-RPC
- **5 sections:**
  1. KPI cards — total, resolved, escalated, timeout, active, resolution rate + WA counts + Claude cost
  2. By-skill table — total/resolved/escalated/timeout/avg turns/top topics per skill
  3. Topic frequency — 12-category keyword detection from `resolution_summary` + `escalation_reason`
  4. Escalations/unresolved — table for future enhancement input (what Glenda couldn't handle)
  5. Suspicious activity — same phone >3 convs, avg tokens/turn >600 (injection probe), 01:00-05:00 VET activity, turns >18
- **Manual run:** `python3 scripts/glenda_daily_digest.py --env production [--date YYYY-MM-DD] [--dry-run]`
- **Email delivery:** creates `mail.mail` as `state=outgoing`, Odoo scheduler sends within minutes

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
- **Escalation:** `ACTION:ESCALATE:desc` marker → Freescout ticket via bridge script
- **Image support (v1.13.0):** Multimodal — Glenda sees customer screenshots via Claude vision
- **Re-trigger:** `ACTION:ALTERNATIVE_PHONE:04XXX` → pre-fills wizard with new number
- **Email verification:** `ACTION:VERIFY_EMAIL:email` → sends verification email
- **Family email context:** Akdemia data prevents duplicate email proposals
- **Credit Guard:** Kill switch at `ai_agent.credits_ok`, checks WA + Claude spend every 30 min
- **Health Monitor:** Dual-layer SPAM detection + auto-failover to backup number
- **Holiday schedule (v1.15.0):** Public holidays use weekend hours (09:30-19:00) via `ai_agent.holidays` param
- **Per-skill schedule (v1.27.0):** `respect_schedule` field on `ai.agent.skill` — `False` = 24/7. `general_inquiry` is 24/7, all others respect contact window
- **General Inquiry skill (v1.26.0):** Handles unsolicited inbound WA messages — auto-creates conversation, identifies contact, routes handoff to `pagos@` (billing) or `soporte@` (general) based on inquiry type
- **Billing routing (v1.28.0):** `ACTION:HANDOFF:name|summary|billing` → `pagos@ueipab.edu.ve`; `ACTION:HANDOFF:name|summary|support` → `soporte@ueipab.edu.ve`
- **turn_count fix (v1.27.1):** Dedup-only records (empty body) excluded from turn counter
- **Flyer support:** `ACTION:SEND_FLYER:key` → `https://dev.ueipab.edu.ve/flyers/` (param: `ai_agent.flyer_base_url`). **⚠️ Suspended** — MassivaMóvil `type=photo` queues but does NOT deliver to end user; awaiting tech support.
- **Credit Guard fail-threshold:** Kill switch activates after N consecutive failures (param `ai_agent.credits_fail_threshold`, default 2). Prevents false-positives from transient API timeouts.
- **2026-2027 enrollment + PDVSA policy:** Inscripción $197,38, Seguro $15, Enc.inglés $30, Enc.digital bach. $36, Kurios $10, MOA $25. PDVSA benefit discontinued — new prospect → billing handoff; existing distressed family → empathetic + `pdvsa_retention` alert to `pagos@`.
- **Farewell message fix:** `resolved` conv allows new conv within 24h (customer farewell ACK); `timeout`/`failed` → blocked.
- **Quotation engine:** 4-section quote: mensualidad + inscripción + costos anuales ($55/std: seguro $15 + enc.inglés $30 + olimpiadas $10; +$36 bach) + TOTAL PRIMER MES. Sibling discounts: 2nd 5%, 3rd 6%, 4th+ 7% on mensualidad. Glenda asks bach level + # children; presents per-child breakdown, hands off with structured quote.
- **Sep 2026 tariff forecast:** inscripción $264,48, mensualidad $264,48, pronto pago $241,16 (8.816% disc). Current $197,38 "hasta agosto 2026".
- **general_inquiry timeout fix (v1.29.8):** Added `get_reminder_message`, per-conv `try/except` in `_cron_check_timeouts`, `max_turns` raised 10→25.

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

**Testing lockout:** `ai_agent.active_db=''` on testing Odoo — all AI agent crons self-skip.

**Contact schedule (VET):** Weekdays 06:30-20:30, Weekends/holidays 09:30-19:00. `general_inquiry` exempt (24/7).

**WhatsApp accounts:** Primary +584148321989 (dedicated), Backup +584248944898, Tertiary +584148321963 (manual only).

### Testing Environment Status (2026-05-10)

| Setting | Value |
|---------|-------|
| `ai_agent.dry_run` | `False` |
| `ai_agent.active_db` | `''` (locked — crons self-skip) |

### Production Migration Checklist

**COMPLETE as of 2026-05-10.** All gaps resolved. See [Full Checklist](documentation/AI_AGENT_MODULE.md) for history.

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
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [WebSocket/Nginx Fix](documentation/WEBSOCKET_NGINX_FIX.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)

### Known Issues

**FIXED** (see [Changelog](documentation/CHANGELOG.md) and linked docs for details):
- PAY1 Journal Sequence/Date Mismatch — FIXED v1.61.2 (wizard auto-fix button + `action_validate_payslips` sets `slip.date` to sequence month start)
- Quincena Salary Rule — FIXED 2026-02-25: `period_days/30.0` → `monthly/2.0` for all V2 rules; see [HR Letter](documentation/HR_LETTER_FEBRERO28_CORRECTION.md)
- Representante Contact Sync — FIXED 2026-02-15: 318/318 contacts fully synced both envs
- AI Agent Poll Cron Rollback Bug — FIXED v1.19.0 (savepoint isolation + global WA dedup + phone-based conv guard)
- HR Loan one-loan-per-employee constraint — FIXED v1.66.0 (unlimited concurrent loans via MRO bypass)
- HR Loan: batch cancel not cancelling draft payslips — FIXED v1.66.1
- HR Loan: LO inputs auto-add on compute (conservative guard) — FIXED v1.66.4
- HR Loan email templates out of sync (prod) — FIXED 2026-05-06 via `scripts/sync_lo_to_production.py`
- HR Loan backdated approval PAY1 mismatch — FIXED v1.66.5 (`today` used when `loan.date` in past month)
- HR Loan batch total_net_amount missing LIQUID_NET_V2 — FIXED v1.65.0
- HR Loan `action_paid_amount` double-accounting + name conflict — FIXED v1.64.6 (no-op override on `hr.loan.line`)
- PAY1 journal sequence contamination (LOAN/ prefix) — FIXED DB-only 2026-04-27 (entries renamed to PAY1/2026/04/0003-0006)
- HR Loan exchange rate not updating on date change — FIXED v1.64.8 (`for_date` param + `_onchange_date_rate`)
- **LIQUID_ANTIGUEDAD_V2 Bug — FIXED 2026-04-08** (prod rule id=29, test id=59); ⚠️ **Open HR case:** SLIP/447 JOSEFINA RODRIGUEZ — $420.87 overpayment, Acuerdo drafted 2026-04-24, awaiting signatures. See [Resolution Doc](documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md).
- Payroll Disbursement + Total Net Payable — FIXED v1.67.1→v1.67.4: use `struct_rule_ids = payslip.struct_id.rule_ids.ids`; V2 detector = `VE_NET_V2` (not `VE_BASIC_V2`); bonus structures need `parent_id=False`

**PENDING:**
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)
- [Freescout Phone Conversation Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) — `Undefined array key 0` in `SendReplyToCustomer.php:76`; fixed upstream, update Freescout on next release
- **Decreto Ingreso Mínimo $240 (2026-04-30):** LUIS RODRIGUEZ ($191.37, gap +$48.63) y NIDYA LIRA ($228.67, gap +$11.33) — incrementar `ueipab_bonus_v2` en contratos. Ver [Análisis](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md).

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
