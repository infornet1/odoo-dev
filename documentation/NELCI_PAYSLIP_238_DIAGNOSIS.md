# NELCI BRITO - SLIP/238 Diagnosis

**Date:** November 10, 2025
**Payslip:** SLIP/238
**Period:** November 1-15, 2025 (15 days)
**Status:** ❌ DISCREPANCY FOUND

---

## 🔍 THE DISCREPANCY

**Payslip NET:** $169.32
**Spreadsheet Column Y (Bi-weekly NET + Cesta):** $153.91
**Difference:** $15.41 (10% higher)

---

## 🎯 ROOT CAUSE IDENTIFIED

The sync script `update-contracts-from-spreadsheet-FIXED.py` has a **CRITICAL BUG**:

### Lines 284-297: UPDATE Query
```sql
UPDATE hr_contract SET
    ueipab_salary_base = %s,
    ueipab_bonus_regular = %s,
    ueipab_extra_bonus = %s,
    ueipab_monthly_salary = %s  -- This field doesn't exist!
WHERE id = %s;
```

### ❌ Problems:

1. **Missing `wage` field update** - The query does NOT update the `wage` field!
2. **Invalid field** - `ueipab_monthly_salary` doesn't exist in Odoo
3. **Wrong mapping** - Uses old 4-column logic (K, L, M, N) instead of correct 3-column (K, L, M)

---

## 📊 CURRENT STATE

### NELCI BRITO Contract (hr_contract):
```
wage:                 $350.00  ← WRONG! Should be $317.29
ueipab_salary_base:   $140.36  ✓ (K - updated correctly)
ueipab_bonus_regular: $176.93  ✓ (M - updated correctly)
ueipab_extra_bonus:   $  0.00  ✓ (L - updated correctly)
Last updated:         2025-11-05 12:56:52
Department ID:        54
```

### Spreadsheet (Row 10):
```
K (Basic Salary):    30,859.88 VEB = $140.36 USD
L (Other Bonus):          0.00 VEB = $  0.00 USD
M (Major Bonus):     38,901.97 VEB = $176.93 USD
────────────────────────────────────────────────
K+L+M (GROSS):       69,761.85 VEB = $317.29 USD

Column Y (Bi-weekly NET + Cesta): $153.91 USD
Column Z (Monthly NET + Cesta):   $307.81 USD
```

---

## 💡 WHY THE PAYSLIP IS WRONG

The payslip calculation uses the **`wage` field** for some rules:

1. Payslip computes based on K, M, L values (✓ correct at $140.36, $176.93, $0.00)
2. But `wage` field is $350.00 (❌ wrong, should be $317.29)
3. Some salary rules might use `wage` as a reference
4. Result: Payslip NET = $169.32 instead of $153.91

---

## ✅ THE FIX

### Option 1: Fix the sync script (RECOMMENDED)

Update the query at lines 284-297:

```python
# CORRECT UPDATE QUERY
cur.execute("""
    UPDATE hr_contract SET
        wage = %s,                      -- ADD THIS!
        ueipab_salary_base = %s,
        ueipab_bonus_regular = %s,
        ueipab_extra_bonus = %s
    WHERE id = %s;
""", (
    salary_data['total'],    # K + L + M (GROSS)
    salary_data['base'],     # K
    salary_data['bonus'],    # M
    salary_data['extra'],    # L
    contract_id
))
```

### Option 2: Manual fix for NELCI

```sql
UPDATE hr_contract
SET wage = 317.29
WHERE id = (
    SELECT c.id FROM hr_contract c
    JOIN hr_employee e ON e.id = c.employee_id
    WHERE e.name = 'NELCI BRITO'
    AND c.state = 'open'
    LIMIT 1
);
```

Then RECOMPUTE the payslip SLIP/238 in Odoo UI.

---

## 📋 AFFECTED EMPLOYEES

**ALL 44 employees** have the same issue:
- K, M, L values updated correctly ✓
- But `wage` field NOT updated ❌

The `wage` field is still set to old values like:
- NELCI: $350.00 (should be $317.29)
- ARCIDES: $549.94 (should be $574.92?)
- NORKA: $1200.00 (needs verification)
- etc.

---

## 🔧 NEXT STEPS

1. **Fix the sync script** - Add `wage` field to UPDATE query
2. **Re-run the sync** - Update all 44 employees with correct `wage` values
3. **Recompute payslips** - All November 2025 payslips need recomputation
4. **Verify Column Y** - Confirm spreadsheet Column Y calculations are correct

---

## ⚠️ IMPORTANT NOTES

- The 43 "successfully updated" contracts were PARTIALLY updated (K, M, L only)
- The `wage` field was NEVER updated by the script
- Backup table has 50 records (includes old contracts and test data)
- Only employees with `state='open'` were updated
- Department_id does NOT prevent updates (no filter on department_id)

---

## 📝 SUMMARY

**Issue:** Sync script missing `wage` field in UPDATE query
**Impact:** All 44 employees have wrong `wage` field values
**Severity:** HIGH - Affects all payslip calculations
**Fix:** Add `wage = K+L+M` to UPDATE query and re-run sync
**Status:** ⚠️ REQUIRES USER ACTION

---

**Prepared by:** Claude Code
**Date:** 2025-11-10
**Document Version:** 1.0
