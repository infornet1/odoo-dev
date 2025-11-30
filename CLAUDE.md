# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-30 16:30 UTC

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
- Required groups: `hr_payroll.group_hr_payroll_manager` OR `hr_payroll.group_hr_payroll_user`
- Regular employees without payroll access will NOT see the widget

**Technical Notes:**
- Does NOT use OWL template inheritance (t-inherit not supported for OWL components)
- Uses DOM manipulation via `insertAdjacentHTML()` after component mounts
- Widget only renders if user has payroll role AND has payslips (`stats.personal.total > 0`)

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

**Payslip Acknowledgment Landing Page (Updated 2025-11-28):**
- Amount displayed in **VES (Bs.)** using payslip exchange rate
- Title: "Confirmar Recepción Digital"
- Text: "Al hacer click en el botón, confirma que ha recibido y revisado este comprobante de pago de forma digital."
- Button: "Confirmar Recepción Digital"
- Audit trail: Records date, time, and IP address

---

## Module Versions

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | v17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | v1.47.0 | 2025-11-29 |
| ueipab_hr_contract | v17.0.2.1.0 | 2025-11-26 |
| ueipab_ari_portal | v17.0.1.0.0 | 2025-11-26 |
| hrms_dashboard | v17.0.1.0.0 | 2025-11-29 |

**OHRMS Core Modules (2025-11-29):**
Installed from `ohrms_core-17.0.1.0.0.zip` - safe modules only (excluded `hr_payroll_community` and `hr_payroll_account_community` to preserve customizations):
- `hrms_dashboard` - HR Dashboard (requires pandas)
- `ohrms_loan` - Employee loan management
- `ohrms_salary_advance` - Salary advance requests
- `ohrms_core` - Base OHRMS module
- `hr_employee_transfer`, `hr_employee_updation`, `hr_resignation`, `hr_reminder`, `hr_reward_warning`
- `hr_leave_request_aliasing`, `hr_multi_company`
- `oh_employee_creation_from_user`, `oh_employee_documents_expiry`

**hrms_dashboard Bug Fix (2025-11-29):**
- **File:** `addons/hrms_dashboard/models/hr_employee.py:43`
- **Bug:** `attendance_manual()` used `browse(request.session.uid)` assuming user_id == employee_id
- **Fix:** Changed to `search([('user_id', '=', request.session.uid)])` to correctly find employee by user link
- **Symptom:** "Record does not exist" error on check-in/check-out

**v1.47.0 Changes (2025-11-29):**
- **Relación de Liquidación Report Fix:** Interest now uses historical monthly rates (accrual method) instead of latest rate
- **Net Amount Fix:** Now calculated from Benefits - Deductions instead of simple USD conversion
- Both reports ("Prestaciones Soc. Intereses" and "Relación de Liquidación") now show matching interest amounts

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

**Contract Status:**
- Production: 44 contracts (V2 structure assigned)
- Testing: 46 contracts

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
