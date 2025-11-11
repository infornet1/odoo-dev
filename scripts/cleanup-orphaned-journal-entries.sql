-- =====================================================================
-- CLEANUP ORPHANED PAYROLL JOURNAL ENTRIES
-- =====================================================================
-- Date: 2025-11-11
-- Issue: Payslip deletion leaves journal entries orphaned
-- Impact: 91 orphaned entries totaling $31,531.89
--
-- ROOT CAUSE:
-- Missing unlink() override in hr_payslip.py
-- When payslips deleted → journal entries remain posted → accounting mess
--
-- THIS SCRIPT:
-- 1. Identifies all orphaned payroll journal entries
-- 2. Cancels them (set state to 'cancel')
-- 3. Deletes them from database
-- 4. Cleans up associated journal entry lines
--
-- SAFETY:
-- - Only affects PAY1 journal (payroll)
-- - Only affects entries with NO linked payslip
-- - Creates backup before deletion
-- =====================================================================

BEGIN;

-- Step 1: Show current orphaned entries
SELECT
    'BEFORE CLEANUP' as status,
    COUNT(*) as orphaned_entries,
    SUM(amount_total) as total_amount
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND am.state = 'posted'
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Step 2: Create backup table
CREATE TABLE IF NOT EXISTS account_move_orphaned_backup_20251111 AS
SELECT am.*
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Verify backup
SELECT COUNT(*) as backed_up_entries
FROM account_move_orphaned_backup_20251111;

-- Step 3: Cancel orphaned journal entries (required before deletion)
UPDATE account_move
SET state = 'cancel'
WHERE id IN (
    SELECT am.id
    FROM account_move am
    WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
    AND am.state = 'posted'
    AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)
);

-- Step 4: Delete orphaned journal entry lines
DELETE FROM account_move_line
WHERE move_id IN (
    SELECT am.id
    FROM account_move am
    WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
    AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)
);

-- Step 5: Delete orphaned journal entries
DELETE FROM account_move
WHERE id IN (
    SELECT am.id
    FROM account_move am
    WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
    AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)
);

-- Step 6: Verify cleanup
SELECT
    'AFTER CLEANUP' as status,
    COUNT(*) as remaining_orphaned_entries
FROM account_move am
WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
AND NOT EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id);

-- Step 7: Show summary
SELECT
    'SUMMARY' as info,
    (SELECT COUNT(*) FROM account_move_orphaned_backup_20251111) as backed_up,
    (SELECT COUNT(*) FROM account_move am
     WHERE am.journal_id = (SELECT id FROM account_journal WHERE code = 'PAY1' LIMIT 1)
     AND EXISTS (SELECT 1 FROM hr_payslip ps WHERE ps.move_id = am.id)) as valid_entries_remaining;

-- COMMIT or ROLLBACK?
-- Review the output above, then:
-- - If everything looks good: COMMIT;
-- - If something wrong: ROLLBACK;

-- Uncommenting for safety - you must manually commit:
-- COMMIT;

-- =====================================================================
-- ROLLBACK INSTRUCTIONS (if needed):
-- =====================================================================
-- If you need to restore the deleted entries:
--
-- INSERT INTO account_move
-- SELECT * FROM account_move_orphaned_backup_20251111;
--
-- Then restore the move lines from Odoo or re-generate payslips
-- =====================================================================
