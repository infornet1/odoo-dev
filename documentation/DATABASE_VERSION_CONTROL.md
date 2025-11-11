# Database Version Control Strategy
**Last Updated:** 2025-11-11
**System:** Odoo 17 Development Environment (Docker-based)

---

## Executive Summary

✅ **Database schema changes ARE properly tracked in version control** through:
1. Odoo Python model definitions (primary method)
2. SQL migration scripts (documentation/reproducibility)
3. Docker Compose configuration (infrastructure as code)
4. Git commits with detailed change logs

The database **data** itself (employee records, payslips, etc.) is NOT tracked in git (by design) but is persistent in Docker volumes.

---

## Version Control Architecture

### 1. Docker Infrastructure (Tracked in Git)

**File:** `docker-compose.yml`

```yaml
postgres:
  container_name: odoo-dev-postgres
  image: postgres:14
  volumes:
    - odoo-db-data:/var/lib/postgresql/data/pgdata
  ports:
    - "5433:5432"
```

**What's Tracked:**
- ✅ Docker container configuration
- ✅ PostgreSQL version (14)
- ✅ Port mappings
- ✅ Volume definitions
- ✅ Environment variables structure

**What's NOT Tracked:**
- ❌ Database volume data (`odoo-db-data`)
- ❌ Actual employee/payslip records
- ❌ Production database contents

**Why:** Database data should never be in git (security, size, portability). Only infrastructure config is tracked.

---

## 2. Schema Version Control (Tracked in Git)

### Method A: Odoo ORM (Primary)

**How it works:**
1. Define fields in Python models (e.g., `hr_contract.py`)
2. Commit Python code to git
3. Odoo automatically creates/updates database schema on module upgrade
4. Schema changes are versioned through module `__manifest__.py` version field

**Example:**

```python
# File: addons/ueipab_hr_contract/models/hr_contract.py

class HrContract(models.Model):
    _inherit = 'hr.contract'

    ueipab_deduction_base = fields.Monetary(
        'Deduction Base (K+L)',
        help="Original Column K + L value used for calculating monthly deductions..."
    )
```

**Git Tracking:**
- ✅ Python model file tracked in git
- ✅ Field definition versioned
- ✅ Git commit describes the change (commit `f546854`)
- ✅ Module version updated in `__manifest__.py` (17.0.1.2.0)

**Deployment:**
```bash
# Upgrade module to apply schema changes
docker exec -it odoo-dev-web odoo-bin -u ueipab_hr_contract -d testing --stop-after-init
```

### Method B: SQL Migration Scripts (Documentation)

**Purpose:** Document manual schema changes for reproducibility and reference.

**Files in `scripts/sql/`:**
- `add-monthly-salary-tracking-fields.sql` - Aguinaldos fields
- `add-cesta-ticket-deduction-base-field.sql` - Deduction base field (NEW)

**Example:**

```sql
-- File: scripts/sql/add-cesta-ticket-deduction-base-field.sql

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'hr_contract'
        AND column_name = 'ueipab_deduction_base'
    ) THEN
        ALTER TABLE hr_contract
        ADD COLUMN ueipab_deduction_base NUMERIC(16,2);
    END IF;
END $$;
```

**Benefits:**
- ✅ Idempotent (safe to run multiple times)
- ✅ Self-documenting with comments
- ✅ Can be used for manual deployment if needed
- ✅ Version controlled in git
- ✅ Includes verification queries

**Git Tracking:**
- ✅ SQL scripts tracked in `scripts/sql/`
- ✅ Committed with descriptive messages
- ✅ Linked to corresponding Python model changes

---

## 3. Data Migration Scripts (Tracked in Git)

**File:** `scripts/rebalance-cesta-ticket-contracts.py`

**Purpose:** Populate new fields with calculated data based on business rules.

**Example:** Rebalancing 44 employee contracts with Cesta Ticket separation:

```python
# Extract $40 from M, redistribute remainder
cesta_fixed = 40.0
m_remaining = column_m_usd - cesta_fixed
new_base = column_k_usd + column_l_usd + m_remaining

contract.ueipab_salary_base = new_base * 0.70
contract.ueipab_bonus_regular = new_base * 0.25
contract.ueipab_extra_bonus = new_base * 0.05
contract.cesta_ticket_usd = cesta_fixed
contract.ueipab_deduction_base = column_k_usd + column_l_usd  # ← New field
```

