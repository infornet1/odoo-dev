# Send Mail Button Bug - Diagnosis Report

**Date:** 2025-11-22
**Module:** `hr_payslip_monthly_report` v17.0.1.0
**Reported By:** User
**Status:** 🔴 CRITICAL BUG - Button disappears after cancelling email

---

## Problem Description

When a user clicks the "Send Mail" button on a payslip form:

1. ✅ Email compose wizard opens correctly
2. ❌ If user **cancels** the wizard (doesn't send email)
3. ❌ Button **disappears** and never comes back
4. ❌ Payslip is marked as "email sent" even though it wasn't

**Expected Behavior:**
- Button should remain visible if email is not actually sent
- `is_send_mail` flag should only be set to `True` when email is successfully sent

**Actual Behavior:**
- Button disappears immediately when clicked
- `is_send_mail` flag is set to `True` before email wizard opens
- Cancelling wizard doesn't reset the flag

---

## Root Cause Analysis

### Code Location
**File:** `/opt/odoo-dev/addons/hr_payslip_monthly_report/models/hr_payslip.py`
**Method:** `action_payslip_send()` (lines 55-87)

### The Bug (Line 59)

```python
def action_payslip_send(self):
    """Opens a window to compose an email,
    with template message loaded by default"""
    self.ensure_one()
    self.write({'is_send_mail': True})  # 🔴 BUG: Sets flag IMMEDIATELY!
    # ... opens email wizard ...
    return {
        'name': _('Compose Email'),
        'type': 'ir.actions.act_window',
        # ... wizard configuration ...
    }
```

### Execution Flow (Current - BUGGY)

```
1. User clicks "Send Mail" button
   ↓
2. action_payslip_send() is called
   ↓
3. 🔴 is_send_mail = True (WRITTEN TO DATABASE)
   ↓
4. Button visibility condition evaluates:
   invisible="is_send_mail == True"  → Button HIDDEN
   ↓
5. Email wizard opens (return action window)
   ↓
6. User CANCELS wizard
   ↓
7. 🔴 is_send_mail STAYS True (email never sent!)
   ↓
8. Button remains HIDDEN forever
```

### Why This Happens

The button has this visibility condition in the XML view:

```xml
<button string="Send Mail"
        name="action_payslip_send"
        type="object"
        class="oe_highlight"
        invisible="is_send_mail == True"/>
```

**The problem:**
- Line 59 sets `is_send_mail = True` **BEFORE** opening the wizard
- Odoo re-renders the view with updated field value
- Button becomes invisible **immediately**
- If wizard is cancelled, field stays `True` but email was never sent
- No way to show button again (record is "permanently marked as sent")

---

## Impact Assessment

**Severity:** 🔴 HIGH

**Affected Users:**
- Any user who clicks "Send Mail" but cancels the wizard
- Payslip is permanently marked as "sent" even if email was never delivered

**Data Integrity:**
- `is_send_mail` field becomes unreliable
- No way to know if email was actually sent or just button was clicked

**User Experience:**
- Confusing behavior (button disappears before action completes)
- No way to retry sending email after cancellation
- Must manually reset field via developer mode or database

---

## Expected vs Actual Behavior

### ✅ Expected Flow (Correct)

```
1. User clicks "Send Mail"
   ↓
2. Open email wizard (is_send_mail still FALSE)
   ↓
3. User sends email
   ↓
4. Email sent successfully
   ↓
5. SET is_send_mail = True
   ↓
6. Button hidden (correct - email was sent)
```

### ❌ Actual Flow (Buggy)

```
1. User clicks "Send Mail"
   ↓
2. SET is_send_mail = True (TOO EARLY!)
   ↓
3. Button hidden immediately
   ↓
4. Open email wizard
   ↓
5. User CANCELS
   ↓
6. is_send_mail stays True (WRONG!)
   ↓
7. Button stays hidden forever
```

---

## Comparison with Auto-Send Feature

The **automatic send on confirm** (lines 37-53) works correctly:

```python
def action_payslip_done(self):
    if self.env['ir.config_parameter'].sudo().get_param('send_payslip_by_email'):
        self.write({'is_send_mail': True})  # Set flag BEFORE send
    res = super(HrPayslip, self).action_payslip_done()
    if self.env['ir.config_parameter'].sudo().get_param('send_payslip_by_email'):
        for payslip in self:
            if payslip.employee_id.private_email:
                template.sudo().send_mail(payslip.id, force_send=True)
                # Email ACTUALLY SENT
    return res
```

**Why auto-send works:**
- Flag is set AND email is sent in the same transaction
- User doesn't have opportunity to cancel
- No wizard involved - direct send

**Why manual send fails:**
- Flag is set in method
- Wizard is returned (but not executed yet)
- User can cancel wizard
- No callback to reset flag on cancel

---

## Technical Details

### Odoo Wizard Behavior

When you return an `ir.actions.act_window` with `target='new'`:

1. Method executes completely (including `self.write()`)
2. Database changes are committed
3. View is re-rendered with new field values
4. THEN wizard window opens
5. Wizard actions (send/cancel) happen in SEPARATE transaction
6. No automatic rollback if wizard is cancelled

### Button Visibility

The `invisible` attribute is reactive:
- Evaluates whenever record fields change
- Once `is_send_mail = True`, button hides
- No mechanism to show button again

---

## Workaround for Users (Until Fixed)

If you accidentally clicked "Send Mail" and cancelled:

### Option 1: Developer Mode (GUI)
1. Enable Developer Mode
2. Open the payslip form
3. Click "View Metadata"
4. Find `is_send_mail` field
5. Manually change to `False`

### Option 2: Odoo Shell (Database)
```python
slip = env['hr.payslip'].browse(PAYSLIP_ID)
slip.write({'is_send_mail': False})
env.cr.commit()
```

### Option 3: Direct SQL (Emergency)
```sql
UPDATE hr_payslip
SET is_send_mail = false
WHERE id = PAYSLIP_ID;
```

---

## Recommended Fix (DO NOT IMPLEMENT YET)

**Strategy:** Use a callback mechanism or remove premature flag setting

### Option A: Remove premature flag setting
```python
def action_payslip_send(self):
    self.ensure_one()
    # DON'T set is_send_mail here!
    # self.write({'is_send_mail': True})  # ← REMOVE THIS
    # ... rest of wizard code ...
```

Then set flag in the wizard's send action or via template callback.

### Option B: Create custom wizard
- Create a custom wizard model
- Set `is_send_mail = True` only in wizard's `action_send_mail()` method
- Button stays visible until actual send

### Option C: Change button logic
- Remove `invisible` condition
- Change button text based on state: "Send Mail" vs "Resend Mail"
- Allow multiple sends

---

## Files Involved

```
/opt/odoo-dev/addons/hr_payslip_monthly_report/
├── models/
│   └── hr_payslip.py               # 🔴 Bug on line 59
├── views/
│   └── hr_payslip_views.xml        # Button definition with invisible condition
└── __manifest__.py
```

---

## Reproduction Steps

1. Open any payslip with `is_send_mail = False`
2. Click "Send Mail" button (appears in blue)
3. Observe: Email compose wizard opens
4. Observe: Button has already disappeared from background form
5. Click "Discard" or "Cancel" in wizard
6. Result: Button does not reappear
7. Check field value: `is_send_mail = True` (but no email was sent!)

---

## Verification Script

```python
# Check a payslip's send status
slip = env['hr.payslip'].browse(SLIP_ID)
print(f"Number: {slip.number}")
print(f"is_send_mail: {slip.is_send_mail}")

# Check actual sent emails
mails = env['mail.mail'].search([
    ('model', '=', 'hr.payslip'),
    ('res_id', '=', slip.id)
])
print(f"Actual emails sent: {len(mails)}")

# Compare
if slip.is_send_mail and len(mails) == 0:
    print("🔴 BUG CONFIRMED: Flag is True but no email exists!")
```

---

## Conclusion

This is a **design flaw** in the Cybrosys module where the `is_send_mail` flag is set too early in the process. The flag should only be set after email is successfully sent, not when opening the compose wizard.

**Recommendation:** Fix should be implemented to either:
1. Remove line 59 (`self.write({'is_send_mail': True})`)
2. Set flag via email template callback after successful send
3. Create custom wizard with proper lifecycle management

**Priority:** HIGH - Affects data integrity and user experience

---

**Status:** Diagnosis complete, awaiting approval to implement fix.
