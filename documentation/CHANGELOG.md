# UEIPAB Odoo Development - Changelog

This file contains detailed version history, bug fixes, and deployment notes moved from CLAUDE.md.

---

## 2026-05-11 — Employee Private Info Request System (ueipab_hr_employee v17.0.1.2.0)

**Type:** Feature | **Environments:** Testing + Production

Token-based self-service system for HR to collect and update employee private information. Employees receive a personalized email, click a link, confirm or edit 14 private fields on a public pre-filled form, and submit. HR receives a diff notification.

### Key components
- **Model:** `hr.employee.info.request` — one record per employee per campaign; token UUID, state pending/completed, sent_date, completed_date, completed_ip, JSON diff snapshot
- **Reminder tracking:** `reminder_count`, `reminder_last_date`, `days_pending` (computed). Daily cron auto-sends: 1st reminder at day 3, 2nd at day 7 (max 2 auto-reminders). Manual "Enviar Recordatorio" button on form.
- **Public form:** `/employee-info/<token>` — pre-filled, mobile-friendly, amber highlights for missing fields, 4 sections (Identificación, Contacto Personal, Información Personal, Emergencia, Dirección)
- **Email template:** Navy blue + UEIPAB logo + "📋 Fase 1" amber banner + pre-filled data table + CTA button. CC: `recursoshumanos@ueipab.edu.ve`. Testing id=88, Production id=59.
- **HR diff notification:** sent to `recursoshumanos@ueipab.edu.ve` on every form submission, shows old→new per field
- **HR tracking view:** Employees → Solicitudes de Datos; columns: employee, campaign, state badge, days pending, reminders, last reminder, completed date
- **Nginx:** `/employee-info` added to testing whitelist; production uses catch-all

### Fase 1 campaign — `private_info_v1` (2026-05-11)
- 44 employees from ENERO15 batch (excludes Gustavo Perdomo + 2× Administrador 3Dv)
- All 44 sent at 14:40 UTC; MARIA NIETO completed within 2 minutes
- Private address bulk-fill: 46/47 employees updated to El Tigre / Anzoátegui / 6050 / Venezuela via XML-RPC (all had empty private address fields)
- Note: initial 44 emails sent without CC; template fixed immediately after — reminders will CC HR

**Production template IDs:** email=59 | **Testing:** email=88
**Files:** `models/hr_employee_info_request.py`, `controllers/employee_info_controller.py`, `wizard/`, `data/employee_info_request_template.xml`, `views/hr_employee_info_request_views.xml`, `security/ir.model.access.csv`

---

## 2026-05-10 — Glenda Daily Executive Digest + Invoice Balance Query (ueipab_ai_agent v17.0.1.31.4)

**Type:** Feature | **Environments:** Testing + Production

### Invoice Balance Query — ACTION:QUERY_BALANCE

Glenda can now retrieve and send customers their outstanding invoice balance directly via WhatsApp.

**How it works:**
- If customer is identified by phone → balance pre-loaded in `get_context()` from `account.move` ORM query; Claude answers immediately and appends `ACTION:QUERY_BALANCE:FOUND`
- If customer unknown → Claude asks for cédula, customer provides it → Claude appends `ACTION:QUERY_BALANCE:V-XXXXXXXX`
- Handler: `_handle_balance_action()` → `_query_partner_balance()` → posted invoices with outstanding balance → `_format_balance_message()` with BCV VEB conversion
- Breakdown sent as separate WA message (logged in `ai.agent.message`)
- Security: only shows balance for identified partner

**Files changed:** `general_inquiry.py` (3 new methods + `get_context()` + `get_system_prompt()` + `process_ai_response()`), `ai_agent_conversation.py` (`balance_message` key handling)

### Daily Executive Digest — glenda_daily_digest.py

HTML email sent to `gustavo.perdomo@ueipab.edu.ve` daily at 07:00 VET with previous day's activity summary.

**5 sections:**
1. **KPI cards** — total/resolved/escalated/timeout/active conversations + resolution rate + WA sent/recv + Claude tokens + cost estimate
2. **By-skill table** — per-skill breakdown with avg turns and top topics
3. **Topic frequency** — 12-category keyword detection (inscripciones, saldo/deuda, PDVSA, BCV, etc.) from resolution summaries and escalation reasons — horizontal bar chart
4. **Escalations / unresolved** — table of what Glenda couldn't handle (input for future enhancement roadmap)
5. **Suspicious activity alerts** — same phone >3 convs/day (bot candidate), avg tokens/turn >600 (prompt injection probe), night activity 01:00-05:00 VET, conversations >18 turns

**Cron:** `/etc/cron.d/glenda_daily_digest` — `0 11 * * *` UTC (07:00 VET), sources `/root/.odoo_agent_env_prod`
**Manual run:** `python3 scripts/glenda_daily_digest.py --env production [--date YYYY-MM-DD] [--dry-run]`

---

## 2026-05-10 — Glenda BCV Rate Context (ueipab_ai_agent v17.0.1.31.3)

**Type:** Feature | **Environments:** Testing + Production

### Summary

Glenda (`general_inquiry` skill) can now answer BCV exchange rate questions and USD↔VEB conversion requests in real time, using a 30-minute synced rate context injected directly into her system prompt.

### Architecture

```
BCV MySQL (exchange_rates_bcv.bcv_rates, host localhost)
    ↓  scripts/sync_bcv_to_odoo.py  (cron every 30 min)
ir.config_parameter  ai_agent.bcv_rate_context  (JSON)
    ↓  general_inquiry.get_context()  (read at conversation load)
Claude system prompt  →  Glenda response
```

No runtime DB or HTTP calls from within the Odoo Docker container — the host-side cron pre-populates the param. Zero latency added to conversation processing.

### Files

| File | Change |
|------|--------|
| `scripts/sync_bcv_to_odoo.py` | New — queries BCV MySQL, pushes JSON to both Odoo envs via XML-RPC |
| `/etc/cron.d/sync_bcv_odoo` | New — runs sync every 30 min, sources `/root/.odoo_agent_env_prod` |
| `addons/ueipab_ai_agent/skills/general_inquiry.py` | `_get_bcv_context()` reads ICP param; `_build_bcv_block()` formats prompt block; `get_context()` adds `bcv` key; `get_system_prompt()` injects block |
| `addons/ueipab_ai_agent/__manifest__.py` | Bumped to 17.0.1.31.3 |

### JSON param shape

```json
{
  "current": {"rate": 499.8608, "date": "2026-05-08", "updated_at": "2026-05-10 03:00"},
  "history": [
    {"date": "2026-05-08", "rate": 499.8608, "min_rate": 499.8608, "max_rate": 499.8608},
    ...
  ]
}
```
History: last 30 days, one entry per day (AVG/MIN/MAX). Updated every 30 min.

### Glenda capabilities added

- ¿Cuál es la tasa BCV hoy? → exact rate with effective date
- ¿Cuánto son $197.38 en bolívares? → inline multiplication
- ¿Cuál era la tasa el [fecha]? → looks up history (last 30 days); outside range → directs to `bcv.gob.ve`
- Quotes mensualidades/aranceles in VEB at today's rate on request
- Graceful fallback if param missing: "no disponible, consulta bcv.gob.ve"

---

## 2026-05-10 — Glenda Calibration Programme + Instagram Stories (ueipab_attendance_report v17.0.1.5.2)

**Type:** Feature | **Environments:** Testing → Production

### Summary

Staff introduction campaign for Glenda AI Agent: 4 Instagram story slides + email template with per-employee WA-number ACK tracking for calibration programme bonus calculation.

### Instagram Stories (`scripts/create_glenda_stories.py`)

| Slide | Content |
|-------|---------|
| S1 | Bienvenida — flyer composite + WA badge + 6 capability teaser cards (2-col grid) + Claude AI credit |
| S2 | 5 capability cards (24/7, billing, payslip ACK, HR data, bounce resolution) |
| S3 | Calibration programme — 3 steps + who can participate + bono teaser |
| S4 | Bonus formula (Salario Base ÷ 21.75 per documented weekly session) + CTA |

Output: `/home/ftpuser/odoo-dev/glenda_story_s[1-4].png`

### ueipab_attendance_report v17.0.1.5.1 → v17.0.1.5.2

**Model `hr.notice.acknowledgment`:**
- New field `wa_number` (Char) — WhatsApp number confirmed by employee for Glenda calibration

**Controller `notice_ack.py`:**
- `_WA_FORM_KEYS` set: notice keys that trigger the 2-step WA form instead of one-click ACK
- GET `/notice-ack/<token>` for `glenda_calibracion_v1` → shows WA confirmation form pre-filled from `employee.mobile_phone`
- POST `/glenda-calibracion/<token>` → validates WA number (VE format normalisation), saves `wa_number` on ACK record, updates `employee.mobile_phone` if empty
- **Mismatch detection:** if submitted WA ≠ existing `mobile_phone` → auto-update employee + send HR alert email (old/new number, employee name, timestamp) to `recursoshumanos@ueipab.edu.ve`
- Success page shows amber notice when number was auto-updated

**Views:** `wa_number` column added to ACK list + form views

### Email template (mail.template id=86, testing)

- **Model:** `hr.notice.acknowledgment` (renders per-employee token)
- **Subject:** ¡Bienvenida Glenda! — Confirma tu participación en el Programa de Calibración
- **CC:** `recursoshumanos@ueipab.edu.ve` on every send
- **Body:** intro + 2nd paragraph (ciclo escolar 2026-2027 / ajuste mensualidad / competitividad salarial) + capabilities grid + 3-step programme + bonus formula + per-employee ACK button → `/notice-ack/<token>`
- Body stored via SQL (both `en_US` + `es_VE` JSONB keys)

### Production deployment

- 47 staff emails sent to `@ueipab.edu.ve` addresses (44 employees + gustavo.perdomo + alberto.perdomo + yelitza.chirinos as direct recipients); CC: recursoshumanos@ueipab.edu.ve
- `hr.notice.acknowledgment` records created for each employee (`notice_key=glenda_calibracion_v1`)
- HR tracks registrations at: Nómina → Reports → Notice Acknowledgments → filter `glenda_calibracion_v1`

---

## 2026-05-10 — Glenda AI Agent production deployment (GAP 0 → Phase D)

**Type:** Production Deployment | **Modules:** `ueipab_hr_employee` + `ueipab_bounce_log` + `ueipab_ai_agent` v17.0.1.31.2

### Summary

Glenda deployed to production (`DB_UEIPAB`). All prior testing work (v1.0–v1.31.2) now live. `dry_run=False`, `active_db=DB_UEIPAB`, all 6 host crons targeting production.

### Security hardening (GAP 0)

- Removed hardcoded production Odoo API key and Freescout password from `ai_agent_wa_health_monitor.py` and `daily_bounce_processor.py` — replaced with `os.environ.get()` + `RuntimeError` fail-fast
- Added `RuntimeError` fail-fast to all 6 bridge scripts for `TARGET_ENV=production` without env vars
- Created `/root/.odoo_agent_env_prod` (chmod 600) and `/var/www/dev/.odoo_agent_env_prod` (chmod 640, root:www-data)
- Updated all 5 `/etc/cron.d/ai_agent_*` files: source env file, `TARGET_ENV=production`
- Fixed `akdemia_api_sync.py` production block to use env vars; `customer_matching_wrapper.sh` sources env file
- Updated `.gitignore`: added `.odoo_agent_env_prod`, `google_sheets_credentials.json`

### Module installation (GAP 1 + GAP 2)

- DB backup: `/backup/DB_UEIPAB_20260510_pre_ai_agent.dump`
- `PyMuPDF (fitz)` installed in production container (was missing, blocked install)
- `__init__.py` updated: added `/etc/odoo` to config search paths (production container mount point for `/home/vision/ueipab17/config/`)
- Config params loaded manually via Odoo shell after install (post_init_hook searched wrong path)
- 6 skills + 7 crons created; 2 deferred (Timeouts, HR Collection)

