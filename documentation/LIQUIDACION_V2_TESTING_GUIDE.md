# Liquidación Venezolana V2 - UI Testing Guide

**Date:** 2025-11-16
**Status:** ✅ V2 STRUCTURE CREATED - READY FOR UI TESTING

---

## Implementation Complete ✅

**Liquidación Venezolana V2** has been successfully created with all 14 salary rules.

**Structure Details:**
- **Name:** Liquidación Venezolana V2
- **Code:** LIQUID_VE_V2
- **ID:** 10
- **Parent:** None (Independent) ✅
- **Total Rules:** 14
- **Accounting:** 5.1.01.10.010 (Debit) / 2.1.01.10.005 (Credit)

---

## Key Changes from V1

| Aspect | V1 (Old) | V2 (New) |
|--------|----------|----------|
| **Salary Field** | `ueipab_deduction_base` | `ueipab_salary_v2` ✅ |
| **Field Type** | Calculated (~42% of wage) | Direct HR-approved amount ✅ |
| **Clarity** | Percentage-based | Transparent direct value ✅ |
| **Accounting** | 5.1.01.10.002 / 2.1.01.10.005 | **5.1.01.10.010** / 2.1.01.10.005 ✅ |

---

## Test Employees (All Ready)

All 3 test employees have complete V2 contract data and historical tracking fields:

### 1. VIRGINIA VERDE (Most Complex)
- **Employee ID:** 613
- **Department:** Docentes
- **Wage:** $389.37

**V2 Fields:**
- `ueipab_salary_v2`: $146.19
- `ueipab_extrabonus_v2`: $0.00
- `ueipab_bonus_v2`: $203.19
- `cesta_ticket_usd`: $40.00

**Historical Tracking:**
- `ueipab_original_hire_date`: **2019-10-01** (6.17 years seniority)
- `ueipab_previous_liquidation_date`: 2023-07-31
- `ueipab_vacation_paid_until`: 2024-08-01

**Expected Results:**
- **Bono Vacacional Rate:** 20.2 days/year (progressive for 6+ years)
- **Antiguedad:** Uses original hire date, subtracts previous liquidation period
- **Prepaid Deduction:** YES (received Aug 1 payment)

---

### 2. GABRIEL ESPAÑA (Medium Complexity)
- **Employee ID:** 582
- **Department:** Operaciones
- **Wage:** $354.95

**V2 Fields:**
- `ueipab_salary_v2`: $151.56
- `ueipab_extrabonus_v2`: $0.00
- `ueipab_bonus_v2`: $163.38
- `cesta_ticket_usd`: $40.00

**Historical Tracking:**
- `ueipab_original_hire_date`: **2023-04-14** (2.63 years seniority)
- `ueipab_previous_liquidation_date`: 2023-07-31
- `ueipab_vacation_paid_until`: 2024-08-01

**Expected Results:**
- **Bono Vacacional Rate:** 16.6 days/year (progressive for 2+ years)
- **Antiguedad:** Uses original hire date, subtracts previous liquidation period
- **Prepaid Deduction:** YES (received Aug 1 payment)

---

### 3. DIXIA BELLORIN (Long Seniority)
- **Employee ID:** 577
- **Department:** Docentes
- **Wage:** $307.33

**V2 Fields:**
- `ueipab_salary_v2`: $127.66
- `ueipab_extrabonus_v2`: $0.00
- `ueipab_bonus_v2`: $139.67
- `cesta_ticket_usd`: $40.00

**Historical Tracking:**
- `ueipab_original_hire_date`: **2012-09-01** (13.25 years seniority!)
- `ueipab_previous_liquidation_date`: 2023-07-31
- `ueipab_vacation_paid_until`: 2024-08-01

**Expected Results:**
- **Bono Vacacional Rate:** 27.3 days/year (progressive, almost max 30)
- **Antiguedad:** Uses original hire date (265.7 days already paid!)
- **Prepaid Deduction:** YES (received Aug 1 payment)

---

## UI Testing Procedure

### Step 1: Navigate to Payslips

1. Go to **Payroll > Payslips**
2. Click **Create** button

### Step 2: Create Test Liquidation Payslip

**For VIRGINIA VERDE:**
1. Select **Employee:** VIRGINIA VERDE
2. **Contract** will auto-fill: Contract #110
3. **Salary Structure:** Select "**Liquidación Venezolana V2**" ⭐
4. **Period:**
   - **Date From:** 2023-09-01 (contract start)
   - **Date To:** 2025-11-30 (termination date)
5. Click **Save**

### Step 3: Compute Payslip

1. Click **Compute Sheet** button
2. Wait for computation to complete
3. Review the **Salary Computation** tab

### Step 4: Verify V2 Calculations

