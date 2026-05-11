# Employee Private Info Request System

**Status:** Production | **Module:** `ueipab_hr_employee` | **Version:** 17.0.1.2.0 | **Deployed:** 2026-05-11

---

## Overview

Token-based self-service system that lets HR send a personalized email to employees asking them to confirm or update specific private information fields. Employees click a link, see a pre-filled form with their current values, edit what's needed, and submit. HR gets a diff notification and a tracking view.

---

## Fields Collected (hr.employee)

| Field | Label |
|---|---|
| `identification_id` | Cédula de identidad |
| `private_email` | Correo personal |
| `private_phone` | Teléfono personal |
| `gender` | Género |
| `birthday` | Fecha de nacimiento |
| `marital` | Estado civil |
| `place_of_birth` | Lugar de nacimiento |
| `country_of_birth` | País de nacimiento |
| `private_city` | Ciudad |
| `private_state_id` | Estado/Provincia |
| `private_zip` | Código postal |
| `private_country_id` | País de residencia |
| `emergency_contact` | Contacto de emergencia |
| `emergency_phone` | Teléfono de emergencia |

---

## Architecture

### Model: `hr.employee.info.request`

| Field | Type | Purpose |
|---|---|---|
| `employee_id` | Many2one hr.employee | Linked employee |
| `campaign_key` | Char | Campaign identifier (e.g. `private_info_v1`) |
| `token` | Char | UUID, auto-generated on create, used in public URL |
| `state` | Selection | `pending` / `completed` |
| `sent_date` | Datetime | When email was sent |
| `completed_date` | Datetime | When employee submitted the form |
| `completed_ip` | Char | IP audit trail |
| `submitted_values` | Text | JSON snapshot: old vs new values diff |
| `reminder_count` | Integer | Number of reminder emails sent (max 2) |
| `reminder_last_date` | Datetime | Timestamp of last reminder |
| `days_pending` | Integer | Computed: days since sent_date (0 if completed) |

### Public Route

`/employee-info/<token>` — `auth='public'`

- **GET**: Renders pre-filled form with current employee values. Missing fields highlighted in amber.
- **POST**: Writes changed fields to `hr.employee`, stores JSON diff, marks `state=completed`, sends HR diff notification.
- **Invalid/used token**: Shows error page.

### Email Template

- **ID (testing):** 88 | **ID (production):** 59
- **Subject:** `Actualización de Datos Personales — UEIPAB`
- **From:** `Recursos Humanos UEIPAB <recursoshumanos@ueipab.edu.ve>`
- **CC:** `recursoshumanos@ueipab.edu.ve`
- **Features:** UEIPAB logo, Fase 1 amber banner, pre-filled data table, CTA button
- **Body:** Stored via direct SQL (JSONB `en_US` + `es_VE` keys) — do NOT use ORM write

### HR Diff Notification

Sent to `recursoshumanos@ueipab.edu.ve` on every form submission. Shows old vs new values in a 3-column table (Campo / Valor anterior / Valor nuevo). If no changes, confirms "datos correctos".

---

## Reminder Tracking

| Event | Trigger | Action |
|---|---|---|
| Day 3, no response | Daily cron | 1st reminder email (`reminder_count` → 1) |
| Day 7, no response | Daily cron | 2nd reminder email (`reminder_count` → 2) |
| Max 2 reminders | — | No further automatic sends |
| Manual | "Enviar Recordatorio" button on form | Re-sends immediately |

**Cron:** `UEIPAB: Recordatorios de Solicitudes de Datos Personales` — daily

---

## HR Tracking View

**Menu:** Employees → Solicitudes de Datos

**List columns:** Empleado, Campaña, Estado (badge), Enviado, Días pendiente, Recordatorios, Último recordatorio, Completado

**Filters:** Pendientes (default), Completados, Sin respuesta +3 días

**Search groups:** Campaña, Estado

---

## Wizard

Action available from Employees list view → "Solicitar Actualización de Datos".

- Set `campaign_key` (default: `private_info_v1`)
- Select employees (defaults to all active `employee_type=employee`)
- Skips employees with existing pending/completed request for the same campaign_key

---

## Files

| File | Purpose |
|---|---|
| `models/hr_employee_info_request.py` | Model + reminder cron + URL helper |
| `controllers/employee_info_controller.py` | GET/POST public form handler + HR diff email |
| `wizard/employee_info_wizard.py` | Batch send wizard |
| `wizard/employee_info_wizard_view.xml` | Wizard view |
| `data/employee_info_request_template.xml` | Email template (source) |
| `data/cron.xml` | Document expiry cron + reminder cron |
| `views/hr_employee_info_request_views.xml` | List/form/search views + menu |
| `security/ir.model.access.csv` | Access rules (hr.group_hr_user) |

---

## Nginx

- **Testing:** `/employee-info` added to location whitelist in `/etc/nginx/sites-available/dev.ueipab.edu.ve`
- **Production:** Uses `location /` catch-all — no whitelist change needed

---

## Campaign: `private_info_v1` (2026-05-11)

- **Launched:** 2026-05-11
- **Scope:** 44 employees from ENERO15 payroll batch
- **Excluded:** Gustavo Perdomo, Administrador 3Dv (×2)
- **Sent:** 44/44 ✓
- **Note:** Initial 44 emails sent without CC (template fixed after); all reminders will CC `recursoshumanos@ueipab.edu.ve`

**Private address bulk-fill (2026-05-11):** 46/47 active employees had empty `private_city/state_id/zip/country_id`. Bulk-updated to El Tigre / Anzoátegui / 6050 / Venezuela via XML-RPC.

---

## Future Campaigns

To run a new campaign:
1. Change `campaign_key` to e.g. `private_info_v2`
2. Use wizard from Employees list or script
3. Existing `private_info_v1` records are unaffected (different key)
