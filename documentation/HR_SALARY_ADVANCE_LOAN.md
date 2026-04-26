# HR Salary Advance / Loan System

**Status:** Testing | **Version:** 17.0.1.63.0 | **Module:** `ueipab_payroll_enhancements` (+ `ohrms_loan`)

Tracks employee salary advances granted outside of Odoo and recovers them automatically through payslip deductions — either via regular bi-weekly batches (`NOMINA_VE_V2`) or at termination via the liquidation payslip (`LIQUID_VE_V2`).

---

## Business Context

**Phase 1 (current):** Accounting recovery flow. HR records an advance that was already paid outside Odoo; the system automatically deducts the balance from the designated payslip batch.

**Phase 2 (future):** Full request-approval flow. Employee submits a request, manager approves, disbursement is recorded, then same recovery logic applies.

---

## Architecture

| Layer | Component | Purpose |
|---|---|---|
| Data model | `hr.loan` (Cybrosys `ohrms_loan`) | Loan record with installment schedule and approval workflow |
| Extension | `hr.loan.recovery_type` (our field) | Controls which payslip structure triggers deduction |
| Salary rules | `VE_LOAN_DED_V2`, `LIQUID_LOAN_DED_V2` | Deduction rules in each V2 structure |
| Payslip hook | `get_inputs()` override | Guards injection based on `recovery_type` vs structure code |
| Reports | Disbursement Detail, Relación de Liquidación | Dedicated loan column / deduction line |
| Email templates | Employee Delivery, Adelanto Prestaciones | Conditional loan notice block |

---

## Recovery Types

| `recovery_type` | Salary Structure | When it deducts |
|---|---|---|
| `quincena` | `VE_PAYROLL_V2` (id=9) | Payslip whose `date_from–date_to` window contains the installment date |
| `liquidacion` | `LIQUID_VE_V2` (id=10) | Only from termination liquidation payslip |

HR sets the installment date when creating the loan. For quincena recovery the date must fall inside the target quincena window (Q1 = 1–15, Q2 = 16–end of month).

---

## Salary Rules

| Code | Structure | Sequence | Formula |
|---|---|---|---|
| `VE_LOAN_DED_V2` | `VE_PAYROLL_V2` | 106 | `result = -(inputs.LO.amount) if inputs.LO else 0` |
| `LIQUID_LOAN_DED_V2` | `LIQUID_VE_V2` | 196 | `result = -(inputs.LO.amount) if inputs.LO else 0` |

Both rules reference input code `LO` (hr.rule.input). The `LO` amount (USD) is injected by the `get_inputs()` override from the approved loan installment.

**NET formulas updated:**
- `VE_TOTAL_DED_V2` — now includes `VE_LOAN_DED_V2` (try/except block)
- `LIQUID_NET_V2` — now includes `LIQUID_LOAN_DED_V2` (try/except block)

---

## Workflow: Phase 1 (Accounting Recovery)

```
Outside Odoo: HR pays employee advance (cash / bank transfer)
                ↓
Odoo: HR creates hr.loan record
    - Employee, amount (USD), installments, payment_start_date
    - recovery_type: quincena OR liquidacion
                ↓
HR clicks "Compute Installment" → installment lines created
                ↓
HR clicks "Submit" → "Approve"
    (ohrms_loan_accounting: creates journal entry at approval)
                ↓
Next payslip batch computed:
    get_inputs() injects LO amount → VE_LOAN_DED_V2 / LIQUID_LOAN_DED_V2 fires
                ↓
Payslip confirmed → installment line marked paid=True
    Balance auto-decrements on hr.loan
                ↓
When balance_amount = 0 → loan fully recovered
```

---

## Key Technical Notes

### `get_inputs()` override (hr_payslip.py)
Runs after `ohrms_loan`'s own override (MRO chain). Guards the injected `LO` input:
- If `recovery_type='liquidacion'` and current struct is NOT `LIQUID_VE_V2` → zeros out LO input
- If `recovery_type='quincena'` and current struct IS `LIQUID_VE_V2` → zeros out LO input
- No double-deduction risk: ohrms_loan's date range check (`date_from ≤ installment_date ≤ date_to`) ensures only the matching quincena window picks up each installment

