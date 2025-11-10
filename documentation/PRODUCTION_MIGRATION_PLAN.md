# Production Migration Plan
**Module:** ueipab_payroll_enhancements v17.0.1.0.0
**Date Prepared:** November 10, 2025
**Status:** DRAFT - Awaiting Approval
**Author:** UEIPAB Technical Team
**Target Environment:** Production (10.124.0.3)

---

## Executive Summary

This document outlines the comprehensive plan to migrate the **ueipab_payroll_enhancements** module from the local development environment to the production server (10.124.0.3). The module has been thoroughly tested with 44 employees and $13,124.65 in Aguinaldos payments with 100% success rate.

**Migration Type:** New Module Deployment (Non-Breaking Change)
**Risk Level:** LOW
**Expected Downtime:** None (zero-downtime deployment possible)
**Rollback Complexity:** LOW (simple module uninstall)

---

## Table of Contents

1. [Environment Analysis](#1-environment-analysis)
2. [Pre-Migration Requirements](#2-pre-migration-requirements)
3. [Risk Assessment](#3-risk-assessment)
4. [Migration Steps](#4-migration-steps)
5. [Testing & Validation](#5-testing--validation)
6. [Rollback Procedures](#6-rollback-procedures)
7. [Post-Migration Monitoring](#7-post-migration-monitoring)
8. [Approval Checklist](#8-approval-checklist)

---

## 1. Environment Analysis

### 1.1 Development Environment (Current)

| Component | Details |
|-----------|---------|
| **Server** | Local Docker: odoo-dev-web |
| **Odoo Version** | 17.0-20251106 (Community) |
| **Database** | testing (PostgreSQL 14) |
| **Port** | 8019 (HTTP) |
| **Total Modules** | 142 installed |
| **Custom Modules** | 4 UEIPAB modules installed |

### 1.2 Production Environment (Target)

| Component | Expected Details |
|-----------|------------------|
| **Server** | 10.124.0.3 |
| **Odoo Version** | 17.0 (Community) - *To be verified* |
| **Database** | testing (PostgreSQL) - *To be verified* |
| **Port** | Standard ports - *To be verified* |
| **Access Method** | SSH (credentials required) |

**⚠️ CRITICAL: Production environment assessment requires:**
1. SSH access credentials
2. Database connection details
3. Odoo configuration review
4. Current module inventory
5. User activity analysis

### 1.3 Modules to be Deployed

| Module Name | Version | Status (Dev) | Size | Dependencies |
|-------------|---------|--------------|------|--------------|
| **ueipab_payroll_enhancements** | 17.0.1.0.0 | Installed | 40KB | hr_payroll_community, ueipab_hr_contract |

**Module Components:**
- `models/hr_payslip_employees.py` (128 lines)
- `views/hr_payslip_employees_views.xml` (50 lines)
- `__manifest__.py`
- `__init__.py` files

### 1.4 Database Changes

**Schema Changes:** NONE
- Module adds computed transient model fields only
- No permanent database table modifications
- No data migrations required

**Data Changes:** NONE
- No master data changes
- No existing record modifications
- Backward compatible with existing payslips

---

## 2. Pre-Migration Requirements

### 2.1 Access & Credentials Checklist

- [ ] SSH access to production server (10.124.0.3)
- [ ] Database credentials (username/password)
- [ ] Odoo admin credentials
- [ ] Sudo/root access (if needed for file operations)
- [ ] Git repository access (if using version control on production)

### 2.2 Production Environment Assessment (REQUIRED)

**Must Complete Before Migration:**

```bash
# 1. Check Odoo version
odoo --version

# 2. Check installed modules
psql -U odoo -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name LIKE 'ueipab%' OR name LIKE '%payroll%'
ORDER BY name;"

# 3. Check addons path
grep addons_path /etc/odoo/odoo.conf

# 4. Check disk space
df -h /opt/odoo  # or wherever addons are stored

# 5. Check current git status (if applicable)
cd /path/to/addons && git status

# 6. Identify active users
psql -U odoo -d testing -c "
SELECT COUNT(*) as active_sessions
FROM res_users
WHERE login_date > NOW() - INTERVAL '1 hour';"

# 7. Check for running payroll batches
psql -U odoo -d testing -c "
SELECT COUNT(*) as active_batches
FROM hr_payslip_run
WHERE state = 'draft';"
```

### 2.3 Backup Requirements (MANDATORY)

**Before ANY changes:**

1. **Full Database Backup**
```bash
# On production server:
pg_dump -U odoo -Fc testing > /backups/testing_pre_payroll_enhancement_$(date +%Y%m%d_%H%M%S).dump

# Verify backup:
pg_restore --list /backups/testing_pre_payroll_enhancement_*.dump | head -20
```

2. **Addons Directory Backup**
```bash
# Backup current addons:
tar -czf /backups/addons_pre_payroll_enhancement_$(date +%Y%m%d).tar.gz \
    /opt/odoo/addons/ueipab_*  # Adjust path as needed
```

3. **Configuration Backup**
```bash
# Backup Odoo configuration:
cp /etc/odoo/odoo.conf /backups/odoo.conf.$(date +%Y%m%d)
```

4. **Verify Backup Integrity**
```bash
# Test restore on a separate test environment if possible
# At minimum, verify backup files exist and are not corrupted:
ls -lh /backups/*$(date +%Y%m%d)*
```

### 2.4 Dependency Verification

**Required Modules Must Be Installed:**
- ✅ `hr_payroll_community` (Community Payroll)
- ✅ `ueipab_hr_contract` (UEIPAB Contract Extensions)

**Verification Query:**
```sql
SELECT name, state, latest_version
FROM ir_module_module
WHERE name IN ('hr_payroll_community', 'ueipab_hr_contract', 'hr_payroll_account_community')
ORDER BY name;
```

**Expected Result:**
```
hr_payroll_community           | installed | 17.0.x.x.x
hr_payroll_account_community   | installed | 17.0.x.x.x
ueipab_hr_contract            | installed | 17.0.1.1.0
```

---

## 3. Risk Assessment

### 3.1 Risk Matrix

| Risk | Probability | Impact | Mitigation | Severity |
|------|-------------|--------|------------|----------|
| **Module conflicts with existing code** | LOW | MEDIUM | Pre-deployment testing, code review | LOW |
| **Database performance degradation** | VERY LOW | LOW | No database changes, monitoring | VERY LOW |
| **User interface issues** | LOW | MEDIUM | Browser cache clear, asset regeneration | LOW |
| **Payroll batch generation errors** | VERY LOW | HIGH | Thorough testing, rollback plan | LOW |
| **Accounting entry failures** | VERY LOW | HIGH | Validated in dev, data integrity checks | VERY LOW |
| **Production data corruption** | VERY LOW | CRITICAL | Full backup, no data modifications | VERY LOW |
| **Deployment timing conflicts** | MEDIUM | MEDIUM | Deploy during maintenance window | LOW |

**Overall Risk Level:** **LOW** ✅

### 3.2 Impact Analysis

**Affected Systems:**
- ✅ Payroll module (Wizard enhancement only)
- ✅ HR module (Indirect via payroll)
- ❌ Accounting (No impact - works with existing structure)
- ❌ Other modules (No impact)

**Affected Users:**
- **Direct Impact:** Payroll administrators (2-3 users)
- **Indirect Impact:** None (end users don't interact with batch generation)
- **User Training Required:** 5-10 minutes (demonstration)

**Business Continuity:**
- **Zero Downtime:** Module can be installed without stopping Odoo
- **Backward Compatible:** Existing functionality unchanged
- **Fail-Safe:** Empty structure field = old behavior

### 3.3 Critical Success Factors

**Must Have:**
1. ✅ Complete production backup verified
2. ✅ SSH and database access confirmed
3. ✅ Dependency modules installed and up-to-date
4. ✅ At least one test batch run in production
5. ✅ Rollback plan documented and ready

**Should Have:**
1. ✅ Staging environment test (if available)
2. ✅ Off-peak deployment window
3. ✅ Technical staff available for monitoring
4. ✅ Communication plan for users

---

## 4. Migration Steps

### 4.1 Pre-Deployment Phase (Day -1)

**Timeline:** 1-2 hours
**Responsible:** Technical Team

#### Step 1: Production Assessment
```bash
# Connect to production server:
ssh user@10.124.0.3

# Run assessment script:
/opt/odoo-dev/scripts/production_assessment.sh > assessment_$(date +%Y%m%d).txt

# Review output and confirm:
# - Odoo version compatibility
# - Dependencies installed
# - Disk space available
# - No active payroll batches
```

#### Step 2: Create Backups
```bash
# 1. Database backup:
sudo -u postgres pg_dump -Fc testing > \
    /backups/testing_pre_payroll_$(date +%Y%m%d_%H%M%S).dump

# 2. Verify backup size (should be > 100MB):
ls -lh /backups/testing_pre_payroll_*.dump

# 3. Addons backup:
tar -czf /backups/addons_backup_$(date +%Y%m%d).tar.gz /opt/odoo/addons/

# 4. Configuration backup:
cp /etc/odoo/odoo.conf /backups/odoo.conf.$(date +%Y%m%d)
```

#### Step 3: Prepare Module Files
```bash
# On development machine:
cd /opt/odoo-dev
tar -czf ueipab_payroll_enhancements.tar.gz \
    addons/ueipab_payroll_enhancements/

# Transfer to production:
scp ueipab_payroll_enhancements.tar.gz user@10.124.0.3:/tmp/
```

#### Step 4: Schedule Deployment Window
- **Preferred Time:** Off-peak hours (evening or weekend)
- **Duration:** 30-60 minutes
- **Notification:** Inform payroll team (email/Slack)
- **Availability:** Technical staff on-call

### 4.2 Deployment Phase

**Timeline:** 30-45 minutes
**Responsible:** Technical Team Lead

#### Step 1: Extract and Install Module (10 min)
```bash
# On production server:
ssh user@10.124.0.3

# Extract module:
cd /opt/odoo/addons/  # Adjust path to your addons directory
sudo tar -xzf /tmp/ueipab_payroll_enhancements.tar.gz

# Verify extraction:
ls -la ueipab_payroll_enhancements/
# Expected: __init__.py, __manifest__.py, models/, views/

# Set proper permissions:
sudo chown -R odoo:odoo ueipab_payroll_enhancements/
sudo chmod -R 755 ueipab_payroll_enhancements/
```

#### Step 2: Update Module List (5 min)
```bash
# Option A: Via Odoo Shell (Recommended)
sudo -u odoo odoo shell -d testing << 'EOF'
env['ir.module.module'].update_list()
print("Module list updated")
env.cr.commit()
EOF

# Option B: Via UI (If shell not available)
# 1. Login to Odoo as admin
# 2. Go to Apps menu
# 3. Click "Update Apps List" button
# 4. Confirm update
```

#### Step 3: Install Module (10 min)
```bash
# Option A: Via Command Line (Recommended)
sudo systemctl stop odoo  # or: sudo service odoo stop
sudo -u odoo odoo -d testing -i ueipab_payroll_enhancements --stop-after-init
sudo systemctl start odoo  # or: sudo service odoo start

# Wait for Odoo to start (check logs):
tail -f /var/log/odoo/odoo.log  # Adjust path as needed
# Look for: "Modules loaded" and "HTTP service running"

# Option B: Via UI (If command line not preferred)
# 1. Login to Odoo as admin
# 2. Enable Developer Mode (Settings → Activate developer mode)
# 3. Go to Apps menu
# 4. Remove "Apps" filter
# 5. Search: "ueipab_payroll"
# 6. Click "Install" on "UEIPAB Payroll Enhancements"
# 7. Wait for installation to complete
```

#### Step 4: Verify Installation (5 min)
```bash
# Check module status:
sudo -u postgres psql -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';"

# Expected output:
# ueipab_payroll_enhancements | installed | 17.0.1.0.0

# Check for errors in log:
tail -100 /var/log/odoo/odoo.log | grep -i "error\|warning" | grep payroll
```

#### Step 5: Clear Browser Cache & Regenerate Assets (5 min)
```bash
# Via UI (Recommended):
# 1. Enable Developer Mode
# 2. Click bug icon (🐞) in top-right
# 3. Select "Regenerate Assets Bundles"
# 4. Wait for completion

# Via Command Line (Alternative):
sudo -u odoo odoo -d testing --stop-after-init --update=ueipab_payroll_enhancements
```

### 4.3 Testing Phase

**Timeline:** 15-30 minutes
**Responsible:** Payroll Team + Technical Team

#### Test 1: UI Verification (5 min)
```
1. Login as payroll user
2. Go to: Payroll → Batches
3. Create test batch: "TEST_MIGRATION"
   - Dates: Current month
   - Journal: Standard payroll journal
4. Click "Generate Payslips" button
5. ✅ VERIFY: "Salary Structure" dropdown is visible
6. ✅ VERIFY: Info banner displays usage instructions
7. ✅ VERIFY: Placeholder text shows: "Leave empty to use contract structure"
8. Cancel wizard (don't generate yet)
```

#### Test 2: Smart Default Detection (5 min)
```
1. Create new batch: "Aguinaldos_TEST"
2. Click "Generate Payslips"
3. ✅ VERIFY: AGUINALDOS_2025 structure is pre-selected
4. ✅ VERIFY: Green success alert shows "Structure Override Active"
5. Cancel wizard
```

#### Test 3: Generate Test Payslips (10 min)
```
1. Create batch: "TEST_VALIDATION_$(date +%Y%m%d)"
2. Dates: Current month, 1-15
3. Click "Generate Payslips"
4. Select structure: UEIPAB_VE (or leave empty)
5. Select 2-3 test employees
6. Click "Generate"
7. ✅ VERIFY: Payslips created successfully
8. ✅ VERIFY: Payslips show correct structure
9. ✅ VERIFY: Amounts computed correctly
10. Delete test payslips (cleanup)
```

#### Test 4: Validate Batch (Optional - if time permits)
```
1. Generate 1-2 real payslips for testing
2. Click "Validate" on batch
3. ✅ VERIFY: No accounting errors
4. ✅ VERIFY: Journal entries created
5. ✅ VERIFY: Entries are balanced
6. Document results
```

### 4.4 Post-Deployment Phase

#### Step 1: Monitor Logs (Ongoing)
```bash
# Watch for errors in real-time:
tail -f /var/log/odoo/odoo.log | grep -i "error\|payroll"

# Check for any unusual activity:
tail -100 /var/log/odoo/odoo.log | grep -c "ERROR"
```

#### Step 2: User Communication
```
# Email to payroll team:
Subject: Payroll Enhancement Deployed - New Feature Available

Dear Payroll Team,

The new Payroll Batch Structure Selector has been successfully deployed to production.

New Feature:
- When generating payslips, you'll now see a "Salary Structure" dropdown
- For Aguinaldos batches, the system will automatically select AGUINALDOS_2025
- This eliminates the need to manually change structures after generation

Usage:
1. Create your batch as usual
2. Click "Generate Payslips"
3. The structure will be pre-selected if needed
4. Or leave it empty to use the default contract structure

Training session scheduled: [Date/Time]

Questions? Contact: [Technical Support]
```

#### Step 3: Document Deployment
```bash
# Create deployment record:
cat > /backups/deployment_log_$(date +%Y%m%d).txt << EOF
Deployment Date: $(date)
Module: ueipab_payroll_enhancements v17.0.1.0.0
Deployed By: [Name]
Production Server: 10.124.0.3
Database: testing
Status: SUCCESS / FAILED
Issues: [None / List issues]
Rollback Required: NO / YES
Notes: [Any additional notes]
EOF
```

---

## 5. Testing & Validation

### 5.1 Acceptance Criteria

**Module Must:**
- [ ] Install without errors
- [ ] Show structure selector in wizard UI
- [ ] Auto-detect "Aguinaldos" in batch name
- [ ] Allow manual structure selection
- [ ] Allow empty selection (backward compatibility)
- [ ] Generate payslips with correct structure
- [ ] Pass validation without accounting errors
- [ ] Create balanced journal entries

**Module Must NOT:**
- [ ] Break existing payroll functionality
- [ ] Cause performance degradation
- [ ] Modify existing payslip data
- [ ] Interfere with other modules

### 5.2 Production Test Scenarios

| Test # | Scenario | Expected Result | Status |
|--------|----------|-----------------|--------|
| 1 | Create regular payroll batch, leave structure empty | Payslips use contract structure | ⬜ |
| 2 | Create "Aguinaldos" batch | Structure auto-selects AGUINALDOS_2025 | ⬜ |
| 3 | Generate 3 test payslips with override | All use selected structure | ⬜ |
| 4 | Validate batch with structure override | No errors, entries posted | ⬜ |
| 5 | Check browser compatibility | Works in Chrome, Firefox | ⬜ |
| 6 | Test with different user roles | Payroll users can access | ⬜ |

### 5.3 Performance Validation

**Metrics to Monitor:**
```sql
-- Query execution time (should be < 1 second):
EXPLAIN ANALYZE
SELECT * FROM hr_payslip_run WHERE name LIKE '%Aguinaldo%';

-- Database size (should not increase significantly):
SELECT pg_size_pretty(pg_database_size('testing'));

-- Active connections:
SELECT count(*) FROM pg_stat_activity WHERE datname = 'testing';
```

---

## 6. Rollback Procedures

### 6.1 Rollback Decision Criteria

**Trigger Rollback if:**
- ✗ Module installation fails
- ✗ Critical errors in Odoo logs
- ✗ Payroll batch generation fails
- ✗ Accounting validation fails
- ✗ Data corruption detected
- ✗ Performance degradation > 50%
- ✗ User-reported critical bugs

### 6.2 Rollback Steps

**Timeline:** 10-15 minutes

#### Step 1: Uninstall Module
```bash
# Option A: Via Odoo Shell
sudo -u odoo odoo shell -d testing << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
module.button_immediate_uninstall()
env.cr.commit()
print("Module uninstalled")
EOF

# Option B: Via UI
# 1. Apps → Search "ueipab_payroll"
# 2. Click "Uninstall"
# 3. Confirm uninstall
```

#### Step 2: Remove Module Files
```bash
# Backup before removal (just in case):
sudo mv /opt/odoo/addons/ueipab_payroll_enhancements \
    /backups/ueipab_payroll_enhancements.removed_$(date +%Y%m%d)

# Verify removal:
ls /opt/odoo/addons/ | grep ueipab_payroll_enhancements
# Should return nothing
```

#### Step 3: Restart Odoo
```bash
sudo systemctl restart odoo
# or: sudo service odoo restart

# Verify startup:
tail -f /var/log/odoo/odoo.log
# Look for: "Modules loaded" and "HTTP service running"
```

#### Step 4: Verify Rollback
```bash
# Check module status:
sudo -u postgres psql -d testing -c "
SELECT name, state FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';"

# Expected: uninstalled or not found

# Test payroll batch generation:
# 1. Go to Payroll → Batches
# 2. Create test batch
# 3. Click "Generate Payslips"
# 4. ✅ VERIFY: Old wizard (no structure selector)
# 5. ✅ VERIFY: Payslips generate normally
```

#### Step 5: Database Restore (If Needed - EXTREME CASE ONLY)
```bash
# ONLY if module caused database corruption:
# 1. Stop Odoo:
sudo systemctl stop odoo

# 2. Restore database:
sudo -u postgres psql << EOF
DROP DATABASE testing;
CREATE DATABASE testing;
\q
EOF

sudo -u postgres pg_restore -d testing \
    /backups/testing_pre_payroll_*.dump

# 3. Restart Odoo:
sudo systemctl start odoo

# 4. Verify restoration:
sudo -u postgres psql -d testing -c "SELECT current_database(), version();"
```

### 6.3 Post-Rollback Actions

1. **Document Rollback Reason**
```bash
cat > /backups/rollback_log_$(date +%Y%m%d).txt << EOF
Rollback Date: $(date)
Module: ueipab_payroll_enhancements
Reason: [Describe the issue]
Impact: [Describe what broke]
Rolled Back By: [Name]
Status: COMPLETE
Next Steps: [Investigation plan]
EOF
```

2. **Notify Stakeholders**
3. **Schedule Root Cause Analysis**
4. **Update Deployment Plan** (for retry)

---

## 7. Post-Migration Monitoring

### 7.1 First 24 Hours

**Immediate Monitoring (First Hour):**
- [ ] Check Odoo logs every 15 minutes
- [ ] Monitor server resources (CPU, memory, disk)
- [ ] Test payroll batch generation
- [ ] Verify no user-reported issues

**Extended Monitoring (24 Hours):**
- [ ] Review all Odoo errors in logs
- [ ] Check database performance metrics
- [ ] Monitor user activity
- [ ] Collect user feedback

### 7.2 First Week

- [ ] Daily log review
- [ ] Weekly user survey
- [ ] Performance metrics comparison
- [ ] Issue tracking and resolution

### 7.3 Monitoring Queries

```sql
-- 1. Module usage tracking:
SELECT
    COUNT(*) as total_batches,
    COUNT(CASE WHEN name LIKE '%Aguinaldo%' THEN 1 END) as aguinaldos_batches
FROM hr_payslip_run
WHERE create_date > NOW() - INTERVAL '7 days';

-- 2. Error tracking:
SELECT
    COUNT(*) as error_count,
    message
FROM ir_logging
WHERE level = 'ERROR'
  AND create_date > NOW() - INTERVAL '24 hours'
  AND message LIKE '%payroll%'
GROUP BY message;

-- 3. Performance metrics:
SELECT
    schemaname,
    tablename,
    n_tup_ins + n_tup_upd + n_tup_del as total_changes
FROM pg_stat_user_tables
WHERE tablename LIKE '%payslip%'
ORDER BY total_changes DESC;
```

---

## 8. Approval Checklist

### 8.1 Pre-Approval Requirements

**Technical Review:**
- [ ] Code review completed (peer review)
- [ ] All tests passed in development
- [ ] Documentation complete
- [ ] Rollback plan validated
- [ ] Dependencies verified

**Business Review:**
- [ ] Payroll team trained
- [ ] User acceptance testing complete
- [ ] Business continuity plan reviewed
- [ ] Communication plan approved

**Infrastructure Review:**
- [ ] Production access confirmed
- [ ] Backup strategy validated
- [ ] Monitoring tools configured
- [ ] Deployment window scheduled

### 8.2 Approval Signatures

**Technical Approval:**
```
Name: _______________________
Title: Technical Lead
Date: _______________________
Signature: __________________
```

**Business Approval:**
```
Name: _______________________
Title: Payroll Manager
Date: _______________________
Signature: __________________
```

**Final Approval:**
```
Name: _______________________
Title: IT Director / CTO
Date: _______________________
Signature: __________________
```

### 8.3 Go/No-Go Decision

**Deployment Authorization:**
- [ ] All pre-approval requirements met
- [ ] All signatures obtained
- [ ] Deployment window confirmed
- [ ] Technical team available
- [ ] Rollback plan ready

**Decision:** ⬜ GO / ⬜ NO-GO

**If NO-GO, Reason:** _________________________________

**Rescheduled Date:** _________________________________

---

## 9. Appendices

### Appendix A: Contact Information

| Role | Name | Contact | Availability |
|------|------|---------|--------------|
| Technical Lead | [Name] | [Email/Phone] | [Hours] |
| Payroll Manager | [Name] | [Email/Phone] | [Hours] |
| Database Admin | [Name] | [Email/Phone] | On-call |
| IT Director | [Name] | [Email/Phone] | Emergency only |

### Appendix B: Emergency Procedures

**Critical Issue - Immediate Rollback:**
1. Notify Technical Lead
2. Execute rollback steps (Section 6.2)
3. Document issue
4. Schedule emergency meeting

**Data Corruption - Database Restore:**
1. Notify IT Director
2. Stop all Odoo services
3. Restore from backup (Section 6.2.5)
4. Verify data integrity
5. Full system test before resuming

### Appendix C: Reference Links

- [PAYROLL_BATCH_STRUCTURE_SELECTOR.md](./PAYROLL_BATCH_STRUCTURE_SELECTOR.md) - Full module documentation
- [AGUINALDOS_TEST_RESULTS_2025-11-10.md](./AGUINALDOS_TEST_RESULTS_2025-11-10.md) - Test results
- Odoo Community Documentation: https://www.odoo.com/documentation/17.0/

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-10 | Technical Team | Initial draft |
| - | - | - | - |

---

**Status:** 🟡 DRAFT - AWAITING REVIEW AND APPROVAL

**Next Steps:**
1. Review this document with technical team
2. Schedule production environment assessment
3. Obtain necessary approvals
4. Schedule deployment window
5. Execute migration plan

---

**END OF DOCUMENT**
