# Payslip Acknowledgment System

## Overview

Complete system for tracking employee acknowledgment of payslip receipt, including dashboard widget, monitoring, and reminder functionality.

---

## HRMS Dashboard Acknowledgment Widget

**Status:** Production | **Module:** `ueipab_hrms_dashboard_ack` | **Version:** 17.0.1.0.0 | **Deployed:** 2025-12-21

**Purpose:** Adds payslip acknowledgment tracking widget to the HRMS Dashboard.

### Architecture
- Extends `hrms_dashboard` using Odoo's `patch()` mechanism (upgrade-safe)
- Backend: `hr.employee.get_payslip_acknowledgment_stats()` method
- Frontend: OWL component patch with DOM manipulation (not template inheritance)

### Widget Location
- EmployeeDashboard section, after Announcements widget
- Reduces Announcements column from `col-lg-4` to `col-lg-2`
- Adds Ack widget as new `col-lg-2` column
- Maintains 12-column grid layout on large screens

### Widget Features

| Feature | Description |
|---------|-------------|
| Done count | Number of acknowledged payslips (clickable) |
| Pending count | Number of pending acknowledgments (clickable) |
| Progress bar | Visual percentage complete |
| Recent payslips | Last 3 payslips with status icons |

**Click Actions:**
- Click "Done" box -> Opens list of acknowledged payslips
- Click "Pending" box -> Opens list of pending payslips

### Files
```
addons/ueipab_hrms_dashboard_ack/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── hr_employee.py             # get_payslip_acknowledgment_stats()
├── static/src/
│   ├── js/payslip_ack_widget.js   # OWL patch with DOM manipulation
│   ├── xml/payslip_ack_templates.xml  # Empty (templates via JS)
│   └── css/payslip_ack.css        # Compact widget styling
└── security/ir.model.access.csv
```

### Installation
1. Go to Apps -> Update Apps List
2. Search "UEIPAB HRMS Dashboard"
3. Install the module
4. Refresh browser (Ctrl+Shift+R)

**Dependencies:** `hrms_dashboard`, `ueipab_payroll_enhancements`

### Access Control
- Widget only visible to users with payroll roles
- Required groups: `hr_payroll_community.group_hr_payroll_community_manager` OR `hr_payroll_community.group_hr_payroll_community_user`
- Regular employees without payroll access will NOT see the widget

### Technical Notes
- Does NOT use OWL template inheritance (t-inherit not supported for OWL components)
- Uses DOM manipulation via `insertAdjacentHTML()` after component mounts
- Widget renders in two modes:
  - **Manager view (Ack Overview):** For HR managers (`is_manager=true`) - ALWAYS shows batch overview stats
    - Includes "My Status: X/Y" personal summary line if manager has payslips
    - Click "Done" → All acknowledged payslips (all employees)
    - Click "Pending" → All pending payslips (all employees)
    - Click "My Status" → Manager's own pending payslips
  - **Personal view (Payslip Ack):** For regular employees with payslips (`stats.personal.total > 0`)
    - Shows only the employee's own acknowledgment stats
    - Click "Done" → Employee's acknowledged payslips
    - Click "Pending" → Employee's pending payslips

**Enhanced Widget Logic (2025-12-21):**
- Managers ALWAYS see Overview, even if they have personal payslips
- Personal summary line added for managers who are also employees
- Regular employees only see their personal stats

---

## Payslip Acknowledgment Monitoring

**Status:** Production (since 2025-11-28)

**First Real Batch:** NOVIEMBRE30 (44 employees, sent 2025-11-28)

### Monitoring Query
```python
# Check acknowledgment status for a batch
batch = env['hr.payslip.run'].search([('name', 'ilike', 'BATCH_NAME')])
acknowledged = batch.slip_ids.filtered(lambda s: s.is_acknowledged)
pending = batch.slip_ids.filtered(lambda s: not s.is_acknowledged)
print(f"Acknowledged: {len(acknowledged)} / {len(batch.slip_ids)}")
```

### Payslip Acknowledgment Fields
- `is_acknowledged` (Boolean) - True when employee confirms
- `acknowledged_date` (Datetime) - When confirmation was made
- `acknowledged_ip` (Char) - IP address of confirmation
- `acknowledged_user_agent` (Char) - Browser info

**Portal Route:** `/payslip/acknowledge/<payslip_id>/<token>`

---

## Payslip Acknowledgment Confirmation Email

