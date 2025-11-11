-- =====================================================
-- Sync VEB Currency Rates from Production to Testing
-- =====================================================
-- Date: 2025-11-11
-- Purpose: Copy missing VEB rates from production DB
-- Database: testing (LOCAL - NOT production!)
-- Currency: VEB (currency_id = 2)
-- Company: UEIPAB (company_id = 1)
--
-- Changes:
-- 1. Fix wrong 2025-11-11 rate (0.00432... -> 2.437636599917301)
-- 2. Insert 4 missing dates (2025-11-07 through 2025-11-10)
--
-- Safety: Uses transaction with explicit COMMIT
-- =====================================================

BEGIN;

-- Step 1: Fix wrong 2025-11-11 rate
UPDATE res_currency_rate
SET rate = 2.437636599917301
WHERE currency_id = 2
  AND name::date = '2025-11-11'
  AND company_id = 1;

-- Step 2: Insert missing dates (2025-11-07 through 2025-11-10)
INSERT INTO res_currency_rate (name, rate, currency_id, company_id, create_uid, create_date, write_uid, write_date)
VALUES
    ('2025-11-07', 2.4100613486578397, 2, 1, 2, NOW(), 2, NOW()),
    ('2025-11-08', 2.4100613486578397, 2, 1, 2, NOW(), 2, NOW()),
    ('2025-11-09', 2.4100613486578397, 2, 1, 2, NOW(), 2, NOW()),
    ('2025-11-10', 2.437134502923976, 2, 1, 2, NOW(), 2, NOW())
ON CONFLICT (name, currency_id, company_id) DO UPDATE
SET rate = EXCLUDED.rate,
    write_date = NOW(),
    write_uid = 2;

-- Verification query
SELECT
    name::date,
    rate,
    'VEB' as currency,
    company_id
FROM res_currency_rate
WHERE currency_id = 2
  AND name::date >= '2025-11-06'
ORDER BY name DESC;

-- Commit the transaction
COMMIT;

-- Final count check
SELECT COUNT(*) as total_veb_rates
FROM res_currency_rate
WHERE currency_id = 2;
