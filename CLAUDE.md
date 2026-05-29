# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-05-29 (v35)

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

These are independent — updating one does NOT update the other. On 2026-05-19 the second cron was mistakenly removed (deemed "duplicate"), causing a 10-day gap in `res.currency.rate` (May 20–28). Restored + backfilled 2026-05-29.

---

## Payslip Batch Features

Date Sync (auto-recomputes), Total Net Payable (V1/V2/Aguinaldos), Exchange Rate Application + Auto-Population (BCV/last batch), Email Template Selector, Advance Payment (% multiplier, [details](documentation/ADVANCE_PAYMENT_SYSTEM.md)), Remainder Payment (linked to advance batch).

---

## Module Versions

**Odoo base:** `odoo:17.0` build `17.0-20260504` (commit `d66bb0d7`) — both envs as of 2026-05-10.
**Last sync verified:** 2026-05-28 (v33) — all modules in sync ✓

| Module | Version | Notes |
|--------|---------|-------|
| hr_payroll_community | 17.0.1.0.0 | testing only |
| ueipab_payroll_enhancements | 17.0.1.70.2 | both |
| ueipab_hr_contract | 17.0.2.0.0 | both |
| ueipab_bounce_log | 17.0.1.4.0 | both |
| ueipab_ai_agent | 17.0.1.57.19 | both |
| ueipab_attendance_report | 17.0.1.6.21 | both |
| ueipab_hr_employee | 17.0.1.3.0 | both |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | both |
| ueipab_ari_portal | 17.0.1.5.0 | both |
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

### Closed-Contract Payslip (terminated employee mid-batch)

When an employee's contract is in `close` state, `_get_contract()` filters it out → payslip gets `contract_id = False` and zero lines computed.

**Fix procedure (via XML-RPC / Odoo shell):**
1. `contract.write({'state': 'open'})` — temporarily re-open so `_get_contract()` finds it
2. If pro-rating is needed (e.g. employee worked 7 of 15 days): set `ueipab_salary_v2 = original × (2 × days/30)` and same for `ueipab_bonus_v2` — the rule's `/2` then yields the correct `days/30` amount
3. `payslip.action_compute_sheet()` — runs all rules correctly
4. `payslip.write({'contract_id': contract.id})` — `action_compute_sheet` does NOT write this back; must set manually
5. Restore original salary fields: `contract.write({'ueipab_salary_v2': orig, 'ueipab_bonus_v2': orig})`
6. `contract.write({'state': 'close'})` — restore final state
7. Adjust fixed lines (e.g. `VE_CESTA_TICKET_V2`) manually via `hr.payslip.line.write()`, then update `VE_GROSS_V2` and `VE_NET_V2` accordingly

**Cesta ticket pro-ration:** `$20 × days_worked / quincena_days` (e.g. 7/15 → $9.33). Update GROSS and NET lines to match.

**Note:** Deductions (SSO, PARO, FAOV, ARI) auto-scale correctly because their bases reference the salary/bonus rules. SSO stays near $0.05 regardless — it uses the minimum wage base by design.

**Reference:** SLIP/801 RAMON BELLO MAYO31 — 7 days (May 16–22), contract end 2026-05-22.

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

**HR Monitor:** `Employees → AR-I Portal → Confirmaciones de Guía` (action id prod=TBD, testing=969) — filtered `hr.notice.acknowledgment` list for `ari_guide_2026_v1` with ⚙️ Action → "📧 Enviar Recordatorio (pendientes)". Smart: form view sends to that employee only; list view sends to all pending.

**Blast script:** `scripts/create_ari_portal_guide_email.py --env production --bulk` — 43 employees sent 2026-05-28 (RAMON BELLO id=608 excluded — contract termination in progress). `_EXCLUDE_EMP_IDS = {608}`.

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

**Directory:** `scripts/sync_google_directory.py --live`; cron 07:00 VET; 224 accounts. Name: exact → word-overlap ≥2. Cédula: strip `-`, `V/E/J/G/P`. Akdemia reset: `https://edge.akdemia.com/login#resetPasswordModal`; FS UNASSIGNED soporte@.

### Telegram Channel (ai.agent.telegram.service)

See [GLENDA_TELEGRAM_CHANNEL.md](documentation/GLENDA_TELEGRAM_CHANNEL.md) for full deployment docs (welcome menu, contact sharing, `/vincular`, auto-link via cédula, wizard invite).

**Critical Odoo 17 rename:** PostgreSQL tables are `discuss_channel` / `discuss_channel_member` (not `mail_channel`). ORM: `discuss.channel` / `discuss.channel.member`.