### Cron switch (GAP 4 + GAP 10)

- All 5 host AI agent crons switched to production; testing locked (`active_db=''`)
- Akdemia pipeline: `customer_matching_wrapper.sh` now sources production credentials
- Dry-run verified all 5 bridge scripts against production before go-live

### Go-live (Phase D)

- `ai_agent.dry_run = False` set on production Odoo
- `ai_agent.claude_spend_limit_usd = 4.15` (90% of ~$4.61 Anthropic credit remaining after testing)
- Initial bounce load: 2 records created (dcontrerasperez82@gmail.com tier=not_found, lacruzde@pdvsa.com tier=flag)
- Poll cron running at 5 min interval; webhook deferred (poll sufficient for current volume)

### Post-deploy TODOs

- Enable "Check Conversation Timeouts" cron after 48h stable
- Phase 2: enable "Stagger HR Data Collection" cron
- Raise `claude_spend_limit_usd` on each Anthropic credit top-up
- Optional: add nginx `/ai-agent/` proxy on production server for <1s webhook responses

---

## 2026-05-10 — Odoo 17.0 base container update (both environments)

**Type:** Infrastructure | **Environments:** Testing + Production

### Summary

Both Odoo containers updated from `17.0-20251106` (testing) / `17.0-20250807` (production) to `17.0-20260504` — closing a 6–9 month upstream gap.

| Environment | Before | After | Gap closed |
|-------------|--------|-------|------------|
| Testing | `17.0-20251106` (`cdf3ad5c`) | `17.0-20260504` (`d66bb0d7`) | 6 months |
| Production | `17.0-20250807` (`2026212d`) | `17.0-20260504` (`d66bb0d7`) | 9 months |

### Upstream fixes now applied

| Module | Key fix |
|--------|---------|
| `mail` | Duplicate records on concurrent email processing (`a4d3386`) |
| `mail` | Ignore archived email blacklists (`3e70e71`) |
| `mail` | Sanitize `mail.catchall.domain.allowed` (`7324c39`) |
| `account` | Stop rounding discount on import (`7ebce9b`) |
| `account` | Allow branch users to create journal currency transactions (`05e9714`) |
| `web` | PERF: respect limit during onchange fetch (`14d3893`) |
| `web` | Fix translation button save on nested records (`9da5291`) |
| `web` | Realign x2many cache filtering in web_read (`0b2356d`) |
| `hr_attendance` | Checkout employee when archived (`ca8e687`) |
| `hr` | Clear bank account on employee duplication (`94e4f85`) |
| `hr_holidays` | Leave dual-approval fallback fix (`e834bf7`) |

### Procedure

1. Pre-update compatibility audit — all UEIPAB custom modules: no hard blockers (MEDIUM risk areas verified via smoke tests)
2. Testing DB backup: `testing_backup_before_odoo_update_20260510_082038.sql.gz`
3. `docker pull odoo:17.0` on both servers
4. `docker-compose down && docker-compose up -d` — testing first, production after validation
5. Module upgrade: `ueipab_payroll_enhancements -u` (registers wizard models in DB)
6. Full smoke test suite: 18/18 checks passed on testing, 11/11 on production

### Notes

- `ueipab_ai_agent` not installed in production — `ai.agent.conversation` missing there is expected
- Pre-existing transient vacuum error from `base_accounting_kit` (unrelated to update)
- Production had a stale container name conflict (`/ueipab17`) — resolved with `docker rm -f` before `docker-compose up -d`
- Both environments now on identical image digest: `sha256:f4d974041d580ef358ab2d7a49a67439252797a791b7799d3a3432da3ac92722`

---

## 2026-05-09 — Glenda institutional knowledge update (ueipab_ai_agent v17.0.1.31.2)

**Module:** `ueipab_ai_agent` v17.0.1.31.2 | **Status:** Testing

### Leadership & privacy policy (`general_inquiry.py`)

Two new sections added to `_INSTITUTIONAL_KNOWLEDGE`:

**AUTORIDADES INSTITUCIONALES ACTUALES**
- Director General: Prof. Arcides Arzola → soporte@ueipab.edu.ve
- Sub-directora (Media General y Bachillerato): Prof. Norka La Rosa → soporte@ueipab.edu.ve
- Sub-director (Inicial, Preescolar y Primaria): Prof. David Hernández → soporte@ueipab.edu.ve
- Fundadora histórica (1977): Carmen Violeta Mata de Perdomo

**POLÍTICA DE PRIVACIDAD INSTITUCIONAL**
- Glenda must NEVER reveal the name of the legal owner/shareholder.
- If asked "¿quién es el dueño?" or similar: redirect to academic authorities (Director/Sub-directors) + soporte@ueipab.edu.ve.
- The founder (Carmen Violeta Mata de Perdomo) may be mentioned in historical context.
- Guard also added in `get_system_prompt()` INSTRUCCIONES block.

**Trigger:** A tester asked Glenda "¿quién es el dueño del colegio?" and she responded with the business owner's name (Alberto Perdomo), which is confidential information. This update prevents that disclosure.

---

### Industry workers credit policy — Comunicado 08/05/2026 (`general_inquiry.py`)

Full content of the official May 8, 2026 communicado added to `_INSTITUTIONAL_KNOWLEDGE` and `get_system_prompt()`.

**`POLÍTICA FUERZA LABORAL INDUSTRIA`** block (replaces the old `POLÍTICA PDVSA / PETROPIAR` block):

| Topic | Detail |
|---|---|
| Scope | PDVSA, Petropiar, and **all other industry companies** |
| Policy change | 35% credit discount ceases September 1, 2026 |
| Nature of benefit | Always voluntary concession, not an acquired right |
| Reason | Operational cost obligations to staff and suppliers |
| **Confirmation deadline** | **08 June 2026 at 12:30 p.m.** — written notice to pagos@ueipab.edu.ve required. Silence = acceptance of new conditions |
| Casos Especiales | Individual review (no general exceptions) for: excellent academic record, national-medal athletes, active Sistema de Orquestas Juveniles musicians, or recognized outstanding skills |
| Tuition increase 2026-2027 | Projected 20–34% adjustment (pending Comité de Contraloría). Non-tuition costs (insurance, olympiads, textbooks, contests) billed separately |
| Local alliances | Almacén París, Comercial Caracas, Ferretería Veramar — discounts on uniforms and school supplies |

**Instruction block updates (`MANEJO ESPECIAL FUERZA LABORAL INDUSTRIA`):**
- New prospect from any industry company → policy explanation + billing handoff
- Existing distressed family → empathy + deadline reminder + Caso Especial hint + pdvsa_retention handoff
- Deadline question → exact date/time answer (08/06/2026 12:30 p.m.)
- Caso Especial question → eligibility criteria + pagos@ referral
- Tuition increase question → 20–34% projection + pagos@ referral

---

## 2026-05-08 — Notice Acknowledgment system + email template fixes

**Module:** `ueipab_attendance_report` v17.0.1.5.0 | **Status:** Testing validated

### hr.notice.acknowledgment — new model

Generic acknowledgment tracking for any institutional communication:

| Field | Type | Notes |
|-------|------|-------|
| `notice_key` | Char | Machine key e.g. `attendance_guide_v1` |
| `notice_label` | Char | Human-readable title |
| `employee_id` | Many2one | `hr.employee` |
| `token` | Char | UUID auto-generated on create |
| `state` | Selection | `pending` / `acknowledged` |
| `sent_date` | Datetime | Auto-set on create |
| `ack_date` | Datetime | Set by controller on click |
| `ack_ip` | Char | IP at time of click |
| `days_pending` | Integer | Computed, non-stored |

**Public controller:** `/notice-ack/<token>` — `auth='public'`, no login required. Records `state=acknowledged`, `ack_date`, `ack_ip`. Returns styled HTML pages: success / already-done / invalid token.

**Views:** tree (badge status, decoration), form (Manual Acknowledge + Reset buttons), search (Pending / Acknowledged filters, Group by Notice / Status / Employee).

**Menu:** Payroll → Reports → Notice Acknowledgments (sequence 95).

**Security:** `hr_payroll_community_manager` = CRUD, `hr_payroll_user` = read-only.

### Email template (id=84 testing) — updated to hr.notice.acknowledgment model

- Model changed from `hr.employee` to `hr.notice.acknowledgment`
- Employee name: `<t t-out="object.employee_id.name"/>` via QWeb
- Green ACK button: `<a t-att-href="object._get_ack_url()">` — unique URL per send
- CC: `recursoshumanos@ueipab.edu.ve` on every send
- `email_to`: `{{ object.employee_id.work_email }}`
- Send flow: create `hr.notice.acknowledgment` record → `send_mail(ack.id)` → email to employee

### Infrastructure fixes

- **nginx** (`/etc/nginx/sites-available/dev.ueipab.edu.ve`): added `attendance-ack`, `attendance-fix`, `attendance-correction`, `notice-ack` to the Odoo proxy location regex so public routes reach Odoo on port 8019
- **odoo.conf** `dbfilter`: changed from `^(DB_UEIPAB|testing|openeducat_demo)$` to `^testing$` — Odoo now auto-selects the `testing` DB for public (cookieless) requests, enabling `/notice-ack/` and `/attendance-ack/` routes to function
- **`web.base.url`**: updated from `http://dev.ueipab.edu.ve:8019` to `https://dev.ueipab.edu.ve` — all generated links (ACK buttons, attendance report links) now use the correct HTTPS URL

### asistencia_story_s2.png — card overflow fix

Three contingency card heights were too small, causing text and note bars to overflow outside their boundaries:

| Card | Old height | New height | Root cause |
|------|-----------|-----------|------------|
| Odoo Dashboard | 195px | 250px | Note bar ended at y+230, outside 195px |
| Docentes | 210px | 278px | Note bar ended at y+262, outside 210px |
| Admin & Mant. | 210px | 278px | Note bar ended at y+262, outside 210px |

Added `?v=2` cache-buster to `asistencia_story_s2.png` URL in both testing (id=84) and production (id=58) templates to force email clients to re-fetch the corrected image.

### Production template (id=58) — CC and s2 fix applied live

Both the CC (`recursoshumanos@ueipab.edu.ve`) and the `?v=2` cache-buster were applied to production template id=58 via XML-RPC write with explicit `lang` context for both `en_US` and `es_VE` JSONB keys.

---

## 2026-05-08 — Gestión de Control de Asistencia — Guía Visual para Empleados

**Tipo:** Asset operacional + actualización conocimiento Glenda | **Estado:** Testing validado, listo para producción

### Componentes

**1. Instagram Stories — 4 slides PNG (1080×1920 px)**
Script: `scripts/create_attendance_story.py` | Output: `/home/ftpuser/odoo-dev/` → `/var/www/dev/flyers/`

| Slide | Contenido |
|---|---|
| S1 | Jerarquía del sistema: Kiosko (obligatorio) + 3 contingencias |
| S2 | Detalle de los 3 métodos de contingencia con pasos |
| S3 | Preview del reporte quincenal por email + leyenda de íconos |
| S4 | 4 pasos de acción + alerta política 1° junio 2026 |

Jerarquía de registro: Kiosko (obligatorio) → Dashboard Odoo Check In/Out (contingencia digital) → Control de Asistencias (contingencia docentes) → WiFi UEIPAB ≥2h (contingencia admin/mant).

