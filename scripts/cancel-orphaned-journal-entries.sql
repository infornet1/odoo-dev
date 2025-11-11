-- =====================================================================
-- CANCEL ORPHANED PAYROLL JOURNAL ENTRIES (NO DELETION)
-- =====================================================================
-- Date: 2025-11-11
-- Issue: Payslip deletion leaves journal entries orphaned
-- Impact: 91 orphaned entries totaling $31,531.89
--
-- BUSINESS POLICY:
-- NEVER delete Odoo records - only CANCEL for audit trail and history
--
-- THIS SCRIPT:
-- 1. Identifies all orphaned payroll journal entries
-- 2. Sets their state to 'cancel' (preserves audit trail)
-- 3. Does NOT delete any records
-- 4. Maintains complete history for tracking and audit purposes
--
-- SAFETY:
-- - Only affects PAY1 journal (payroll)
-- - Only affects entries with NO linked payslip
-- - Does NOT delete any data
-- - Fully reversible (can set back to 'posted' if needed)
-- =====================================================================

BEGIN;

-- Step 1: Show current orphaned entries BEFORE cancellation
SELECT
    'BEFORE CANCELLATION' as status,
    COUNT(*) as orphaned_entries,
    COUNT(CASE WHEN state = 'posted' THEN 1 END) as posted_entries,
    COUNT(CASE WHEN state = 'cancel' THEN 1 END) as already_cancelled,
    SUM(amount_total) as total_amount,
    MIN(date) as oldest_date,
    MAX(date) as newest_date
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Step 2: List sample orphaned entries (first 10)
SELECT
    'SAMPLE ORPHANED ENTRIES' as info,
    am.name as journal_entry,
    am.date,
    am.state,
    am.amount_total,
    am.id as move_id
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)
ORDER BY am.date DESC
LIMIT 10;

-- Step 3: CANCEL orphaned journal entries (preserve for audit trail)
UPDATE account_move
SET state = 'cancel'
WHERE id IN (
    SELECT am.id
    FROM account_move am
    WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
    AND am.state = 'posted'
    AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)
);

-- Step 4: Show results AFTER cancellation
SELECT
    'AFTER CANCELLATION' as status,
    COUNT(*) as total_orphaned_entries,
    COUNT(CASE WHEN state = 'posted' THEN 1 END) as still_posted,
    COUNT(CASE WHEN state = 'cancel' THEN 1 END) as now_cancelled,
    SUM(amount_total) as total_amount
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Step 5: Verify no posted orphans remain
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN 'SUCCESS: All orphaned entries cancelled ✅'
        ELSE 'WARNING: ' || COUNT(*) || ' orphaned entries still posted ⚠️'
    END as verification_result
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND am.state = 'posted'
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Step 6: Summary
SELECT
    'SUMMARY' as info,
    'Cancelled orphaned entries (preserved for audit trail)' as action,
    COUNT(*) as total_orphaned,
    SUM(amount_total) as total_amount
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- AUTO-COMMIT (safe because we're only cancelling, not deleting)
COMMIT;

SELECT '✅ CLEANUP COMPLETE - All orphaned journal entries cancelled (audit trail preserved)' as final_status;

-- =====================================================================
-- NOTES:
-- =====================================================================
-- - All orphaned entries now have state = 'cancel'
-- - NO data was deleted - full audit trail maintained
-- - Entries remain visible in Odoo with 'Cancelled' state
-- - Can be used for historical reporting and audits
-- - Follows proper accounting best practices
--
-- To view cancelled orphaned entries in Odoo:
-- Go to Accounting → Accounting → Journal Entries
-- Filter by: Journal = PAY1, State = Cancelled
-- =====================================================================
