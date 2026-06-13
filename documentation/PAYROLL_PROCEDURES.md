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

## Josefina Phase 2 (pending)

`LIQUID_OTHER_DED_V2` rule in `LIQUID_VE_V2` to deduct $420.87 overpayment from Year 2 liquidation via `ueipab_other_deductions`. See `documentation/JOSEFINA_RODRIGUEZ_OVERPAYMENT_RESOLUTION.md`.

---

## `LIQUID_UTILIDADES_V2` Rate Inconsistency (open decision)

Rule uses 15 days/year (LOTTT minimum) but UEIPAB's aguinaldo policy pays 60 days/year (2× monthly salary). Under LOTTT Art. 131, utilidades and aguinaldos are the same concept. Formula also uses full `service_months` — overlaps with Dec aguinaldo already paid for prior fiscal year; proportional utilidades in liquidation should cover only current fiscal year up to termination date.

**Decision needed:** (1) align rate to 60 days (company policy) or keep 15 days (LOTTT minimum); (2) fix period to current fiscal year only. See `documentation/LIQUID_UTILIDADES_V2_RESEARCH.md` and CHANGELOG 2026-06-05 for detailed numbers.
