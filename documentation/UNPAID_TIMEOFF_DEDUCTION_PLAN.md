# Unpaid Time Off Deduction - Implementation Plan

**Date:** 2025-12-04
**Status:** DRAFT - Pending Review
**Module:** `ueipab_payroll_enhancements`
**Target Environment:** Testing first, then Production

---

## 1. Overview

### Problem Statement

Currently, the Venezuelan payroll system (V2) calculates salary based on calendar days only:

```python
# Current VE_SALARY_V2 rule
monthly_salary = contract.ueipab_salary_v2 or 0.0
period_days = (payslip.date_to - payslip.date_from).days + 1
result = monthly_salary * (period_days / 30.0)
```

**Issue:** Approved Time Off requests marked as `unpaid=True` are NOT deducted from the salary.

### Solution

Create a new salary rule `VE_UNPAID_LEAVE_DED_V2` that:
1. Detects approved unpaid Time Off during the payslip period
2. Calculates the monetary deduction based on days absent
3. Subtracts from gross salary

---

## 2. Affected Time Off Types

Based on Venezuelan Labor Law (LOTTT) analysis:

| ID | Type | `unpaid` | Deduction |
|----|------|----------|-----------|
| 13 | Permiso Muerte de un familiar (luto) | `false` | No deduction (paid) |
| 14 | Lactancia | `false` | No deduction (paid - Art. 345 LOTTT) |
| 15 | Cita Médica personal | `true` | **DEDUCT** |
| 16 | Cuidados maternos | `false` | No deduction (paid - Art. 336 LOTTT) |
| 17 | Reposo Postnatal | `false` | No deduction (paid - Art. 336 LOTTT) |
| 18 | Diligencia Personal | `true` | **DEDUCT** |
| 19 | Cita Médica de un familiar | `true` | **DEDUCT** |

---

## 3. Technical Design

### 3.1 How `hr_payroll_community` Tracks Leaves

The `get_worked_day_lines()` method already:
1. Fetches approved leaves from `hr.leave` for the payslip period
2. Groups them by `holiday_status_id` (Time Off Type)
3. Creates entries in `worked_days_line_ids` with:
   - `code`: Time Off Type code (or 'GLOBAL')
   - `number_of_days`: Days of absence
   - `number_of_hours`: Hours of absence

**Key insight:** We can access this data via `worked_days` object in salary rules.

### 3.2 New Salary Rule Structure

```
Sequence: 106 (after VE_OTHER_DED_V2, before VE_TOTAL_DED_V2)

VE_UNPAID_LEAVE_DED_V2
├── Category: DED (Deduction)
├── Condition: Always (or check if unpaid leaves exist)
├── Amount: Python code calculating deduction
└── Appears on payslip: Yes
```

### 3.3 Python Code Logic

```python
# VE_UNPAID_LEAVE_DED_V2 - Unpaid Time Off Deduction

# Get daily salary rate
monthly_salary = contract.ueipab_salary_v2 or 0.0
daily_rate = monthly_salary / 30.0

# Calculate total unpaid leave days
unpaid_days = 0.0

# Method 1: Check worked_days for leave entries
for wd_code, wd_line in worked_days.dict.items():
    if wd_code != 'WORK100':  # It's a leave, not regular work
        # We need to check if this leave type is unpaid
        # The code comes from hr.leave.type.code field
        pass

# Method 2: Query hr.leave directly (more reliable)
# This requires accessing the database within the rule

# Deduction is negative (reduces net)
result = -(unpaid_days * daily_rate)
```

### 3.4 Challenge: Identifying Unpaid Leaves

The `worked_days` object only contains:
- `code`: From `hr.leave.type.code` field (may be empty)
- `number_of_days`: Days count
- `number_of_hours`: Hours count

**Problem:** We cannot directly check `hr.leave.type.unpaid` from `worked_days`.

### 3.5 Proposed Solutions

#### Option A: Use Time Off Type Code Convention

Set specific codes for unpaid leave types:

| ID | Type | Current Code | Proposed Code |
|----|------|--------------|---------------|
| 15 | Cita Médica personal | (empty) | `UNPAID_CITA_MED` |
| 18 | Diligencia Personal | (empty) | `UNPAID_DILIG` |
| 19 | Cita Médica de un familiar | (empty) | `UNPAID_CITA_FAM` |

