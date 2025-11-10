# CORRECTED Salary Structure Analysis

**Date:** November 10, 2025
**Status:** ⚠️ REVISED UNDERSTANDING - Previous analysis partially incorrect

---

## 🔍 CORRECTED FINDINGS

After reviewing production `/tmp` documentation and comparing ARCIDES vs NELCI data, here's the CORRECTED understanding:

### Spreadsheet Structure (Confirmed):
- **Column K:** "SALARIO MENSUAL MAS BONO" (Monthly salary plus bonus)
- **Column L:** "OTROS BONOS" (Other bonuses) - often $0
- **Column M:** "CESTA TICKET MENSUAL PTR" - Monthly cesta ticket
- **Columns N-S:** DEDUCTIONS (IVSS, FAOV, INCES, ARI, etc.)
- **Column Z:** NET SALARY (after deductions)

**Total Compensation = K + L + M** (3 columns, not 4!)

---

## 📊 COMPARISON: ARCIDES vs NELCI

### ARCIDES ARZOLA (Row 5):

**Spreadsheet:**
```
Column K: 62,748.90 VEB = $285.39 USD (Salary+Bonus)
Column L:      0.00 VEB = $  0.00 USD (Other Bonus)
Column M: 63,657.77 VEB = $289.52 USD (Cesta Ticket)
────────────────────────────────────────────────────
K+L+M:   126,406.67 VEB = $574.92 USD (GROSS)
Column Z (NET):           $549.94 USD ✓
```

**Current Odoo Contract:**
```
wage:                 $549.94 ✓ MATCHES Column Z (NET)!
ueipab_salary_base:   $204.49
ueipab_bonus_regular: $ 73.03
ueipab_extra_bonus:   $ 14.61
────────────────────────────────────────────────────
Total (70+25+5):      $292.13 ✗ WRONG (should be based on $549.94)
```

**Expected (if wage = $549.94):**
```
ueipab_salary_base:   $549.94 × 0.70 = $384.96
ueipab_bonus_regular: $549.94 × 0.25 = $137.49
ueipab_extra_bonus:   $549.94 × 0.05 = $ 27.50
────────────────────────────────────────────────────
Total:                                $549.94 ✓
```

---

### NELCI BRITO (Row 10):

**Spreadsheet:**
```
Column K:  30,859.88 VEB = $140.36 USD (Salary+Bonus)
Column L:       0.00 VEB = $  0.00 USD (Other Bonus)
Column M:  38,901.97 VEB = $176.93 USD (Cesta Ticket)
────────────────────────────────────────────────────
K+L+M:     69,761.85 VEB = $317.29 USD (GROSS)
Column Z (NET):           $307.81 USD ✓
```

**Current Odoo Contract:**
```
wage:                 $163.52 ✗ Doesn't match K+L+M OR Column Z!
ueipab_salary_base:   $114.46
ueipab_bonus_regular: $ 40.88
ueipab_extra_bonus:   $  8.18
────────────────────────────────────────────────────
Total (70+25+5):      $163.52 ✗ WRONG
```

**Expected (if wage should be K+L+M = $317.29):**
```
ueipab_salary_base:   $317.29 × 0.70 = $222.10
ueipab_bonus_regular: $317.29 × 0.25 = $ 79.32
ueipab_extra_bonus:   $317.29 × 0.05 = $ 15.86
────────────────────────────────────────────────────
Total:                                $317.29 ✓
```

---

## 🎯 KEY DISCOVERIES

###1. ARCIDES is CORRECTLY SYNCED, but 70/25/5 is WRONG
- ✅ `wage` field = $549.94 (matches Column Z NET)
- ✗ The 70/25/5 breakdown ($292.13) is NOT based on wage
- ✗ The 70/25/5 should be: $384.96 / $137.49 / $27.50

### 2. NELCI is COMPLETELY WRONG
- ✗ `wage` field = $163.52 (matches nothing!)
- ✗ Should be either $317.29 (K+L+M) or $307.81 (NET)
- ✗ The 70/25/5 breakdown is also wrong

### 3. Column M is NOT just "cesta ticket"
- ARCIDES M = $289.52 (way more than $40 cesta ticket!)
- NELCI M = $176.93 (also way more than $40!)
- **Column M is a major compensation component, NOT just cesta ticket**

---

## 🤔 CRITICAL QUESTIONS FOR USER

### Question 1: What should the `wage` field represent?

**Option A:** GROSS (K + L + M)
- ARCIDES: $574.92
- NELCI: $317.29

**Option B:** NET (Column Z - after deductions)
- ARCIDES: $549.94 ✓ (currently matches!)
- NELCI: $307.81

### Question 2: How should K, L, M map to custom fields?

**Current Design (from /tmp/venezuelan_payroll_setup.py):**
```python
ueipab_salary_base = wage × 0.70
ueipab_bonus_regular = wage × 0.25  # Comment says "includes Cesta Ticket"
ueipab_extra_bonus = wage × 0.05
```

**But Column M alone is larger than the 25% allocation!**
- ARCIDES: M=$289.52 but 25% of wage=$137.49 (M is 210% of allocated!)
- NELCI: M=$176.93 but 25% of wage=$79.32 (M is 223% of allocated!)

### Question 3: What is Column M really?

The column header says "CESTA TICKET MENSUAL PTR" but the values are:
- ARCIDES: $289.52 (not $40!)
- NELCI: $176.93 (not $40!)
- NORKA: $280.63
- DAVID: $275.88

**These are NOT cesta ticket values - they're major salary components!**

---

## 🔄 POSSIBLE ORIGINAL DESIGN

Based on the production `/tmp/venezuelan_payroll_setup.py` comments:

```python
ueipab_bonus_regular = wage * 0.25  -- 25% regular bonus (includes Cesta Ticket)
cesta_ticket_usd = 40  -- $40 monthly Cesta Ticket
```

This suggests:
1. `ueipab_bonus_regular` was meant to include the $40 cesta ticket as part of the 25%
2. `cesta_ticket_usd` is a SEPARATE field for the $40 legal requirement
3. But Column M values are MUCH larger than 25% allocation

---

## ✅ NEXT STEPS

**BEFORE making ANY changes, we need the user to clarify:**

1. **Spreadsheet Column Meaning:**
   - What does Column K really represent?
   - What does Column L really represent?
   - What does Column M really represent? (It's not just $40 cesta ticket!)

2. **Original Design Intent:**
   - Should `wage` = GROSS (K+L+M) or NET (Column Z)?
   - Was the 70/25/5 split ALWAYS intended?
   - How were ARCIDES and RAFAEL originally set up during testing?

3. **Correct Mapping:**
   - How should K, L, M map to the three custom fields?
   - Is Column M supposed to be part of the 25% bonus, or separate?
   - Where does the $40 cesta ticket fit in?

**Status:** ANALYSIS REVISED - Awaiting user clarification on original design intent
**Priority:** HIGH - Need to understand if ARCIDES is "correct" or also wrong
**Document Version:** 2.0 - CORRECTED ANALYSIS