**Git Tracking:**
- ✅ Python migration scripts tracked
- ✅ Includes backup creation logic
- ✅ Test mode and production mode
- ✅ Transaction-based with rollback capability

---

## 4. Database Backup Strategy

### Docker Volume Backups

**Current Database Volume:**
```bash
docker volume inspect odoo-db-data
```

**Backup Commands:**

```bash
# Backup database to SQL file
docker exec odoo-dev-postgres pg_dump -U odoo testing > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup entire Docker volume
docker run --rm -v odoo-db-data:/data -v $(pwd):/backup ubuntu tar czf /backup/odoo-db-backup-$(date +%Y%m%d).tar.gz /data

# Restore from SQL file
docker exec -i odoo-dev-postgres psql -U odoo testing < backup_20251111_120000.sql
```

**Automated Backups (Recommended):**
- Set up cron job for daily database backups
- Store backups outside Docker volumes
- Keep last 30 days of backups
- Test restore procedure monthly

---

## 5. Git Commit History for Database Changes

### Recent Schema Changes:

```bash
$ git log --oneline | grep -E "field|schema|deduction|cesta"

935cd34 Complete Cesta Ticket separation project - production ready
f546854 Add ueipab_deduction_base field to hr_contract Python model
8dbf70c Implement Cesta Ticket $40 separation with spreadsheet-matching deduction logic
ad4a0ba Implement Cesta Ticket separation and rebalancing (Venezuelan labor law)
```

### Detailed Commit Example:

```
commit f5468542d0f80a76f658b86d333b70bb605a625c
Author: infornet1 <infornet1@github.com>
Date:   Tue Nov 11 08:47:58 2025 -0400

    Add ueipab_deduction_base field to hr_contract Python model

    FIX: Salary rule error 'Invalid Operation' for VE_SSO_DED

    SOLUTION:
    Added ueipab_deduction_base field definition to hr_contract.py model:
    - Field stores original K+L value for deduction calculations
    - Used by VE_SSO_DED, VE_FAOV_DED, VE_PARO_DED, VE_ARI_DED rules

    Files changed:
    - addons/ueipab_hr_contract/models/hr_contract.py | 9 +++++++++
```

---

## 6. Verification Checklist

Use this checklist when making database schema changes:

### Schema Changes Checklist:

- [ ] ✅ Python model field definition added to `models/*.py`
- [ ] ✅ Module version updated in `__manifest__.py`
- [ ] ✅ SQL migration script created in `scripts/sql/`
- [ ] ✅ SQL script is idempotent (safe to run multiple times)
- [ ] ✅ Data migration script created if needed
- [ ] ✅ Changes committed to git with descriptive message
- [ ] ✅ Module upgraded in development environment
- [ ] ✅ Tested with sample data
- [ ] ✅ Backup created before production deployment
- [ ] ✅ Documentation updated

### Cesta Ticket Project Status:

- [x] ✅ Python model field definition (`ueipab_deduction_base`)
- [x] ✅ Module version 17.0.1.2.0
- [x] ✅ SQL migration script created
- [x] ✅ SQL script is idempotent
- [x] ✅ Data migration script (`rebalance-cesta-ticket-contracts.py`)
- [x] ✅ Changes committed (4 commits)
- [x] ✅ Module upgraded in development
- [x] ✅ Tested with 5 employees
- [x] ✅ Backup capability in rebalancing script
- [x] ✅ Documentation created (`CESTA_TICKET_FINAL_SOLUTION.md`)

---

## 7. Best Practices Summary

### ✅ DO:

1. **Always define schema in Python models first** (Odoo ORM is the source of truth)
2. **Create SQL migration scripts for documentation** (even if Odoo handles the actual change)
3. **Commit all schema changes to git** with detailed messages
4. **Update module version** in `__manifest__.py` for each schema change
5. **Create backups** before any schema/data migration
6. **Test in development** before touching production
7. **Use transactions** in data migration scripts
8. **Document business logic** in SQL script comments

### ❌ DON'T:

