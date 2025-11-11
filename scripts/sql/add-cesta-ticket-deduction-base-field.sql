-- =====================================================================
-- SQL Migration: Add ueipab_deduction_base field to hr_contract
-- =====================================================================
-- Date: 2025-11-11
-- Module: ueipab_hr_contract
-- Version: 17.0.1.2.0
-- Purpose: Add deduction base field for Cesta Ticket separation project
--
-- CONTEXT:
-- Venezuelan labor law requires Cesta Ticket ($40 USD) to be shown
-- as a separate benefit on payslips. This requires storing the original
-- K+L (Salary+Bonus) value separately for deduction calculations.
--
-- BUSINESS REQUIREMENT:
-- - Extract $40 from Column M (Cesta Ticket) as fixed benefit
-- - Redistribute remainder: New Base = K + L + (M - $40)
-- - Calculate deductions on ORIGINAL K+L (not rebalanced amounts)
-- - Store deduction base separately from 70/25/5 distribution
--
-- DEDUCTION LOGIC (Non-standard, matches spreadsheet):
-- Monthly deductions calculated on K+L, then scaled to payslip period:
-- - IVSS (2.25%): deduction_base × 0.0225 × (period_days / 15.0)
-- - FAOV (0.5%):  deduction_base × 0.005  × (period_days / 15.0)
-- - INCES (0.125%): deduction_base × 0.00125 × (period_days / 15.0)
-- - ARI (variable): deduction_base × (rate / 100) / 2 × (period_days / 15.0)
--
-- NOTE:
-- This SQL script is for documentation and manual execution only.
-- When using Odoo ORM, the field will be auto-created/updated when
-- the ueipab_hr_contract module is upgraded.
-- =====================================================================

-- Check if field already exists (PostgreSQL 9.6+)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'hr_contract'
        AND column_name = 'ueipab_deduction_base'
    ) THEN
        -- Add the field
        ALTER TABLE hr_contract
        ADD COLUMN ueipab_deduction_base NUMERIC(16,2);

        RAISE NOTICE 'Field ueipab_deduction_base added to hr_contract table';
    ELSE
        RAISE NOTICE 'Field ueipab_deduction_base already exists in hr_contract table';
    END IF;
END $$;

-- Add comment to document field purpose
COMMENT ON COLUMN hr_contract.ueipab_deduction_base IS
'Original Column K + L value used for calculating monthly deductions. This is the base amount BEFORE 70/25/5 distribution and BEFORE extracting Cesta Ticket. Deductions (IVSS, FAOV, INCES, ARI) are calculated on this amount per spreadsheet logic. Formula: deduction_base = Column K + Column L (from payroll spreadsheet)';

-- Verification query
SELECT
    COUNT(*) as total_contracts,
    COUNT(ueipab_deduction_base) as contracts_with_deduction_base,
    AVG(ueipab_deduction_base) as avg_deduction_base,
    MIN(ueipab_deduction_base) as min_deduction_base,
    MAX(ueipab_deduction_base) as max_deduction_base
FROM hr_contract
WHERE state = 'open';

-- Show sample contracts with new field
SELECT
    e.name as employee_name,
    c.ueipab_deduction_base,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus,
    c.cesta_ticket_usd
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
AND c.ueipab_deduction_base IS NOT NULL
ORDER BY e.name
LIMIT 10;

-- =====================================================================
-- DEPLOYMENT NOTES:
-- =====================================================================
-- 1. This script is IDEMPOTENT - safe to run multiple times
-- 2. If using Odoo ORM: Just upgrade ueipab_hr_contract module
--    Command: odoo-bin -u ueipab_hr_contract -d testing
-- 3. If manual execution: Run this script via psql
--    Command: psql -U odoo -d testing -f add-cesta-ticket-deduction-base-field.sql
-- 4. After adding field, run rebalancing script to populate values:
--    python3 /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py production
-- =====================================================================

-- RELATED FILES:
-- - /opt/odoo-dev/addons/ueipab_hr_contract/models/hr_contract.py (Python model)
-- - /opt/odoo-dev/scripts/rebalance-cesta-ticket-contracts.py (Data migration)
-- - /opt/odoo-dev/documentation/CESTA_TICKET_FINAL_SOLUTION.md (Documentation)
-- =====================================================================