**Salary Rule Logic:**
```python
unpaid_days = 0.0
for wd_code, wd_line in worked_days.dict.items():
    if wd_code and wd_code.startswith('UNPAID_'):
        unpaid_days += wd_line.number_of_days

daily_rate = (contract.ueipab_salary_v2 or 0.0) / 30.0
result = -(unpaid_days * daily_rate)
```

**Pros:** Simple, uses existing mechanism
**Cons:** Requires code convention discipline, manual setup

---

#### Option B: Query Database Directly

Access `hr.leave` records within the salary rule:

```python
# Get employee's approved unpaid leaves in this period
leaves = payslip.env['hr.leave'].search([
    ('employee_id', '=', employee.id),
    ('state', '=', 'validate'),
    ('date_from', '<=', payslip.date_to),
    ('date_to', '>=', payslip.date_from),
    ('holiday_status_id.unpaid', '=', True)
])

unpaid_days = sum(leaves.mapped('number_of_days'))
daily_rate = (contract.ueipab_salary_v2 or 0.0) / 30.0
result = -(unpaid_days * daily_rate)
```

**Pros:** Accurate, uses `unpaid` field directly
**Cons:** Database query in salary rule (performance), may not work in `safe_eval`

---

#### Option C: Extend `get_worked_day_lines()` Method (Recommended)

Modify `hr_payroll_community` or create override in `ueipab_payroll_enhancements`:

1. Add `is_unpaid` field to `hr.payslip.worked.days` model
2. Modify `get_worked_day_lines()` to populate this field
3. Use simple check in salary rule

**New Field:**
```python
class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked.days'

    is_unpaid = fields.Boolean(string='Is Unpaid Leave', default=False)
```

**Modified `get_worked_day_lines()`:**
```python
# In leave processing section
current_leave_struct = leaves.setdefault(
    holiday.holiday_status_id, {
        'name': holiday.holiday_status_id.name or _('Global Leaves'),
        'sequence': 5,
        'code': holiday.holiday_status_id.code or 'GLOBAL',
        'number_of_days': 0.0,
        'number_of_hours': 0.0,
        'contract_id': contract.id,
        'is_unpaid': holiday.holiday_status_id.unpaid,  # NEW
    })
```

**Salary Rule:**
```python
unpaid_days = 0.0
for wd_code, wd_line in worked_days.dict.items():
    if hasattr(wd_line, 'is_unpaid') and wd_line.is_unpaid:
        unpaid_days += wd_line.number_of_days

daily_rate = (contract.ueipab_salary_v2 or 0.0) / 30.0
result = -(unpaid_days * daily_rate)
```

**Pros:** Clean, accurate, reusable
**Cons:** Requires model modification, more development effort

---

## 4. Recommended Approach: Option A (Code Convention)

Given the current setup and minimal changes required, **Option A** is recommended for initial implementation.

### 4.1 Implementation Steps

#### Step 1: Update Time Off Type Codes (Database)

```sql
-- Set codes for unpaid Time Off Types in Odoo 17
UPDATE hr_leave_type SET code = 'UNPAID_CITA_MED' WHERE id = 15;
UPDATE hr_leave_type SET code = 'UNPAID_DILIG' WHERE id = 18;
UPDATE hr_leave_type SET code = 'UNPAID_CITA_FAM' WHERE id = 19;
```

#### Step 2: Create New Salary Rule

| Field | Value |
|-------|-------|
| Name | `VE_UNPAID_LEAVE_DED_V2 - Ausencias No Pagadas` |
| Code | `VE_UNPAID_LEAVE_DED_V2` |
| Category | DED (Deduction) |
| Sequence | 106 |
| Active | Yes |
| Appears on Payslip | Yes |
| Condition Select | `none` (always compute) |
| Amount Type | Python Code |

