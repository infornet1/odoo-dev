# HR Issue: JOSEFINA RODRIGUEZ — Overpayment Resolution (SLIP/447)

**Status:** IN PROGRESS — Analysis complete, pending execution  
**Opened:** 2026-04-08  
**Detected by:** Liquidation forecast audit (NELCI BRITO SLIP/1068)  
**Root cause:** Bug in `LIQUID_ANTIGUEDAD_V2` salary rule  
**Severity:** High — affects antigüedad (prestaciones sociales) calculation  

---

## Root Cause: LIQUID_ANTIGUEDAD_V2 Bug

### What was the bug?

The salary rule `LIQUID_ANTIGUEDAD_V2` contained a validation condition:

```python
# OLD (buggy) — broke for terminated+rehired employees
if previous_liquidation and previous_liquidation >= contract.date_start:
```

This condition was designed to protect against invalid `previous_liquidation_date` values.
However, for employees who were **terminated and rehired**, their `previous_liquidation_date`
is naturally **before** their new `contract.date_start` (there is a gap between contracts).

When the condition failed, the rule fell back to calculating antigüedad from `original_hire_date`
**without deducting the already-paid prior period** — effectively computing decades of full
seniority instead of only the current contract period.

### Fix applied

```python
# NEW (fixed) — supports terminated+rehired employees
if previous_liquidation and previous_liquidation > original_hire:
    paid_days = (previous_liquidation - original_hire).days
    paid_months = paid_days / 30.0
    net_months = total_months - paid_months
    if net_months > 0:
        antiguedad_days = net_months * 2
    else:
        antiguedad_days = 0.0
```

| Environment | Rule ID | Fix applied | Date |
|-------------|---------|-------------|------|
| Testing     | 59      | ✅ Yes      | 2026-04-08 |
| Production  | 29      | ✅ Yes      | 2026-04-08 |

Source file updated: `scripts/create_production_salary_structures.py`

---

## Employee: JOSEFINA RODRIGUEZ

**Employee ID:** 590  
**Contract ID:** 102 (production)  

### Contract fields at time of SLIP/447

| Field | Value |
|-------|-------|
| `date_start` | 2023-09-18 |
| `ueipab_original_hire_date` | 2020-08-01 |
| `ueipab_previous_liquidation_date` | 2023-07-31 |
| `ueipab_salary_v2` | 143.27 |
| `ueipab_bonus_v2` | 139.96 |
| `ueipab_vacation_prepaid_amount` | 478.26 |

### Why the bug triggered

`previous_liquidation_date (2023-07-31)` < `contract.date_start (2023-09-18)`

The employee was terminated on 2023-07-31, then **rehired 2023-09-18** (48-day gap).
The validation incorrectly rejected her prior liquidation date, causing the rule to compute
antigüedad from `original_hire_date = 2020-08-01` — all 4 years — instead of just 1 year.

---

## SLIP/447 — Impact Analysis

**Payslip:** SLIP/447  
**Period:** 2023-09-18 → 2024-07-31 (Year 1 advance annual liquidation)  
**State:** DRAFT (never confirmed in Odoo)  
**Payment status:** ⚠️ Cash payment already disbursed to employee  

### Line-by-line comparison

| Line | Buggy amount | Correct amount | Difference |
|------|-------------|----------------|------------|
| Vacaciones V2 | $75.69 | $75.69 | $0.00 |
| Bono Vacacional V2 | $75.69 | $75.69 | $0.00 |
| Utilidades V2 | $63.08 | $63.08 | $0.00 |
| Prestaciones V2 | $304.88 | $304.88 | $0.00 |
| **Antigüedad V2** | **$561.67** | **$140.80** | **-$420.87** |
| Intereses V2 | $17.45 | $17.45 | $0.00 |
| FAOV V2 | -$2.14 | -$2.14 | $0.00 |
| INCES V2 | -$0.32 | -$0.32 | $0.00 |
| Vacation Prepaid (ded) | -$478.26 | -$478.26 | $0.00 |
| **NET** | **$617.75** | **$196.87** | **-$420.88** |

**Total overpayment: $420.87** — entirely from the LIQUID_ANTIGUEDAD_V2 bug.

### Correct antigüedad calculation (verified)

```
total_days  = (2024-07-31 − 2020-08-01).days  = 1461 days → 48.70 months
paid_days   = (2023-07-31 − 2020-08-01).days  = 1095 days → 36.50 months
net_months  = 48.70 − 36.50                   = 12.20 months  (~1 year ✓)
ant_days    = 12.20 × 2                        = 24.40 days
integral    = 143.27 / 30 × (1 + 60/360 + 15/360) = $5.77/day
ANTIGUEDAD  = 24.40 × 5.77                    = $140.80
```

### Accounting status

- **No journal entry exists** for SLIP/447 — the cash payment has no accounting record yet
- The $420.87 overpayment is currently **not reflected in any account**
- This gives full flexibility to record it correctly

---

## Resolution Plan — Option 1: Confirm as-is + Recover in Year 2

Chosen because:
- Records accounting reality (journal entry matches actual cash disbursed)
- Employee is still active — recovery via next annual liquidation is clean
- Full audit trail in Odoo — no hidden adjustments
- Legally sound under LOTTT (antigüedad advance recovery)

### Phase 1 — Regularize SLIP/447

**Prerequisites:** None — ready to execute

> ⚠️ **CANNOT USE THE UI CONFIRM BUTTON.**
> `action_payslip_done()` always calls `action_compute_sheet()` before setting state=done.
> With the fixed rule now live, that recompute would produce **$196.87** instead of $617.75.
> All Phase 1 steps must be executed via **direct DB + Odoo shell only**.

