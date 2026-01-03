# Batch Email Progress Wizard

**Status:** PRODUCTION | **Updated:** 2026-01-02 | **Module Version:** v1.51.1

## Problem Solved

When clicking "Send Payslips by Email" on batch form:
- No progress indicator during sending
- No feedback on success/failure per employee
- No error reporting if emails fail
- User doesn't know when process completes
- **No control over which employees receive emails**

## Solution Implemented

Enhanced progress wizard with employee selection and real-time feedback.

**Button:** "Send Emails (with Progress)" on batch form

## Wizard Features

### Employee Selection (v1.51.1 Enhancement)
- **Pre-send selection screen**: Choose which employees to email before sending
- **Toggle controls**: Select/Deselect individual employees
- **Bulk actions**: "Select All", "Deselect All", "Select With Email Only"
- **Visual indicators**: Green checkmark for valid email, red X for missing email
- **No automatic sending**: User must explicitly confirm before any emails are sent

### Progress Tracking
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
3. SELECT STATE: Choose employees to email
   - Use toggles to select/deselect individuals
   - Use bulk buttons: "Select All", "Deselect All", "Select With Email Only"
   - Employees without email are highlighted and cannot receive emails
   - Click "Continue" when ready
4. CONFIRM STATE: Review selection
   - Shows list of selected employees
   - Click "Send Emails Now" to proceed
   - Click "Back to Selection" to modify
5. SENDING STATE: Emails are sent
   - Progress bar updates in real-time
   - Results table shows status per employee
6. DONE STATE: Review results
   - Summary of sent/failed/no-email counts
   - "Failed Only" tab for troubleshooting
   - Click "Close" to finish
```

## Wizard States

| State | Description | Actions Available |
|-------|-------------|-------------------|
| `select` | Choose employees | Select All, Deselect All, Select With Email, Continue |
| `confirm` | Review before sending | Send Emails Now, Back to Selection |
| `sending` | Processing emails | (automatic) |
| `done` | Complete | Close |

## Technical Models

### Main Wizard: `hr.payslip.batch.email.wizard`
- `payslip_run_id`: Link to batch
- `email_template_id`: Email template to use
- `state`: Current wizard state
- `selection_ids`: One2many to selection lines
- `result_ids`: One2many to result lines
- Progress counters: `processed_count`, `sent_count`, `failed_count`, `no_email_count`

### Selection Model: `hr.payslip.batch.email.selection`
- `wizard_id`: Link to wizard
- `payslip_id`: Link to payslip (Many2one)
- `payslip_id_int`: Payslip ID (Integer, for reliability across form submissions)
- `employee_name`, `employee_email`: Cached employee data
- `has_email`: Boolean for email availability
- `selected`: Boolean toggle for sending

### Result Model: `hr.payslip.batch.email.result`
- `wizard_id`: Link to wizard
- `payslip_id`: Link to payslip (Many2one)
- `payslip_id_int`: Payslip ID (Integer, for reliability)
- `employee_name`, `employee_email`: Cached data
- `status`: pending, sending, sent, no_email, error
- `error_message`: Captured error details

## Files

### Created
- `wizard/batch_email_wizard.py` - Three TransientModels (wizard, selection, result)
- `wizard/batch_email_wizard_view.xml` - Multi-state wizard form

### Modified
- `wizard/__init__.py` - Added import
- `views/hr_payslip_run_view.xml` - Added button
- `security/ir.model.access.csv` - Access rules for all three models
- `__manifest__.py` - Version updates

## Technical Notes

### Transient Model Data Persistence
The wizard uses integer fields (`payslip_id_int`) alongside Many2one fields to ensure reliable data persistence across form submissions in transient models. This prevents "Payslip not found" errors that can occur when Many2one relationships are lost during wizard state transitions.

### Fallback Mechanism
If payslip ID is missing, the code falls back to looking up the payslip from the batch using the employee name, ensuring emails can still be sent.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.47.0 | 2025-12-16 | Initial release with progress tracking |
| v1.51.1 | 2026-01-02 | Added employee selection before sending |
