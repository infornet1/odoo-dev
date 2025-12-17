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

## Change Log

| Date | Action | By |
|------|--------|-----|
| 2025-12-16 | Issue identified and documented | Claude |
| 2025-12-16 | Fixed FACTU/2025/12/0018 | Claude |
| 2025-12-16 | Fixed INV/2025/00377 | Claude |
| 2025-12-16 | Fixed INV/2025/00014 | Claude |

---

## Next Steps

- [ ] Review proposed fixes with development team
- [ ] Decide on permanent fix approach (Option 1, 2, or 3)
- [ ] Implement fix in testing environment
- [ ] Test with various currency change scenarios
- [ ] Deploy to production
- [ ] Monitor for new affected invoices
