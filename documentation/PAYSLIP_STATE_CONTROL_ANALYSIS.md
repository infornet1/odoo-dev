# Payslip State Control Analysis
**Date:** 2025-11-11  
**Context:** Enhancement 3 improvement - prevent individual payslip state changes when batch is cancelled

## Problem Statement

After cancelling a payslip batch (NOVIEMBRE15), users discovered they can:
1. Open individual payslips from the cancelled batch
2. Click "Set to Draft" button on individual payslip
3. Potentially break the integrity of the cancelled batch

**User Question:**  
> "Should we disable Set to Draft button and prevent any action outside payslip batches view once cancelled? Maybe add a Reject button state/status at payslip level?"

## Current State Workflow

### Payslip States (hr_payslip)
From `hr_payroll_community/models/hr_payslip.py`:
```python
state = fields.Selection(selection=[
    ('draft', 'Draft'),
    ('verify', 'Waiting'),
    ('done', 'Done'),
    ('cancel', 'Rejected'),  # ← Already called "Rejected"!
], ...)
```

**Key Finding:** Cancel state is already labeled "Rejected" in Odoo!

### Batch States (hr.payslip.run)
```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('close', 'Close'),
    ('cancel', 'Cancelled'),  # ← Added by us
], ...)
```

### Current Button Visibility (Individual Payslip Form)
```xml
<button string="Set to Draft" 
        name="action_payslip_draft" 
        type="object" 
        invisible="state != 'cancel'"/>
```

**Problem:** Only checks payslip state, NOT batch state!

## The Issue in Detail

### Scenario:
1. Batch "NOVIEMBRE15" is cancelled (state='cancel')
2. All 44 payslips are cancelled (state='cancel')
3. User opens Payslip ID 480 individually
4. Payslip shows state="Rejected" (cancel)
5. "Set to Draft" button is VISIBLE
6. User clicks it
7. Payslip state changes: cancel → draft
8. **Batch integrity broken!** Batch is cancelled but payslip is draft

### Current Validation in action_payslip_draft:
```python
def action_payslip_draft(self):
    """Function for change stage of Payslip"""
    return self.write({'state': 'draft'})
```

**No validation!** It just changes state without checking:
- Is the batch cancelled?
- Are there journal entries?
- Any other business rules?

## Research Findings

### 1. Odoo Standard Patterns

**Pattern: Parent state affects child actions**

Example from sales orders:
- When sale order is confirmed, order lines can't be edited
- When sale order is cancelled, order lines can't be modified
- Visibility: `invisible="parent_id.state == 'cancel'"`

**Pattern: Related field for visibility**

Common approach:
```python
# In child model
parent_state = fields.Selection(related='parent_id.state', readonly=True)

# In view
<button invisible="parent_state == 'cancel'"/>
```

### 2. State Naming Consistency

**Important Finding:**  
- Payslip cancel state is already labeled "Rejected" 
- No need to add new "Reject" state - it already exists!
- User suggestion about "Reject button" is already implemented via "Cancel Payslip" button

## Solution Options

### Option 1: Add Related Field + Button Visibility ✅ RECOMMENDED

**Approach:**
1. Add computed/related field `payslip_run_state` to hr_payslip
2. Modify button visibility to check both payslip state AND batch state
3. Add validation in `action_payslip_draft()` to prevent state change if batch is cancelled

**Implementation:**
```python
# In hr_payslip model (our module extension)
payslip_run_state = fields.Selection(
    related='payslip_run_id.state',
    string='Batch Status',
    readonly=True,
    store=False
)

def action_payslip_draft(self):
    """Override to prevent setting to draft if batch is cancelled"""
    for payslip in self:
        if payslip.payslip_run_id and payslip.payslip_run_id.state == 'cancel':
            raise UserError(
                _('Cannot set payslip to draft. '
                  'The batch "%s" is cancelled.') % payslip.payslip_run_id.name
            )
    return super().action_payslip_draft()
```

**View modification:**
```xml
<button string="Set to Draft" 
        name="action_payslip_draft" 
        type="object" 
        invisible="state != 'cancel' or payslip_run_state == 'cancel'"/>
```

**Benefits:**
- ✅ Prevents button from showing when batch is cancelled
- ✅ Backend validation as safety net
- ✅ Clear error message if user bypasses UI
- ✅ Maintains batch integrity
- ✅ Clean, Odoo-standard approach

### Option 2: Hide All Buttons When Batch Cancelled ⚠️ MORE RESTRICTIVE

**Approach:**
Hide ALL action buttons on individual payslips when batch is cancelled

