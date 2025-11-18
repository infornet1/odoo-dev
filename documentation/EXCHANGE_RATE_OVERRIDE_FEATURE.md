# Exchange Rate Override Feature - Design Document

**Date:** 2025-11-17
**Status:** Proposed Enhancement
**Affects:** Relación de Liquidación Report Wizard

---

## Business Problem

**Scenario:**
- Liquidation computed: Jul 31, 2025 (all amounts in USD)
- VEB rate on Jul 31: 124.51 VEB/USD
- Payment delayed until: Nov 15, 2025
- VEB rate on Nov 15: 234.87 VEB/USD
- **Issue:** Report uses old rate (124.51), not actual payment rate (234.87)

**Impact:** VEB amounts shown on report don't match actual bolivares paid to employee

---

## Proposed Solution

### Add Exchange Rate Override to Wizard

**New Fields:**

```python
# In liquidacion_breakdown_wizard.py

use_custom_rate = fields.Boolean(
    string='Use Custom Exchange Rate',
    default=False,
    help='Override automatic rate with custom rate for VEB currency'
)

custom_exchange_rate = fields.Float(
    string='Custom VEB Rate',
    digits=(12, 4),
    help='Custom VEB/USD exchange rate (e.g., 234.8715)\n'
         'Only used when "Use Custom Exchange Rate" is enabled and VEB currency selected'
)

rate_date = fields.Date(
    string='Rate Date',
    help='Date for automatic exchange rate lookup (defaults to payslip date_to)'
)
```

### UI Layout

```xml
<group string="Currency & Exchange Rate">
    <field name="currency_id"/>
    <field name="use_custom_rate" invisible="currency_id.name != 'VEB'"/>
    <field name="custom_exchange_rate"
           invisible="not use_custom_rate or currency_id.name != 'VEB'"
           required="use_custom_rate and currency_id.name == 'VEB'"/>
    <field name="rate_date"
           invisible="use_custom_rate or currency_id.name != 'VEB'"
           placeholder="Leave blank to use payslip date"/>
</group>
```

### Report Logic Update

**Current (liquidacion_breakdown_report.py:277-298):**
```python
def _get_exchange_rate(self, date_ref, currency):
    """Get exchange rate for display."""
    if currency.name == 'USD':
        return 1.0

    if currency.name == 'VEB':
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('name', '<=', date_ref)
        ], limit=1, order='name desc')

        if rate_record and hasattr(rate_record, 'company_rate'):
            return rate_record.company_rate
        # ...
```

**Proposed:**
```python
def _get_exchange_rate(self, date_ref, currency, custom_rate=None, custom_date=None):
    """Get exchange rate for display.

    Args:
        date_ref: Reference date from payslip
        currency: Target currency
        custom_rate: Optional custom rate override
        custom_date: Optional custom date for rate lookup

    Returns:
        float: Exchange rate (VEB/USD)
    """
    if currency.name == 'USD':
        return 1.0

    if currency.name == 'VEB':
        # USE CUSTOM RATE IF PROVIDED
        if custom_rate and custom_rate > 0:
            return custom_rate

        # USE CUSTOM DATE IF PROVIDED, OTHERWISE USE date_ref
        lookup_date = custom_date if custom_date else date_ref

        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('name', '<=', lookup_date)
        ], limit=1, order='name desc')

        if rate_record and hasattr(rate_record, 'company_rate'):
            return rate_record.company_rate
        # ...
```

### Data Passing

**Wizard → Report:**
```python
def action_print_pdf(self):
    # ...
    data = {
        'wizard_id': self.id,
        'currency_id': self.currency_id.id,
        'currency_name': self.currency_id.name,
        'payslip_ids': self.payslip_ids.ids,
        'use_custom_rate': self.use_custom_rate,
        'custom_exchange_rate': self.custom_exchange_rate if self.use_custom_rate else None,
        'rate_date': self.rate_date,
    }
```