**Check these key lines:**

| Rule Code | Rule Name | What to Verify |
|-----------|-----------|----------------|
| `LIQUID_SERVICE_MONTHS_V2` | Meses de Servicio | Should show ~27 months |
| `LIQUID_DAILY_SALARY_V2` | Salario Diario Base | Should be **$146.19 ÷ 30 = $4.87**/day ✅ |
| `LIQUID_INTEGRAL_DAILY_V2` | Salario Diario Integral | Should be ~$5.89/day |
| `LIQUID_BONO_VACACIONAL_V2` | Bono Vacacional | Should use **20.2 days/year rate** (6+ years) ✅ |
| `LIQUID_ANTIGUEDAD_V2` | Antigüedad | Should subtract previous liquidation period ✅ |
| `LIQUID_VACATION_PREPAID_V2` | Vacaciones/Bono Prepagadas | Should be **NEGATIVE** (deduction) ✅ |
| `LIQUID_NET_V2` | Liquidación Neta | Final amount to pay |

**Critical Verifications:**

✅ **V2 Salary Field Usage:**
```
LIQUID_DAILY_SALARY_V2 = ueipab_salary_v2 / 30
Expected: $146.19 / 30 = $4.873/day
```

✅ **Original Hire Date Logic:**
```
Bono Vacacional Rate = f(total seniority from 2019-10-01)
6.17 years → 15 + (6.17 - 1) = 20.2 days/year
```

✅ **Previous Liquidation Deduction:**
```
Total Antiguedad from 2019-10-01
MINUS Already Paid (up to 2023-07-31)
= Net Owed
```

✅ **Prepaid Vacation Deduction:**
```
Received Aug 1, 2024 annual payment
Deduction = -(Vacaciones + Bono Vacacional)
Net = Positive benefits - Prepaid deduction
```

### Step 5: Confirm Payslip

1. Click **Confirm** button (DO NOT click if just testing!)
2. **Warning:** Confirming will:
   - Create journal entry
   - Post to accounting (5.1.01.10.010 / 2.1.01.10.005)
   - Change state to "Done"

**For testing:** Just review the computed lines, **DO NOT confirm** unless ready for production.

### Step 6: Repeat for Other Employees

Test the same process with:
- **GABRIEL ESPAÑA** (2.63 years → 16.6 days/year bono rate)
- **DIXIA BELLORIN** (13.25 years → 27.3 days/year bono rate)

---

## Expected Calculation Examples

### VIRGINIA VERDE (Hypothetical Liquidation Nov 30, 2025)

**Service Period:** Sep 1, 2023 → Nov 30, 2025 = 26.97 months

**Daily Rates (V2):**
```
Daily Salary = $146.19 / 30 = $4.873/day
Integral Daily = $4.873 + utilidades_daily + bono_daily = $5.887/day
```

**Benefits:**
```
Vacaciones (15 days/year):
  - From Aug 1, 2024 to Nov 30, 2025 = 16 months
  - Days = (16/12) × 15 = 20 days
  - Amount = 20 × $4.873 = $97.46

Bono Vacacional (20.2 days/year for 6+ years seniority):
  - From Aug 1, 2024 to Nov 30, 2025 = 16 months
  - Days = (16/12) × 20.2 = 26.9 days
  - Amount = 26.9 × $4.873 = $131.08

Utilidades (30 days/year):
  - Service = 26.97 months
  - Days = (26.97/12) × 30 = 67.4 days
  - Amount = 67.4 × $4.873 = $328.44

Prestaciones (15 days/quarter):
  - Quarters = 26.97 / 3 = 8.99
  - Days = 8.99 × 15 = 134.8 days
  - Amount = 134.8 × $5.887 = $793.57

Antiguedad (2 days/month):
  - Total seniority: Oct 1, 2019 → Nov 30, 2025 = 74.97 months
  - Already paid: Oct 1, 2019 → Jul 31, 2023 = 46.0 months
  - Net owed: 74.97 - 46.0 = 28.97 months
  - Days = 28.97 × 2 = 57.9 days
  - Amount = 57.9 × $5.887 = $340.86

Intereses (13% annual on prestaciones):
  - Average balance = $793.57 × 0.5 = $396.79
  - Interest = $396.79 × 0.13 × (26.97/12) = $115.90
```

**Deductions:**
```
FAOV (1% on Vac+Bono+Util):
  - Base = $97.46 + $131.08 + $328.44 = $556.98
  - FAOV = $556.98 × 1% = $5.57

INCES (0.5% on Vac+Bono+Util):
  - INCES = $556.98 × 0.5% = $2.78

Prepaid Deduction:
  - Already received Aug 1, 2024 annual payment
  - Deduction = -($97.46 + $131.08) = -$228.54
```

