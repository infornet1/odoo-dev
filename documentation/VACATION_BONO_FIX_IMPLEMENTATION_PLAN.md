# Vacation & Bono Vacacional Fix - Implementation Plan

**Date:** 2025-11-17
**Status:** Ready for Review
**Affects:** Liquidation V2 Structure (LIQUID_VE_V2)

---

## Executive Summary

The current vacation/bono calculation formulas in V2 liquidation have a critical flaw that results in $0 net vacation/bono for all employees, even when they should receive payments. This plan details the fix to correct this issue.

---

## Problem Statement

### Current Behavior (WRONG)

**Example: YOSMARI (SLIP/801)**
- Liquidation: Sep 2024 - Oct 2025 (14.10 months)
- Prepaid on Aug 1, 2025: $88.98 (covers Aug 2025 only)
- **Current result:** $0.00 ❌
- **Should be:** $15.01 ✅

**Why it's wrong:**
1. VACACIONES/BONO calculate only 2.93 months (Aug-Oct 2025) = $21.77
2. PREPAID deducts all of it = -$21.77
3. Net = $0.00 (employee gets nothing!)

**But employee should receive:**
- Full period (14.10 months) = $103.98
- Minus prepaid (1 month) = $88.98
- **Net:** $15.01

---

## Root Cause Analysis

### Problem 1: VACACIONES_V2 Formula

**Current Logic (WRONG):**
```python
if vacation_paid_until:
    # Calculate ONLY from vacation_paid_until to end
    days_from_last_payment = (payslip.date_to - vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    vacation_days = (months_in_period / 12.0) * 15.0
```

**What it does:** Calculates Aug 1, 2025 → Oct 28, 2025 = 2.93 months

**What it SHOULD do:** Calculate FULL liquidation period (14.10 months)

### Problem 2: BONO_VACACIONAL_V2 Formula

**Same issue as VACACIONES_V2** - calculates only partial period instead of full period.

### Problem 3: VACATION_PREPAID_V2 Formula

**Current Logic (WRONG):**
```python
if vacation_paid_until:
    result = -1 * (vacaciones + bono)  # Deducts 100% of calculated amount
```

**What it does:** Deducts the entire $21.77 calculated above

**What it SHOULD do:** Deduct the ACTUAL prepaid amount ($88.98)

---

## Solution Design

### Overview

**New Approach:**
1. **VACACIONES_V2:** Calculate for FULL liquidation period (no exclusions)
2. **BONO_VACACIONAL_V2:** Calculate for FULL liquidation period (no exclusions)
3. **PREPAID_V2:** Deduct ACTUAL prepaid amount from new contract field

### Changes Required

#### Change 1: Add New Contract Field

**Module:** `ueipab_hr_contract`
**Field:** `ueipab_vacation_prepaid_amount`

```python
ueipab_vacation_prepaid_amount = fields.Monetary(
    string="Vacation/Bono Prepaid Amount",
    currency_field='currency_id',
    help="Total amount paid in advance for vacation and bono vacacional "
         "(e.g., Aug 1 annual payments). This will be deducted from liquidation.",
    tracking=True,
    copy=False,
)
```

**Why:** Store the ACTUAL dollar amount paid (e.g., $88.98) instead of calculating it.

#### Change 2: Update LIQUID_VACACIONES_V2 Formula

**Current Formula (83 lines):**
```python
# Vacaciones: 15 days per year with vacation paid until tracking
# CHANGED: Uses V2 rule references

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get vacation paid until field safely
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Calculate only unpaid period (from last payment to liquidation)
    days_from_last_payment = (payslip.date_to - vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    vacation_days = (months_in_period / 12.0) * 15.0
else:
    # No tracking, calculate proportionally for full service
    vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary
```

**New Formula (SIMPLIFIED - 22 lines):**
```python
# Vacaciones: 15 days per year - Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Calculate for FULL liquidation period (no exclusions)
vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary
```

