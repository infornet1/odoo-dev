# FINAL DIAGNOSIS - Salary Mapping Error

**Date:** November 10, 2025
**Status:** 🎯 ROOT CAUSE IDENTIFIED

---

## 📋 USER CLARIFICATIONS

1. **wage field** = GROSS (K+L+M) with NO deductions
2. **Column K** = Basic Salary Component (always present)
3. **Column L** = Other Bonus
4. **Column M** = Major bonus component paid to each employee

---

## 🔍 WHAT'S ACTUALLY IN THE SPREADSHEET

### ARCIDES ARZOLA (Row 5):
```
K (Basic):      $285.39 USD (49.6% of total)
L (Other):      $  0.00 USD ( 0.0% of total)
M (Major Bonus): $289.52 USD (50.4% of total)
──────────────────────────────────────────────
K+L+M (GROSS):  $574.92 USD (100%)
Deductions:     $ 24.98 USD (calculated as GROSS-NET)
Column Z (NET): $549.94 USD
```

### NELCI BRITO (Row 10):
```
K (Basic):      $140.36 USD (44.2% of total)
L (Other):      $  0.00 USD ( 0.0% of total)
M (Major Bonus): $176.93 USD (55.8% of total)
──────────────────────────────────────────────
K+L+M (GROSS):  $317.29 USD (100%)
Deductions:     $  9.48 USD (calculated as GROSS-NET)
Column Z (NET): $307.81 USD
```

**KEY FINDING:** The K, L, M percentages VARY by employee!
- NOT a fixed 70/25/5 distribution
- Each employee has unique breakdown
- M (Major Bonus) is actually 50-56% of total, not 25%!

---

## ❌ CURRENT ODOO CONTRACTS (WRONG)

### ARCIDES ARZOLA:
```
wage:                 $549.94 ← Column Z (NET), should be $574.92 (GROSS)!
ueipab_salary_base:   $204.49 ← Calculated as $549.94 * 0.37, should be $285.39 (K)!
ueipab_bonus_regular: $ 73.03 ← Calculated as $549.94 * 0.13, should be $289.52 (M)!
ueipab_extra_bonus:   $ 14.61 ← Calculated as $549.94 * 0.03, should be $0.00 (L)!
```

### NELCI BRITO:
```
wage:                 $163.52 ← Only K! Should be $317.29 (K+L+M)!
ueipab_salary_base:   $114.46 ← Calculated from wrong wage
ueipab_bonus_regular: $ 40.88 ← Calculated from wrong wage
ueipab_extra_bonus:   $  8.18 ← Calculated from wrong wage
```

---

## 🎯 ROOT CAUSE IDENTIFIED

### Problem 1: ARCIDES got NET instead of GROSS
Someone synced Column Z ($549.94 NET) instead of K+L+M ($574.92 GROSS) to the `wage` field.

### Problem 2: Then calculated wrong percentages
The 70/25/5 breakdown was calculated from the wrong wage value.

### Problem 3: NELCI only got K
The sync script only read Column K ($140.36), completely ignoring L and M!

### Problem 4: Field names are misleading
The field names suggest fixed percentages:
- `ueipab_salary_base` (sounds like 70%)
- `ueipab_bonus_regular` (sounds like 25%)
- `ueipab_extra_bonus` (sounds like 5%)

But the ACTUAL data in spreadsheet has:
- K = 44-50% (varies!)
- M = 50-56% (varies!)
- L = 0-13% (varies!)

---

## ✅ CORRECT MAPPING (Confirmed with User)

```python
# From spreadsheet (3 columns)
k_veb = row[10]  # Column K: Basic Salary Component
l_veb = row[11]  # Column L: Other Bonus
m_veb = row[12]  # Column M: Major Bonus Component

# Convert to USD
k_usd = k_veb / exchange_rate
l_usd = l_veb / exchange_rate
m_usd = m_veb / exchange_rate

# Map to Odoo contract fields
wage = k_usd + l_usd + m_usd  # GROSS (no deductions)
ueipab_salary_base = k_usd     # Basic Salary (NOT 70%!)
ueipab_bonus_regular = m_usd   # Major Bonus (NOT 25%!)
ueipab_extra_bonus = l_usd     # Other Bonus (NOT 5%!)
```

