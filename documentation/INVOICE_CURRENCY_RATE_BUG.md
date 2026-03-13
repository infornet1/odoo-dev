# Invoice Second Currency Rate Bug

**Created:** 2025-12-16
**Status:** Active Issue - Needs Fix
**Module:** `tdv_multi_currency_account` (3DVision)
**Priority:** High

---

## Problem Description

When creating vendor bills (or invoices), the "Second Currency" amount displays incorrectly - showing extremely large values instead of the correct converted amount.

**Example:**
- Invoice: FACTU/2025/12/0018
- VEB Amount: 21,886.89
- Expected USD: ~$80.00
- Displayed USD: **$5,287,391.11** ❌

---

## Root Cause

The issue occurs due to the sequence of user actions when creating a bill:

### Problematic Flow:
```
1. User creates new bill → System defaults to USD currency
2. User enters invoice lines (while still in USD)
3. User realizes currency is wrong → Changes from USD to VEB
4. System captures INVERTED exchange rate into `fixed_second_currency_rate`
5. Invoice is posted with wrong rate
6. Second currency amount displays incorrectly
```

### Technical Explanation:

The `tdv_multi_currency_account` module stores a `fixed_second_currency_rate` when the invoice is posted. This rate is used to calculate the "Second Currency" display amounts.

**Code location:** `/mnt/extra-addons/3DVision-C-A/tdv_multi_currency_account/models/account_move.py`

```python
def action_post(self):
    for move in self:
        if move.second_currency_id and not move.fixed_second_currency_rate:
            # Rate is captured at post time
            move.fixed_second_currency_rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=move.currency_id,
                to_currency=move.second_currency_id,
                company=move.company_id,
                date=move.date or fields.Date.today(),
            )
    return super(AccountMove, self).action_post()
```

**The bug:** When the user changes currency mid-entry, the rate calculation may use cached/stale values or calculate the inverse rate, resulting in:
- Correct rate: `0.00365...` (USD per VEB)
- Wrong rate: `241.578` (VEB per USD - inverted!)

---

## Affected Invoices (Fixed)

| Invoice | Date | Wrong Rate | Correct Rate | Status |
|---------|------|------------|--------------|--------|
| FACTU/2025/12/0018 | 2025-12-16 | 241.578 | 0.00365... | ✅ Fixed |
| INV/2025/00377 | 2025-11-01 | 223.646 | 0.00447... | ✅ Fixed |
| INV/2025/00014 | 2025-10-01 | 144.373 | 0.00557... | ✅ Fixed |

---

## How to Detect Affected Invoices

```sql
-- Find invoices with inverted rates (rate > 1 is wrong for VEB->USD)
SELECT
    name,
    date,
    move_type,
    amount_total,
    fixed_second_currency_rate,
    CASE
        WHEN fixed_second_currency_rate > 1 THEN 'INVERTED - NEEDS FIX'
        ELSE 'OK'
    END as status
FROM account_move
WHERE state = 'posted'
AND currency_id = 2  -- VEB
AND fixed_second_currency_rate IS NOT NULL
AND fixed_second_currency_rate > 1
ORDER BY date DESC;
```

---

## Manual Fix Procedure

### Step 1: Calculate Correct Rate
```sql
-- Get the correct rate for a specific invoice date
WITH rates AS (
    SELECT
        (SELECT rate FROM res_currency_rate WHERE currency_id = 1 ORDER BY name DESC LIMIT 1) as usd_rate,
        (SELECT rate FROM res_currency_rate WHERE currency_id = 2 AND name <= 'INVOICE_DATE' ORDER BY name DESC LIMIT 1) as veb_rate
)
SELECT usd_rate / veb_rate as correct_rate FROM rates;
```

### Step 2: Update the Invoice
```sql
UPDATE account_move
SET fixed_second_currency_rate = CORRECT_RATE_HERE
WHERE name = 'INVOICE_NUMBER_HERE';
```

### Step 3: Verify
```sql
SELECT
    name,
    amount_total as veb_amount,
    fixed_second_currency_rate as rate,
    ROUND((amount_total * fixed_second_currency_rate)::numeric, 2) as usd_amount
FROM account_move
WHERE name = 'INVOICE_NUMBER_HERE';
```

---

## Proposed Permanent Fix

### Option 1: Recalculate Rate on Currency Change (Recommended)

Add an `@api.onchange('currency_id')` method to recalculate or clear the rate when currency changes:

```python
@api.onchange('currency_id')
def _onchange_currency_id_rate(self):
    """Reset fixed rate when currency changes to prevent inverted rates."""
    if self.state == 'draft':
        self.fixed_second_currency_rate = False
```

### Option 2: Validate Rate Before Posting

Add validation in `action_post()` to check if rate is reasonable:

```python
def action_post(self):
    for move in self:
        if move.second_currency_id and move.currency_id:
            rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=move.currency_id,
                to_currency=move.second_currency_id,
                company=move.company_id,
                date=move.date or fields.Date.today(),
            )
            # Validate: VEB->USD rate should be small (< 0.1)
            if move.currency_id.name == 'VEB' and move.second_currency_id.name == 'USD':
                if rate > 1:
                    # Rate is inverted, fix it
                    rate = 1 / rate
            move.fixed_second_currency_rate = rate
    return super(AccountMove, self).action_post()
```

