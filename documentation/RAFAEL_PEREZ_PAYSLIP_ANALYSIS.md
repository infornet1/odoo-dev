# Rafael Perez Payslip Analysis (SLIP/240)

**Date:** November 10, 2025
**Payslip:** SLIP/240
**Period:** November 1-15, 2025 (15 days)

---

## 🔍 Issue Found: Small Difference

**Odoo NET:** $196.29
**Spreadsheet Column Y:** $195.70
**Difference:** **$0.59** ⚠️

---

## 📊 Contract Values (Monthly)

| Component | Odoo | Spreadsheet | Match |
|-----------|------|-------------|-------|
| **K (Salary Base)** | $119.09 | $119.09 | ✓ |
| **M (Bonus Regular)** | $230.32 | $230.32 | ✓ |
| **L (Extra Bonus)** | $51.21 | $51.21 | ✓ |
| **Total Wage** | $400.62 | $400.62 | ✓ |

---

## 💰 Bi-Weekly Gross (15 days)

| Component | Odoo | Spreadsheet | Match |
|-----------|------|-------------|-------|
| **K × 50%** | $59.55 | $59.54 | ≈ $0.01 rounding |
| **M × 50%** | $115.16 | $115.16 | ✓ |
| **L × 50%** | $25.61 | $25.61 | ✓ |
| **Cesta Ticket** | $0.00 | $0.00 | ✓ |
| **TOTAL GROSS** | $200.31 | $200.31 | ✓ |

---

## 📉 Deductions Analysis

### Spreadsheet Deductions (Monthly)
```
N (SSO):     $2.68
O (FAOV):    $0.60
P (INCES):   $0.15
Q (Ref):     $0.00
R (ARI):     $1.19  ← NOTE: Higher than Odoo!
S (Other):   $0.00
─────────────────
TOTAL:       $4.61
```

### Odoo Deductions (Bi-weekly on K only)
```
VE_SSO_DED (4.5%):   -$2.68  ✓ (59.55 × 0.045)
VE_FAOV_DED (1%):    -$0.60  ✓ (59.55 × 0.01)
VE_PARO_DED (0.25%): -$0.15  ✓ (59.55 × 0.0025)
VE_ARI_DED (1%):     -$0.60  ⚠️ (59.55 × 0.01)
─────────────────────
TOTAL:               -$4.02
```

---

## 🎯 Root Cause: ARI Deduction Rate

**Issue:** ARI deduction is different

### Spreadsheet ARI (Monthly):
- Amount: $1.19
- Base: K monthly = $119.09
- Rate: $1.19 ÷ $119.09 = **1.00%**

### Odoo ARI (Applied to bi-weekly):
- Amount: $0.60
- Base: K bi-weekly = $59.55
- Rate: 1% (DOUBLED from 0.5%)
- Calculation: $59.55 × 0.01 = **$0.60**

### Expected if following spreadsheet:
- K bi-weekly: $59.55
- ARI 2%: $59.55 × 0.02 = **$1.19**

---

## 🔍 Detailed Calculation

### Spreadsheet Formula: (Salary ÷ 2) - MONTHLY Deductions
```
Gross bi-weekly:  $200.31
Deductions:       -$4.61  (MONTHLY, not divided)
──────────────────
NET:              $195.70
```

### Odoo Current Formula:
```
Gross bi-weekly:  $200.31
Deductions:       -$4.02  (DOUBLED rates on bi-weekly K)
──────────────────
NET:              $196.29
```

### Difference Breakdown:
```
Spreadsheet deductions: $4.61
Odoo deductions:        $4.02
──────────────────────────
Difference:             $0.59

Where does $0.59 come from?
- ARI in spreadsheet: $1.19
- ARI in Odoo:        $0.60
- Difference:         $0.59  ← This is the issue!
```

---

## 🔧 Analysis of ARI Rate

### Current Odoo Configuration:
```python
# VE_ARI_DED rule
# Venezuelan ARI: 1% on K (Basic Salary) ONLY
# DOUBLED from 0.5% to apply FULL MONTHLY deduction in bi-weekly payslip
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.01)
```