#### Confirmed via source code (`hr_payslip.py` line 152):
```python
def action_payslip_done(self):
    self.action_compute_sheet()   # ← always recomputes — DANGEROUS
    return self.write({'state': 'done'})
```

#### Also confirmed: changing dates in UI is safe
`onchange_date_from` / `onchange_date_to` only refresh `worked_days_line_ids` and
`input_line_ids` — they never touch `line_ids` (salary rule computations). So editing
dates in the form is safe and will not alter the $617.75 lines.

#### Accounting date issue
- Default journal entry date = `payslip.date_to` (confirmed from existing payslips pattern)
- SLIP/447 `date_to = 2024-07-31` → JE would post to **July 2024** (wrong — period likely closed)
- Actual bank disbursement: **2026-02-24**
- Fix: update `date_from` and `date_to` to `2026-02-24` via DB **before** confirming
- Service period (2023-09-18 → 2024-07-31) stays documented in payslip name and audit trail

#### Execution steps

| Step | Action | Method | Status |
|------|--------|--------|--------|
| 1a | Update payslip: `date_from = date_to = 2026-02-24` | Direct DB | ⬜ Pending |
| 1b | Write payslip `state = 'done'` directly | Direct DB | ⬜ Pending |
| 1c | Create journal entry manually for $617.75 dated 2026-02-24 | Odoo shell | ⬜ Pending |
| 1d | Link `move_id` on payslip to the new journal entry | Direct DB | ⬜ Pending |
| 1e | Verify JE: DR `5.1.01.10.010` Prestaciones $617.75 / CR `2.1.01.10.005` Prov.Prestac. | Odoo UI | ⬜ Pending |
| 1f | Add chatter note to SLIP/447 documenting overpayment + bug context | Odoo UI | ⬜ Pending |
| 1g | Update contract: `ueipab_previous_liquidation_date = 2024-07-31` | Direct DB | ⬜ Pending |
| 1h | Set contract: `ueipab_other_deductions = 420.87` (flags debt for Year 2) | Direct DB | ⬜ Pending |

### Phase 2 — Year 2 Liquidation Recovery (2024-08-01 → 2025-07-31)

**Prerequisites:** Phase 1 complete + `LIQUID_OTHER_DED_V2` rule built

| Step | Action | Status |
|------|--------|--------|
| 2a | Build `LIQUID_OTHER_DED_V2` salary rule in LIQUID_VE_V2 structure | ⬜ Pending |
| 2b | Create SLIP for Year 2 period (2024-08-01 → 2025-07-31) | ⬜ Pending |
| 2c | Verify: NET shows correct_year2 − $420.87 deduction | ⬜ Pending |
| 2d | Confirm Year 2 payslip | ⬜ Pending |
| 2e | Reset contract: `ueipab_other_deductions = 0` | ⬜ Pending |
| 2f | Update contract: `ueipab_previous_liquidation_date = 2025-07-31` | ⬜ Pending |

### Phase 3 — Documentation & Communication

| Step | Action | Status |
|------|--------|--------|
| 3a | Issue internal HR memo to employee explaining the overpayment and recovery plan | ⬜ Pending |
| 3b | File this document in HR records | ⬜ Pending |

---

## LIQUID_OTHER_DED_V2 Rule — Design (to be built)

```python
# LIQUID_OTHER_DED_V2 — Otras Deducciones Liquidacion V2
# Deducts ueipab_other_deductions from liquidation NET
# Used for: overpayment recovery, advances, other contractual deductions
# Reset ueipab_other_deductions = 0 on contract after liquidation is confirmed

try:
    other_ded = contract.ueipab_other_deductions or 0.0
except:
    other_ded = 0.0

if other_ded > 0:
    result = -1 * other_ded
else:
    result = 0.0
```

Must also be added to `LIQUID_NET_V2` formula:
```python
result = (
    ...
    (LIQUID_OTHER_DED_V2 or 0) +   # ← add this line
    prepaid_deduction
)
```

---

## Year 2 Forecast (informational)

Once Phase 1 is complete, Year 2 liquidation (2024-08-01 → 2025-07-31) will be computed with:
- `prev_liq_date = 2024-07-31` (updated after Phase 1)
- `ueipab_other_deductions = 420.87` (overpayment recovery)
- Net result: correct Year 2 amount minus $420.87 recovery

---

## Audit Trail

| Date | Event | By |
|------|-------|----|
| 2026-04-08 | Bug detected during NELCI BRITO liquidation forecast | Developer |
| 2026-04-08 | Root cause confirmed: `LIQUID_ANTIGUEDAD_V2` validation | Developer |
| 2026-04-08 | Fix deployed to Testing (rule id=59) and Production (rule id=29) | Developer |
| 2026-04-08 | SLIP/447 impact analyzed: $420.87 overpayment on antigüedad | Developer |
| 2026-04-08 | Resolution plan (Option 1) documented, pending execution | Developer |
| 2026-04-08 | Confirmed: UI Confirm button unsafe (recomputes) — must use direct DB path | Developer |
| 2026-04-08 | Confirmed: JE date = date_to → must set date_to = 2026-02-24 (actual payment date) | Developer |

---

## Related

- Bug fix: `scripts/create_production_salary_structures.py` (updated 2026-04-08)
- Production rule: `hr_salary_rule` id=29, code=`LIQUID_ANTIGUEDAD_V2`
- Testing rule: `hr_salary_rule` id=59, code=`LIQUID_ANTIGUEDAD_V2`
- Only confirmed V2 liquidation audited: SLIP/313 (STEFANY ROMERO) — not affected
