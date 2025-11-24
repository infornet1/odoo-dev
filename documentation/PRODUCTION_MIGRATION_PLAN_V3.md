# Production Migration Plan - UEIPAB Payroll System (44 Critical Employees)

**Module:** ueipab_payroll_enhancements v17.0.1.34.0 + Dependencies
**Date Prepared:** November 24, 2025 (Updated: **PHASE 1 COMPLETE!**)
**Status:** 🟢 **PHASE 1 DEPLOYED** - Modules Installed Successfully!
**Author:** UEIPAB Technical Team
**Target Environment:** Production Server 10.124.0.3 (Container: ueipab17, DB: DB_UEIPAB)
**Scope:** **44 Critical Employees** (employees with active contracts in testing)
**Deployment Date:** November 24, 2025, 21:32-22:06 UTC

---

## 🎯 Executive Summary

This document outlines the **PAYROLL SYSTEM DEPLOYMENT** from testing to production, focusing on **44 critical employees** who currently have active contracts in the testing environment.

### ✅ PHASE 1 DEPLOYMENT COMPLETE (2025-11-24 22:06 UTC)

**🎉 SUCCESSFULLY INSTALLED:**
| Module | Version | Status |
|--------|---------|--------|
| hr_payroll_community | 17.0.1.0.0 | ✅ Installed |
| hr_payroll_account_community | 17.0.1.0.0 | ✅ Installed |
| ueipab_hr_contract | **17.0.1.5.0** | ✅ Installed (V2 Fields Created!) |
| ueipab_payroll_enhancements | **17.0.1.34.0** | ✅ Installed |
| hr_payslip_monthly_report | 17.0.1.2 | ✅ Installed |

**V2 Contract Fields Created:**
- ✅ ueipab_salary_v2
- ✅ ueipab_bonus_v2
- ✅ ueipab_extrabonus_v2
- ✅ ueipab_original_hire_date
- ✅ ueipab_previous_liquidation_date
- ✅ ueipab_vacation_paid_until
- ✅ ueipab_vacation_prepaid_amount

**Backups Created:**
- ✅ DB: /root/backups/DB_UEIPAB_pre_payroll_20251124_213208.dump (14MB)
- ✅ Addons: /root/backups/addons_pre_payroll_20251124_213215.tar.gz (62MB)
- ✅ Config: /root/backups/odoo_conf_20251124_213219.conf

### Current Production Environment Status (Post-Deployment)

**Production Environment Status:**
- ✅ Odoo 17.0-20250807 running in container `ueipab17`
- ✅ Database `DB_UEIPAB` operational (PostgreSQL 14)
- ✅ 49 total employees in system
- ✅ **ALL 5 PAYROLL MODULES INSTALLED**
- ✅ **ueipab_hr_contract v1.5.0** (V2 fields available!)
- ⚠️ **Salary structures need manual creation** (see Section 11)

**Migration Focus:**
- **Target Employees:** 44 employees (those with active contracts + VAT IDs in testing)
- **Type:** Fresh Payroll System Installation + Selective Contract Creation
- **Modules to Deploy:** 5 modules (2 base + 3 custom)
- **Risk Level:** LOW (focused scope, validated employee data)
- **Expected Duration:** 3-4 hours (includes pre-cleanup, deployment, contract creation, testing)

**Data Validation Findings (2025-11-24 - UPDATED):**
- ✅ 43/44 employees have departments assigned (97.7%)
- ✅ 43/44 employees have VAT IDs (97.7%)
- ✅ All 44 employees are active
- ⚠️ **1 employee needs VAT ID + department** (Gustavo Perdomo)
- ℹ️ 1 employee remains without department by design (MARIA JIMENEZ - acceptable)

---

## 📋 Table of Contents

