# Cybrosys Module Modification Report

**Status:** PLANNED REFACTORING | **Priority:** Medium | **Date:** 2025-11-30

## Overview

Analysis of all Cybrosys OHRMS modules to identify direct modifications that pose upgrade risk.

| Category | Count | Risk Level |
|----------|-------|------------|
| Heavily Modified | 2 | HIGH |
| Minor Modification | 2 | MEDIUM |
| Unmodified | 13 | SAFE |

---

## HIGH RISK - Heavily Modified Modules

### 1. `hr_payroll_community` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_payslip.py` | ~25 lines | Exchange rate: removed hardcoded `227.5567`, dynamic BCV lookup |
| `models/hr_payslip_line.py` | ~15 lines | Odoo 17 syntax: `dp.get_precision()` -> `'Payroll'` |
| `models/hr_payslip_run.py` | ~50 lines | Auto-populate rate from `res.currency.rate`, simplified button logic |
| `models/hr_salary_rule.py` | ~4 lines | Digit precision syntax update |
| `views/hr_payslip_run_views.xml` | ~30 lines | Odoo 17: `attrs={}` -> `invisible=` |
| `security/ir.model.access.csv` | ~2 lines | Added wizard access |

### 2. `hr_payroll_account_community` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_payslip.py` | ~60 lines | Cancel policy (no delete), partner fix, unlink override |
| `models/hr_payslip_line.py` | ~40 lines | Partner uses `work_contact_id` (employee) not `address_id` (company) |

**Critical Changes:**
- `action_payslip_cancel()` - No longer deletes journal entries (audit trail policy)
- `unlink()` override - Cancels (not deletes) journal entries
- Partner assignment uses employee's individual partner for accounting accuracy

---

## MEDIUM RISK - Minor Modifications

### 3. `hrms_dashboard` (Cybrosys)

**Status:** Production | **Migrated:** 2025-12-21 | **Version:** 17.0.1.0.2

| File | Changes | Description |
|------|---------|-------------|
| `models/hr_employee.py:42-58` | ~17 lines | Bug fix: `attendance_manual()` search by `user_id` |
| `static/src/js/hrms_dashboard.js:83-91` | ~9 lines | NaN fix: Employee pie chart zero-data check |
| `static/src/js/hrms_dashboard.js:281-286` | ~6 lines | NaN fix: Leave percentage calculation |
| `static/src/js/hrms_dashboard.js:297-305` | ~9 lines | NaN fix: Leave pie chart zero-data check |

**Bug Fix Details:**

1. **`attendance_manual()` Fix** (`hr_employee.py:42-58`)
   - **Original:** `browse(request.session.uid)` assumed user_id == employee_id
   - **Fixed:** `search([('user_id', '=', request.session.uid)])` correctly finds employee by user link
   - **Impact:** Check-in/out from dashboard now works for all employees

2. **D3 Pie Charts NaN Fix** (`hrms_dashboard.js`)
   - **Problem:** D3 pie charts threw NaN errors when no data available
   - **Fix 1 (line 83-91):** Checks `totalEmployees === 0` before rendering employee pie chart
   - **Fix 2 (line 281-286):** `getLegend()` returns 0% if percentage calculation is NaN
   - **Fix 3 (line 297-305):** Checks `totalLeave === 0` before rendering leave pie chart
   - **Fallback:** Shows "No data available" message instead of broken chart

**Migration to Production:**
```bash
# Copy module to production
scp -r addons/hrms_dashboard root@10.124.0.3:/home/vision/ueipab17/addons/

# Also requires ueipab_hrms_dashboard_ack if acknowledgment widget is needed
scp -r addons/ueipab_hrms_dashboard_ack root@10.124.0.3:/home/vision/ueipab17/addons/

# Restart and install
ssh root@10.124.0.3 "docker restart ueipab17"
# Then: Apps -> Update Apps List -> Search "HRMS Dashboard" -> Install
```

**Dependencies Required:**
- `pandas` Python package (already in production container)
- `hr_payroll_community`, `hr_resignation`, `hr_reward_warning` modules

### 4. `hr_payslip_monthly_report` (Cybrosys)

| File | Changes | Description |
|------|---------|-------------|
| `wizard/payslip_compact_wizard.py` | 2 lines | Fixed `report_action(docids=)` parameter |

---

## SAFE - Unmodified Modules (13 total)

All installed from `ohrms_core-17.0.1.0.0.zip` with NO modifications:

`ohrms_core`, `ohrms_loan`, `ohrms_loan_accounting`, `ohrms_salary_advance`,
`hr_employee_transfer`, `hr_employee_updation`, `hr_leave_request_aliasing`,
`hr_multi_company`, `hr_reminder`, `hr_resignation`, `hr_reward_warning`,
`oh_employee_creation_from_user`, `oh_employee_documents_expiry`

---

## Planned Refactoring (Option B)

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

## Upgrade Procedure (Current State)

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
