# Liquidación Venezolana V2 - Migration Plan

**Date:** 2025-11-16
**Status:** PLANNING - Awaiting Approval
**Purpose:** Create V2 version of Venezuelan Liquidation structure using `ueipab_salary_v2` field

---

## Executive Summary

**Objective:** Create a parallel "Liquidación Venezolana V2" salary structure that uses the new V2 contract fields (`ueipab_salary_v2`) instead of the legacy V1 field (`ueipab_deduction_base`).

**Complexity:** **SIMPLE** ✅
- Only **6 out of 14 rules** need formula updates
- Single field replacement: `ueipab_deduction_base` → `ueipab_salary_v2`
- All other logic remains identical (date calculations, historical tracking, deduction rates)
- Straightforward copy-and-modify approach

**Timeline:** 1-2 hours (single phase implementation)

---

## Current V1 Structure Analysis

### Structure Details

| Property | Value |
|----------|-------|
| **Name** | Liquidación Venezolana |
| **Code** | LIQUID_VE |
| **ID** | 3 |
| **Parent** | None (Independent) |
| **Total Rules** | 14 |

### Rule Breakdown

| Category | Count | Purpose |
|----------|-------|---------|
| **Basic (BASIC)** | 4 | Daily rate calculations (hidden) |
| **Allowances (ALW)** | 6 | Benefits to pay (visible on payslip) |
| **Deductions (DED)** | 3 | Mandatory deductions |
| **Net (NET)** | 1 | Final liquidation amount |

### Rules Using `ueipab_deduction_base` (Need V2 Update)

| Seq | Code | Name | Field Usage |
|-----|------|------|-------------|
| 2 | **LIQUID_DAILY_SALARY** | Salario Diario Base | `base_salary = contract.ueipab_deduction_base` |
| 3 | **LIQUID_INTEGRAL_DAILY** | Salario Diario Integral | `base_daily = contract.ueipab_deduction_base / 30.0` |
| 4 | **LIQUID_ANTIGUEDAD_DAILY** | Tasa Diaria Antiguedad | `base_daily = contract.ueipab_deduction_base / 30.0` |
| 13 | **LIQUID_UTILIDADES** | Utilidades | Uses `LIQUID_DAILY_SALARY` (indirect) |
| 21 | **LIQUID_FAOV** | FAOV | Uses `LIQUID_DAILY_SALARY` (indirect) |
| 22 | **LIQUID_INCES** | INCES | Uses `LIQUID_DAILY_SALARY` (indirect) |

**Note:** LIQUID_UTILIDADES, LIQUID_FAOV, and LIQUID_INCES don't directly access `ueipab_deduction_base`, but they reference `LIQUID_DAILY_SALARY` which does. Once we update the 3 daily rate rules, these will automatically use V2 values.

### Rules NOT Requiring Changes (8 rules)

| Seq | Code | Name | Reason |
|-----|------|------|--------|
| 1 | LIQUID_SERVICE_MONTHS | Meses de Servicio | Uses only dates (contract.date_start, payslip.date_to) |
| 11 | LIQUID_VACACIONES | Vacaciones | Uses `LIQUID_DAILY_SALARY` and `LIQUID_SERVICE_MONTHS` |
| 12 | LIQUID_BONO_VACACIONAL | Bono Vacacional | Uses `LIQUID_DAILY_SALARY` and historical tracking |
| 14 | LIQUID_PRESTACIONES | Prestaciones | Uses `LIQUID_INTEGRAL_DAILY` and `LIQUID_SERVICE_MONTHS` |
| 15 | LIQUID_ANTIGUEDAD | Antigüedad | Uses `LIQUID_ANTIGUEDAD_DAILY` and historical tracking |
| 16 | LIQUID_INTERESES | Intereses | Uses `LIQUID_PRESTACIONES` and `LIQUID_SERVICE_MONTHS` |
| 195 | LIQUID_VACATION_PREPAID | Vacaciones/Bono Prepagadas | Uses `LIQUID_VACACIONES` and `LIQUID_BONO_VACACIONAL` |
| 200 | LIQUID_NET | Liquidación Neta | Sum of all other rules |

**These rules only need to be copied with V2 naming convention** - no formula changes required!

---

## V2 Design

### New Structure Details