**2. Email Template `mail.template` — Testing id=83**
- Nombre: `Gestión de Control de Asistencia — Guía Visual para Empleados`
- Modelo: `hr.employee` | From: `recursoshumanos@ueipab.edu.ve`
- Carousel horizontal con las 4 stories + resumen + alerta junio 2026
- Script: `scripts/setup_attendance_email_template.py`
- **Nota técnica:** `body_html` es JSONB multilingual (`render_engine='qweb'`). Siempre actualizar via SQL directo con AMBAS claves `en_US` y `es_VE`. El sistema usa `es_VE`; solo actualizar `en_US` deja el ORM leyendo la versión antigua.

**3. Glenda (`general_inquiry.py`) — conocimiento actualizado**
- Kiosko como método principal obligatorio
- Dashboard Odoo Check In/Out como contingencia digital #1
- Control de Asistencias y WiFi reenmarcados como contingencia automática
- 3 nuevas FAQs sobre uso del Dashboard, impacto en nómina desde junio, qué pasa sin ningún registro
- Lógica de Glenda: Kiosko → Dashboard Odoo → Control/WiFi → enlace corrección

---

## 2026-05-08 — Payroll Disbursement Detail: 4 employee date columns (v1.67.6)

**Module:** `ueipab_payroll_enhancements` | **Deployed:** Testing + Production

Added 4 employee contract date columns to the Payroll Disbursement Detail report (both PDF and Excel output), inserted after `VAT ID` and before `Cuenta`:

| Column header | Source field | Notes |
|---|---|---|
| Ing. Original | `contract_id.ueipab_original_hire_date` | Original hire date (rehire antigüedad continuity) |
| Ini. Contrato | `contract_id.date_start` | Last contract start date |
| Ult. Liq. | `contract_id.ueipab_previous_liquidation_date` | Date of last liquidation settlement |
| Ult. Vac. | `contract_id.ueipab_vacation_paid_until` | Vacations paid through this date |

Dates display as `DD/MM/YYYY`; shows `-` (PDF) or blank (Excel) when field is empty on contract.
PDF column widths rebalanced to fit within landscape width. Excel column indexes shifted +4 for all financial columns.

**Files changed:** `__manifest__.py` (v1.67.5 → v1.67.6), `reports/payroll_disbursement_detail_report.xml`, `models/payroll_disbursement_wizard.py`

---

## 2026-05-07 — Mikrotik Hotspot digest always sent to HR

Fixed `sync_mikrotik_attendance.py` to send the daily HTML summary email to `recursoshumanos@ueipab.edu.ve` on every live run — previously only sent when at least one record was created. HR now receives both digests (control_asistencias + Mikrotik) every weekday as cron confirmation.

---

## 2026-05-07 — Mikrotik Hotspot → Odoo Attendance Bridge (Phase 1, Production)

**New script:** `scripts/sync_mikrotik_attendance.py` — daily cron (18:35 VET) that reads active WiFi sessions from Mikrotik hAP ac³ hotspot and creates `hr.attendance` records for staff present on-site. Runs AFTER control_asistencias sync — only fills gaps.

### Architecture
- Source: `/ip hotspot active print detail` via SSH (paramiko, 172.28.10.10, odooapi)
- Mapping: `wifi_hotspot_users` table (payroll_db) + dynamic generation via `username_helper.py` → 94 usernames for 47 employees
- Two usernames per employee: laptop (`gperdomo`) + cellphone (`celgperdomo`)
- Odoo write: XML-RPC (same credentials as control_asistencias sync)
- Email: HTML summary to recursoshumanos@ueipab.edu.ve

### Confidence criteria
- `uptime >= 120 min` (device connected for significant portion of day)
- `login_time = poll_time - uptime` must be before 14:00 VET
- Excludes: `invitado`, `laptop*`, unregistered users

### Priority
control_asistencias record exists → Mikrotik skipped for that employee. Only fills gaps (admin, maintenance, directors).

### Fixes applied
- `jhernandez` / `celjhernandez` in wifi_hotspot_users had typo email (`ueaipab` → `ueipab`)
- `aarcides` / `celaarcides` (ARCIDES ARZOLA) added with non-standard username
- wifi_hotspot_users: 14 → 16 explicit registrations

### Cron
Phase 1 (22:30 UTC) → control_asistencias; Phase 2 (22:35 UTC) → Mikrotik hotspot. Both in `/etc/cron.d/sync_control_asistencia`.

---

## 2026-05-07 — Control Asistencia → Odoo Attendance Bridge (Testing)

**New script:** `scripts/sync_control_asistencia.py` — daily cron that reads teacher activity from the `control_asistencias` Flask/MySQL app and auto-creates `hr.attendance` records in Odoo for teachers who conducted class. No biometric system required.

### How it works
1. Queries `asistencia_estudiante` grouped by `(id_usuario, fecha)` — any teacher who submitted student attendance records = was physically present at school
2. Matches teachers to Odoo employees by `email` (control_asistencias `usuario.email` = Odoo `hr.employee.work_email`)
3. For each matched teacher with no existing Odoo attendance for that day → inserts clean record: `07:00–13:30 VET` (11:00–17:30 UTC), 6.5h
4. Skips if record already exists (idempotent)
5. Sends HTML summary email to `recursoshumanos@ueipab.edu.ve`

### Key facts
- control_asistencias DB: `mysql://control_asist@localhost/control_asistencias`
- Tested 2026-05-07: 19 teachers detected, 18 matched to Odoo, 18 records created
- FLORMAR HERNANDEZ was the only ⚠ no-match in testing (temp email swap for testing purposes — matches correctly in production)
- Idempotency confirmed: re-run skips all existing records

### Cron installed
`/etc/cron.d/sync_control_asistencia` — weekdays 22:30 UTC (18:30 VET), currently `--env testing`

### Production deployment: LIVE 2026-05-07
- XML-RPC backend implemented for production (psycopg2 only for testing)
- API key created for admin uid=2 in DB_UEIPAB (`res_users_apikeys` id=3)
- Backfill May 4–7 school days completed (6 new records created, rest skipped/overlapped)
- Overlap handling: ORM constraint caught gracefully → counted as skip, existing record kept
- Cron updated to `--env production`, runs weekdays 22:30 UTC (18:30 VET)
- Summary email queued as `state=outgoing` → delivered by Odoo mail cron within 1 min

---

## 2026-05-07 — ueipab_attendance_report v17.0.1.4.0 — Resend Report Button + Wizard Resend Mode

**Enhancement:** HR can now resend attendance report emails from two places — the report form and the generation wizard.

### Enhancement 1 — Report form view
- **"Enviar Correo"** (primary, blue) shown only when `state == 'draft'`
- **"📧 Reenviar Correo"** (secondary, grey) shown for `sent` and `acknowledged` states
- Both call the same `action_send_email()` — resending resets state to `sent` for non-historical reports so HR can track re-acknowledgment

### Enhancement 2 — Wizard resend mode
- New **"Solo reenviar reportes existentes (sin generar nuevos)"** checkbox in the wizard
- When checked: yellow info banner appears, `send_email` checkbox hides, "Generar Reportes" button becomes **"📧 Reenviar Reportes"**
- `action_resend_reports()`: finds existing `hr.attendance.report` records for the selected period + employees and calls `_send_emails()` on them — no new records created
- Works with both single-quincena and range modes
- Returns filtered list view of resent reports

### Deployed
- Testing: 2026-05-07 — validated with LUISA ELENA ABREU (temp email swap)
- Production: 2026-05-07 — synced + upgraded DB_UEIPAB + restarted

---

## 2026-05-07 — Payslip Ack — Manual confirmation + reminder (production)

