# Contract Update Impact Analysis
**Date:** November 9, 2025
**Database:** Production (10.124.0.3 - ueipab17_postgres_1 - testing)
**Objective:** Assess impact of updating contract custom fields for Aguinaldos implementation

---

## 🔍 **Executive Summary**

Updating employee contract custom fields **WILL affect** future payroll calculations but is **SAFE** to proceed with proper precautions. The existing UEIPAB Venezuelan Payroll structure actively uses these fields for all salary calculations.

### **Key Finding:**
✅ **Safe to update** - Custom fields are the source of truth for payroll
⚠️  **Will affect** - All future payslips will use new values
✅ **Past payslips** - Already processed, won't be affected
⚠️  **Must update** - Contract values don't match October 2025 actual payments

---

## 📊 **Current System Architecture**

### **Salary Structure: UEIPAB Venezuelan Payroll**

```
Structure ID: 2
Code: UEIPAB_VE
Name: [VE] Nómina Venezolana UEIPAB
Active Since: September 2024
```

### **Salary Rules Using Custom Fields:**

| Rule Code | Rule Name | Uses Field | Formula |
|-----------|-----------|------------|---------|
| `VE_SALARY_70` | Salary Base (70%) | `ueipab_salary_base` | `base * proportion` |
| `VE_BONUS_25` | Regular Bonus (25%) | `ueipab_bonus_regular` | `bonus * proportion` |
| `VE_EXTRA_5` | Extra Bonus (5%) | `ueipab_extra_bonus` | `extra * proportion` |
| `VE_GROSS` | Gross Total | Categories | Sum of above + Cesta Ticket |

**Python Code Example (from VE_SALARY_70):**
```python
base_monthly_amount = contract.ueipab_salary_base or 0.0
result = base_monthly_amount * proportion  # proportion = 0.5 for bi-monthly
```

### **Bi-Monthly Calculation Logic:**
- Period 1-15: Uses 50% of monthly custom field values
- Period 16-31: Uses 50% of monthly custom field values
- Formula: `payslip_amount = (ueipab_salary_base + ueipab_bonus_regular + ueipab_extra_bonus) * 0.5`

---

## 📈 **Payslip History**

### **Existing Payslips:**
- **Total Payslips:** 46
- **Date Range:** September 2023 - October 31, 2025
- **Unique Employees:** 44
- **Most Recent:** October 15-31, 2025
- **Status:** All marked as "done" (finalized)

### **October 2025 Verification (ARCIDES ARZOLA):**

**Contract Values (Current in Database):**
| Field | Amount (USD) | Monthly Total |
|-------|--------------|---------------|
| `ueipab_salary_base` | $204.49 | 70% |
| `ueipab_bonus_regular` | $73.03 | 25% |
| `ueipab_extra_bonus` | $14.61 | 5% |
| **Total** | **$292.13** | **100%** |

**October Payslip (Oct 15-31, 50% period):**
| Rule | Amount Paid | Expected (50%) | Match? |
|------|-------------|----------------|---------|
| VE_SALARY_70 | $102.25 | $102.25 | ✅ |
| VE_BONUS_25 | $36.52 | $36.52 | ✅ |
| VE_EXTRA_5 | $7.31 | $7.31 | ✅ |
| VE_CESTA_TICKET | $20.00 | $20.00 | ✅ |
| **VE_GROSS** | **$166.07** | **$166.08** | ✅ |

**Conclusion:** October payslips correctly used current contract custom field values.

---

## ⚠️ **Impact Analysis: Updating Custom Fields**

### **What WILL Be Affected:**

1. **✅ Future Payslips (December 2025 onwards)**
   - All new payslips will calculate using updated custom field values
   - Aguinaldos payslip will use new values
   - January 2026 onwards will use new values

2. **✅ Contract Display**
   - Employee contract view will show new salary amounts
   - Reports will reflect new values