| Property | Value |
|----------|-------|
| **Name** | Liquidación Venezolana V2 |
| **Code** | LIQUID_VE_V2 |
| **Parent** | None (Independent) ⚠️ |
| **Total Rules** | 14 (same as V1) |
| **Accounting** | Same as V1 (use existing accounts) |

⚠️ **CRITICAL:** V2 structure must be **independent** (no parent) to avoid duplicate journal entries (lesson learned from regular payroll V2).

### V2 Rule Naming Convention

All V2 rules will follow this pattern:
- **Code:** Add `_V2` suffix → `LIQUID_DAILY_SALARY_V2`
- **Name:** Add "V2" → "Salario Diario Base V2"

**Example:**
```
V1: LIQUID_DAILY_SALARY - Salario Diario Base
V2: LIQUID_DAILY_SALARY_V2 - Salario Diario Base V2
```

### Formula Migration Pattern

**OLD (V1):**
```python
base_salary = contract.ueipab_deduction_base or 0.0
daily_salary = base_salary / 30.0
```

**NEW (V2):**
```python
base_salary = contract.ueipab_salary_v2 or 0.0
daily_salary = base_salary / 30.0
```

**That's it!** Single field name replacement.

### Rule References Migration

When rules reference other rules, we need to update references to V2 versions:

**OLD (V1):**
```python
daily_salary = LIQUID_DAILY_SALARY or 0.0
```

**NEW (V2):**
```python
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0
```

---

## Detailed Rule-by-Rule Migration Guide

### Rules Requiring Formula Changes (6 rules)

#### 1. LIQUID_DAILY_SALARY_V2

**Sequence:** 2
**Category:** BASIC
**Change:** Line 5

```python
# V1 Formula:
base_salary = contract.ueipab_deduction_base or 0.0
result = base_salary / 30.0

# V2 Formula:
base_salary = contract.ueipab_salary_v2 or 0.0  # ⬅️ CHANGED
result = base_salary / 30.0
```

---

#### 2. LIQUID_INTEGRAL_DAILY_V2

**Sequence:** 3
**Category:** BASIC
**Change:** Line 2

```python
# V1 Formula:
base_daily = (contract.ueipab_deduction_base or 0.0) / 30.0
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily

# V2 Formula:
base_daily = (contract.ueipab_salary_v2 or 0.0) / 30.0  # ⬅️ CHANGED
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily
```

---

#### 3. LIQUID_ANTIGUEDAD_DAILY_V2

**Sequence:** 4
**Category:** BASIC
**Change:** Line 2

```python
# V1 Formula:
base_daily = (contract.ueipab_deduction_base or 0.0) / 30.0
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily

# V2 Formula:
base_daily = (contract.ueipab_salary_v2 or 0.0) / 30.0  # ⬅️ CHANGED
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)
result = base_daily + utilidades_daily + bono_vac_daily
```

---

#### 4. LIQUID_VACACIONES_V2

**Sequence:** 11
**Category:** ALW
**Change:** Line 2 (rule reference)

```python
# V1 Formula:
service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0
# ... rest of formula unchanged ...

# V2 Formula:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0  # ⬅️ CHANGED
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0      # ⬅️ CHANGED
# ... rest of formula unchanged ...
```

---

#### 5. LIQUID_BONO_VACACIONAL_V2

**Sequence:** 12
**Category:** ALW
**Change:** Lines 2-3 (rule references)

```python
# V1 Formula:
service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0
# ... rest of formula unchanged ...

# V2 Formula:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0  # ⬅️ CHANGED
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0      # ⬅️ CHANGED
# ... rest of formula unchanged ...
```

---

#### 6. LIQUID_UTILIDADES_V2

**Sequence:** 13
**Category:** ALW
**Change:** Lines 2-3 (rule references)

```python
# V1 Formula:
service_months = LIQUID_SERVICE_MONTHS or 0.0
daily_salary = LIQUID_DAILY_SALARY or 0.0
# ... rest of formula unchanged ...

# V2 Formula:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0  # ⬅️ CHANGED
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0      # ⬅️ CHANGED
# ... rest of formula unchanged ...
```

---

### Rules Requiring Only V2 References (6 rules)

These rules don't use `ueipab_deduction_base` directly, but reference other V2 rules:

