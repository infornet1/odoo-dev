# Production Migration Plan - UEIPAB Payroll System

**Module:** ueipab_payroll_enhancements v17.0.1.33.0 + Dependencies
**Date Prepared:** November 23, 2025
**Status:** 🟡 DRAFT - AWAITING USER REVIEW
**Author:** UEIPAB Technical Team
**Target Environment:** Production Server 10.124.0.3 (Container: ueipab17, DB: DB_UEIPAB)

---

## 🎯 Executive Summary

This document outlines the **COMPLETE PAYROLL SYSTEM DEPLOYMENT** from testing environment to production server. This is a **FRESH INSTALLATION** - production currently has **NO payroll modules installed**.

### Critical Findings from Production Analysis (2025-11-23)

**Production Environment Status:**
- ✅ Odoo 17.0 running in container `ueipab17` (up 2 weeks)
- ✅ Database `DB_UEIPAB` operational (PostgreSQL 14)
- ✅ 50 employees in system
- ⚠️ **ZERO active contracts** (all contracts in system are inactive)
- ❌ **NO PAYROLL MODULES INSTALLED** (hr_payroll_community, hr_payroll_account_community)
- ❌ **CUSTOM MODULES MISSING** (ueipab_payroll_enhancements, hr_payslip_monthly_report)
- ⚠️ **ueipab_hr_contract v1.0.0** (outdated - needs update to v1.5.0)

**Migration Scope:**
- **Type:** Fresh Payroll System Installation
- **Modules to Deploy:** 5 modules (2 base + 3 custom)
- **Risk Level:** MEDIUM (first-time installation, no active contracts = low data risk)
- **Complexity:** HIGH (full system deployment with dependencies)
- **Expected Duration:** 2-3 hours (includes testing)

---

## 📋 Table of Contents