**Webhook cursor abort:** wrap CEO notification calls with `with self.env.cr.savepoint():` to confine raw SQL rollback.

**Token lookup:** `@ormcache` throws `KeyError` after a `create()` mid-transaction. `_token()` has a direct SQL fallback: `env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", [key])`.

**`address_home_id` not searchable:** group-restricted in Odoo 17. Use `user_id.partner_id` for partner→employee lookups.

**Monitoring:** AI Agent → filter Canal=Telegram (action=830 in prod).

### Glenda Family Billing Enrichment (Feature #69)

**Cache:** `school.family_billing_json` (199 families); `scripts/sync_family_billing.py --live` — cron 07:30 VET. Lookup: phone → fuzzy student name. Injected block includes monthly, discount, forecast, annual costs (qty × $111.58 hasta 31 jul / $116.58 desde 1 ago = seguro $30.58 + inglés $35/$40 + olimpiadas $10 + enciclopedia $36).

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

### Leave Notification System (Feature #76 + #77)

**Scripts:** `scripts/leave_notification.py` + `scripts/hr_leave_attendance_digest.py`
**Crons:** `/etc/cron.d/leave_notification` (*/15 weekdays) + `/etc/cron.d/hr_leave_attendance_digest` (08:00 VET weekdays)

**leave_notification.py** — polls `hr.leave` for actionable states every 15 min:
- `confirm` → "📋 Nueva Solicitud de Permiso" email to recursoshumanos@ (blue header)
- `validate1` → "🔔 Segunda Validación Requerida" email to recursoshumanos@ (orange header)
- State file `leave_notification_state.json` tracks `notified_confirm_{id}` / `notified_validate1_{id}` separately — a confirm→validate1 transition fires a second email
- Test: `--test-email gustavo.perdomo@ueipab.edu.ve`

**hr_leave_attendance_digest.py** — daily digest (3 sections):
1. 🔴 Pending approvals split by stage: validate1 rows ("Validar →", orange) above confirm rows ("Aprobar →", blue)
2. 📅 30-day leave activity per employee (approved days / pending days / request count)
3. ⚠️ High-issue employees — parsed from `attendance_daily_alert_state.json` morning entries (threshold: `HIGH_ISSUE_THRESHOLD = 3`; consider raising to 5)

**Leave type validation matrix (prod):**
- `both` (2 approvals): Tiempo personal pagado, Sin pagar, Permiso Muerte (luto), Diligencia Personal, Cita Médica de un familiar
- `hr` (HR only): Tiempo personal por enfermedad, Lactancia, Cita Médica personal, Cuidados maternos, Reposo Postnatal
- `manager` (manager only): Días compensatorios

**Work schedule — Standard 40h (calendar_id=1):** Morning start corrected 08:00→**07:00 VET** on 2026-05-28. All weekdays now 07:00–12:00 + 13:00–17:00.

---

### Attendance Daily Alert + check_out Auto-fill (scripts/attendance_daily_alert.py)

**Crons:** `/etc/cron.d/attendance_daily_alert`
- `30 11 * * 1-5` — morning 11:30 VET: recap yesterday (no attendance / missing exit / <5h) → HTML email to employee CC recursoshumanos@. Skips if yesterday was a weekend (Sat/Sun) or holiday.
- `30 23 * * 1-5` — evening 23:30 VET: employees with check_in but no check_out → one SSH call to Router 2 (`172.28.10.10` ZeroTier) → Mikrotik hotspot logout log → latest logout per employee. WiFi found + <20:00 VET + after check_in → write that time. Fallback → 14:00 VET (18:00 UTC). No email sent.

Special-schedule employees (ids 571/606/610) skipped entirely in both modes.

**State:** `attendance_daily_alert_state.json` — `morning_DATE_EMPID` / `evening_DATE_EMPID`; entries >14 days pruned. WiFi coverage: 8/45 employees in `payroll_db.wifi_hotspot_users`.

**Correction button:** `get_fix_url_for_employee(emp_id, date)` looks up matching `hr.attendance.report` (state=sent/draft) → injects "📝 Solicitar Corrección" link to `/attendance-fix/<token>`. Falls back to plain card if no report. CC `recursoshumanos@` via `email_cc`.

