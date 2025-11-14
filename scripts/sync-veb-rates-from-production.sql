-- =====================================================
-- Sync VEB Currency Rates from Production to Testing
-- =====================================================
-- Date: 2025-11-14
-- Purpose: Copy missing VEB rates from production DB
-- Database: testing (LOCAL - NOT production!)
-- Currency: VEB (currency_id = 2)
-- Company: UEIPAB (company_id = 1)
--
-- Production: ueipab17_postgres_1 container @ 10.124.0.3
-- Production DB: DB_UEIPAB
--
-- Changes:
-- Insert 3 missing dates (2025-11-12 through 2025-11-14)
--   Production: 622 rates (latest: 2025-11-14)
--   Testing:    619 rates (latest: 2025-11-11)
--   Missing:    3 rates
--
-- Safety: Uses transaction with explicit COMMIT
-- =====================================================

BEGIN;

-- Insert missing VEB rates (2025-11-12 through 2025-11-14)
INSERT INTO res_currency_rate (name, rate, currency_id, company_id, create_uid, create_date, write_uid, write_date)
VALUES
    ('2025-11-12', 2.458226795946094, 2, 1, 2, NOW(), 2, NOW()),
    ('2025-11-13', 2.463625393449955, 2, 1, 2, NOW(), 2, NOW()),
    ('2025-11-14', 2.477484747221589, 2, 1, 2, NOW(), 2, NOW())
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
