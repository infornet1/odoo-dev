# Attendance Biweekly Email Report — Implementation Plan

**Status:** Planning
**Target Environment:** Testing first → Production
**Module candidate:** `ueipab_payroll_enhancements` (new sub-feature) or new `ueipab_attendance_report`
**Last Updated:** 2026-05-06

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

### Phase 4 — Cron Automation
- [ ] `ir.cron` record for quincena 1 (day 16)
- [ ] `ir.cron` record for quincena 2 (day 1 next month)
- [ ] Guard: don't create duplicate reports for same employee + period
- [ ] Config param: `attendance_report.auto_send` (True/False kill switch)

### Phase 5 — Dashboard Integration
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