**Leave cross-check (Feature #78):** Morning mode fetches `hr.leave` for yesterday via `get_leaves_for_date()`. If an employee has a matching leave, `_format_leave_context_html()` injects a colored context block into the alert email: green (✅ `validate`) or yellow (⏳ `confirm`/`validate1`). Attendance flag is still raised — context block adds clarity, not suppression.

### Attendance Correction Rejection Wizard (v6.21)

Clicking **❌ Rechazar** on `hr.attendance.correction` opens `hr.attendance.rejection.wizard` — same pattern as the revision wizard. Manager types an optional reason → `action_reject(reason=...)` writes it before firing the email → employee receives the red "Observación de RRHH" block if reason was provided. `rejection_reason` on the form is `readonly=1` (audit only; set exclusively via wizard).

### Attendance Biweekly Report Wizard (v6.4 patterns)

- **Employee default:** `_get_payroll_employees()` — latest closed `hr.payslip.run` employees (e.g. MAYO15 = 44). Fallback: `contract_ids.state='open'`. Wizard file: `ueipab_attendance_report/wizard/hr_attendance_report_wizard.py`
- **Resend skips acknowledged:** `action_resend_reports()` domain includes `('state','!=','acknowledged')` + guard in `_send_emails()`. Never re-emails employees who already confirmed.
- **No UI timeout:** `force_send=False` in `_send_emails()` — emails queue as `state='outgoing'`, mail queue cron delivers. Before: 44 × 2.5s = 110s → HTTP worker killed. After: <1s return.
- **Mail queue cron:** id=3 in production. Manual trigger: `execute_kw(..., 'ir.cron', 'method_direct_trigger', [[3]])`. Sent records deleted on success.
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

**⚠️ DMARC `p=none` since 2026-05-20 (DO record id=1818865872):** Akdemia SendGrid sends FROM `@ueipab.edu.ve` without DKIM; SPF misaligned. Monitor-only until fix: Akdemia admin → Domain Auth → 3 CNAMEs → DigitalOcean → revert to `p=reject`. **DO NOT set SPF `-all` until DKIM live.**

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
- Server: `10.124.0.3` | User: `root` | Password: in `config/production.json` → `server.password`
- Container: `ueipab17`
- Database: `DB_UEIPAB`
- Module Path: `/home/vision/ueipab17/addons`

---

## Dev Server Configuration

**Host:** `freescout.ueipab.edu.ve` | RAM: 3.8 GB | Swap: 2 GB | Disk: 48 GB

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
- **⚠️ Active account as of 2026-05-22:** **BACKUP (+584248944898)** — primary broken (all sends failing at WA delivery level since msg≈76649; Massiva support ticket open). Restore: fix on Massiva dashboard → `whatsapp_account_phone=+584148321989`, `whatsapp_account_id=primary_uid`, `whatsapp_active_account=primary`, clear `whatsapp_flagged_phone/date`.
- **⚠️ As of 2026-05-22 `dry_run=True`:** poll cron fires every 5 min but exits before any Massiva API call — **zero messages read from primary or backup**. Parents get no reply on WA. Telegram unaffected.
- **Anti-spam:** Min 120s between sends
- **Send:** `POST /api/send/whatsapp` | **Validate:** `GET /api/validate/whatsapp` | **Receive:** `GET /api/get/wa.received`
- **Webhook payload:** `secret`, `type=whatsapp`, `data{id, wid, phone, message, attachment, timestamp}`
- **Inbox-to-backup re-routing:** Poll `GET /api/get/wa.received?account=primary_uid`; resend via backup uid; then send Telegram invite. *(inactive while `dry_run=True`)*

### Claude AI API (Anthropic)

- **Config:** `/opt/odoo-dev/config/anthropic_api.json` (gitignored)
- **Model:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) - $1/$5 per MTok
- **Use case:** AI backbone for WhatsApp bounce resolution (~$0.005 per conversation)
- **Retry policy (v48.0):** 2 retries on HTTP 429 — delays 3s, 6s — then OpenAI fallback
- **OpenAI fallback:** `gpt-4o-mini` via `requests`. Triggers on: Claude 429 retries exhausted or `credits_ok=False`. Params: `ai_agent.openai_fallback_enabled/api_key/model`.
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
- **School Account Help:** `ACTION:SCHOOL_ACCOUNT_HELP:cedula|student_name|grade` → see Key Technical Patterns
- **Absence notification:** `ACTION:NOTIFY_ABSENCE:name|grade|reason` → Freescout conv → `absence_processor.py` cron
- **Flyer/Audio:** **⚠️ WA only** — skipped on Telegram (`channel != 'whatsapp'` guard in `_send_flyer()`)
- **Farewell:** `resolved` conv → new conv allowed within 24h; `timeout`/`failed` → blocked
- **Calibration:** WA + Telegram conversations both count toward bonus; feedback linked via `user_id.partner_id`

### WA Poll Cron / Competitor / Environment

**WA Poll:** cron uses `account_id=None` (all accounts) to catch replies to old primary number.

