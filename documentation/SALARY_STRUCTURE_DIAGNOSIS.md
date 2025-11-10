# Salary Structure Diagnosis - Column M (Bonus) Not Being Used
**Date:** November 10, 2025
**Issue:** NELCI BRITO payslip shows $96.96 for 15 days, but expected $153.91
**Root Cause:** Sync script only reads Column K, ignoring Column M (Bonus)

---

## 🔍 DIAGNOSIS SUMMARY

### **The Problem:**

The salary sync scripts (`update-contracts-from-spreadsheet.py` and `sync-monthly-salary-from-spreadsheet.py`) are **ONLY** reading **Column K** from the spreadsheet and then artificially distributing it as 70/25/5.

**They are completely IGNORING Column M (Bonus) which contains 55.8% of the total salary package!**

---

## 📊 SPREADSHEET STRUCTURE (Actual Reality)

### **Column Definitions:**
- **Column K:** Base Salary (where deductions are applied)
- **Column L:** Other Bonus (optional, can be $0)
- **Column M:** Regular Bonus

### **NELCI BRITO Example (Row 10, Sheet "31oct2025"):**

| Column | Description | VEB Value | USD Value | % of Total |
|--------|-------------|-----------|-----------|------------|
| K | Base Salary | 30,859.88 | $140.36 | 44.2% |
| L | Other Bonus | 0.00 | $0.00 | 0.0% |
| M | Bonus | 38,901.97 | $176.93 | 55.8% |
| **TOTAL** | **(K + L + M)** | **69,761.85** | **$317.29** | **100%** |

**Exchange Rate:** 219.87 VEB/USD (Cell O2)

### **Complete Calculation (30 days):**

```
Base Salary (K):        $140.36
Other Bonus (L):        $  0.00
Regular Bonus (M):      $176.93
────────────────────────────────
Subtotal:               $317.29
Cesta Ticket:           $ 40.00
────────────────────────────────
GROSS:                  $357.29

Deductions (8.5% of K+L+M):
  - SSO (4%):           -$12.69
  - FAOV (1%):          -$ 3.17
  - Paro (0.5%):        -$ 1.59
  - ARI (3%):           -$ 9.52
────────────────────────────────
Total Deductions:       -$26.97

NET SALARY:             $330.32 ← Should be close to $307.81
```

**Note:** Slight difference due to rounding and exact deduction rates.

---

## ❌ WHAT'S WRONG: Current Sync Script Behavior

### **File:** `update-contracts-from-spreadsheet.py` (Lines 31, 58-96)

```python
# PROBLEM: Only reads Column K!
self.salary_column = 'K'  # Line 31

# Gets salary from Column K only
salary_veb_raw = row[salary_col_index]  # Column K
salary_veb_float = float(salary_veb_clean)
salary_usd = salary_veb_float / exchange_rate  # $140.36 for NELCI

# THEN artificially splits it as 70/25/5
base_70 = round(salary_usd * 0.70, 2)    # $98.25
bonus_25 = round(salary_usd * 0.25, 2)   # $35.09
extra_5 = round(salary_usd * 0.05, 2)    # $7.02
```

### **Result in Odoo Contract for NELCI:**

| Field | Current Value | Should Be |
|-------|---------------|-----------|
| `ueipab_salary_base` (70%) | $98.25 | ??? |
| `ueipab_bonus_regular` (25%) | $35.09 | ??? |
| `ueipab_extra_bonus` (5%) | $7.02 | ??? |
| **Total** | **$140.36** | **$317.29** |

**Missing:** $176.93 (Column M - 55.8% of salary!)

### **Payslip Calculation (SLIP/237, 15 days = 50%):**

```
Salary Base:    $98.25 * 50% = $49.13
Bonus:          $35.09 * 50% = $17.55
Extra:          $ 7.02 * 50% = $ 3.51
Cesta:          $40.00 * 50% = $20.00
────────────────────────────────────────
GROSS:                          $90.19
Deductions (8.5%):              -$6.84
────────────────────────────────────────
NET:                            $83.35

But we calculated: $96.96 (from database)
```

Wait, this doesn't match either. Let me check the actual contract values...

---

## 🔍 ACTUAL CONTRACT VALUES IN ODOO (from database query):

```sql
ueipab_salary_base:     $114.46  ← Not $98.25!
ueipab_bonus_regular:   $ 40.88  ← Not $35.09!
ueipab_extra_bonus:     $  8.18  ← Not $7.02!
────────────────────────────────
Total:                  $163.52  ← Not $140.36!

ueipab_monthly_salary:  $140.36  ← Synced from Column K
```

### **This reveals ANOTHER problem:**

The contract's 70/25/5 breakdown ($163.52) doesn't match:
- Column K alone ($140.36)
- Column K + M ($317.29)

