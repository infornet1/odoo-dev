# Attendance Biweekly Email Report — Implementation Plan

**Status:** Ready for Production — awaiting maintenance window
**Testing:** Validated with NIDYA LIRA + ANDRES MORALES + PABLO NAVARRO + SERGIO MANEIRO + ARCIDES ARZOLA + DAVID HERNANDEZ + NORKA LA ROSA
**Module:** `ueipab_attendance_report` v17.0.1.2.0
**Last Updated:** 2026-05-06

### v17.0.1.2.0 additions (validated in testing)
- **Holiday support** — 30 Venezuelan national/religious/school holidays excluded from absent count. Config: `attendance_report.holidays` (auto-created on install). HR can add MPPE pedagogical days without losing them on upgrades.
- **Receso Navideño** — Dec 15–Jan 11 (MPPE official 2025-2026). Dec Q2 → `workdays=0 absent=0`. Jan Q1 → `holidays=7`.
- **Special schedule support** — Maintenance/security staff (ANDRES MORALES 571, PABLO NAVARRO 606, SERGIO MANEIRO 610) get neutral `─ Día libre` instead of ❌, weekend attendance visible, `⭐ Horario especial` banner. Config: `attendance_report.special_schedule_employees` = `571,606,610` (manual step after install).
- **Directors** (ARCIDES ARZOLA, DAVID HERNANDEZ, NORKA LA ROSA) — standard Mon-Fri, zero weekend work, handled correctly by regular report with no special config.

---

## 1. Purpose

Send each active employee a **bi-weekly (quincenal) attendance summary** via email so they can:
- Verify all their entry/exit records are correct before payroll closes
- Spot missing check-outs or absent days before any deductions are applied
- Formally acknowledge receipt (audit trail), mirroring the Payslip ACK system

The report serves as a **pre-deduction warning mechanism**: employees see discrepancies in the same quincena window, reducing disputes when payroll applies attendance-based discounts.

---

## 2. Email Visual Design

### 2.1 Full Email Layout (top → bottom)

