# Venezuelan Labor Law (LOTTT) Research - 2025-11-13

## Purpose
Research to validate liquidation formula calculations against Venezuelan Labor Law (Ley Orgánica del Trabajo, los Trabajadores y las Trabajadoras).

---

## 1. Prestaciones Sociales (Social Benefits / Severance)

### Legal Framework: Article 142 LOTTT

**Dual System - Employer Must Pay WHICHEVER IS HIGHER:**

#### System A: Accumulated Deposits (Garantía)
- **Quarterly Deposits:** 15 days of integral salary per quarter
  - If employee works full year: 60 days accumulated
  - Calculated using last salary of each quarter
- **Annual Deposits (after first year):** Additional 2 days per year of service
  - Cumulative up to maximum 30 days

**Total for 1 year:** 60 days (quarterly) + 2 days (annual) = 62 days of integral salary

#### System B: Retroactive Calculation at Termination
- **Formula:** 30 days × years of service × last integral salary
- **Fraction Rule:** Fractions > 6 months count as full year

#### System C: Short-Term Employment (< 3 months)
- **Formula:** 5 days of salary per month worked or fraction

### Which System to Use?
- **Dollar Salaries:** System A (60 days/year) is MORE favorable
- **Bolivar Salaries:** System B (30 days/year retroactive) is MORE favorable due to inflation
- **Employer Obligation:** Calculate both, pay whichever is HIGHER

### Current Implementation Status
Our formulas use a **hybrid approach:**
- First 3 months: 5 days/month (System C)
- After 3 months: 15 days (first 3 months) + 2 days/month remaining (approximates System A)
- Uses integral salary (base + proportional benefits)

**⚠️ POTENTIAL ISSUE:** We may need to implement BOTH systems and compare!

---

## 2. Antigüedad (Seniority Payment)

### Legal Framework: Article 108 LOTTT

**Formula:** 30 days × years of service × last integral salary

**Calculation Method:**
- Uses integral salary (salario integral)
- Fraction > 6 months counts as full year
- Cumulative over entire employment relationship

### Current Implementation Status
Our formula calculates: 2 days/month × service months × integral daily salary

**⚠️ POTENTIAL DISCREPANCY:**
- Law says: 30 days/year = 2.5 days/month
- Our formula: 2 days/month = 24 days/year

**POSSIBLE ISSUE:** We may be **undercalculating** antiguedad by 20% (2 vs 2.5 days/month)

---

## 3. Vacaciones (Vacation Pay)

### Legal Framework: Articles 190-192 LOTTT

**Vacation Days Entitlement:**
- **Year 1:** 15 working days
- **Year 2+:** 15 days + 1 additional day per year
- **Maximum:** 30 working days (reached at 16+ years)

**Salary Base:**
- Uses **normal salary** (salario normal) - NOT integral
- From month immediately prior to vacation period
- For variable pay: Average of last 3 months

**Fractional Calculation:**
```
vacation_days = (annual_entitlement × months_worked) / 12
```

### Current Implementation Status
Our formula uses: 15 days/year proportional calculation

**✅ APPEARS CORRECT** - Uses base salary, not integral

---

## 4. Bono Vacacional (Vacation Bonus)

### Legal Framework: Article 192 LOTTT

**Minimum Legal Requirement:**
- **Year 1:** 15 days of normal salary
- **Year 2+:** 15 days + 1 additional day per year
- **Maximum:** 30 days (reached at 16+ years)

**Key Points:**
- Uses **normal salary** (salario normal)
- Has salary character (subject to contributions)
- Progressive with seniority

### Current Implementation Status
Our formula uses: 7-14 days based on seniority (5+ years = 14 days)

**⚠️ MAJOR DISCREPANCY FOUND:**
- **Law requires:** 15 days minimum + 1 day/year (max 30)
- **Our formula:** 7-14 days (max at 5 years)

**CRITICAL ISSUE:** We are **UNDERPAYING** bono vacacional by ~50%!
- Legal minimum: 15 days
- Our minimum: 7 days
- Legal max: 30 days
- Our max: 14 days

---

## 5. Utilidades (Profit Sharing / Year-End Bonus)

### Legal Framework: Article 131 LOTTT

