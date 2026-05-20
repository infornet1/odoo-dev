# Control Asistencia → Odoo Attendance Bridge

**Status:** Production  
**Script:** `scripts/sync_control_asistencia.py`  
**Cron:** `/etc/cron.d/sync_control_asistencia` — weekdays 22:30 UTC (`--live --env production`)

---

## Overview

Daily bridge that converts teacher activity in the `control_asistencias` Flask app into
`hr.attendance` records in Odoo. The logic is: if a teacher submitted student attendance
records for a given day, that submission proves the teacher was physically present — so an
attendance record is auto-created for them (07:00–13:30 VET, 6.5 h).

---

## Data Flow

```
control_asistencias MySQL
  └─ asistencia_estudiante  (V2 — per-student individual records)
       └─ id_usuario → usuario.email
              │
              ▼
    sync_control_asistencia.py
       matches usuario.email → hr.employee.work_email
              │
              ▼
    Odoo hr.attendance
       check_in  = 11:00 UTC (07:00 VET)
       check_out = 17:30 UTC (13:30 VET)
       worked_hours = 6.5
              │
              ▼
    HR summary email → recursoshumanos@ueipab.edu.ve
```

### Source table (V2)

The sync uses `asistencia_estudiante` (V2), which is what teachers submit via the Flask app's
`/api/asistencia-individual/registrar` endpoint. The legacy table (`asistencia_legacy`) is only
used by old admin stats routes and is not part of this pipeline.

---

## Current State (as of 2026-05-16)

| Metric | Value |
|--------|-------|
| Active teachers in control_asistencias | 27 |
| Sections (secciones) | 15 |
| Students enrolled | 224 |
| Typical daily submission rate | ~17/27 (63%) |

### Submission gaps identified

| Teacher | Last submission | Assigned sections | Issue |
|---------|----------------|-------------------|-------|
| GLADYS BRITO CALZADILLA | Never | 0 | Never used system |
| JESUS DI CESARE | Never | **9** | Largest coverage miss |
| LEIDYMAR ARAY MENESES | Never | 6 | Never used system |
| CAMILA ROSSATO ROJAS | Never | 0 | Never used system |
| EMILIO ISEA APONTE | Never | 6 | Never used system |
| GABRIEL ESPAÑA | 2026-04-08 | 6 | Effectively inactive |

These teachers receive zero `hr.attendance` records via this bridge and appear as absent in
their biweekly attendance reports, generating spurious correction requests.

---

## Current HR Email

The daily summary goes to `recursoshumanos@ueipab.edu.ve` and contains three tables:

- ✅ **Registros creados** — teachers whose Odoo attendance was created today
- ⏩ **Omitidos** — teachers who already had a record (manual or biometric)
- ⚠️ **Sin coincidencia** — emails in control_asistencias with no matching Odoo employee

**Gap:** teachers who are in Odoo but simply did NOT submit today are invisible to HR.

---

## Planned Enhancements

### 1. Non-submitters section in HR email (Priority: High)

Add a 4th table to `_build_email_body()` showing active Odoo teachers who had no submission
in control_asistencias on the target date.

**Implementation:**
- At the start of `main()`, fetch the full active teacher list from Odoo (or control_asistencias)
- After processing, compute `non_submitters = all_teachers - submitted_teachers`
- Add a 4th section in `_build_email_body()`:

```html
<h3 style="color:#721c24;">🚫 No registraron en control_asistencias (N)</h3>
<table ...>
  <tr><th>Docente</th><th>Último registro</th></tr>
  ...
</table>
```

- MySQL query to get last submission date per teacher:

```sql
SELECT u.id_usuario, CONCAT(u.nombre,' ',u.apellido) AS full_name, u.email,
       MAX(ae.fecha) AS last_submission
FROM usuario u
LEFT JOIN asistencia_estudiante ae ON ae.id_usuario = u.id_usuario
WHERE u.rol = 'profesor' AND u.activo = 1
GROUP BY u.id_usuario
```

### 2. Submission rate KPI in email header (Priority: High)

Add a summary line before the tables showing daily coverage:

```
📊 Cobertura del día: 17 / 27 docentes (63%)
```

**Implementation:** single line in `_build_email_body()` using `len(submitted) / total_teachers`.

### 3. Zero-submission guard (Priority: Medium)

Currently the script exits with `print("No submissions found")` and sends no email.
On a school day this likely indicates a system failure, not 27 absences.

**Implementation:** after `get_teachers_who_submitted()` returns empty, check if it is a
scheduled school day (Mon–Fri, not a holiday per `CalendarioEscolar`). If yes, send an
alert email to HR instead of silently exiting.

```python
if not teachers:
    if is_school_day(target_date):
        backend.send_alert_email(target_date, "ALERTA: Ningún docente registró asistencia")
    return
```

### 4. Section coverage column (Priority: Low)

In the "Registros creados" table, add a column showing how many sections/students the
teacher covered:

| Docente | Horario | Secciones | Alumnos registrados |
|---------|---------|-----------|---------------------|
| GIOVANNI VEZZA | 07:00 → 13:30 | 5 | 48 |

**Implementation:** extend `get_teachers_who_submitted()` to also return section count and
student count from `asistencia_estudiante`.

### 5. Source attribution in employee attendance email (Priority: Low)

The biweekly attendance report (`mail_template_attendance.xml`) shows "07:00 → 13:30" for
every control_asistencias-sourced record. Teachers who arrived at 8:30 may be confused and
open correction requests unnecessarily.

Add a footnote in the email body (or a per-row tooltip approach) explaining the fixed
schedule is generated from student attendance reporting, not a biometric system.

**Suggested footer line:**
```
Los registros marcados provienen del Sistema de Control de Asistencias Estudiantiles
y reflejan el horario estándar del plantel (07:00–13:30). No representan la hora
exacta de entrada/salida del docente.
```

---

## Implementation Notes

- The `_build_email_body()` function in `sync_control_asistencia.py` is self-contained —
  all enhancements (1, 2, 3, 4) only require changes to that script, no Odoo module upgrade.
- Enhancement 5 requires editing `mail_template_attendance.xml` in `ueipab_attendance_report`
  and upgrading the module.
- Non-submitters query must run against MySQL (`control_asistencias.usuario`) — the
  "ground truth" for who should be submitting is the Flask app, not Odoo, since only
  teachers with `rol='profesor' AND activo=1` are expected to use the system.
- Avoid fetching all Odoo employees for the non-submitters section; cross-reference only
  against `control_asistencias.usuario` to keep the email meaningful (not every Odoo
  employee is a teacher in this system).
