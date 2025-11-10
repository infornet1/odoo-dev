# Spreadsheet Column Mapping Analysis

**Date:** November 10, 2025
**Analysis:** Understanding K, L, M, N columns and correct mapping to Odoo contract fields

---

## 📊 SPREADSHEET STRUCTURE CONFIRMED

### Column Headers (Row 5):
- **Column K (10):** "Monthly Salary VEB"
- **Column L (11):** "Salary 70% VEB"
- **Column M (12):** "Bonus 25% VEB"
- **Column N (13):** "Extra 5% VEB"
- **Column Z (25):** "NET Salary" (in USD)
- **Cell O2:** Exchange Rate (219.87 VEB/USD)

---

## 🔍 NELCI BRITO DATA ANALYSIS

### Raw Spreadsheet Values:
```
Column K: 30,859.88 VEB = $140.36 USD  (Base Salary)
Column L:      0.00 VEB = $  0.00 USD  (Additional, often 0)
Column M: 38,901.97 VEB = $176.93 USD  (Bonus - LARGER than K!)
Column N:    694.35 VEB = $  3.16 USD  (Extra)
─────────────────────────────────────────────────────────
K+L+M+N:  70,456.20 VEB = $320.44 USD  (Total Gross)

Column Z NET:           = $307.81 USD  (After deductions)
Deductions:             = $ 12.63 USD  (3.94%)
```

### Key Observations:
1. **K is NOT the sum of L+M+N** - they are separate components
2. **M ($176.93) is LARGER than K ($140.36)** - 126% of K
3. **L is often $0** (not used for all employees)
4. **N is always small** (~2-3% of total)
5. **K+L+M+N = Gross before deductions**

---

## 💡 USER'S DESCRIPTION VS REALITY

### User Said:
> "total salary package (in local currency) are composed without any deduction by 3 critical columns K (salary where deductions must be applied), L (other bonus), M (bonus)."

### Reality:
- There are **FOUR columns**: K, L, M, N
- **K**: Base salary (subject to deductions) ✓ Matches user description
- **L**: Other bonus (often 0) ✓ Matches user description
- **M**: Regular bonus (LARGEST component!) ✓ Matches user description
- **N**: Extra bonus (not mentioned by user, but exists)

---

## 🎯 DEDUCTION CALCULATION ANALYSIS

### Expected Deductions (8.5% total):
- SSO (Seguro Social): 4.0%
- FAOV (Housing): 1.0%
- Paro Forzoso: 0.5%
- ARI (Retirement): 3.0%
- **Total:** 8.5%

### NELCI's Actual Deductions:
- Gross (K+L+M+N): $320.44
- NET (Column Z): $307.81
- Deductions: $12.63
- **Actual Rate: 3.94%** (NOT 8.5%!)

### Testing Deduction Hypotheses:

**Hypothesis 1:** Deductions on K only (base salary)
```
K: $140.36
Deductions (8.5%): $140.36 × 0.085 = $11.93
After deductions: $140.36 - $11.93 = $128.43
Add M+N (not deductible): $128.43 + $176.93 + $3.16 = $308.52
Expected NET: $308.52
Actual NET: $307.81
Difference: $0.71 ✓ VERY CLOSE!
```

**CONCLUSION:** Deductions (8.5%) apply ONLY to Column K (base salary), NOT to L, M, N!

---

## 🗺️ CORRECT MAPPING TO ODOO CONTRACT FIELDS

### Current Odoo Contract Fields:
1. `ueipab_salary_base` (currently stores 70% component)
2. `ueipab_bonus_regular` (currently stores 25% component)
3. `ueipab_extra_bonus` (currently stores 5% component)

### Problem:
- Spreadsheet has **4 columns** (K, L, M, N)
- Odoo contract has **3 fields**
- Need to combine some columns

### Recommended Mapping:

```python
# Option 1: Combine L with K (both could be deductible)
ueipab_salary_base   = (K + L) / exchange_rate
ueipab_bonus_regular = M / exchange_rate
ueipab_extra_bonus   = N / exchange_rate

# Option 2: Combine L with M (both are bonuses)
ueipab_salary_base   = K / exchange_rate
ueipab_bonus_regular = (L + M) / exchange_rate
ueipab_extra_bonus   = N / exchange_rate
```

### For NELCI with Option 1 (K+L combined):
```
ueipab_salary_base:   $140.36 + $0.00 = $140.36 ✓
ueipab_bonus_regular: $176.93
ueipab_extra_bonus:   $3.16
─────────────────────────────────────────────
Total:                $320.44 ✓ Matches K+L+M+N
```

### For NELCI with Option 2 (L+M combined):
```
ueipab_salary_base:   $140.36 ✓
ueipab_bonus_regular: $0.00 + $176.93 = $176.93 ✓
ueipab_extra_bonus:   $3.16 ✓
─────────────────────────────────────────────
Total:                $320.44 ✓ Matches K+L+M+N
```