#### 7. LIQUID_SERVICE_MONTHS_V2

**No formula changes** - only uses dates (contract.date_start, payslip.date_to)

#### 8. LIQUID_PRESTACIONES_V2

**Change:** Update rule references
```python
# V1:
service_months = LIQUID_SERVICE_MONTHS or 0.0
integral_daily = LIQUID_INTEGRAL_DAILY or 0.0

# V2:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
integral_daily = LIQUID_INTEGRAL_DAILY_V2 or 0.0
```

#### 9. LIQUID_ANTIGUEDAD_V2

**Change:** Update rule references
```python
# V1:
service_months = LIQUID_SERVICE_MONTHS or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY or 0.0

# V2:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
antiguedad_daily = LIQUID_ANTIGUEDAD_DAILY_V2 or 0.0
```

#### 10. LIQUID_INTERESES_V2

**Change:** Update rule references
```python
# V1:
service_months = LIQUID_SERVICE_MONTHS or 0.0
prestaciones = LIQUID_PRESTACIONES or 0.0

# V2:
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
prestaciones = LIQUID_PRESTACIONES_V2 or 0.0
```

#### 11. LIQUID_FAOV_V2

**Change:** Update rule references
```python
# V1:
deduction_base = ((LIQUID_VACACIONES or 0) +
                  (LIQUID_BONO_VACACIONAL or 0) +
                  (LIQUID_UTILIDADES or 0))

# V2:
deduction_base = ((LIQUID_VACACIONES_V2 or 0) +
                  (LIQUID_BONO_VACACIONAL_V2 or 0) +
                  (LIQUID_UTILIDADES_V2 or 0))
```

#### 12. LIQUID_INCES_V2

**Change:** Update rule references (same pattern as FAOV)
```python
# V1:
deduction_base = ((LIQUID_VACACIONES or 0) +
                  (LIQUID_BONO_VACACIONAL or 0) +
                  (LIQUID_UTILIDADES or 0))

# V2:
deduction_base = ((LIQUID_VACACIONES_V2 or 0) +
                  (LIQUID_BONO_VACACIONAL_V2 or 0) +
                  (LIQUID_UTILIDADES_V2 or 0))
```

---

### Rules Requiring V2 References in Final Calculation (2 rules)

#### 13. LIQUID_VACATION_PREPAID_V2

**Change:** Update rule references
```python
# V1:
vacaciones = LIQUID_VACACIONES or 0.0
bono = LIQUID_BONO_VACACIONAL or 0.0

# V2:
vacaciones = LIQUID_VACACIONES_V2 or 0.0
bono = LIQUID_BONO_VACACIONAL_V2 or 0.0
```

#### 14. LIQUID_NET_V2

**Change:** Update ALL rule references
```python
# V1:
result = (
    (LIQUID_VACACIONES or 0) +
    (LIQUID_BONO_VACACIONAL or 0) +
    (LIQUID_UTILIDADES or 0) +
    (LIQUID_PRESTACIONES or 0) +
    (LIQUID_ANTIGUEDAD or 0) +
    (LIQUID_INTERESES or 0) +
    (LIQUID_FAOV or 0) +
    (LIQUID_INCES or 0) +
    prepaid_deduction
)

# V2:
result = (
    (LIQUID_VACACIONES_V2 or 0) +
    (LIQUID_BONO_VACACIONAL_V2 or 0) +
    (LIQUID_UTILIDADES_V2 or 0) +
    (LIQUID_PRESTACIONES_V2 or 0) +
    (LIQUID_ANTIGUEDAD_V2 or 0) +
    (LIQUID_INTERESES_V2 or 0) +
    (LIQUID_FAOV_V2 or 0) +
    (LIQUID_INCES_V2 or 0) +
    prepaid_deduction  # This references LIQUID_VACATION_PREPAID_V2
)
```

---

## Accounting Configuration

### V1 Accounting (Current)

All V1 benefit rules use the same accounting:
- **Debit:** 5.1.01.10.002 (Nomina Administracion)
- **Credit:** 2.1.01.10.005 (Provisión Prestaciones Sociales)

**Rules with accounting configured:**
- LIQUID_VACACIONES
- LIQUID_BONO_VACACIONAL
- LIQUID_UTILIDADES
- LIQUID_PRESTACIONES
- LIQUID_ANTIGUEDAD
- LIQUID_INTERESES
- LIQUID_FAOV
- LIQUID_INCES

