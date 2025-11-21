# AGUINALDOS V2 Formula Migration

**Date:** 2025-11-21
**Status:** ✅ COMPLETED
**Script:** `scripts/fix_aguinaldos_v2_formula.py`

## Overview

Updated the AGUINALDOS salary rule to use V2 payroll fields, ensuring consistency with the V2 payroll system implemented in November 2025.

## Problem Identified

**Issue:** AGUINALDOS rule was using V1 field `ueipab_salary_base` instead of V2 field `ueipab_salary_v2`

**Impact:**
- Inconsistent with V2 payroll system (VE_PAYROLL_V2)
- All 44 employees migrated to V2 fields, but AGUINALDOS still referenced old V1 field
- Could cause calculation errors if V1 fields become stale

## Changes Applied

### Old Formula (V1)
```python
# Uses V1 field (percentage-based system)
monthly_k = contract.ueipab_salary_base or 0.0
base_annual_aguinaldos = monthly_k * 2
result = base_annual_aguinaldos * proportion
```

### New Formula (V2)
```python
# V2: Uses ueipab_salary_v2 (direct salary subject to deductions)
monthly_salary_v2 = contract.ueipab_salary_v2 or 0.0
base_annual_aguinaldos = monthly_salary_v2 * 2
result = base_annual_aguinaldos * proportion
```

## Venezuelan Law Compliance

**Legal Requirement:** Aguinaldos = 2× monthly salary
**Payment Structure:** Bi-monthly installments (50% each period)

- **Period 1-15:** 50% of annual Aguinaldos
- **Period 16-31:** 50% of annual Aguinaldos

✅ Both V1 and V2 formulas maintain legal compliance

## V2 Payroll Context

### V2 Migration Timeline
- **Phase 2 (2025-11-16):** Created V2 contract fields (`ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`)
- **Phase 3 (2025-11-16):** Created VE_PAYROLL_V2 structure with V2 rules
- **Phase 4 (2025-11-16):** Migrated all 44 employees to V2 fields
- **Phase 5 (2025-11-16):** Testing & validation (97.7% accuracy)
- **AGUINALDOS Update (2025-11-21):** Migrated AGUINALDOS formula to V2 ✅

### V2 Field Definitions
```python
# V2 Contract Fields (Direct Amounts - NO Percentages)
contract.ueipab_salary_v2       # Direct salary subject to deductions
contract.ueipab_extrabonus_v2   # Extra bonus NOT subject to deductions
contract.ueipab_bonus_v2        # Bonus NOT subject to deductions
contract.cesta_ticket_usd       # Food allowance (existing field)
```

## Technical Details

### Backup Created
```
Table: aguinaldos_rule_backup_20251121_133251
Contains: Complete backup of AGUINALDOS rule before V2 migration
```

### Rollback (if needed)
```sql
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
FROM aguinaldos_rule_backup_20251121_133251 b
WHERE r.id = b.id;
```

## Testing Recommendations

### 1. Test Calculation (Single Employee)
```python
# Example: Employee with ueipab_salary_v2 = $119.21
# Expected bi-monthly AGUINALDOS: $119.21 × 2 × 50% = $119.21
```

### 2. Batch Processing
- Create test batch: "AGUINALDOS_TEST_DIC_2025"
- Period: Dec 1-15, 2025 (first half)
- Verify all 44 employees calculate correctly

### 3. Validation Checklist
- ✅ Formula references `contract.ueipab_salary_v2`
- ✅ Bi-monthly proportion logic intact (50% per period)
- ✅ Calculations match expected 2× monthly salary
- ✅ No references to old V1 fields

## Related Documentation

- **V2 Implementation Reference:** [V2_PAYROLL_IMPLEMENTATION.md](V2_PAYROLL_IMPLEMENTATION.md)
- **V2 Revision Plan:** [VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md](VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)
- **Original Aguinaldos Fix:** [AGUINALDOS_FORMULA_FIX.md](AGUINALDOS_FORMULA_FIX.md) (V1 - Nov 2025)
- **Aguinaldos Testing:** [AGUINALDOS_TEST_RESULTS_2025-11-10.md](AGUINALDOS_TEST_RESULTS_2025-11-10.md)

## Summary

| Aspect | Before (V1) | After (V2) |
|--------|-------------|------------|
| **Field Used** | `ueipab_salary_base` | `ueipab_salary_v2` |
| **System** | Percentage-based | Direct amounts |
| **Migration Status** | Outdated | ✅ Current |
| **Legal Compliance** | ✅ Compliant | ✅ Compliant |
| **Calculation** | 2× monthly (50% bi-monthly) | 2× monthly (50% bi-monthly) |

**Result:** AGUINALDOS formula now fully integrated with V2 payroll system

---

**Backup Table:** `aguinaldos_rule_backup_20251121_133251`
**Script:** `/opt/odoo-dev/scripts/fix_aguinaldos_v2_formula.py`
**Date Applied:** 2025-11-21 13:32:51 UTC