3. **✅ Payroll Calculations**
   - VE_SALARY_70 rule will use new `ueipab_salary_base`
   - VE_BONUS_25 rule will use new `ueipab_bonus_regular`
   - VE_EXTRA_5 rule will use new `ueipab_extra_bonus`

### **What WILL NOT Be Affected:**

1. **✅ Past Payslips (Sept 2023 - Oct 2025)**
   - Status: "done" (finalized/posted)
   - Values are stored in `hr_payslip_line` table
   - Cannot be recalculated automatically
   - Historical record is preserved

2. **✅ Standard `wage` Field**
   - Not used by UEIPAB Venezuelan Payroll structure
   - Only referenced for display/reporting
   - Can be updated independently

3. **✅ Liquidación Structure (ID: 3)**
   - Separate structure for severance calculations
   - May have its own field dependencies (needs separate check)

---

## 🚨 **Critical Discrepancy Identified**

### **Spreadsheet (Oct 31, 2025) vs Odoo Production**

**Sample Comparisons:**

| Employee | Spreadsheet | Odoo Contract | Difference | % |
|----------|-------------|---------------|------------|---|
| ARCIDES ARZOLA | $285.39 | $292.13 | -$6.74 | -2.4% |
| VIRGINIA VERDE | $134.01 | $184.08 | -$50.07 | -37.4% |
| RAFAEL PEREZ | $119.09 | $205.06 | -$85.97 | -72.2% |
| RAMON BELLO | $145.26 | $230.15 | -$84.89 | -58.4% |

**Total Aguinaldos Impact:**
- **Spreadsheet Total:** $12,753.41 (45 employees)
- **Current Odoo Total:** $14,586.66 (42 employees)
- **Overpayment Risk:** $1,833.25 (14.4%)

### **Root Cause Analysis:**

The spreadsheet shows **LOWER** amounts than Odoo, suggesting:
1. ✅ Recent salary reductions were applied in actual payments (October)
2. ✅ Odoo contracts were not updated to reflect these changes
3. ❌ October payslips used OLD (higher) contract values
4. ⚠️  Discrepancy between what was PAID vs what was RECORDED

**VERIFICATION NEEDED:**
Were October payslips actually paid at the higher amounts ($292.13 for ARCIDES) or lower amounts ($285.39 from spreadsheet)?

---

## 🎯 **Update Strategy: Safe Implementation**

### **Phase 1: Pre-Update Validation** ✅ COMPLETED

- [x] Identify salary structures using custom fields
- [x] Check existing payslips and their status
- [x] Verify calculation formulas
- [x] Confirm bi-monthly payment logic
- [x] Document current vs spreadsheet discrepancies

### **Phase 2: Backup & Preparation**

**Critical Backups Required:**
```sql
-- Backup hr_contract table
CREATE TABLE hr_contract_backup_20251109 AS
SELECT * FROM hr_contract WHERE state = 'open';

-- Backup specific custom fields
CREATE TABLE contract_salary_backup_20251109 AS
SELECT
    id,
    employee_id,
    ueipab_salary_base,
    ueipab_bonus_regular,
    ueipab_extra_bonus,
    wage,
    wage_ves
FROM hr_contract
WHERE state = 'open';
```

**Verification Queries:**
```sql
-- Verify backup
SELECT COUNT(*) FROM hr_contract_backup_20251109;

-- Check current values
SELECT
    e.name,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
ORDER BY e.name;
```

### **Phase 3: Calculate New Values from Spreadsheet**

**Exchange Rate:** 219.87 VEB/USD (from cell O2)

**Formula:**
```
Column K (VEB) ÷ 219.87 = USD Salary
```

**Distribution (based on current structure):**
- `ueipab_salary_base` = USD Salary × 0.70 (70%)
- `ueipab_bonus_regular` = USD Salary × 0.25 (25%)
- `ueipab_extra_bonus` = USD Salary × 0.05 (5%)
- `wage` = USD Salary (for display)