**Python Compute:**
```python
# VE_UNPAID_LEAVE_DED_V2 - Deducción por Ausencias No Pagadas
# Deducts salary for unpaid Time Off (codes starting with UNPAID_)

unpaid_days = 0.0

# Check worked_days for unpaid leave codes
for wd_code, wd_line in worked_days.dict.items():
    if wd_code and wd_code.startswith('UNPAID_'):
        unpaid_days += wd_line.number_of_days

# Calculate deduction (negative value)
if unpaid_days > 0:
    daily_rate = (contract.ueipab_salary_v2 or 0.0) / 30.0
    result = -(unpaid_days * daily_rate)
else:
    result = 0.0
```

#### Step 3: Update `VE_TOTAL_DED_V2` Rule

Add new rule to total deductions:

```python
# Current
result = -(VE_SSO_DED_V2 + VE_FAOV_DED_V2 + VE_PARO_DED_V2 + VE_ARI_DED_V2 + VE_OTHER_DED_V2)

# New (add VE_UNPAID_LEAVE_DED_V2)
result = -(VE_SSO_DED_V2 + VE_FAOV_DED_V2 + VE_PARO_DED_V2 + VE_ARI_DED_V2 + VE_OTHER_DED_V2) + VE_UNPAID_LEAVE_DED_V2
```

**Note:** `VE_UNPAID_LEAVE_DED_V2` is already negative, so we ADD it (not subtract).

#### Step 4: Add to Salary Structure

Link rule to `LIQUID_VE_V2` and/or regular payroll structure.

---

## 5. Testing Plan

### 5.1 Test Scenario 1: No Unpaid Leave

1. Create payslip for employee with no Time Off
2. Verify `VE_UNPAID_LEAVE_DED_V2` = 0
3. Verify NET salary unchanged

### 5.2 Test Scenario 2: Unpaid Leave (Diligencia Personal)

1. Create Time Off request:
   - Type: Diligencia Personal (ID 18)
   - Days: 2
   - State: Approved
2. Create payslip for same period
3. Verify:
   - `worked_days` contains entry with code `UNPAID_DILIG`
   - `VE_UNPAID_LEAVE_DED_V2` = -(2 * daily_rate)
   - NET salary reduced correctly

### 5.3 Test Scenario 3: Mixed Leaves

1. Create two Time Off requests:
   - Diligencia Personal: 1 day (unpaid)
   - Lactancia: 1 day (paid)
2. Create payslip
3. Verify:
   - Only 1 day deducted (Diligencia Personal)
   - Lactancia not deducted

### 5.4 Test Scenario 4: Partial Period Leave

1. Create Time Off that spans payslip boundary
2. Verify only days within payslip period are deducted

---

## 6. Rollout Plan

### Phase 1: Testing Environment

1. Update Time Off Type codes (SQL)
2. Create salary rule via Odoo UI or XML
3. Run test scenarios
4. Verify payslip calculations

### Phase 2: Production Deployment

1. Backup database
2. Apply Time Off Type code updates
3. Create salary rule
4. Update VE_TOTAL_DED_V2
5. Test with draft payslip
6. Go live

---

## 7. Files to Modify

| File | Change |
|------|--------|
| `ueipab_payroll_enhancements/__manifest__.py` | Bump version |
| `ueipab_payroll_enhancements/data/hr_salary_rule_data.xml` | Add new rule (optional, can do via UI) |
| Database: `hr_leave_type` | Set `code` field for unpaid types |
| Database: `hr_salary_rule` | Update `VE_TOTAL_DED_V2` formula |

---

## 8. Alternative: Future Enhancement (Option C)

If code convention becomes cumbersome, implement Option C:

1. Add `is_unpaid` field to `hr.payslip.worked.days`
2. Override `get_worked_day_lines()` in `ueipab_payroll_enhancements`
3. Simplify salary rule to check `is_unpaid` flag

This provides a more robust long-term solution.

---

## 9. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Claude | 2025-12-04 | Draft |
| Reviewer | | | Pending |
| HR Approval | | | Pending |

---

## 10. Questions for Review

1. Should unpaid leave deduction appear as separate line on payslip or combined with other deductions?
2. Should we deduct based on calendar days or working days?
3. Are there any other Time Off Types that should be marked as unpaid?
4. Should partial day leaves (hours) be supported?

---

**Next Steps:** Await approval to proceed with implementation in testing environment.
