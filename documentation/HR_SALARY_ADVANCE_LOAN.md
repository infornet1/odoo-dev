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

| Code | Structure | Seq | Debit | Credit | Formula |
|---|---|---|---|---|---|
| `VE_LOAN_DED_V2` | `VE_PAYROLL_V2` | 106 | `1.1.06.01.001` | `1.1.01.02.001` | `result = -(inputs.LO.amount) if inputs.LO else 0` |
| `LIQUID_LOAN_DED_V2` | `LIQUID_VE_V2` | 196 | `1.1.06.01.001` | `5.1.01.10.010` | `result = -(inputs.LO.amount) if inputs.LO else 0` |

Both rules reference input code `LO` (hr.rule.input). The `LO` amount (USD) is injected by the `get_inputs()` override from the approved loan installment.

**NET formulas updated:**
- `VE_TOTAL_DED_V2` — now includes `VE_LOAN_DED_V2` (try/except block)
- `LIQUID_NET_V2` — now includes `LIQUID_LOAN_DED_V2` (try/except block)

---

## Accounting Configuration

### Account Roles

| Account | Name | Role |
|---|---|---|
| `1.1.06.01.001` | Cuentas por cobrar empleados m.nac.corri | Tracks the outstanding advance (asset) |
| `1.1.01.02.001` | Banco Venezuela | Bank — net cash paid to employee |
| `5.1.01.10.010` | Prestaciones sociales (PD) | Liquidation expense |

### Step 0 — Record advance manually when paid outside Odoo

```
DR 1.1.06.01.001  Cuentas por cobrar empleados   $500
   CR 1.1.01.02.001 Banco Venezuela               $500
```

> Phase 2: `ohrms_loan_accounting` can automate this on loan approval.

### Quincena payslip journal (NOMINA_VE_V2)

Example: Gross $1,000 | SSO $40 | FAOV $10 | Loan recovery $50 | NET $900

```
DR 5.1.01.10.001  Nómina (Docentes)    $850
   CR 1.1.01.02.001 Banco Venezuela     $800   ← actual cash to employee
   CR 1.1.06.01.001 Emp. Receivable      $50   ← advance partially cleared
```

### Liquidation payslip journal (LIQUID_VE_V2)

Example: Total liquidation $5,000 | Loan recovery $500 | NET $4,500

```
DR 5.1.01.10.010  Prestaciones Sociales  $5,000   ← FULL expense
   CR 2.1.01.10.005 Provisión Prestaciones $4,500  ← net to employee
   CR 1.1.06.01.001 Emp. Receivable         $500   ← advance fully cleared
```

Balance proof: The loan rule's debit account (`1.1.06.01.001`) produces a **credit** (reduces asset) and its credit account (`5.1.01.10.010`) produces a **debit** (increases expense) for negative rule amounts — this is Odoo payroll's sign convention for deductions.

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
- `VE_LOAN_DED_V2` rule + `LO` input in `VE_PAYROLL_V2` (via `structure.rule_ids` Many2many — no `struct_id` field on `hr.salary.rule` in this version)
- `LIQUID_LOAN_DED_V2` rule + `LO` input in `LIQUID_VE_V2`
- Updates `VE_TOTAL_DED_V2` formula to include loan
- Updates `LIQUID_NET_V2` formula to include loan deduction

> **Note:** Migration runs automatically on first upgrade from pre-63.0. If already at 63.0 (DB version matches), run `setup_loan_rules.py` manually via Odoo shell instead.

---

## Bs Helper Fields (v1.63.1)

| Field | Editable | Behaviour |
|---|---|---|
| `advance_bs_amount` | Until approved | HR enters the Bs amount actually paid. Auto-calculates `loan_amount` USD when changed. |
| `advance_exchange_rate` | Until approved | Auto-populated from latest `res.currency.rate.company_rate` (VEB). HR can override if the actual disbursement rate differs. |
| `loan_amount` (existing) | Always | The USD obligation. Set automatically from Bs ÷ rate; can be overridden manually for USD-first workflows. |

Onchange chain: `advance_bs_amount` or `advance_exchange_rate` → `loan_amount = round(bs / rate, 2)`.
`loan_amount` is **not** forced — editing it directly works without disturbing the Bs fields.

### Approval Journal Entry (v1.63.1)

If `treasury_account_id` + `journal_id` are filled before approval, `action_approve()` automatically posts:
```
DR 1.1.06.01.001  Cuentas por cobrar empleados   loan_amount USD
   CR treasury_account_id                         loan_amount USD
```

If those fields are blank (Phase 1 retroactive), the loan is approved without a journal entry and HR records the advance manually.

`employee_account_id` auto-defaults to `1.1.06.01.001` when an employee is selected on a new loan form.

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
| 17.0.1.63.0 | 2026-04-26 | Initial implementation — Phase 1 recovery flow. Deployed to testing. |
| 17.0.1.63.0 | 2026-04-26 | Path B accounting: VE_LOAN_DED_V2 → DR 1.1.06.01.001 / CR 1.1.01.02.001; LIQUID_LOAN_DED_V2 → DR 1.1.06.01.001 / CR 5.1.01.10.010. Migration script updated. |
| 17.0.1.63.1 | 2026-04-26 | Bs helper fields: `advance_bs_amount` + `advance_exchange_rate` (auto from VEB rate, editable pre-approval). Onchange auto-calculates `loan_amount`. Journal entry posted at approval when treasury_account_id + journal_id are set. `employee_account_id` defaults to 1.1.06.01.001. |