**Key Changes:**
- ❌ Removed: `vacation_paid_until` logic
- ✅ Simplified: Always calculate for full service period
- ✅ Cleaner: 73% reduction in code (83 → 22 lines)

#### Change 3: Update LIQUID_BONO_VACACIONAL_V2 Formula

**Current Formula (113 lines):**
```python
# Bono Vacacional: 15 days minimum with historical tracking
# CHANGED: Uses V2 rule references
# ⚠️ CRITICAL: Uses ueipab_original_hire_date for progressive seniority bonus!

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual bonus days based on total seniority
if total_seniority_years >= 16:
    annual_bonus_days = 30.0  # Maximum
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year
    annual_bonus_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_bonus_days = 15.0  # Minimum

# Try to get vacation paid until for period calculation
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Calculate only unpaid period
    days_from_last_payment = (payslip.date_to - vacation_paid_until).days
    months_in_period = days_from_last_payment / 30.0
    bonus_days = (months_in_period / 12.0) * annual_bonus_days
else:
    # No tracking, calculate proportionally for full service
    bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary
```

**New Formula (SIMPLIFIED - 47 lines):**
```python
# Bono Vacacional: Progressive rate based on seniority
# Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments
# ⚠️ CRITICAL: Uses ueipab_original_hire_date for progressive seniority bonus!

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual bonus days based on total seniority
if total_seniority_years >= 16:
    annual_bonus_days = 30.0  # Maximum
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year
    annual_bonus_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_bonus_days = 15.0  # Minimum

# Calculate for FULL liquidation period (no exclusions)
bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary
```

**Key Changes:**
- ❌ Removed: `vacation_paid_until` logic
- ✅ Kept: Progressive seniority bonus rate calculation (CRITICAL)
- ✅ Simplified: Always calculate for full service period
- ✅ Cleaner: 58% reduction in code (113 → 47 lines)

#### Change 4: Update LIQUID_VACATION_PREPAID_V2 Formula

**Current Formula (27 lines):**
```python
# Deduct prepaid vacation/bono if already paid on Aug 1, 2025
# CHANGED: Uses V2 rule references

# Try to get vacation paid until field
try:
    vacation_paid_until = contract.ueipab_vacation_paid_until
    if not vacation_paid_until:
        vacation_paid_until = False
except:
    vacation_paid_until = False

if vacation_paid_until:
    # Employee received Aug 1 annual payment - deduct from liquidation
    vacaciones = LIQUID_VACACIONES_V2 or 0.0
    bono = LIQUID_BONO_VACACIONAL_V2 or 0.0
    result = -1 * (vacaciones + bono)
else:
    # No prepayment (hired after Aug 31, 2025) - no deduction
    result = 0.0
```

**New Formula (IMPROVED - 31 lines):**
```python
# Deduct prepaid vacation/bono amount from contract field
# This represents the actual dollar amount paid in advance (e.g., Aug 1 payments)
# CHANGED: Uses new ueipab_vacation_prepaid_amount field

# Try to get prepaid amount from contract field
try:
    prepaid_amount = contract.ueipab_vacation_prepaid_amount
    if not prepaid_amount:
        prepaid_amount = 0.0
except:
    prepaid_amount = 0.0

if prepaid_amount > 0:
    # Deduct the actual prepaid amount
    result = -1 * prepaid_amount
else:
    # No prepayment - no deduction
    result = 0.0
```

**Key Changes:**
- ❌ Removed: Calculation based on VACACIONES/BONO values
- ✅ Changed: Use actual prepaid amount from contract field
- ✅ Simpler: Direct deduction of stored amount
- ✅ Flexible: User controls exact deduction amount

---

## Implementation Steps

### Step 1: Update Contract Module (ueipab_hr_contract)

**File:** `/mnt/extra-addons/ueipab_hr_contract/models/hr_contract.py`

**Action:** Add new field to contract model