### V2 Accounting (Proposed)

**Option A: Reuse V1 Accounts (RECOMMENDED)**
- Same as V1: 5.1.01.10.002 / 2.1.01.10.005
- **Advantage:** Simple, immediate deployment
- **Limitation:** Not aligned with external COA (if reconciliation proceeds)

**Option B: Use External COA Accounts (FUTURE)**
- Wait for COA reconciliation decision
- May use department-based accounts (5.2.00.xx.xx, 5.3.00.xx.xx)
- **Advantage:** Aligns with external accountant's structure
- **Limitation:** Requires COA reconciliation to be completed first

**Recommendation:** **Option A** for initial V2 deployment. Update accounting in Phase 2 after COA reconciliation.

---

## Implementation Plan

### Single-Phase Approach

Since this is a straightforward field replacement, we can do it all in one phase.

**Phase 1: Create V2 Liquidation Structure and Rules**

**Steps:**
1. Create new salary structure "Liquidación Venezolana V2" (code: LIQUID_VE_V2)
2. Create all 14 V2 rules with updated formulas
3. Link all rules to V2 structure
4. Copy accounting configuration from V1
5. Test with sample employee (e.g., create test liquidation for Virginia Verde)
6. Verify calculations match expected V2 values

**Script:** `/opt/odoo-dev/scripts/create_liquidation_v2_structure.py`

**Timeline:** 1-2 hours

---

## Testing Strategy

### Test Case 1: Simple Employee (No Historical Tracking)

**Employee:** Gabriel España
**Contract Data:**
- `ueipab_salary_v2`: (Will be set after V2 migration script)
- `date_start`: 2024-09-01
- `ueipab_original_hire_date`: Not set (simple case)
- `ueipab_previous_liquidation_date`: Not set
- `ueipab_vacation_paid_until`: Not set

**Expected V2 Behavior:**
- All calculations use `ueipab_salary_v2` instead of `ueipab_deduction_base`
- Results should be proportional to V2 salary field

---

### Test Case 2: Complex Employee (With Historical Tracking)

**Employee:** Virginia Verde
**Contract Data:**
- `ueipab_salary_v2`: (Will be set after V2 migration script)
- `date_start`: 2024-04-01 (current contract)
- `ueipab_original_hire_date`: 2021-09-01 (original hire)
- `ueipab_previous_liquidation_date`: 2024-03-31 (last liquidation)
- `ueipab_vacation_paid_until`: Not set

**Expected V2 Behavior:**
- Antigüedad uses original hire date for total seniority
- Subtracts already-paid antiguedad from previous liquidation
- Bono vacacional uses total seniority for progressive rate
- All calculations use `ueipab_salary_v2`

---

### Test Case 3: Employee With Prepaid Vacation

**Employee:** Josefina Rodriguez
**Contract Data:**
- `ueipab_salary_v2`: (Will be set after V2 migration script)
- `date_start`: 2023-09-01
- `ueipab_vacation_paid_until`: 2025-08-01 (received Aug 1 annual payment)

**Expected V2 Behavior:**
- Vacation/bono calculated only from Aug 1 to liquidation date
- Prepaid deduction removes vacation/bono already paid
- Net liquidation reduced by prepaid amount

---

## Risk Assessment

### Low Risk ✅

**Why Low Risk:**
1. **Simple field replacement** - only changing `ueipab_deduction_base` to `ueipab_salary_v2`
2. **All logic remains identical** - date calculations, rates, formulas unchanged
3. **Parallel deployment** - V1 structure remains active and untouched
4. **Well-tested V1 base** - V1 formulas already validated (9 phases complete)
5. **No percentage calculations** - direct field usage (simpler than regular payroll V2)

### Potential Issues

**Issue 1: Missing ueipab_salary_v2 Values**
- **Risk:** Some contracts may not have `ueipab_salary_v2` populated yet
- **Mitigation:** Run Phase 4 bulk update script (already completed for 44 employees)
- **Fallback:** Formula uses `or 0.0` to handle missing values safely

