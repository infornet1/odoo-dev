# Currency Rate Synchronization Protocol

**Date:** 2025-11-11
**Context:** Syncing VEB currency rates between production and testing environments

## Critical Rules

### 🚨 NEVER TOUCH PRODUCTION DATABASE WITHOUT AUTHORIZATION

**Production Database:**
- Location: 10.124.0.3 (remote server)
- Container: ueipab17_postgres_1
- Database: DB_UEIPAB
- **Access:** READ ONLY unless explicitly authorized by user

**Testing Database:**
- Location: localhost (local Docker)
- Container: odoo-dev-postgres
- Database: testing
- **Access:** Full read/write for development

## Synchronization Script

**Script Location:** `/opt/odoo-dev/scripts/sync-veb-rates-from-production.sql`

**Purpose:** Copy missing VEB currency rates from production to testing

**Usage Pattern:**
1. User identifies that production has more currency rates than testing
2. User requests sync operation
3. Check rate counts in both databases
4. Identify missing dates in testing
5. Query production for correct rates
6. Execute sync script on testing database ONLY
7. Verify synchronization success

## Standard Sync Workflow

### Step 1: Check Rate Counts

```bash
# Testing database
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT COUNT(*) as testing_veb_rates
FROM res_currency_rate
WHERE currency_id = 2;
"

# Production database (READ ONLY)
sshpass -p 'g)9nE>?rq-#v3Hn' ssh -o StrictHostKeyChecking=no root@10.124.0.3 \
"docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c \"
SELECT COUNT(*) as production_veb_rates
FROM res_currency_rate
WHERE currency_id = 2;
\""
```

### Step 2: Identify Missing Dates

```bash
# Export production dates
sshpass -p 'g)9nE>?rq-#v3Hn' ssh root@10.124.0.3 \
"docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -t -c \"
SELECT name::date FROM res_currency_rate WHERE currency_id = 2 ORDER BY name;
\"" > /tmp/production_dates.txt

# Export testing dates
docker exec odoo-dev-postgres psql -U odoo -d testing -t -c "
SELECT name::date FROM res_currency_rate WHERE currency_id = 2 ORDER BY name;
" > /tmp/testing_dates.txt

# Find differences
comm -23 <(sort /tmp/production_dates.txt | tr -d ' ') \
         <(sort /tmp/testing_dates.txt | tr -d ' ') | grep -v '^$'
```

### Step 3: Query Production for Correct Rates

```bash
# Get rates for missing dates (READ ONLY query)
sshpass -p 'g)9nE>?rq-#v3Hn' ssh root@10.124.0.3 \
"docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c \"
SELECT name::date, rate, company_id, currency_id
FROM res_currency_rate
WHERE currency_id = 2 AND name::date IN ('YYYY-MM-DD', ...)
ORDER BY name;
\""
```

### Step 4: Execute Sync Script

```bash
# Apply to testing database ONLY
docker exec -i odoo-dev-postgres psql -U odoo -d testing < \
  /opt/odoo-dev/scripts/sync-veb-rates-from-production.sql
```

### Step 5: Verify Success

```bash
# Verify rate count matches
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT COUNT(*) FROM res_currency_rate WHERE currency_id = 2;
"

# Verify recent rates are correct
docker exec odoo-dev-postgres psql -U odoo -d testing -c "
SELECT name::date, rate FROM res_currency_rate
WHERE currency_id = 2 AND name >= CURRENT_DATE - 7
ORDER BY name DESC;
"
```

## Currency Rate Storage Format

**Table:** `res_currency_rate`

**Fields:**
- `name` (timestamp) - Date of the rate
- `rate` (numeric) - Exchange rate value
- `currency_id` (integer) - Foreign key to res.currency (VEB = 2)
- `company_id` (integer) - Foreign key to res.company (UEIPAB = 1)

**Important:** Odoo stores rates in a specific format. DO NOT calculate or invert rates manually. Always copy the exact rate value from production.

**Example VEB Rates:**
```
Date        | Rate (stored value) | Notes
------------|---------------------|------------------------
2025-11-11  | 2.437636599917301  | Latest rate
2025-11-10  | 2.437134502923976  | Previous day
2025-11-09  | 2.4100613486578397 | Weekend rate (same)
2025-11-06  | 2.4003263630456613 | Earlier rate
```

**DO NOT:**
- Calculate rates as 1/X or X/1
- Assume inverse relationships
- Modify rate format or precision
- Guess rate values

**ALWAYS:**
- Copy exact rate values from production
- Use READ ONLY queries on production
- Apply changes to testing only
- Verify results after sync

## Historical Context

**Issue:** Previous attempts to update currency rates failed because:
1. Misunderstood Odoo's rate storage format
2. Calculated rates manually instead of copying from production
3. Accidentally touched production database

**Solution:**
- Created standardized sync script
- Established clear protocol: READ production, WRITE testing
- Document exact rate values from production

## Sync Script Template

The sync script (`scripts/sync-veb-rates-from-production.sql`) follows this pattern:

```sql
BEGIN;

-- Fix any incorrect rates
UPDATE res_currency_rate
SET rate = [EXACT_VALUE_FROM_PRODUCTION]
WHERE currency_id = 2
  AND name::date = 'YYYY-MM-DD'
  AND company_id = 1;

-- Insert missing rates
INSERT INTO res_currency_rate (name, rate, currency_id, company_id, create_uid, create_date, write_uid, write_date)
VALUES
    ('YYYY-MM-DD', [EXACT_RATE], 2, 1, 2, NOW(), 2, NOW())
ON CONFLICT (name, currency_id, company_id) DO UPDATE
SET rate = EXCLUDED.rate,
    write_date = NOW(),
    write_uid = 2;

-- Verification
SELECT name::date, rate, currency_id, company_id
FROM res_currency_rate
WHERE currency_id = 2 AND name >= CURRENT_DATE - 7
ORDER BY name DESC;

COMMIT;
```

## Success Criteria

After successful sync:
- ✅ Testing rate count matches production
- ✅ All recent rates match production exactly
- ✅ No errors in verification query
- ✅ Production database untouched
- ✅ Audit trail maintained

## Emergency Rollback

If wrong rates are applied to testing:

```sql
BEGIN;

-- Rollback specific date
UPDATE res_currency_rate
SET rate = [CORRECT_VALUE]
WHERE currency_id = 2
  AND name::date = 'YYYY-MM-DD'
  AND company_id = 1;

-- Verify
SELECT * FROM res_currency_rate
WHERE currency_id = 2 AND name::date = 'YYYY-MM-DD';

COMMIT;
```

## Key Takeaways

1. **Production is READ ONLY** - Never write to DB_UEIPAB without explicit authorization
2. **Use the sync script** - Don't manually calculate or update rates
3. **Copy exact values** - Odoo's rate format is internal, don't interpret it
4. **Verify everything** - Check counts and values before and after
5. **Transaction safety** - Always use BEGIN/COMMIT for rollback capability

**Last Sync:** 2025-11-11 (619 VEB rates synced)
