# Venezuelan Payroll V2 - Cesta Ticket Design Decision

**Date:** 2025-11-15
**Status:** ✅ APPROVED - Reuse Existing Field

---

## Executive Summary

**Decision:** REUSE existing `cesta_ticket_usd` field instead of creating `ueipab_cesta_ticket_v2`

**Rationale:** Cesta Ticket is a legally distinct mandatory benefit (not a bonus) that requires separate tracking for labor law compliance and accounting purposes.

---

## Background Investigation

### Current V1 System (Already Working)

**Contract Field:**
- `cesta_ticket_usd` - Monthly food allowance (default $40.00 for all employees)

**Salary Rule:**
- `VE_CESTA_TICKET` (sequence 40)
- Formula: `contract.cesta_ticket_usd * 0.5` (bi-monthly split)
- Category: VE_BENEFITS (Venezuelan Benefits)
- **NOT subject to deductions** (IVSS, FAOV, INCES, ARI)
- Appears in payslips as separate line item

**Example Payslip (FLORMAR HERNANDEZ):**
```
VE_SALARY_70:      $133.34
VE_BONUS_25:       $ 47.62
VE_EXTRA_5:        $  9.53
VE_CESTA_TICKET:   $ 20.00  ← Separate mandatory benefit
----------------------------
VE_GROSS:          $210.49

Deductions (ONLY on Salary):
VE_SSO_DED:        $ -4.61
VE_FAOV_DED:       $ -1.02
VE_PARO_DED:       $ -0.26
----------------------------
VE_NET:            $204.59
```

---

## V2 Design Decision

### ✅ APPROVED: Option 1 - Reuse Existing Field

**V2 Contract Fields (HR-Approved Actual Values):**
```python
# New V2 fields (HR-approved dollar amounts, NOT calculated percentages!)
ueipab_salary_v2 = $119.21       # HR-approved amount subject to deductions
ueipab_extrabonus_v2 = $42.58    # HR-approved amount NOT subject to deductions
ueipab_bonus_v2 = $198.83        # HR-approved amount NOT subject to deductions

# REUSE existing field (DO NOT create new)
cesta_ticket_usd = $40.00        # Mandatory benefit - NOT subject to deductions

# Total wage formula
wage = ueipab_salary_v2 + ueipab_extrabonus_v2 + ueipab_bonus_v2 + cesta_ticket_usd
     = $119.21 + $42.58 + $198.83 + $40.00
     = $400.62 ✓
```

**CRITICAL V2 Design Principle:**
- ❌ **NO percentage calculations** (no `× 70%`, no `× 30%`)
- ✅ **HR-approved actual dollar values** imported from spreadsheet
- ✅ **70/30 is only a suggestion** for HR when filling spreadsheet

**V2 Salary Rules Breakdown:**
```python
VE_SALARY_V2       = contract.ueipab_salary_v2
VE_EXTRABONUS_V2   = contract.ueipab_extrabonus_v2
VE_BONUS_V2        = contract.ueipab_bonus_v2
VE_CESTA_TICKET    = contract.cesta_ticket_usd * 0.5  ← REUSE EXISTING RULE
VE_GROSS_V2        = VE_SALARY_V2 + VE_EXTRABONUS_V2 + VE_BONUS_V2 + VE_CESTA_TICKET

# Deductions ONLY on Salary
VE_SSO_DED_V2      = ueipab_salary_v2 * 2.25%  ← NOT on bonuses or cesta ticket
VE_FAOV_DED_V2     = ueipab_salary_v2 * 0.5%   ← NOT on bonuses or cesta ticket
VE_PARO_DED_V2     = ueipab_salary_v2 * 0.125% ← NOT on bonuses or cesta ticket
VE_ARI_DED_V2      = ueipab_salary_v2 * rate%  ← NOT on bonuses or cesta ticket
VE_TOTAL_DED_V2    = Sum of all deductions
VE_NET_V2          = VE_GROSS_V2 + VE_TOTAL_DED_V2 (deductions are negative)
```