```
┌─────────────────────────────────────────────────────────┐
│  ░░░░░ HEADER BANNER ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  [Navy gradient #1a2c5b → #2471a3]                      │
│                                                         │
│    📊  Reporte de Asistencia Quincenal                  │
│        Instituto Privado Andrés Bello, CA               │
│        Quincena: 1 al 15 de Mayo 2026                   │
└─────────────────────────────────────────────────────────┘
│                                                         │
│  Estimado/a  NOMBRE COMPLETO,                           │
│                                                         │
│  A continuación encontrará su registro de asistencia    │
│  correspondiente a la quincena del 1 al 15 de           │
│  Mayo 2026 (10 días hábiles).                           │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░ SEMANA 1 — 28 Abr al 02 May ░░░░░░░░░░░░░░░░░░░░░░  │
│  [sub-header light navy #2471a3, white text]            │
├────────┬────────────┬──────────┬──────────┬──────┬──────┤
│ Fecha  │ Día        │ Entrada  │ Salida   │ Hrs  │Estado│
├────────┼────────────┼──────────┼──────────┼──────┼──────┤
│ 28/04  │ Lunes      │ 07:55    │ 17:02    │ 9.12 │  ✅  │
│ 29/04  │ Martes     │ 08:03    │ 17:15    │ 9.20 │  ✅  │
│ 30/04  │ Miércoles  │ 08:30    │  ─ ─ ─   │  ─   │  ⚠️  │
│ 01/05  │ Jueves     │  ─ ─ ─   │  ─ ─ ─   │  ─   │  ❌  │
│ 02/05  │ Viernes    │ 07:58    │ 17:05    │ 9.12 │  ✅  │
├────────┴────────────┴──────────┴──────────┼──────┴──────┤
│                       Sub-total Semana 1  │  27.44 h    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░ SEMANA 2 — 05 May al 09 May ░░░░░░░░░░░░░░░░░░░░░░  │
├────────┬────────────┬──────────┬──────────┬──────┬──────┤
│ 05/05  │ Lunes      │ 08:01    │ 17:10    │ 9.15 │  ✅  │
│ 06/05  │ Martes     │ 07:55    │ 17:00    │ 9.08 │  ✅  │
│ 07/05  │ Miércoles  │ 08:10    │ 17:20    │ 9.17 │  ✅  │
│ 08/05  │ Jueves     │ 08:05    │ 17:15    │ 9.17 │  ✅  │
│ 09/05  │ Viernes    │ 08:00    │ 17:05    │ 9.08 │  ✅  │
├────────┴────────────┴──────────┴──────────┼──────┴──────┤
│                       Sub-total Semana 2  │  45.65 h    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░░░░░ RESUMEN QUINCENAL ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  [Light blue bg #f0f4fa, border #1a2c5b]                │
│                                                         │
│   Total horas trabajadas   :   73.09 h                  │
│   Días hábiles en período  :   10 días                  │
│   Registros completos      :   8 / 10                   │
│   Sin registro (ausentes)  :   1 día                    │
│   Sin salida registrada    :   1 día                    │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  [STATUS BANNER — changes color based on state]         │
│                                                         │
│  ✅ VERDE — "Asistencia conforme. No se detectaron     │
│    incidencias en este período."                        │
│                                                         │
│  ─────── OR ──────────────────────────────────────────  │
│                                                         │
│  ⚠️ NARANJA — "Su registro presenta incidencias        │
│    (1 ausencia, 1 salida faltante). Si algún registro   │
│    es incorrecto, comuníquese con RRHH antes del        │
│    [fecha límite] para su corrección. Las               │
│    inconsistencias no corregidas pueden generar         │
│    descuentos en nómina."                               │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░░░░░ LEYENDA ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│   ✅  Registro completo (entrada y salida registrados)  │
│   ⚠️  Salida no registrada (requiere corrección)        │
│   ❌  Sin registro (ausencia o día no marcado)          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░░░░░ ACK BUTTON (green gradient) ░░░░░░░░░░░░░░░░░░  │
│                                                         │
│  ✅ He revisado mi reporte de asistencia quincenal      │
│     y confirmo su recepción                             │
│                                                         │
│       [ Confirmar Recepción del Reporte ]               │
│                                                         │
│  Su confirmación quedará registrada con fecha,          │
│  hora e IP de acceso.                                   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  ░░░░░ FOOTER ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  Cordialmente,                                          │
│  Recursos Humanos                                       │
│  Instituto Privado Andrés Bello                         │
│  📧 recursoshumanos@ueipab.edu.ve                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Status Cell Color Coding

| Situation | Icon | Row background | Status text |
|-----------|------|----------------|-------------|
| Entry + exit recorded | ✅ | White | — |
| Entry only, no exit | ⚠️ | `#fff3cd` (yellow tint) | "Sin salida" |
| No record at all | ❌ | `#fde8e8` (red tint) | "Sin registro" |
| Weekend / holiday | — | `#f5f5f5` (gray tint) | "No hábil" |

### 2.3 Status Banner Logic

| Condition | Banner color | Message |
|-----------|-------------|---------|
| 0 incidents | `#d4edda` green | "Asistencia conforme" |
| Only missing exits | `#fff3cd` amber | "Salidas pendientes de corrección" |
| Any absent day | `#fde8e8` red-ish | "Presenta ausencias — contactar RRHH" |

---

## 3. Technical Architecture

### 3.1 Module Decision

**Decision: New module `ueipab_attendance_report`**

- Keeps `ueipab_payroll_enhancements` untouched — zero risk to production payroll, liquidations, and loan processing
- Independent version lifecycle — attendance report can be upgraded or rolled back without affecting payroll
- Clean git history — attendance commits never mix with payroll changes
- Follows the same pattern as other isolated features: `ueipab_hrms_dashboard_ack`, `ueipab_bounce_log`
- One-time install cost in testing → production is acceptable given the safety benefit

### 3.2 Data Model

#### New Model: `hr.attendance.report` (permanent, not transient)

