# Deduction Rules Bug - November 10, 2025

**Status:** 🚨 CRITICAL BUG IDENTIFIED

---

## 🎯 THE PROBLEM

SLIP/239 (NELCI BRITO) shows NET = **$169.32** but spreadsheet Column Y shows **$153.91**

**Root Cause:** Deduction rules are applying deductions to **K+M+L** when they should **ONLY apply to K**!

---

## 📋 CURRENT (WRONG) FORMULAS

All deduction rules use this pattern:

```python
# Calculate salary base from previous rules
salary_base = 0.0
if VE_SALARY_70:
    salary_base += VE_SALARY_70  # K
if VE_BONUS_25:
    salary_base += VE_BONUS_25   # M ← WRONG! Should NOT include
if VE_EXTRA_5:
    salary_base += VE_EXTRA_5    # L ← WRONG! Should NOT include

# Apply deduction rate
result = -(salary_base * RATE)
```

---

## 🔍 IMPACT ON NELCI BRITO

### Current Calculation (WRONG):
```
VE_SALARY_70 (K):  $70.18
VE_BONUS_25 (M):   $88.47
VE_EXTRA_5 (L):    $0.00
───────────────────────────
salary_base:       $158.65  ← K+M+L

SSO 2.25%:   $158.65 × 0.0225 = $3.57
FAOV 0.5%:   $158.65 × 0.005  = $0.79
Paro 0.125%: $158.65 × 0.00125 = $0.20
ARI 3%:      $158.65 × 0.03    = $4.76
────────────────────────────────────────
TOTAL DEDUCTIONS:            $9.32
```

### Correct Calculation (from spreadsheet):
```
K ONLY:  $70.18

SSO 2.25%:   $70.18 × 0.0225 = $1.58
FAOV 0.5%:   $70.18 × 0.005  = $0.35
INCES 0.125%: $70.18 × 0.00125 = $0.09
ARI 0.5%:    $70.18 × 0.005  = $0.35  ← RATE IS WRONG TOO!
────────────────────────────────────────
TOTAL DEDUCTIONS:            $2.37
```

**Deductions are 4× too high!** ($9.32 vs $2.37)

---

## ✅ THE FIX

### 1. Fix Formula Base (All Deduction Rules)

**Change FROM:**
```python
salary_base = 0.0
if VE_SALARY_70:
    salary_base += VE_SALARY_70
if VE_BONUS_25:
    salary_base += VE_BONUS_25
if VE_EXTRA_5:
    salary_base += VE_EXTRA_5
```

**Change TO:**
```python
# Deductions apply ONLY to Column K (Basic Salary)
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
```

### 2. Fix ARI Rate

**VE_ARI_DED:**
- Current rate: **3%** (0.03)
- Correct rate: **0.5%** (0.005)

**Change FROM:**
```python
result = -(salary_base * 0.03)
```

**Change TO:**
```python
result = -(salary_base * 0.005)
```

### 3. Add INCES Deduction (Missing)

The spreadsheet shows **INCES 0.25%** but Odoo doesn't have VE_INCES_DED rule!

**Create new rule:** VE_INCES_DED
```python
# Venezuelan INCES: 0.125% bi-monthly on K only
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.00125)
```

---

## 📊 AFFECTED RULES

Need to update these 4 rules + create 1 new:

| Rule Code      | Name                     | Current Rate | Correct Rate | Fix Needed          |
|----------------|--------------------------|--------------|--------------|---------------------|
| VE_SSO_DED     | SSO                      | 2.25%        | 2.25%        | Base formula only   |
| VE_FAOV_DED    | FAOV                     | 0.5%         | 0.5%         | Base formula only   |
| VE_PARO_DED    | Paro Forzoso             | 0.125%       | 0.125%       | Base formula only   |
| VE_ARI_DED     | ARI SENIAT               | 3% ❌        | 0.5% ✓       | Base formula + rate |
| VE_INCES_DED   | INCES (Missing!)         | N/A          | 0.125%       | CREATE NEW RULE     |

---

## 🔧 HOW TO FIX IN ODOO

### Option 1: Via Odoo UI (RECOMMENDED)

1. Go to **Payroll → Configuration → Rules**
2. Filter: Structure = "UEIPAB Venezuelan Payroll"
3. Edit each deduction rule (VE_SSO_DED, VE_FAOV_DED, VE_PARO_DED, VE_ARI_DED)
4. Update Python Code to use ONLY VE_SALARY_70
5. Fix ARI rate from 0.03 to 0.005
6. Create new INCES rule with 0.00125 rate
7. Recompute all November payslips

### Option 2: Via SQL

```sql
-- Fix VE_SSO_DED
UPDATE hr_salary_rule SET
    amount_python_compute = '# Venezuelan SSO: 2.25% bi-monthly on K only
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.0225)'
WHERE code = 'VE_SSO_DED';

-- Fix VE_FAOV_DED
UPDATE hr_salary_rule SET
    amount_python_compute = '# Venezuelan FAOV: 0.5% bi-monthly on K only
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.005)'
WHERE code = 'VE_FAOV_DED';

-- Fix VE_PARO_DED
UPDATE hr_salary_rule SET
    amount_python_compute = '# Venezuelan PARO: 0.125% bi-monthly on K only
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.00125)'
WHERE code = 'VE_PARO_DED';

-- Fix VE_ARI_DED (rate AND base)
UPDATE hr_salary_rule SET
    amount_python_compute = '# Venezuelan ARI: 0.5% bi-monthly on K only
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.005)'
WHERE code = 'VE_ARI_DED';
```

---

## 📝 USER CONFIRMATION

From earlier conversation, user said:

> "total salary structure are only 3 columns (K, L, M) because of column N to S are deductions that **only could be applied to column K**"

This confirms:
- ✓ Deductions ONLY on K (Basic Salary)
- ✗ NO deductions on M (Major Bonus) or L (Other Bonus)

---

## ✅ EXPECTED RESULT AFTER FIX

### NELCI BRITO SLIP/239:

**Gross:**
- K × 50%: $70.18
- M × 50%: $88.47
- L × 50%: $0.00
- Cesta: $20.00
- **Total: $178.65** ✓

**Deductions (on K only):**
- SSO 2.25%: $1.58
- FAOV 0.5%: $0.35
- Paro 0.125%: $0.09
- ARI 0.5%: $0.35
- INCES 0.125%: $0.09
- **Total: $2.46** (close to spreadsheet $2.37)

**NET:**
- $178.65 - $2.46 = **$176.19**

**But wait...** Spreadsheet Column Y says **$153.91**!

Let me recalculate:
- Spreadsheet gross (K+L+M) × 50% = $158.64 (doesn't include cesta!)
- Deductions: $2.37
- NET: $158.64 - $2.37 = $156.27

Still doesn't match $153.91...

**Need to clarify with user:**
1. Should cesta ticket be included in gross or separate?
2. Is cesta subject to deductions?
3. What's the formula for Column Y exactly?

---

**Date:** November 10, 2025
**Priority:** CRITICAL
**Status:** Fix identified, awaiting user clarification on cesta treatment
