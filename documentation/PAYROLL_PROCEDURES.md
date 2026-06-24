# Payroll Procedures — Operational Runbook

## Closed-Contract Payslip (terminated employee mid-batch)

When an employee's contract is in `close` state, `_get_contract()` filters it out → payslip gets `contract_id = False` and zero lines computed.

**Fix procedure (via XML-RPC / Odoo shell):**
1. `contract.write({'state': 'open'})` — temporarily re-open so `_get_contract()` finds it
2. If pro-rating needed (e.g. employee worked 7 of 15 days): set `ueipab_salary_v2 = original × (2 × days/30)` and same for `ueipab_bonus_v2` — the rule's `/2` then yields the correct `days/30` amount
3. `payslip.action_compute_sheet()` — runs all rules correctly
4. `payslip.write({'contract_id': contract.id})` — `action_compute_sheet` does NOT write this back; must set manually
5. Restore original salary fields: `contract.write({'ueipab_salary_v2': orig, 'ueipab_bonus_v2': orig})`
6. `contract.write({'state': 'close'})` — restore final state
7. Adjust fixed lines (e.g. `VE_CESTA_TICKET_V2`) manually via `hr.payslip.line.write()`, then update `VE_GROSS_V2` and `VE_NET_V2` accordingly

**Cesta ticket pro-ration:** `$20 × days_worked / quincena_days` (e.g. 7/15 → $9.33). Update GROSS and NET lines to match.

**Note:** Deductions (SSO, PARO, FAOV, ARI) auto-scale correctly because their bases reference the salary/bonus rules. SSO stays near $0.05 regardless — it uses the minimum wage base by design.

---

## Unwinding a Mistaken Advance/Loan (money paid ONCE)

**When:** an `is_advance_payment` slip + an `hr.loan` (LO/000X) were created for what was really just the employee's **current-period salary paid early** — no extra money, nothing to recover. Often the loan installment date collided with the advance slip's own period, producing a "phantom recovery" (loan shows paid, but NET never reduced). See the Pitfall in `HR_SALARY_ADVANCE_LOAN.md`. Reference case: Lorena Reyes 2026-06-24 (memory `project-lorena-lo-payslip`).

**Goal:** one slip = the employee's pay; no loan, no receivable, no duplicate JE.

**Procedure (Odoo shell, with a record snapshot first):**
1. **Backup** — snapshot the payslip, loan, and both moves (disbursement + payslip) to JSON for rollback.
2. `payslip.action_payslip_cancel()` — cancels the posted payslip move (kept `cancel` for audit, per `hr_payroll_account_community` policy).
3. `payslip.action_payslip_draft()`.
4. Remove the `LO` input line: `il.unlink()`; reset the installment `il.loan_line_id.write({'paid': False, 'payslip_id': False})`.
5. `loan.action_cancel()` (state → `cancel`); reset lines `paid=False`; `loan._compute_total_amount()`. **Note:** `action_cancel` only flips state — it does NOT reverse the disbursement JE.
6. Cancel the disbursement move: unreconcile its receivable line if matched, then `loan.move_id.button_cancel()` (cancel-not-delete, audit kept).
7. `payslip.action_compute_sheet()` — with no approved loan, no `LO` input is re-added; NET returns to the plain salary figure.
8. `payslip.action_payslip_done()` — posts a fresh clean move (salary only, 0 receivable lines).
9. **Safety gate before commit:** assert NET == expected, no `VE_LOAN_DED_V2` line, no `LO` input, `loan.state=='cancel'`, `disb.state=='cancel'` — else `env.cr.rollback()`.

**Verify** after commit (fresh session): payslip `done` with clean move, loan `cancel`, both old moves `cancel`, new move has 0 lines on the employee-receivable account (`1.1.06.01.001`).

**Rule of thumb:** a salary advance spans **two** pay periods (pay early → deduct from a *later* check). Don't create an LO for a current-period early payment, and never set the installment date inside the advance slip's own period.

---

## Josefina Phase 2 (pending)

`LIQUID_OTHER_DED_V2` rule in `LIQUID_VE_V2` to deduct $420.87 overpayment from Year 2 liquidation via `ueipab_other_deductions`. See `documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md`.

---

## `LIQUID_UTILIDADES_V2` Rate Inconsistency (open decision)

Rule uses 15 days/year (LOTTT minimum) but UEIPAB's aguinaldo policy pays 60 days/year (2× monthly salary). Under LOTTT Art. 131, utilidades and aguinaldos are the same concept. Formula also uses full `service_months` — overlaps with Dec aguinaldo already paid for prior fiscal year; proportional utilidades in liquidation should cover only current fiscal year up to termination date.

**Decision needed:** (1) align rate to 60 days (company policy) or keep 15 days (LOTTT minimum); (2) fix period to current fiscal year only. See `documentation/LIQUID_UTILIDADES_V2_RESEARCH.md` and CHANGELOG 2026-06-05 for detailed numbers.