This gives:
- K bi-weekly: $59.55
- ARI 1%: $59.55 × 0.01 = $0.60

### What spreadsheet shows:
- K monthly: $119.09
- ARI: $1.19
- Rate: 1.19 ÷ 119.09 = **1.00%** monthly

When applied to bi-weekly following our formula (DOUBLED):
- K bi-weekly: $59.55
- ARI 2%: $59.55 × 0.02 = $1.19 ✓

---

## ⚠️ CRITICAL FINDING

**ARI rate should be 2% (DOUBLED from 1%), not 1%!**

All other deductions were correctly DOUBLED:
- SSO: 2.25% → 4.5% ✓
- FAOV: 0.5% → 1% ✓
- Paro: 0.125% → 0.25% ✓
- ARI: 0.5% → 1% ❌ (should be 2%)

---

## 🔧 Fix Required

### Current VE_ARI_DED formula:
```python
# WRONG: Should be 2%, not 1%
result = -(salary_base * 0.01)
```

### Correct VE_ARI_DED formula:
```python
# Venezuelan ARI: 2% on K (Basic Salary) ONLY
# DOUBLED from 1% to apply FULL MONTHLY deduction in bi-weekly payslip
# Spreadsheet applies monthly deductions to each bi-weekly payment
salary_base = VE_SALARY_70 if VE_SALARY_70 else 0.0
result = -(salary_base * 0.02)
```

---

## 📊 Verification After Fix

### With ARI at 2%:
```
Gross:         $200.31
Deductions:
  SSO 4.5%:    $2.68
  FAOV 1%:     $0.60
  Paro 0.25%:  $0.15
  ARI 2%:      $1.19  ← Fixed!
  ─────────────────
  TOTAL:       $4.61  ← Now matches spreadsheet!

NET: $200.31 - $4.61 = $195.70 ✓
```

---

## 🎯 Impact Assessment

### Employees Affected:
- ALL 43 employees with bi-weekly payslips
- Underpaying by ARI difference (approx $0.50-$0.60 per employee per payslip)

### Past Payslips:
- NOT affected (finalized before fix)
- Only future payslips will use corrected rate

### NELCI BRITO (our reference test):
- Current NET: $153.91
- With ARI 2%: Need to verify if still $153.91 or different

Let me check NELCI's ARI calculation...

**NELCI Contract:**
- K monthly: $140.36
- K bi-weekly: $70.18
- ARI 1%: $0.70 (current)
- ARI 2%: $1.40 (corrected)
- Difference: $0.70

**NELCI Current NET:** $153.91
**NELCI Corrected NET:** $153.91 - $0.70 = $153.21

**⚠️ WARNING:** This would break NELCI's match to spreadsheet!

Need to verify NELCI's spreadsheet ARI amount...

---

## 🔍 Next Steps

1. **Verify NELCI's ARI in spreadsheet**
   - Check if NELCI's spreadsheet shows 1% or 2% ARI
   - Determine if ARI rate is employee-specific or universal

2. **Check other employees**
   - Verify 2-3 more employees against spreadsheet
   - Determine if ARI rate varies by employee

3. **Update VE_ARI_DED formula** (if confirmed universal)
   - Change from 1% to 2%
   - Create backup before change
   - Recompute test payslips

4. **Alternative:** ARI might be variable rate
   - Some employees: 1%
   - Other employees: 2%
   - Need to check spreadsheet pattern

---

## 📝 Recommendation

**Before fixing ARI rate globally:**

1. Check NELCI BRITO's spreadsheet ARI
2. Check 3-5 more employees
3. Determine if rate is:
   - Universal 2% for all
   - Variable per employee
   - Different for some reason

**If universal 2%:**
- Update VE_ARI_DED formula
- Retest all reference employees
- Update documentation

**If variable:**
- May need employee-specific ARI rate field
- More complex fix required

---

**Status:** ⚠️ ISSUE IDENTIFIED - Awaiting Decision
**Date:** November 10, 2025
**Document Version:** 1.0