**Report Model:**
```python
def _generate_breakdown(self, payslip, currency, data=None):
    # ...
    custom_rate = data.get('custom_exchange_rate') if data else None
    custom_date = data.get('rate_date') if data else None

    # Calculate exchange rate for display
    exchange_rate = self._get_exchange_rate(
        date_ref=payslip.date_to,
        currency=currency,
        custom_rate=custom_rate,
        custom_date=custom_date
    )
```

---

## Use Cases

### Case 1: Normal - Use Payslip Date Rate
- **User Action:** Select VEB, leave "Use Custom Rate" unchecked
- **Result:** Uses rate from payslip.date_to (Jul 31: 124.51)

### Case 2: Custom Rate - Actual Payment Date
- **User Action:**
  - Select VEB
  - Check "Use Custom Rate"
  - Enter 234.8715 (Nov 15 rate)
- **Result:** All VEB amounts calculated at 234.8715

### Case 3: Different Date - Auto Lookup
- **User Action:**
  - Select VEB
  - Leave "Use Custom Rate" unchecked
  - Set "Rate Date" = Nov 15, 2025
- **Result:** System looks up rate for Nov 15 automatically (234.8715)

### Case 4: Future Payment - Estimated Rate
- **User Action:**
  - Select VEB
  - Check "Use Custom Rate"
  - Enter 250.00 (estimated future rate)
- **Result:** Report shows estimated amounts for budgeting

---

## Display Changes

**Report Header:** Show which rate is being used

**Current:**
```
Tasa de Cambio: 124.5102 VEB/USD (31/07/2025)
```

**Enhanced:**
```
Tasa de Cambio: 234.8715 VEB/USD (Personalizada - 15/11/2025)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^
                                  Shows it's custom + date
```

Or:
```
Tasa de Cambio: 234.8715 VEB/USD (Tasa del 15/11/2025)
                                  ^^^^^^^^^^^^^^^^^^^^^
                                  Shows rate date override
```

---

## Validation Rules

```python
@api.constrains('custom_exchange_rate', 'use_custom_rate')
def _check_custom_rate(self):
    for wizard in self:
        if wizard.use_custom_rate and wizard.currency_id.name == 'VEB':
            if not wizard.custom_exchange_rate or wizard.custom_exchange_rate <= 0:
                raise ValidationError(
                    'Custom exchange rate must be greater than 0'
                )
            if wizard.custom_exchange_rate > 1000:
                raise ValidationError(
                    'Exchange rate seems too high. Please verify.'
                )

@api.onchange('currency_id')
def _onchange_currency_reset_custom(self):
    """Reset custom rate when switching currencies."""
    if self.currency_id.name != 'VEB':
        self.use_custom_rate = False
        self.custom_exchange_rate = 0.0
```

---

## Benefits

✅ **Flexibility:** Report reflects actual payment conditions
✅ **Accuracy:** VEB amounts match cash paid to employees
✅ **Transparency:** Shows which rate is being used
✅ **Backward Compatible:** Default behavior unchanged
✅ **Future Planning:** Can estimate with projected rates

---

## Implementation Effort

**Time:** 2-3 hours

**Files to Modify:**
1. `models/liquidacion_breakdown_wizard.py` (add 3 fields)
2. `wizard/liquidacion_breakdown_wizard_view.xml` (add fields to form)
3. `models/liquidacion_breakdown_report.py` (update _get_exchange_rate method)
4. `reports/liquidacion_breakdown_report.xml` (update rate display)

**Testing:**
- Test all 4 use cases
- Verify USD currency unaffected
- Test validation rules

---

## Alternative: Just Add Rate Date Override

**Simpler version:** Only add `rate_date` field, skip custom rate

**Pros:**
- Simpler UI
- Automatic rate lookup
- Less validation needed

**Cons:**
- Can't use future/estimated rates
- Can't override if rate missing in system

**Recommendation:** Implement BOTH for maximum flexibility

---

**Status:** Ready for Implementation
**Priority:** Medium (nice-to-have, not critical)
**Risk:** Low (isolated change, backward compatible)