**Implementation:**
```xml
<button string="Set to Draft" 
        invisible="state != 'cancel' or payslip_run_state == 'cancel'"/>
<button string="Confirm" 
        invisible="state != 'draft' or payslip_run_state == 'cancel'"/>
<button string="Compute Sheet" 
        invisible="state != 'draft' or payslip_run_state == 'cancel'"/>
<!-- etc for all buttons -->
```

**Issues:**
- ⚠️ Very restrictive
- ⚠️ Users can't even VIEW cancelled payslips comfortably
- ⚠️ May hide buttons that are informational
- ⚠️ Might be overkill

### Option 3: Make Form Read-Only When Batch Cancelled 🔒 NUCLEAR OPTION

**Approach:**
Make entire payslip form read-only when batch is cancelled

**Implementation:**
```xml
<form string="Payslip">
    <field name="payslip_run_state" invisible="1"/>
    <sheet>
        <group>
            <field name="employee_id" readonly="payslip_run_state == 'cancel'"/>
            <field name="date_from" readonly="payslip_run_state == 'cancel'"/>
            <!-- etc for all fields -->
        </group>
    </sheet>
</form>
```

**Issues:**
- ⚠️ Very restrictive
- ⚠️ Lots of view modifications
- ⚠️ Users can't even copy/view data easily
- ⚠️ Overkill for the actual risk

## Analysis: What's the Real Risk?

### If User Sets Cancelled Payslip to Draft:

**What breaks:**
1. Batch state integrity (batch=cancel, payslip=draft)
2. Confusion about which payslips are actually cancelled
3. Potential re-processing of cancelled payslips
4. Audit trail becomes unclear

**What doesn't break:**
- Journal entries are still cancelled (they don't auto-revert)
- Database integrity intact
- No accounting corruption
- No payroll calculation errors

### User Intent Analysis:

**When would users legitimately want to set payslip to draft?**
1. Batch was cancelled by mistake → Should reopen batch first
2. Individual payslip had error → Should never have been in batch
3. Need to reprocess → Should create new batch

**Correct workflow:**
1. If batch cancelled by mistake: Use batch's "Set to Draft" button
2. Then individual payslips can be managed
3. Maintain parent-child state integrity

## Recommended Solution

**Option 1: Add Related Field + Validation** (Balanced approach)

### Why This is Best:

1. **User-Friendly:**
   - Button simply doesn't show when it shouldn't be clicked
   - No confusing "why can't I click this?" moments
   - Clear error message if somehow bypassed

2. **Technically Sound:**
   - Follows Odoo patterns (related fields for visibility)
   - Backend validation as safety net
   - Minimal code changes
   - Easy to maintain

3. **Flexible:**
   - Only restricts the specific problematic action
   - Users can still view payslips
   - Users can still access for reporting
   - Not overly restrictive

4. **Consistent:**
   - Matches how we handle batch cancellation
   - Follows parent-child state relationship pattern
   - Standard Odoo approach

### Implementation Plan:

1. **Add field to hr_payslip model:**
   ```python
   payslip_run_state = fields.Selection(
       related='payslip_run_id.state',
       string='Batch Status',
       store=False
   )
   ```

2. **Override action_payslip_draft:**
   ```python
   def action_payslip_draft(self):
       for payslip in self:
           if payslip.payslip_run_id.state == 'cancel':
               raise UserError(...)
       return super().action_payslip_draft()
   ```

3. **Update button visibility:**
   ```xml
   <button invisible="state != 'cancel' or payslip_run_state == 'cancel'"/>
   ```

4. **Optional: Add warning banner:**
   ```xml
   <div class="alert alert-warning" 
        invisible="payslip_run_state != 'cancel'">
       This payslip belongs to a cancelled batch and cannot be modified.
   </div>
   ```

### Test Scenarios:

1. ✅ Cancelled batch, open individual payslip → "Set to Draft" button hidden
2. ✅ Try to call action_payslip_draft via code → UserError raised
3. ✅ Regular payslip (no batch) → Button works normally
4. ✅ Draft batch, cancelled payslip → Button works (can reopen)
5. ✅ Reopen batch first → Payslips become editable

## Conclusion

**Recommended:** Implement Option 1 - Add related field + validation

This provides:
- ✅ State integrity protection
- ✅ User-friendly experience  
- ✅ Standard Odoo patterns
- ✅ Minimal code changes
- ✅ Clear error messages
- ✅ Flexible (not overly restrictive)

**No need to add new "Reject" state** - it already exists as "cancel" with label "Rejected"

**Module changes needed:**
- `models/hr_payslip.py` (new file in ueipab_payroll_enhancements)
- `views/hr_payslip_view.xml` (new file in ueipab_payroll_enhancements)

**Version:** 17.0.1.3.2 (patch release)