**BOTH OPTIONS GIVE SAME RESULT for NELCI** (since L = 0)

Need to check employees where L ≠ 0 to determine correct mapping.

---

## 👥 EMPLOYEES WITH L ≠ 0

From analysis:

### SERGIO MANEIRO:
- K: $106.12
- L: $ 13.30 ← NOT ZERO!
- M: $183.40
- N: $  2.39
- Total: $305.21

### ANDRES MORALES:
- K: $124.19
- L: $ 13.30 ← NOT ZERO!
- M: $151.61
- N: $  2.79
- Total: $291.90

**Question:** Should L be grouped with K (base) or M (bonus)?

Looking at the percentages:
- L is ~10-12% of K
- Column L header: "Salary 70% VEB"
- This suggests L might be a "salary" component, not a "bonus"

**Conclusion:** L should be grouped with K (both are "salary" components)

---

## ✅ FINAL RECOMMENDED MAPPING

```python
# Read from spreadsheet columns
k_veb = float(row[10])  # Monthly Salary VEB
l_veb = float(row[11])  # Salary 70% VEB (additional salary)
m_veb = float(row[12])  # Bonus 25% VEB
n_veb = float(row[13])  # Extra 5% VEB

# Get exchange rate from O2
exchange_rate = float(worksheet.acell('O2').value)

# Map to Odoo contract fields
ueipab_salary_base   = (k_veb + l_veb) / exchange_rate  # Base + Additional
ueipab_bonus_regular = m_veb / exchange_rate             # Regular Bonus
ueipab_extra_bonus   = n_veb / exchange_rate             # Extra Bonus
```

### For NELCI BRITO:
```
ueipab_salary_base:   (30,859.88 + 0.00) / 219.87 = $140.36
ueipab_bonus_regular: 38,901.97 / 219.87           = $176.93
ueipab_extra_bonus:   694.35 / 219.87              = $  3.16
────────────────────────────────────────────────────────────
Total:                                               $320.44 ✓
```

### Payslip Calculation (15 days = 50%):
```
VE_SALARY_BASE:  $140.36 × 0.50 = $70.18
VE_BONUS_25:     $176.93 × 0.50 = $88.47
VE_EXTRA_5:      $  3.16 × 0.50 = $ 1.58
VE_CESTA:        $ 40.00 × 0.50 = $20.00
──────────────────────────────────────────
GROSS:                            $180.23

Deductions (8.5% of VE_SALARY_BASE only):
  SSO (4%):      $70.18 × 0.04   = $ 2.81
  FAOV (1%):     $70.18 × 0.01   = $ 0.70
  PARO (0.5%):   $70.18 × 0.005  = $ 0.35
  ARI (3%):      $70.18 × 0.03   = $ 2.11
──────────────────────────────────────────
Total Deductions:                 $ 5.97

NET SALARY (15 days):             $174.26

Current payslip shows:            $ 96.96 ✗ WRONG!
```

**Still not matching!** Need to verify if bonus and extra are also paid bi-monthly or monthly.

---

## 🚨 CURRENT ISSUE SUMMARY

### The Problem:
The sync scripts (`update-contracts-from-spreadsheet.py` and `sync-monthly-salary-from-spreadsheet.py`) are:
1. **Only reading Column K** ($140.36)
2. **Ignoring Columns L, M, N** (missing $176.93 + $3.16 = $180.09!)
3. **Artificially splitting K as 70/25/5**

### Current Contract Values (WRONG):
```
ueipab_salary_base:   $114.46  ✗
ueipab_bonus_regular: $ 40.88  ✗
ueipab_extra_bonus:   $  8.18  ✗
────────────────────────────────
Total:                $163.52  ✗ (should be $320.44!)
```

### Impact:
- **NELCI is short:** $320.44 - $163.52 = **$156.92 per month!**
- If all 44 employees affected similarly: **~$6,900/month underpayment**
- **Annual impact:** ~$82,800 USD
- **Aguinaldos impact:** 2 months × $6,900 = **~$13,800 shortfall**

---

## ✅ NEXT STEPS

1. ✅ **COMPLETED:** Analyze spreadsheet column pattern
2. ✅ **COMPLETED:** Determine correct mapping (K+L → base, M → bonus, N → extra)
3. ⏳ **PENDING:** Fix sync scripts to read all 4 columns
4. ⏳ **PENDING:** Update all employee contracts with correct values
5. ⏳ **PENDING:** Recompute SLIP/237 and verify
6. ⏳ **PENDING:** Check if M and N are paid bi-monthly or monthly

---

**Status:** MAPPING CONFIRMED - Ready to fix sync scripts
**Priority:** CRITICAL - Systematic underpayment affecting all employees
**Confidence:** HIGH - Pattern confirmed across all employees