**Advantages:**
- ✅ No field duplication
- ✅ Maintains legal distinction (mandatory benefit vs bonus)
- ✅ Existing VE_CESTA_TICKET rule continues working
- ✅ Clear audit trail (Cesta Ticket always separate line)
- ✅ Easier accounting/reporting (distinct GL accounts)
- ✅ Complies with Venezuelan labor law requirement (LOTTT)

---

## Legal & Accounting Justification

### Venezuelan Labor Law (LOTTT)

**Cesta Ticket Classification:**
- **Mandatory benefit** per Ley de Alimentación
- Fixed amount for all employees (~$40/month)
- **Exempt from social security contributions:**
  - IVSS (SSO) - 4.5% exempt
  - FAOV - 1% exempt
  - INCES (PARO) - 0.25% exempt
- **Separate reporting requirement** for labor inspections
- Must appear as distinct line item in payslips for transparency

**Legal Distinction: Benefit vs Bonus**
- **Cesta Ticket (Benefit):** Mandatory, fixed amount, tax-exempt
- **Bonuses (Variable Compensation):** Discretionary, performance-based, may be taxable

### Accounting Treatment

**General Ledger Accounts:**
- **Cesta Ticket:** Account 6210 - "Mandatory Employee Benefits"
- **Bonuses:** Account 6220 - "Variable Compensation"
- **Different GL accounts = must be tracked separately**

**Financial Reporting:**
- Cesta Ticket appears in "Benefits" section
- Bonuses appear in "Compensation" section
- Separation required for labor cost analysis

---

## Migration Impact

### What Changes in V2

**Contract Migration:**
```python
# For each employee contract:
new_salary_v2 = current_deduction_base * 0.70
new_bonus_v2 = current_deduction_base * 0.30
new_extrabonus_v2 = current_wage - current_deduction_base - cesta_ticket_usd

# NOTE: cesta_ticket_usd is NOT migrated (field already exists)
```

**Payslip Structure (V2):**
```
Earnings:
  VE_SALARY_V2:       $119.21  (subject to deductions)
  VE_EXTRABONUS_V2:   $ 42.58  (NOT subject to deductions)
  VE_BONUS_V2:        $198.83  (NOT subject to deductions)
  VE_CESTA_TICKET:    $ 20.00  (mandatory benefit, NOT subject to deductions)
  ----------------------------
  VE_GROSS_V2:        $380.62

Deductions (ONLY on Salary):
  VE_SSO_DED_V2:      $ -2.68  (2.25% of $119.21)
  VE_FAOV_DED_V2:     $ -0.60  (0.5% of $119.21)
  VE_PARO_DED_V2:     $ -0.15  (0.125% of $119.21)
  ----------------------------
  VE_TOTAL_DED_V2:    $ -3.43

Net Salary:
  VE_NET_V2:          $377.19
```

### What Does NOT Change

**Unchanged Elements:**
- ✅ `cesta_ticket_usd` field (already exists, values remain)
- ✅ `VE_CESTA_TICKET` salary rule (formula unchanged)
- ✅ Bi-monthly split logic (50% per period)
- ✅ Deduction exemption (still exempt from IVSS/FAOV/PARO/ARI)

---

## Comparison: V1 vs V2

### V1 Current System

**Fields:**
- `wage` = $400.62
- `ueipab_deduction_base` = $170.30
- `cesta_ticket_usd` = $40.00

**Calculated:**
- VE_SALARY_70 = $170.30 × 70% = $119.21
- VE_BONUS_25 = $170.30 × 25% = $42.58
- VE_EXTRA_5 = $170.30 × 5% = $8.52
- VE_CESTA_TICKET = $40.00 × 50% = $20.00

**Deductions:** Applied to 100% of deduction_base ($170.30)

### V2 Proposed System