1. [Environment Analysis](#1-environment-analysis)
2. [Module Dependency Chain](#2-module-dependency-chain)
3. [Pre-Migration Requirements](#3-pre-migration-requirements)
4. [Risk Assessment](#4-risk-assessment)
5. [Migration Steps](#5-migration-steps)
6. [Testing & Validation](#6-testing--validation)
7. [Rollback Procedures](#7-rollback-procedures)
8. [Post-Migration Configuration](#8-post-migration-configuration)
9. [Post-Migration Monitoring](#9-post-migration-monitoring)
10. [Support & Documentation](#10-support--documentation)
11. [Approval Checklist](#11-approval-checklist)

---

## 1. Environment Analysis

### 1.1 Testing Environment (Source - VALIDATED)

| Component | Details |
|-----------|---------|
| **Container** | odoo-dev-web |
| **Odoo Version** | 17.0-20251106 (Community) |
| **Database** | testing (PostgreSQL 14) |
| **Port** | 8019 (HTTP) |
| **Active Contracts** | 44 employees with active contracts |
| **Payroll Status** | ✅ FULLY OPERATIONAL |

**Installed Modules (Testing):**
```
hr_payroll_community               v17.0.1.0.0  (Base payroll)
hr_payroll_account_community       v17.0.1.0.0  (Payroll accounting)
ueipab_hr_contract                 v17.0.1.5.0  (Contract extensions - V2 fields)
ueipab_payroll_enhancements        v17.0.1.33.0 (Custom payroll features)
hr_payslip_monthly_report          v17.0.1.2    (Email delivery system)
```

### 1.2 Production Environment (Target - ANALYZED 2025-11-23)

| Component | Details |
|-----------|---------|
| **Server** | 10.124.0.3 |
| **Container** | ueipab17 (up 2 weeks) |
| **Odoo Version** | 17.0 (Community) |
| **Database** | DB_UEIPAB (PostgreSQL 14) |
| **Port** | 8069 (HTTP) |
| **Employees** | 50 total |
| **Active Contracts** | **0 contracts** (all inactive) |
| **Payroll Status** | ❌ NOT INSTALLED |

**Current Module Status (Production):**
```
hr_payroll_community               NOT INSTALLED (available but not active)
hr_payroll_account_community       NOT INSTALLED (available but not active)
ueipab_hr_contract                 v17.0.1.0.0  (OUTDATED - needs v1.5.0)
ueipab_payroll_enhancements        NOT FOUND    (needs deployment)
hr_payslip_monthly_report          NOT FOUND    (needs deployment)
```

**Critical Observations:**
1. **Fresh Installation Required** - No payroll system currently deployed
2. **Zero Active Contracts** - Low risk of data conflicts during deployment
3. **Contract Module Outdated** - Must update ueipab_hr_contract before payroll installation
4. **Base Payroll Available** - hr_payroll_community present but not installed

### 1.3 Version Comparison Matrix

| Module | Testing (Source) | Production (Target) | Action Required |
|--------|------------------|---------------------|-----------------|
| **hr_payroll_community** | v17.0.1.0.0 (installed) | Available (not installed) | ✅ INSTALL |
| **hr_payroll_account_community** | v17.0.1.0.0 (installed) | Available (not installed) | ✅ INSTALL |
| **ueipab_hr_contract** | v17.0.1.5.0 | v17.0.1.0.0 | ⚠️ UPDATE (deploy v1.5.0) |
| **ueipab_payroll_enhancements** | v17.0.1.33.0 | NOT FOUND | 📦 DEPLOY + INSTALL |
| **hr_payslip_monthly_report** | v17.0.1.2 | NOT FOUND | 📦 DEPLOY + INSTALL |

---

## 2. Module Dependency Chain

### 2.1 Installation Order (CRITICAL - Must Follow Exact Sequence)

**Phase 1: Base Payroll Foundation**
```
1. hr_payroll_community (v17.0.1.0.0)
   └─ Already in production, just needs installation

2. hr_payroll_account_community (v17.0.1.0.0)
   └─ Depends on: hr_payroll_community
   └─ Already in production, just needs installation
```

**Phase 2: Contract Extensions**
```
3. ueipab_hr_contract (v17.0.1.5.0)
   └─ UPDATE from v1.0.0 to v1.5.0
   └─ Adds V2 salary fields, vacation tracking, liquidation fields
   └─ MUST update BEFORE payroll enhancements
```

**Phase 3: Custom Payroll Features**
```
4. ueipab_payroll_enhancements (v17.0.1.33.0)
   └─ Depends on: hr_payroll_community, ueipab_hr_contract
   └─ DEPLOY files then INSTALL
   └─ Includes: Batch enhancements, reports, email templates

5. hr_payslip_monthly_report (v17.0.1.2)
   └─ Depends on: hr_payroll_community
   └─ DEPLOY files then INSTALL
   └─ Cybrosys module with custom fixes
```

### 2.2 Dependency Graph

```
hr_payroll_community (BASE)
    ├── hr_payroll_account_community
    ├── ueipab_hr_contract (v1.5.0)
    │   └── ueipab_payroll_enhancements (v1.33.0)
    └── hr_payslip_monthly_report (v1.2)
```

### 2.3 File Deployment Requirements

**Files to Transfer from Testing → Production:**

```bash
# 1. ueipab_hr_contract (v1.5.0) - UPDATE
Source: /opt/odoo-dev/addons/ueipab_hr_contract/
Size: ~25 KB
Files: 8 files (models, views, security, manifest)

# 2. ueipab_payroll_enhancements (v1.33.0) - NEW
Source: /opt/odoo-dev/addons/ueipab_payroll_enhancements/
Size: ~180 KB
Files: 45+ files (models, views, reports, wizards, controllers, data)

# 3. hr_payslip_monthly_report (v1.2) - NEW
Source: /opt/odoo-dev/addons/hr_payslip_monthly_report/
Size: ~35 KB
Files: 12 files (models, views, wizards, templates)
```

**Total Deployment Size:** ~240 KB

---

## 3. Pre-Migration Requirements

### 3.1 Access Checklist

- [x] SSH access to production (root@10.124.0.3) - ✅ VERIFIED
- [x] Production analysis complete - ✅ COMPLETED 2025-11-23
- [ ] Database admin credentials (PostgreSQL user)
- [ ] Odoo admin credentials (web interface)
- [ ] File system write permissions to addons directory
- [ ] Sudo/root access confirmed

**SSH Access (Temporary - Provided by User):**
```bash
Server: 10.124.0.3
User: root
Password: g)9nE>?rq-#v3Hn
Note: READ-ONLY analysis completed, deployment requires authorization
```

### 3.2 Production Environment Assessment (✅ COMPLETED)

**Analysis Results (2025-11-23):**

```bash
# Odoo Version
Odoo Server 17.0
Container: ueipab17 (up 2 weeks)

# Database Status
Database: DB_UEIPAB (PostgreSQL 14)
Size: ~800 MB
Employees: 50 total, 0 active contracts

# Module Status
Total installed modules: ~85 modules
Payroll modules: NONE installed (hr_payroll_community available but not active)
Custom modules: ueipab_hr_contract v1.0.0 only

# Disk Space
Available: Sufficient (verified)

# Current Git Status
Not checked (deployment via file transfer recommended)

# Active Users
Need to verify during deployment window

# Active Payroll Batches
NONE (payroll not installed)
```

### 3.3 Backup Requirements (⚠️ MANDATORY BEFORE DEPLOYMENT)

**Critical Backups Required:**

**1. Full Database Backup**
```bash
# On production server:
docker exec ueipab17_postgres_1 pg_dump -U odoo -Fc DB_UEIPAB > \
    /backups/DB_UEIPAB_pre_payroll_$(date +%Y%m%d_%H%M%S).dump

# Verify backup:
ls -lh /backups/DB_UEIPAB_pre_payroll_*.dump
# Expected size: ~800 MB
```

**2. Addons Directory Backup**
```bash
# Backup existing custom addons:
docker exec ueipab17 tar -czf /tmp/addons_backup_$(date +%Y%m%d).tar.gz \
    /mnt/extra-addons/ueipab_*

# Copy to host:
docker cp ueipab17:/tmp/addons_backup_*.tar.gz /backups/
```

**3. Configuration Backup**
```bash
# Backup Odoo config from container:
docker exec ueipab17 cat /etc/odoo/odoo.conf > \
    /backups/odoo.conf.$(date +%Y%m%d)
```

**4. Verify Backup Integrity**
```bash
# List all backups:
ls -lh /backups/*$(date +%Y%m%d)*

# Test database backup (optional):
docker exec ueipab17_postgres_1 pg_restore --list \
    /backups/DB_UEIPAB_pre_payroll_*.dump | head -20
```

---

## 4. Risk Assessment

### 4.1 Risk Matrix

| Risk | Probability | Impact | Mitigation | Severity |
|------|-------------|--------|------------|----------|
| **Module dependency conflicts** | LOW | MEDIUM | Follow exact installation order | LOW |
| **Database migration failures** | MEDIUM | HIGH | Full backup, test rollback plan | MEDIUM |
| **Contract field migration issues** | MEDIUM | HIGH | Zero active contracts = low data risk | LOW |
| **Accounting configuration errors** | MEDIUM | HIGH | Document account setup, test validation | MEDIUM |
| **Module installation failures** | LOW | MEDIUM | Pre-validation, verified dependencies | LOW |
| **Production data corruption** | VERY LOW | CRITICAL | Full backup mandatory | VERY LOW |
| **User access during deployment** | MEDIUM | MEDIUM | Deploy during maintenance window | LOW |
| **Email template conflicts** | LOW | LOW | Templates use unique XML IDs | VERY LOW |

**Overall Risk Level:** **MEDIUM** ⚠️
(Higher than typical update due to fresh installation scope, but mitigated by zero active contracts)

### 4.2 Impact Analysis

**Affected Systems:**
- ✅ **Payroll Module:** Complete new installation
- ✅ **HR Contract Module:** Update from v1.0.0 → v1.5.0 (adds V2 fields)
- ✅ **Accounting Module:** New payroll accounting integration
- ⚠️ **Existing HR Data:** Minimal impact (no active contracts)
- ❌ **Other Modules:** No impact

**Affected Users:**
- **Direct Impact:** Payroll administrators (2-3 users) - NEW system to learn
- **Indirect Impact:** HR staff (employee contract management) - NEW fields available
- **Employee Impact:** None during deployment (no payslips currently generated)
- **User Training Required:** 30-60 minutes (full payroll system orientation)

**Business Continuity:**
- **Current State:** No payroll system operational (manual processing)
- **Migration Impact:** Enables automated payroll processing
- **Downtime:** 1-2 hours during installation (maintenance window required)
- **Fail-Safe:** Full rollback plan documented

### 4.3 Critical Success Factors

**Must Have:**
1. ✅ Complete production backup verified (database + files)
2. ✅ All 5 modules deployed in correct order
3. ✅ Accounting chart of accounts verified and configured
4. ✅ At least one test employee contract created and validated
5. ✅ Test payslip generated and validated successfully
6. ✅ Email delivery system tested
7. ✅ Rollback plan tested (in staging if available)

**Should Have:**
1. ✅ Staging environment test (if available)
2. ✅ Off-peak deployment window (evening/weekend)
3. ✅ Technical staff available for 2-3 hours
4. ✅ Communication plan for HR/payroll users
5. ✅ Accounting team notified of new integration

---

## 5. Migration Steps

### 5.1 Pre-Deployment Phase (Day -1) - 2 Hours

**Responsible:** Technical Team

#### Step 1: Final Production Assessment (15 min)
```bash
# Connect to production:
ssh root@10.124.0.3

# Verify container status:
docker ps | grep ueipab17
# Expected: Container running, healthy

# Check database accessibility:
docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c "SELECT current_database();"
# Expected: DB_UEIPAB

# Check disk space:
docker exec ueipab17 df -h /mnt/extra-addons
# Expected: >1GB available

# Identify addons path:
docker exec ueipab17 grep addons_path /etc/odoo/odoo.conf
# Note the exact path
```

#### Step 2: Create Comprehensive Backups (30 min)
```bash
# 1. Database backup:
docker exec ueipab17_postgres_1 pg_dump -U odoo -Fc DB_UEIPAB > \
    /backups/DB_UEIPAB_pre_payroll_$(date +%Y%m%d_%H%M%S).dump

# Verify size (should be ~800MB):
ls -lh /backups/DB_UEIPAB_pre_payroll_*.dump

# 2. Test backup integrity:
docker exec ueipab17_postgres_1 pg_restore --list \
    /backups/DB_UEIPAB_pre_payroll_*.dump | wc -l
# Expected: >1000 lines

# 3. Backup addons:
docker exec ueipab17 tar -czf /tmp/addons_backup.tar.gz /mnt/extra-addons/
docker cp ueipab17:/tmp/addons_backup.tar.gz /backups/addons_$(date +%Y%m%d).tar.gz

# 4. Backup config:
docker exec ueipab17 cat /etc/odoo/odoo.conf > /backups/odoo.conf.$(date +%Y%m%d)
```

#### Step 3: Prepare Module Files on Testing Server (30 min)
```bash
# On testing server (10.124.0.2 or local):
cd /opt/odoo-dev/addons

# Create deployment package:
tar -czf /tmp/payroll_deployment_$(date +%Y%m%d).tar.gz \
    ueipab_hr_contract/ \
    ueipab_payroll_enhancements/ \
    hr_payslip_monthly_report/

# Verify package:
tar -tzf /tmp/payroll_deployment_*.tar.gz | head -20

# Transfer to production:
scp /tmp/payroll_deployment_*.tar.gz root@10.124.0.3:/tmp/
```

#### Step 4: Verify Module Files (15 min)
```bash
# On production server:
cd /tmp
tar -tzf payroll_deployment_*.tar.gz | grep __manifest__.py
# Expected: 3 manifest files (one per module)

# Check package size:
ls -lh payroll_deployment_*.tar.gz
# Expected: ~240 KB
```

#### Step 5: Schedule Deployment Window (30 min)
- **Preferred Time:** Saturday evening or Sunday (off-peak)
- **Duration:** 2-3 hours (includes testing)
- **Notification:** Email to HR, payroll, and accounting teams
- **Availability:** Technical lead + 1 backup person on-call
- **Rollback Window:** Additional 1 hour if needed

**Notification Template:**
```
Subject: Payroll System Deployment - Saturday [DATE] 6:00 PM

Dear Team,

We will be deploying the new payroll system to production on:
Date: Saturday, [DATE]
Time: 6:00 PM - 9:00 PM
Impact: Odoo system will be in maintenance mode

New Features:
- Automated payroll batch generation
- Disbursement reports (PDF/Excel)
- Liquidation calculations (V1 & V2)
- Email delivery for payslips
- Prestaciones interest reports

Training Session:
Monday, [DATE+2] at 10:00 AM (1 hour)

Questions? Contact: [Technical Lead Email/Phone]
```

---

### 5.2 Deployment Phase (Day 0) - 2-3 Hours

**Timeline:** Saturday evening 6:00 PM - 9:00 PM
**Responsible:** Technical Team Lead + Backup

#### Phase 1: Extract Module Files (15 min)

```bash
# Connect to production:
ssh root@10.124.0.3

# Navigate to container's addon directory:
docker exec -it ueipab17 bash

# Inside container:
cd /mnt/extra-addons  # Adjust path as needed

# Extract deployment package:
tar -xzf /tmp/payroll_deployment_*.tar.gz

# Verify extraction:
ls -la ueipab_hr_contract/ ueipab_payroll_enhancements/ hr_payslip_monthly_report/

# Set proper permissions:
chown -R odoo:odoo ueipab_hr_contract/ ueipab_payroll_enhancements/ hr_payslip_monthly_report/
chmod -R 755 ueipab_hr_contract/ ueipab_payroll_enhancements/ hr_payslip_monthly_report/

# Exit container:
exit
```

#### Phase 2: Update Module List (10 min)

```bash
# Update apps list via Odoo shell:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
env['ir.module.module'].update_list()
print("✅ Module list updated")
env.cr.commit()
EOF

# Verify new modules detected:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
modules = env['ir.module.module'].search([
    ('name', 'in', ['ueipab_payroll_enhancements', 'hr_payslip_monthly_report'])
])
for m in modules:
    print(f"  {m.name}: {m.state}")
env.cr.commit()
EOF

# Expected output:
#   ueipab_payroll_enhancements: uninstalled
#   hr_payslip_monthly_report: uninstalled
```

#### Phase 3: Install Base Payroll Modules (20 min)

```bash
# Stop Odoo container:
docker stop ueipab17

# Install base payroll (hr_payroll_community):
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i hr_payroll_community \
    --stop-after-init \
    --log-level=info

# Check logs for errors:
docker logs ueipab17 --tail=100 | grep -i "error\|installed"

# Expected: "Module hr_payroll_community installed"

# Install payroll accounting (hr_payroll_account_community):
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i hr_payroll_account_community \
    --stop-after-init \
    --log-level=info

# Verify installation:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
modules = env['ir.module.module'].search([
    ('name', 'in', ['hr_payroll_community', 'hr_payroll_account_community'])
])
for m in modules:
    print(f"  ✅ {m.name}: {m.state} (v{m.latest_version})")
env.cr.commit()
EOF
```

#### Phase 4: Update ueipab_hr_contract (15 min)

```bash
# Update contract module (v1.0.0 → v1.5.0):
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -u ueipab_hr_contract \
    --stop-after-init \
    --log-level=info

# Verify update:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_hr_contract')])
print(f"  ✅ ueipab_hr_contract: {module.state} (v{module.latest_version})")

# Verify new V2 fields exist:
Contract = env['hr.contract']
if hasattr(Contract, 'ueipab_salary_v2'):
    print("  ✅ V2 salary fields detected")
else:
    print("  ❌ WARNING: V2 fields not found!")
env.cr.commit()
EOF
```

#### Phase 5: Install Custom Payroll Enhancements (20 min)

```bash
# Install ueipab_payroll_enhancements:
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i ueipab_payroll_enhancements \
    --stop-after-init \
    --log-level=info

# Check for errors:
docker logs ueipab17 --tail=200 | grep -i "error\|warning" | grep payroll

# Verify installation:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
print(f"  ✅ {module.name}: {module.state} (v{module.latest_version})")

# Verify salary structures:
structures = env['hr.payroll.structure'].search([])
print(f"\n  Salary Structures: {len(structures)} found")
for s in structures:
    print(f"    - {s.name} (code: {s.code or 'N/A'})")

# Verify email templates:
templates = env['mail.template'].search([('model', '=', 'hr.payslip')])
print(f"\n  Email Templates: {len(templates)} found")
for t in templates:
    print(f"    - {t.name}")

env.cr.commit()
EOF
```

#### Phase 6: Install Email Delivery System (15 min)

```bash
# Install hr_payslip_monthly_report:
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i hr_payslip_monthly_report \
    --stop-after-init \
    --log-level=info

# Verify installation:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'hr_payslip_monthly_report')])
print(f"  ✅ {module.name}: {module.state} (v{module.latest_version})")
env.cr.commit()
EOF
```

#### Phase 7: Start Odoo and Verify (15 min)

```bash
# Start Odoo container:
docker start ueipab17

# Wait for startup (60 seconds):
sleep 60

# Check container is running:
docker ps | grep ueipab17
# Expected: Container running, healthy

# Monitor logs for errors:
docker logs ueipab17 --tail=100 | grep -i "error"

# Verify HTTP service:
curl -I http://10.124.0.3:8069/web/database/selector
# Expected: HTTP/1.1 200 OK
```

#### Phase 8: Clear Assets and Regenerate (10 min)

```bash
# Clear assets via Odoo shell:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
# Clear web assets:
env['ir.attachment'].search([
    ('res_model', '=', 'ir.ui.view'),
    ('name', 'like', 'web_assets%')
]).unlink()

print("✅ Web assets cleared")
env.cr.commit()
EOF

# Regenerate assets via command:
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    --stop-after-init \
    --update=ueipab_payroll_enhancements

# Restart container:
docker restart ueipab17

# Wait for startup:
sleep 60
```

---

### 5.3 Testing Phase - 45-60 Minutes

**Responsible:** Technical Team + Payroll Team
**Critical:** Must complete ALL tests before declaring success

#### Test 1: UI Verification (10 min)

```
1. Login to Odoo as admin:
   URL: http://10.124.0.3:8069

2. Enable Developer Mode:
   Settings → Activate developer mode

3. Verify Payroll menu:
   Payroll → Should see: Batches, Payslips, Structures, Rules
   ✅ PASS: Menu visible and accessible

4. Verify Custom Reports menu:
   Payroll → Reports → Custom Reports
   ✅ PASS: See all 5 custom reports listed

5. Check HR Contract form:
   Employees → Contracts → Open any contract
   ✅ PASS: See "💼 Salary Breakdown - V2" notebook page
   ✅ PASS: See V2 fields (ueipab_salary_v2, bonus_v2, etc.)
```

#### Test 2: Create Test Employee Contract (15 min)

```
1. Create test employee:
   Employees → Create
   Name: "TEST EMPLOYEE - PAYROLL"
   Email: (payroll admin email)
   Department: Administration
   Save

2. Create test contract:
   Employee form → Contracts tab → Create
   Start Date: First of current month
   Salary Structure: VE_PAYROLL_V2
   Wage: $500.00
   V2 Salary Fields:
     - ueipab_salary_v2: $300.00
     - ueipab_bonus_v2: $100.00
     - ueipab_extrabonus_v2: $100.00
     - cesta_ticket_usd: $40.00
   Save

3. Verify contract state:
   ✅ PASS: Contract saved successfully
   ✅ PASS: All V2 fields visible and editable
```

#### Test 3: Generate Test Payslip (15 min)

```
1. Create payroll batch:
   Payroll → Batches → Create
   Name: "TEST_MIGRATION_2025_11_23"
   Period: Current month (1st to 15th)
   Save

2. Generate payslips:
   Click "Generate Payslips" button
   ✅ PASS: Wizard opens with structure selector
   ✅ PASS: Can select VE_PAYROLL_V2 or leave empty

3. Select test employee:
   Employee: TEST EMPLOYEE - PAYROLL
   Generate: 1 payslip
   Click "Generate"

4. Verify payslip created:
   ✅ PASS: Payslip created successfully
   ✅ PASS: Payslip lines show salary breakdown
   ✅ PASS: NET amount calculated correctly

5. Compute sheet:
   Open payslip → Click "Compute Sheet"
   ✅ PASS: Lines calculated without errors
   ✅ PASS: All rule calculations correct
```

#### Test 4: Validate Accounting Integration (10 min)

```
1. Validate payslip:
   Payslip form → Click "Confirm"
   ✅ PASS: Payslip confirmed successfully
   ✅ PASS: State changed to "Done"

2. Check accounting entries:
   Payslip form → Smart button "Journal Entries"
   ✅ PASS: Journal entry created
   ✅ PASS: Entry is balanced (Debit = Credit)
   ✅ PASS: Accounts are correct:
     - Debit: 5.1.01.10.001 (Payroll Expense)
     - Credit: 2.1.01.01.002 (Payroll Payable)

3. Check batch total:
   Batches → Open test batch
   ✅ PASS: "Total Net Payable" field shows correct amount
```

#### Test 5: Email Template Testing (10 min)

```
1. Test email template selector:
   Batch form → Check "Email Template" field
   ✅ PASS: Field visible
   ✅ PASS: See 3 templates:
     - Payslip Compact Report (default)
     - Payslip - Employee Delivery
     - Aguinaldos Email - Christmas Bonus Delivery

2. Test send payslip email:
   Batch form → Click "Send Payslips by Email"
   ✅ PASS: Button visible and clickable
   ✅ PASS: Email sent successfully (check logs)

3. Verify email received:
   Check payroll admin email inbox
   ✅ PASS: Email received with PDF attachment
   ✅ PASS: Email formatting correct (QWeb rendered)
```

#### Test 6: Custom Reports (Optional - if time permits)

```
1. Test Disbursement Report:
   Payroll → Reports → Payroll Disbursement Detail
   Select batch: TEST_MIGRATION_2025_11_23
   Format: PDF
   Generate
   ✅ PASS: PDF generated successfully
   ✅ PASS: Shows employee, amounts, deductions

2. Test Relación de Liquidación:
   (Skip if no liquidation test employee)
   ✅ PASS: Report accessible
```

---

## 6. Rollback Procedures

### 6.1 Rollback Decision Criteria

**Trigger Rollback if:**
- ❌ Module installation fails with critical errors
- ❌ Database corruption detected
- ❌ Payslip generation fails repeatedly
- ❌ Accounting validation fails (unbalanced entries)
- ❌ Critical UI bugs prevent payroll operations
- ❌ Performance degradation > 50%
- ❌ Any data loss detected

**Do NOT Rollback for:**
- ✅ Minor UI glitches (can be fixed post-deployment)
- ✅ Email template formatting issues (can be fixed in database)
- ✅ Report layout adjustments needed (non-critical)
- ✅ User training needed (expected)

### 6.2 Rollback Steps

**Timeline:** 30-45 minutes

#### Step 1: Stop Odoo (5 min)

```bash
# On production server:
ssh root@10.124.0.3

# Stop container:
docker stop ueipab17

# Verify stopped:
docker ps -a | grep ueipab17
# Expected: Container stopped
```

#### Step 2: Restore Database (15 min)

```bash
# Drop current database:
docker exec ueipab17_postgres_1 psql -U postgres << 'EOF'
DROP DATABASE DB_UEIPAB;
CREATE DATABASE DB_UEIPAB;
\q
EOF

# Restore from backup:
docker exec -i ueipab17_postgres_1 pg_restore \
    -U odoo -d DB_UEIPAB \
    /backups/DB_UEIPAB_pre_payroll_*.dump

# Verify restoration:
docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c "
SELECT name, state FROM ir_module_module
WHERE name LIKE '%payroll%' OR name LIKE 'ueipab%'
ORDER BY name;"

# Expected: Pre-migration state
```

#### Step 3: Restore Addon Files (10 min)

```bash
# Remove deployed modules:
docker exec ueipab17 bash -c "
cd /mnt/extra-addons
rm -rf ueipab_payroll_enhancements hr_payslip_monthly_report
"

# Restore old contract module version:
docker exec ueipab17 bash -c "
cd /mnt/extra-addons
rm -rf ueipab_hr_contract
"

# Extract backup:
docker cp /backups/addons_*.tar.gz ueipab17:/tmp/
docker exec ueipab17 bash -c "
cd /mnt/extra-addons
tar -xzf /tmp/addons_*.tar.gz
"

# Verify restoration:
docker exec ueipab17 ls -la /mnt/extra-addons/ueipab_*
```

#### Step 4: Restart Odoo (5 min)

```bash
# Start container:
docker start ueipab17

# Wait for startup:
sleep 60

# Check logs:
docker logs ueipab17 --tail=100

# Verify HTTP service:
curl -I http://10.124.0.3:8069/web/database/selector
# Expected: HTTP/1.1 200 OK
```

#### Step 5: Verify Rollback (10 min)

```bash
# Check module status:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
modules = env['ir.module.module'].search([
    '|', ('name', 'like', '%payroll%'),
    ('name', 'like', 'ueipab%')
])
print("\n📋 Module Status After Rollback:")
for m in modules:
    print(f"  {m.name}: {m.state} (v{m.latest_version})")
env.cr.commit()
EOF

# Expected:
#   ueipab_hr_contract: installed (v17.0.1.0.0)
#   hr_payroll_community: uninstalled (or not found)
#   ueipab_payroll_enhancements: not found
```

#### Step 6: Document Rollback

```bash
# Create rollback log:
cat > /backups/rollback_log_$(date +%Y%m%d_%H%M%S).txt << EOF
========================================
PAYROLL DEPLOYMENT ROLLBACK LOG
========================================
Date: $(date)
Server: 10.124.0.3
Database: DB_UEIPAB
Rolled Back By: [Name]

REASON FOR ROLLBACK:
--------------------
[Describe the critical issue that triggered rollback]

MODULES ROLLED BACK:
--------------------
- hr_payroll_community (uninstalled)
- hr_payroll_account_community (uninstalled)
- ueipab_hr_contract (restored to v1.0.0)
- ueipab_payroll_enhancements (removed)
- hr_payslip_monthly_report (removed)

RESTORATION STATUS:
-------------------
✅ Database restored from backup
✅ Addon files restored
✅ Odoo container restarted
✅ System operational

NEXT STEPS:
-----------
1. Root cause analysis meeting scheduled: [DATE/TIME]
2. Fix issues in testing environment
3. Retest thoroughly before retry
4. Update migration plan with lessons learned

APPROVER:
---------
Name: _______________________
Title: _______________________
Date: _______________________
EOF
```

---

## 7. Post-Migration Configuration

### 7.1 Accounting Setup (30 min)

**Required After Installation:**

```bash
# Run accounting configuration script:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB < /opt/odoo-dev/scripts/configure_v2_salary_rule_accounts.py

# Expected output:
#   ✅ [VE_SSO_DED_V2] configured
#   ✅ [VE_FAOV_DED_V2] configured
#   ✅ [VE_PARO_DED_V2] configured
#   ✅ [VE_ARI_DED_V2] configured
#   ✅ [VE_NET_V2] configured
#   ... (11 rules total)

# Verify configuration:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
SalaryRule = env['hr.salary.rule']
rules = SalaryRule.search([('code', 'like', '_V2')])

print("\n📊 Salary Rule Accounting Configuration:")
configured = 0
for rule in rules:
    if rule.account_debit_id and rule.account_credit_id:
        print(f"  ✅ {rule.code}: Dr {rule.account_debit_id.code} | Cr {rule.account_credit_id.code}")
        configured += 1
    else:
        print(f"  ❌ {rule.code}: NOT CONFIGURED")

print(f"\nTotal: {configured}/{len(rules)} rules configured")
env.cr.commit()
EOF
```

### 7.2 SMTP Configuration for Emails (15 min)

```bash
# Check current SMTP settings:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
smtp = env['ir.mail_server'].search([], limit=1)
if smtp:
    print(f"✅ SMTP Server: {smtp.name}")
    print(f"   Host: {smtp.smtp_host}")
    print(f"   Port: {smtp.smtp_port}")
    print(f"   User: {smtp.smtp_user}")
else:
    print("❌ No SMTP server configured")
env.cr.commit()
EOF

# If no SMTP configured, create via UI:
# Settings → Technical → Email → Outgoing Mail Servers
# Add server details:
#   Name: UEIPAB Mail Server
#   SMTP Server: (your SMTP host)
#   SMTP Port: 587 (or 465 for SSL)
#   Connection Security: TLS
#   Username: (SMTP username)
#   Password: (SMTP password)
#   Test Connection: Send test email
```

### 7.3 Payroll Settings Configuration (10 min)

```
1. Enable automatic payslip email:
   Settings → Payroll
   ✅ Enable "Automatic Send Payslip By Mail"
   Save

2. Verify email template default:
   Payroll → Batches → Create new batch
   Check "Email Template" field
   ✅ Default should be "Payslip Compact Report"

3. Configure payroll journal:
   Accounting → Configuration → Journals
   Find "Payroll Journal"
   Verify accounts:
     - Default Debit Account: 5.1.01.10.001
     - Default Credit Account: 2.1.01.01.002
```

### 7.4 User Permissions Setup (15 min)

```bash
# Verify user groups:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
# Find payroll users:
payroll_group = env['res.groups'].search([('name', '=', 'Payroll / Officer')])
payroll_users = payroll_group.users

print("\n👥 Payroll Users:")
for user in payroll_users:
    print(f"  - {user.name} ({user.login})")

# Verify access to custom reports:
report_group = env['res.groups'].search([('name', '=', 'Payroll / Manager')])
print(f"\n✅ Payroll Managers: {len(report_group.users)} users")

env.cr.commit()
EOF

# Grant access if needed (via UI):
# Settings → Users & Companies → Users
# Select user → Edit → Access Rights
# Payroll: Officer or Manager
```

---

## 8. Post-Migration Monitoring

### 8.1 First 24 Hours Monitoring

**Immediate (First Hour):**
- [ ] Check Odoo logs every 15 minutes for errors
- [ ] Monitor container health (`docker ps`, check CPU/memory)
- [ ] Test payslip generation with 2-3 real employees
- [ ] Verify email delivery working
- [ ] Check database size (should not increase >10%)

**Extended (24 Hours):**
- [ ] Review all Odoo errors in logs
- [ ] Monitor user activity (login attempts, errors)
- [ ] Check accounting entry creation (balanced)
- [ ] Collect user feedback (payroll team)
- [ ] Verify report generation working

### 8.2 Monitoring Commands

```bash
# 1. Watch logs in real-time:
docker logs ueipab17 -f | grep -i "error\|payroll"

# 2. Check container health:
docker stats ueipab17 --no-stream
# Expected: <10% CPU, <2GB memory

# 3. Database size:
docker exec ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c "
SELECT pg_size_pretty(pg_database_size('DB_UEIPAB'));"

# 4. Error count (last hour):
docker logs ueipab17 --since 60m | grep -c ERROR

# 5. Module usage tracking:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
# Count payslips created since deployment:
payslips = env['hr.payslip'].search([
    ('create_date', '>', '2025-11-23 18:00:00')
])
print(f"📊 Payslips created: {len(payslips)}")

# Count batches created:
batches = env['hr.payslip.run'].search([
    ('create_date', '>', '2025-11-23 18:00:00')
])
print(f"📊 Batches created: {len(batches)}")

# Count emails sent:
mails = env['mail.mail'].search([
    ('create_date', '>', '2025-11-23 18:00:00'),
    ('model', '=', 'hr.payslip')
])
print(f"📧 Emails sent: {len(mails)}")
env.cr.commit()
EOF
```

### 8.3 First Week Monitoring

**Daily Tasks:**
- [ ] Review error logs (morning check)
- [ ] Check batch generation success rate
- [ ] Monitor accounting entry accuracy
- [ ] Collect user feedback via email/survey

**Weekly Review:**
- [ ] Generate usage report (payslips, batches, emails)
- [ ] Review all user-reported issues
- [ ] Performance comparison (before/after)
- [ ] Schedule follow-up training if needed

---

## 9. Support & Documentation

### 9.1 Post-Deployment Training

**Payroll Team Training Session (1 hour):**

**Topics to Cover:**
1. Module overview (10 min)
   - What's new vs manual process
   - Key features demo

2. Batch generation workflow (15 min)
   - Create batch
   - Structure selector usage
   - Generate payslips
   - Validate batch

3. Custom reports (15 min)
   - Disbursement Detail Report (PDF/Excel)
   - Relación de Liquidación (liquidation breakdown)
   - Prestaciones Interest Report
   - Finiquito (labor settlement)
   - Payslip Compact Report

4. Email delivery system (10 min)
   - Template selector
   - Send batch emails
   - Individual payslip email

5. Q&A and hands-on practice (10 min)

**Training Materials:**
- [ ] Screen recording of full workflow
- [ ] Quick reference guide (PDF)
- [ ] FAQ document
- [ ] Contact info for support

### 9.2 Documentation References

**Available Documentation (in `/opt/odoo-dev/documentation/`):**

1. **CLAUDE.md** - Main project guidelines (comprehensive)
2. **PAYROLL_DISBURSEMENT_REPORT.md** - Disbursement report guide
3. **LIQUIDATION_COMPLETE_GUIDE.md** - V1 liquidation guide
4. **LIQUIDATION_V2_IMPLEMENTATION.md** - V2 liquidation guide
5. **V2_PAYROLL_IMPLEMENTATION.md** - V2 payroll system reference
6. **PRESTACIONES_INTEREST_REPORT.md** - Prestaciones report guide
7. **RELACION_BREAKDOWN_REPORT.md** - Breakdown report journey
8. **FINIQUITO_REPORT.md** - Labor settlement report guide
9. **WIZARD_BASED_REPORT_PATTERN.md** - Report development pattern

### 9.3 Support Contacts

| Role | Responsibility | Contact Method | Availability |
|------|----------------|----------------|--------------|
| **Technical Lead** | Deployment, system issues | [Email/Phone] | Mon-Fri 9-5 + On-call |
| **Payroll Manager** | Process, workflow, training | [Email/Phone] | Mon-Fri 9-5 |
| **Database Admin** | Database, performance | [Email/Phone] | On-call (emergencies) |
| **Accounting Team** | Journal entries, accounts | [Email] | Mon-Fri 9-5 |

### 9.4 Issue Escalation Path

**Level 1: User Issues (Payroll Team)**
- Questions about workflow
- Report formatting preferences
- Email template selection
- Contact: Payroll Manager

**Level 2: Technical Issues (Technical Team)**
- Module errors
- Calculation discrepancies
- Report generation failures
- Contact: Technical Lead

**Level 3: Critical Issues (IT Director)**
- System downtime
- Data corruption
- Database issues
- Contact: IT Director (emergency only)

---

## 10. Approval Checklist

### 10.1 Pre-Deployment Approval

**Technical Readiness:**
- [ ] Production environment analyzed (✅ COMPLETED 2025-11-23)
- [ ] All module files prepared and tested
- [ ] Dependency chain verified
- [ ] Backup procedures validated
- [ ] Rollback plan tested (in staging if possible)
- [ ] Deployment scripts reviewed
- [ ] Testing checklist finalized

**Infrastructure Readiness:**
- [ ] Production access credentials confirmed
- [ ] Backup storage verified (sufficient space)
- [ ] Deployment window scheduled
- [ ] Technical team availability confirmed
- [ ] Monitoring tools configured

**Business Readiness:**
- [ ] Payroll team notified of deployment
- [ ] Training session scheduled
- [ ] User documentation prepared
- [ ] HR team informed of new features
- [ ] Accounting team notified of integration

### 10.2 Go/No-Go Checklist (Final Review Before Deployment)

**Must Be "YES" for All:**

- [ ] **YES** Full database backup completed and verified
- [ ] **YES** Addon files backup completed
- [ ] **YES** Configuration backup completed
- [ ] **YES** Production analysis complete (zero active contracts confirmed)
- [ ] **YES** Deployment window scheduled (off-peak time)
- [ ] **YES** Technical team available (2-3 hours)
- [ ] **YES** Rollback plan ready and understood
- [ ] **YES** All dependencies verified present
- [ ] **YES** Testing checklist prepared
- [ ] **YES** User notification sent

**Any "NO" = NO-GO (reschedule deployment)**

### 10.3 Approval Signatures

**Technical Approval:**
```
I have reviewed the migration plan and confirm:
✅ All technical requirements are met
✅ Risks are acceptable and mitigated
✅ Rollback plan is viable
✅ Team is prepared for deployment

Name: _______________________
Title: Technical Lead
Date: _______________________
Signature: __________________
```

**Business Approval:**
```
I have reviewed the migration plan and confirm:
✅ Business impact is understood
✅ Training plan is adequate
✅ Deployment timing is acceptable
✅ User communication is complete

Name: _______________________
Title: Payroll Manager / HR Director
Date: _______________________
Signature: __________________
```

**Final Authorization:**
```
Deployment is authorized to proceed.

Decision: ⬜ GO / ⬜ NO-GO

If NO-GO, Reason: _________________________________

Rescheduled Date: _________________________________

Name: _______________________
Title: IT Director / CTO
Date: _______________________
Signature: __________________
```

---

## 11. Appendices

### Appendix A: Quick Command Reference

**Essential Production Commands:**

```bash
# Connect to production:
ssh root@10.124.0.3

# Check container status:
docker ps | grep ueipab17

# View recent logs:
docker logs ueipab17 --tail=100

# Access Odoo shell:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB

# Restart Odoo:
docker restart ueipab17

# Check module status:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
modules = env['ir.module.module'].search([('name', 'like', '%payroll%')])
for m in modules: print(f"{m.name}: {m.state}")
EOF

# Database backup:
docker exec ueipab17_postgres_1 pg_dump -U odoo -Fc DB_UEIPAB > /backups/backup_$(date +%Y%m%d).dump

# Watch for errors:
docker logs ueipab17 -f | grep -i error
```

### Appendix B: Module Feature Summary

**ueipab_payroll_enhancements v1.33.0:**
- ✅ Total Net Payable calculation (batch aggregation)
- ✅ Exchange rate field + apply to batch
- ✅ Cancel/Draft workflow for batches
- ✅ Structure selector in batch generation wizard
- ✅ Smart defaults (Aguinaldos auto-detection)
- ✅ 5 custom reports (PDF/Excel export)
- ✅ 3 email templates for payslip delivery
- ✅ Batch email sending with template selector

**ueipab_hr_contract v1.5.0 (V2 Fields):**
- ✅ ueipab_salary_v2 (direct salary amount)
- ✅ ueipab_bonus_v2 (bonus amount)
- ✅ ueipab_extrabonus_v2 (extra bonus)
- ✅ ueipab_original_hire_date (for antiguedad)
- ✅ ueipab_previous_liquidation_date (tracking)
- ✅ ueipab_vacation_paid_until (tracking)
- ✅ ueipab_vacation_prepaid_amount (deduction base)

**hr_payslip_monthly_report v1.2:**
- ✅ Automatic email on payslip confirmation
- ✅ Manual "Send Email" button
- ✅ Mass confirm wizard (bulk operations)
- ✅ Professional email template
- ✅ PDF attachment support
- ✅ Reset send status button (v1.2 fix)

### Appendix C: Troubleshooting Common Issues

**Issue: Module installation fails with "dependency not found"**
```
Solution: Verify installation order
1. Check hr_payroll_community installed first
2. Then hr_payroll_account_community
3. Then ueipab_hr_contract updated
4. Finally custom modules

Command to check:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
deps = ['hr_payroll_community', 'hr_payroll_account_community', 'ueipab_hr_contract']
for d in deps:
    m = env['ir.module.module'].search([('name', '=', d)])
    print(f"{d}: {m.state if m else 'NOT FOUND'}")
EOF
```

**Issue: Email sending fails**
```
Solution: Check SMTP configuration
1. Settings → Technical → Outgoing Mail Servers
2. Verify server settings
3. Test connection
4. Check Odoo logs for SMTP errors:
   docker logs ueipab17 | grep -i smtp
```

**Issue: Accounting entries not created**
```
Solution: Configure salary rule accounts
1. Run configuration script:
   docker exec -it ueipab17 odoo shell -d DB_UEIPAB < /opt/odoo-dev/scripts/configure_v2_salary_rule_accounts.py
2. Verify accounts configured
3. Re-validate payslip
```

**Issue: UI not updating after module install**
```
Solution: Clear assets and regenerate
1. Enable Developer Mode
2. Bug icon → Regenerate Assets Bundles
3. Hard refresh browser (Ctrl+Shift+R)
4. Clear browser cache if needed
```

### Appendix D: Emergency Rollback Flowchart

```
Deployment Issue Detected
        ↓
Is system completely broken?
    YES → Immediate Rollback (Section 6.2)
    NO → Continue investigation
        ↓
Can issue be fixed in <30 minutes?
    YES → Fix and retest
    NO → Schedule rollback
        ↓
Execute Rollback:
    1. Stop Odoo (5 min)
    2. Restore database (15 min)
    3. Restore files (10 min)
    4. Restart Odoo (5 min)
    5. Verify rollback (10 min)
    6. Document issues
        ↓
System Restored to Pre-Migration State
        ↓
Schedule Root Cause Analysis
        ↓
Fix in Testing → Retest → Retry Migration
```

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2025-11-23 | Technical Team | Complete rewrite based on production analysis |
| - | - | Current module versions (v1.33.0, v1.5.0, v1.2) | - |
| - | - | Fresh installation scope (no payroll currently installed) | - |
| - | - | All 5 modules in dependency chain | - |
| 1.0 | 2025-11-10 | Technical Team | Initial draft (outdated) |

---

## 📊 Status Summary

**Current Status:** 🟡 **DRAFT - AWAITING USER REVIEW**

**Completion Checklist:**
- ✅ Production environment analyzed (2025-11-23)
- ✅ Module versions identified and verified
- ✅ Dependency chain documented
- ✅ Migration steps detailed (5 phases)
- ✅ Testing procedures comprehensive
- ✅ Rollback plan complete
- ✅ Post-migration configuration documented
- ⬜ **USER REVIEW PENDING**
- ⬜ Deployment window scheduled
- ⬜ Final approvals obtained

**Next Steps:**
1. ⏳ **User reviews this migration plan (FIRST REVISION)**
2. ⏳ User provides feedback and approvals
3. ⏳ Schedule deployment window
4. ⏳ Execute pre-deployment phase (backups)
5. ⏳ Execute deployment
6. ⏳ Complete testing and validation
7. ⏳ User training and handoff

**Estimated Timeline:**
- User review: 1-2 days
- Deployment preparation: 1 day
- Deployment execution: 2-3 hours
- Testing and validation: 1 hour
- Training: 1 hour
- **Total: 3-4 days from approval to go-live**

---

**⚠️ IMPORTANT NOTES FOR USER:**

1. **Zero Active Contracts:** Production has 50 employees but ZERO active contracts. This significantly reduces data migration risk.

2. **Fresh Installation:** This is NOT an update - it's a complete new payroll system installation. No existing payroll data to migrate.

3. **Critical Dependencies:** Must install in exact order: Base payroll → Contract update → Custom modules. Breaking this order will cause failures.

4. **Accounting Setup Required:** After installation, must run accounting configuration script to link salary rules to chart of accounts.

5. **SMTP Configuration Needed:** Email delivery will not work until SMTP server is configured in Odoo settings.

6. **Training Essential:** Payroll team needs training on new system (1 hour session recommended).

7. **Testing Cannot Be Skipped:** All 6 test scenarios must pass before declaring success. No shortcuts.

---

**END OF MIGRATION PLAN**

**Document prepared by:** Technical Team (Automated Analysis + Human Review)
**Document prepared for:** UEIPAB Management - First Revision
**Preparation date:** November 23, 2025
**Production analysis date:** November 23, 2025
**Deployment target:** TBD (pending approval)
