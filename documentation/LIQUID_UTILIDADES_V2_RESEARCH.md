# LIQUID_UTILIDADES_V2 — Utilidades Rate & Period Research

**Status:** ⚠️ PENDING DECISION  
**Identified:** 2026-06-05 (EMILIO ISEA liquidation SLIP/840)  
**Rule affected:** `LIQUID_UTILIDADES_V2` in `LIQUID_VE_V2` structure  
**Rule ID:** prod=unknown, testing=unknown (search by code)

---

## Summary of Issue

Two independent problems in `LIQUID_UTILIDADES_V2`:

| Problem | Current | Correct |
|---------|---------|---------|
| **Rate** | 15 days/year (LOTTT minimum) | 60 days/year (UEIPAB aguinaldo policy) |
| **Period** | Full `service_months` (overlaps prior fiscal year) | Current fiscal year only (Jan–termination month) |

---

## Legal Basis

**LOTTT Article 131** — Utilidades (profit-sharing / year-end bonus):
- Minimum: **15 days/year**
- Maximum: **120 days/year** (4 months)
- Proportional at termination: employer pays for fraction of current fiscal year worked

**"Aguinaldo" = "Utilidades"** — they are the same legal concept. "Aguinaldo" is the colloquial term. UEIPAB's AGUINALDOS salary structure is the December payment of this benefit.

---

## UEIPAB Aguinaldo Policy

The `AGUINALDOS` rule formula (prod id=35):
```python
base_annual_aguinaldos = contract.ueipab_salary_v2 * 2   # 2× monthly = 60 days/year
result = base_annual_aguinaldos * proportion               # 50% each December quincena
```

**UEIPAB pays 60 days/year** — 4× the LOTTT minimum of 15 days. This is a company benefit, within the legal maximum of 120 days.

---

## Current `LIQUID_UTILIDADES_V2` Formula

```python
# Utilidades: 15 days per year (UEIPAB company policy)
service_months = LIQUID_SERVICE_MONTHS_V2 or 0.0
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0
if service_months < 12:
    utilidades_days = (service_months / 12.0) * 15.0
else:
    utilidades_days = 15.0
result = utilidades_days * daily_salary
```

**Problem 1 — Wrong rate:** comment says "UEIPAB company policy" but uses the LOTTT minimum (15 days), not the actual UEIPAB policy (60 days).

**Problem 2 — Wrong period:** uses `LIQUID_SERVICE_MONTHS_V2` = net service months from `previous_liquidation_date` to `payslip.date_to`. For EMILIO this was 10.27 months (Aug 2025 – Jun 2026), which includes Aug–Dec 2025 — months already covered by the Dec 2025 aguinaldo payment ($321.52). The liquidation should only cover the **current fiscal year** up to termination.

---

## EMILIO ISEA Reference Case (SLIP/840, terminated 2026-06-04)

- Monthly salary: $160.76 | Daily: $5.359
- Dec 2025 aguinaldo paid: **$321.52** (covers fiscal year 2025; employee worked Aug–Dec 2025 = 5 months under this contract)
- service_months used by rule: **10.27** (Aug 2025 – Jun 2026)
- Correct fiscal-2026 period: **Jan 2026 – Jun 2026 ≈ 5.13 months**

### Scenario comparison

| Scenario | Period (months) | Rate (days/yr) | Amount |
|----------|-----------------|----------------|--------|
| **Current formula** | 10.27 (full service) | 15 | **$68.77** |
| Correct period, LOTTT minimum | 5.13 | 15 | **$34.38** |
| Full period, UEIPAB policy | 10.27 | 60 | **$275.08** |
| **Correct period + UEIPAB policy** | **5.13** | **60** | **~$137.52** |

The current $68.77 sits between the "both wrong" extremes and accidentally produces a middle value — it underpays on rate (×4 below policy) while overpaying on period (×2 above correct period).

---

## Decision Required

### Option A — Keep current (15 days, full service_months)
- **Pro:** Conservative; minimises liability risk.
- **Con:** Internally inconsistent — company pays 60 days in December but only 15 in liquidation. Period boundary not aligned with fiscal year.