### Currency
All amounts stored and computed in USD (same as all other V2 rules). VEB display handled by:
- Email templates via `get_liq_veb()` helper
- Reports via `exchange_rate` multiplication

### ohrms_loan Constraint
One approved loan per employee at a time (`balance_amount > 0` guard). Multiple installments on same loan are fine.

---

## Dependencies

| Module | Required | Purpose |
|---|---|---|
| `ohrms_loan` | Yes | `hr.loan` model, installment schedule, `get_inputs()` integration |
| `ohrms_loan_accounting` | Recommended | Journal entry at loan approval |

---

## Installation Sequence (Testing)

```bash
# 1. Install ohrms_loan (and optionally ohrms_loan_accounting)
docker exec odoo-dev-web /usr/bin/odoo -d testing \
    -i ohrms_loan,ohrms_loan_accounting \
    --stop-after-init --http-port=18069

# 2. Upgrade ueipab_payroll_enhancements (runs post_migrate, adds salary rules)
docker exec odoo-dev-web /usr/bin/odoo -d testing \
    -u ueipab_payroll_enhancements \
    --stop-after-init --http-port=18069

# 3. Restart Odoo
docker restart odoo-dev-web
```

The `post_migrate.py` script creates:
- `VE_LOAN_DED_V2` rule + `LO` input in `VE_PAYROLL_V2`
- `LIQUID_LOAN_DED_V2` rule + `LO` input in `LIQUID_VE_V2`
- Updates `VE_TOTAL_DED_V2` formula to include loan
- Updates `LIQUID_NET_V2` formula to include loan deduction

---

## HR Usage Guide

### Creating a Loan Record (Phase 1)

1. Go to **Employees → Loans** (or via HR menu)
2. Click **New**
3. Fill in:
   - **Employee**: select employee
   - **Loan Amount**: USD amount advanced
   - **No. of Installments**: 1 for single recovery, N for multi-month
   - **Payment Start Date**: first payslip date where deduction should appear
   - **Tipo de Recuperación**: `Quincena` or `Liquidación`
4. Click **Compute Installment** — generates installment lines
5. Click **Submit** → **Approve**

For **quincena** recovery, set payment start date to any date inside the target quincena window.
For **liquidacion** recovery, set payment start date to any date inside the employee's final liquidation period.

### Monitoring

- `hr.loan` form shows: Total Amount, Total Paid, Balance Amount
- Payslip confirmation auto-marks installment as `paid=True`
- When `balance_amount = 0` → loan fully recovered

---

## Reports & Templates Affected

| Artifact | Change | Conditional? |
|---|---|---|
| Payroll Disbursement Detail | Dedicated "Loan Rec." column | Shows 0.00 when no loan |
| Relación de Liquidación | Deduction line in SECTION 2 | Only if LIQUID_LOAN_DED_V2 ≠ 0 |
| Payslip Email - Employee Delivery | Yellow info box with amount | Only if VE_LOAN_DED_V2 ≠ 0 |
| Adelanto de Prestaciones Sociales | Row in deductions table | Only if LIQUID_LOAN_DED_V2 ≠ 0 |
| Send Ack Reminder | No change (not financial doc) | — |

---

## Production Deployment Notes

- Email template "Adelanto de Prestaciones Sociales" body is managed via **direct SQL** — XML changes to this template require a separate SQL sync after testing validation (same procedure as v1.62.2 deployment)
- `ohrms_loan` + `ohrms_loan_accounting` must be installed in production before upgrading `ueipab_payroll_enhancements`
- Migration script is idempotent — safe to re-run (checks for existing rules before creating)

---

## Phase 2 Plan (Future)

When the business requires employee-facing requests:
1. Configure portal access for `hr.loan` model
2. Add employee self-service form view (currently only HR/Manager)
3. Wire `action_approve` to trigger optional disbursement journal entry (ohrms_loan_accounting)
4. No changes needed to deduction logic or reports

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 17.0.1.63.0 | 2026-04-26 | Initial implementation — Phase 1 recovery flow |