### For ARCIDES:
```
wage: $285.39 + $0.00 + $289.52 = $574.92 ✓
ueipab_salary_base:   $285.39 (K)
ueipab_bonus_regular: $289.52 (M)
ueipab_extra_bonus:   $  0.00 (L)
```

### For NELCI:
```
wage: $140.36 + $0.00 + $176.93 = $317.29 ✓
ueipab_salary_base:   $140.36 (K)
ueipab_bonus_regular: $176.93 (M)
ueipab_extra_bonus:   $  0.00 (L)
```

---

## 🔧 WHAT WENT WRONG ORIGINALLY

### Original Design Assumption (from /tmp/venezuelan_payroll_setup.py):
```python
# This was the ASSUMPTION:
ueipab_salary_base = wage * 0.70   # 70% base
ueipab_bonus_regular = wage * 0.25  # 25% bonus
ueipab_extra_bonus = wage * 0.05    # 5% extra
```

### Reality in Spreadsheet:
```
Each employee has UNIQUE breakdown in columns K, L, M!
Not a calculated 70/25/5, but ACTUAL amounts per employee!
```

### What Happened:
1. Original design assumed 70/25/5 distribution
2. But spreadsheet already has ACTUAL K, L, M values
3. Sync script ignored this and only read K
4. ARCIDES somehow got NET instead of GROSS
5. Everyone else got wrong calculations

---

## ✅ THE FIX

Update the sync script to:
1. **Read all 3 columns:** K, L, M
2. **Sum them for wage:** wage = K + L + M (GROSS)
3. **Direct mapping:**
   - ueipab_salary_base = K
   - ueipab_bonus_regular = M
   - ueipab_extra_bonus = L

**DO NOT calculate 70/25/5** - use the actual K, L, M values from spreadsheet!

---

## 📊 VERIFICATION

After fix, ARCIDES should have:
```
wage:                 $574.92 ✓ (K+L+M GROSS)
ueipab_salary_base:   $285.39 ✓ (K - Basic)
ueipab_bonus_regular: $289.52 ✓ (M - Major Bonus)
ueipab_extra_bonus:   $  0.00 ✓ (L - Other Bonus)

Payslip (15 days = 50%):
  Base:  $285.39 × 50% = $142.70
  Bonus: $289.52 × 50% = $144.76
  Extra: $  0.00 × 50% = $  0.00
  Cesta: $ 40.00 × 50% = $ 20.00
  ────────────────────────────────
  GROSS (15 days):       $307.46
  Deductions (~4.3%):    -$13.22
  ────────────────────────────────
  NET (15 days):         $294.24
  NET (30 days):         $588.48... wait, this doesn't match Column Z ($549.94)
```

Hmm, something still doesn't add up. Let me recalculate...

Actually, the Cesta Ticket ($40) is SEPARATE from K+L+M:
```
K+L+M (GROSS salary): $574.92
Cesta Ticket:         $ 40.00
──────────────────────────────────
Total GROSS:          $614.92
Deductions on K+L+M:  -$ 24.98 (4.3%)
Cesta (no deductions): $ 40.00
──────────────────────────────────
NET:                  $549.94 + $40.00 = $589.94?
```

Still doesn't match. Need to understand deduction calculation better.

---

## ❓ REMAINING QUESTIONS

1. **Cesta Ticket:** Is the $40 cesta ticket INCLUDED in M or SEPARATE?
2. **Deductions:** Are deductions applied to K+L+M or only K?
3. **NET Calculation:** How does Column Z calculate to $549.94?

**Status:** Mapping clarified, but need to verify deduction calculations
**Next Step:** Update sync script with corrected K, L, M mapping