```
hr.attendance.report
├── employee_id        Many2one(hr.employee)       — required
├── date_from          Date                         — quincena start
├── date_to            Date                         — quincena end
├── quincena           Selection [('1','1-15'), ('2','16-fin')]
├── state              Selection [draft, sent, acknowledged]
├── sent_date          Datetime                     — when email sent
├── ack_date           Datetime                     — when employee clicked
├── ack_ip             Char                         — IP from ack click
├── ack_token          Char(64)                     — UUID, used in URL
├── absent_days        Integer                      — computed
├── missing_exit_days  Integer                      — computed
├── total_worked_hours Float                        — computed
```

Each record = one employee × one quincena. Mirrors how `hr.payslip` works.

#### New Wizard: `hr.attendance.report.wizard` (TransientModel)

```
hr.attendance.report.wizard
├── date_from          Date        — auto-filled from quincena logic
├── date_to            Date        — auto-filled
├── employee_ids       Many2many(hr.employee)       — defaults all active
├── quincena_select    Selection   — '1' or '2' + year/month picker
├── send_email         Boolean     — True = send now, False = preview only
```

### 3.3 Dynamic Attendance Data (QWeb Template)

The template is linked to `hr.attendance.report` model. Key computed method on the model:

```python
def get_attendance_days(self):
    """Returns list of dicts for each calendar day in period."""
    # Iterates date_from → date_to
    # For each day: lookup hr.attendance records for self.employee_id
    # Returns: [{date, weekday_name, is_workday, check_in, check_out,
    #            worked_hours, status: 'ok'|'missing_exit'|'absent'|'holiday'}]
```

This method is called inside QWeb with `t-foreach`, producing the day rows.

### 3.4 Acknowledgment URL

Same pattern as Payslip ACK:

```
https://dev.ueipab.edu.ve/attendance-ack/<token>
```

Controller sets `state='acknowledged'`, records `ack_date` and `ack_ip`, renders a simple confirmation page.

---

## 4. Sending Workflow

### 4.1 Manual Send (Wizard)

```
HR opens Payroll → Reports → Reporte de Asistencia Quincenal
    → Selects period (auto-fills from quincena logic)
    → Selects employees (default: all active)
    → Click "Generar y Enviar"
        ↓
    Creates one hr.attendance.report per employee
    Sends email via mail.template
    state → 'sent'
```

### 4.2 Automatic Cron (Bi-weekly)

Two cron jobs:
- **Quincena 1** — fires on **day 16** of each month at 07:00 VET (covers days 1–15)
- **Quincena 2** — fires on **1st of next month** at 07:00 VET (covers days 16–end)

Cron auto-determines `date_from`/`date_to`, sends to all active employees with `work_email`.

---

## 5. Mail Template

**Template name:** `Attendance Report - Quincenal`
**Model:** `hr.attendance.report`
**From:** `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>`
**To:** `{{ object.employee_id.work_email }}`
**Subject:** `📊 Reporte de Asistencia │ Quincena {{ object.quincena }} │ {{ period_label }} │ {{ object.employee_id.name }}`

Key QWeb blocks:
- `t-foreach` over `object.get_attendance_days()` → daily rows
- Week separator rows computed by checking ISO week number change
- Summary block reads `object.absent_days`, `object.missing_exit_days`, `object.total_worked_hours`
- Status banner rendered with `t-if/t-elif` on incident count
- ACK button uses `object._get_ack_url()`

---

## 6. ACK System (mirrors Payslip ACK)

| Aspect | Payslip ACK | Attendance ACK |
|--------|------------|----------------|
| Token model | `hr.payslip` field | `hr.attendance.report` field |
| URL path | `/payslip-ack/<token>` | `/attendance-ack/<token>` |
| Confirmation page | Simple "Acusado" page | Same style |
| Odoo view | Payslip form badge | Attendance report list/form |
| Dashboard widget | HRMS Dashboard | Same widget (extend) |

A new tab or section in the existing HRMS Dashboard widget can show attendance ACK status alongside payslip ACK status.

---

## 7. Implementation Phases