- **5 payslips manually acknowledged** via Odoo shell: ANDRES MORALES (SLIP/580, SLIP/673, SLIP/700) and PABLO NAVARRO (SLIP/672, SLIP/693). `is_acknowledged=True`, `acknowledged_ip='Manual - HR'`, chatter note added per payslip.
- **1 reminder sent** to RAMON BELLO (SLIP/655, ABRIL15) → `ramon.bello@ueipab.edu.ve` (reminder #4).
- Production status: **584 / 585 acknowledged** (99.8%). Only SLIP/655 RAMON BELLO pending.

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.3.4 — Self-Service Attendance Correction

**New feature:** Employees can self-report attendance incidencias via a public form; HR approves in one click.

### Full correction flow
1. Employee clicks **"Solicitar Corrección de Asistencia"** button in their report email (visible when `absent_days > 0`)
2. Public form at `/attendance-fix/<token>` — no login: date dropdown (past only), AM/PM time pickers, 8 LOTTT/LOPCYMAT motivos, optional file attachment (PDF/JPG/PNG, max 5MB)
3. HR receives notification email with direct **"Revisar Solicitud en Odoo"** button → `/attendance-correction/<id>` (login-safe redirect)
4. HR opens `Nómina → Reportes → Solicitudes de Corrección` → pending queue highlighted in yellow
5. HR clicks **✅ Aprobar** → attendance record created via SQL (bypasses overlap constraint), employee notified by email, form reloads to show Aprobado state
6. HR clicks **📧 Reenviar Reporte al Empleado** → employee gets updated report (corrected ✅) with ACK button
7. Employee clicks **Confirmar Recepción** → ACK registered

### Technical details
- New model `hr.attendance.correction` (pending/approved/rejected, attachment_ids M2M, token)
- New controller `/attendance-fix/<token>` (public) + `/attendance-correction/<id>` (auth='user', login-safe redirect)
- 3 email templates: HR notification, employee approval, employee rejection
- `action_approve()`: SQL INSERT to `hr_attendance` (bypasses overlap), sends approval email, reloads form via `next` action
- Mail server `from_filter` widened to `ueipab.edu.ve` domain — HR emails send from `recursoshumanos@ueipab.edu.ve`
- UX fixes: AM/PM dropdowns, LOTTT motivo select + JS dynamic label, file upload widget, attachments inline below motivo in Odoo form

### LOTTT/LOPCYMAT predefined motivos
Corte de energía eléctrica · Consulta/emergencia médica (Art. 49) · Reposo médico · Duelo familiar (Art. 49) · Citación judicial · Matrimonio (Art. 49) · Calamidad doméstica · Otro motivo (free text)

### Production note — after upgrade set mail server from_filter
```bash
docker exec ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http <<'EOF'
server = env['ir.mail_server'].search([], limit=1)
server.from_filter = 'ueipab.edu.ve'
env.cr.commit()
print("Done:", server.from_filter)
EOF
```

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.2.0 — Special Schedule Support

**Enhancement:** Maintenance/security staff with non-standard rotating schedules handled correctly.

### Problem solved
Without this feature: ANDRES MORALES (3 days/week rotation) would show **8 false ❌ absences per quincena**. SERGIO MANEIRO's **18 weekend shifts** were invisible (shown as `─ No hábil`).

### What changed
- New `STATUS_CFG` entry `'dayoff'` — light blue-gray, shown for special employees on weekdays with no attendance (not a penalty)
- Weekend attendance **now visible** for special employees (`ok`/`missing_exit` with actual times)
- `absent_days` always 0 for special employees — no false penalties
- `complete_days` counts ALL days including weekends for special employees
- `get_status_info()` returns `⭐ Horario especial` informational banner instead of ok/warning/danger
- `is_special_schedule` computed field on `hr.attendance.report` — exposed to QWeb
- Email template: `dayoff` row ("Día libre"), conditional summary box (no absent row), legend updated
- New `_get_special_schedule_employees()` reads `attendance_report.special_schedule_employees` system param (comma-separated IDs)

### Configuration (production)
After module install, set via Settings > Technical > Parameters:
```
Key:   attendance_report.special_schedule_employees
Value: 571,606,610
```
| ID | Employee | Role |
|----|----------|------|
| 571 | ANDRES MORALES | Mantenimiento |
| 606 | PABLO NAVARRO | Mantenimiento |
| 610 | SERGIO MANEIRO | Seguridad |

### Director analysis (validated in testing)
Synced ARCIDES ARZOLA (572), DAVID HERNANDEZ (576), NORKA LA ROSA (605).
**Directors follow standard Mon-Fri, zero weekend work** → no special schedule needed, report handles them correctly. Feb 2026 Q1: DAVID 10/10 present, NORKA 9/10, ARCIDES 8/10 (2 absences flagged for HR review).

### Sync scripts
- `scripts/sync_maintenance_attendance.py` — ANDRES, PABLO, SERGIO (385 records)
- Directors synced inline (340 records); work_email unchanged for all — no test emails

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.1.0 — Holiday Support

**Enhancement:** Official Venezuelan national holidays are now excluded from absent-day counts.

### What changed
- New `STATUS_CFG` entry `'holiday'` — light-blue row (📅), shown when a weekday has no attendance AND is a configured public holiday
- `_get_holiday_dates()` reads `attendance_report.holidays` system parameter (JSON array `[{"date":"YYYY-MM-DD","name":"..."}]`)
- `get_attendance_days()` marks unworked holidays as `'holiday'` instead of `'absent'`; if attendance IS recorded on a holiday, actual data takes precedence
- `workday_count` now excludes holidays (employees are no longer penalized for official days off)
- New `holiday_days` computed field — appears in summary box only when `> 0`
- Email template: holiday row spans the three time columns and shows the holiday name in italics; legend updated; summary box shows "Feriados oficiales: 📅 N"
- Form view HTML table: holiday row uses colspan=3 with holiday name; legend updated
- New `data/holidays_config.xml` — 12 holidays loaded as `noupdate="1"` system parameter

### Holidays configured (2025-2026 academic year)
| Date | Holiday |
|------|---------|
| Oct 12, 2025 | Día de la Resistencia Indígena |
| Dec 25, 2025 | Navidad |
| Jan 1, 2026 | Año Nuevo |
| Feb 16-17, 2026 | Carnaval |
| Apr 2-3, 2026 | Jueves y Viernes Santos |
| Apr 19, 2026 | Declaración de Independencia |
| May 1, 2026 | Día del Trabajador |
| Jun 24, 2026 | Batalla de Carabobo |
| Jul 5, 2026 | Día de la Independencia |
| Jul 24, 2026 | Natalicio de Simón Bolívar |

**Note:** HR can add MPPE-specific pedagogical days via Settings > Technical > Parameters > `attendance_report.holidays` without losing them on upgrades (`noupdate="1"`).

### Verified in testing
- Dec 2025 Q2 (NIDYA LIRA): Dec 25 detected as Navidad → `holiday_days=1`, `workday_count=11`
- Jan 2026 Q1: Jan 1 detected as Año Nuevo → `holiday_days=1`, `workday_count=10`
- Apr 2026 Q1: Apr 2+3 detected as Semana Santa → `holiday_days=2`, `workday_count=9`
- Oct 12 (Sunday) correctly handled as weekend (not double-counted)

### Receso Navideño added (same date, separate commit c3cd9ad)
18 weekdays Dec 15–Jan 11 added as "Receso Navideño" (MPPE official: recess Dec 15, classes resume Jan 12).
Dec 25 stays "Navidad", Jan 1 stays "Año Nuevo". Total holidays in config: **30 entries**.
Result: Dec Q2 → `workdays=0 absent=0`; Jan Q1 → `holidays=7 workdays=4`.

### Production deployment note
`attendance_report.holidays` **auto-created** by module install (30 entries from `holidays_config.xml`, `noupdate="1"`).

---

## 2026-05-06 — ueipab_attendance_report v17.0.1.0.0 — READY FOR PRODUCTION

**New standalone module** — zero changes to `ueipab_payroll_enhancements`.
**Status:** Validated in testing with NIDYA LIRA (108 real production attendance records). Awaiting production maintenance window.

### Post-validation fix (same date)
- **Danger banner message** — Updated to Opción 1 professional tone: "Su registro actual presenta un total de N incidencias (...). Le recordamos que las inasistencias no justificadas o que presenten inconsistencias sin informar podrían generar descuentos automáticos. Este nuevo mecanismo de control entrará en vigor de manera efectiva a partir del 1 de junio de 2026."

### Production deployment checklist
| Step | Action |
|------|--------|
| A | `scp -r addons/ueipab_attendance_report root@10.124.0.3:/home/vision/ueipab17/addons/` |
| B | `docker exec ueipab17 /usr/bin/odoo -d DB_UEIPAB -i ueipab_attendance_report --stop-after-init` |
| C | `docker restart ueipab17` |
| D | Open Payroll → Reports → Reporte de Asistencia Quincenal |
| E | Mode: Rango de meses · Oct 2025 → current month · Todos los empleados · ✓ Enviar correo |
| F | Verify: Oct 2025–Apr 2026 → state=Confirmado (auto-ack, informational email) |
| G | Verify: current quincena → state=Enviado (ACK button in email) |

**Note:** No DB_UEIPAB schema risk — new module, no changes to existing tables.

### Features delivered
| # | Feature | Detail |
|---|---------|--------|
| 1 | `hr.attendance.report` model | Per-employee quincenal attendance snapshot with ack_token, state (draft/sent/acknowledged), summary stats, VET UTC-4 timezone handling |
| 2 | Wizard — single quincena | Year/month/quincena picker, dates auto-computed, employee 3-mode filter (all/department/manual), live counter |
| 3 | Wizard — bulk range mode | Select month range → generates Q1+Q2 for every month up to today; designed for production backfill Oct 2025 onward |
| 4 | HTML table preview | Day-by-day attendance table rendered in Odoo form view (`_build_html_table`) |
| 5 | QWeb email template | No attachment, inline body: week tables, status banner (ok/warning/danger), legend, ACK button |
| 6 | ACK controller | `/attendance-ack/<token>` public route — records ack_date + IP, three confirmation pages |
| 7 | `is_historical` auto-ack | Periods before current month: auto-acknowledged on `create()`, email shows informational footer instead of ACK button — prevents HR headaches on backfill sends |
| 8 | Menu | Payroll → Reports → Reporte de Asistencia Quincenal + Reportes Generados (Asistencia) |

### Key design decisions
- `is_historical` cutoff = first day of current month (self-updating, no magic number)
- `_send_emails()` does not downgrade `acknowledged → sent` for historical records
- `noupdate` removed from template XML — body reloads on every upgrade (dev phase)
- Year fields as `Char` to prevent locale "2,026" formatting
- Radio button groups use `col="1"` for proper left-aligned layout

### Test data
- NIDYA LIRA: 108 attendance records synced from production via `scripts/sync_nidya_attendance.py`
- Work email set to `gustavo.perdomo@ueipab.edu.ve` for testing
- Discount policy effective date in danger banner: **1 de junio de 2026**

---

## 2026-05-06 — LO module sync: testing → production (no version bump)

**Production-only DB fix. No code change.**

| Item | Fix |
|---|---|
| Payslip Email (id=37) | Loan block was appended **after** closing `</div>` — invisible in emails. Replaced full body with testing version: block now inside deductions table, uses `object.get_line_amount()` for both `VE_LOAN_DED_V2` + `LIQUID_LOAN_DED_V2`, correct `'{:,.2f}'` format. `es_VE` translation added. |
| Adelanto Prestaciones (id=50) | Body synced to match testing id=71 (was 224 bytes different). Missing `es_VE` translation added. |
| `VE_TOTAL_DED_V2` (id=19) | Deploy script had appended the loan line leaving two `result =` assignments. Removed duplicate first line. |
| `LIQUID_NET_V2` (id=34) | Same issue — removed duplicate first `result = (...)` block. |

**Script:** `scripts/sync_lo_to_production.py`

---

## v1.66.5 — 2026-05-05 — Backdated loan approval JE date fix

**Files:** `hr_loan_extension.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| `_create_advance_journal_entry()` date fix | When `loan.date` is in a past calendar month, use `today` as the JE date instead. Prevents PAY1 sequence/date mismatch error when approving historical advances. `loan.date` stays unchanged as the disbursement record. |

**Root cause:** PAY1 enforces chronological sequence continuity. If loan date is February 2026 but PAY1 is already at `PAY1/2026/04/xxxx`, Odoo rejects the entry with "Date doesn't match sequence number". HR workaround was to change loan date before approving — now automatic.

---

## v1.66.4 — 2026-05-05 — Option B conservative + batch cancel + payslip cancel fix

**Files:** `hr_loan_extension.py`, `hr_payslip.py`, `hr_payslip_run.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| Option B — conservative | `action_compute_sheet()` only adds LO inputs when the payslip has **zero** LO inputs. If any LO input already exists HR is managing them manually — no interference. Handles "loan approved after batch generation" without re-adding deliberately deleted inputs. |
| Batch cancel → cancels draft payslips | `action_cancel()` filter changed from `state not in ('cancel','draft')` to `state != 'cancel'`. Draft payslips now correctly cancelled with their batch. |
| `action_payslip_cancel()` override | For `done` payslips: resets posted JE to draft via `button_draft()`, cancels via `button_cancel()`, then sets `state='cancel'`. Draft/verify payslips bypass JE handling. |

> **v1.66.2–v1.66.3** were intermediate steps: v1.66.2 added additive-only Option B; v1.66.3 attempted an `act_window` display workaround. Both superseded by v1.66.4.

---

## v1.66.1 — 2026-05-05 — Batch cancel includes draft payslips

**Files:** `hr_payslip.py`, `hr_payslip_run.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| Filter fix | `action_cancel()` was filtering `state not in ('cancel','draft')` — draft payslips silently survived batch cancellation. Fixed to `state != 'cancel'`. |
| JE cancel on done payslips | `action_payslip_cancel()` override: posted journal entry reset to draft + cancelled before setting payslip state. |

---

## v1.66.0 — 2026-05-05 — Multiple Loans per Employee

**Files:** `hr_loan_extension.py`, `liquidacion_breakdown_report.py`, `setup_loan_rules.py`, `__manifest__.py`

| Change | Detail |
|---|---|
| No loan constraint | `HrLoan.create()` bypasses ohrms_loan one-loan-per-employee check via MRO (`super(ohrms_cls, self)`). Unlimited concurrent loans allowed (Option A). |
| `get_inputs()` rewrite | One LO input per active matching loan. Finds earliest unpaid installment with `date ≤ payslip.date_to` — handles skipped periods. Removes ohrms_loan last-wins bug. HR can zero any LO input to skip that loan this period. |
| `action_payslip_done()` rewrite | Uses `loan_line_id` on each input directly. Reverts `paid=True` for zero-amount LO inputs (HR skip). Writes `payslip_id` back for paid ones. |
| Salary rule formula | `VE_LOAN_DED_V2` and `LIQUID_LOAN_DED_V2` now: `slip = payslip.dict; result = -sum(l.amount for l in slip.input_line_ids if l.code == 'LO')`. Sums all LO inputs; avoids `inputs.LO` last-wins limitation. Updated in testing DB and in `setup_loan_rules.py` (idempotent). |
| Report multiple loans | `liquidacion_breakdown_report.py`: removed `limit=1`, shows all active liquidación loan names, sums total loan amount. |

---

## HR Analyses

### 2026-05-01 - Decreto Ingreso Mínimo Integral $240 — Análisis de Impacto Salarial

**Ad-hoc analysis — no module change. PDF ejecutivo generado para equipo de Finanzas.**

| Item | Detalle |
|---|---|
| **Decreto** | Ingreso Mínimo Integral sube a $240 USD efectivo 30/04/2026 (retroactivo) |
| **Composición** | Bono de Guerra Económica $199.73 + Cestaticket $40.00 + Salario base $0.27 |
| **Anterior** | ~$190 USD (+26.3% de incremento) |
| **Empleados analizados** | 44 (excluyendo Alberto Perdomo, María Jiménez, Gustavo Perdomo) |
| **No conformes** | LUIS RODRIGUEZ ($191.37, gap +$48.63) · NIDYA LIRA ($228.67, gap +$11.33) |
| **Ajuste mensual requerido** | $59.96 (anualizado: $719.52) |
| **Banda de riesgo $240–$300** | 9 empleados — MARIELA PRADO y ZARETH FARIAS con solo $10.03 de margen |
| **Cestaticket** | Valor actual $40.00 coincide exactamente con el decreto — sin cambio requerido |
| **Acción** | Incrementar `ueipab_bonus_v2`: LUIS RODRIGUEZ $55.69→$104.32 · NIDYA LIRA $83.44→$94.77 |
| **PDF** | `/home/ftpuser/odoo-dev/Analisis_Impacto_Salarial_Mayo2026.pdf` (2 páginas) |
| **Docs** | [SALARIO_MINIMO_DECRETO_MAYO2026.md](SALARIO_MINIMO_DECRETO_MAYO2026.md) |

---

## Production Deployments

### 2026-05-05 — Backdated loan JE date fix (ueipab_payroll_enhancements v1.66.5)

**Deployed to production DB_UEIPAB.**

| Item | Details |
|------|---------|
| **Module version** | 17.0.1.66.5 (upgraded from 17.0.1.66.4) |
| **Fix** | `_create_advance_journal_entry()` now uses `today` when loan date is in a past month |
| **Trigger** | HEYDI RON's second loan (LO/0004) — date 2026-03-02 rejected by PAY1 sequence at 2026/04 |
| **Workaround applied** | HR changed loan date to 2026-05-01 before approving (manual fix, still valid) |

---

### 2026-05-05 — HR Loan System (ueipab_payroll_enhancements v1.66.4)

**Deployed to production DB_UEIPAB.**

| Item | Details |
|------|---------|
| **Module version** | 17.0.1.66.4 (upgraded from 17.0.1.65.0) |
| **ohrms_loan** | Already installed (17.0.1.0.0) — no change |
| **ohrms_loan_accounting** | Already installed (17.0.1.0.0) — no change |
| **Salary rules updated** | `VE_LOAN_DED_V2` id=38, `LIQUID_LOAN_DED_V2` id=39 — formula updated to multi-loan sum via `setup_loan_rules.py` |
| **Templates patched** | id=37 (Payslip Email), id=50 (Adelanto Prestaciones) — loan block inserted; id=52 (Adelanto Salario) already existed. Note: initial deploy had loan block outside HTML — corrected 2026-05-06 via `sync_lo_to_production.py`. |
| **PAY1 pre-check** | 0 `LOAN/` contamination entries — clean |
| **DB backup** | `/home/vision/backups/DB_UEIPAB_before_v1.66.4_20260504_2236.sql.gz` (18MB) |
| **Features deployed** | Multiple loans per employee, batch cancel fix, Option B, `action_payslip_cancel()` with JE handling |

---

### 2026-04-22 - Relación de Liquidación PDF Title Selector (ueipab_payroll_enhancements v1.62.7)

**Deployed to production DB_UEIPAB. Files: `__manifest__.py`, `models/liquidacion_breakdown_wizard.py`, `models/liquidacion_breakdown_report.py`, `wizard/liquidacion_breakdown_wizard_view.xml`, `reports/liquidacion_breakdown_report.xml`, `reports/report_actions.xml`, `controllers/liquidacion_breakdown_xlsx.py`.**

| Item | Details |
|------|---------|
| **Feature** | New "Título del Documento PDF" radio selector in Relación de Liquidación wizard |
| **Options** | `Relación de Liquidación` (default) / `Adelanto Prestaciones Sociales` |
| **PDF header** | Title, subtitle (`Fecha Liquidación:` / `Fecha Adelanto:`), and declaration text all adapt to selection |
| **Declaration text** | Adelanto mode: "...por concepto de adelanto de prestaciones sociales." |
| **PDF filename** | `Relacion_Liquidacion_{EMPLOYEE}_{YYYYMMDD}.pdf` or `Adelanto_Prestaciones_{EMPLOYEE}_{YYYYMMDD}.pdf` |
| **XLSX filename** | Same naming logic applied to XLSX export |
| **Technical note** | Odoo 17 `print_report_name` only exposes `object`+`time` — no context. When `data=` is passed to `report_action`, docids are not in the URL path so `print_report_name` is never evaluated. Fixed via custom PDF controller (`/liquidacion/breakdown/pdf/<wizard_id>`) mirroring the existing XLSX controller pattern |
| **Version** | `17.0.1.62.7` |

---

### 2026-04-19 - Email Template Sync: Subject + Color Fixes (both envs)

**Synced testing (id=71) and production (id=50) templates to identical state.**

| Fix | Detail |
|---|---|
| Subject | `📋 LIQUIDACIÓN V2 │...` → `📋 ADELANTO PRESTACIONES │...` (production) |
| Red colors | `#c0392b` (×5) + `#7b1a1a` (×1) → navy blue `#2471a3` / `#1a2c5b` (both envs) |
| Legal box bg | `#fdf6f0` (orange tint) → `#f0f4fa` (light blue) (production) |
| Result | Both templates fully navy blue, subject identical, bodies in sync |

---

### 2026-04-18 - Adelanto de Prestaciones Sociales Email Template (ueipab_payroll_enhancements v1.62.2)

**Deployed to production DB_UEIPAB. Template id=50. Files deployed: hr_payslip.py, payslip_acknowledgment.py, __manifest__.py, mail_template_payslip.xml. Body applied via direct SQL (psycopg2). Production Odoo restarted.**

---

## Testing Deployments

### 2026-05-04 - HR Loan Production Deployment Scripts Prepared

| Item | Details |
|---|---|
| **`setup_loan_rules.py`** | Idempotent Odoo shell script — creates `VE_LOAN_DED_V2` + `LIQUID_LOAN_DED_V2`, links to structures, creates LO input types, patches `VE_TOTAL_DED_V2` and `LIQUID_NET_V2` formulas |
| **`deploy_loan_templates_prod.py`** | Standalone psycopg2 script — creates "Adelanto de Salario – Notificación" template (new), patches Payslip Email id=37 and Adelanto Prestaciones id=50 with loan blocks |
| **Production IDs confirmed** | PAY1 journal=170, acc_receivable=890, acc_banco=876, acc_prestaciones=1017, Payslip Email tpl=37, Adelanto Prestaciones tpl=50 |
| **PAY1 clean** | No `LOAN/` contamination entries confirmed in production |

---

### 2026-05-04 - HR Loan Bug Fixes (ueipab_payroll_enhancements v1.65.0)

| Item | Details |
|---|---|
| **`total_net_amount` fix** | `_compute_total_net_amount` on `hr.payslip.run` now includes `LIQUID_NET_V2` — liquidation-only batches were showing Bs. 0 as total net |
| **Relación de Liquidación sign fix** | Loan deduction `amount_formatted` was using `abs()` causing the deduction to display as positive, inconsistent with other deductions in the report |
| **Known issue documented** | Creating `LIQUID_VE_V2` payslips via batch does not auto-populate LO input (struct_id is taken from contract, not payslip). Workaround: create liquidation payslips individually |
| **Version** | `17.0.1.65.0` |

---

### 2026-04-19 - Payslip Ack Reminder via Glenda (ueipab_ai_agent v1.31.0)

**New `payslip_ack_reminder` skill + Tab 2 in "Recolección de Datos" wizard.**

| Item | Details |
|------|---------|
| **Skill** | `payslip_ack_reminder` — source model `hr.payslip`, max_turns=4, timeout=48h |
| **Wizard** | Tab 2 "Conformidades Pendientes" in existing wizard — lists `done` payslips with `is_acknowledged=False` |
| **Message** | Greeting with payslip number, period, net VEB, acknowledgment portal URL |
| **Auto-resolve** | CRON every 30 min checks `is_acknowledged` — auto-resolves conversation when True |
| **Stagger CRON** | New `_cron_start_ack_reminders()` — 30 min, respects capacity (max_active=10) |
| **LIQUID_VE_V2** | Greeting uses "adelanto de prestaciones sociales" instead of "comprobante de pago" |
| **Duplicate guard** | Employees with existing active WA reminder shown as muted, deselected by default |
| **New model** | `hr.data.collection.create.ack.line` (TransientModel for wizard Tab 2) |
| **Module version** | 17.0.1.31.0 |
| **Docs** | [PAYSLIP_ACK_REMINDER_GLENDA.md](PAYSLIP_ACK_REMINDER_GLENDA.md) |

**Files changed:** `skills/payslip_ack_reminder.py` (new), `wizard/create_collection_wizard.py`, `wizard/create_collection_wizard_view.xml`, `skills/__init__.py`, `data/skills_data.xml`, `data/cron.xml`, `models/ai_agent_conversation.py`, `security/ir.model.access.csv`, `__manifest__.py`

---

### 2026-04-18 - Adelanto de Prestaciones Sociales Email Template (ueipab_payroll_enhancements v1.62.2)

**New email template for LIQUID_VE_V2 payslips with legal agreement body and structure-aware ack landing page.**

| Item | Details |
|------|---------|
| **Template name** | `Adelanto de Prestaciones Sociales` (DB id=71 testing) |
| **Structure** | `LIQUID_VE_V2` only |
| **Color scheme** | Navy blue gradient (`#1a2c5b → #2471a3`) — distinct from red liquidación template |
| **Body** | Four legal clauses (PRIMERO–CUARTO) with company/employee data, period dates, net VEB amount, signing date |
| **Amounts** | All in VEB via `get_liq_veb()` / `get_liq_net_veb()` helpers |
| **Key fields** | `date_from/date_to` for period, `ueipab_original_hire_date` for hire date, `get_next_period_start()` for day after period end |
| **Signing date** | Uses email send date (today) via `get_today_day/month_es/year()` helpers — not `date_to` |
| **Hardcoded rep** | `GUSTAVO PERDOMO`, `Representante Legal`, `V15128008` |
| **Ack button** | "Enviar conformidad digital para recibir mi pago" |
| **PDF attachment** | Disabled during body refinement — re-enable via `action_report_liquidacion_breakdown` ref in XML |
| **Landing page** | Branches on `struct_id.code == 'LIQUID_VE_V2'` — adelanto-specific title/subtitle/button; all other structures see generic text |
| **New helpers in hr_payslip.py** | `get_liq_veb(code)`, `get_liq_net_veb()`, `get_next_period_start()`, `get_original_hire_date_fmt()`, `get_today_day()`, `get_today_month_es()`, `get_today_year()` |
| **Business flow** | Batch stays DRAFT → email sent → employee reviews and acknowledges → HR confirms receipt → batch confirmed/closed |
| **Template body** | Managed via direct SQL (`jsonb_set`) — ORM `Html` sanitizer strips custom method calls |
| **Version** | `17.0.1.62.2` |

### 2026-04-18 - Farewell Message Fix After Resolved Conversation (ueipab_ai_agent v1.30.2, testing only)

**Fixed: post-handoff farewell messages ("Gracias", "saludos") silently dropped.**

| Item | Details |
|------|---------|
| **Root cause** | `_get_or_create_general_inquiry_conversation()` 24h cooldown blocked ALL terminal states equally. When a customer sent a farewell after a resolved handoff, the guard found the resolved conv within 24h and returned `None` — message dropped, no reply |
| **Example** | Gustavo received 5-student quotation at 00:34, replied "Gracias saludos" shortly after → Glenda never acknowledged it |
| **Fix** | Cooldown now distinguishes terminal states: `timeout`/`failed` → still blocked (unresponsive or broken); `resolved` → **allow new conversation** so Glenda can give a brief, warm acknowledgment |
| **Behavior after fix** | Customer who says "Gracias" after a handoff gets a natural closing reply from Glenda instead of silence |
| **Version** | `17.0.1.30.2` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-18 - Annual Extras in Quotation (ueipab_ai_agent v1.30.1, testing only)

**Extended quotation engine to include one-time annual costs and full first-month total.**

| Item | Details |
|------|---------|
| **Annual one-time costs** | Seguro escolar $15 + Enciclopedia de Inglés $30 + Olimpiadas Recreativas $10 = **$55/alumno** (no sibling discount, full price per student) |
| **Bachillerato extra** | +$36 Enciclopedia digital bachillerato per bachillerato-level student. Glenda asks if any student is in bachillerato before quoting |
| **Optional costs excluded** | Competencia Kurios ($10) and Competencia MOA inglés ($25) are conditional (only if selected by school) — NOT included in standard quote |
| **Quote format** | 4 sections: (1) mensualidad per child with sibling discount, (2) inscripción total, (3) costos anuales total, (4) TOTAL PRIMER MES = inscripción + extras + mensualidad (regular and pronto pago) |
| **Example 2 students** | Primer mes regular $1.154,70 / con pronto pago $1.109,23 |
| **Version** | `17.0.1.30.1` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-18 - Multi-Student Quotation Engine (ueipab_ai_agent v1.30.0, testing only)

**Glenda can now generate full enrollment quotations for families with multiple children.**

| Item | Details |
|------|---------|
| **Sibling discounts** | 1st child: full price · 2nd: 5% off mensualidad · 3rd: 6% · 4th+: 7%. Inscripción at full price per child. Discounts stack with pronto pago (applied on already-discounted mensualidad) |
| **Pre-calculated table** | Per-child amounts embedded in knowledge: 1st $264,48 (PP $241,16) · 2nd $251,26 (PP $229,11) · 3rd $248,61 (PP $226,69) · 4th+ $245,97 (PP $224,28) |
| **Quote flow** | If student count not stated, Glenda asks first. Presents per-child breakdown + total mensual (regular and pronto pago) + total inscripción |
| **Handoff** | After quote, hands off to `billing` with structured summary: N alumnos, total mensualidad, total PP, total inscripción |
| **Email subject** | Quotation emails automatically get subject `[Glenda] Cotización solicitada` (detected from summary keyword "cotización") |
| **Version** | `17.0.1.30.0` |
| **Deployed** | Testing 2026-04-18 |

### 2026-04-17 - Forecast Tarifas 2026-2027 Sep (ueipab_ai_agent v1.29.9, testing only)

**Added upcoming September 2026 projected pricing to Glenda's institutional knowledge.**

| Item | Details |
|------|---------|
| **New knowledge** | Proyected rates effective September 1, 2026 (start of 2026-2027 school year): Inscripción $264,48 · Mensualidad $264,48 · Pronto pago $241,16 (8,816% discount, first 10 days of month) |
| **Current rates retained** | $197,38 inscripción / mensualidad, pronto pago $162,39 — labeled "vigente hasta agosto 2026" |
| **Glenda behavior** | Answers correctly for current OR upcoming rates depending on what the customer asks. If asked whether price will increase: confirms Sep 1 adjustment without alarming. Recommends pagos@ to confirm for specific cases |
| **Version** | `17.0.1.29.9` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - General Inquiry Timeout Fix (ueipab_ai_agent v1.29.8, testing only)

**Fixed three bugs that caused `general_inquiry` conversations to stay permanently stuck in `waiting` state.**

| Item | Details |
|------|---------|
| **Bug 1 — Missing `get_reminder_message`** | `general_inquiry` skill never implemented this method. `_send_reminder()` called it unconditionally → `AttributeError` every time the cron tried to send a 24h follow-up. Crash prevented `reminder_count` from ever incrementing, so `action_timeout()` was never reached. Conversations stuck forever |
| **Root cause confirmed** | Cron logged `ERROR: Call from cron AI Agent: Check Conversation Timeouts ... failed` every hour since a general_inquiry conv entered waiting state. Conv 100 stayed `waiting` from 2026-04-03 to 2026-04-17 (14 days) instead of timing out after 72h |
| **Fix 1** | Added `get_reminder_message()` to `GeneralInquirySkill`. Reminder 1: gentle follow-up ("¿Pude ayudarte?"). Reminder 2: friendly closing ("Si necesitas información en otro momento...") |
| **Bug 2 — No error isolation in timeout cron** | `_cron_check_timeouts` had no `try/except` per conversation. One bad conversation crashed the ENTIRE cron run for all skills, leaving other waiting conversations also unprocessed |
| **Fix 2** | Wrapped each conversation's `_send_reminder()` / `action_timeout()` call in `try/except` with savepoint. One failure now logs an error and continues to the next conversation |
| **Bug 3 — max_turns=10 too low for general_inquiry** | Conversations can accumulate turns across unrelated sessions if timeout never fires. 10 turns exhausted by a mix of old (Apr 3) and new (Apr 17) interactions. The PDVSA question (turn 10) got no reply |
| **Fix 3** | `max_turns` raised from 10 → 25 for `general_inquiry` skill. Updated directly in DB (record has `noupdate="1"`) |
| **Cascade effect** | Conv 100 (14-day-old stale conv) appended Apr 17 enrollment inquiry to itself. PDVSA question at turn 10 got no reply. Customer went unanswered |
| **Version** | `17.0.1.29.8` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Batch Date Logic Validator (v1.61.0, testing only)

**New feature: automatic date consistency check on payslip batches.**

| Item | Details |
|------|---------|
| **Problem** | Batches could be created/saved with wrong dates (e.g. MARZO31-7 had April dates) with no warning until the error was noticed manually |
| **Feature** | New "Check Date Logic" button on batch form runs 4 checks: (1) overlap with existing confirmed payslips, (2) gap from expected next period, (3) quincena alignment for V2 structures, (4) batch name vs date month mismatch |
| **UX** | Issues shown in modal wizard with severity (Blocker/Warning/Info). User can fix dates or acknowledge and proceed |
| **Auto-trigger** | Check runs automatically after "Sync Dates to Payslips" — shows wizard instead of success notification if issues found |
| **Override** | `date_check_acknowledged` flag on batch. Resets automatically whenever batch dates change |
| **New files** | `wizard/payslip_batch_date_check_wizard.py`, `wizard/payslip_batch_date_check_wizard_view.xml` |
| **Version** | `17.0.1.61.0` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Glenda 2026-2027 Knowledge Update + PDVSA Policy (ueipab_ai_agent v1.29.7, testing only)

**Updated `general_inquiry` skill with 2026-2027 enrollment costs and new PDVSA/Petropiar policy.**

| Item | Details |
|------|---------|
| **Year updated** | `_INSTITUTIONAL_KNOWLEDGE` now reflects año escolar 2026-2027 |
| **New costs** | Inscripción $197,38 · Seguro escolar $15 (was $10) · Enciclopedia de Inglés $30 (replaces Guía de inglés $15) · Olimpiadas Recreativas $10 · Enciclopedia digital bachillerato $36 · Competencia Kurios $10 (si seleccionado) · Competencia MOA inglés $25 (si seleccionado) |
| **Logística** | Encuentros Regionales/Nacionales: traslados a cargo de los padres |
| **PDVSA policy** | New "POLÍTICA PDVSA / PETROPIAR 2026-2027" section: benefit of 35% credit advance **discontinued**. New prospects: 100% upfront at BCV rate. Existing enrolled families expressing distress: empathetic handling + urgent retention alert |
| **Scenario A** | New PDVSA prospect → inform discontinuation, billing handoff |
| **Scenario B** | Existing 2025-2026 family expressing hardship → empathetic calm, invite Director meeting, urgent `pdvsa_retention` route email to `pagos@ueipab.edu.ve` with ⚠️ subject |
| **New route** | `pdvsa_retention` added to valid handoff routes. On-resolve sends urgent alert: `[URGENTE - Glenda] Familia PDVSA — Riesgo de no renovación — {name}` |
| **Version** | `17.0.1.29.7` |
| **Deployed** | Testing 2026-04-17 |

### 2026-04-17 - Credit Guard False-Positive Fix (ueipab_ai_agent v1.29.6, testing only)

**Eliminated false-positive credit alert emails caused by transient MassivaMóvil API timeouts.**

| Item | Details |
|------|---------|
| **Problem** | Credit Guard fail-safe treated any API error (including 15s read timeout) as depleted credits, immediately activating the kill switch and sending an alert email — even when credits were fine |
| **Root Cause** | `_cron_check_credits()` had no retry or confirmation logic — one failure = immediate alert |
| **Fix** | Added consecutive-failure counter (`ai_agent.credits_fail_count`). Kill switch only activates after N consecutive failures (configurable via `ai_agent.credits_fail_threshold`, default 2). Any clean check resets the counter to 0 |
| **Alert email** | Now includes confirmation count: "Confirmado tras 2 chequeos consecutivos fallidos (umbral: 2). No es una alerta transitoria." |
| **New params** | `ai_agent.credits_fail_threshold` (default `2`), `ai_agent.credits_fail_count` (internal counter) |
| **Version** | `17.0.1.29.6` |
| **Deployed** | Testing 2026-04-17 |

---

## Production Deployments

### 2026-04-08 - LIQUID_ANTIGUEDAD_V2 Bug Fix (DB-only, both envs)

**Fixed incorrect antigüedad calculation for terminated+rehired employees.**

| Item | Details |
|------|---------|
| **Problem** | Employees with `previous_liquidation_date < contract.date_start` (terminated + rehired with a gap) had their antigüedad computed from `original_hire_date` without deducting the prior paid period — effectively paying decades of full seniority instead of only the current contract period |
| **Root Cause** | Validation `previous_liquidation >= contract.date_start` was too strict. For rehired employees, the prior liquidation naturally falls before the new contract start, so the check always failed and fell back to full history |
| **Fix** | Changed to `previous_liquidation > original_hire AND net_months > 0` — correctly computes net antigüedad regardless of rehire gap |
| **Affected rule** | `LIQUID_ANTIGUEDAD_V2` — prod id=29, test id=59 |
| **Script updated** | `scripts/create_production_salary_structures.py` |
| **Deployed** | Testing 2026-04-08, Production 2026-04-08 (direct DB update, no module upgrade needed) |
| **Impact audit** | Only 1 confirmed V2 liquidation in production (SLIP/313 STEFANY ROMERO) — not affected. Open issue: SLIP/447 JOSEFINA RODRIGUEZ (draft) — see [resolution doc](JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md) |

### 2026-04-14 - Disbursement Report V1 Fallback Fix (v1.61.5)

**Fixed crash when generating Payroll Disbursement Report for payslips with missing or no-V2 contract.**

| Item | Details |
|------|---------|
| **Problem** | `AttributeError: 'hr.contract' object has no attribute 'ueipab_deduction_base'` when downloading the report |
| **Root Cause** | `ueipab_deduction_base` was intentionally removed from `ueipab_hr_contract` v2.0.0 (2025-11-24, commit `e953099`) but two V1 fallback references were left in `payroll_disbursement_wizard.py` and `payroll_disbursement_detail_report.xml`. Triggered by MAIRELSY MOTTA's payslip having no contract (expired contract not renewed in time) |
| **Fix** | Replaced V1 `else` branch in both files with safe fallback: `salary = wage`, `bonus = 0.0`. Only fires for edge cases (missing contract or `ueipab_salary_v2` not set) — all V2 employees unaffected |
| **Files** | `models/payroll_disbursement_wizard.py`, `reports/payroll_disbursement_detail_report.xml` |
| **Version** | `17.0.1.61.5` |
| **Deployed** | Testing + Production 2026-04-14 |

### 2026-04-08 - Ack Reminder Email CC Fix (v1.61.4)

**Added CC to `recursoshumanos@ueipab.edu.ve` on acknowledgment reminder emails.**

| Item | Details |
|------|---------|
| **Problem** | Reminder emails sent to employees had no CC — HR had no visibility |
| **Root Cause** | `email_cc` field missing from `email_template_ack_reminder.xml` |
| **Fix** | Added `email_cc` field + changed template to `noupdate="0"` so upgrades apply it. Reset `ir_model_data.noupdate=false` in testing DB before re-upgrade |
| **File** | `data/email_template_ack_reminder.xml` |
| **Version** | `17.0.1.61.4` |
| **Deployed** | Testing 2026-04-08 — Production pending |

### 2026-04-08 - Ack Reminder Wizard Layout Fix (v1.61.3)

**Fixed "📊 Resumen de Resultados" step not fully expanding in the reminder wizard.**

| Item | Details |
|------|---------|
| **Problem** | Step 2 (done state) results panel was constrained — not full width |
| **Root Cause** | `<notebook>` for results was wrapped inside a `<group>` element, which applies Odoo's 2-column constrained layout. Step 1 notebook was placed directly in the form (full width), but step 2 was not |
| **Fix** | Removed `<group>` wrapper, applied `invisible="state != 'done'"` directly on `<notebook>` — same pattern as step 1 |
| **File** | `wizard/ack_reminder_wizard_view.xml` |
| **Version** | `17.0.1.61.3` |
| **Deployed** | Testing + Production 2026-04-08 |

### 2026-04-07 - Advance Payment Email Template Fix (Testing + Production, DB-only)

**Fixed "Payslip Email - Advance Payment - Employee Delivery" showing half the correct advance amount.**

| Item | Details |
|------|---------|
| **Problem** | Email showed `advance_amt = net_wage × (advance_pct/100)` — double-reducing an amount already reduced by salary rules. E.g. GUSTAVO PERDOMO (50% advance, net=$88.46): email showed Bs. 20,988.63 instead of Bs. 41,977.26 |
| **Root Cause (template)** | `advance_amt` t-set used old formula. `full_salary` t-set was missing so the "neto total" reference line also showed wrong value |
| **Root Cause (why prior fix failed)** | In Odoo 17, `body_html` is stored as JSONB `{"en_US":"...", "es_VE":"..."}`. Prior fix ran with `lang=False` which updates a neutral fallback Python reads — but does NOT update the `en_US` key used by the UI at send time. The email was rendered using the unfixed `en_US` key |
| **Fix** | Explicitly iterate `['en_US', 'es_VE']` with `tpl.with_context(lang=lang)` to write each JSONB key directly. Updated `fix_advance_payment_template.py` accordingly |
| **Testing** | Template id=65, both `en_US` and `es_VE` keys fixed. Verified: Bs. 41,977.26 ✓ |
| **Production** | Template id=44, `en_US` key fixed (was missed by prior SQL fix). `es_VE` was already correct. Verified via render test ✓ |
| **Correct formula** | `advance_amt = net_wage` (already the advance), `full_salary = net_wage × (100/advance_pct)` for reference line |

---

### 2026-04-07 - PAY1 Sequence Conflict — Permanent Auto-fix (`ueipab_payroll_enhancements` v1.61.2)

**Implemented two-layer permanent prevention of PAY1 sequence/date mismatch errors.**

| Item | Details |
|------|---------|
| **Problem** | When the PAY1 journal sequence advances into a new month (e.g. April), payslips with `date_to` still in the prior month (e.g. March 31) fail validation: `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/xxxx"` |
| **Layer 1 — Early Warning** | `_collect_date_issues()` (Check 5) detects the sequence/date mismatch before the user clicks Validate. The date check wizard displays an **"Auto-fix Accounting Dates"** button that sets `slip.date` on all draft payslips to the first day of the sequence month. |
| **Layer 2 — Safety Net** | `action_validate_payslips()` override auto-detects any remaining conflict just before confirming payslips and silently sets `slip.date` if needed. Logs the adjustment via Python logger. No popup shown. |
| **Detection method** | Queries `account_move` for the latest posted entry in the payslip journal; extracts year/month from name pattern `PAY1/YYYY/MM/NNNN`. Compares against batch `date_end`. |
| **Files** | `models/hr_payslip_run.py` (+3 methods), `wizard/payslip_batch_date_check_wizard.py` (+`seq_fix_date` field, +`action_fix_accounting_dates`), `wizard/payslip_batch_date_check_wizard_view.xml` (info banner + button) |
| **Version** | `17.0.1.61.2` |

---

### 2026-04-07 - MARZO31-G3 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of DAVID HERNANDEZ payslip in MARZO31-G3 (batch id=43).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/0025"` |
| **Root Cause** | Same pattern as MARZO31-15 (2026-04-06): PAY1 sequence locked in April 2026, payslip `date=NULL` falls back to `date_to=2026-03-31` → sequence mismatch |
| **Fix** | Permanent fix (v1.61.2) handles this automatically at validate time |

---

### 2026-04-06 - MARZO31-15 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of payslip batch MARZO31-15 (id=42, 19 employees).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number of the related Journal Entry (PAY1/2026/04/0006)"` |
| **Root Cause** | PAY1 journal sequence had already advanced to April (`04`) because a prior April-period payslip (ISMARY ARCILA `PAY1/2026/04/0001`) was posted with a March 31 accounting date, pushing the sequence counter into April. All subsequent entries get `PAY1/2026/04/*` sequence numbers. Odoo 17 validates that the entry date month matches the sequence month — March 31 vs April sequence = rejected. |
| **Fix** | Set `date` (accounting date) field to `2026-04-01` on all 19 draft payslips via Odoo shell. `hr_payroll_account_community` uses `slip.date or slip.date_to` for the journal entry date — with `date=NULL` it fell back to `date_to` (2026-03-31). |
| **Action** | `env['hr.payslip'].browse([batch_42_slip_ids]).write({'date': date(2026, 4, 1)})` |

**Result:** 19 journal entries posted as `PAY1/2026/04/0006` → `PAY1/2026/04/0024`, all dated 2026-04-01. Batch closed successfully.

**Accounting Impact:**

| Account | Debit | Credit |
|---------|-------|--------|
| `5.1.01.10.001` Nómina (Docentes) | 3,013.85 | 29.20 |
| `1.1.01.02.001` Banco Venezuela | 29.20 | 3,013.85 |
| **Net payroll expense / bank outflow** | **2,984.65** | **2,984.65** |

**Period note:** These 19 entries (payroll period 2026-03-16→31) post to **April's accounting period** (date=2026-04-01), not March. All other MARZO31 batches posted on 2026-03-31. Finance team informed: March P&L understated by USD 2,984.65; April overstated by same amount. No system correction needed unless March books require restatement.

**Root cause pattern — how to avoid in future:**
> When posting April-period payslips with a March 31 accounting date, Odoo's PAY1 sequence advances to April. Any remaining March-dated payslips then fail with this mismatch. Solution: always post out-of-period payslips with an accounting date that matches the current sequence month, or confirm all March payslips before confirming any April-period ones.

---

### 2026-04-06 - Batch Email Wizard Confirm Step Filter Fix (`ueipab_payroll_enhancements` view patch)

**Fixed confirm step showing all employees instead of only selected ones.**

| Item | Details |
|------|---------|
| **Problem** | Step 2 "Selected Employees" section displayed all employees regardless of selection state |
| **Root Cause** | `domain` on One2many field in Odoo 17 form views does not filter displayed records — only restricts new record creation |
| **Fix** | Added computed `Many2many` field `selected_ids` filtered server-side; confirm block uses `selected_ids` instead of `selection_ids` with broken domain |
| **Files** | `wizard/batch_email_wizard.py` (+computed field), `wizard/batch_email_wizard_view.xml` (field swap) |
| **Deployed** | Both testing and production |

---

### 2026-04-06 - Batch Email Wizard `boolean_toggle` Fix (`ueipab_payroll_enhancements` v60.1 view patch)

**Fixed `RPC_ERROR` when unchecking individual employees in the Send Emails wizard.**

| Item | Details |
|------|---------|
| **Problem** | Clicking any individual checkbox in the employee selection list inside the "Send Emails (with Progress)" wizard threw a Validation Error: `wizard_id` missing on `hr.payslip.batch.email.selection` |
| **Root Cause** | `boolean_toggle` widget fires an immediate `webSave` on the child record, sending only the changed field — ORM rejected because `wizard_id` (`required=True`) was absent from the auto-save payload |
| **Fix** | Removed `widget="boolean_toggle"` from `selected` field in selection tree; standard checkbox saves on row blur / form submit, which includes full context |
| **File** | `wizard/batch_email_wizard_view.xml` — 1-line change |
| **Deployed** | View-only patch applied directly; production manifest version unchanged (60.1) |

**Workaround that worked before fix:** Use "Select All" / "Deselect All" / "Select With Email Only" bulk buttons.

---

### 2026-02-08 - Contact Data Sync Fix (Bounce Log + Partner Emails)

**Fixed cross-reference inconsistencies between Odoo, Freescout bounces, Customers sheet, and Akdemia.**

**Category A — 7 not-found bounce logs linked to correct partners:**
- Linked bounce logs #30, #32, #33, #46, #54, #56, #58 to their matching partners
- Updated `action_tier` from `not_found` to `flag` (temporary) or `clean` (permanent)
- Appended bounced emails to partner email fields (multi-email `;` pattern)
- Contacts: DAIRILYS CHAURAN, ANTONIO MARTINEZ, MARIA APONTE, DOALBERT NUÑEZ, FRANCIA LORETO, CASTO GONZALEZ, GLORIA MILLAN

**Category B — MIGUEL MARIN #3663:**
- Added `susanaquijada102@gmail.com` as secondary email in Odoo (mother's email from Akdemia)
- Updated Customers Google Sheet row 128 to include both emails

**Category C — SORELIS MAITA #3669:**
- Flagged for manual mobile lookup (no phone/mobile in any data source)
- Glenda cannot WhatsApp without mobile number

**Category D — Perdomo duplicates cleanup:**
- Deleted 3 irrelevant bounce logs (#27, #28, #29) — staff, not Representante
- Archived 2 duplicate partners (#3612 Alberto J Perdomo, #3676 Gustavo Perdomo)
- Added `perdomo.gustavo@gmail.com` as secondary email on real user #7

**Category E — 8 orphan bounces:** No action (no match in any data source)

**Verification:** 37 bounce logs total, 29 linked to partners, 8 orphans as expected.

**Scripts:** `scripts/contact_data_sync_fix.py`, `scripts/contact_sync_comparison.py`

---

### 2026-01-10 - LIQUID_VE_V2 Accounting Configuration Fix

**Fixed payslip confirmation error for Liquidación Venezolana V2:**

| Item | Details |
|------|---------|
| **Problem** | SLIP/313 (STEFANY ROMERO) could not be confirmed: "choose Debit and Credit account for at least one salary rule" |
| **Root Cause** | `LIQUID_VE_V2` structure had no accounting accounts configured on any salary rules |
| **Solution** | Configured `LIQUID_NET_V2` rule with debit/credit accounts |
| **Affected Structure** | LIQUID_VE_V2 (Liquidación Venezolana V2) |

**Accounts Configured:**

| Rule | Debit Account | Credit Account |
|------|---------------|----------------|
| LIQUID_NET_V2 | 5.1.01.10.010 (Prestaciones sociales) | 2.1.01.10.005 (Provisión Prestaciones Sociales) |

**Environment Comparison:**
- **Testing:** All 14 rules have accounting configured (more comprehensive)
- **Production:** Only NET rule configured (minimum required - follows design pattern)

**Note:** Per Odoo payroll accounting design, only NET/deduction rules need accounting. Earnings rules should NOT post to accounting.

---

### 2026-01-08 - Salary Rules & Email Template Fix for Remainder Batches

**Fixed salary rules not applying percentage to remainder batches:**

| Item | Details |
|------|---------|
| **Problem** | Remainder batches (is_remainder_batch=True) computed at 100% instead of 50% |
| **Root Cause** | Salary rules only checked `is_advance_payment`, not `is_remainder_batch` |
| **Solution** | Updated condition to check both flags |
| **Rules Fixed** | VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2 |

**Salary Rule Fix:**
```python
# Before (only advance batches got percentage)
if payslip.payslip_run_id and payslip.payslip_run_id.is_advance_payment:

# After (both advance AND remainder batches get percentage)
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
```

**Email Template Updated (ID 45 prod / ID 66 testing):**
- Removed percentage multiplication (salary rules now handle it)
- Uses `net_wage` directly: `<t t-set="rest_usd" t-value="object.net_wage or 0.0"/>`
- Removed "Tasa de Cambio Actual" section

**Synced:** Both production and testing environments updated

### 2026-01-07 - Payslip Batch Delete Fix (NewId Sorting Error)

**Fixed TypeError when deleting payslips from batch UI:**

| Item | Details |
|------|---------|
| **Problem** | Deleting payslip from batch view caused `TypeError: '<' not supported between instances of 'NewId' and 'NewId'` |
| **Root Cause** | `_compute_exchange_rate` sorted payslips by `s.id`, but during onchange operations unsaved records have `NewId` objects that can't be compared |
| **Solution** | Filter to only saved records (with integer IDs) before sorting, with fallback for unsaved slips |
| **File Changed** | `hr_payslip_run.py` line 180 |
| **Version** | 17.0.1.51.2 |

**Fix Applied:**
```python
# Before (broken)
first_slip = batch.slip_ids.sorted(lambda s: s.id)[0]

# After (fixed)
real_slips = batch.slip_ids.filtered(lambda s: isinstance(s.id, int))
if real_slips:
    first_slip = real_slips.sorted(lambda s: s.id)[0]
else:
    first_slip = batch.slip_ids[0]  # Fallback for unsaved slips
```

### 2025-11-27 - Password Reset URL Fix (dbfilter)

**Fixed invitation/password reset email links returning 404:**

| Item | Details |
|------|---------|
| **Problem** | Users clicking password reset links got "Not Found" error |
| **Root Cause** | `dbfilter = ^(DB_UEIPAB\|testing)$` allowed multiple DBs, preventing auto-session |
| **Solution** | Changed to `dbfilter = ^DB_UEIPAB$` (single database) |
| **File Changed** | `/etc/odoo/odoo.conf` in `ueipab17` container |
| **Impact** | 30 pending invitation tokens now work directly |

**Diagnosis:**
- Route `/web/reset_password` uses `auth='public'` + `website=True`
- Without active session, Odoo couldn't determine which database to use
- Single-database filter enables automatic session creation

### 2025-11-27 - Payslip Acknowledgment System + Email Fix

**Payslip Acknowledgment System deployed to production:**

| Change | Details |
|--------|---------|
| ueipab_payroll_enhancements | Upgraded v1.41.0 → v1.43.0 |
| Acknowledgment Fields | access_token, is_acknowledged, acknowledged_date, acknowledged_ip |
| Portal Routes | /payslip/acknowledge/<id>/<token> for employee confirmation |
| Access Tokens | Generated for 49 existing payslips |
| Email Template | "Payslip Compact Report" subject Jinja2 conditional fixed |

**Email Subject Fix:**
- **Old (broken):** `{{ (' │ Lote: ' + object.payslip_run_id.name) if object.payslip_run_id else '' }}`
- **New (working):** `{{' │ Lote: ' + object.payslip_run_id.name if object.payslip_run_id else ''}}`

**Payslip Data Cleanup:**
- Cancelled 5 confirmed payslips (reversed accounting moves)
- Deleted 49 payslips via ORM unlink()
- Deleted 2 test batches
- Reset sequence to 1 (next = SLIP/001)

### 2025-11-26 - SSO Rate Change + Otras Deducciones

| Change | Details |
|--------|---------|
| VE_SSO_DED_V2 | Rate changed from 4.5% → 4% |
| VE_OTHER_DED_V2 | New salary rule created (seq 105) |
| VE_TOTAL_DED_V2 | Updated to include other deductions |
| Contract Field | `ueipab_other_deductions` added |
| Email Template | "Payslip Email - Employee Delivery" created |
| Compact Report | SSO label updated to 4% |

### 2025-11-25 - Production Migration Complete

- All 44 production contracts assigned to "Salarios Venezuela UEIPAB V2"
- ARI rates compared: 43/44 match, 1 discrepancy (ARCIDES ARZOLA)
- V1 fields removed, V2 fields active
- 47 users had excessive permissions removed

---

## Feature Version History

### Payslip Acknowledgment System (v1.42.0-v1.43.0)

**Purpose:** Token-based portal for employees to acknowledge payslip receipt.

**Fields Added:**
- `access_token` - UUID for secure portal access
- `is_acknowledged` - True when employee confirms
- `acknowledged_date` - When confirmation occurred
- `acknowledged_ip` - IP address of confirmation
- `acknowledged_user_agent` - Browser/device info

**Routes:**
- GET `/payslip/acknowledge/<id>/<token>` - Landing page
- POST `/payslip/acknowledge/<id>/<token>/confirm` - Process confirmation

**Session Requirement:** Routes use `auth='public'` which requires database session.

### Batch Email Template Selector (v1.33.0-v1.34.0)

**v1.34.0 (2025-11-24):**
- Fixed `total_net_amount` computed field to include `VE_NET_V2` code
- Changed `exchange_rate` to computed field auto-populated from VEB rates

**v1.33.0 (2025-11-24):**
- Added template selector with 3 templates
- Fixed "Payslip Compact Report" QWeb syntax
- Fixed "Aguinaldos Email" with Christmas theme

### Comprobante de Pago Compacto (v1.40.0-v1.41.0)

**v1.41.0 (2025-11-26):**
- ARI Deduction now shows actual rate from contract
- Before: `VE_ARI_DED_V2 - ARI Variable %`
- After: `Retención impuestos AR-I X%`

**v1.40.0 (2025-11-25):**
- Added payslip's `exchange_rate_used` as default for VEB display
- 4-priority system: Custom → Rate date → Payslip rate → Latest

### Relación de Liquidación Report (v1.19.0-v1.26.0)

**v1.26.0 (2025-11-21):** Auto-latest rate as default for VEB
**v1.25.4 (2025-11-20):** XLSX layout matches PDF exactly
**v1.25.3 (2025-11-20):** Antigüedad displays for ALL employees
**v1.25.2 (2025-11-19):** XLSX export uses wizard's exchange rate
**v1.24.0 (2025-11-18):** Added payslip number to header
**v1.21.0 (2025-11-18):** Improved interest formula display
**v1.20.0 (2025-11-18):** Accrual-based interest calculation
**v1.19.0-1.19.8 (2025-11-17):** Exchange rate override, formatting, layout

### Acuerdo Finiquito Laboral (v1.18.0-v1.25.1)

**v1.25.1 (2025-11-18):** Fixed rate_date parameter handling
**v1.25.0 (2025-11-18):** Added exchange rate override UI
**v1.23.0 (2025-11-18):** Exchange rate override support
**v1.18.2:** DOCX export with python-docx
**v1.18.0:** Initial release with PDF export

### Prestaciones Interest Report (v1.20.0-v1.22.0)

**v1.22.0 (2025-11-18):** Exchange rate consistency fix using `company_rate`
**v1.20.0 (2025-11-18):** Accrual-based interest calculation

### Payslip Email Delivery (hr_payslip_monthly_report v17.0.1.2)

**v17.0.1.2 (2025-11-22):**
- Fixed "Send Mail" button disappearing after cancel
- Added "Reset Send Status" button for recovery

---

## Bug Fixes & Critical Fixes

### V2 Antigüedad Validation Fix (2025-11-21)

**Bug:** Invalid `previous_liquidation_date` causing overpayments
- Dates before contract start created negative "already paid" periods
- Example: SLIP/853 paid $195.08 instead of $100.40 (94% error!)

**Fix:** Added validation `if previous_liquidation and previous_liquidation >= contract.date_start:`
**Impact:** Prevents 20.7% overpayment on affected liquidations

### V2 Vacation/Bono Fix (2025-11-17)

- Fixed double deduction bug where NET was incorrectly $0.00
- New field: `ueipab_vacation_prepaid_amount` for actual prepaid amounts
- School year: Sep 1 - Aug 31

### INCES Deduction Scope Fix (2025-11-18)

**Observation:** INCES should only apply to Utilidades (profit sharing)
**Fix:** Updated LIQUID_INCES_V2 formula to exclude Vacaciones and Bono Vacacional

### Container Issues (2025-11-19)

**Empty Database Pollution:**
- Problem: Database "ueipab" exists but not initialized
- Fix: `DROP DATABASE ueipab;`

**WebSocket Port Mismatch:**
- Problem: Config uses deprecated `longpolling_port = 8078`
- Fix: Update to `gevent_port = 8072`

---

## Technical Learnings

### Accrual-Based Currency Conversion (2025-11-18)

```python
# WRONG - Re-converts total accumulated USD each month
accumulated_usd = 0.0
for month in months:
    accumulated_usd += month_amount_usd
    accumulated_veb = convert(accumulated_usd, month_rate)  # WRONG!

# CORRECT - Convert each month's amount once, accumulate VEB
accumulated_veb = 0.0
for month in months:
    month_veb = convert(month_amount_usd, month_rate)
    accumulated_veb += month_veb  # Proper accrual
```

### Exchange Rate Override for Interest

**Decision:** Interest calculation should IGNORE exchange rate override

**Rationale:**
- Interest accumulated over months at historical rates
- Different from other benefits (computed once at liquidation)
- Both reports must match for employee understanding

---

## AR-I Portal (v17.0.1.0.0)

**Module Structure:**
```
ueipab_ari_portal/
├── models/
│   ├── hr_employee_ari.py    # Main AR-I model (81 fields)
│   ├── ari_excel_generator.py # SENIAT template filler
│   └── hr_contract.py        # Contract extension
├── controllers/portal.py     # Portal routes
├── views/                    # XML views
├── wizard/ari_reject_wizard.py
├── security/                 # Access rules
├── data/                     # Cron, email templates
└── static/templates/         # SENIAT Excel template
```

**Tax Calculation Example:**
```
Annual Income: 50,000.00 (5,555.56 UT @ 9.00 Bs/UT)
Desgravamen Único: 774.00 UT
Taxable Income: 4,781.56 UT
Estimated Tax: 811.65 UT
Personal Rebate: 10.00 UT
Tax to Withhold: 801.65 UT
Withholding %: 14.43%
```

---

## Smart Invoice Confirmation Script (2025-11-27)

**Business Rules:**
| Scenario | Unit Price | Credit Applied |
|----------|------------|----------------|
| Credit ≥ $34.99 | $162.39 (discount) | Yes |
| Credit < $34.99 | $197.38 (regular) | Yes |
| No credit | $197.38 (regular) | No |

**Usage:**
```bash
# Dry run
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/smart_invoice_confirmation.py
```

---

## V1 to V2 Migration

**V1 Fields Removed:**
- `ueipab_salary_base`, `ueipab_bonus_regular`, `ueipab_extra_bonus`
- `ueipab_deduction_base`, `ueipab_monthly_salary`, `ueipab_salary_notes`

**V2 Fields Active:**
- `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `cesta_ticket_usd`
- `ueipab_ari_withholding_rate`, `ueipab_ari_last_update`
- `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`
- `ueipab_vacation_paid_until`, `ueipab_vacation_prepaid_amount`
- `ueipab_other_deductions`

---

**Last Updated:** 2025-11-27