**Competitor risk:** Price gate is primary defence (quotes $197.38/$162.39 only). Re-trigger stuck conv: `env['ai.agent.conversation'].browse(ID).action_process_reply(message_text='...', wa_message_id=0); env.cr.commit()`

**Production:** `dry_run=True` (WA paused; Telegram active, v57.17), `active_db=DB_UEIPAB`. WA poll 5min. Webhook: `odoo.ueipab.edu.ve`. Hours VET: Weekdays 06:30-20:30, Weekends 09:30-19:00. `general_inquiry` exempt (24/7). Kill: `ai_agent.telegram_enabled=False`. `wa_primary_relay`: `--live` removed 2026-05-23.
**Testing:** `dry_run=False`, `active_db=DB_UEIPAB` (crons self-skip). Webhook: `dev.ueipab.edu.ve`.

---

## Akdemia Data Pipeline

See [Full Documentation](documentation/AKDEMIA_DATA_PIPELINE.md). Scraper: `akdemia_scraper.py` (Playwright); cron daily 06:00 VET; phases 2a–5 (Freescout + Sheets sync).

---

## Documentation Index

**Payroll/Liquidation:** [V2 Impl](documentation/LIQUIDATION_V2_IMPLEMENTATION.md) · [V2 Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) · [V2 Payroll](documentation/V2_PAYROLL_IMPLEMENTATION.md) · [Disbursement](documentation/PAYROLL_DISBURSEMENT_REPORT.md) · [Prestaciones](documentation/PRESTACIONES_INTEREST_REPORT.md) · [Relacion](documentation/RELACION_BREAKDOWN_REPORT.md) · [Finiquito](documentation/FINIQUITO_REPORT.md) · [V1 Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md) · [V2 Migration](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md) · [Requisition Est.](documentation/PAYROLL_REQUISITION_ESTIMATION_REPORT.md)

**Features:** [Advance Payment](documentation/ADVANCE_PAYMENT_SYSTEM.md) · [Adelanto PS Ack](documentation/ADELANTO_PRESTACIONES_PAYMENT_RECEIPT_ACK.md) · [Comprobante](documentation/COMPROBANTE_DE_PAGO.md) · [Payslip Ack](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) · [Ack Status](documentation/PAYSLIP_ACK_STATUS_REPORT.md) · [Batch Wizard](documentation/BATCH_EMAIL_WIZARD.md) · [Email Templates](documentation/EMAIL_TEMPLATES.md) · [Cybrosys Mods](documentation/CYBROSYS_MODULE_MODIFICATIONS.md) · [Employee Info](documentation/EMPLOYEE_INFO_REQUEST.md)

**AI Agent / Glenda:** [UX Improvement](documentation/GLENDA_UX_IMPROVEMENT_PLAN.md) · [Module](documentation/AI_AGENT_MODULE.md) · [Technical Patterns](documentation/GLENDA_TECHNICAL_PATTERNS.md) · [Overview](documentation/GLENDA_AI_AGENT_OVERVIEW.md) · [HR Data](documentation/GLENDA_HR_DATA_COLLECTION.md) · [Telegram](documentation/GLENDA_TELEGRAM_CHANNEL.md) · [CEO Center](documentation/CEO_COMMAND_CENTER.md) · [WA Invoice Reminder](documentation/WA_INVOICE_REMINDER_PLAN.md) · [Ack Reminder Glenda](documentation/PAYSLIP_ACK_REMINDER_GLENDA.md)

**Ops/Infra:** [Meta WA Migration](documentation/META_CLOUD_API_MIGRATION_PLAN.md) · [Production](documentation/PRODUCTION_ENVIRONMENT.md) · [WebSocket/Nginx](documentation/WEBSOCKET_NGINX_FIX.md) · [Finanzas Spoofing](documentation/FINANZAS_EMAIL_SPOOFING_FIX.md) · [Combined Fix](documentation/COMBINED_FIX_PROCEDURE.md) · [Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md) · [Bounce Cleanup](documentation/BOUNCE_EMAIL_CLEANUP_PROCEDURE.md) · [Akdemia Pipeline](documentation/AKDEMIA_DATA_PIPELINE.md) · [Freescout Plan](documentation/FREESCOUT_API_MIGRATION_PLAN.md)

**Campaigns/School:** [PDVSA Campaign](documentation/PDVSA_CONTINUITY_CAMPAIGN.md) · [Representante Campaign](documentation/REPRESENTANTE_CONTINUITY_CAMPAIGN.md) · [Notice ACK](documentation/NOTICE_ACKNOWLEDGMENT_SYSTEM.md) · [Calibration](documentation/GLENDA_CALIBRATION_PROGRAMME.md) · [Budget Vote](documentation/BUDGET_VOTE_EMAIL.md) · [Attendance Plan](documentation/ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md) · [Control Asistencia](documentation/CONTROL_ASISTENCIA_BRIDGE.md)

