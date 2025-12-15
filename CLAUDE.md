# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-12-15 21:10 UTC

## Core Instructions

**CRITICAL RULES:**
- **ALWAYS work locally, NEVER in production environment**
- **NEVER TOUCH DB_UEIPAB without proper authorization**
- Development database: `testing`
- Production database: `DB_UEIPAB` (requires authorization)

---

## Active Features Summary

| # | Feature | Status | Module | Documentation |
|---|---------|--------|--------|---------------|
| 1 | Payroll Disbursement Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYROLL_DISBURSEMENT_REPORT.md) |
| 2 | Venezuelan Liquidation V1/V2 | Production | `ueipab_payroll_enhancements` | [V2 Impl](documentation/LIQUIDATION_V2_IMPLEMENTATION.md) |
| 3 | Prestaciones Interest Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PRESTACIONES_INTEREST_REPORT.md) |
| 4 | Venezuelan Payroll V2 | Production | `ueipab_payroll_enhancements` | [V2 Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) |
| 5 | Relacion Liquidacion Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/RELACION_BREAKDOWN_REPORT.md) |
| 18 | Liquidacion Estimation Mode | Testing | `ueipab_payroll_enhancements` | See below |
| 6 | Payslip Email Delivery | Production | `hr_payslip_monthly_report` | [Docs](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md) |
| 7 | Batch Email Template Selector | Production | `ueipab_payroll_enhancements` | - |
| 8 | Comprobante de Pago Compacto | Production | `ueipab_payroll_enhancements` | - |
| 9 | Acuerdo Finiquito Laboral | Production | `ueipab_payroll_enhancements` | [Docs](documentation/FINIQUITO_REPORT.md) |
| 10 | AR-I Portal | Testing | `ueipab_ari_portal` | - |
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | - |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](documentation/RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | See below |
| 15 | Batch Email Progress Wizard | Testing | `ueipab_payroll_enhancements` | See below |
| 16 | HRMS Dashboard Ack Widget | Testing | `ueipab_hrms_dashboard_ack` | See below |
| 17 | Cybrosys Module Refactoring | Planned | Multiple | See below |
| 19 | Payslip Ack Reminder System | Planned | `ueipab_payroll_enhancements` | See below |
| 20 | V2 Payroll Accounting Config | Production | Database config | See below |

---

## HRMS Dashboard Acknowledgment Widget

**Status:** Testing | **Module:** `ueipab_hrms_dashboard_ack` | **Version:** 17.0.1.0.0

**Purpose:** Adds payslip acknowledgment tracking widget to the HRMS Dashboard.

**Architecture:**
- Extends `hrms_dashboard` using Odoo's `patch()` mechanism (upgrade-safe)
- Backend: `hr.employee.get_payslip_acknowledgment_stats()` method
- Frontend: OWL component patch with DOM manipulation (not template inheritance)

**Widget Location:** EmployeeDashboard section, after Announcements widget
- Reduces Announcements column from `col-lg-4` to `col-lg-2`
- Adds Ack widget as new `col-lg-2` column
- Maintains 12-column grid layout on large screens

**Widget Features:**

| Feature | Description |
|---------|-------------|
| Done count | Number of acknowledged payslips (clickable) |
| Pending count | Number of pending acknowledgments (clickable) |
| Progress bar | Visual percentage complete |
| Recent payslips | Last 3 payslips with status icons |

**Click Actions:**
- Click "Done" box → Opens list of acknowledged payslips
- Click "Pending" box → Opens list of pending payslips

**Files:**
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

**Installation:**
1. Go to Apps → Update Apps List
2. Search "UEIPAB HRMS Dashboard"
3. Install the module
4. Refresh browser (Ctrl+Shift+R)

**Dependencies:** `hrms_dashboard`, `ueipab_payroll_enhancements`

**Access Control:**
- Widget only visible to users with payroll roles
- Required groups: `hr_payroll_community.group_hr_payroll_community_manager` OR `hr_payroll_community.group_hr_payroll_community_user`
- Regular employees without payroll access will NOT see the widget

**Technical Notes:**
- Does NOT use OWL template inheritance (t-inherit not supported for OWL components)
- Uses DOM manipulation via `insertAdjacentHTML()` after component mounts
- Widget renders in two modes:
  - **Personal view:** For employees with payslips (`stats.personal.total > 0`)
  - **Manager view:** For HR managers (`hr.group_hr_manager`) with batch overview stats

---

## Payslip Acknowledgment Monitoring

**Feature Status:** Production (since 2025-11-28)

**First Real Batch:** NOVIEMBRE30 (44 employees, sent 2025-11-28)

**Monitoring Query:**
```python
# Check acknowledgment status for a batch
batch = env['hr.payslip.run'].search([('name', 'ilike', 'BATCH_NAME')])
acknowledged = batch.slip_ids.filtered(lambda s: s.is_acknowledged)
pending = batch.slip_ids.filtered(lambda s: not s.is_acknowledged)
print(f"Acknowledged: {len(acknowledged)} / {len(batch.slip_ids)}")
```

**Payslip Acknowledgment Fields:**
- `is_acknowledged` (Boolean) - True when employee confirms
- `acknowledged_date` (Datetime) - When confirmation was made
- `acknowledged_ip` (Char) - IP address of confirmation
- `acknowledged_user_agent` (Char) - Browser info

**Portal Route:** `/payslip/acknowledge/<payslip_id>/<token>`

---

## Planned: Payslip Acknowledgment Reminder System

**Status:** 📋 PLANNED | **Priority:** Medium | **Module:** `ueipab_payroll_enhancements`

**Problem:** Employees who receive payslip emails may forget to click the acknowledgment button. Currently there's no way to:
- Send reminder emails to employees who haven't acknowledged
- Automatically remind after X days
- Track reminder history

**Proposed Solution - Two Components:**

### 1. Manual Reminder Button (Batch Form)

**Button:** "Send Reminder to Pending" on batch form header

**Logic:**
```python
def action_send_reminder_to_pending(self):
    """Send reminder email to employees who haven't acknowledged."""
    pending = self.slip_ids.filtered(
        lambda s: not s.is_acknowledged
        and s.state in ['done', 'paid']
        and s.employee_id.work_email
    )
    template = self.env.ref('ueipab_payroll_enhancements.email_template_payslip_ack_reminder')
    for payslip in pending:
        template.send_mail(payslip.id)

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'message': f'Reminder sent to {len(pending)} employees',
            'type': 'success',
        }
    }
```

### 2. Automatic Cron Job (Daily Reminder)

**Cron:** Run daily at 9:00 AM

**Logic:**
```python
def _cron_payslip_ack_reminder(self):
    """Send reminder to employees who haven't acknowledged after 3 days."""
    threshold = fields.Date.today() - timedelta(days=3)

    pending = self.env['hr.payslip'].search([
        ('is_acknowledged', '=', False),
        ('state', 'in', ['done', 'paid']),
        ('create_date', '<=', threshold),
        # Optionally: limit to recent batches only
    ])

    template = self.env.ref('ueipab_payroll_enhancements.email_template_payslip_ack_reminder')
    for payslip in pending:
        if payslip.employee_id.work_email:
            template.send_mail(payslip.id)
```

**Configuration Options (Future):**
- `reminder_days` - Days before first reminder (default: 3)
- `max_reminders` - Maximum reminders per payslip (default: 2)
- `reminder_interval` - Days between reminders (default: 3)

### Email Template (To Create)

**Template ID:** `email_template_payslip_ack_reminder`

**Subject:** `⏰ Recordatorio: Confirmar recepción de comprobante de pago`

**Body:** Friendly reminder with:
- Original payslip reference
- Link to acknowledge
- Note that this is a reminder

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `models/hr_payslip_run.py` | Modify | Add `action_send_reminder_to_pending()` |
| `views/hr_payslip_run_view.xml` | Modify | Add reminder button |
| `data/email_template_ack_reminder.xml` | Create | Reminder email template |
| `data/ir_cron_ack_reminder.xml` | Create | Cron job definition |
| `models/hr_payslip.py` | Modify | Add `reminder_count`, `last_reminder_date` fields |

---

## Batch Email Progress Wizard

**Status:** ✅ TESTING | **Deployed:** 2025-11-29 | **Module Version:** v1.45.0

**Problem Solved:** When clicking "Send Payslips by Email" on batch form:
- No progress indicator during sending
- No feedback on success/failure per employee
- No error reporting if emails fail
- User doesn't know when process completes

**Solution Implemented:** Progress wizard with real-time feedback

**New Button:** "Send Emails (with Progress)" on batch form (alongside existing button)

**Wizard Features:**
- Progress bar showing percentage complete
- Real-time stats: ✅ Sent, 📭 No Email, ❌ Failed
- Results table with status icons per employee
- "Failed Only" tab for quick error review
- Color-coded rows (green=sent, orange=no email, red=error)
- Error messages captured for each failure

**User Flow:**
```
1. Open Payslip Batch form
2. Click "Send Emails (with Progress)" button
3. Select email template (defaults to batch template)
4. Click "Start Sending"
5. Click "Process All Remaining" to send all at once
6. Review results in summary table
7. Check "Failed Only" tab if issues occurred
```

**Files Created:**
- `wizard/batch_email_wizard.py` - Two TransientModels:
  - `hr.payslip.batch.email.wizard` - Main wizard
  - `hr.payslip.batch.email.result` - Per-payslip result tracking
- `wizard/batch_email_wizard_view.xml` - Wizard form view with tabs

**Files Modified:**
- `wizard/__init__.py` - Added import
- `views/hr_payslip_run_view.xml` - Added button (action ID 850)
- `security/ir.model.access.csv` - Added access rules
- `__manifest__.py` - Updated version, added XML file

**Testing Notes:**
- All tests used `env.cr.rollback()` - no actual emails sent
- Tested: wizard creation, progress tracking, no-email detection, error capture
- Ready for manual testing in browser

---

## Planned: Duplicate Payslip Warning Enhancement

**Status:** 📋 PLANNED | **Priority:** Medium

**Problem:** Users can accidentally create duplicate payslips for the same employee/period when clicking "Generate Payslips" multiple times.

**Proposed Solution:** Warning wizard before generating payslips

**Duplicate Detection Criteria:**
- Same employee (`employee_id`)
- Overlapping date range (`date_from` ≤ batch.date_end AND `date_to` ≥ batch.date_start)
- Not cancelled (`state != 'cancel'`)

**User Flow:**
```
User clicks "Generate Payslips" → System checks for duplicates → If found:
┌─────────────────────────────────────────────────────┐
│  ⚠️ Duplicate Payslips Warning                      │
│                                                     │
│  The following employees already have payslips      │
│  for this period (Nov 16-30, 2025):                 │
│                                                     │
│  • JUAN PEREZ - SLIP/1001 (Draft)                  │
│  • MARIA LOPEZ - SLIP/1002 (Confirmed)             │
│                                                     │
│  [Skip Duplicates]  [Create All]  [Cancel]          │
└─────────────────────────────────────────────────────┘
```

**Button Actions:**
- **Skip Duplicates:** Only create for employees WITHOUT existing payslips
- **Create All:** Create all payslips (for intentional duplicates/corrections)
- **Cancel:** Abort operation

**Implementation:**
1. Create TransientModel: `hr.payslip.duplicate.warning`
2. Modify `hr.payslip.employees.action_compute_sheet()` to check duplicates
3. If duplicates found, open warning wizard instead of creating
4. Warning wizard buttons call back with `skip_duplicates` or `force_create` flag

**Files to Modify:**
- `models/hr_payslip_employees.py` - Add duplicate check logic
- `wizard/payslip_duplicate_warning.py` - New warning wizard (create)
- `wizard/payslip_duplicate_warning_view.xml` - Wizard form view (create)
- `security/ir.model.access.csv` - Add wizard access

---

## Cybrosys Module Modification Report

**Status:** 📋 PLANNED REFACTORING | **Priority:** Medium | **Date:** 2025-11-30

### Overview

Analysis of all Cybrosys OHRMS modules to identify direct modifications that pose upgrade risk.

| Category | Count | Risk Level |
|----------|-------|------------|
| Heavily Modified | 2 | HIGH |
| Minor Modification | 2 | MEDIUM |
| Unmodified | 13 | SAFE |

### HIGH RISK - Heavily Modified Modules

#### 1. `hr_payroll_community` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_payslip.py` | ~25 lines | Exchange rate: removed hardcoded `227.5567`, dynamic BCV lookup |
| `models/hr_payslip_line.py` | ~15 lines | Odoo 17 syntax: `dp.get_precision()` → `'Payroll'` |
| `models/hr_payslip_run.py` | ~50 lines | Auto-populate rate from `res.currency.rate`, simplified button logic |
| `models/hr_salary_rule.py` | ~4 lines | Digit precision syntax update |
| `views/hr_payslip_run_views.xml` | ~30 lines | Odoo 17: `attrs={}` → `invisible=` |
| `security/ir.model.access.csv` | ~2 lines | Added wizard access |

#### 2. `hr_payroll_account_community` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_payslip.py` | ~60 lines | Cancel policy (no delete), partner fix, unlink override |
| `models/hr_payslip_line.py` | ~40 lines | Partner uses `work_contact_id` (employee) not `address_id` (company) |

**Critical Changes:**
- `action_payslip_cancel()` - No longer deletes journal entries (audit trail policy)
- `unlink()` override - Cancels (not deletes) journal entries
- Partner assignment uses employee's individual partner for accounting accuracy

### MEDIUM RISK - Minor Modifications

#### 3. `hrms_dashboard` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_employee.py` | 3 lines | Bug fix: `attendance_manual()` search by `user_id` |

#### 4. `hr_payslip_monthly_report` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `wizard/payslip_compact_wizard.py` | 2 lines | Fixed `report_action(docids=)` parameter |

### SAFE - Unmodified Modules (13 total)

All installed from `ohrms_core-17.0.1.0.0.zip` with NO modifications:

`ohrms_core`, `ohrms_loan`, `ohrms_loan_accounting`, `ohrms_salary_advance`,
`hr_employee_transfer`, `hr_employee_updation`, `hr_leave_request_aliasing`,
`hr_multi_company`, `hr_reminder`, `hr_resignation`, `hr_reward_warning`,
`oh_employee_creation_from_user`, `oh_employee_documents_expiry`

### Planned Refactoring (Option B)

Create extension modules to make Cybrosys modules upgrade-safe:

```
# NEW MODULES TO CREATE:

addons/ueipab_hr_payroll_fixes/
├── __manifest__.py              # depends: ['hr_payroll_community']
├── __init__.py
├── models/__init__.py
├── models/hr_payslip.py         # Exchange rate dynamic lookup
└── models/hr_payslip_run.py     # Auto-populate rate, button logic

addons/ueipab_hr_payroll_account_fixes/
├── __manifest__.py              # depends: ['hr_payroll_account_community']
├── __init__.py
├── models/__init__.py
├── models/hr_payslip.py         # Cancel policy, unlink override
└── models/hr_payslip_line.py    # Partner assignment fix

addons/ueipab_hrms_dashboard_fix/
├── __manifest__.py              # depends: ['hrms_dashboard']
├── __init__.py
├── models/__init__.py
└── models/hr_employee.py        # attendance_manual() fix
```

**After Refactoring:**
1. Restore original Cybrosys modules (unmodified)
2. Install extension modules on top
3. Cybrosys updates won't overwrite customizations
4. Extension modules load AFTER originals via `depends`

---

## Liquidacion Estimation Mode

**Status:** Testing | **Module:** `ueipab_payroll_enhancements` | **Version:** 17.0.1.46.0

**Purpose:** Generate projection/estimation reports for liquidation with optional global % reduction.

**Feature Overview:**
- Adds "Modo Estimación" option to Relación de Liquidación wizard
- Only available when VEB (local currency) is selected
- Applies configurable global reduction % to all calculated amounts
- Generates projection report without signature sections

**Wizard Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `is_estimation` | Boolean | Enable estimation mode |
| `reduction_percentage` | Float | Global reduction % (0-100) |
| `is_veb_currency` | Computed | Technical field for view visibility |

**PDF Output (Estimation Mode):**
- Title: "ESTIMACIÓN DE LIQUIDACIÓN" (red)
- Subtitle: "PROYECCIÓN - NO VÁLIDO COMO DOCUMENTO OFICIAL"
- Watermark: "ESTIMACIÓN" (diagonal, semi-transparent)
- Declaration section: Hidden
- Signature sections: Hidden
- Disclaimer box: Yellow warning about projection nature

**Calculation:**
```python
# All amounts multiplied by reduction factor
reduction_multiplier = (100 - reduction_percentage) / 100.0
# Example: 48% reduction → amounts show 52% of calculated value
```

**Files Modified:**
- `models/liquidacion_breakdown_wizard.py` - Added estimation fields and computed field
- `models/liquidacion_breakdown_report.py` - Apply reduction to all amounts
- `reports/liquidacion_breakdown_report.xml` - Conditional template sections
- `wizard/liquidacion_breakdown_wizard_view.xml` - Estimation mode UI section

**User Flow:**
1. Open Relación de Liquidación wizard
2. Select liquidation payslip(s)
3. Select **VEB** currency (estimation only available for VEB)
4. Enable "Modo Estimación" toggle
5. Enter reduction percentage (e.g., 48 for 48%)
6. Click "Generar Estimación PDF"

---

### Upgrade Procedure (Current State)

Until refactoring is complete, use this procedure when Cybrosys releases updates:

```bash
# 1. Backup current modules
cp -r addons/hr_payroll_community addons/hr_payroll_community.backup
cp -r addons/hr_payroll_account_community addons/hr_payroll_account_community.backup

# 2. Create diff of changes
git diff adca35a..HEAD -- addons/hr_payroll_community/ > /tmp/payroll_changes.patch
git diff adca35a..HEAD -- addons/hr_payroll_account_community/ > /tmp/payroll_account_changes.patch

# 3. After installing new version, manually review and apply changes
```

---

## Venezuelan Liquidation System (V1 vs V2)

| Aspect | V1 (Legacy) | V2 (Current) |
|--------|-------------|--------------|
| Structure Code | LIQUID_VE | LIQUID_VE_V2 |
| Salary Field | `ueipab_deduction_base` | `ueipab_salary_v2` |
| Accounting | 5.1.01.10.002 | 5.1.01.10.010 |

**V2 Contract Fields:**
```python
contract.ueipab_salary_v2              # Direct salary subject to deductions
contract.ueipab_extrabonus_v2          # NOT subject to deductions
contract.ueipab_bonus_v2               # NOT subject to deductions
contract.ueipab_original_hire_date     # Original hire date (antiguedad)
contract.ueipab_previous_liquidation_date  # Last full liquidation
contract.ueipab_vacation_prepaid_amount    # Total prepaid vacation/bono
contract.ueipab_other_deductions       # Fixed USD for loans/advances
```

---

## Venezuelan Payroll V2 Deductions

| Deduction | Rate | Applies To |
|-----------|------|------------|
| SSO (IVSS) | 4% | Salary, Vacaciones, Bono Vac., Utilidades |
| FAOV | 1% | Salary, Vacaciones, Bono Vac., Utilidades |
| INCES (PARO) | 0.5% | **Utilidades ONLY** |
| ARI | Variable % | From contract field |
| Otras Deducciones | Fixed USD | From contract field |
| INCES (Payroll) | 0.25% | **DISABLED** - pending legal |

---

## V2 Payroll Accounting Configuration

**Status:** Testing ✅ | Production ✅ | **Updated:** 2025-12-15

**Fixed:** Production V2 payroll accounting configured on 2025-12-13, updated 2025-12-15. V2 payslips now create journal entries correctly.

### Account Mapping

| Purpose | Debit Account | Credit Account |
|---------|---------------|----------------|
| V2 Payroll (deductions + NET) | 5.1.01.10.001 (Nómina) | 1.1.01.02.001 (Banco Venezuela) |
| V2 Liquidation | 5.1.01.10.010 (Prestaciones) | 2.1.01.10.005 (Provisión Prestaciones) |

### Rules Configuration Status

| Rule Code | Testing | Production | Description |
|-----------|---------|------------|-------------|
| VE_SSO_DED_V2 | ✅ Configured | ✅ Configured | SSO 4% |
| VE_PARO_DED_V2 | ✅ Configured | ✅ Configured | PARO 0.5% |
| VE_FAOV_DED_V2 | ✅ Configured | ✅ Configured | FAOV 1% |
| VE_ARI_DED_V2 | ✅ Configured | ✅ Configured | ARI Variable % |
| VE_OTHER_DED_V2 | ✅ Configured | ✅ Configured | Otras Deducciones |
| VE_NET_V2 | ✅ Configured | ✅ Configured | Net Salary |
| VE_SALARY_V2, etc. | NOT SET | NOT SET | Earnings (no accounting needed) |
| VE_TOTAL_DED_V2 | NOT SET | NOT SET | Summary (no accounting needed) |

**Design Pattern:** Only deductions and NET create journal entries. Earnings rules do NOT post to accounting.

### Configuration Change Log

**2025-12-15 - Credit Account Update:**
- Changed credit account from `2.1.01.01.002` (Ctas por pagar nómina) to `1.1.01.02.001` (Banco Venezuela)
- Applied to both Testing and Production environments

**2025-12-13 - Initial Configuration:**
- Created account `2.1.01.01.002` in Production (ID: 1123)
- Configured all 6 V2 deduction/NET rules

**Container Note:** Production uses container `0ef7d03db702_ueipab17` (not `ueipab17`)

---

## Report Exchange Rate System

**3-Priority System for VEB Reports:**
1. Custom rate (wizard) → "Tasa personalizada"
2. Rate date lookup (wizard) → "Tasa del DD/MM/YYYY"
3. Latest available / Payslip rate → "Tasa automática"

**Disbursement Report Priority (2025-11-27):**
1. Batch `exchange_rate` field → "Batch (BATCH_NAME)"
2. Payslip `exchange_rate_used` → "Payslip (exchange_rate_used)"
3. Date-based currency lookup → "Date lookup (YYYY-MM-DD)"

**Interest Calculation:** Always uses accrual method (ignores override)

---

## Payslip Batch Features

**Date Sync to Payslips (2025-11-27):**
- Button: "Sync Dates to Payslips" on batch form
- Updates `date_from`/`date_to` on all **draft** payslips
- **Automatically recomputes** all updated payslips
- Skips non-draft payslips with warning
- Use case: Batch date range changed after payslips created

**Total Net Payable (2025-11-27):**
- Shows sum of NET amounts for all payslips in batch
- **Includes draft payslips** (critical for pre-validation)
- Supports both V1 (`VE_NET`) and V2 (`VE_NET_V2`) structures
- Only excludes cancelled payslips

**Exchange Rate Application:**
- Button: "Apply Rate to Payslips" on batch form
- Updates `exchange_rate_used` on all payslips in batch
- Works on any state (draft, done, paid, cancel)

**Batch Email Sending (2025-11-28):**
- Button: "Send Payslips by Email" on batch form
- Field: `email_template_id` - Select email template before sending
- Uses notification popup instead of chatter (model doesn't inherit mail.thread)
- Default template: **Payslip Email - Employee Delivery** (updated 2025-11-28)

**Generate Payslips Button Visibility (Updated 2025-11-28):**
- Requires `batch_exchange_rate > 0` (simplified - no confirmation step required)
- Exchange rate auto-populates from latest BCV rate in `res.currency.rate`
- Fallback: Uses most recent confirmed batch rate if no BCV rate available

**Exchange Rate Auto-Population (2025-11-28):**
- New batches automatically get latest BCV rate from `res.currency.rate`
- Lookup order: VEB/VES/VEF currency → latest `company_rate`
- Fallback: Most recent confirmed batch rate
- Also triggers on `date_start`/`date_end` change if rate is still 0

---

## Email Templates (Batch Sending)

| Template | Use Case |
|----------|----------|
| Payslip Compact Report | Regular payroll |
| Payslip Email - Employee Delivery | Monthly detailed view with acknowledgment **(DEFAULT)** |
| Aguinaldos Email | December Christmas bonuses |

**Syntax Rules:**
- Headers (subject): Jinja2 `{{object.field}}`
- Body (body_html): QWeb `t-out="object.field"`

**Payslip Email - Employee Delivery Template (2025-11-28):**
- **Subject:** `💰 Comprobante de Pago │ Nro.: {{ object.number }} │ Lote: {{ object.payslip_run_id.name if object.payslip_run_id else "N/A" }}`
- **Email From:** `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>`
- **Email To:** `{{ object.employee_id.work_email }}`
- **Email CC:** `recursoshumanos@ueipab.edu.ve`
- **Exchange Rate:** Uses `object.exchange_rate_used` dynamically (fixed 2025-11-28)
- Includes digital acknowledgment button
- Button text: "Enviar conformidad digital"
- Acknowledgment title: "Acuso conformidad y recepción digital de este comprobante"
- Records confirmation with date, time, and IP
- Deduction labels: IVSS 4%, FAOV 1%, Paro Forzoso 0.5%

**Email Template Exchange Rate Fix (2025-11-28):**
- **Problem:** Template had hardcoded rate `241.5780` in JSONB `body_html` field
- **Solution:** Changed to `object.exchange_rate_used or 1.0` for dynamic lookup
- **Affected:** Both `es_VE` and `en_US` locale versions
- **Template IDs:** Testing: 43, Production: 37

**Email Template Salary Breakdown Fix (2025-12-15):**
- **Problem:** Salary breakdown section was empty in delivered emails (DICIEMBRE15 batch)
- **Root Cause:** Template used `filtered(lambda ...)` which gets silently stripped in QWeb email rendering
- **Symptoms:** Working NOVIEMBRE30 emails had ~9KB body, broken emails only ~3KB
- **Solution:**
  1. Added `get_line_amount(code)` helper method to `hr.payslip` model
  2. Replaced all `filtered(lambda l: l.code == 'CODE')` with `object.get_line_amount('CODE')`
  3. Fixed via direct SQL update to `mail_template.body_html` JSONB field
- **Template Update Method:** Direct PostgreSQL update (Odoo ORM wasn't persisting correctly)
  ```sql
  UPDATE mail_template SET body_html = (SELECT pg_read_file('/tmp/template.json')::jsonb) WHERE id = 37;
  ```
- **Files Modified:**
  - `ueipab_payroll_enhancements/models/hr_payslip.py` - Added `get_line_amount()` helper
  - `mail.template` ID 37 (Production), ID 43 (Testing) - Replaced body_html
- **Template Features:**
  - Uses `object.get_line_amount('VE_SALARY_V2')` instead of lambda filters
  - Uses `object.exchange_rate_used or 1.0` for dynamic exchange rate
  - Includes emojis: 💰📋📅👤🆔💳✅❌💵📧
  - Both `en_US` and `es_VE` locales identical (22,900 chars each)
- **Module Version:** 17.0.1.47.0

**Payslip Acknowledgment Landing Page (Updated 2025-11-28):**
- Amount displayed in **VES (Bs.)** using payslip exchange rate
- Title: "Confirmar Recepción Digital"
- Text: "Al hacer click en el botón, confirma que ha recibido y revisado este comprobante de pago de forma digital."
- Button: "Confirmar Recepción Digital"
- Audit trail: Records date, time, and IP address

---

## Module Versions

### Testing Environment

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | 17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | 17.0.1.47.0 | 2025-12-15 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| ueipab_ari_portal | 17.0.1.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | 2025-12-01 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.44.0 | **Needs upgrade to 1.45.0** |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | Not installed | Optional |
| ueipab_hrms_dashboard_ack | Not installed | Optional |

**OHRMS Core Modules (2025-11-29):**
Installed from `ohrms_core-17.0.1.0.0.zip` - safe modules only (excluded `hr_payroll_community` and `hr_payroll_account_community` to preserve customizations):
- `hrms_dashboard` - HR Dashboard (requires pandas)
- `ohrms_loan` - Employee loan management
- `ohrms_salary_advance` - Salary advance requests
- `ohrms_core` - Base OHRMS module
- `hr_employee_transfer`, `hr_employee_updation`, `hr_resignation`, `hr_reminder`, `hr_reward_warning`
- `hr_leave_request_aliasing`, `hr_multi_company`
- `oh_employee_creation_from_user`, `oh_employee_documents_expiry`

**hrms_dashboard Bug Fixes (2025-12-01):**
- **File:** `addons/hrms_dashboard/models/hr_employee.py:43`
- **Bug 1:** `attendance_manual()` used `browse(request.session.uid)` assuming user_id == employee_id
- **Fix:** Changed to `search([('user_id', '=', request.session.uid)])` to correctly find employee by user link
- **Bug 2:** D3 pie charts threw NaN errors when no data available
- **Fix:** Added zero-data checks to show "No data available" message instead of broken charts

**v1.45.0 Changes (2025-12-01):**
- Batch email progress wizard with error tracking
- Auto-populate exchange rate from BCV
- Simplified Generate Payslips button (no confirmation required)
- Batch email template selector and fix notifications
- Recompute payslips after syncing dates
- Include draft payslips in Total Net Payable
- SSO 4.5% → 4% fix for V2 payslips
- Interest calculation fix (accrual method) for Finiquito and Liquidación reports

---

## Key Technical Patterns

### Odoo safe_eval (Salary Rules)
```python
# FORBIDDEN:
from datetime import timedelta  # NO imports
hasattr(contract, 'field')      # NO hasattr

# ALLOWED:
(date1 - date2).days            # Direct arithmetic
try:
    value = contract.field or False
except:
    value = False
```

### Odoo 17 View Syntax
```xml
<!-- OLD (Odoo 16) -->
<div attrs="{'invisible': [('field', '=', 0)]}">

<!-- NEW (Odoo 17) -->
<div invisible="field == 0">
```

### Public Routes & Database Selection (Odoo 17)
Routes with `auth='public'` require database session.

**Production Fix (2025-11-27):** Changed `dbfilter` from `^(DB_UEIPAB|testing)$` to `^DB_UEIPAB$`
- **Problem:** Password reset/invitation links returned 404 without active session
- **Root Cause:** Multiple databases in filter prevented auto-selection
- **Solution:** Single-database filter enables auto-session creation
- **File:** `/etc/odoo/odoo.conf` in `ueipab17` container

### Report Development
- Use `web.basic_layout` for UTF-8 support
- Model naming: `report.<module>.<template_id>` (exact match)
- TransientModel wizards need security access rules
- QWeb: Pass data structures only (no Python calls)

---

## Production Environment

**Config File:** `config/production.json` (gitignored - contains credentials)

```json
{
  "production": {
    "server": { "host": "10.124.0.3", "user": "root" },
    "database": { "name": "DB_UEIPAB", "user": "odoo" },
    "containers": { "odoo": "ueipab17", "postgres": "ueipab17_postgres_1" }
  }
}
```

**SSH Connection Pattern:**
```bash
sshpass -p '$PASSWORD' ssh -o StrictHostKeyChecking=no root@10.124.0.3 \
  "docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c 'SQL_QUERY'"
```

**SSH Rate Limiting Fix (2025-12-12):**
- **Problem:** Parallel SSH connections from dev server got "Connection refused"
- **Cause:** UFW had `ufw limit 22/tcp` rule (max 6 connections per 30s)
- **Solution:** Whitelisted dev server IP for unlimited SSH access
- **Rule Applied:** `ufw insert 1 allow from 10.124.0.2 to any port 22 comment 'Dev server SSH unlimited'`
- **Result:** Parallel SSH calls now work; external IPs still rate-limited

**Contract Status:**
- Production: 44 contracts (V2 structure assigned)
- Testing: 46 contracts

### Production Upgrade Procedure

**Pending Upgrade:** `ueipab_payroll_enhancements` 1.44.0 → 1.45.0

**Files to Copy:**
```
addons/ueipab_payroll_enhancements/
├── __manifest__.py                    (modified)
├── models/finiquito_report.py         (modified - interest fix)
├── models/liquidacion_breakdown_report.py (modified - interest fix)
├── models/liquidacion_breakdown_wizard.py (modified)
├── security/ir.model.access.csv       (modified - wizard access)
├── views/hr_payslip_run_view.xml      (modified - buttons)
├── wizard/__init__.py                 (modified)
├── wizard/batch_email_wizard.py       (NEW)
└── wizard/batch_email_wizard_view.xml (NEW)
```

**Upgrade Steps:**
```bash
# 1. Backup production database
sshpass -p '$PASSWORD' ssh root@10.124.0.3 \
  "docker exec ueipab17_postgres_1 pg_dump -U odoo DB_UEIPAB > /backup/DB_UEIPAB_$(date +%Y%m%d).sql"

# 2. Copy module files (from dev server)
scp -r addons/ueipab_payroll_enhancements root@10.124.0.3:/path/to/extra-addons/

# 3. Restart Odoo
sshpass -p '$PASSWORD' ssh root@10.124.0.3 "docker restart ueipab17"

# 4. Upgrade module via UI or shell
# Apps → ueipab_payroll_enhancements → Upgrade
```

**Optional - HRMS Dashboard Installation:**
```bash
# Copy both modules
scp -r addons/hrms_dashboard root@10.124.0.3:/path/to/extra-addons/
scp -r addons/ueipab_hrms_dashboard_ack root@10.124.0.3:/path/to/extra-addons/

# Install via Apps menu (hrms_dashboard first, then ueipab_hrms_dashboard_ack)
```

---

## Quick Commands

```bash
# Run script in testing
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py

# Restart Odoo
docker restart odoo-dev-web

# Clear cache
Ctrl+Shift+R (browser hard reload)
```

---

## Environment Sync

**VEB Exchange Rate Sync:** `scripts/sync-veb-rates-from-production.sql`
- Source: `ueipab17_postgres_1` @ 10.124.0.3
- Production: 636 rates (2024-01-30 to 2025-11-27)
- Currency ID: 2 (VEB)

---

## Documentation Index

### Core Systems
- [V2 Implementation](documentation/LIQUIDATION_V2_IMPLEMENTATION.md)
- [V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)
- [V2 Payroll Implementation](documentation/V2_PAYROLL_IMPLEMENTATION.md)

### Reports
- [Payroll Disbursement](documentation/PAYROLL_DISBURSEMENT_REPORT.md)
- [Prestaciones Interest](documentation/PRESTACIONES_INTEREST_REPORT.md)
- [Relacion Breakdown](documentation/RELACION_BREAKDOWN_REPORT.md)
- [Finiquito Report](documentation/FINIQUITO_REPORT.md)
- [Exchange Rate Override](documentation/EXCHANGE_RATE_OVERRIDE_FEATURE.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)
- [V2 Formula Bugs](documentation/LIQUIDATION_V2_FORMULA_BUGS_2025-11-21.md)
- [Vacation/Bono Fix](documentation/VACATION_BONO_FIX_IMPLEMENTATION_PLAN.md)

### Email System
- [Send Mail Fix](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md)
- [Phase 2 Decommission](documentation/PHASE2_EMAIL_DECOMMISSION_PLAN.md)

### Infrastructure
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [WebSocket Issue](documentation/WEBSOCKET_ISSUE_DIAGNOSIS.md)

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)
- [Liquidation Clarifications](documentation/LIQUIDATION_CLARIFICATIONS.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history and bug fixes.
