# IGTF Module - SQL Empty Tuple Bug Fix

**Status:** Fixed | **Date:** 2025-12-30 | **Module:** `igtf` (3DVision-C-A)

---

## Issue Summary

The IGTF module's `_get_igtf()` method caused a PostgreSQL syntax error when accessing invoice forms, particularly during `onchange` events on new/unsaved records.

## Error Message

```
psycopg2.errors.SyntaxError: syntax error at or near ")"
LINE 8:             WHERE part.debit_move_id IN ()
                                                 ^
```

## Root Cause

The `_get_igtf()` method in `/mnt/extra-addons/3DVision-C-A/igtf/models/account_move.py` called `self._get_all_reconciled_invoice_partials()` without checking if:

1. The record has a real database ID (not a `NewId` object used during `onchange`)
2. The receivable/payable line_ids have real integer IDs

During `onchange` events on new invoices, Odoo creates temporary records with `NewId` objects instead of integer database IDs. When these are passed to the core Odoo method `_get_all_reconciled_invoice_partials()`, it attempts to execute SQL with an empty tuple `IN ()`, which is invalid PostgreSQL syntax.

## Call Stack

```
tdv_multi_currency_account/models/account_move.py:131 (_compute_second_tax_totals)
  └─> igtf/models/account_move.py:109 (_compute_tax_totals)
      └─> igtf/models/account_move.py:62 (_get_igtf)
          └─> odoo/addons/account/models/account_move.py:3694 (_get_all_reconciled_invoice_partials)
              └─> SQL: WHERE part.debit_move_id IN ()  <-- ERROR
```

## Fix Applied

Added early return checks in `_get_igtf()` method at lines 42-54:

```python
def _get_igtf(self, currency=None):
    self.ensure_one()

    # Early return for new/unsaved records (prevents SQL IN () error during onchange)
    # NewId records don't have real database IDs yet
    if not self.id or not isinstance(self.id, int):
        return 0

    # Early return if no receivable/payable lines with real database IDs
    receivable_payable_lines = self.line_ids.filtered(
        lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
    )
    # Filter to only real integer IDs (exclude NewId)
    real_ids = [lid for lid in receivable_payable_lines.ids if isinstance(lid, int)]
    if not real_ids:
        return 0

    # ... rest of the method
```

## Files Modified

| Environment | File Path |
|-------------|-----------|
| Testing | `/opt/odoo-dev/addons/3DVision-C-A/igtf/models/account_move.py` |
| Production | `/home/vision/ueipab17/addons/3DVision-C-A/igtf/models/account_move.py` |

## Deployment

- **Testing:** Applied 2025-12-30, Odoo restarted
- **Production:** Applied 2025-12-30, Odoo restarted

## Testing

1. Navigate to Accounting > Invoices
2. Create a new invoice (triggers `onchange`)
3. Verify no error occurs when loading the form
4. Verify existing invoices still display IGTF calculations correctly

## Notes

- This is a third-party module from 3DVision-C-A
- The fix is defensive - it ensures the method gracefully returns 0 for new records instead of crashing
- IGTF (Impuesto a las Grandes Transacciones Financieras) is a Venezuelan tax on large financial transactions