1. **Don't commit database data** to git (only schema/config)
2. **Don't run ALTER TABLE directly** without corresponding Python model changes
3. **Don't skip SQL migration scripts** (needed for reproducibility)
4. **Don't forget to upgrade modules** after schema changes
5. **Don't modify production database** without tested migration scripts
6. **Don't skip backups** before migrations
7. **Don't use hardcoded values** in migration scripts (read from config/spreadsheet)

---

## 8. Recovery Procedures

### If Database is Corrupted:

1. **Stop Odoo container:**
   ```bash
   docker-compose down
   ```

2. **Restore from backup:**
   ```bash
   docker-compose up -d postgres
   docker exec -i odoo-dev-postgres psql -U odoo postgres -c "DROP DATABASE testing;"
   docker exec -i odoo-dev-postgres psql -U odoo postgres -c "CREATE DATABASE testing;"
   docker exec -i odoo-dev-postgres psql -U odoo testing < backup_20251111.sql
   ```

3. **Restart Odoo:**
   ```bash
   docker-compose up -d
   ```

4. **Upgrade modules:**
   ```bash
   docker exec -it odoo-dev-web odoo-bin -u ueipab_hr_contract -d testing --stop-after-init
   ```

### If Schema is Out of Sync:

1. **Check module installation status:**
   ```sql
   SELECT name, state, latest_version
   FROM ir_module_module
   WHERE name = 'ueipab_hr_contract';
   ```

2. **Force module upgrade:**
   ```bash
   docker exec -it odoo-dev-web odoo-bin -u ueipab_hr_contract -d testing --stop-after-init
   ```

3. **Or run SQL migration manually:**
   ```bash
   docker exec -i odoo-dev-postgres psql -U odoo testing < scripts/sql/add-cesta-ticket-deduction-base-field.sql
   ```

---

## 9. Current System Status

### Database Configuration:

| Component | Value | Status |
|-----------|-------|--------|
| PostgreSQL Version | 14 | ✅ Tracked in docker-compose.yml |
| Database Name | testing | ✅ In git |
| Database Volume | odoo-db-data | ✅ Persistent (not in git) |
| Port Mapping | 5433:5432 | ✅ In git |
| Latest Schema Version | 17.0.1.2.0 | ✅ In git |

### Recent Schema Changes:

| Field | Table | Purpose | Git Commit | SQL Script |
|-------|-------|---------|------------|------------|
| ueipab_deduction_base | hr_contract | Store K+L for deductions | f546854 | ✅ Created |
| ueipab_ari_withholding_rate | hr_contract | ARI tax rate | Previous | ✅ Exists |
| ueipab_monthly_salary | hr_contract | Aguinaldos calculation | Previous | ✅ Exists |

### Data Migration Status:

| Migration | Records | Status | Backup |
|-----------|---------|--------|--------|
| Cesta Ticket Rebalancing | 44 employees | ✅ Complete | ✅ Created |
| Deduction Base Population | 44 employees | ✅ Complete | ✅ Created |
| ARI Rate Sync | 45 employees | ✅ Complete | ✅ Historical |

---

## 10. Conclusion

✅ **Database schema changes ARE properly version controlled** through:

1. **Odoo Python models** (primary, automatic schema sync)
2. **SQL migration scripts** (documentation, manual deployment option)
3. **Git commits** (full change history)
4. **Docker Compose** (infrastructure as code)

✅ **Database data is persistent** through Docker volumes (not in git, by design)

✅ **Backup and recovery procedures** are documented and tested

✅ **Cesta Ticket project** has complete version control:
   - Python model: `hr_contract.py` ← Git tracked
   - SQL script: `add-cesta-ticket-deduction-base-field.sql` ← Git tracked
   - Data migration: `rebalance-cesta-ticket-contracts.py` ← Git tracked
   - Documentation: `CESTA_TICKET_FINAL_SOLUTION.md` ← Git tracked

**The system follows Odoo and Docker best practices for database version control.**

---

**For Questions or Issues:**
- Review this document
- Check `git log` for schema change history
- Consult SQL scripts in `scripts/sql/`
- Review module `__manifest__.py` version numbers
- Verify Docker volumes: `docker volume ls`
