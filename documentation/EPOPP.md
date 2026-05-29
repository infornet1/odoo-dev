# EPOPP — Educational Programme and Operations Policies and Procedures
### Instituto Privado "Andrés Bello" · El Tigre, Edo. Anzoátegui

> **Version:** 0.1 (Preliminary)  
> **Effective:** 2026-05-28  
> **Owner:** Dirección / Administración  
> **Review cycle:** Annually (or after any regulatory change)  
> **Status:** 🟡 DRAFT — Structure and priority content seeded; sections marked `[stub]` need content development  

---

## About this Document

The EPOPP is the Instituto Andrés Bello's single source of truth for how we operate.  
It answers three questions for every process: **what** we do, **why** we do it, and **how** to do it.

**Design principle:** Every policy fits on one screen. Every procedure fits on one page.  
**Audience:** Staff, teachers, and administrators. Parent-facing policies link to the public portal.

---

## Table of Contents

| Domain | Sections |
|--------|---------|
| [1. Governance & Institutional Framework](#1-governance--institutional-framework) | Mission · Fee Structure · Budget Consultation · Regulatory Compliance |
| [2. Academic Programme](#2-academic-programme) | STEAM Identity · English Programme · Uniforms · Calendar |
| [3. Student & Family Services](#3-student--family-services) | Enrollment · Tuition & Payment · Insurance · Communications |
| [4. HR & People Operations](#4-hr--people-operations) | Payroll · Leave · Attendance · ARI · Salary Advance |
| [5. Finance & Accounting](#5-finance--accounting) | Invoicing · Collections · Exchange Rates · Disbursements |
| [6. Technology & Digital Systems](#6-technology--digital-systems) | Odoo ERP · Glenda AI · Freescout · Attendance Bridge |
| [7. Communications & Outreach](#7-communications--outreach) | Channel Policy · Email Blasts · Bounce Management · DMARC |

---

---

## 1. Governance & Institutional Framework

> **Lead:** Dirección  
> **Legal basis:** Constitución, Ley Orgánica de Educación, MPPE Resoluciones 009 y 024-2020

### 1.1 Mission, Vision & STEAM Identity

**Mission:**  
Form citizens with scientific thinking, technological competence, artistic sensibility, and ethical values, through an integrated STEAM curriculum that connects knowledge to the real world.

**Vision:**  
To be the reference STEAM secondary school in Anzoátegui — recognized for academic excellence, inclusive innovation, and meaningful community impact.

**What STEAM means here:**  
- **S**cience: experimental inquiry, critical thinking  
- **T**echnology: digital tools, coding, automation  
- **E**ngineering: project-based problem solving  
- **A**rts: creative expression woven into every subject  
- **M**athematics: quantitative reasoning across disciplines  

The STEAM framework is not a subject — it is the lens through which we teach every subject.

---

### 1.2 Annual Fee Structure

**Current cycle: 2026–2027**

| Concept | Amount (USD) |
|---------|-------------|
| Mensualidad (Opción A — confirmed May 2026) | $218.88 |
| Mensualidad pronto pago | $207.93 |
| Mensualidad (early bird hasta 31 jul 2026) | $197.38 |
| Inscripción anticipada (hasta 31 jul 2026) | $187.51 |
| Seguro Escolar 2026–2027 | $30.58/alumno/año |
| Guía de Inglés (hasta 31 jul 2026) | $35.00 |
| Guía de Inglés (desde 1 ago 2026) | $40.00 |
| Olimpiadas | $10.00 |
| Enciclopedia | $36.00 |

**Annual total per student (full year, standard rate):** ~$111.58/mes (ver desagregado en Glenda)

**Payment currency:** USD equivalent collected in VES at BCV rate on payment date.

**Fee changes:** Any adjustment to the fee structure requires:  
1. Board review and approval  
2. Parental consultation if change > 10% (per Resolución MPPE 024-2020)  
3. Written notice to families ≥ 30 days before effective date  
4. Update of `_INSTITUTIONAL_KNOWLEDGE` in the Glenda AI knowledge base

---

### 1.3 Budget Consultation Process

Triggered when a fee adjustment exceeds the annual CPI threshold or requires a new cost category.

**Steps:**

1. **Drafting** — Administration prepares cost breakdown with two or more options  
2. **Board approval** — Directors approve the options to be submitted to parents  
3. **Communication** — Options sent to all ACTIVE families via email + Glenda AI  
4. **Voting period** — Minimum 5 business days; quorum = 50% + 1 of registered families  
5. **Result announcement** — Official document published + email blast + Glenda update  
6. **System update** — Odoo `ir.config_parameter` fees updated; Glenda knowledge base updated  

**Last consultation:** 2026-05-26. Result: Opción A ($218.88) — 108 votes (60.7%), quorum 64%.  
**Result document:** [Google Doc](https://docs.google.com/document/d/1GSGzXLxGaaMvYtbyJuGki5KFodmpoy5OyHk0fm4e2fg/edit?usp=sharing)

---

### 1.4 Late Payment Policy (Mora)

**Public page:** https://odoo.ueipab.edu.ve/mora-policy/

| Days overdue | Status | Action |
|-------------|--------|--------|
| 1–15 | Grace | Glenda AI reminder |
| 16–30 | Mora Leve | Automatic WA notification + email |
| 31–60 | Mora Moderada | Direct contact from pagos@ |
| 61+ | Mora Severa | Escalation to Dirección; enrollment risk |

**Exchange rate for overdue balances:** BCV rate on the date payment is finally received (not original invoice date).

---

---

## 2. Academic Programme

> **Lead:** Coordinación Académica  

### 2.1 English Language Programme

**Provider:** MoA (allied consultant)  
**Delivery:** In-house teachers + MoA materials (Guías de Inglés)  
**Cost to families:** See fee table in §1.2 — two-tier pricing applies from Aug 2026

**Guide pricing rationale:**  
MoA notified a cost increase effective August 2026. Families who pay before July 31 lock in the $35 rate. Official communication sent 2026-05-28 via email blast.

**Procedure for guide cost changes:**  
1. MoA notifies Administration of new price  
2. Administration reviews and sets institution's effective date  
3. Email communication sent to all ACTIVE/PIPELINE families (script: `send_english_guide_announcement_email.py`)  
4. Glenda AI `_INSTITUTIONAL_KNOWLEDGE` updated with new amounts  
5. Fee table in §1.2 of this document updated  

---

### 2.2 School Uniform Policy (Distintivo Escolar)

**Official provider:** Almacenes París  
**Local advisor:** Sra. Johanna Hernández — WA: https://wa.me/584248340051  
**Contact:** email / Instagram (see Glenda for current links)  

Families must purchase the officially approved badge/distintivo from Almacenes París only. Third-party reproductions are not accepted.

---

### 2.3 Academic Calendar `[stub]`

> *Content pending — to be seeded from institutional planning documents.*

---

### 2.4 Student Assessment Framework `[stub]`

> *Content pending.*

---

---

## 3. Student & Family Services

> **Lead:** Administración / pagos@ueipab.edu.ve

### 3.1 Enrollment & Inscription

**Early-bird window:** Up to July 31 of each year  
**Process:**

1. Family contacts `pagos@ueipab.edu.ve` or Glenda AI  
2. Administration confirms available slots  
3. Inscription invoice issued in Odoo  
4. Payment received and confirmed  
5. Student record created in Akdemia + Odoo directory  
6. Welcome communication sent

**Inscription fee (2026–2027):** $187.51 (before Jul 31) / standard rate thereafter

---

### 3.2 Tuition Collection & Payment

**Accepted methods:** Bank transfer (Banco de Venezuela, Banco Plaza) · Zelle · Cash USD  
**Payment contact:** `pagos@ueipab.edu.ve`  
**Receipt confirmation:** Via Glenda AI or pagos@ email

**Pagos@ bridge (automated):**  
The `pagos_receipt_processor.py` script reads payment receipts from the Freescout `pagos@` mailbox and:  
1. Identifies the parent by email or Google Sheets lookup  
2. Matches the payment to an open Odoo invoice  
3. Creates and confirms the payment in Odoo (`action_post()`)  
4. Marks the Freescout conversation as resolved  

**Advance payment:** If no open invoice is matched and balance = 0, payment is registered as advance credit.

---

### 3.3 Seguro Escolar 2026–2027

**Provider:** Seguros Caracas (Alternative 2 approved by board)  
**Cost:** $30.58 per student per year (included in monthly fee breakdown)  
**Coverage:** Medical, accident, liability (full detail available via Glenda AI or Administración)  
**Claims:** Contact Administración who coordinates with Seguros Caracas directly

---

### 3.4 PDVSA Discount Policy

**Applicable to:** Families with a parent employed by PDVSA  
**Discount:** 35% on mensualidad (valid until September 1, 2026)  
**Verification:** Employment certificate required annually  
**Status tracking:** `partner.communication.ack` model, `notice_key = pdvsa_continuacion_2026_2027`  

Post-September 2026: Discount program under review. Families contacted via PDVSA Continuity Campaign.

---

### 3.5 Family Communications Policy

**Official channels:**

| Channel | Purpose | Response time |
|---------|---------|--------------|
| WhatsApp (Glenda AI) | Billing inquiries, general info | < 5 min (automated) |
| Telegram (Glenda AI) | Same as WA, no 24h window restriction | Instant |
| `pagos@ueipab.edu.ve` | Payments, invoices, receipts | 1 business day |
| `soporte@ueipab.edu.ve` | Academic / general support | 2 business days |
| `recursoshumanos@ueipab.edu.ve` | HR matters (staff only) | 2 business days |

**Mass communications (blasts):**  
Sent to ACTIVE + PIPELINE families from the Customers Google Sheet (`col J = email`, `col C = status`).  
Pre-blast bounce audit required — see §7.3.

---

---

## 4. HR & People Operations

> **Lead:** Recursos Humanos / `recursoshumanos@ueipab.edu.ve`  
> **System:** Odoo 17 Community + `ueipab_payroll_enhancements` v70.x

### 4.1 Payroll — Venezuelan V2 Structure

**Payroll structure code:** `NOMINA_VE_V2`  
**Database:** Production `DB_UEIPAB`  
**Frequency:** Biweekly (quincenas: 1–15 and 16–end of month)

**Salary components:**

| Code | Description | Calculation |
|------|-------------|-------------|
| `VE_SALARY_V2` | Salario base | `ueipab_salary_v2 / 2.0` |
| `VE_BONUS_V2` | Bono | `ueipab_bonus_v2 / 2.0` |
| `VE_CESTA_TICKET_V2` | Cesta ticket | Fixed $20 (pro-rated for partial periods) |
| `VE_SSO_V2` | IVSS | 4% of base |
| `VE_FAOV_V2` | FAOV | 1% of base |
| `VE_ARI_V2` | Retención ISLR | Variable % from contract field `ueipab_ari_withholding_rate` |
| `VE_NET_V2` | Neto a pagar | GROSS − deductions |

**Minimum salary compliance (Decreto Ingreso Mínimo $240, 2026-04-30):**  
PENDING — LUIS RODRIGUEZ (+$88.62) y NIDYA LIRA (+$51.33) require `ueipab_bonus_v2` adjustment in both environments.

**Accounting:** Debit `5.1.01.10.001` (Nomina) · Credit `1.1.01.02.001` (Banco Venezuela)

---

### 4.2 Liquidation — V2 Structure

**Structure code:** `LIQUID_VE_V2`  
**When triggered:** Contract termination or end of annual cycle  
**Key fields:** `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`, `ueipab_vacation_prepaid_amount`, `ueipab_other_deductions`  
**Accounting:** Debit `5.1.01.10.010` (Prestaciones) · Credit `2.1.01.10.005` (Provision Prestaciones)

**Terminated employee mid-batch procedure:**  
If a contract is in `close` state when a payslip batch runs, follow the closed-contract fix procedure documented in CLAUDE.md → Key Technical Patterns.

---

### 4.3 Leave (Time Off) Policy

**System:** Odoo `hr.leave` — validated via `leave_notification.py`

**Approval matrix:**

| Leave type | Approvals required | Approvers |
|-----------|-------------------|-----------|
| Tiempo personal pagado | 2 (both) | Manager → HR |
| Sin pagar | 2 (both) | Manager → HR |
| Permiso Muerte (luto) | 2 (both) | Manager → HR |
| Diligencia Personal | 2 (both) | Manager → HR |
| Cita Médica familiar | 2 (both) | Manager → HR |
| Enfermedad | HR only | RRHH |
| Lactancia | HR only | RRHH |
| Cita Médica personal | HR only | RRHH |
| Cuidados maternos | HR only | RRHH |
| Reposo Postnatal | HR only | RRHH |
| Días compensatorios | Manager only | Direct manager |

**Notification flow:**  
`confirm` state → email to `recursoshumanos@` (blue, "📋 Nueva Solicitud")  
`validate1` state → email to `recursoshumanos@` (orange, "🔔 Segunda Validación Requerida")

**Daily digest:** Sent 08:00 VET weekdays via `hr_leave_attendance_digest.py` — shows pending approvals + 30-day activity + high-issue employees.

---

### 4.4 Attendance Policy

**Work schedule (Standard 40h, calendar_id=1):** Monday–Friday · 07:00–12:00 + 13:00–17:00 VET

**Biweekly report:** Automatically generated and emailed to each employee every quincena.  
States: `draft → sent → acknowledged`. Employees confirm receipt via `/attendance-ack/<token>`.

**Morning alert (11:30 VET):** Employees with no attendance / missing exit / < 5h yesterday receive an automated email. Leave cross-check: if a leave is approved, the alert includes a context block (green/yellow) instead of a standalone warning.

**Auto-fill check_out (23:30 VET):** If an employee checked in but not out, the system queries the Mikrotik hotspot log (ZeroTier `172.28.10.10`) for the latest WiFi logout. If found before 20:00 VET and after check-in → written as check_out. Fallback: 14:00 VET.

**Correction requests:** Employee clicks "📝 Solicitar Corrección" in the attendance alert email → lands at `/attendance-fix/<token>`.

---

### 4.5 ARI — ISLR Withholding Declaration

**Legal basis:** Decreto N.° 1.808, LISLR Arts. 57, 59, 61  
**Frequency:** Every 90 days — key dates: Jan 15 · Mar 15 · Jun 15 · Sep 15 · Dec 15  
**Portal:** https://odoo.ueipab.edu.ve/my/ari  
**Guide:** http://dev.ueipab.edu.ve:8019/ari-guide/ (generic) or `/ari-guide/<token>` (personalized)

**Process:**  
1. Employee completes AR-I form on Odoo portal  
2. RRHH reviews and approves  
3. Approved % written to `contract.ueipab_ari_withholding_rate`  
4. Applied automatically to next payslip as `VE_ARI_V2` deduction  

**Consequence of non-filing:** Institution must apply maximum withholding rate — employee bears the cost.

---

### 4.6 Salary Advance & Loan Policy

**System:** `ohrms_loan` + `ueipab_payroll_enhancements` (testing only — not yet in production)  
**Recovery types:** `quincena` (deducted from regular payslip) | `liquidacion` (deducted at termination)  

> *Policy details pending production deployment.*

---

---

## 5. Finance & Accounting

> **Lead:** Administración / `finanzas@ueipab.edu.ve`  
> **System:** Odoo 17 Accounting

### 5.1 Invoice Management

**Invoice currency:** USD (multi-currency module)  
**Payment registration:** `pagos_receipt_processor.py` automates matching and posting  
**Known issue:** `tdv_multi_currency_account` bug — exchange rate applied at invoice date, not payment date. Pending fix (both environments).

---

### 5.2 Collections & Overdue Follow-up

**Automated reminders:**

| Channel | Trigger | Script |
|---------|---------|--------|
| WhatsApp (Glenda) | Weekdays 07:00 VET | `wa_invoice_reminder_state.json` |
| Email | Manual wizard launch | Accounting → Customers → Recordatorio de Saldo |

**Excluded:** Partners with VIP tag (id=30) — handled directly by Administración.  
**Tags:** REP=25, PDVSA=26 included; VIP=30 excluded.

---

### 5.3 Exchange Rate Policy (VEB)

**Source:** BCV (Banco Central de Venezuela) — fetched automatically by Odoo  
**3-priority system for reports:**  
1. Custom rate (wizard override) → labeled "Tasa personalizada"  
2. Rate date lookup (wizard) → labeled "Tasa del DD/MM/YYYY"  
3. Latest available / payslip rate → labeled "Tasa automática"

**Payroll:** Each quincena batch records the BCV rate at batch creation; applied to all slips in that run.

---

### 5.4 Payroll Disbursement Process

1. Payslip batch created and computed in Odoo  
2. Net totals exported (V1 + V2 + Aguinaldos columns)  
3. Bank transfer prepared (Banco de Venezuela account `1.1.01.02.001`)  
4. Advance payment option available: percentage multiplier on net, creates linked remainder batch  
5. Batch confirmed → journal entries posted → `state = done`

---

---

## 6. Technology & Digital Systems

> **Lead:** Sistemas / `soporte@ueipab.edu.ve`

### 6.1 Odoo ERP

**Version:** 17.0 Community (build `17.0-20260504`)  
**Environments:**

| Environment | URL | Database | Purpose |
|------------|-----|----------|---------|
| Production | https://odoo.ueipab.edu.ve | `DB_UEIPAB` | Live operations |
| Testing/Dev | http://dev.ueipab.edu.ve:8019 | `testing` | Module development |

**Custom modules:** `ueipab_payroll_enhancements`, `ueipab_hr_contract`, `ueipab_ai_agent`, `ueipab_attendance_report`, `ueipab_hr_employee`, `ueipab_ari_portal`, `ueipab_bounce_log`

**Module sync requirement:** Both environments must run the same module versions. Verify with `documentation/CHANGELOG.md` after any production deployment.

---

### 6.2 Glenda AI Assistant

**Bot name:** Glenda  
**Channels:** WhatsApp (+584248944898 backup active) · Telegram (@GlendaUeipabBot) · OdooBot/Discuss  
**Role:** First-line contact for families — billing inquiries, enrollment info, general school questions  
**Skills:** `general_inquiry` (24/7), `billing_support`, `bill_reminder`, `bounce_resolution`, `hr_data_collection`  

**Key operational parameters:**

| Parameter | Production value |
|-----------|-----------------|
| `dry_run` | `True` (WA paused 2026-05-22; Telegram active) |
| `credits_ok` | `True` |
| Active WA number | +584248944898 (backup) |
| Primary broken since | 2026-05-22 (Massiva ticket open) |

**Restore WA primary:** Once Massiva fixes → update `whatsapp_account_phone`, `whatsapp_account_id`, clear `whatsapp_flagged_phone/date`, set `dry_run=False`.

---

### 6.3 Freescout Support Desk

**URL:** https://freescout.ueipab.edu.ve  
**Mailboxes:**

| ID | Email | Purpose |
|----|-------|---------|
| 2 | pagos@ | Payment receipts and billing |
| 3 | soporte@ | General support + bounce DSNs |
| 4 | recursoshumanos@ | HR / employee matters |
| 5 | finanzas@ | Financial / DMARC reports |
| 8 | votacion@ | Parental consultation confirmations |

**API access:** REST only — never direct MySQL. Key: `X-FreeScout-API-Key`. Config: `/opt/odoo-dev/config/freescout_api.json`.

**Bounce DSN management:** Daily processor (`daily_bounce_processor.py`) runs at 05:00 VET — classifies `soporte@` DSN conversations as LIMPIADO / DUPLICADO / RESUELTO-AI / REVISION.

---

### 6.4 Attendance Systems

**Biometric / manual:** Odoo `hr.attendance` — employees check in/out via kiosk or manager  
**WiFi bridge:** Mikrotik hotspot log (Router 2, ZeroTier `172.28.10.10`) → SSH query → auto-fill missing check_out (23:30 UTC cron)  
**Teacher attendance:** `control_asistencias` DB → `asistencia_estudiante` table → Odoo bridge (22:30 UTC cron, 27 teachers)  
**Student directory sync:** Akdemia scraper (Playwright) → `school.student_directory_json` (daily 06:00 VET)

---

### 6.5 Data Privacy & Retention `[stub]`

> *Policy pending — to cover: student records, employee data, LOPD/LOPDP Venezuela, data retention periods, Google Sheets access controls.*

---

---

## 7. Communications & Outreach

> **Lead:** Administración + Sistemas

### 7.1 Official Channel Policy

**Outbound email FROM addresses:**

| Address | Used for |
|---------|---------|
| `soporte@ueipab.edu.ve` | Mass communications to families |
| `recursoshumanos@ueipab.edu.ve` | HR / employee communications |
| `pagos@ueipab.edu.ve` | Payment confirmations (Reply-To only) |
| `finanzas@ueipab.edu.ve` | Financial correspondence |

**Logo usage:** Always use `https://odoo.ueipab.edu.ve/web/image/res.company/1/logo` (1080×1080 square). Never use the flat landscape version (distorts in circular frames).

**DMARC status:** Currently `p=none` (since 2026-05-20) — Akdemia SendGrid sends FROM `@ueipab.edu.ve` without DKIM. **Do not set SPF `-all` until Akdemia Domain Authentication is configured.**

---

### 7.2 Email Blast Procedure

**Source:** Google Sheets `1Oi3Zw1OLFPVuHMe9rJ7cXKSD7_itHRF0bL4oBkKBPzA` — `Customers!A2:M`  
**Filter:** Column C = `ACTIVE` or `PIPELINE` · Column J = email  
**Standard extra recipients:** docentesprimaria@, docentesecundaria@, academico@, administracion@, jesus.rengel@, yelitza.chirinos@

**Required steps before any blast:**

1. **Preview first** — run `--preview` to send to CEO (`gustavo.perdomo@ueipab.edu.ve`) for visual review
2. **Bounce audit** — scan `soporte@` Freescout for unprocessed Failure DSN conversations; cross-reference against sheet; add hard-bounce addresses to `SKIP_EMAILS` (see §7.3)
3. **Status filter** — confirm filter is ACTIVE + PIPELINE only; never blast all rows
4. **Approval** — explicit go-ahead from CEO before `--live`
5. **Execute** — `python3 scripts/<script>.py --live`
6. **Queue trigger** — cron id=3 triggered automatically; verify queue draining

**Blast scripts inventory:**

| Script | Purpose | Last sent |
|--------|---------|-----------|
| `send_budget_results_email.py` | Resultados Consulta Presupuestaria 2026-2027 | 2026-05-26 |
| `send_english_guide_announcement_email.py` | Ajuste Guías de Inglés 2026-2027 | 2026-05-28 |
| `send_pdvsa_communication.py` | PDVSA continuity survey | 2026-05-19 |
| `send_representante_communication.py` | Representante continuity | Pending (content blocked) |
| `send_vote_wa_reminder.py` | WA blast — budget vote reminders | 2026-05-22 |
| `send_calibration_programme_email.py` | Glenda calibration programme | 2026-05-11 |

---

### 7.3 Bounce Email Management

**Daily processor:** `scripts/daily_bounce_processor.py` — runs 05:00 VET weekdays  
**Source:** `soporte@` mailbox (id=3) — DSN conversations  
**3-tier classification:**

| Tier | Trigger | Action |
|------|---------|--------|
| LIMPIADO | Representante partner + permanent failure | Remove email from Odoo + flag 🔴 in Customers sheet |
| REVISION | Temporary failure (mailbox_full, rejected) | Flag for manual review; no auto-removal |
| DUPLICADO | Already processed in previous run | Closed without action |

**Pre-blast bounce audit procedure:**  
Query `GET /api/conversations` (soporte@ mailbox) for unprocessed `(Failure)` DSN conversations. Fetch thread bodies via `GET /api/conversations/{id}`. Extract email addresses. Cross-reference against blast sheet. Add matches to `SKIP_EMAILS` in the blast script. Document in CHANGELOG.

**Google Sheets bounce log:** `BounceEmail` tab — Date / Customer / Email / Source / Status.

---

### 7.4 WhatsApp Broadcast Policy

**Anti-spam rule:** Minimum 120 seconds between individual sends.  
**Active account:** Backup (+584248944898) — primary broken since 2026-05-22.  
**Provider:** MassivaMóvil (`whatsapp.massivamovil.com`)  
**Dry-run guard:** `ai_agent.dry_run = True` blocks all WA sends from Glenda (Telegram unaffected).

---

---

## Appendix A — Document Conventions

| Element | Meaning |
|---------|---------|
| `[stub]` | Section placeholder — content to be written |
| **Bold** in procedures | Mandatory action |
| ⚠️ | Warning — non-compliance has operational consequences |
| 🔗 | External link |
| Version suffix `vX.Y.Z` | Odoo module version where a feature lives |

---

## Appendix B — Key People & Contacts

| Role | Name | Contact |
|------|------|---------|
| CEO / Director | Gustavo Perdomo | gustavo.perdomo@ueipab.edu.ve |
| HR / RRHH | Josefina Rodríguez | recursoshumanos@ueipab.edu.ve |
| Absences coordinator | Josefina (Freescout user_id=8) | soporte@ueipab.edu.ve |
| IT / Sistemas | — | soporte@ueipab.edu.ve |
| English programme | MoA (consultant) | — |
| Uniform supplier | Almacenes París · Sra. Johanna Hernández | wa.me/584248340051 |
| Insurance | Seguros Caracas | Via Administración |
| WA provider | MassivaMóvil | whatsapp.massivamovil.com |

---

## Appendix C — Regulatory References

| Regulation | Scope |
|-----------|-------|
| MPPE Resolución 009 | Parent participation in school budget setting |
| MPPE Resolución 024-2020 | Fee consultation quorum requirements |
| Decreto N.° 1.808 · Gaceta 36.203 | ISLR withholding obligations |
| LISLR Arts. 57, 59, 61 | ARI filing requirements |
| Decreto Ingreso Mínimo 2026-04-30 | Minimum wage $240 effective |
| LOPDP Venezuela | Data protection |

---

## Appendix D — Related Documentation

> Internal links — requires repo access

- [Features index](FEATURES.md)
- [Changelog](CHANGELOG.md)
- [Payroll V2 Implementation](V2_PAYROLL_IMPLEMENTATION.md)
- [Liquidation V2](LIQUIDATION_V2_IMPLEMENTATION.md)
- [Advance Payment System](ADVANCE_PAYMENT_SYSTEM.md)
- [Attendance Biweekly Email Plan](ATTENDANCE_BIWEEKLY_EMAIL_PLAN.md)
- [Bounce Email Processor](BOUNCE_EMAIL_PROCESSOR.md)
- [Freescout API Migration Plan](FREESCOUT_API_MIGRATION_PLAN.md)
- [AI Agent Module](AI_AGENT_MODULE.md)
- [Glenda Technical Patterns](GLENDA_TECHNICAL_PATTERNS.md)
- [CEO Command Center](CEO_COMMAND_CENTER.md)
- [Production Environment](PRODUCTION_ENVIRONMENT.md)
- [Notice Acknowledgment System](NOTICE_ACKNOWLEDGMENT_SYSTEM.md)

---

*Instituto Privado "Andrés Bello" · El Tigre, Edo. Anzoátegui · RIF J-08008617-1*  
*EPOPP v0.1 — 2026-05-28 · Next review: 2027-03-01*
