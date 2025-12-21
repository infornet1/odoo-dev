# Batch Email Progress Wizard

**Status:** PRODUCTION | **Deployed:** 2025-12-16 | **Module Version:** v1.47.0

## Problem Solved

When clicking "Send Payslips by Email" on batch form:
- No progress indicator during sending
- No feedback on success/failure per employee
- No error reporting if emails fail
- User doesn't know when process completes

## Solution Implemented

Progress wizard with real-time feedback.

**New Button:** "Send Emails (with Progress)" on batch form (alongside existing button)

## Wizard Features

- Progress bar showing percentage complete
- Real-time stats: Sent, No Email, Failed
- Results table with status icons per employee
- "Failed Only" tab for quick error review
- Color-coded rows (green=sent, orange=no email, red=error)
- Error messages captured for each failure

## User Flow

```
1. Open Payslip Batch form
2. Click "Send Emails (with Progress)" button
3. Select email template (defaults to batch template)
4. Click "Start Sending"
5. Click "Process All Remaining" to send all at once
6. Review results in summary table
7. Check "Failed Only" tab if issues occurred
```

## Files Created

- `wizard/batch_email_wizard.py` - Two TransientModels:
  - `hr.payslip.batch.email.wizard` - Main wizard
  - `hr.payslip.batch.email.result` - Per-payslip result tracking
- `wizard/batch_email_wizard_view.xml` - Wizard form view with tabs

## Files Modified

- `wizard/__init__.py` - Added import
- `views/hr_payslip_run_view.xml` - Added button (action ID 850)
- `security/ir.model.access.csv` - Added access rules
- `__manifest__.py` - Updated version, added XML file

## Testing Notes

- All tests used `env.cr.rollback()` - no actual emails sent
- Tested: wizard creation, progress tracking, no-email detection, error capture
- Ready for manual testing in browser