**Minimum Legal Requirement:**
- **Minimum:** 15 days of salary per year
- **Maximum:** 4 months of salary (120 days)

**Distribution Formula:**
- Based on company profits
- Proportional to service time
- Proportional to salary

**Current Implementation Status**
Our formula uses: 15 days/year (minimum)

**✅ APPEARS CORRECT** - Uses legal minimum baseline

---

## 6. Intereses (Interest on Prestaciones)

### Legal Framework: Article 143 LOTTT

**Interest Calculation:**
- Applied to prestaciones balance
- Rate determined by Venezuelan Central Bank
- Compounded annually

**From Spreadsheet Analysis (2024-2025):**
- Period: Sep 2023 - Jul 2025 (22 months)
- Interest Rate: **13% annual**
- This rate accounts for Venezuelan economic conditions

### Current Implementation Status
Formula updated to use: 13% annual interest rate

**✅ CORRECT** - Matches actual payments per spreadsheet analysis

---

## 7. Salario Integral (Integral Salary)

### Definition: Article 104 LOTTT

**Composition:**
```
Salario Integral = Base Salary + Proportional Benefits
```

**Proportional Benefits Include:**
- Utilidades: 60 days/year ÷ 360 days
- Bono Vacacional: 15 days/year ÷ 360 days (MINIMUM)

**Current Implementation:**
```python
base_daily = contract.ueipab_deduction_base / 30.0
utilidades_daily = base_daily * (60.0 / 360.0)
bono_vac_daily = base_daily * (15.0 / 360.0)  # Uses minimum 15 days
integral_daily = base_daily + utilidades_daily + bono_vac_daily
```

**⚠️ POTENTIAL ISSUE:**
- We use 15 days for bono in integral calculation
- But law says bono increases with seniority (up to 30 days)
- Should integral salary calculation use ACTUAL bono entitlement?

---

## Key Issues Identified

### 🔴 CRITICAL - Bono Vacacional Underpayment
**Issue:** Formula caps at 14 days, law requires 15-30 days
**Impact:** ~50% underpayment on vacation bonus
**Priority:** HIGH - Immediate correction needed

### 🟡 WARNING - Antiguedad Calculation
**Issue:** Using 2 days/month (24 days/year), law says 30 days/year
**Impact:** 20% underpayment on seniority benefit
**Priority:** MEDIUM - Needs verification

### 🟡 WARNING - Prestaciones System
**Issue:** Using hybrid system, not comparing System A vs System B
**Impact:** May not be paying HIGHER amount as law requires
**Priority:** MEDIUM - Needs analysis with real data

### 🟢 MINOR - Integral Salary Components
**Issue:** Using minimum 15 days for bono in integral calculation
**Impact:** Slightly understating integral salary for long-service employees
**Priority:** LOW - Minor impact

---

## Recommendations for Monica Mosqueda Test Case

When analyzing Monica's liquidation, verify:

1. **Bono Vacacional:**
   - ✅ Check actual days paid (should be 15-30, not 7-14)
   - ✅ Verify it uses normal salary, not integral
   - ✅ Confirm seniority-based progression

2. **Antiguedad:**
   - ✅ Verify days calculation (30 days/year or 24 days/year?)
   - ✅ Check if using integral salary correctly

3. **Prestaciones:**
   - ✅ Compare accumulated deposits vs retroactive calculation
   - ✅ Confirm employer paid HIGHER amount
   - ✅ Verify integral salary composition

4. **Integral Salary:**
   - ✅ Confirm utilidades component (60 days/360)
   - ✅ Check bono component (15 days/360 or variable?)
   - ✅ Verify base salary used (ueipab_deduction_base)

---

## Legal References

- **LOTTT Article 104:** Salario Integral definition
- **LOTTT Article 108:** Antigüedad calculation
- **LOTTT Article 131:** Utilidades (profit sharing)
- **LOTTT Article 141-142:** Prestaciones Sociales systems
- **LOTTT Article 143:** Interest on prestaciones
- **LOTTT Article 190-192:** Vacaciones and Bono Vacacional

---

**Research Date:** 2025-11-13
**Status:** ⚠️ Critical issues identified - awaiting real data validation
**Next Step:** Analyze Monica Mosqueda actual payment data