### Phase 1 — Data Model + Manual Wizard (Testing) ✅ COMPLETE 2026-05-06
- [x] Create `hr.attendance.report` model with all fields
- [x] Create `hr.attendance.report.wizard` transient model
- [x] `get_attendance_days()` method + summary computed fields
- [x] `_build_html_table()` — renders day-by-day HTML table (used in form view + future email)
- [x] Menu entry: `Payroll → Reports → Reporte de Asistencia Quincenal` (added via `views/menu.xml` — does NOT touch `ueipab_payroll_enhancements`)
- [x] Security: `hr_payroll_manager` full access, `hr_payroll_user` read/create
- [x] Installed and smoke-tested in `testing` DB — `ueipab_attendance_report` v17.0.1.0.0

### Phase 2 — Email Template + ACK Controller ✅ COMPLETE 2026-05-06
- [x] QWeb template (id=76 in testing) — no attachments, inline body only
- [x] Week grouping via `get_attendance_weeks()`, iterated with `t-foreach`
- [x] Status banner logic (ok/warning/danger) via `get_status_info()`
- [x] Leyenda block + contact box
- [x] ACK button with `_get_ack_url()` → `/attendance-ack/<token>`
- [x] Controller route `/attendance-ack/<token>` — sets state/ack_date/IP
- [x] Three response pages: success, already_done, invalid
- [x] `action_send_email()` on model — sends + sets state='sent'
- [x] Wizard `send_email` toggle — optional bulk send on generate
- [x] Upgraded and smoke-tested in `testing` DB

### Phase 2 Enhancements ✅ COMPLETE 2026-05-06
- [x] Bulk range mode wizard: select month range → generates Q1+Q2 per month (Oct 2025 → today)
- [x] Employee filter UX: 3-mode radio (all / department / manual) + live counter
- [x] `is_historical` flag: periods before current month auto-acknowledged on `create()`
- [x] Historical email footer: informational banner replaces ACK button for closed periods
- [x] State guard: `_send_emails()` does not downgrade `acknowledged → sent` for historical
- [x] `noupdate` removed from template so body reloads on every upgrade (dev phase)
- [x] Year fields changed `Integer → Char` (prevents "2,026" locale formatting)
- [x] Radio button groups use `col="1"` for proper left-aligned layout
- [x] Danger banner message updated — Opción 1 professional tone (June 1 2026 policy)
- [x] Full end-to-end test: NIDYA LIRA 108 records, 15 quincenas, historical auto-ack confirmed

---

## Production Deployment

### Prerequisites
- `ueipab_attendance_report/` copied to `/home/vision/ueipab17/addons/` on production server
- Module installed via `docker exec ueipab17 /usr/bin/odoo -d DB_UEIPAB -i ueipab_attendance_report --stop-after-init`
- Container restarted

### First-run bulk send procedure
1. Open **Payroll → Reports → Reporte de Asistencia Quincenal**
2. Mode: **Rango de meses**
3. Desde: Octubre 2025 / Hasta: current month
4. Filter: **Todos los empleados activos**
5. ✅ Enviar correo inmediatamente
6. Click **Generar Reportes**

**Expected outcome:**
- Oct 2025 → Apr 2026 (historical): `state=acknowledged`, email arrives with informational footer — no employee action required
- Current quincena: `state=sent`, email arrives with green **Confirmar Recepción** button

### Key facts for HR
- Discount policy message effective: **1 de junio de 2026**
- Historical periods are auto-confirmed — employees should NOT be asked to re-confirm
- ACK link per employee: `/attendance-ack/<unique-token>` (public, no login needed)
- Contact for discrepancies: `recursoshumanos@ueipab.edu.ve`

---

### Phase 3 — Cron Automation (post-production)
- [ ] `ir.cron` record for quincena 1 (day 16)
- [ ] `ir.cron` record for quincena 2 (day 1 next month)
- [ ] Guard: don't create duplicate reports for same employee + period
- [ ] Config param: `attendance_report.auto_send` (True/False kill switch)

### Phase 4 — Dashboard Integration (post-production)
- [ ] Extend `ueipab_hrms_dashboard_ack` widget to show attendance ACK stats
- [ ] "Pendiente" / "Confirmado" count for current quincena

