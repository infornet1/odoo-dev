# Leave Notification System — Features #76, #77, #78

## Overview

**Scripts:** `scripts/leave_notification.py` + `scripts/hr_leave_attendance_digest.py`
**Crons:** `/etc/cron.d/leave_notification` (every 15 min weekdays) + `/etc/cron.d/hr_leave_attendance_digest` (08:00 VET weekdays)

---

## Odoo-level CC on Outcomes (v17.0.1.6.27, 2026-06-19)

`ueipab_attendance_report/models/hr_leave.py` overrides `hr.leave` to CC `recursoshumanos@ueipab.edu.ve` **immediately** (synchronous, no cron delay) when a leave reaches a final state:

- `_validate_leave_request` override → `message_notify` to RRHH after the employee approval email is sent
- `action_refuse` override → `message_notify` to RRHH after the employee refusal email is sent

Both use `holiday.sudo().message_notify(...)` so they work regardless of the approver's access level.  The script's `notified_validate_*` / `notified_refuse_*` entries remain as a ~15-min safety net (intentional slight duplication for outcome states).

---

## leave_notification.py (Feature #76)

Polls `hr.leave` for actionable states every 15 min:
- `confirm` → "📋 Nueva Solicitud de Permiso" email to `recursoshumanos@ueipab.edu.ve` (blue header)
- `validate1` → "🔔 Segunda Validación Requerida" email to `recursoshumanos@ueipab.edu.ve` (orange header)
- `validate` / `refuse` → also handled here as safety net; primary path is now the Odoo-level CC above
- All events CC `arcides.arzola@ueipab.edu.ve` (omitted if the leave is for ARCIDES himself)
- State file `scripts/leave_notification_state.json` tracks `notified_confirm_{id}` / `notified_validate1_{id}` / `notified_validate_{id}` / `notified_refuse_{id}` separately — a confirm→validate1 transition fires a second email
- Test: `python3 scripts/leave_notification.py --test-email gustavo.perdomo@ueipab.edu.ve`

---

## hr_leave_attendance_digest.py (Feature #77)

Daily digest email to CEO (08:00 VET), 3 sections:
1. 🔴 **Pending approvals** — split by stage: `validate1` rows ("Validar →", orange) above `confirm` rows ("Aprobar →", blue)
2. 📅 **30-day leave activity** per employee: approved days / pending days / request count
3. ⚠️ **High-issue employees** — parsed from `attendance_daily_alert_state.json` morning entries (threshold: `HIGH_ISSUE_THRESHOLD = 3`; consider raising to 5)

---

## Leave Type Validation Matrix (production)

| Approval | Leave Types |
|----------|-------------|
| `both` (2 approvals) | Tiempo personal pagado, Sin pagar, Permiso Muerte (luto), Diligencia Personal, Cita Médica de un familiar |
| `hr` (HR only) | Tiempo personal por enfermedad, Lactancia, Cita Médica personal, Cuidados maternos, Reposo Postnatal |
| `manager` (manager only) | Días compensatorios |

---

## Work Schedule

**Standard 40h (calendar_id=1):** Morning start corrected 08:00→**07:00 VET** on 2026-05-28. All weekdays now 07:00–12:00 + 13:00–17:00. Re-apply `hr_org_chart` patch (`/tmp/patch_org_chart.py`) if containers are rebuilt.

---

## Feature #78 — Leave Cross-check in Daily Attendance Alert

Morning attendance alert mode fetches `hr.leave` for yesterday via `get_leaves_for_date()`. If employee has matching leave, `_format_leave_context_html()` injects a colored context block:
- ✅ green → `validate` (approved leave)
- ⏳ yellow → `confirm` / `validate1` (pending)

Attendance flag is still raised — context block adds clarity, not suppression.
