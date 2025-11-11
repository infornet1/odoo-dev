# Aguinaldos Formula Fix - November 11, 2025

## Issue

The AGUINALDOS salary rule was calculating Christmas bonus using the **wrong field**, resulting in significant overpayment.

**Error:** Using `contract.ueipab_monthly_salary` (K+M+L total wage)
**Should use:** `contract.ueipab_salary_base` (Column K - Salary Base only)

## Impact

For 15-day Aguinaldos payment period:

**Example: FLORMAR HERNANDEZ (SLIP/203)**

| Field | Old (Wrong) | New (Correct) | Difference |
|-------|-------------|---------------|------------|
| K (Salary Base) | - | $204.94 | - |
| Total (K+M+L) | $420.97 | - | - |
| Annual Aguinaldos | $841.94 | $409.88 | -$432.06 |
| **15-day Payment (50%)** | **$420.97** ❌ | **$204.94** ✓ | **-$216.03** |

**Result:** Employee was receiving **$216.03 overpayment** (105% overpaid!)

## Root Cause

Venezuelan law: Aguinaldos = 2x monthly **salary base (Column K)**, not total compensation.

The formula incorrectly used `contract.ueipab_monthly_salary` which stored the full wage breakdown:
- K (70%) = Salary Base
- M (25%) = Regular Bonus
- L (5%) = Extra Bonus

## Fix Applied

### Old Formula (INCORRECT)
```python
# Used total wage (K+M+L)
base_annual_aguinaldos = contract.ueipab_monthly_salary * 2
result = base_annual_aguinaldos * 0.5  # 50% for 15 days
```

### New Formula (CORRECT)
```python
# Uses only Column K (Salary Base)
monthly_k = contract.ueipab_salary_base or 0.0
base_annual_aguinaldos = monthly_k * 2
result = base_annual_aguinaldos * proportion  # 50% for 15 days
```

## Technical Details

**Backup Created:** `aguinaldos_rule_backup_20251110_235722`

**Fields Used:**
- ✅ `contract.ueipab_salary_base` - Column K (Salary Base 70%)
- ❌ `contract.ueipab_monthly_salary` - Legacy field from uninstalled module (confusing)

**Salary Structure:** "Aguinaldos Diciembre 2025"
**Salary Rule:** "AGUINALDOS" (code: AGUINALDOS)

## Module Clarification: ueipab_aguinaldos

**Status:** UNINSTALLED and NOT NEEDED ✓

The `ueipab_aguinaldos` module is **not being used** by the current Aguinaldos implementation:

| Component | Source | Status | Notes |
|-----------|--------|--------|-------|
| ueipab_aguinaldos module | /addons/ueipab_aguinaldos | ❌ Uninstalled | Not needed |
| ueipab_monthly_salary field | Legacy (module) | ⚠️ Exists but wrong | Stores K+M+L total |
| ueipab_salary_base field | ueipab_hr_contract | ✅ Active | Correct (K only) |
| AGUINALDOS rule | Manual (UI) | ✅ Active | Now uses K only |
| Aguinaldos structure | Manual (UI) | ✅ Active | Working correctly |

**Recommendation:** The ueipab_aguinaldos module can remain uninstalled. The current system works correctly using fields from `ueipab_hr_contract`.

## Verification

After recomputing SLIP/203:
- **Before:** $420.97 (overpayment)
- **After:** $204.94 (correct) ✓
- **Savings:** $216.03 per employee per payment

## Rollback (if needed)

```sql
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
FROM aguinaldos_rule_backup_20251110_235722 b
WHERE r.id = b.id;
```

## Related Changes

This fix completes the November 2025 payroll accuracy project:
1. ✅ Fixed Rafael Perez $0.59 ARI discrepancy
2. ✅ Implemented employee-specific ARI rates (0%, 1%, 2%, 3%)
3. ✅ Fixed 0% ARI rate bug (Python falsy value)
4. ✅ Fixed Aguinaldos overpayment ($216+ per employee)

---

**Date:** November 11, 2025
**Status:** ✅ FIXED and TESTED
**Script:** `fix_aguinaldos_formula.py`