---

## 8. Open Questions (Decisions Needed)

1. **Workday schedule:** How do we know which days are "expected" work days?
   - Option A: All weekdays Mon–Fri (simple, may miss holidays)
   - Option B: Use `resource.calendar` from the employee's contract (accurate but complex)
   - Option C: Manual holiday list (same `ai_agent.holidays` param already configured)
   - **Recommendation: Option A + Option C** — skip weekends + skip configured holidays

2. **Multiple check-ins per day:** If an employee has 2 attendance records for the same day (e.g. goes out and comes back), should we:
   - A) Show the first check-in and last check-out (total span)
   - B) Sum all worked_hours for the day
   - **Recommendation: Option B** — sum all `worked_hours` for the day, show first in / last out

3. **Missing exit threshold:** Some check-outs within the same day may be legitimate (lunch break scanning). Define: if `worked_hours < 4` and no check-out after 16:00 → flag as `missing_exit`.

4. **Expected hours per day:** What is the standard workday?
   - If contract has `resource.calendar` → use scheduled hours
   - Otherwise default: **8 hours/day**

5. **Module placement:** New `ueipab_attendance_report` vs. add to `ueipab_payroll_enhancements`?
   - Current lean: add to `ueipab_payroll_enhancements` to avoid new install cycle

6. **ACK requirement:** Should ACK be mandatory? Or informational only?
   - If mandatory: block payslip confirmation until ACK received? (complex)
   - **Recommendation: Informational only** in Phase 1; add enforcement later if needed

7. **Quincena date cut-off for corrections:** What is the deadline for employees to report discrepancies? Configurable param or fixed (e.g., day 18 and day 3)?

---

## 9. Color Scheme (Consistent with UEIPAB)

```css
/* Header / sections */
background: linear-gradient(135deg, #1a2c5b 0%, #2471a3 100%);

/* Summary box */
background: #f0f4fa;
border: 2px solid #1a2c5b;

/* OK status */
color: #155724; background: #d4edda;

/* Warning (missing exit) */
color: #856404; background: #fff3cd;

/* Alert (absent) */
color: #721c24; background: #fde8e8;

/* Holiday/weekend */
color: #6c757d; background: #f8f9fa;

/* ACK button */
background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
```

---

## 10. File Structure (when implemented)

```
addons/ueipab_attendance_report/
├── __init__.py
├── __manifest__.py                      ← depends: ['hr_attendance', 'mail']
├── models/
│   ├── __init__.py
│   └── hr_attendance_report.py          ← hr.attendance.report model
├── wizard/
│   ├── __init__.py
│   └── hr_attendance_report_wizard.py   ← TransientModel wizard
├── views/
│   ├── hr_attendance_report_views.xml   ← list/form views
│   ├── hr_attendance_report_wizard.xml  ← wizard dialog
│   └── menu.xml                         ← Payroll → Reports → entry
├── data/
│   ├── mail_template_attendance.xml     ← QWeb email template
│   └── ir_cron_attendance_report.xml    ← 2 bi-weekly crons
├── controllers/
│   ├── __init__.py
│   └── attendance_ack.py                ← /attendance-ack/<token> handler
└── security/
    ├── ir.model.access.csv              ← access rules for new model
    └── security.xml                     ← groups (reuse hr_payroll groups)
```

**`__manifest__.py` key fields:**
```python
{
    'name': 'UEIPAB Attendance Biweekly Report',
    'version': '17.0.1.0.0',
    'depends': ['hr_attendance', 'mail', 'hr_payroll_community'],
    'data': [...],
    'installable': True,
}
```

---

## 11. Version

Initial release: `ueipab_attendance_report` `17.0.1.0.0`
No version bump needed on `ueipab_payroll_enhancements`.

---

## References

- [Payslip ACK System](PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) — ACK pattern to mirror
- [Batch Email Wizard](BATCH_EMAIL_WIZARD.md) — sending pattern reference
- [Changelog](CHANGELOG.md)

---

## Appendix A — Attendance Daily Alert Operational Reference

**Script:** `scripts/attendance_daily_alert.py`