```python
ueipab_vacation_prepaid_amount = fields.Monetary(
    string="Vacation/Bono Prepaid Amount",
    currency_field='currency_id',
    help="Total amount paid in advance for vacation and bono vacacional "
         "(e.g., Aug 1 annual payments: $88.98, $134.48 + $122.34 = $256.82). "
         "This amount will be deducted from liquidation. "
         "Leave at 0.00 if no advance payments were made.",
    tracking=True,
    copy=False,
    groups='hr.group_hr_user',
)
```

**File:** `/mnt/extra-addons/ueipab_hr_contract/views/hr_contract_views.xml`

**Action:** Add field to contract form view in "📋 Salary Liquidation" page

```xml
<page string="📋 Salary Liquidation" name="salary_liquidation">
    <group string="Liquidation Historical Tracking">
        <group>
            <field name="ueipab_original_hire_date"/>
            <field name="ueipab_previous_liquidation_date"/>
            <field name="ueipab_vacation_paid_until"/>
            <!-- NEW FIELD -->
            <field name="ueipab_vacation_prepaid_amount"
                   widget="monetary"
                   options="{'currency_field': 'currency_id'}"/>
        </group>
        <group>
            <separator string="💡 Help"/>
            <div class="o_form_label">
                <strong>Vacation Prepaid Amount:</strong> Enter the total dollar amount
                paid in advance for vacation and bono (e.g., Aug 1 annual payments).
                Examples:
                <ul>
                    <li>Single payment: $88.98</li>
                    <li>Two payments: $134.48 + $122.34 = $256.82</li>
                </ul>
                This amount will be deducted from the liquidation calculation.
            </div>
        </group>
    </group>
</page>
```

**File:** `/mnt/extra-addons/ueipab_hr_contract/__manifest__.py`

**Action:** Bump version

```python
'version': '1.5.0',  # Was 1.4.0
```

### Step 2: Update Liquidation V2 Salary Rules

**Method:** Use Odoo shell script to update the 3 salary rules directly in database

**Script:** `/opt/odoo-dev/scripts/fix_vacation_bono_formulas_v2.py`