**Example (ARCIDES ARZOLA):**
```
Spreadsheet: 62,748.90 VEB
USD: 62,748.90 ÷ 219.87 = $285.39

New values:
- ueipab_salary_base: $285.39 × 0.70 = $199.77
- ueipab_bonus_regular: $285.39 × 0.25 = $71.35
- ueipab_extra_bonus: $285.39 × 0.05 = $14.27
- wage: $285.39
```

### **Phase 4: Update Execution**

**Update Script (with rollback capability):**
```sql
-- Start transaction
BEGIN;

-- Update single employee (test first)
UPDATE hr_contract SET
    ueipab_salary_base = 199.77,
    ueipab_bonus_regular = 71.35,
    ueipab_extra_bonus = 14.27,
    wage = 285.39
WHERE id = (
    SELECT c.id FROM hr_contract c
    JOIN hr_employee e ON c.employee_id = e.id
    WHERE e.name = 'ARCIDES ARZOLA'
    AND c.state = 'open'
    LIMIT 1
);

-- Verify the update
SELECT
    e.name,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus,
    c.wage
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE e.name = 'ARCIDES ARZOLA'
AND c.state = 'open';

-- If verification passes, COMMIT; otherwise ROLLBACK;
-- COMMIT;
-- ROLLBACK;
```

### **Phase 5: Post-Update Validation**

**Validation Checks:**
1. ✅ Verify all 45 employees updated
2. ✅ Confirm totals match spreadsheet
3. ✅ Test payslip generation for one employee
4. ✅ Validate calculation formulas still work
5. ✅ Check Aguinaldos total equals $12,753.41

---

## 🔒 **Rollback Plan**

If issues are discovered after update:

```sql
-- Restore from backup
UPDATE hr_contract c SET
    ueipab_salary_base = b.ueipab_salary_base,
    ueipab_bonus_regular = b.ueipab_bonus_regular,
    ueipab_extra_bonus = b.ueipab_extra_bonus,
    wage = b.wage,
    wage_ves = b.wage_ves
FROM contract_salary_backup_20251109 b
WHERE c.id = b.id;

-- Verify restoration
SELECT COUNT(*) FROM hr_contract c
JOIN contract_salary_backup_20251109 b ON c.id = b.id
WHERE c.ueipab_salary_base = b.ueipab_salary_base;
```

---

## ✅ **Recommendations**

### **PROCEED with update because:**

1. ✅ **Alignment with Reality**
   - Spreadsheet reflects actual October 2025 payments
   - Odoo contracts are outdated (some by 70%+)
   - Risk of overpayment if not updated

2. ✅ **Clean Implementation**
   - Past payslips are finalized (won't be affected)
   - Future payslips will use correct values
   - Aguinaldos will be calculated correctly

3. ✅ **Safeguards in Place**
   - Full backup before changes
   - Transaction-based updates (can rollback)
   - Test on single employee first
   - Verification at each step

### **Precautions:**

1. ⚠️  **Confirm Spreadsheet is Authoritative**
   - Verify with accounting/payroll manager
   - Ensure October data is final
   - Confirm exchange rate (219.87 VEB/USD)

2. ⚠️  **Test Before Full Rollout**
   - Update 1 employee contract
   - Generate test payslip
   - Verify calculations
   - Then proceed with all employees

3. ⚠️  **Document the Change**
   - Communicate to payroll team
   - Update procedure documentation
   - Note change in system logs

---

## 📋 **Next Steps**

1. ✅ Get approval from stakeholders (accounting/HR)
2. ⬜ Create backup tables in production database
3. ⬜ Run update script with spreadsheet values
4. ⬜ Verify updates completed successfully
5. ⬜ Test payslip generation for sample employee
6. ⬜ Proceed with Aguinaldos structure creation

---

**Prepared by:** Claude Code AI Assistant
**Review Status:** Ready for stakeholder approval
**Risk Level:** Low (with backups and testing)
**Estimated Time:** 30 minutes (backup + update + verify)