**Cron schedule (`/etc/cron.d/attendance_daily_alert`):**
- `30 11 * * 1-5` — morning 11:30 VET: recap yesterday (no attendance / missing exit / <5h) → HTML email to employee CC recursoshumanos@. Skips if yesterday was weekend or holiday.
- `30 23 * * 1-5` — evening 23:30 VET: employees with check_in but no check_out → SSH to Router 2 (`172.28.10.10` ZeroTier) → Mikrotik hotspot logout log. WiFi found + <20:00 VET + after check_in → write that time. Fallback → 14:00 VET (18:00 UTC). No email sent.

Special-schedule employees (ids 571/606/610) skipped entirely in both modes.

**State file:** `attendance_daily_alert_state.json` — keys `morning_DATE_EMPID` / `evening_DATE_EMPID`; entries >14 days pruned. WiFi coverage: 8/45 employees in `payroll_db.wifi_hotspot_users`.

**Correction button:** `get_fix_url_for_employee(emp_id, date)` looks up matching `hr.attendance.report` (state=sent/draft) → injects "📝 Solicitar Corrección" link to `/attendance-fix/<token>`. Falls back to plain card if no report. CC `recursoshumanos@` via `email_cc`.

**Attendance record source tracing:** `hr_attendance.in_mode` / `out_mode` fields: `kiosk` / `systray` / `manual` / empty (sync scripts). Also `in_ip_address`, `in_browser`, `create_uid=4` (public/kiosk). Timestamps = server-side UTC. For kiosk records: production Odoo server's clock at HTTP POST receipt.

---

## Appendix B — Correction Wizard (v6.21–6.23)

**Rejection wizard (v6.21):** Clicking ❌ Rechazar on `hr.attendance.correction` opens `hr.attendance.rejection.wizard`. Manager types optional reason → `action_reject(reason=...)` writes it before firing email → employee receives red "Observación de RRHH" block. `rejection_reason` on form is `readonly=1` (audit only).

**CC policy (v6.22):** All correction events (submit/approve/reject) CC `recursoshumanos@` + `arcides.arzola@` via `_build_cc()`. Guard: if ARCIDES is the employee, omit from CC. `email_values={'email_cc': self._build_cc()}` overrides template's own CC.

**Double-submit guard (v6.23):** `/attendance-fix/<token>` JS disables submit button + shows bottom banner on first click — prevents race-condition duplicate `hr.attendance.correction` records from double-taps.

---

## Appendix C — Biweekly Report Wizard Technical Patterns (v6.4+)

- **Employee default:** `_get_payroll_employees()` — latest closed `hr.payslip.run` employees (e.g. MAYO15 = 44). Fallback: `contract_ids.state='open'`. File: `wizard/hr_attendance_report_wizard.py`
- **Resend skips acknowledged:** `action_resend_reports()` domain includes `('state','!=','acknowledged')`. Never re-emails employees who already confirmed.
- **No UI timeout:** `force_send=False` in `_send_emails()` — emails queue as `state='outgoing'`, mail queue cron delivers. Before: 44 × 2.5s = 110s → HTTP worker killed.
- **Mail queue cron:** id=3 in production. Manual trigger: `execute_kw(..., 'ir.cron', 'method_direct_trigger', [[3]])`.
- **ACK CC (v6.4):** `_notify_rrhh()` fires on `/attendance-ack/<token>` only. CC to `recursoshumanos@` on ACK confirmation, NOT on reminder send.
- **States:** `draft` → `sent` (queued) → `acknowledged`. `is_historical` records auto-acknowledged on create.
- **ORM query fields:** `date_from`, `date_to`, `month` (int), `year` (int), `quincena` (`'1'`/`'2'`). NOT `period_start`/`period_end` — raise `ValueError`.
- **Production email template:** id=53 (`ueipab_attendance_report.email_template_attendance_report`).
- **Test account exclusion:** "Administrador 3Dv" has duplicate `hr.employee` ids 574 and 764 (both `tdv.devs@gmail.com`). Exclude: `('employee_id','not in',[574,764])`.
