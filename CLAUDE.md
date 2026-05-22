# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-05-21 (v26)

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
| 10 | AR-I Portal | Testing | `ueipab_ari_portal` | Portal `/my/ari`; nginx whitelist includes `my` (2026-05-17) |
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
| 49 | PDVSA Continuity Campaign | Production | `ueipab_attendance_report` | [Docs](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) — deadline 08-Jun-2026 |
| 50 | Representante Continuity Campaign | Pending (letter not ready) | `ueipab_attendance_report` | [Docs](documentation/REPRESENTANTE_CONTINUITY_CAMPAIGN.md) |
| 51 | Glenda Auto Draft Payment (WA) | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 52 | Pagos@ Email Receipt Processor | Production | Script | `scripts/pagos_receipt_processor.py` — [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 53 | WA Invoice Reminder | Production | Script + Wizard | [Plan](documentation/WA_INVOICE_REMINDER_PLAN.md) |
| 54 | Glenda OdooBot Bridge | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 55 | Glenda Silent Timeout + Quiet Hours | Production | `ueipab_ai_agent` | [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 56 | DMARC Report Processor | Production | Script + Cron | `scripts/dmarc_report_processor.py` — [CEO](documentation/CEO_COMMAND_CENTER.md) |
| 57 | Glenda Telegram Channel | Production | `ueipab_ai_agent` | [Docs](documentation/GLENDA_TELEGRAM_CHANNEL.md) — `@GlendaUeipabBot`; deep-link `EMP_{id}` |
| 58 | Absence Notification System | Production | Script + Cron + `ueipab_ai_agent` | `scripts/absence_processor.py`; see Key Technical Patterns |
| 59 | Glenda School Account Help | Production | `ueipab_ai_agent` + Script | `ACTION:SCHOOL_ACCOUNT_HELP`; see Key Technical Patterns |
| 60 | Budget Consultation 2026-2027 | Production | `ueipab_ai_agent` + Script | price gate lifted; [Docs](documentation/BUDGET_VOTE_EMAIL.md) |
| 61 | Glenda Kurios Robotics Link | Production | `ueipab_ai_agent` | Shares `https://info.kuriosedu.com/books/kmbs/#p=3` on request |
| 62 | Glenda MOA Spelling Bee 2026 | Production | `ueipab_ai_agent` | Jun 1 Primaria / Jun 2 Media General |
| 63 | Glenda Telegram Parent Announcement | Production | Script | `scripts/send_glenda_telegram_email.py` |
| 64 | Glenda WA→Telegram Speed Suggestion | Production | `ueipab_ai_agent` | WA slow-response → recommends Telegram; WA-channel only |
| 65 | Glenda Almacenes París — Distintivo Escolar | Production | `ueipab_ai_agent` | ~$8–$10/u |
| 66 | Attendance ACK → CC recursoshumanos@ | Production | `ueipab_attendance_report` | `attendance_ack.py` `_notify_rrhh()` — CC recursoshumanos@ on ACK |
| 67 | Glenda Seguro Escolar 2026-2027 | Production | `ueipab_ai_agent` | Seguros Caracas Alt.2; $30.58/alumno |
| 68 | Manual WA/Telegram Trigger from AI Agent | Production | `ueipab_ai_agent` | AI Agent → Operaciones → Iniciar Conversación; Canal toggle WA/Telegram (v57.5) |
| 69 | Glenda Family Billing Enrichment | Production | `ueipab_ai_agent` + Script | `school.family_billing_json`; `sync_family_billing.py` 07:30 VET; [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 70 | Glenda AI Supervisor | Production | Script + Cron | `scripts/glenda_supervisor.py`; scores 1–5; CEO email + OdooBot DM + WA if critical |
| 71 | Glenda Staff Operational Guide | Production | Script | `scripts/create_glenda_ops_guide_email.py` |
| 72 | Glenda Welcome Menu + Budget UX v52 | Production | `ueipab_ai_agent` | 5-option menu; balance gate; A vs B quotation; [Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) |
| 73 | Glenda Prior Conversation History | Production | `ueipab_ai_agent` | `_get_prior_conversation_summary()` in `general_inquiry.py`; 1-2 convs (7-day window) |
| 74 | Freescout Pagos@ Bridge | Production | `ueipab_ai_agent` + scripts | `ai.agent.freescout.task`; AI Agent → Operaciones → Pagos Freescout |

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

**Odoo base:** `odoo:17.0` build `17.0-20260504` (commit `d66bb0d7`) — both envs as of 2026-05-10.
**Last sync verified:** 2026-05-22 — all modules in sync ✓

| Module | Version | Notes |
|--------|---------|-------|
| hr_payroll_community | 17.0.1.0.0 | testing only |
| ueipab_payroll_enhancements | 17.0.1.70.2 | both |
| ueipab_hr_contract | 17.0.2.0.0 | both |
| ueipab_bounce_log | 17.0.1.4.0 | both |
| ueipab_ai_agent | 17.0.1.57.12 | both |
| ueipab_attendance_report | 17.0.1.6.16 (testing) / 17.0.1.6.15 (prod — pending SSH deploy) | both |
| ueipab_hr_employee | 17.0.1.3.0 | both |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | both |
| ueipab_ari_portal | 17.0.1.1.0 | testing only |
| ohrms_loan + ohrms_loan_accounting | 17.0.1.0.0 | testing only |

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
- **Config:** `ir.config_parameter` keys `ai_agent.freescout_api_url` + `ai_agent.freescout_api_key` (production). File `/opt/odoo-dev/config/freescout_api.json` is dev-only fallback — Docker container cannot read host paths. All Odoo model methods must use the param lookup first.
- **Auth:** `X-FreeScout-API-Key` header; Conversation ID = DB primary key, NOT display number
- **`PUT /api/conversations/{id}`** — status must be **string**; `byUser` (int) **required** on status changes
- **`POST /api/conversations/{id}/threads`** — note: `{"type":"note","text":"<html>","user":<int>}`; `user` required
- **Hybrid:** API for writes; SQL for reads + `threads.body` search

### Absence Notification System (Feature #58)

**Script:** `scripts/absence_processor.py` | **Cron:** `/etc/cron.d/absence_processor` — weekdays 06:00–17:00 VET

- **Entry:** email parent→soporte@ OR WA/Telegram `ACTION:NOTIFY_ABSENCE:name|grade|reason` → Freescout conv → cron
- **Per-conv:** assign Josefina (user_id=8), CC soporte@+arcides.arzola@+norka.larosa@(media)/david.hernandez@(prim)+teachers, OdooBot DM, 24h follow-up
- **Teacher lookup:** `control_asistencias` DB `profesor_seccion` JOIN `usuario`; grade→`id_grado` via `_GRADE_PATTERNS`
- **Detection:** keyword pre-filter → Haiku extracts fields; failure → skip (no false positives). Marker: `[AUSENCIA]` prefix.

### Glenda School Account Help (Feature #59)

**Action:** `ACTION:SCHOOL_ACCOUNT_HELP:cedula|student_name|grade` — 3-factor verify: (1) partner by phone/Telegram; (2) cédula matches `res.partner.vat` (mismatch → deny); (3) student fuzzy-matched in `school.student_directory_json`.

**Directory:** `scripts/sync_google_directory.py --live`; cron 07:00 VET; 224 active accounts. Name: exact → word-overlap ≥2. Cédula: strip `-`, `V/E/J/G/P` prefix.

**Akdemia reset:** `https://edge.akdemia.com/login#resetPasswordModal`. FS UNASSIGNED soporte@ (mailbox_id=3).

### Telegram Channel (ai.agent.telegram.service)

See [GLENDA_TELEGRAM_CHANNEL.md](documentation/GLENDA_TELEGRAM_CHANNEL.md) for full deployment docs (welcome menu, contact sharing, `/vincular`, auto-link via cédula, wizard invite).

**Critical Odoo 17 rename:** PostgreSQL tables are `discuss_channel` / `discuss_channel_member` (not `mail_channel`). ORM: `discuss.channel` / `discuss.channel.member`.

**Webhook cursor abort:** wrap CEO notification calls with `with self.env.cr.savepoint():` — raw SQL failure inside a webhook aborts the PG cursor; savepoint confines the rollback.

**Token lookup:** `@ormcache` throws `KeyError` after a `create()` mid-transaction. `_token()` has a direct SQL fallback: `env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", [key])`.

**`address_home_id` not searchable:** group-restricted in Odoo 17. Use `user_id.partner_id` for partner→employee lookups.

**Monitoring:** `https://odoo.ueipab.edu.ve/web#action=830&cids=1&menu_id=569` → filter Canal=Telegram.

### Glenda Family Billing Enrichment (Feature #69)

**Cache:** `school.family_billing_json` (199 families); `scripts/sync_family_billing.py --live` — cron 07:30 VET. Lookup: phone → fuzzy student name. Injected block includes monthly, discount, forecast, annual costs (qty × $101.58 = seguro $30.58 + inglés $25 + olimpiadas $10 + enciclopedia $36).

**Iniciar Conversación (v57.5):** WA: draft/send; `initial_message` skips greeting. Telegram: `partner_id` required, sends FAM_ invite via WA. `🔄 Actualizar` reloads form in-place.

**Glenda AI Supervisor (Feature #70):** `scripts/glenda_supervisor.py`; scores 1–5; CEO email + OdooBot DM + WA if critical.

### Freescout Pagos@ Bridge (Feature #74)

**`pagos_faq_email_checker.py`** — 100% REST API (no pymysql). `fs_get_conversations_page()` + `fs_get_conversation_detail()`.

**`pagos_receipt_processor.py`** key patterns:
- **Email lookup:** use `ilike` (not `=ilike`) — Odoo stores multi-email as `a@x.com;b@x.com`; exact match fails (v57.10).
- **Google Sheet fallback:** email miss → `sheets_lookup_by_email()` checks `Customers!B2:J` → `odoo_find_partner_by_name()`. Spreadsheet: `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA`.
- **Advance payment:** invoice match fails + balance=0 → `is_advance_payment=True` → labels "💰 Pago adelantado"; payment created+confirmed via `action_post()` (v57.11).
- **Bridge upsert:** `upsert_freescout_task()` at every non-skipped exit.

**`action_reprocess()` (v57.11/v57.12):** advance-payment path → GPT-4o-mini Vision on thread image. `_parse_monto(v)`: normalises Venezuelan comma-decimal (`'85.039,58'` → `85039.58`). `_load_fs_config()`: reads `ir.config_parameter`; file fallback dev-only (same pattern in `ai_agent_conversation.py`).

**`ai.agent.freescout.task`** — UI: AI Agent → Operaciones → Pagos Freescout. Status: pending/identified/no_partner/no_receipt/duplicate/success/error.

**`sync_customers_sheet.py`** — syncs `Customers!B2:J` → `school.customers_sheet_json` (email→name). Cron: 11:30 UTC. Used by `_get_customers_sheet_context()` for unidentified contact hints.

### Glenda Technical Patterns

See [GLENDA_TECHNICAL_PATTERNS.md](documentation/GLENDA_TECHNICAL_PATTERNS.md) for full reference on: Silent Timeout/Quiet Hours, OdooBot Bridge (Discuss), Auto Draft Payment / Journal Map, BCV Rate Context, Invoice Balance Query, Daily Executive Digest, Quotation Engine & Enrollment info.

### Attendance Daily Alert + check_out Auto-fill (scripts/attendance_daily_alert.py)

**Crons:** `/etc/cron.d/attendance_daily_alert`
- `30 11 * * 1-5` — morning 11:30 VET: recap yesterday (no attendance / missing exit / <5h) → HTML email to employee CC recursoshumanos@
- `30 23 * * 1-5` — evening 23:30 VET: employees with check_in but no check_out → one SSH call to Router 2 (`172.28.10.10` ZeroTier) → Mikrotik hotspot logout log → latest logout per employee. WiFi found + <20:00 VET + after check_in → write that time. Fallback → 14:00 VET (18:00 UTC). No email sent.

Special-schedule employees (ids 571/606/610) skipped entirely in both modes.

**State:** `attendance_daily_alert_state.json` — `morning_DATE_EMPID` / `evening_DATE_EMPID`; entries >14 days pruned. WiFi coverage: 8/45 employees in `payroll_db.wifi_hotspot_users`.

**Correction button (2026-05-22):** `get_fix_url_for_employee(emp_id, date)` looks up the `hr.attendance.report` covering that date (`state=sent/draft`) and injects an orange "📝 Solicitar Corrección" button linking to `/attendance-fix/<token>`. Falls back to plain email card if no matching report exists. Q2 quincena reports must be generated before alerts fire for them to have tokens. CC `recursoshumanos@ueipab.edu.ve` via `mail.mail.email_cc`.

### Attendance Biweekly Report Wizard (v6.4 patterns)

- **Employee default:** `_get_payroll_employees()` — latest closed `hr.payslip.run` employees (e.g. MAYO15 = 44). Fallback: `contract_ids.state='open'`. Wizard file: `ueipab_attendance_report/wizard/hr_attendance_report_wizard.py`
- **Resend skips acknowledged:** `action_resend_reports()` domain includes `('state','!=','acknowledged')` + guard in `_send_emails()`. Never re-emails employees who already confirmed.
- **No UI timeout:** `force_send=False` in `_send_emails()` — emails queue as `state='outgoing'`, mail queue cron delivers. Before: 44 × 2.5s = 110s → HTTP worker killed. After: <1s return.
- **Mail queue cron:** id=3 "Mail: Email Queue Manager" in production. `force_send=False` means emails wait for next scheduled run. If immediate delivery needed, trigger manually: `models.execute_kw(db, uid, key, 'ir.cron', 'method_direct_trigger', [[3]])`. Sent `mail.mail` records are deleted from table on success (0 results = all sent).
- **ACK CC (v6.4):** `attendance_ack.py` `_notify_rrhh()` — fires when employee confirms via `/attendance-ack/<token>` only. CC to `recursoshumanos@ueipab.edu.ve` is on ACK confirmation, NOT on reminder send.
- **States:** `draft` → `sent` (queued) → `acknowledged` (confirmed via token link). `is_historical` records auto-acknowledged on create.
- **ORM query fields:** `date_from`, `date_to`, `month` (int), `year` (int), `quincena` (`'1'`/`'2'`). NOT `period_start`/`period_end` — those don't exist and raise `ValueError`.
- **Production email template:** id=53 "Attendance Report - Quincenal" (`ueipab_attendance_report.email_template_attendance_report`).
- **Test account exclusion:** "Administrador 3Dv" has two duplicate `hr.employee` records (ids 574 and 764, both `tdv.devs@gmail.com`, no dept/job). Exclude from all attendance sends: `('employee_id','not in',[574,764])`.

### WA & Email Invoice Reminder

See [WA_INVOICE_REMINDER_PLAN.md](documentation/WA_INVOICE_REMINDER_PLAN.md) for full technical reference.
- **Wizard:** Accounting → Customers → Recordatorio de Saldo; Tags REP=25 / PDVSA=26 / VIP=30 (excluded)
- **WA cron:** weekdays 07:00 VET; state file `scripts/wa_invoice_reminder_state.json`

### CEO Command Center (wa_monitor)

See [CEO_COMMAND_CENTER.md](documentation/CEO_COMMAND_CENTER.md) for full reference.
- Params: `wa_monitor.ceo_email` / `wa_monitor.ceo_phone` / `wa_monitor.tertiary_notified_ids`
- **OdooBot DM** = primary (no throttle); **WA backup** = 120s anti-spam throttle

### DMARC Report Processor

See [CEO_COMMAND_CENTER.md](documentation/CEO_COMMAND_CENTER.md). Script: `scripts/dmarc_report_processor.py`; cron 10:30 UTC daily. Source: FreeScout `finanzas@` (mailbox_id=5). IP classes: `good`/`third_party`/`unknown`. Alert: unknown IPs with dkim/spf=pass → OdooBot DM. Akdemia SendGrid `50.31.44.87` = `third_party` (expected). SPF upgrade to `-all` planned ~2026-05-27.

**⚠️ DMARC status (2026-05-20):** Policy changed `p=reject` → `p=none` (DigitalOcean record id=1818865872) because Akdemia sends emails FROM `@ueipab.edu.ve` via SendGrid (`em.akdemia.com`, IP `50.31.44.87`) without DKIM signing for `ueipab.edu.ve`. SPF alignment also fails (Return-Path: `@em.akdemia.com` ≠ org domain `ueipab.edu.ve`). With `p=none`, DMARC is monitor-only — Akdemia emails deliver to inbox, reports still sent to `finanzas@`. **Pending permanent fix:** set up DKIM domain authentication in Akdemia/SendGrid admin → generate 3 CNAME records for `ueipab.edu.ve` → add to DigitalOcean → verify → revert DMARC to `p=reject`. DO NOT upgrade SPF to `-all` until DKIM is live and DMARC is back to `p=reject`.

### HTML Email / WA Broadcast Templates (ad-hoc)

Sent via `mail.mail` XML-RPC (`state='outgoing'`, trigger queue cron id=3 with `method_direct_trigger`). These are one-off campaigns, not saved `mail.template` records.

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
- **⚠️ Active account as of 2026-05-22:** **BACKUP (+584248944898)** — primary broken (all sends failing at WA delivery level since msg≈76649; Massiva support ticket open). Restore: fix on Massiva dashboard → `whatsapp_account_phone=+584148321989`, `whatsapp_account_id=primary_uid`, `whatsapp_active_account=primary`, clear `whatsapp_flagged_phone/date`.
- **Anti-spam:** Min 120s between sends
- **Send:** `POST /api/send/whatsapp` | **Validate:** `GET /api/validate/whatsapp` | **Receive:** `GET /api/get/wa.received`
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`
- **Inbox-to-backup re-routing (2026-05-22):** When primary can receive but not send, manually poll `GET /api/get/wa.received?account=primary_uid` and resend failed outbound messages via backup uid. Then send Telegram invite as follow-up nudge.

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Use case:** AI backbone for WhatsApp bounce resolution (~$0.005 per conversation)
- **Retry policy (v48.0):** 2 retries on HTTP 429 — delays 3s, 6s — then OpenAI fallback
- **OpenAI fallback (v48.0):** `gpt-4o-mini` via `requests` (no SDK). Triggers on: (1) Claude 429 after all retries, (2) `credits_ok=False`. Toggle: `ai_agent.openai_fallback_enabled=True`. Key: `ai_agent.openai_api_key`. Model override: `ai_agent.openai_model`.
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
- **School Account Help:** `ACTION:SCHOOL_ACCOUNT_HELP:cedula|student_name|grade` → 3-factor verify → student email from Google Directory + Akdemia reset link; UNASSIGNED FS soporte@ ticket
- **Absence notification:** `ACTION:NOTIFY_ABSENCE:name|grade|reason` → Glenda creates Freescout soporte@ conv → `absence_processor.py` cron picks it up within 10 min
- **Flyer/Audio:** **⚠️ WA only** — skipped on Telegram (`channel != 'whatsapp'` guard in `_send_flyer()`)
- **Farewell:** `resolved` conv → new conv allowed within 24h; `timeout`/`failed` → blocked
- **Calibration:** WA + Telegram conversations both count toward bonus; feedback linked via `user_id.partner_id`

### WA Poll Cron — Account Filter Note

Primary account +584148321989. Poll cron uses `account_id=None` (all accounts) to catch any replies to old number.

### Competitor/Suspicious Contact Pattern

**Known risk:** Competitors may contact Glenda via Telegram or WA to probe pricing.
- **Price gate** is the primary defence — Glenda only quotes $197.38 / $162.39, never proposed budget amounts
- **Detection signal:** immediately asks about next-year costs with no child/grade context
- **Action:** Let Glenda handle within guardrails. Re-trigger stuck conv via shell: `env['ai.agent.conversation'].browse(ID).action_process_reply(message_text='...', wa_message_id=0); env.cr.commit()`

### Environment Status

**Production:** `dry_run=False`, `active_db=DB_UEIPAB`, v56.0. WA poll 5min. Telegram webhook `odoo.ueipab.edu.ve`. Hours VET: Weekdays 06:30-20:30, Weekends 09:30-19:00. `general_inquiry` exempt (24/7). Kill switch: `ai_agent.telegram_enabled=False`.

**Testing:** `dry_run=False`, `active_db=DB_UEIPAB` (locked — crons self-skip). Telegram webhook `dev.ueipab.edu.ve`.

---

## Akdemia Data Pipeline

See [Full Documentation](documentation/AKDEMIA_DATA_PIPELINE.md). Scraper: `akdemia_scraper.py` (Playwright); cron daily 06:00 VET; phases 2a–5 (Freescout + Sheets sync).

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
- [Bounce Email Cleanup Procedure](documentation/BOUNCE_EMAIL_CLEANUP_PROCEDURE.md) — manual campaign bounce cleanup: Freescout API → Odoo contacts → Google Sheet → BounceEmail tab log
- [Akdemia Data Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md)
- [Freescout API Migration Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md)

### School Operations

See Feature table rows 49–67. Key patterns: Absence Processor (Feature #58), School Account Help (Feature #59), Budget Consultation (Feature #60) — all detailed in Key Technical Patterns above.

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

**PENDING — Code / Infrastructure:**
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md) — `tdv_multi_currency_account`; both envs
- [Freescout Phone Conversation Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) — `Undefined array key 0` in `SendReplyToCustomer.php:76`; fixed upstream, update Freescout on next release
- **MassivaMóvil Webhook wrong Content-Type** — controller uses `type='json'` but MassivaMóvil sends form-encoded POST. Fix: change to `type='http'`, parse `request.httprequest.form.get()`, `json.loads(data)`. Currently falling back to 5-min poll cron.
- **Internal number guard** — Gustavo's +584142337463 triggers `general_inquiry` conversations. Fix: add `ai_agent.general_inquiry_blocked_phones` param checked before creating a conversation.

**PENDING — Data / Contract:**
- **Decreto Ingreso Mínimo $240 (2026-04-30):** LUIS RODRIGUEZ (total $151.38, gap **+$88.62**) y NIDYA LIRA (total $188.67, gap **+$51.33**) — incrementar `ueipab_bonus_v2` en contratos (ambos envs). Ver [Análisis](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md).
- **Josefina Phase 2** — liquidation SLIP confirmed (done). Pending: `LIQUID_OTHER_DED_V2` rule in `LIQUID_VE_V2` to deduct $420.87 overpayment from Year 2 liquidation via `ueipab_other_deductions`. See `documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md`.

**PENDING — External / Infrastructure:**
- **WA Primary +584148321989 broken** (2026-05-22) — all sends fail at WA delivery; Massiva support ticket open. Glenda on backup (+584248944898). Once Massiva fixes: reconnect in dashboard → restore config params → clear flagged_phone.

**PENDING — Production Deploy (needs SSH key to 10.124.0.3):**
- **`ueipab_attendance_report` v6.16** — correction form handles missing_exit days + button shows for both absent/missing_exit. Testing upgraded; production still v6.15. Deploy: `scp -r addons/ueipab_attendance_report root@10.124.0.3:/home/vision/ueipab17/addons/ && ssh root@10.124.0.3 "docker exec 0ef7d03db702_ueipab17 /usr/bin/odoo -d DB_UEIPAB -u ueipab_attendance_report --stop-after-init && docker restart 0ef7d03db702_ueipab17"`

**PENDING — Refactor:**
- **`partner.communication.ack` misplaced in `ueipab_attendance_report`** — model, views, controller (`partner_ack.py`), and wizard belong in `ueipab_ai_agent` (or a new `ueipab_campaigns` module). Placed there for convenience when first built; all campaign logic lives in `ueipab_ai_agent`. Requires DB migration (model is live in production). Low urgency — zero functional impact. See [ACK_FORM_UX_IMPROVEMENTS.md](documentation/ACK_FORM_UX_IMPROVEMENTS.md) §Structural Note.

**BLOCKED — Waiting on external trigger:**
- **Seguro Escolar 2026-2027 → Glenda** — knowledge ready, blocked until budget results published 2026-05-26. Add to `_INSTITUTIONAL_KNOWLEDGE` in `general_inquiry.py`.
- **Representante Continuity Campaign** — script ready (`send_representante_communication.py`), blocked until letter content (LETTER_URL + BULLET_1-3 + EMAIL_HEADLINE) provided.
- **Banco Plaza API** — QA/eval phase; credentials pending from Banco Plaza team.

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
