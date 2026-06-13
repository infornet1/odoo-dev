# Leave Notification System — Features #76, #77, #78

## Overview

**Scripts:** `scripts/leave_notification.py` + `scripts/hr_leave_attendance_digest.py`
**Crons:** `/etc/cron.d/leave_notification` (every 15 min weekdays) + `/etc/cron.d/hr_leave_attendance_digest` (08:00 VET weekdays)

---

## leave_notification.py (Feature #76)

Polls `hr.leave` for actionable states every 15 min:
- `confirm` → "📋 Nueva Solicitud de Permiso" email to `recursoshumanos@ueipab.edu.ve` (blue header)
- `validate1` → "🔔 Segunda Validación Requerida" email to `recursoshumanos@ueipab.edu.ve` (orange header)
- State file `scripts/leave_notification_state.json` tracks `notified_confirm_{id}` / `notified_validate1_{id}` separately — a confirm→validate1 transition fires a second email
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
