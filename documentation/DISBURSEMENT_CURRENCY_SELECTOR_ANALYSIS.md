# Payroll Disbursement Detail Report - Currency Selector Enhancement

**Date:** 2025-11-14
**Status:** 📋 ANALYSIS FOR REVIEW
**Reference:** Prestaciones Sociales Interest Report (already implemented with currency selector)

---

## Current State Analysis

### Existing Implementation

**Wizard:** `payroll_disbursement_wizard.py`
- ✅ Has filter options: batch/date range
- ✅ Has employee/department filters
- ❌ **NO currency selector field**
- ❌ Passes no currency information to report

**Report Model:** `payroll_disbursement_report.py`
- ✅ Simple pass-through model
- ❌ No currency conversion logic
- ❌ Assumes all values in USD

**QWeb Template:** `payroll_disbursement_detail_report.xml`
- ❌ **Hardcoded "$" symbols** (4 locations found)
- ❌ No dynamic currency symbol
- ❌ No currency conversion

---

## Proposed Changes

### Comparison with Prestaciones Interest Report

**What We Successfully Implemented There:**
1. ✅ Currency selector field in wizard (USD/VEB dropdown)
2. ✅ Currency passed to report model via `data` dict
3. ✅ `_convert_currency()` helper method for conversion
4. ✅ All monetary values converted to selected currency
5. ✅ Dynamic currency symbol in template
6. ✅ Historical exchange rate display

**What We Need Here:**
Same approach, but adapted for aggregate report format:
- Prestaciones = individual payslip breakdown (23 months per employee)
- **Disbursement = aggregate summary (all employees, single totals row)**

---

## Implementation Plan

### Phase 1: Add Currency Field to Wizard

**File:** `payroll_disbursement_wizard.py`

**Changes Needed:**
```python
# Add after department_ids field (line ~60)

currency_id = fields.Many2one(
    'res.currency',
    string='Display Currency',
    required=True,
    default=lambda self: self.env.ref('base.USD'),
    help='Currency for report display (USD or VEB)'
)
```

**Update action_print_report() method:**
```python
# In data dict preparation (line ~158)
data = {
    'wizard_id': self.id,
    'filter_type': self.filter_type,
    'batch_name': self.batch_id.name if self.batch_id else None,
    'date_from': self.date_from,
    'date_to': self.date_to,
    'employee_count': len(payslips.mapped('employee_id')),
    'payslip_count': len(payslips),
    'payslip_ids': payslip_ids,
    'currency_id': self.currency_id.id,  # ← NEW
    'currency_name': self.currency_id.name,  # ← NEW
}
```

**Estimated Impact:** ~5 lines added

---

### Phase 2: Update Wizard View

**File:** `wizard/payroll_disbursement_wizard_view.xml`

**Changes Needed:**
```xml
<!-- Add after department_ids field -->
<field name="currency_id"
       options="{'no_create': True, 'no_open': True}"
       domain="[('name', 'in', ['USD', 'VEB'])]"/>
```

**Estimated Impact:** ~3 lines added

---

### Phase 3: Enhance Report Model

**File:** `payroll_disbursement_report.py`

**Changes Needed:**

1. **Add currency conversion helper method:**
```python
def _convert_currency(self, amount, from_currency, to_currency, date_ref):
    """Convert amount from one currency to another.

    Args:
        amount: Amount to convert
        from_currency: Source currency (res.currency)
        to_currency: Target currency (res.currency)
        date_ref: Date for exchange rate lookup

    Returns:
        float: Converted amount
    """
    if from_currency == to_currency:
        return amount

    return from_currency._convert(
        from_amount=amount,
        to_currency=to_currency,
        company=self.env.company,
        date=date_ref
    )
```

2. **Update _get_report_values() method:**
```python
def _get_report_values(self, docids, data=None):
    # Get payslip IDs from data dict (passed by wizard)
    payslip_ids = data.get('payslip_ids', []) if data else []

    # If no IDs in data, try to use docids parameter
    if not payslip_ids and docids:
        payslip_ids = docids

    # Build payslip recordset from IDs
    payslips = self.env['hr.payslip'].browse(payslip_ids)

    # Sort payslips by employee name
    payslips = payslips.sorted(lambda p: p.employee_id.name or '')

    # Get currency from data (NEW)
    usd = self.env.ref('base.USD')
    currency_id = data.get('currency_id') if data else usd.id
    currency = self.env['res.currency'].browse(currency_id)

    # Convert payslip values if needed (NEW)
    if currency != usd:
        payslips_converted = self._convert_payslip_values(payslips, currency)
    else:
        payslips_converted = payslips

    # Return context for QWeb template
    return {
        'doc_ids': payslip_ids,
        'doc_model': 'hr.payslip',
        'docs': payslips_converted,  # Converted values
        'data': data,
        'currency': currency,  # NEW - pass currency to template
    }
```

