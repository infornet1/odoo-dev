# Multiple Loans per Employee

**Status:** Planned | **Target version:** 17.0.1.66.0
**Created:** 2026-05-04 | **Discussion:** 2026-05-05 morning

---

## Problem Statement

`ohrms_loan` enforces a global one-loan-per-employee constraint: `create()` / `action_approve()` rejects a new loan if the employee already has any approved loan with `balance_amount > 0`, regardless of `recovery_type`. This prevents valid business scenarios such as an employee having both a quincena advance and a liquidación advance simultaneously.

---

## Proposed Changes (3 files)

### 1. `hr_loan_extension.py` — Override approval constraint

Replace global block with per-`recovery_type` constraint (Option C):
- Allow: employee has quincena loan + liquidacion loan simultaneously
- Block: employee has two quincena loans, or two liquidacion loans

### 2. `hr_loan_extension.py` — Fix `get_inputs()` to SUM multiple loans

**Critical.** Current `ohrms_loan` logic overwrites LO amount on each loan iteration — only last loan wins. Must accumulate total across all matching installment lines for the payslip window.

### 3. `liquidacion_breakdown_report.py` — Handle multiple liquidación loans

Currently uses `limit=1` for loan description. Update to show all loan names and correct total when employee has more than one liquidación loan.

---

## Design Questions for Discussion

1. **Constraint scope:** Per-`recovery_type` (Option B) vs. no constraint at all (Option A)?
   - Option B is safer — prevents accidental duplicates of the same type
   - Option A is simpler but allows unlimited stacking

2. **`loan_line_id` on payslip input:** With multiple loans, only one `loan_line_id` can be stored on `hr.payslip.input`. The `action_payslip_done()` hook searches by employee + date range so it handles multiple lines correctly. But is there a case where this ambiguity causes issues?

3. **Report display for multiple quincena loans:** The Payslip Email currently shows one "Recuperación Anticipo Salarial" row. With two quincena loans deducting in the same payslip, should they appear as:
   - One combined row (sum)
   - Two separate rows (one per loan)

4. **UI / UX for HR:** Should the loan form show a warning when the employee already has an active loan of the same type (soft warning vs. hard block)?

---

## Related

- [HR Salary Advance / Loan System](HR_SALARY_ADVANCE_LOAN.md) — full architecture, Option C reference
- Current known issue in CLAUDE.md: "HR Loan one-loan-per-employee constraint (ohrms_loan)"