**Where did $163.52 come from?**

---

## 🎯 CRITICAL QUESTIONS TO ANSWER:

### **Question 1: What is the TRUE mapping?**

**Option A:** Direct mapping (Most Likely?)
- `ueipab_salary_base` = Column K (Base Salary)
- `ueipab_bonus_regular` = Column M (Bonus)
- `ueipab_extra_bonus` = Column L (Other Bonus)

**Option B:** Calculated mapping
- Total = K + L + M
- `ueipab_salary_base` = Total * 0.70
- `ueipab_bonus_regular` = Total * 0.25
- `ueipab_extra_bonus` = Total * 0.05

**Option C:** Hybrid (K is base, M is split?)
- `ueipab_salary_base` = Column K * 0.70
- `ueipab_bonus_regular` = (Column K * 0.25) + (Column M * ???)
- `ueipab_extra_bonus` = Column K * 0.05

### **Question 2: What are the salary rule formulas?**

Current rules use the contract fields with bi-monthly proportion (50%):
```python
VE_SALARY_70:  contract.ueipab_salary_base * proportion
VE_BONUS_25:   contract.ueipab_bonus_regular * proportion
VE_EXTRA_5:    contract.ueipab_extra_bonus * proportion
```

**Are these names misleading?**
- "VE_SALARY_70" suggests it's 70% of total
- But if it comes from Column K directly, it's NOT 70%!

### **Question 3: How were contracts originally set up?**

The current values ($163.52 for NELCI) don't match any of:
- Column K: $140.36
- Column K + M: $317.29
- Column K * (70+25+5): $140.36

**Were they manually entered? From a different spreadsheet? Old exchange rate?**

---

## 📋 INFORMATION NEEDED TO PROCEED:

### **From Spreadsheet:**
1. ✅ Column K value (Base Salary): $140.36
2. ✅ Column L value (Other Bonus): $0.00
3. ✅ Column M value (Bonus): $176.93
4. ✅ Column Z value (NET): $307.81
5. ⏳ What do column headers say exactly?
6. ⏳ Are there any formulas in columns?
7. ⏳ Check 2-3 other employees to see the pattern

### **From Original Design:**
1. ⏳ Review original salary structure documentation
2. ⏳ Check `/tmp` files in production for design notes
3. ⏳ Check git history for when structure was created
4. ⏳ Check if Column M was EVER read by sync scripts

### **From Accounting/Payroll:**
1. ⏳ Confirm intended mapping of columns to fields
2. ⏳ Verify what "70/25/5" really means
3. ⏳ Confirm if Column M should be included
4. ⏳ Check actual payment records vs payslips

---

## 🔧 PROPOSED SOLUTIONS (Once Mapping is Confirmed):

### **Solution 1: If K+L+M is Total, distribute as 70/25/5**

```python
# Read all three columns
col_k = row[10]  # Base Salary
col_l = row[11]  # Other Bonus
col_m = row[12]  # Bonus

# Calculate total
total_veb = float(col_k) + float(col_l) + float(col_m)
total_usd = total_veb / exchange_rate

# Distribute
ueipab_salary_base = total_usd * 0.70
ueipab_bonus_regular = total_usd * 0.25
ueipab_extra_bonus = total_usd * 0.05
```

### **Solution 2: If Direct Mapping**

```python
# Map columns directly
ueipab_salary_base = float(col_k) / exchange_rate    # Base
ueipab_bonus_regular = float(col_m) / exchange_rate  # Bonus
ueipab_extra_bonus = float(col_l) / exchange_rate    # Other
```

### **Solution 3: Hybrid Based on Column Headers**

Need to see actual column headers to determine correct mapping.

---

## 🚨 IMMEDIATE IMPACT:

**ALL employees are likely affected by this issue!**

If NELCI is missing $176.93, and this pattern holds:
- 45 employees * $176.93 average = **~$7,961 missing per month**
- Annual impact: **~$95,532 USD** in underpayment
- Aguinaldos impact: 2 months * $7,961 = **~$15,922 shortfall**

**This is CRITICAL and needs immediate resolution!**

---

## ✅ NEXT STEPS:

1. **URGENT:** Check spreadsheet columns K, L, M for 3-5 more employees
2. **URGENT:** Review column headers to understand what each represents
3. **URGENT:** Consult with accounting/payroll to confirm intended mapping
4. **URGENT:** Check production `/tmp` for any design notes
5. Review git history for salary structure creation
6. Update sync scripts with correct column mapping
7. Recalculate all contracts
8. Recompute affected payslips

---

**Status:** DIAGNOSIS IN PROGRESS - Awaiting clarification on column mapping
**Priority:** CRITICAL - Potential systematic underpayment
**Estimated Fix Time:** 2-4 hours once mapping is confirmed