3. **Add payslip value conversion method:**
```python
def _convert_payslip_values(self, payslips, target_currency):
    """Convert all payslip line amounts to target currency.

    Note: This doesn't modify the database records, just the in-memory
    values that will be displayed in the report.

    Args:
        payslips: hr.payslip recordset
        target_currency: res.currency record

    Returns:
        recordset: Same payslips with converted line amounts
    """
    usd = self.env.ref('base.USD')

    for payslip in payslips:
        # Get conversion date from payslip
        conversion_date = payslip.date_to or payslip.date_from

        # Convert each payslip line amount
        for line in payslip.line_ids:
            if line.total != 0:
                line.total = self._convert_currency(
                    line.total, usd, target_currency, conversion_date
                )

    return payslips
```

**Estimated Impact:** ~60 lines added

---

### Phase 4: Update QWeb Template

**File:** `payroll_disbursement_detail_report.xml`

**Changes Needed:**

**Current hardcoded symbols (4 locations):**
```xml
Line 187: <strong>Total Gross:</strong> $ <t t-esc="..."/>
Line 190: <strong>Total Deductions:</strong> $ <t t-esc="..."/>
Line 195: <strong>Total Net Payable (USD):</strong> ... $ <t t-esc="..."/>
Line 201: <strong>9% Tax Payable (USD):</strong> ... $ <t t-esc="..."/>
```

**Replace with dynamic currency symbol:**
```xml
Line 187: <strong>Total Gross:</strong> <t t-esc="currency.symbol"/> <t t-esc="..."/>
Line 190: <strong>Total Deductions:</strong> <t t-esc="currency.symbol"/> <t t-esc="..."/>
Line 195: <strong>Total Net Payable (<t t-esc="currency.name"/>):</strong> ... <t t-esc="currency.symbol"/> <t t-esc="..."/>
Line 201: <strong>9% Tax Payable (<t t-esc="currency.name"/>):</strong> ... <t t-esc="currency.symbol"/> <t t-esc="..."/>
```

**Also update period display to include currency:**
```xml
<!-- Add currency info to report header/subtitle -->
<h5>Currency: <t t-esc="currency.name"/> (<t t-esc="currency.symbol"/>)</h5>
```

**Estimated Impact:** ~5 lines modified, ~2 lines added

---

## Technical Considerations

### 1. Exchange Rate Application

**Question:** Which date to use for currency conversion?

**Options:**
A. **Payslip date_to** (end of pay period) - ✅ RECOMMENDED
   - Most accurate for the period being paid
   - Matches Prestaciones Interest Report approach

B. Report generation date
   - Less accurate (could be days/weeks later)

**Recommendation:** Use `payslip.date_to` for each payslip's conversion

---

### 2. In-Memory vs Database Conversion