**Fields:**
- `wage` = $400.62
- `ueipab_salary_v2` = $119.21 (stored directly)
- `ueipab_bonus_v2` = $51.09 (stored directly)
- `ueipab_extrabonus_v2` = $190.32 (stored directly)
- `cesta_ticket_usd` = $40.00 (unchanged)

**Calculated:**
- VE_SALARY_V2 = $119.21 (from field)
- VE_EXTRABONUS_V2 = $42.58 (from field)
- VE_BONUS_V2 = $198.83 (from field)
- VE_CESTA_TICKET = $40.00 × 50% = $20.00 (same as V1)

**Deductions:** Applied ONLY to salary_v2 ($119.21) ← KEY DIFFERENCE

---

## Implementation Notes

### Phase 2: Module Structure Design

**NO NEW CESTA TICKET FIELD:**
- ❌ Do NOT create `ueipab_cesta_ticket_v2`
- ✅ Use existing `cesta_ticket_usd` in all calculations

### Phase 3: Development

**Contract Fields (Updated):**
```python
# In ueipab_hr_contract/models/hr_contract.py
class HrContract(models.Model):
    _inherit = 'hr.contract'

    # New V2 fields
    ueipab_salary_v2 = fields.Monetary(...)
    ueipab_extrabonus_v2 = fields.Monetary(...)
    ueipab_bonus_v2 = fields.Monetary(...)

    # NOTE: cesta_ticket_usd ALREADY EXISTS - reuse it

    @api.onchange('ueipab_salary_v2', 'ueipab_extrabonus_v2', 'ueipab_bonus_v2', 'cesta_ticket_usd')
    def _onchange_salary_breakdown_v2(self):
        self.wage = (self.ueipab_salary_v2 or 0.0) + \
                    (self.ueipab_extrabonus_v2 or 0.0) + \
                    (self.ueipab_bonus_v2 or 0.0) + \
                    (self.cesta_ticket_usd or 0.0)
```

**Salary Rules (Updated):**
- Create: VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2
- REUSE: VE_CESTA_TICKET (no changes needed)
- Create: VE_GROSS_V2 = sum(VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2, VE_CESTA_TICKET)

### Phase 6: Data Migration

**Spreadsheet Column Structure (Updated):**
```
A: Employee Name
B: Employee ID (VAT)
C: Current Wage
D: Current Deduction Base
E: Current Cesta Ticket (from existing field)
F: NEW Salary V2 (= D × 70%)
G: NEW Bonus V2 (= D × 30%)
H: NEW ExtraBonus V2 (= C - D - E)
I: Verification Total (= F + G + H + E)
J: Difference (= I - C, should be $0.00)
```

**Migration Script (Updated):**
```python
for contract in active_contracts:
    deduction_base = contract.ueipab_deduction_base
    cesta_ticket = contract.cesta_ticket_usd or 40.00

    contract.write({
        'ueipab_salary_v2': deduction_base * 0.70,
        'ueipab_bonus_v2': deduction_base * 0.30,
        'ueipab_extrabonus_v2': contract.wage - deduction_base - cesta_ticket,
        # NOTE: cesta_ticket_usd NOT updated (field already exists)
    })
```

---

## Summary

**Decision:** ✅ REUSE `cesta_ticket_usd` (existing field)

**Key Points:**
1. Cesta Ticket is legally distinct from bonuses (mandatory benefit vs variable compensation)
2. Existing field and salary rule already work perfectly
3. No duplication = cleaner codebase
4. Maintains legal compliance and accounting separation
5. No migration needed for Cesta Ticket (values already correct)

**V2 Wage Breakdown:**
```
wage = ueipab_salary_v2 + ueipab_extrabonus_v2 + ueipab_bonus_v2 + cesta_ticket_usd
       ↑ Deductible      ↑ Exempt              ↑ Exempt           ↑ Exempt (mandatory)
```

**Next Steps:**
- ✅ V2 Plan updated (728 lines)
- ✅ Contract fields documented
- ✅ Migration scripts updated
- ✅ Test cases updated
- ⏳ Proceed to Phase 2 (Module Structure Design) upon user approval

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