### Option B — Fix period only, keep LOTTT minimum (15 days, fiscal year only)
- Amount: ~$34.38 vs current $68.77 (employee receives **less**).
- **Pro:** No double-counting; legally clean at minimum rate.
- **Con:** Employees who worked long periods under the net window would receive very little utilidades.

### Option C — Fix rate + fix period (60 days, fiscal year only) ✅ Recommended
- Amount: ~$137.52 vs current $68.77 (employee receives **more**, consistent with company policy).
- **Pro:** Matches UEIPAB's actual aguinaldo policy; no double-counting; legally consistent.
- **Con:** Higher cost per liquidation; requires deciding exact fiscal year boundary logic.

### Option D — Fix rate only, keep full service_months (60 days, full service_months)
- Amount: ~$275.08 vs current $68.77 (employee receives significantly **more**).
- **Con:** Over-counts months already covered by prior aguinaldo payment. Not recommended.

---

## Implementation (if Option C approved)

The rule needs:

1. **Rate change:** `15.0` → `60.0`
2. **Period fix:** compute fiscal-year months instead of using `LIQUID_SERVICE_MONTHS_V2`

```python
# REVISED LIQUID_UTILIDADES_V2 — 60 days/year, current fiscal year only
import datetime
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

# Fiscal year = calendar year (Jan 1 – Dec 31)
termination_date = payslip.date_to
fiscal_year_start = datetime.date(termination_date.year, 1, 1)

# If there is a previous_liquidation_date in the same fiscal year, use it as start
try:
    prev_liq = contract.ueipab_previous_liquidation_date
except:
    prev_liq = False

if prev_liq and prev_liq.year == termination_date.year and prev_liq > fiscal_year_start:
    period_start = prev_liq
else:
    period_start = fiscal_year_start

fiscal_months = (termination_date - period_start).days / 30.0
if fiscal_months < 0:
    fiscal_months = 0.0

utilidades_days = (fiscal_months / 12.0) * 60.0
result = utilidades_days * daily_salary
```

**Note:** `import datetime` is FORBIDDEN in Odoo `safe_eval`. The period calculation must use payslip date fields directly, not imports. The formula above is pseudocode for the logic — the actual implementation must use the existing date arithmetic pattern (`.days / 30.0` from already-available fields).

**Safe implementation (no imports):**
```python
daily_salary = LIQUID_DAILY_SALARY_V2 or 0.0

try:
    prev_liq = contract.ueipab_previous_liquidation_date
    if not prev_liq:
        prev_liq = False
except:
    prev_liq = False

# Fiscal year start = Jan 1 of termination year
# payslip.date_to is a date object — replace month/day via arithmetic
date_to = payslip.date_to
fiscal_start_days = (date_to - date_to.replace(month=1, day=1)).days  # days into current year
fiscal_months = fiscal_start_days / 30.0 + (date_to.day / 30.0)  # approx

# If prev_liq is within current year, shrink the period
if prev_liq and prev_liq.year == date_to.year:
    paid_days = (prev_liq - prev_liq.replace(month=1, day=1)).days
    paid_months = paid_days / 30.0
    fiscal_months = fiscal_months - paid_months

if fiscal_months < 0:
    fiscal_months = 0.0

utilidades_days = (fiscal_months / 12.0) * 60.0
result = utilidades_days * daily_salary
```

---

## Related

- `LIQUID_ANTIGUEDAD_DAILY_V2` — uses integral salary which itself includes a `60/360` utilidades proportion (LOTTT Art. 104). This is a separate calculation for the antigüedad integral daily rate, not the standalone utilidades payment.
- CHANGELOG 2026-06-05 — EMILIO ISEA liquidation, where this discrepancy was first identified.
- `AGUINALDOS` rule (prod id=35) — reference for the 60-day company policy.

---

## Change Log

| Date | Event |
|------|-------|
| 2026-06-05 | Issue identified during EMILIO ISEA liquidation audit. Current formula produces $68.77 vs legally-aligned $137.52 (Option C). PENDING decision. |