**Approach:** In-memory conversion (don't modify database)
- Payslip line.total values stored in USD in database
- Convert at display time only
- Same approach as Prestaciones Interest Report

**Why?**
- ✅ Preserves source data integrity
- ✅ Can generate same payslip in multiple currencies
- ✅ No risk of corrupting payroll records

---

### 3. Aggregate Totals Handling

**Challenge:** Report shows aggregate totals for all employees

**Solution:**
- Convert each payslip line individually
- QWeb template aggregates the converted values
- Totals automatically reflect converted currency

**Example:**
```
Employee A: Gross $100 → Bs.23,109 (rate 231.09)
Employee B: Gross $200 → Bs.46,218
Total Gross: Bs.69,327
```

---

### 4. Tax Calculation (9%)

**Current:** 9% calculated on USD net payable
**New:** 9% calculated on VEB net payable (if VEB selected)

**No code change needed:**
- Template calculates `total_net * 0.09`
- If total_net is in VEB, tax will be in VEB
- Automatic!

---

## Testing Plan

### Test Case 1: USD Display (Existing Behavior)
**Input:**
- Batch: Any payslip batch
- Currency: USD

**Expected:**
- ✅ All values display with "$" symbol
- ✅ Values match current report exactly
- ✅ No conversion applied
- ✅ "Total Net Payable (USD)"

---

### Test Case 2: VEB Display (New Behavior)
**Input:**
- Batch: Same batch as Test 1
- Currency: VEB

**Expected:**
- ✅ All values display with "Bs." symbol
- ✅ Values converted using latest exchange rate (~231 VEB/USD)
- ✅ "Total Net Payable (VEB)"
- ✅ 9% tax calculated on VEB amount

**Verification:**
- Employee with $100 gross should show ~Bs.23,109
- Compare totals between USD and VEB (VEB ≈ USD × 231)

---

### Test Case 3: Historical Batch
**Input:**
- Batch: Payslips from Jan 2024
- Currency: VEB

**Expected:**
- ✅ Uses Jan 2024 exchange rate (~36 VEB/USD)
- ✅ Employee with $100 gross should show ~Bs.3,600
- ✅ Demonstrates historical rate application

---

## File Change Summary

| File | Type | Lines Added | Lines Modified | Complexity |
|------|------|-------------|----------------|------------|
| `payroll_disbursement_wizard.py` | Model | ~5 | ~3 | Low |
| `wizard/payroll_disbursement_wizard_view.xml` | View | ~3 | 0 | Low |
| `payroll_disbursement_report.py` | Model | ~60 | ~15 | Medium |
| `payroll_disbursement_detail_report.xml` | Template | ~2 | ~5 | Low |
| **Total** | | **~70** | **~23** | **Low-Medium** |

---

## Estimated Effort

**Development:** 1-2 hours
- Wizard changes: 15 minutes
- Report model enhancements: 45 minutes
- Template updates: 15 minutes
- Testing: 30 minutes

**Testing:** 30 minutes
- USD verification
- VEB verification
- Historical batch verification

**Documentation:** 15 minutes
- Update CLAUDE.md
- Update PAYROLL_DISBURSEMENT_REPORT.md

**Total:** ~2-3 hours

---

## Risks & Mitigation

### Risk 1: Performance Impact
**Issue:** Converting hundreds of payslip lines could be slow

**Mitigation:**
- Currency conversion is simple arithmetic (very fast)
- Prestaciones report converts 23 rows × multiple values (working fine)
- Disbursement converts ~50 employees × ~20 lines each = ~1000 conversions
- Should complete in < 1 second

**Severity:** Low

---

### Risk 2: In-Memory Conversion Breaking Template
**Issue:** Modifying line.total in memory might cause issues

**Mitigation:**
- Same approach works in Prestaciones Interest Report
- Python recordsets handle in-memory modifications well
- Not persisting to database, so safe

**Severity:** Very Low

---

### Risk 3: Exchange Rate Not Available
**Issue:** Historical payslips before 2024-01-30 (earliest VEB rate)

**Mitigation:**
- Use earliest available rate (36.14 VEB/USD)
- Same fallback logic as Prestaciones report
- Document limitation in report notes

**Severity:** Low (affects display only, not calculations)

---

## Recommendation

**Proceed:** ✅ YES

**Rationale:**
1. Low complexity (reusing proven patterns from Prestaciones report)
2. Low risk (in-memory conversion, no database changes)
3. High value (consistent currency support across all payroll reports)
4. Quick implementation (~2-3 hours total)
5. Leverages existing VEB rate sync infrastructure (622 rates available)

**Next Steps:**
1. ✅ User reviews this analysis
2. User approves implementation
3. Implement Phase 1-4 in sequence
4. Test with USD and VEB
5. Document changes
6. Commit and push

---

## Questions for User Review

1. **Currency Options:** Only USD and VEB, or should we allow other currencies?
   - Recommendation: Limit to USD and VEB (domain filter in view)

2. **Default Currency:** USD (as specified)?
   - Recommendation: ✅ USD as default

3. **Historical Payslips:** How to handle payslips before 2024-01-30 (no VEB rates)?
   - Recommendation: Use earliest available rate (36.14 VEB/USD) with note

4. **Report Title:** Should it change based on currency?
   - Current: "RELACIÓN DE SUELDOS Y SALARIOS A PAGAR"
   - Recommendation: Keep title same, add currency indicator in subtitle

5. **9% Tax Label:** Should it specify currency?
   - Current: "9% Tax Payable (USD)"
   - Recommendation: "9% Tax Payable (<currency>)"

---

**Ready for implementation upon approval!** ✅
