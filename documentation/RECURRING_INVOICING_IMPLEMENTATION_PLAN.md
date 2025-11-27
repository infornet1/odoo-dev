# Recurring Invoicing Implementation Plan

**Created:** 2025-11-27
**Status:** Planning Phase
**Author:** Claude Code Assistant

## Executive Summary

Implement a robust recurring invoicing system for UEIPAB using the `sale.order` business process combined with a recurring invoices module, then integrate our custom discount/credit application logic.

## Current State vs Target State

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| Invoice Creation | Manual entry | Auto-generated from contracts |
| Customer Management | Ad-hoc | Structured sale orders/contracts |
| Monthly Billing | Manual process | Automated recurring |
| Discount Application | Manual script | Automated post-generation hook |
| Credit Application | Manual script | Automated post-generation |
| Audit Trail | Invoice only | Customer → SO → Contract → Invoice |

## Proposed Architecture

```
┌─────────────────┐
│   res.partner   │  Customer (parent/representative)
│   (Customer)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   sale.order    │  One-time or template for subscription
│   (Quotation)   │
└────────┬────────┘
         │ Confirm
         ▼
┌─────────────────┐
│    Contract     │  Recurring billing configuration
│ (analytic.acct) │  - Period: Monthly
└────────┬────────┘  - Next Invoice Date
         │
         │ Cron/Manual Generate
         ▼
┌─────────────────┐
│  account.move   │  Draft Invoice
│  (Draft Inv)    │
└────────┬────────┘
         │
         │ ★ Custom Hook ★
         ▼
┌─────────────────┐
│  Discount &     │  Our smart_invoice_confirmation.py logic
│  Credit Script  │  - Check credits ≥ $34.99 → discount
└────────┬────────┘  - Confirm invoice
         │           - Apply available credits
         ▼
┌─────────────────┐
│  account.move   │  Posted Invoice with credits applied
│  (Posted Inv)   │
└─────────────────┘
```

## Module Options Analysis

### Option A: `sales_contract_and_recurring_invoices` (Cybrosys)
- **Price:** Free (AGPL-3)
- **Technical Name:** `sales_contract_and_recurring_invoices`
- **Pros:** Free, portal access, simple
- **Cons:** Less features, basic automation

### Option B: `contract_recurring_invoice_analytic` (Cybrosys)
- **Price:** $67.97 (One-time)
- **Technical Name:** `contract_recurring_invoice_analytic`
- **Pros:** More robust, cron automation, wizard batch processing
- **Cons:** Paid, Odoo Proprietary License

### Recommendation: **Option B**
The paid module offers better automation (cron job) and batch processing which will scale better for UEIPAB's needs.

---

## Implementation Phases

### Phase 1: Module Installation & Configuration
**Duration:** 1-2 days
**Environment:** Testing first

#### Tasks:
1. Purchase and download `contract_recurring_invoice_analytic` module
2. Install in testing environment
3. Configure basic settings:
   - Recurring period: Monthly
   - Invoice generation method: Cron (automated)
   - Currency: USD

#### Dependencies to verify:
- `sale_management` ✅ (should be installed)
- `account` ✅ (should be installed)
- `mail` ✅ (should be installed)

---

### Phase 2: Product & Pricing Setup
**Duration:** 1 day

#### Tasks:
1. Create subscription product(s):
   ```
   Product: "Mensualidad Escolar"
   Type: Service
   Invoicing Policy: Prepaid/Fixed (subscription)
   Price: $197.38 (Regular)
   Recurring: Monthly
   ```

2. Create discount product variant (optional):
   ```
   Product: "Mensualidad Escolar (Descuento)"
   Price: $162.39
   ```

3. Configure product as subscription-enabled

---

### Phase 3: Customer Migration to Sale Orders
**Duration:** 2-3 days

#### Tasks:
1. Create sale order template for monthly tuition
2. For each active customer (parent/representative):
   - Create Sale Order with subscription product
   - Link to existing partner record
   - Set contract start date
   - Confirm to create contract

#### Data to migrate per customer:
| Field | Source | Target |
|-------|--------|--------|
| Customer | res.partner | sale.order.partner_id |
| Product | - | Mensualidad product |
| Price | $197.38 or $162.39 | sale.order.line.price_unit |
| Start Date | Current | contract.date_start |

#### Script approach:
```python
# Bulk create sale orders for existing customers
for partner in active_customers:
    sale_order = env['sale.order'].create({
        'partner_id': partner.id,
        'order_line': [(0, 0, {
            'product_id': mensualidad_product.id,
            'price_unit': 197.38,
            'product_uom_qty': 1,
        })]
    })
    sale_order.action_confirm()  # Creates contract
```

---

### Phase 4: Custom Discount Integration
**Duration:** 2-3 days

#### Approach Options:

**Option A: Post-Generation Hook (Recommended)**
Override the invoice generation method to apply discounts after creation:

```python
class ContractAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def _create_invoice(self):
        """Override to apply discount logic after invoice creation."""
        invoice = super()._create_invoice()

        # Apply our discount logic
        self._apply_credit_discount(invoice)

        return invoice

    def _apply_credit_discount(self, invoice):
        """Apply discount if customer has sufficient credits."""
        REGULAR_FEE = 197.38
        DISCOUNT_FEE = 162.39
        DISCOUNT_THRESHOLD = 34.99

        partner = invoice.partner_id
        credits = self._get_partner_credits(partner)

        if credits >= DISCOUNT_THRESHOLD:
            for line in invoice.invoice_line_ids:
                if abs(line.price_unit - REGULAR_FEE) < 0.01:
                    line.price_unit = DISCOUNT_FEE
```