### Option 3: User Training

Train users to:
1. **Always set the correct currency FIRST** before entering any invoice lines
2. If currency needs to be changed, delete all lines first, change currency, then re-enter lines

---

## Workaround for Users

**Before creating a new bill:**
1. Click "Create"
2. **IMMEDIATELY** change currency from USD to VEB (if needed)
3. Only then start entering invoice lines
4. Verify the exchange rate shown is correct before posting

---

## Files Involved

| File | Description |
|------|-------------|
| `/mnt/extra-addons/3DVision-C-A/tdv_multi_currency_account/models/account_move.py` | Main module with rate logic |
| `/mnt/extra-addons/3DVision-C-A/tdv_multi_currency_account/__manifest__.py` | Module manifest |

---

## Related Configuration

**Company Settings:**
- Company Currency: USD (id=1)
- Second Currency: VEB (id=2)

**Currency Rates Table:** `res_currency_rate`
- VEB rates stored with format: ~2.88 (inverse of VEB/USD)
- Conversion formula: `USD.rate / VEB.rate = 0.00365...`

---

## Monitoring

Run this query periodically to detect new affected invoices:

```sql
SELECT COUNT(*) as affected_count
FROM account_move
WHERE state = 'posted'
AND currency_id = 2
AND fixed_second_currency_rate > 1;
```

---

## FORMA LIBRE Exchange Rate Fix (v17.0.1.4)

**Date:** 2026-03-12
**Module:** `impresion_forma_libre`
**Status:** Deployed to production (2026-03-12)

### Problem

FORMA LIBRE PDF footer showed the exchange rate based on `self.date` (invoice accounting date), not the latest available rate. Invoice INV/2026/00483 displayed 417.36 instead of the current BCV rate.

**Root cause:** `_get_rate()` and `_compute_fiscal_tax_totals._convert()` both used `move.date or fields.date.today()` to look up the exchange rate. This returned the rate for the invoice date (or the nearest earlier date if no entry existed), not the latest rate.

**Additional bug found:** `_compute_fiscal_tax_totals` had a hardcoded `"amount_untaxed": 335.26` that overwrote the computed value.

### Fix Applied

1. `_get_rate()`: changed date parameter from `self.date or fields.date.today()` to `fields.date.today()` — footer always shows latest BCV rate
2. `_compute_fiscal_tax_totals._convert()`: same change — fiscal amounts converted at latest rate, consistent with footer
3. Removed hardcoded `amount_untaxed: 335.26` override

### Production Database Fix

Deleted 3 orphaned USD rate entries (IDs 4, 5, 6) and 1 EUR entry (ID 3) from `res_currency_rate` created during a bulk BCV import on 2025-10-09. Restored a single USD base rate (date 2024-01-01, rate 0.010548256162291249) as the normalization factor for VEB rate calculations.

### Fiscal Check Visibility Fix (2026-03-13)

**Module:** `ueipab_impresion_forma_libre` (view ID 2742 in both envs)

**Problem:** When migrating from Odoo `attrs` syntax to Odoo 17 `invisible=` syntax, the move types were inverted — `fiscal_check`, `control_number`, and `fiscal_correlative` were hidden on `out_invoice` and `in_invoice` (all regular invoices) instead of `out_receipt` and `in_receipt`. Also missing `readonly="state == 'posted'"` guard.

**Fix:** Corrected `invisible` domain to `move_type in ('entry', 'out_receipt', 'in_receipt')` and restored `readonly="state == 'posted'"`. Removed `widget="boolean_toggle"` which was preventing `@api.onchange("fiscal_check")` from firing — the toggle widget doesn't properly trigger onchange for auto-populating `control_number` and `fiscal_correlative`. Reverted to standard checkbox. Applied via direct DB update on both envs + source file fix in `addons_archived/`.

---

## Change Log

| Date | Action | By |
|------|--------|-----|
| 2025-12-16 | Issue identified and documented | Claude |
| 2025-12-16 | Fixed FACTU/2025/12/0018 | Claude |
| 2025-12-16 | Fixed INV/2025/00377 | Claude |
| 2025-12-16 | Fixed INV/2025/00014 | Claude |
| 2026-03-12 | FORMA LIBRE rate fix — always use latest BCV rate at print time | Claude |
| 2026-03-12 | Removed hardcoded amount_untaxed=335.26 bug | Claude |
| 2026-03-12 | Cleaned stale USD/EUR rate entries + restored USD base rate in production | Claude |
| 2026-03-12 | Deployed v17.0.1.4 to production — verified INV/2026/00483 shows 440.97 (today's rate) | Claude |
| 2026-03-13 | Fixed fiscal_check visibility bug in ueipab_impresion_forma_libre view (both envs) | Claude |
| 2026-03-13 | Removed boolean_toggle widget from fiscal_check — was blocking onchange auto-population | Claude |

---

## Next Steps

- [ ] Review proposed fixes with development team
- [ ] Decide on permanent fix approach (Option 1, 2, or 3)
- [ ] Implement fix in testing environment
- [ ] Test with various currency change scenarios
- [ ] Deploy to production
- [ ] Monitor for new affected invoices
