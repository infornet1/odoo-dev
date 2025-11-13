# Liquidation Formula - Clarifications & Updates

**Date:** 2025-11-12
**Status:** Awaiting final confirmation before implementation

---

## Clarifications Requested

### 1. ✅ Bono Vacacional Rate - CONFIRMED
**Question:** Confirmed 14 days/year for 5+ years seniority?

**Answer:** ✅ **CONFIRMED**

**Implementation:**
```python
# Seniority-based bono vacacional rate
if total_seniority_years >= 5:
    annual_bono_days = 14.0
else:
    annual_bono_days = 7.0 + (total_seniority_years * 1.4)

# Applied proportionally to period owed
bono_days = period_years * annual_bono_days
```

**Example (Virginia Verde):**
- Total seniority: 5.92 years (from Oct 1, 2019)
- Rate: 14 days/year (≥ 5 years)
- Period owed: 1 year (Aug 1, 2024 - Jul 31, 2025)
- Calculation: 1 year × 14 days = 14 days

---

### 2. ✅ Utilidades - CONFIRMED
**Question:** Always 15 days minimum?

**Answer:** ✅ **CONFIRMED - 15 days minimum**

**Implementation:**
```python
# Calculate utilidades based on service period
service_years = service_months / 12.0
utilidades_days = service_years * 15.0

# Cap at maximum (4 months = 120 days)
if utilidades_days > 120.0:
    utilidades_days = 120.0
```

**Note:** 15 days is the legal minimum. Actual profit sharing may be higher based on company profits, but formulas will use minimum unless manually adjusted.

---

### 3. ✅ Interest Rate - CONFIRMED FROM SPREADSHEET
**Question:** What % interest rate should be used for Intereses (Interest on Prestaciones)?

**Spreadsheet Analyzed:** `1-lSovpboNcKli9_qlYe1i8DTXajIR8QBUiKuhaDNZfU`
**Title:** "INTERESES DE PRESTACIONES SOCIALES PERIODO ESCOLAR 2024-2025"

**Analysis Results:**

| Employee | Prestaciones | Interest | Total Rate | Annual Rate (22m) |
|----------|-------------|----------|------------|-------------------|
| Virginia Verde | $871.24 | $213.18 | 24.47% | **13.3%** |
| Gabriel España | $656.09 | $160.54 | 24.47% | **13.3%** |
| Dixia Bellorin | $593.15 | $145.14 | 24.47% | **13.3%** |

**Calculation:**
- Period: September 2023 to July 2025 = 22 months = 1.83 years
- Total Interest: 24.47% over 22 months
- Annual Rate: 24.47% ÷ 1.83 = **13.3% per year**

**Answer:** ✅ **CONFIRMED - Use 13% annual interest rate**

**Note:** This is significantly higher than the 3% assumption. Venezuelan inflation and economic conditions justify this higher rate.

---

### 4. ❓ Aug 1 Payment Dates - NEEDS CLARIFICATION
**Question:** Are vacation/bono payments ALWAYS on August 1, or can they vary by employee?

**Context:**
- Fiscal year: Sep 1 - Aug 31
- Typical payment: Aug 1 of each year
- Vacation period: Previous 12 months (Sep-Jul)

**Scenarios:**
```
A. FIXED DATE (Aug 1 for everyone)
   - All employees paid Aug 1, 2024
   - All employees paid Aug 1, 2025
   - Simplest to implement

B. VARIABLE DATES (per employee)
   - Employee A: Aug 1, 2024
   - Employee B: Aug 5, 2024
   - Employee C: Jul 28, 2024
   - Requires tracking individual dates

C. ANNIVERSARY-BASED (on hire date anniversary)
   - Hired Oct 1 → Payment Oct 1 each year
   - Hired Mar 15 → Payment Mar 15 each year
   - Complex, less common
```

**❓ NEED USER INPUT:** Which scenario applies to your school?

**Working Assumption:** Scenario A (Fixed Aug 1 date for all employees)

---

## Implementation Plan - UPDATED

### ✅ CONFIRMED Items
1. Bono Vacacional: 14 days/year for 5+ years seniority
2. Utilidades: Always 15 days minimum
3. Approach 2: Use contract.date_start as liability start
4. Critical Fix: Change all contracts from Sep 1, 2024 → Sep 1, 2023

### ⚠️ PENDING Items
1. **Interest Rate %** - Need to access Google Sheet or get confirmation
2. **Aug 1 Payment Rule** - Fixed date or variable per employee?

---

## Recommended Next Steps

### Option A: Proceed with Assumptions
**If you approve, we can proceed with:**
- Interest Rate: 3% annual
- Vacation Payment: Aug 1 fixed date for all employees
- Can adjust later if needed

**Timeline:**
- Phase 1: Fix contract dates (30 minutes)
- Phase 2: Add new fields (1 hour)
- Phase 3: Update formulas (2 hours)
- Phase 4: Testing (1 hour)
- **Total: ~4.5 hours**

### Option B: Wait for Clarifications
**If you prefer, we can wait until:**
- Google Sheet analyzed for interest rate
- Aug 1 payment rule confirmed
- Then proceed with exact values

**Timeline:**
- Clarifications received
- Then 4.5 hours implementation

---

## Current Status Summary

| Item | Status | Value/Decision |
|------|--------|----------------|
| Approach | ✅ Confirmed | Approach 2 (contract.date_start = liability start) |
| Contract Date Fix | ✅ Ready | Sep 2024 → Sep 2023 (all employees) |
| Bono Vacacional | ✅ Confirmed | 14 days/year for 5+ years |
| Utilidades | ✅ Confirmed | 15 days minimum |
| Interest Rate | ✅ Confirmed | **13% annual** (from spreadsheet analysis) |
| Aug 1 Payment | ⚠️ Pending | Fixed date or variable? |
| New Fields | ✅ Ready | 3 fields designed and documented |
| Formula Updates | ✅ Ready | 3 formulas ready to implement |

---

## Questions for User

### 1. Google Spreadsheet Access
**Please provide ONE of the following:**

**Option A:** Location of credentials
```bash
# Where is the odoo_api_bridge directory?
# Full path: /path/to/odoo_api_bridge
```

**Option B:** Interest rate from spreadsheet
```
# What is the annual interest rate shown in the sheet?
# Example: 3%, 2.5%, 4%, etc.
```

**Option C:** Approval to use assumption
```
# Approve using 3% for now?
# Can be changed later in formula
```

### 2. Vacation Payment Dates
**Please confirm:**

**Fixed Date Scenario:**
```
All employees receive vacation payment on August 1 each year
□ YES - Use Aug 1 as fixed date
□ NO - It varies (explain below)
```

**If variable:**
```
How is the payment date determined?
- By employee anniversary?
- By department?
- By other rule?
```

---

## Awaiting User Confirmation

**To proceed with implementation, please provide:**

1. ✅ Interest rate (from sheet, or approve 3% assumption)
2. ✅ Aug 1 payment rule (fixed or variable)

**OR approve to proceed with assumptions:**
- Interest: 3% annual
- Payment: Aug 1 fixed date

**Once confirmed, implementation can begin immediately.**

---

**Document Status:** Awaiting clarifications
**Prepared by:** Claude Code
**Date:** 2025-11-12
