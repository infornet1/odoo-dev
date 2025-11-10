-- ============================================================================
-- ADD MONTHLY SALARY TRACKING FIELDS TO HR_CONTRACT
-- ============================================================================
-- Purpose: Add dual system for tracking spreadsheet-based salary
--          without affecting existing payroll structure
-- Date: November 9, 2025
-- Database: Production (10.124.0.3 - testing)
-- ============================================================================

-- Step 1: Add new columns
ALTER TABLE hr_contract
ADD COLUMN IF NOT EXISTS ueipab_monthly_salary NUMERIC(12,2),
ADD COLUMN IF NOT EXISTS ueipab_salary_notes TEXT;

-- Step 2: Add column documentation
COMMENT ON COLUMN hr_contract.ueipab_monthly_salary IS
'Total monthly salary from payroll spreadsheet (Column K in USD).
Used for Aguinaldos, year-end bonuses, and other special calculations.
This field tracks the official salary independent of the 70/25/5 distribution used for regular payroll.
Synced from Google Sheets using sync-monthly-salary-from-spreadsheet.py script.';

COMMENT ON COLUMN hr_contract.ueipab_salary_notes IS
'Complete audit trail for ueipab_monthly_salary including:
- Source spreadsheet and date
- Column reference
- Original VEB amount
- Exchange rate used

Format: "From payroll sheet {date}, Column K ({veb} VEB) @ {rate} VEB/USD"

Example: "From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD"

This provides complete traceability and allows verification of calculations at any time.';

-- Step 3: Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_hr_contract_monthly_salary
ON hr_contract(ueipab_monthly_salary)
WHERE ueipab_monthly_salary IS NOT NULL;

-- Step 4: Create index on notes for text search (if needed)
CREATE INDEX IF NOT EXISTS idx_hr_contract_salary_notes
ON hr_contract USING gin(to_tsvector('english', ueipab_salary_notes))
WHERE ueipab_salary_notes IS NOT NULL;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify columns were created
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'hr_contract'
  AND column_name IN ('ueipab_monthly_salary', 'ueipab_salary_notes')
ORDER BY column_name;

-- Verify indexes were created
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'hr_contract'
  AND indexname LIKE '%monthly_salary%';

-- Check current contract structure
SELECT
    e.name as employee,
    c.wage as standard_wage,
    c.ueipab_salary_base as payroll_base_70,
    c.ueipab_bonus_regular as payroll_bonus_25,
    c.ueipab_extra_bonus as payroll_extra_5,
    c.ueipab_monthly_salary as new_monthly_field,
    c.ueipab_salary_notes as new_notes_field
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
ORDER BY e.name
LIMIT 5;

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================
-- Uncomment the following lines if you need to rollback these changes:

-- DROP INDEX IF EXISTS idx_hr_contract_salary_notes;
-- DROP INDEX IF EXISTS idx_hr_contract_monthly_salary;
-- ALTER TABLE hr_contract DROP COLUMN IF EXISTS ueipab_salary_notes;
-- ALTER TABLE hr_contract DROP COLUMN IF EXISTS ueipab_monthly_salary;

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

SELECT '✓ Monthly salary tracking fields added successfully!' as status;
SELECT 'Next step: Run sync-monthly-salary-from-spreadsheet.py to populate data' as next_action;