**Net Liquidation:**
```
Total Benefits = $97.46 + $131.08 + $328.44 + $793.57 + $340.86 + $115.90
               = $1,807.31

Total Deductions = -$5.57 + -$2.78 + -$228.54
                 = -$236.89

Net = $1,807.31 - $236.89 = $1,570.42
```

---

## Troubleshooting

### Issue: Payslip doesn't compute

**Possible Causes:**
1. Employee has no active contract
2. Contract doesn't have V2 fields populated
3. Salary structure not selected correctly

**Solution:**
- Verify contract state is "Running"
- Check V2 fields: `ueipab_salary_v2`, `ueipab_bonus_v2`, etc.
- Ensure structure selected is "Liquidación Venezolana V2" (not V1!)

### Issue: Daily Salary is wrong

**Check:**
```python
Expected Daily Salary = ueipab_salary_v2 / 30

VIRGINIA VERDE: $146.19 / 30 = $4.873/day ✅
```

If showing different value, verify:
- Contract V2 fields are populated correctly
- Formula is using `ueipab_salary_v2` (not `ueipab_deduction_base`)

### Issue: Bono Vacacional rate seems wrong

**Verify:**
- Is `ueipab_original_hire_date` set?
- Calculate expected rate:
  ```
  If seniority >= 16 years: 30 days/year
  If seniority >= 1 year: 15 + (years - 1) days/year
  Else: 15 days/year
  ```

**Example:**
- VIRGINIA VERDE: 6.17 years → 15 + (6.17 - 1) = 20.2 days/year ✅

### Issue: Accounting doesn't post

**Check:**
- Accounts exist: 5.1.01.10.010 (Debit) and 2.1.01.10.005 (Credit)
- V2 rules have accounting configured (8 rules should have it)
- Payslip is in "Done" state (after confirmation)

---

## Comparison: V1 vs V2 Results

When you test both V1 and V2 for the same employee:

**Expected Difference:**
```
V1 uses: ueipab_deduction_base (~42% of wage)
V2 uses: ueipab_salary_v2 (direct salary amount)

VIRGINIA VERDE:
  V1 deduction_base: $134.01
  V2 salary_v2:      $146.19  (+$12.18 or +9.1% more)

Result: V2 liquidation will be HIGHER than V1
```

This is **EXPECTED** because V2 uses the actual deductible salary amount, not the inflated percentage-based field.

---

## Production Deployment Checklist

Before using V2 for real terminations:

- [ ] ✅ All 3 test employees tested via UI
- [ ] ✅ V2 salary field usage verified (daily salary = salary_v2 / 30)
- [ ] ✅ `ueipab_original_hire_date` logic working (progressive bono rate)
- [ ] ✅ `ueipab_previous_liquidation_date` logic working (antiguedad deduction)
- [ ] ✅ `ueipab_vacation_paid_until` logic working (prepaid deduction)
- [ ] ✅ Accounting posts correctly (5.1.01.10.010 / 2.1.01.10.005)
- [ ] ✅ Journal entry totals match liquidation gross
- [ ] ✅ User training completed
- [ ] ✅ V1 parallel operation confirmed (both structures available)

---

## Files Created

**Implementation:**
- `/opt/odoo-dev/scripts/create_liquidation_v2_structure.py` - V2 creation script (EXECUTED ✅)
- `/opt/odoo-dev/scripts/test_liquidation_v2_three_employees.py` - Automated test script (UI testing recommended instead)

**Documentation:**
- `/opt/odoo-dev/documentation/LIQUIDACION_V2_MIGRATION_PLAN.md` - Complete migration plan
- `/opt/odoo-dev/documentation/LIQUIDACION_V2_TESTING_GUIDE.md` - This testing guide

---

## Summary

**✅ Liquidación Venezolana V2 is READY FOR TESTING!**

**What's Complete:**
- ✅ V2 structure created (ID: 10, Code: LIQUID_VE_V2)
- ✅ All 14 salary rules configured with V2 formulas
- ✅ Accounting configured (5.1.01.10.010 / 2.1.01.10.005)
- ✅ `ueipab_original_hire_date` logic preserved
- ✅ Historical tracking supported (previous liquidation, prepaid vacation)
- ✅ Independent structure (no parent inheritance issues)

**Next Steps:**
1. Test via Odoo UI with VIRGINIA VERDE
2. Test with GABRIEL ESPAÑA
3. Test with DIXIA BELLORIN
4. Verify all calculations match expected formulas
5. Confirm accounting posts correctly
6. Deploy to production when ready

**Status:** 🚀 **READY FOR UI TESTING**

---

**Last Updated:** 2025-11-16
**Structure ID:** 10
**Code:** LIQUID_VE_V2