1. [44 Critical Employees - Scope Definition](#1-44-critical-employees---scope-definition)
2. [Custom Contract Fields Timeline](#2-custom-contract-fields-timeline)
3. [Pre-Migration Data Cleanup](#3-pre-migration-data-cleanup)
4. [Module Dependency Chain](#4-module-dependency-chain)
5. [Pre-Migration Requirements](#5-pre-migration-requirements)
6. [Risk Assessment](#6-risk-assessment)
7. [Migration Steps](#7-migration-steps)
8. [Contract Creation (44 Employees)](#8-contract-creation-44-employees)
9. [Testing & Validation](#9-testing--validation)
10. [Rollback Procedures](#10-rollback-procedures)
11. [Post-Migration Configuration](#11-post-migration-configuration)
12. [Approval Checklist](#12-approval-checklist)

---

## 1. 44 Critical Employees - Scope Definition

### 1.1 Who Are the 44 Critical Employees?

**Selection Criteria:**
- ✅ Have active contracts in testing database (state = 'open')
- ✅ Have valid VAT ID (identification_id) in testing
- ✅ Represent real employees (not test accounts)

**Why Focus on 44?**
1. These employees already have validated contract data in testing
2. Their contracts have been tested with V2 salary structures
3. They have complete data (compensation, start dates, structure assignments)
4. Lower risk - we know their contracts work correctly

### 1.2 Department Distribution (41/44 found in production)

| Department | Employee Count |
|------------|----------------|
| Docentes | 22 |
| Operaciones | 9 |
| Dirección | 5 |
| Soporte | 2 |
| Control de Estudios | 1 |
| **(No Department)** | **1** ⚠️ |

**Total:** 41 employees found in production, 3 with discrepancies

### 1.3 Data Quality Summary (44 Employees) - UPDATED 2025-11-24

| Data Element | Status | Action Required |
|--------------|--------|-----------------|
| **Department Assignment** | 43/44 ready (97.7%) | 1 employee needs department (Gustavo Perdomo) |
| **VAT ID** | 43/44 ready (97.7%) | 1 employee needs VAT ID (Gustavo Perdomo) |
| **Employee Status** | 44/44 active (100%) ✅ | None - All active |
| **Work Email** | 44/44 ready (100%) ✅ | None |

**Recent Fixes Completed:**
- ✅ YOSMARI GONZÁLEZ - Reactivated (active=true, dept=57, vat=V17009331)
- ✅ Luis Rodriguez - VAT ID added (V18453474, dept=55 Docentes)
- ℹ️ MARIA JIMENEZ - Remains without department by design (acceptable)

### 1.4 Employees Requiring Data Cleanup - UPDATED 2025-11-24

**Status:** ✅ **3 of 4 employees FIXED** - Only 1 remaining blocker

| # | Employee Name | VAT ID | Status | Action Required |
|---|---------------|--------|--------|-----------------|
| 1 | ~~YOSMARI GONZÁLEZ~~ | ✅ V17009331 | ✅ **FIXED** | ~~Reactivate~~ (active=t, dept=57) |
| 2 | ~~Luis Rodriguez~~ | ✅ V18453474 | ✅ **FIXED** | ~~Add VAT ID~~ (vat added, dept=55) |
| 3 | MARIA JIMENEZ | V30597749 | ℹ️ **ACCEPTABLE** | No department (by design) |
| 4 | **Gustavo Perdomo** | ❌ (missing) | ⚠️ **NEEDS FIX** | Add VAT ID + assign department |

**Remaining Blocker (1 employee):**
- **Gustavo Perdomo** (ID: 761)
  - Missing: VAT ID (identification_id = NULL)
  - Missing: Department (department_id = NULL)
  - Note: Has fake VAT ID (V12345678) in testing - needs real cédula from HR
  - Action: HR must collect real cédula number before deployment

---

## 2. Custom Contract Fields Timeline

### 2.1 Module vs. Fields Clarification

**IMPORTANT CLARIFICATION:**

**Custom contract fields (V2 fields) are NOT created by `ueipab_payroll_enhancements`**

**V2 Contract Fields Come From:**
- **Module:** `ueipab_hr_contract` v1.5.0
- **Installation Timing:** Phase 1, Step 4 (UPDATE existing module)
- **Availability:** Immediate after ueipab_hr_contract update completes

**Fields That Will Be Created:**
```python
# V2 Compensation Fields
ueipab_salary_v2              # Base salary (subject to deductions)
ueipab_bonus_v2               # Bonus (not subject to deductions)
ueipab_extrabonus_v2          # Extra bonus (not subject to deductions)

# V2 Liquidation Tracking Fields
ueipab_original_hire_date     # For antiguedad continuity
ueipab_previous_liquidation_date  # For rehires
ueipab_vacation_paid_until    # Vacation accrual tracking
ueipab_vacation_prepaid_amount    # Prepaid vacation/bono amount
```

### 2.2 Timeline: When Fields Become Available

```
Phase 1 - Module Deployment (Day 1)
├── Step 1-3: Base Payroll (30 min)
│   └── ❌ V2 fields NOT available yet
│
├── Step 4: Update ueipab_hr_contract (15 min) ⭐ CRITICAL STEP
│   ├── Database migration runs
│   ├── V2 fields ADDED to hr_contract table
│   ├── Custom views REGISTERED in UI
│   └── ✅ V2 FIELDS NOW AVAILABLE
│
├── Step 5-8: Custom Payroll Modules (45 min)
│   ├── Install ueipab_payroll_enhancements
│   │   └── Uses V2 fields in salary rules (VE_PAYROLL_V2, LIQUID_VE_V2)
│   └── ✅ V2 fields still available (no changes)
│
└── ✅ Phase 1 Complete: Ready to create contracts with V2 data
```

**Key Takeaway:**
- V2 fields created in **Step 4** (ueipab_hr_contract update)
- Payroll enhancements **use** those fields in **Step 5**
- Contract creation happens **after** Phase 1 completes

### 2.3 Module Responsibilities

| Module | Responsibility | V2 Fields? |
|--------|----------------|------------|
| **ueipab_hr_contract v1.5.0** | Defines V2 contract fields | ✅ **CREATES FIELDS** |
| **ueipab_payroll_enhancements v1.33.0** | Uses V2 fields in salary rules | ❌ Uses existing fields |
| **hr_payroll_community v1.0.0** | Base payroll engine | ❌ No custom fields |

**Reference Documentation:**
- `/opt/odoo-dev/documentation/CUSTOM_FIELDS_AVAILABILITY_TIMELINE.md` (331 lines)

---

## 3. Pre-Migration Data Cleanup

### 3.1 Critical Data Issues - UPDATED 2025-11-24

**Timeline:** Day -1 (before module deployment)
**Responsible:** HR Department + Technical Team

**Status:** ✅ **75% COMPLETE** - 3 of 4 employees fixed!

#### ✅ Fixed Issues (No Action Required)

**1. YOSMARI GONZÁLEZ (ID: 615)** - ✅ **FIXED**
- ✅ Reactivated (active = true)
- ✅ Has department (dept = 57, Operaciones)
- ✅ Has VAT ID (V17009331)
- **No action required**

**2. Luis Rodriguez (ID: 595)** - ✅ **FIXED**
- ✅ VAT ID added (V18453474)
- ✅ Has department (dept = 55, Docentes)
- **No action required**

**3. MARIA JIMENEZ (ID: 600)** - ℹ️ **ACCEPTABLE**
- ✅ Has VAT ID (V30597749)
- ℹ️ No department (by design - acceptable)
- **No action required**

#### ⚠️ Remaining Issue: Gustavo Perdomo (1 employee)

**Employee:** Gustavo Perdomo (ID: 761)
**Problems:**
1. Missing VAT ID (identification_id = NULL)
2. Missing Department (department_id = NULL)

**Impact:**
- Cannot create contract without VAT ID (required field)
- Department missing (appears on reports, professional appearance)

**Action Required from HR:**
- Collect real cédula number from Gustavo Perdomo
- Decide appropriate department assignment

**SQL Fix (once data collected):**
```sql
-- Update VAT ID and department
UPDATE hr_employee
SET identification_id = 'V[REAL_CEDULA_NUMBER]',
    department_id = [DEPT_ID]  -- See available departments below
WHERE id = 761 AND name = 'Gustavo Perdomo';

-- Verify update:
SELECT id, name, identification_id, department_id
FROM hr_employee
WHERE id = 761;
```

**Available Departments:**
- 51: AUXILIAR DE SOPORTE Y DESARROLLO
- 53: Control de Estudios
- 54: Dirección
- 55: Docentes
- 56: Mantenimiento
- 57: Operaciones
- 59: Soporte

**Note:** Gustavo Perdomo has **fake VAT ID (V12345678)** in testing database - this must be replaced with real cédula.

### 3.2 Pre-Cleanup Checklist - UPDATED

**Must Complete Before Deployment:**
- [x] ~~YOSMARI GONZÁLEZ reactivated~~ ✅ **DONE** (active = true, dept = 57)
- [x] ~~Luis Rodriguez VAT ID added~~ ✅ **DONE** (V18453474, dept = 55)
- [x] ~~MARIA DANIELA JIMENEZ status verified~~ ✅ **ACCEPTABLE** (no dept by design)
- [ ] **Gustavo Perdomo VAT ID collected from HR** ⚠️ **PENDING**
- [ ] **Gustavo Perdomo department assigned** ⚠️ **PENDING**
- [ ] **Gustavo Perdomo verified in production** ⚠️ **PENDING**

**Verification Script (Current Status):**
```bash
# Check current status of all 4 employees
docker exec -i ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB << 'EOF'
SELECT
    id,
    name,
    identification_id,
    active,
    CASE
        WHEN department_id IS NULL THEN '❌ NO DEPARTMENT'
        ELSE '✅ Has Department'
    END as dept_status
FROM hr_employee
WHERE id IN (615, 595, 600, 761)  -- YOSMARI, Luis, MARIA, Gustavo
ORDER BY name;
EOF

# Current output (as of 2025-11-24):
# 595 | LUIS RODRIGUEZ   | V18453474 | t | ✅ Has Department   (FIXED)
# 600 | MARIA JIMENEZ    | V30597749 | t | ❌ NO DEPARTMENT    (ACCEPTABLE)
# 615 | YOSMARI GONZALEZ | V17009331 | t | ✅ Has Department   (FIXED)
# 761 | Gustavo Perdomo  | (null)    | t | ❌ NO DEPARTMENT    (NEEDS FIX)

# Expected after Gustavo Perdomo fix:
# 761 | Gustavo Perdomo  | V[REAL]   | t | ✅ Has Department   (READY)
```

**Quick Check - Gustavo Perdomo Only:**
```bash
# Check if Gustavo Perdomo is ready for deployment
docker exec -i ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB -c "
SELECT
    id,
    name,
    identification_id,
    department_id,
    CASE
        WHEN identification_id IS NOT NULL AND department_id IS NOT NULL
        THEN '✅ READY FOR DEPLOYMENT'
        ELSE '❌ NEEDS DATA'
    END as status
FROM hr_employee
WHERE id = 761;"

# Expected after fix: status = '✅ READY FOR DEPLOYMENT'
```

---

## 4. Module Dependency Chain

### 4.1 Installation Order (CRITICAL - Must Follow Exact Sequence)

**Phase 1: Base Payroll Foundation**
```
1. hr_payroll_community (v17.0.1.0.0)
   └─ Already in production, needs installation

2. hr_payroll_account_community (v17.0.1.0.0)
   └─ Depends on: hr_payroll_community
   └─ Already in production, needs installation
```

**Phase 2: Contract Extensions (V2 Fields)**
```
3. ueipab_hr_contract (UPDATE v1.0.0 → v1.5.0) ⭐ CREATES V2 FIELDS
   └─ Adds V2 salary fields to hr_contract model
   └─ Adds liquidation tracking fields
   └─ Adds custom form views with V2 field notebooks
   └─ MUST update BEFORE payroll enhancements
```

**Phase 3: Custom Payroll Features (USES V2 Fields)**
```
4. ueipab_payroll_enhancements (v17.0.1.33.0)
   └─ Depends on: hr_payroll_community, ueipab_hr_contract v1.5.0
   └─ USES V2 fields in salary structures (VE_PAYROLL_V2, LIQUID_VE_V2)
   └─ DEPLOY files then INSTALL

5. hr_payslip_monthly_report (v17.0.1.2)
   └─ Depends on: hr_payroll_community
   └─ Email delivery system
   └─ DEPLOY files then INSTALL
```

### 4.2 Dependency Graph

```
hr_payroll_community (BASE)
    ├── hr_payroll_account_community
    ├── ueipab_hr_contract v1.5.0 ⭐ CREATES V2 FIELDS
    │   └── ueipab_payroll_enhancements v1.33.0 (USES V2 FIELDS)
    └── hr_payslip_monthly_report v1.2
```

### 4.3 V2 Fields Flow

```
Step 4: ueipab_hr_contract UPDATE
    ↓
[V2 fields created in database]
    ↓
Step 5: ueipab_payroll_enhancements INSTALL
    ↓
[Salary rules reference V2 fields]
    ↓
[Contracts can be created with V2 data]
```

---

## 5. Pre-Migration Requirements

### 5.1 Access Checklist

- [x] SSH access to production (root@10.124.0.3) - ✅ VERIFIED
- [x] Production analysis complete - ✅ COMPLETED 2025-11-24
- [x] Employee data validation complete - ✅ COMPLETED 2025-11-24
- [ ] Database admin credentials (PostgreSQL user)
- [ ] Odoo admin credentials (web interface)
- [ ] File system write permissions to addons directory
- [ ] Sudo/root access confirmed

**SSH Access (Provided by User):**
```bash
Server: 10.124.0.3
User: root
Password: g)9nE>?rq-#v3Hn
```

### 5.2 Pre-Migration Data Cleanup (Day -1)

**Required Before Module Deployment:**
- [ ] Reactivate YOSMARI GONZÁLEZ (employee ID 615)
- [ ] Assign department to MARIA DANIELA JIMENEZ LADERA
- [ ] Collect and add VAT ID for Gustavo Perdomo
- [ ] Collect and add VAT ID for Luis Rodriguez
- [ ] Verify all 4 employees with script from Section 3.2

**Timeline:** 30-60 minutes (HR + Technical Team)

### 5.3 Backup Requirements (⚠️ MANDATORY BEFORE DEPLOYMENT)

**Critical Backups Required:**

**1. Full Database Backup**
```bash
# On production server:
ssh root@10.124.0.3

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
# Backup Odoo config:
docker exec ueipab17 cat /etc/odoo/odoo.conf > \
    /backups/odoo.conf.$(date +%Y%m%d)
```

---

## 6. Risk Assessment

### 6.1 Risk Matrix (44 Employees Scope)

| Risk | Probability | Impact | Mitigation | Severity |
|------|-------------|--------|------------|----------|
| **Module dependency conflicts** | LOW | MEDIUM | Follow exact installation order | LOW |
| **Database migration failures** | LOW | HIGH | Full backup, test rollback plan | LOW |
| **Contract data issues (44 employees)** | VERY LOW | MEDIUM | Pre-validated in testing | VERY LOW |
| **Employee data errors (4 employees)** | MEDIUM | LOW | Pre-cleanup completed before deployment | LOW |
| **Accounting configuration errors** | MEDIUM | HIGH | Document account setup, test validation | MEDIUM |
| **Production data corruption** | VERY LOW | CRITICAL | Full backup mandatory | VERY LOW |

**Overall Risk Level:** **LOW** ✅
(Significantly reduced by focusing on 44 validated employees + pre-cleanup)

### 6.2 Success Factors (44 Employees)

**Advantages of 44 Employee Scope:**
1. ✅ All 44 have validated contracts in testing (known good data)
2. ✅ All 44 have VAT IDs (after pre-cleanup)
3. ✅ 90.9% already have departments in production
4. ✅ Contract data can be exported from testing (CSV or direct copy)
5. ✅ Lower risk than all 50 employees (focused scope)

**Criteria for Success:**
- ✅ All 5 modules installed successfully
- ✅ V2 contract fields visible in UI
- ✅ At least 5 test contracts created and validated
- ✅ Test payslips generated successfully
- ✅ Accounting entries balanced
- ✅ Email delivery tested

---

## 7. Migration Steps

### 7.1 Pre-Deployment Phase (Day -1) - 2 Hours

#### Step 1: Complete Data Cleanup (15-30 min) - UPDATED

**Status:** ✅ **3 of 4 ALREADY FIXED** - Only Gustavo Perdomo remains!

**Already Fixed (No action required):**
- ✅ YOSMARI GONZÁLEZ - Reactivated
- ✅ Luis Rodriguez - VAT ID added (V18453474)
- ✅ MARIA JIMENEZ - Acceptable without department

**Remaining Fix Required:**

```bash
# Connect to production:
ssh root@10.124.0.3

# 1. Update Gustavo Perdomo (HR must provide real cédula and department):
docker exec -i ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB << 'EOF'
-- Replace [REAL_CEDULA] with actual cédula from HR
-- Replace [DEPT_ID] with appropriate department (51, 53, 54, 55, 56, 57, or 59)

UPDATE hr_employee
SET identification_id = 'V[REAL_CEDULA]',
    department_id = [DEPT_ID]
WHERE id = 761 AND name = 'Gustavo Perdomo';

-- Verify update:
SELECT id, name, identification_id, department_id
FROM hr_employee
WHERE id = 761;
EOF

# Expected output:
# 761 | Gustavo Perdomo | V[REAL_CEDULA] | [DEPT_ID]

# 2. Run final verification (all 4 employees):
docker exec -i ueipab17_postgres_1 psql -U odoo -d DB_UEIPAB << 'EOF'
SELECT
    id,
    name,
    identification_id,
    CASE WHEN department_id IS NULL THEN '❌ NO DEPT' ELSE '✅ OK' END as dept_status
FROM hr_employee
WHERE id IN (615, 595, 600, 761)
ORDER BY name;
EOF

# Expected output:
# 595 | LUIS RODRIGUEZ   | V18453474 | ✅ OK
# 600 | MARIA JIMENEZ    | V30597749 | ❌ NO DEPT (acceptable)
# 615 | YOSMARI GONZALEZ | V17009331 | ✅ OK
# 761 | Gustavo Perdomo  | V[REAL]   | ✅ OK  ← This should be fixed now
```

**Available Departments for Gustavo Perdomo:**
```
51: AUXILIAR DE SOPORTE Y DESARROLLO
53: Control de Estudios
54: Dirección
55: Docentes (most common - 22 employees)
56: Mantenimiento
57: Operaciones (9 employees)
59: Soporte (2 employees)
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

#### Step 3: Prepare Module Files (30 min)

```bash
# On testing server (or use scp from development):
cd /opt/odoo-dev/addons

# Create deployment package:
tar -czf /tmp/payroll_deployment_$(date +%Y%m%d).tar.gz \
    ueipab_hr_contract/ \
    ueipab_payroll_enhancements/ \
    hr_payslip_monthly_report/

# Verify package:
tar -tzf /tmp/payroll_deployment_*.tar.gz | grep __manifest__.py
# Expected: 3 manifest files

# Transfer to production:
scp /tmp/payroll_deployment_*.tar.gz root@10.124.0.3:/tmp/
```

---

### 7.2 Deployment Phase (Day 0) - 2 Hours

**Timeline:** Saturday evening 6:00 PM - 8:00 PM
**Responsible:** Technical Team Lead

#### Phase 1: Extract Module Files (15 min)

```bash
# Connect to production:
ssh root@10.124.0.3

# Navigate to container's addon directory:
docker exec -it ueipab17 bash

# Inside container:
cd /mnt/extra-addons

# Extract deployment package:
tar -xzf /tmp/payroll_deployment_*.tar.gz

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
```

#### Phase 3: Install Base Payroll Modules (20 min)

```bash
# Install hr_payroll_community:
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i hr_payroll_community \
    --stop-after-init \
    --log-level=info

# Install hr_payroll_account_community:
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
    print(f"  ✅ {m.name}: {m.state}")
env.cr.commit()
EOF
```

#### Phase 4: Update ueipab_hr_contract (15 min) ⭐ V2 FIELDS CREATED HERE

```bash
# Update contract module (v1.0.0 → v1.5.0):
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -u ueipab_hr_contract \
    --stop-after-init \
    --log-level=info

# Verify V2 fields created:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_hr_contract')])
print(f"✅ ueipab_hr_contract: {module.state} (v{module.latest_version})")

# Verify V2 fields exist:
Contract = env['hr.contract']
v2_fields = ['ueipab_salary_v2', 'ueipab_bonus_v2', 'ueipab_extrabonus_v2',
             'ueipab_vacation_prepaid_amount']

print("\n📋 V2 Fields Status:")
for field in v2_fields:
    if hasattr(Contract, field):
        print(f"  ✅ {field}")
    else:
        print(f"  ❌ {field} MISSING!")

env.cr.commit()
EOF

# Expected output: All 4 V2 fields present
```

#### Phase 5: Install Custom Payroll Enhancements (20 min)

```bash
# Install ueipab_payroll_enhancements (USES V2 fields):
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -i ueipab_payroll_enhancements \
    --stop-after-init \
    --log-level=info

# Verify salary structures created:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
print(f"✅ {module.name}: {module.state}")

# Check salary structures:
structures = env['hr.payroll.structure'].search([])
print(f"\n📊 Salary Structures: {len(structures)} found")
for s in structures:
    print(f"  - {s.name} (code: {s.code or 'N/A'})")

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
```

#### Phase 7: Start Odoo and Clear Assets (20 min)

```bash
# Start Odoo container:
docker start ueipab17

# Wait for startup (60 seconds):
sleep 60

# Clear assets:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
env['ir.attachment'].search([
    ('res_model', '=', 'ir.ui.view'),
    ('name', 'like', 'web_assets%')
]).unlink()
print("✅ Assets cleared")
env.cr.commit()
EOF

# Restart container:
docker restart ueipab17
sleep 60
```

---

## 8. Contract Creation (44 Employees)

### 8.1 Contract Data Source

**All 44 employees have validated contracts in testing database.**

**Options for Contract Creation:**

**Option A: Manual Creation (5-10 test employees)**
- Create 5-10 contracts manually via UI
- Validate system working correctly
- Continue with remaining employees later

**Option B: CSV Import (Recommended for all 44)**
- Export contract data from testing database
- Import via Odoo import tool
- Faster, less error-prone

**Option C: Database Copy (Advanced)**
- Export contracts from testing database (SQL)
- Import to production database
- Requires careful ID mapping

### 8.2 Recommended Approach: Phased Creation

**Phase A: Test Contracts (5-10 employees) - 30 minutes**

Create 5-10 contracts manually to validate system:

```
1. Login to Odoo: http://10.124.0.3:8069
2. Navigate: Employees → Contracts → Create
3. For each test employee:
   - Employee: Select from list
   - Start Date: First of current month
   - Salary Structure: VE_PAYROLL_V2
   - 💼 Salary Breakdown tab:
     - ueipab_salary_v2: [from testing]
     - ueipab_bonus_v2: [from testing]
     - ueipab_extrabonus_v2: [from testing]
     - cesta_ticket_usd: [from testing]
   - Verify wage auto-calculated correctly
   - Save

4. Generate test payslip (Section 9.3)
```

**Phase B: Bulk Creation (Remaining 34-39 employees) - 1-2 hours**

Two approaches:

**Approach 1: CSV Import**
```bash
# 1. Export contract data from testing:
docker exec -i odoo-dev-postgres psql -U odoo -d testing -c "
COPY (
  SELECT
    e.name as employee_name,
    e.identification_id,
    c.date_start,
    c.date_end,
    c.wage,
    c.ueipab_salary_v2,
    c.ueipab_bonus_v2,
    c.ueipab_extrabonus_v2,
    c.cesta_ticket_usd,
    s.name as structure_name
  FROM hr_contract c
  JOIN hr_employee e ON c.employee_id = e.id
  JOIN hr_payroll_structure s ON c.structure_type_id = s.id
  WHERE c.state = 'open'
  AND e.identification_id IS NOT NULL
  ORDER BY e.name
) TO STDOUT WITH CSV HEADER;
" > /tmp/contracts_44_employees.csv

# 2. Review CSV file:
cat /tmp/contracts_44_employees.csv | head -10

# 3. Import via Odoo UI:
#    Navigate: Employees → Contracts
#    Click: Import
#    Upload: contracts_44_employees.csv
#    Map fields and validate
#    Import all 44 contracts
```

**Approach 2: Python Script (Odoo Shell)**
```bash
# Create contract creation script:
cat > /tmp/create_contracts_44.py << 'EOF'
# Script to create contracts for 44 employees
# Data source: Testing database contracts

Employee = env['hr.employee']
Contract = env['hr.contract']
Structure = env['hr.payroll.structure'].search([('code', '=', 'VE_PAYROLL_V2')])

# Example data (populate from testing export):
employee_data = [
    {
        'vat': 'V30712714',
        'start_date': '2024-09-01',
        'salary_v2': 146.19,
        'bonus_v2': 198.83,
        'extrabonus_v2': 42.58,
        'cesta': 40.00
    },
    # ... (add all 44 employees)
]

created = 0
for data in employee_data:
    emp = Employee.search([('identification_id', '=', data['vat'])])
    if not emp:
        print(f"❌ Employee not found: {data['vat']}")
        continue

    # Check if contract already exists:
    existing = Contract.search([
        ('employee_id', '=', emp.id),
        ('state', '=', 'open')
    ])
    if existing:
        print(f"⚠️  Contract exists: {emp.name}")
        continue

    # Create contract:
    contract = Contract.create({
        'name': f'Contract - {emp.name}',
        'employee_id': emp.id,
        'date_start': data['start_date'],
        'structure_type_id': Structure.id,
        'ueipab_salary_v2': data['salary_v2'],
        'ueipab_bonus_v2': data['bonus_v2'],
        'ueipab_extrabonus_v2': data['extrabonus_v2'],
        'cesta_ticket_usd': data['cesta'],
        'state': 'open'
    })

    print(f"✅ Created: {emp.name} (wage: ${contract.wage})")
    created += 1

print(f"\n📊 Total contracts created: {created}/44")
env.cr.commit()
EOF

# Execute script:
docker exec -i ueipab17 odoo shell -d DB_UEIPAB < /tmp/create_contracts_44.py
```

### 8.3 Contract Creation Verification

**After creating all contracts:**

```bash
# Verify contract count:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
Contract = env['hr.contract']
contracts = Contract.search([('state', '=', 'open')])

print(f"\n📊 Active Contracts: {len(contracts)}")
print(f"   Target: 44 contracts")

# Verify V2 fields populated:
v2_count = 0
for c in contracts:
    if c.ueipab_salary_v2 and c.ueipab_bonus_v2:
        v2_count += 1

print(f"\n✅ Contracts with V2 fields: {v2_count}/{len(contracts)}")

# List employees without contracts:
Employee = env['hr.employee']
all_employees = Employee.search([('active', '=', True)])
employees_with_contracts = contracts.mapped('employee_id')
no_contract = all_employees - employees_with_contracts

print(f"\n⚠️  Employees WITHOUT contracts: {len(no_contract)}")
for e in no_contract[:5]:
    print(f"   - {e.name}")

env.cr.commit()
EOF
```

---

## 9. Testing & Validation

### 9.1 UI Verification (10 min)

```
1. Login to Odoo as admin: http://10.124.0.3:8069
2. Enable Developer Mode
3. Verify Payroll menu accessible
4. Check HR Contract form:
   - Open any contract
   - ✅ See "💼 Salary Breakdown" notebook page
   - ✅ See V2 fields populated
```

### 9.2 Contract Data Validation (15 min)

```
1. Random sample 5 contracts
2. Compare with testing database:
   - Employee name matches
   - VAT ID matches
   - Wage matches
   - V2 fields match (salary_v2, bonus_v2, extrabonus_v2)
   - Structure assignment correct
3. ✅ PASS: All 5 match testing data
```

### 9.3 Test Payslip Generation (20 min)

```
1. Create test batch:
   Payroll → Batches → Create
   Name: "TEST_44_EMPLOYEES_2025_11_24"
   Period: Current month (1st to 15th)

2. Generate payslips:
   - Click "Generate Payslips"
   - Select 5 test employees
   - Structure: VE_PAYROLL_V2
   - Generate

3. Compute sheets:
   - Open each payslip
   - Click "Compute Sheet"
   - ✅ Lines calculated without errors
   - ✅ NET amount correct

4. Validate payslips:
   - Confirm each payslip
   - ✅ Accounting entries created
   - ✅ Entries balanced
```

### 9.4 Email Delivery Test (10 min)

```
1. Verify SMTP configured
2. Test batch → "Send Payslips by Email"
3. ✅ Emails sent successfully
4. ✅ PDF attachments present
5. ✅ Template rendered correctly
```

---

## 10. Rollback Procedures

### 10.1 Rollback Decision Criteria

**Trigger Rollback if:**
- ❌ V2 fields not created after ueipab_hr_contract update
- ❌ Module installation fails with critical errors
- ❌ Payslip generation fails repeatedly
- ❌ Accounting entries unbalanced
- ❌ Database corruption detected

### 10.2 Rollback Steps (30-45 minutes)

```bash
# 1. Stop Odoo:
docker stop ueipab17

# 2. Restore database:
docker exec -i ueipab17_postgres_1 pg_restore \
    -U odoo -d DB_UEIPAB --clean \
    /backups/DB_UEIPAB_pre_payroll_*.dump

# 3. Restore addon files:
docker cp /backups/addons_*.tar.gz ueipab17:/tmp/
docker exec ueipab17 bash -c "
cd /mnt/extra-addons
tar -xzf /tmp/addons_*.tar.gz
"

# 4. Restart Odoo:
docker start ueipab17
sleep 60

# 5. Verify rollback:
docker logs ueipab17 --tail=100
```

---

## 11. Post-Migration Configuration

### 11.1 Create Salary Structures (30 min)

**IMPORTANT:** Salary structures are database-only (not in XML files).
They must be manually created in production after module installation.

**3 Structures to Create:**

**1. VE_PAYROLL_V2** (Regular payroll - 11 rules)
```
Navigation: Payroll → Configuration → Salary Structures → Create

Fields:
  Name: Venezuelan Payroll V2
  Code: VE_PAYROLL_V2
  Parent Structure: (None)

Rules to add (in sequence order):
  [001] VE_BASIC_V2 - Base Salary V2
  [002] VE_BONUS_V2 - Regular Bonus V2
  [003] VE_EXTRABONUS_V2 - Extra Bonus V2
  [004] VE_CESTA - Food Allowance (Cesta Ticket)
  [010] VE_SSO_DED_V2 - Social Security Deduction (4.5%)
  [011] VE_FAOV_DED_V2 - Housing Fund Deduction (1.0%)
  [012] VE_PARO_DED_V2 - Unemployment Insurance (0.5%)
  [013] VE_ARI_DED_V2 - Income Tax Withholding (Variable %)
  [099] VE_GROSS_V2 - Gross Salary
  [100] VE_DEDUCTIONS_V2 - Total Deductions
  [999] VE_NET_V2 - Net Salary

Save
```

**2. LIQUID_VE_V2** (Liquidation - 14 rules)
```
Name: Liquidación Laboral V2
Code: LIQUID_VE_V2
Parent Structure: (None)

Rules to add:
  [Similar to testing, see export_salary_structures.py output]

Save
```

**3. AGUINALDOS_2025** (Christmas bonus)
```
Name: Aguinaldos 2025
Code: AGUINALDOS_2025
Parent Structure: (None)

Rules to add:
  [Uses AGUINALDO_V2 rule]

Save
```

**Reference Script:**
- `/opt/odoo-dev/scripts/export_salary_structures.py` (127 lines)
- Run in testing to see exact rule assignments

### 11.2 Accounting Configuration (15 min)

```bash
# Configure salary rule accounts:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB < /opt/odoo-dev/scripts/configure_v2_salary_rule_accounts.py

# Verify configuration:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
SalaryRule = env['hr.salary.rule']
rules = SalaryRule.search([('code', 'like', '_V2')])

print("\n📊 Salary Rule Accounting:")
for rule in rules:
    if rule.account_debit_id and rule.account_credit_id:
        print(f"  ✅ {rule.code}")
    else:
        print(f"  ❌ {rule.code}: NOT CONFIGURED")
env.cr.commit()
EOF
```

### 11.3 SMTP Configuration (10 min)

```
1. Navigate: Settings → Technical → Email → Outgoing Mail Servers
2. Verify SMTP server configured
3. Test connection
4. Enable auto-send: Settings → Payroll → Automatic Send Payslip By Mail
```

---

## 12. Approval Checklist

### 12.1 Pre-Deployment Approval

**Technical Readiness:**
- [x] Employee data validation complete (✅ COMPLETED 2025-11-24)
- [x] Data cleanup plan ready (✅ **3 of 4 FIXED** - only Gustavo Perdomo remains)
- [ ] Module files prepared and tested
- [ ] Backup procedures validated
- [x] Rollback plan documented
- [x] Contract creation strategy defined (44 employees)

**Infrastructure Readiness:**
- [ ] Production access confirmed
- [ ] Backup storage verified
- [ ] Deployment window scheduled
- [ ] Technical team availability confirmed

**Business Readiness:**
- [ ] Payroll team notified
- [ ] Training session scheduled
- [ ] HR team informed (44 employee scope)

### 12.2 Go/No-Go Checklist (Final Review) - UPDATED 2025-11-24

**Pre-Deployment (Day -1) - Employee Data Status:**
- [x] **YES** ~~YOSMARI GONZÁLEZ reactivated~~ ✅ **DONE** (active=t, dept=57, vat=V17009331)
- [x] **YES** ~~Luis Rodriguez VAT ID added~~ ✅ **DONE** (vat=V18453474, dept=55)
- [x] **YES** ~~MARIA DANIELA JIMENEZ status verified~~ ✅ **ACCEPTABLE** (no dept by design)
- [ ] **YES** Gustavo Perdomo VAT ID collected and added ⚠️ **PENDING**
- [ ] **YES** Gustavo Perdomo department assigned ⚠️ **PENDING**
- [ ] **YES** Gustavo Perdomo verified ready ⚠️ **PENDING**

**Critical:** Only 1 employee (Gustavo Perdomo) needs data before deployment!

**Deployment Day:**
- [ ] **YES** Full database backup completed and verified
- [ ] **YES** Addon files backup completed
- [ ] **YES** Deployment window scheduled (off-peak)
- [ ] **YES** Technical team available (3-4 hours)
- [ ] **YES** Rollback plan ready
- [ ] **YES** Contract data from testing exported/ready

**Any "NO" = NO-GO (reschedule deployment)**

### 12.3 Success Criteria (44 Employees)

**Module Installation:**
- [ ] All 5 modules installed successfully
- [ ] V2 fields visible in contract form
- [ ] Salary structures created (3 structures)
- [ ] No critical errors in logs

**Contract Creation:**
- [ ] 5-10 test contracts created successfully
- [ ] Test payslips generated successfully
- [ ] Accounting entries balanced
- [ ] Email delivery tested

**Optional (if time permits):**
- [ ] All 44 contracts created
- [ ] Random sample validation (5 contracts match testing)

**Final Validation:**
- [ ] System stable (no errors for 30 minutes)
- [ ] Payroll team can access system
- [ ] Documentation handoff complete

---

## 13. Timeline Summary

### 13.1 Deployment Timeline

**Day -1 (Pre-Deployment):**
- Data cleanup: 30-60 min
- Backups: 30 min
- Module file prep: 30 min
- **Total:** 2 hours

**Day 0 (Deployment):**
- Module deployment: 2 hours
- Test contract creation: 30 min
- Testing & validation: 45 min
- **Total:** 3-4 hours

**Day 1 (Post-Deployment):**
- Bulk contract creation: 1-2 hours (optional)
- Training: 1 hour
- **Total:** 2-3 hours

**Total Project Duration:** 7-9 hours (spread over 2-3 days)

### 13.2 Critical Path

```
Day -1: Data Cleanup
    ↓
Day 0: Module Deployment (2 hours)
    ↓
Day 0: V2 Fields Available (Step 4 complete)
    ↓
Day 0: Test Contracts (5-10 employees, 30 min)
    ↓
Day 0: Testing & Validation (45 min)
    ↓
Decision: GO or NO-GO
    ↓
    [GO] → Day 1: Bulk Contracts (remaining 34-39 employees)
    [NO-GO] → Rollback (45 min)
```

---

## 14. Post-Deployment Success Metrics

**First Week Monitoring:**

```bash
# Track contract creation:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
contracts = env['hr.contract'].search([('state', '=', 'open')])
print(f"Active contracts: {len(contracts)}/44")

payslips = env['hr.payslip'].search([])
print(f"Payslips generated: {len(payslips)}")

batches = env['hr.payslip.run'].search([])
print(f"Batches created: {len(batches)}")
EOF
```

**Success Indicators:**
- ✅ All 44 contracts created successfully
- ✅ At least 1 full payroll batch generated
- ✅ Zero critical errors in production logs
- ✅ Payroll team comfortable with system
- ✅ Email delivery working correctly

---

## Appendices

### Appendix A: 44 Employee List (Sample)

**Full list available in:**
- `/tmp/testing_contract_employees.txt` (44 lines)
- Generated from testing database
- Contains: VAT ID, Name, Email for all 44 employees

**Sample (first 10):**
```
V30712714 | ALEJANDRA LOPEZ | alejandra.lopez@ueipab.edu.ve
V10938616 | ANDRES MORALES | andres.morales@ueipab.edu.ve
V8478634 | ARCIDES ARZOLA | arcides.arzola@ueipab.edu.ve
V17870047 | AUDREY GARCIA | audrey.garcia@ueipab.edu.ve
V29807160 | CAMILA ROSSATO | camila.rossato@ueipab.edu.ve
...
```

### Appendix B: Module Feature Summary

**ueipab_hr_contract v1.5.0:**
- ✅ **CREATES V2 contract fields** (Step 4)
- ✅ ueipab_salary_v2, ueipab_bonus_v2, ueipab_extrabonus_v2
- ✅ ueipab_vacation_prepaid_amount, ueipab_original_hire_date
- ✅ Custom form views with V2 field notebooks

**ueipab_payroll_enhancements v1.33.0:**
- ✅ **USES V2 fields** in salary rules (Step 5)
- ✅ VE_PAYROLL_V2 structure (references V2 fields)
- ✅ LIQUID_VE_V2 structure (references V2 fields)
- ✅ 5 custom reports (PDF/Excel export)
- ✅ Batch enhancements, email templates

### Appendix C: Key Documentation References

1. **CUSTOM_FIELDS_AVAILABILITY_TIMELINE.md** (331 lines)
   - Exact timeline for V2 field availability
   - Step-by-step module deployment impact

2. **EMPLOYEE_DATA_VALIDATION_REPORT.md** (458 lines)
   - Complete employee data analysis
   - Bank accounts, VAT IDs, emails, departments

3. **DATA_MIGRATION_ANALYSIS.md** (564 lines)
   - What data needs migration vs. auto-creation
   - Salary structure manual creation guide

4. **CONTRACT_MIGRATION_PLAN.md** (671 lines)
   - Original plan for all 50 employees
   - Contract creation workflows

### Appendix D: Emergency Contacts

| Role | Responsibility | Availability |
|------|----------------|--------------|
| **Technical Lead** | Deployment, rollback, troubleshooting | On-call during deployment |
| **Database Admin** | Database issues, backups | On-call (emergencies) |
| **HR Manager** | Employee data verification | Mon-Fri 9-5 |
| **Payroll Manager** | Process validation, training | Mon-Fri 9-5 |

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| **3.2** | **2025-11-24** | **🎉 PHASE 1 DEPLOYMENT COMPLETE!** |
| | | - ✅ All 5 modules successfully installed in production |
| | | - ✅ 15 V2 contract fields created |
| | | - ✅ Backups created before deployment |
| | | - ✅ Fixed hr_payroll_community attrs syntax issue |
| | | - ✅ Installed python-docx dependency |
| | | - ✅ Fixed ueipab_payroll_enhancements manifest load order |
| | | - ✅ Gustavo Perdomo override approved (CEO testing account) |
| | | - Next: Create salary structures + contracts (Phase 2) |
| 3.1 | 2025-11-24 | Updated: 3 of 4 employees fixed |
| 3.0 | 2025-11-24 | **44 EMPLOYEE FOCUS** - Complete rewrite |
| 2.0 | 2025-11-23 | Production analysis, all 50 employees |
| 1.0 | 2025-11-10 | Initial draft |

---

## 📊 Status Summary

**Current Status:** 🟢 **PHASE 1 COMPLETE - MODULES DEPLOYED!**

**Deployment Completed (2025-11-24 22:06 UTC):**
| Step | Status | Duration |
|------|--------|----------|
| Pre-deployment backup | ✅ Complete | 3 min |
| Transfer module files | ✅ Complete | 2 min |
| Install hr_payroll_community | ✅ Complete | 3 min |
| Install hr_payroll_account_community | ✅ Complete | 2 min |
| Install ueipab_hr_contract v1.5.0 | ✅ Complete | 2 min |
| Install ueipab_payroll_enhancements v1.34.0 | ✅ Complete | 5 min |
| Install hr_payslip_monthly_report v1.2 | ✅ Complete | 2 min |
| **Total Deployment Time** | **✅ Complete** | **~35 min** |

**Issues Resolved During Deployment:**
1. ✅ Fixed `hr_payroll_community` (replaced version with deprecated `attrs` syntax)
2. ✅ Installed `python-docx` library for DOCX export functionality
3. ✅ Fixed `ueipab_payroll_enhancements` manifest (data file load order)

**What's Available Now:**
- ✅ All 5 payroll modules installed and operational
- ✅ 15 V2 contract fields created in database
- ✅ Custom reports menu in Payroll
- ✅ Email delivery system ready
- ✅ Payslip batch enhancements active

**Next Steps (Phase 2):**
1. ⏳ Create Venezuelan salary structures manually (VE_PAYROLL_V2, LIQUID_VE_V2, AGUINALDOS_2025)
2. ⏳ Create test contracts for 5-10 employees
3. ⏳ Generate test payslips and validate
4. ⏳ Create remaining 34-39 contracts
5. ⏳ Configure accounting entries
6. ⏳ Train payroll team

**Gustavo Perdomo Override:**
- ℹ️ CEO testing account - skipped data cleanup (approved by user)
- Does not affect 43 other employees

**Estimated Remaining Work:**
- Salary structure creation: 30-45 min
- Test contracts (5-10): 30 min
- Validation: 30 min
- Bulk contracts (34-39): 1-2 hours
- **Total Phase 2: 3-4 hours**

---

**END OF MIGRATION PLAN V3**

**Document prepared by:** Technical Team
**Document prepared for:** UEIPAB Management - Final Review (44 Employee Scope)
**Preparation date:** November 24, 2025
**Employee data validation date:** November 24, 2025
**Deployment target:** TBD (pending approval)