```python
#!/usr/bin/env python3
"""
Fix Vacation/Bono Vacacional formulas in Liquidation V2 structure

This script updates 3 salary rules:
1. LIQUID_VACACIONES_V2 - Calculate for FULL period
2. LIQUID_BONO_VACACIONAL_V2 - Calculate for FULL period
3. LIQUID_VACATION_PREPAID_V2 - Deduct actual prepaid amount

Usage:
    docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \\
      < /opt/odoo-dev/scripts/fix_vacation_bono_formulas_v2.py
"""

# Get V2 liquidation structure
struct = env['hr.payroll.structure'].search([('code', '=', 'LIQUID_VE_V2')], limit=1)

if not struct:
    print("ERROR: LIQUID_VE_V2 structure not found!")
    exit(1)

print("=" * 80)
print("UPDATING VACATION/BONO FORMULAS - LIQUIDATION V2")
print("=" * 80)

# =============================================================================
# 1. Update LIQUID_VACACIONES_V2
# =============================================================================

vacaciones_rule = env['hr.salary.rule'].search([
    ('code', '=', 'LIQUID_VACACIONES_V2'),
    ('struct_id', '=', struct.id)
], limit=1)

if vacaciones_rule:
    new_vacaciones_formula = """# Vacaciones: 15 days per year - Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Calculate for FULL liquidation period (no exclusions)
vacation_days = (service_months / 12.0) * 15.0

result = vacation_days * daily_salary"""

    vacaciones_rule.write({
        'amount_python_compute': new_vacaciones_formula
    })

    print(f"\n✅ Updated LIQUID_VACACIONES_V2 (Rule ID: {vacaciones_rule.id})")
    print(f"   Old formula: 83 lines with vacation_paid_until logic")
    print(f"   New formula: 22 lines - calculate for FULL period")
else:
    print("\n❌ ERROR: LIQUID_VACACIONES_V2 rule not found!")

# =============================================================================
# 2. Update LIQUID_BONO_VACACIONAL_V2
# =============================================================================

bono_rule = env['hr.salary.rule'].search([
    ('code', '=', 'LIQUID_BONO_VACACIONAL_V2'),
    ('struct_id', '=', struct.id)
], limit=1)

if bono_rule:
    new_bono_formula = """# Bono Vacacional: Progressive rate based on seniority
# Calculate for FULL liquidation period
# PREPAID deduction will handle any advance payments
# ⚠️ CRITICAL: Uses ueipab_original_hire_date for progressive seniority bonus!

service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Try to get original hire date for seniority calculation
try:
    original_hire = contract.ueipab_original_hire_date
    if not original_hire:
        original_hire = False
except:
    original_hire = False

if original_hire:
    # Calculate total seniority for bonus rate determination
    total_days = (payslip.date_to - original_hire).days
    total_seniority_years = total_days / 365.0
else:
    # Use current contract seniority
    total_seniority_years = service_months / 12.0

# Determine annual bonus days based on total seniority
if total_seniority_years >= 16:
    annual_bonus_days = 30.0  # Maximum
elif total_seniority_years >= 1:
    # Progressive: 15 + 1 day per year
    annual_bonus_days = min(15.0 + (total_seniority_years - 1), 30.0)
else:
    annual_bonus_days = 15.0  # Minimum

# Calculate for FULL liquidation period (no exclusions)
bonus_days = (service_months / 12.0) * annual_bonus_days

result = bonus_days * daily_salary"""

    bono_rule.write({
        'amount_python_compute': new_bono_formula
    })

    print(f"\n✅ Updated LIQUID_BONO_VACACIONAL_V2 (Rule ID: {bono_rule.id})")
    print(f"   Old formula: 113 lines with vacation_paid_until logic")
    print(f"   New formula: 47 lines - calculate for FULL period")
else:
    print("\n❌ ERROR: LIQUID_BONO_VACACIONAL_V2 rule not found!")

# =============================================================================
# 3. Update LIQUID_VACATION_PREPAID_V2
# =============================================================================

prepaid_rule = env['hr.salary.rule'].search([
    ('code', '=', 'LIQUID_VACATION_PREPAID_V2'),
    ('struct_id', '=', struct.id)
], limit=1)

if prepaid_rule:
    new_prepaid_formula = """# Deduct prepaid vacation/bono amount from contract field
# This represents the actual dollar amount paid in advance (e.g., Aug 1 payments)
# CHANGED: Uses new ueipab_vacation_prepaid_amount field

# Try to get prepaid amount from contract field
try:
    prepaid_amount = contract.ueipab_vacation_prepaid_amount
    if not prepaid_amount:
        prepaid_amount = 0.0
except:
    prepaid_amount = 0.0

if prepaid_amount > 0:
    # Deduct the actual prepaid amount
    result = -1 * prepaid_amount
else:
    # No prepayment - no deduction
    result = 0.0"""

    prepaid_rule.write({
        'amount_python_compute': new_prepaid_formula
    })

    print(f"\n✅ Updated LIQUID_VACATION_PREPAID_V2 (Rule ID: {prepaid_rule.id})")
    print(f"   Old formula: Deduct calculated vacaciones + bono")
    print(f"   New formula: Deduct actual prepaid amount from contract field")
else:
    print("\n❌ ERROR: LIQUID_VACATION_PREPAID_V2 rule not found!")

# =============================================================================
# Commit changes
# =============================================================================

env.cr.commit()

print("\n" + "=" * 80)
print("FORMULA UPDATES COMPLETE")
print("=" * 80)
print("\nNext steps:")
print("1. Restart Odoo: docker restart odoo-dev-web")
print("2. Update contract field for test employees:")
print("   - YOSMARI (ID: 615): ueipab_vacation_prepaid_amount = $88.98")
print("   - VIRGINIA (ID: 577): ueipab_vacation_prepaid_amount = $256.82")
print("3. Recompute test payslips (SLIP/801, SLIP/797)")
print("4. Verify results match simulations")
```