**Status:** PRODUCTION | **Deployed:** 2026-02-28 | **Module Version:** v1.53.0

**Problem Solved:** After an employee acknowledges their payslip via the portal, there was no email confirmation sent. Employee had no proof of acknowledgment, and HR only knew via dashboard.

**Solution Implemented:** Automatic confirmation email sent immediately after successful acknowledgment.

### Email Template

- Template: `email_template_payslip_ack_confirmation`
- Template ID: Testing=67, Production=46
- Subject: `{{object.number}} ha sido confirmado exitosamente`
- From: `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>`
- To: Employee work email
- CC: `recursoshumanos@ueipab.edu.ve`
- Body: Green-themed confirmation with payslip details and acknowledgment timestamp

### Trigger Point

Sent automatically from `controllers/payslip_acknowledgment.py` in the `payslip_acknowledge_confirm()` method, right after:
1. `payslip.write()` sets `is_acknowledged=True` with audit trail
2. `payslip.message_post()` adds chatter note

Wrapped in try/except so email failures never block the acknowledgment success page.

### Files Created

| File | Description |
|------|-------------|
| `data/email_template_ack_confirmation.xml` | Confirmation email template (noupdate=1) |

### Files Modified

| File | Changes |
|------|---------|
| `controllers/payslip_acknowledgment.py` | Added send_mail() call after acknowledgment |
| `__manifest__.py` | Version 1.53.0, added XML file |

---

## Payslip Acknowledgment Reminder System

**Status:** PRODUCTION | **Deployed:** 2025-12-19 | **Module Version:** v1.49.1

**Problem Solved:** Employees who receive payslip emails may forget to click the acknowledgment button.

**Solution Implemented:** Wizard-based reminder system with employee selection and result tracking.

### Phase 1: Manual Reminder Wizard (Implemented)

**Access:** Payslip Batch Form -> "Send Ack Reminders" button (fa-bell icon)

**UI Update (2025-12-17):** Email-related buttons are now grouped in a compact `btn-group` with icon-only buttons and tooltips:
- Send Payslips by Email (fa-envelope)
- Send Emails with Progress (fa-paper-plane)
- Send Ack Reminders (fa-bell)

**Note:** A true dropdown menu would require custom JavaScript/OWL component due to Odoo's validation requiring all `<button>` elements to have a `name` attribute.

### Wizard Features

| Feature | Description |
|---------|-------------|
| Preview Stats | Shows Total, Confirmed, Pending badges |
| Employee Table | List of pending employees with select/deselect toggles |
| Email Status | Shows work email for each employee |
| Reminder Count | Tracks how many reminders sent per payslip |
| Select All/Deselect All | Bulk selection buttons |
| Results Summary | Shows Sent/No Email/Failed counts after sending |

### Wizard States
1. **Preview** - Shows pending employees, allows selection
2. **Sending** - Processing reminders (transitional)
3. **Done** - Shows results with color-coded status per employee

### Email Template
- Template: `email_template_payslip_ack_reminder`
- Subject: `Recordatorio: Confirmar recepcion de comprobante - {{object.number}}`
- Body: Orange-themed reminder with payslip details and acknowledgment button
- Shows reminder count (e.g., "Este es el recordatorio #2")

### Tracking Fields (hr.payslip)
- `ack_reminder_count` - Number of reminders sent for this payslip
- `ack_reminder_last_date` - Datetime of last reminder sent

### Files Created

| File | Description |
|------|-------------|
| `wizard/ack_reminder_wizard.py` | TransientModels for wizard and line items |
| `wizard/ack_reminder_wizard_view.xml` | Wizard form with notebook tabs |
| `data/email_template_ack_reminder.xml` | Reminder email template |

### Files Modified

| File | Changes |
|------|---------|
| `models/hr_payslip.py` | Added tracking fields |
| `views/hr_payslip_run_view.xml` | Added wizard button |
| `security/ir.model.access.csv` | Added wizard access rules |
| `__manifest__.py` | Version 1.48.0, added XML files |

### Phase 2: Automatic Cron Job (Planned)

**Status:** PLANNED | **Priority:** Low

**Planned Features:**
- Daily cron job at 9:00 AM
- Auto-send reminders after X days of no acknowledgment
- Configuration options: `reminder_days`, `max_reminders`, `reminder_interval`

**Files to Create:**
- `data/ir_cron_ack_reminder.xml` - Cron job definition
