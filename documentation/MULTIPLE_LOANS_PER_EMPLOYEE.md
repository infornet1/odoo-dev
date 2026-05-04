# Multiple Loans per Employee

**Status:** Implemented | **Version:** 17.0.1.66.0
**Created:** 2026-05-04 | **Implemented:** 2026-05-05

---

## Problem Statement (resolved)

`ohrms_loan` enforced a global one-loan-per-employee constraint: `create()` rejected a new loan if the employee already had any approved loan with `balance_amount > 0`. Also, `get_inputs()` had a last-wins bug (only last loan's installment amount used) and `action_payslip_done()` used date-range search instead of per-input tracking.

---

## Implemented Changes (v1.66.0)

### 1. `hr_loan_extension.py` — Remove approval constraint (Option A)

`HrLoan.create()` bypasses ohrms_loan's `create()` via MRO: assigns the sequence itself then calls `super(ohrms_cls, self).create()` skipping the constraint. No limit on concurrent loans.

### 2. `hr_loan_extension.py` — `get_inputs()` fully rewritten

- Removes all LO entries from super() result (replaces ohrms_loan last-wins)
- Searches active loans by `recovery_type` matching `self.struct_id.code`
- Creates one LO input per loan: earliest unpaid installment with `date <= payslip.date_to`
  - Handles skipped periods — past-due installments resurface in next payslip
- HR can zero any LO input in "Other Inputs" tab to skip that loan this period

### 3. `hr_loan_extension.py` — `action_payslip_done()` rewritten

- Iterates `payslip.input_line_ids` with `loan_line_id` set
- For `amount <= 0`: reverts ohrms_loan's `paid=True` (HR chose to skip)
- For `amount > 0`: writes `payslip_id` back onto the installment

### 4. Salary rules — updated formula (both envs, v1.66.0)

Old: `result = -(inputs.LO.amount) if inputs.LO else 0` (only reads last LO input — broken for multiple)

New:
```python
slip = payslip.dict
result = -sum(l.amount for l in slip.input_line_ids if l.code == 'LO')
```

`inputs_dict` in `_get_payslip_lines()` builds a last-wins dict so `inputs.LO` can't sum multiple. The new formula reads `payslip.dict.input_line_ids` directly (all saved inputs, no extra DB query).

### 5. `liquidacion_breakdown_report.py` — multiple loans display

Removed `limit=1`. Shows all active liquidación loan names joined by comma, sums `loan_amount` across all, shows actual recovered amount from the salary rule line.

---

## Design Decisions

- **Option A** (no constraint) chosen — simpler, covers Venezuelan hardship scenarios
- **Full installment or skip** — no partial amounts; HR sets LO to 0 to skip, otherwise full installment deducted
- **One combined row** in payslip email — `VE_LOAN_DED_V2` already sums all LO inputs into one salary rule line
- **No UI warning** for now — HR sees all active loans in "Other Inputs" tab naturally

---

## Related

- [HR Salary Advance / Loan System](HR_SALARY_ADVANCE_LOAN.md) — full architecture and changelog