### Step 3: Test & Verify

**Test Cases:**

**1. YOSMARI (SLIP/801) - Single Prepayment**
- Contract update: `ueipab_vacation_prepaid_amount = 88.98`
- Delete and recreate SLIP/801
- **Expected results:**
  - VACACIONES_V2: $51.99
  - BONO_VACACIONAL_V2: $51.99
  - VACATION_PREPAID_V2: -$88.98
  - **NET:** $15.01 ✅

**2. VIRGINIA (SLIP/797) - Double Prepayment**
- Contract update: `ueipab_vacation_prepaid_amount = 256.82` (134.48 + 122.34)
- Delete and recreate SLIP/797
- **Expected results:**
  - VACACIONES_V2: $142.04
  - BONO_VACACIONAL_V2: $142.04
  - VACATION_PREPAID_V2: -$256.82
  - **NET:** $27.26 ✅

**3. Employee with NO Prepayment**
- Contract: `ueipab_vacation_prepaid_amount = 0.00` (default)
- **Expected results:**
  - VACACIONES_V2: (calculated for full period)
  - BONO_VACACIONAL_V2: (calculated for full period)
  - VACATION_PREPAID_V2: $0.00
  - **NET:** Full vacation/bono amount ✅

---

## Rollback Plan

If issues are found, rollback is simple:

**Step 1:** Restore old formulas using backup script
**Step 2:** Restart Odoo
**Step 3:** Recompute affected payslips

**Backup Script:** Will be created before making changes

---

## Documentation Updates

### Files to Update:

1. **LIQUIDATION_V2_IMPLEMENTATION.md**
   - Add section: "Vacation/Bono Formula Fix (2025-11-18)"
   - Document the new simplified logic

2. **CLAUDE.md**
   - Update module versions
   - Add note about vacation prepaid field

3. **Create:** `VACATION_BONO_FIX_SUMMARY.md`
   - Brief summary of the fix
   - Before/after comparisons
   - Test results

---

## Risk Assessment

### Low Risk:
- ✅ Changes isolated to 3 salary rules only
- ✅ New field doesn't affect existing calculations (defaults to 0.00)
- ✅ Easy rollback if issues found
- ✅ Can test thoroughly before production

### Medium Risk:
- ⚠️ All future liquidations will need prepaid amount manually entered
- ⚠️ User must remember to update the field when Aug 1 payments are made

### Mitigation:
- Create user guide for entering prepaid amounts
- Add validation warning if liquidation created without checking prepaid field
- Train HR staff on the new field

---

## Timeline Estimate

**Total time:** ~2-3 hours

1. **Contract field addition:** 30 minutes
   - Code changes
   - View updates
   - Testing

2. **Formula updates:** 30 minutes
   - Run update script
   - Verify formulas changed

3. **Testing:** 60 minutes
   - Test both cases (YOSMARI, VIRGINIA)
   - Test edge cases (no prepayment, partial prepayment)
   - Verify reports still work

4. **Documentation:** 30 minutes
   - Update docs
   - Create user guide

---

## Success Criteria

✅ YOSMARI (SLIP/801) shows NET: $15.01 (not $0.00)
✅ VIRGINIA (SLIP/797) shows NET: $27.26 (not $0.00)
✅ Employee with no prepayment shows full vacation/bono amount
✅ All liquidation reports display correctly
✅ No errors in Odoo logs
✅ Formulas are simpler and easier to understand

---

## Questions for User Approval

1. **Approve new contract field?** `ueipab_vacation_prepaid_amount`
2. **Approve simplified formulas?** (Calculate for full period)
3. **Approve manual entry of prepaid amounts?** (User enters $88.98, $256.82, etc.)
4. **Ready to proceed with implementation?**

---

**End of Implementation Plan**
