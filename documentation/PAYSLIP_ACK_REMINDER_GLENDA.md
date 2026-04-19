# Payslip Ack Reminder via Glenda (WhatsApp)

**Status:** Testing (v1.31.0)
**Created:** 2026-04-19
**Module:** `ueipab_ai_agent`
**Skill Code:** `payslip_ack_reminder`

---

## Overview

Extends the "Recolección de Datos" wizard with a second tab — **Conformidades Pendientes** — that lets HR contact employees via Glenda (WhatsApp) to remind them to confirm their payslip acknowledgment via the portal.

This complements the existing email-based ack reminder wizard (`ack_reminder_wizard`). WhatsApp reminders are more effective for employees who haven't opened the email.

---

## UI Flow

1. HR opens a payslip batch → clicks **"Recolección de Datos"**
2. Wizard opens with two tabs:
   - **Tab 1: Recolección de Datos HR** — existing HR data collection
   - **Tab 2: Conformidades Pendientes** — NEW: employees with unacknowledged payslips
3. Tab 2 shows employees whose payslip is in `done` state but `is_acknowledged=False`
4. HR selects employees → clicks **"Enviar Recordatorios via Glenda"**
5. Draft `ai.agent.conversation` records are created per employee
6. Stagger CRON starts conversations within 30 min (respects anti-spam and capacity limits)
7. Glenda sends WhatsApp with the payslip portal link
8. Employee clicks link → confirms → `is_acknowledged=True`
9. Auto-resolve CRON (every 30 min) detects acknowledgment and closes conversation

---

## Skill: `payslip_ack_reminder`

| Property | Value |
|---|---|
| Code | `payslip_ack_reminder` |
| Source Model | `hr.payslip` |
| Max Turns | 4 |
| Timeout | 48 hours |
| Reminder Interval | 24 hours |
| Max Reminders | 1 |
| Respects Schedule | Yes (VET contact window) |

### Conversation Flow

```
Glenda (greeting)
  ├── Employee name
  ├── Payslip number + period + net VEB amount
  └── Acknowledgment URL (portal link)

Employee replies (optional)
  └── If problem with link → Glenda redirects to recursoshumanos@ueipab.edu.ve

[No reply] → 24h later: one reminder message with URL
[Still no reply] → 48h later: conversation times out

[Employee acknowledges via portal] → cron auto-resolves conversation
```

### Message Template (greeting)

```
Buenos días, [NOMBRE]. Te saluda Glenda de Recursos Humanos de UEIPAB.

Tu [comprobante de pago / adelanto de prestaciones sociales] *[NÚMERO]*
correspondiente al período [DD/MM/YYYY] - [DD/MM/YYYY] por *[MONTO] Bs.*
está pendiente de conformidad digital.

Por favor ingresa al siguiente enlace para confirmar:
https://[domain]/payslip/acknowledge/[id]/[token]?db=DB_UEIPAB

Si tienes alguna dificultad con el enlace, responde a este mensaje y te ayudamos.
```

For `LIQUID_VE_V2` payslips, "comprobante de pago" is replaced with "adelanto de prestaciones sociales".

---

## Auto-Resolve Mechanism

Two new CRON jobs:

| CRON | Method | Interval | Purpose |
|---|---|---|---|
| Stagger Ack Reminders | `_cron_start_ack_reminders()` | 30 min | Start draft conversations respecting capacity |
| Auto-Resolve Ack Reminders | `_cron_check_ack_acknowledged()` | 30 min | Resolve conversations when `is_acknowledged=True` |

The auto-resolve CRON checks all active/waiting `payslip_ack_reminder` conversations, reads the linked `hr.payslip.is_acknowledged` flag, and calls `action_resolve()` if True.

---

## Duplicate Guard

Before creating a conversation in the wizard, the code checks for an existing active/waiting/draft conversation for the same payslip. Employees with an active reminder show as **muted** in the list and are deselected by default.

---

## Wizard Changes

### New Model: `hr.data.collection.create.ack.line`

| Field | Type | Purpose |
|---|---|---|
| `wizard_id` | Many2one | Parent wizard |
| `employee_id` | Many2one | Employee |
| `payslip_id` | Many2one | Payslip |
| `payslip_number` | Char | Payslip number display |
| `selected` | Boolean | HR selects/deselects |
| `has_phone` | Boolean | Employee has mobile_phone |
| `has_existing_reminder` | Boolean | Active conversation already exists |
| `existing_reminder_state` | Selection | draft/active/waiting |

### New Fields on Wizard

| Field | Purpose |
|---|---|
| `ack_line_ids` | One2many to ack lines |
| `ack_total_count` | Computed count |
| `ack_selected_count` | Computed selected count |
| `ack_created_count` | Created on submit |
| `done_mode` | hr / ack — controls done screen display |

### New Wizard Methods

| Method | Purpose |
|---|---|
| `_prepare_ack_lines(run)` | Build Tab 2 lines from batch payslips |
| `action_select_all_ack()` | Select all with phone and no active reminder |
| `action_deselect_all_ack()` | Deselect all |
| `action_create_ack_reminders()` | Create draft conversations |
| `action_view_ack_conversations()` | Open conversation tree filtered by batch |

---

## Related Files

| File | Purpose |
|---|---|
| `addons/ueipab_ai_agent/skills/payslip_ack_reminder.py` | Skill class |
| `addons/ueipab_ai_agent/wizard/create_collection_wizard.py` | Wizard with Tab 2 |
| `addons/ueipab_ai_agent/wizard/create_collection_wizard_view.xml` | Wizard view with notebook |
| `addons/ueipab_ai_agent/data/skills_data.xml` | Skill record |
| `addons/ueipab_ai_agent/data/cron.xml` | Two new CRONs |
| `addons/ueipab_ai_agent/models/ai_agent_conversation.py` | New cron methods |
| `addons/ueipab_payroll_enhancements/models/hr_payslip.py` | `is_acknowledged` + `_get_acknowledgment_url()` |

---

## Relation to Existing Ack Reminder Wizard

| Feature | Email Reminder (existing) | Glenda WA Reminder (new) |
|---|---|---|
| Channel | Email | WhatsApp |
| Wizard | `ack_reminder_wizard` on batch | Tab 2 in "Recolección de Datos" |
| Trigger | HR manual | HR manual |
| Tracking | `ack_reminder_count` on payslip | `ai.agent.conversation` records |
| Auto-close | N/A | Yes — cron checks `is_acknowledged` |

Both can be used independently or together.

---

## Changelog

| Date | Version | Change |
|---|---|---|
| 2026-04-19 | 1.31.0 | Initial implementation — skill, wizard Tab 2, 2 CRONs |