**Option B: Scheduled Action (Cron)**
Run our existing script after the module's cron generates invoices:

```xml
<record id="ir_cron_apply_discounts" model="ir.cron">
    <field name="name">Apply Discounts to Draft Invoices</field>
    <field name="model_id" ref="account.model_account_move"/>
    <field name="state">code</field>
    <field name="code">model._apply_monthly_discounts()</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="nextcall">2025-01-01 06:00:00</field>
</record>
```

**Option C: Wizard-Based (Manual Control)**
Create a wizard for HR/Admin to run the discount process:

```python
class ApplyDiscountsWizard(models.TransientModel):
    _name = 'apply.discounts.wizard'

    def action_apply_discounts(self):
        """Manual trigger for discount application."""
        draft_invoices = self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('move_type', '=', 'out_invoice'),
        ])
        # Apply discount logic...
```

#### Recommendation: **Option A + Option C**
- Use Option A for automatic processing
- Use Option C for manual control/verification

---

### Phase 5: Credit Application Integration
**Duration:** 1-2 days

#### Tasks:
1. Extend the invoice post-processing to apply credits
2. Use existing `apply_credits_to_invoice()` logic
3. Add logging to chatter for audit trail

```python
def _post_invoice_with_credits(self, invoice):
    """Confirm invoice and apply available credits."""
    # Confirm the invoice
    invoice.action_post()

    # Get available credits
    credit_lines = self._get_partner_credit_lines(invoice.partner_id)

    # Apply credits
    if credit_lines:
        receivable_line = invoice.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
        )
        for credit_line in credit_lines:
            if receivable_line.amount_residual > 0:
                (receivable_line + credit_line).reconcile()

    # Log to chatter
    invoice.message_post(
        body=f"Auto-processed: Discount applied, {len(credit_lines)} credits reconciled"
    )
```

---

### Phase 6: Testing & Validation
**Duration:** 3-5 days

#### Test Cases:

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | New customer, no credit | Invoice at $197.38, no credits |
| 2 | Customer with $50 credit | Invoice at $162.39, $50 applied |
| 3 | Customer with $20 credit | Invoice at $197.38, $20 applied |
| 4 | Multiple students same parent | Multiple lines, correct pricing |
| 5 | Contract renewal | New period, correct dates |
| 6 | Mid-month enrollment | Prorated invoice |

#### Validation Checklist:
- [ ] Cron generates invoices on correct date
- [ ] Discount applied correctly based on credit threshold
- [ ] Credits reconciled automatically
- [ ] Audit trail visible in chatter
- [ ] Portal shows correct invoice to customer
- [ ] Reports reflect accurate data

---

### Phase 7: Production Deployment
**Duration:** 1-2 days

#### Pre-deployment:
1. Full backup of production database
2. Test restore and verify
3. Schedule maintenance window
4. Notify stakeholders

#### Deployment Steps:
1. Install module in production
2. Run customer migration script
3. Verify contract creation
4. Test one invoice cycle manually
5. Enable cron automation

#### Post-deployment:
1. Monitor first automated run
2. Verify invoice accuracy
3. Check credit applications
4. Address any issues

---

## Configuration Reference

### Recurring Period Options:
- Daily
- Weekly
- Monthly ← **UEIPAB setting**
- Quarterly
- Yearly

### Contract States:
```
New → Running → Expires Soon → Expired
         ↓
      Locked (no modifications)
```

### Pricing Logic:
```python
REGULAR_FEE = 197.38      # Standard monthly tuition
DISCOUNT_FEE = 162.39     # Discounted tuition
DISCOUNT_THRESHOLD = 34.99 # Minimum credit to qualify
DISCOUNT_AMOUNT = 34.99    # = REGULAR_FEE - DISCOUNT_FEE
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Module incompatibility | Low | High | Test thoroughly in testing env |
| Data migration errors | Medium | High | Validate each customer record |
| Cron timing issues | Low | Medium | Manual backup process available |
| Credit calculation errors | Low | High | Extensive test cases |
| Performance with many contracts | Low | Medium | Batch processing |

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Module Installation | 1-2 days | Module purchase |
| 2. Product Setup | 1 day | Phase 1 |
| 3. Customer Migration | 2-3 days | Phase 2 |
| 4. Discount Integration | 2-3 days | Phase 3 |
| 5. Credit Integration | 1-2 days | Phase 4 |
| 6. Testing | 3-5 days | Phase 5 |
| 7. Production Deploy | 1-2 days | Phase 6 |
| **Total** | **11-18 days** | |

---

## Next Steps

1. [ ] Review and approve this plan
2. [ ] Decide on module (Option A free vs Option B paid)
3. [ ] Purchase module if Option B selected
4. [ ] Begin Phase 1 in testing environment

---

## References

- [Sales Contract and Recurring Invoices (Free)](https://apps.odoo.com/apps/modules/17.0/sales_contract_and_recurring_invoices)
- [Contract Recurring Invoice Analytic ($67.97)](https://apps.odoo.com/apps/modules/17.0/contract_recurring_invoice_analytic)
- [Cybrosys Odoo 17 Documentation](https://www.cybrosys.com/odoo/odoo-books/v17-ce/sales/invoices/)
- Internal: `scripts/smart_invoice_confirmation.py` (tested discount logic)