**Ad-hoc / Legal:** [PDVSA Tag Check](documentation/QUERY_REPRESENTANTE_PDVSA_TAG_CHECK.md) · [Salario Mínimo Mayo 2026](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md) · [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md) · [Freescout Phone Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) · [Invoice Currency Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)

### Known Issues

**FIXED:** See [CHANGELOG.md](documentation/CHANGELOG.md) for full history of resolved issues.

**FIXED 2026-05-28:**
- **`hr_org_chart` KeyError `new_parent_id`** — build `17.0-20260504` regression; `kw.get('context')['new_parent_id']` and `['max_level']` crash when context key absent. Patched both containers: `(kw.get('context') or {}).get('key')`. Patch lives in container filesystem (`/tmp/patch_org_chart.py` on both hosts); re-apply if containers are rebuilt.
- **Standard 40h work schedule** — morning start was 08:00 VET, corrected to 07:00 VET (`resource_calendar_attendance` calendar_id=1). Triggered by GABRIEL ESPAÑA leave #64 validation failure.

**PENDING — Code / Infrastructure:**
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md) — `tdv_multi_currency_account`; both envs
- [Freescout Phone Conversation Bug](documentation/FREESCOUT_PHONE_CONVERSATION_BUG.md) — `Undefined array key 0` in `SendReplyToCustomer.php:76`; fixed upstream, update Freescout on next release
- **MassivaMóvil Webhook wrong Content-Type** — controller uses `type='json'` but MassivaMóvil sends form-encoded POST. Fix: change to `type='http'`, parse `request.httprequest.form.get()`, `json.loads(data)`. Currently falling back to 5-min poll cron.
- **Internal number guard** — Gustavo's +584142337463 triggers `general_inquiry` conversations. Fix: add `ai_agent.general_inquiry_blocked_phones` param checked before creating a conversation.
- **Glenda supervisor brevity criterion** — split from tone (criterion 4); add avg char_count to digest. See [UX Plan](documentation/GLENDA_UX_IMPROVEMENT_PLAN.md).

**PENDING — Data / Contract:**
- **Decreto Ingreso Mínimo $240 (2026-04-30):** LUIS RODRIGUEZ (total $151.38, gap **+$88.62**) y NIDYA LIRA (total $188.67, gap **+$51.33**) — incrementar `ueipab_bonus_v2` en contratos (ambos envs). Ver [Análisis](documentation/SALARIO_MINIMO_DECRETO_MAYO2026.md).
- **Josefina Phase 2** — liquidation SLIP confirmed (done). Pending: `LIQUID_OTHER_DED_V2` rule in `LIQUID_VE_V2` to deduct $420.87 overpayment from Year 2 liquidation via `ueipab_other_deductions`. See `documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md`.

**PENDING — External / Infrastructure:**
- **WA Primary +584148321989 broken** (2026-05-22) — all sends fail at WA delivery; Massiva support ticket open. Glenda on backup (+584248944898). Once Massiva fixes: reconnect in dashboard → restore config params → clear flagged_phone.
- **Glenda WA paused (2026-05-22)** — `ai_agent.dry_run=True`; poll cron skips, Telegram stays active. Restore: set `ai_agent.dry_run=False` in prod `ir.config_parameter`.
- **`/etc/cron.d/voting_digest` expired** — day-of-month `19-26` in May; will never fire again. Safe to `rm`. Budget vote closed 2026-05-26.
- **`/etc/cron.d/wa_primary_relay`** — fires every 5 min in DRY_RUN (no `--live`). Intentional until WA primary is restored. Remove or re-add `--live` once Massiva fixes primary account.

**PENDING — Refactor:**
- **`partner.communication.ack` misplaced in `ueipab_attendance_report`** — belongs in `ueipab_ai_agent`/`ueipab_campaigns`. Requires DB migration. Low urgency — zero functional impact. See [ACK_FORM_UX_IMPROVEMENTS.md](documentation/ACK_FORM_UX_IMPROVEMENTS.md).

**BLOCKED — Waiting on external trigger:**
- **Representante Continuity Campaign** — script ready (`send_representante_communication.py`), blocked until letter content (LETTER_URL + BULLET_1-3 + EMAIL_HEADLINE) provided.
- **Banco Plaza API** — QA/eval phase; credentials pending from Banco Plaza team.

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