**Issue 2: Accounting Not Aligned with External COA**
- **Risk:** V2 may use V1 accounts (not external COA)
- **Mitigation:** Use V1 accounts initially, update in Phase 2 after COA reconciliation
- **Impact:** Low - accounting can be updated later without affecting calculations

---

## Comparison: V1 vs V2

### Formula Complexity

| Aspect | V1 | V2 |
|--------|----|----|
| **Base Salary Field** | `ueipab_deduction_base` | `ueipab_salary_v2` |
| **Field Type** | Calculated (~42% of wage) | Direct amount |
| **Daily Rate Calculation** | `deduction_base / 30` | `salary_v2 / 30` |
| **Historical Tracking** | ✅ Supported | ✅ Supported (unchanged) |
| **Deduction Rates** | FAOV 1%, INCES 0.5% | ✅ Same |
| **Interest Rate** | 13% annual | ✅ Same |
| **Formula Complexity** | Medium | **Low** ✅ |

### Example Calculation (Hypothetical)

**Scenario:** Employee with 11 months service, $119.09 V2 salary

**V1 Calculation:**
```
ueipab_deduction_base = $170.30 (42% of $400.62 wage)
Daily Rate = $170.30 / 30 = $5.68/day
Vacaciones (15 days) = (11/12) × 15 × $5.68 = $77.90
```

**V2 Calculation:**
```
ueipab_salary_v2 = $119.09 (direct field)
Daily Rate = $119.09 / 30 = $3.97/day
Vacaciones (15 days) = (11/12) × 15 × $3.97 = $54.48
```

**Key Difference:** V2 uses actual deductible salary ($119.09), not the inflated deduction_base ($170.30).

---

## Expected Results

### After V2 Implementation

**Benefits:**
- ✅ Liquidation calculations use transparent V2 salary field
- ✅ Eliminates confusion from percentage-based deduction_base
- ✅ Aligns with regular payroll V2 (both use ueipab_salary_v2)
- ✅ Simplified formula maintenance
- ✅ Parallel operation with V1 (no disruption)

**Deliverables:**
- ✅ New structure: "Liquidación Venezolana V2" (LIQUID_VE_V2)
- ✅ 14 V2 rules with updated formulas
- ✅ Test results for 3 employee scenarios
- ✅ Documentation update in CLAUDE.md

---

## Questions for User

### 1. Accounting Strategy

**Question:** Should V2 liquidation use:
- **Option A:** Same accounts as V1 (5.1.01.10.002 / 2.1.01.10.005) - **RECOMMENDED**
- **Option B:** Wait for COA reconciliation to determine correct accounts

### 2. Testing Scope

**Question:** How many employees should we test before considering V2 ready for production?
- **Option A:** 3 employees (simple, complex, prepaid) - **RECOMMENDED**
- **Option B:** Full validation against historical liquidations
- **Option C:** Minimal (just verify structure loads correctly)

### 3. Deployment Timing

**Question:** When should we deploy V2 liquidation?
- **Option A:** Immediately (parallel to V1, no disruption)
- **Option B:** After COA reconciliation complete
- **Option C:** After next liquidation cycle (to compare V1 vs V2)

---

## Next Steps (Awaiting Approval)

1. ✅ **Review this plan** - Confirm approach is acceptable
2. ⏳ **Create implementation script** - Generate V2 structure and rules
3. ⏳ **Test with 3 employees** - Validate calculations
4. ⏳ **Document in CLAUDE.md** - Update project documentation
5. ⏳ **User acceptance** - Confirm V2 liquidation is production-ready

---

## Conclusion

**Liquidación Venezolana V2 migration is SIMPLE and LOW RISK.**

**Key Advantages:**
- Only 6 rules need direct formula updates (field replacement)
- 8 rules just need V2 rule references updated
- All logic, rates, and historical tracking remain identical
- Parallel deployment (V1 untouched)
- Straightforward testing (3 test cases cover all scenarios)

**Recommendation:** Proceed with single-phase implementation immediately. This is much simpler than the regular payroll V2 migration we already completed successfully.

---

**Status:** ⏸️ PLANNING COMPLETE - AWAITING USER APPROVAL
**Estimated Effort:** 1-2 hours for implementation + testing
**Risk Level:** 🟢 LOW
**Dependencies:** None (V2 contract fields already populated for 44 employees)

**Ready to proceed when you give the green light! 🚀**
