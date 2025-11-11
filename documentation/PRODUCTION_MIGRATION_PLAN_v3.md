# Production Migration Plan v3.0
**Updated:** November 10, 2025
**Status:** READY FOR REVIEW
**Author:** UEIPAB Technical Team
**Target Environment:** Production (10.124.0.3)

---

## 🎯 Executive Summary

This document outlines the **comprehensive migration plan** to deploy all payroll fixes and enhancements from local development to production. This includes:

1. **Database Employee Sync** - 43 employees contract updates from Google Sheets
2. **Payroll Formula Fixes** - 4 critical bug fixes (wage field, deductions, spreadsheet formula, journal entries)
3. **Module Deployment** - ueipab_payroll_enhancements module with structure selector

**Migration Type:** Critical Fixes + Enhancement Deployment
**Risk Level:** MEDIUM (due to payroll formula changes)
**Expected Downtime:** None (configuration changes only)
**Rollback Complexity:** LOW (all changes backed up with restore scripts)

---

## 📋 Table of Contents

1. [What's Being Deployed](#1-whats-being-deployed)
2. [Pre-Migration Requirements](#2-pre-migration-requirements)
3. [Risk Assessment](#3-risk-assessment)
4. [Migration Steps](#4-migration-steps)
5. [Testing & Validation](#5-testing--validation)
6. [Rollback Procedures](#6-rollback-procedures)
7. [Post-Migration Actions](#7-post-migration-actions)
8. [Approval Checklist](#8-approval-checklist)

---

## 1. What's Being Deployed

### 1.1 Database Employee Sync ✅

**Purpose:** Update 43 employee contracts with correct salary data from Google Sheets

**Components:**
- Contract wage field (GROSS salary: K+M+L)
- ueipab_salary_base (K - 70% component)
- ueipab_bonus_regular (M - 25% component)
- ueipab_extra_bonus (L - 5% component)

**Impact:**
- 43 employees updated
- All future payslips will use correct salary values
- Past payslips (Sept 2023 - Oct 2025) NOT affected (already finalized)

**Script:** `scripts/update-contracts-from-spreadsheet-FIXED.py`

**Example (NELCI BRITO):**
- BEFORE: wage = $350.00 (incorrect)
- AFTER: wage = $317.29 (K=$140.36 + M=$176.94 + L=$0.00)

---

### 1.2 Payroll Formula Fixes ✅

**4 Critical Bugs Fixed:**

#### Fix #1: Contract Wage Field Not Updated
**Problem:** Sync script wasn't updating the `wage` field
**Impact:** All employees had wrong wage values
**Fix:** Added wage field to UPDATE query
**Backup:** `contract_salary_backup_20251110_190655`

#### Fix #2: Deductions Applied to Wrong Base
**Problem:** Deductions applied to K+M+L instead of K only
**Impact:** Deductions were 4× too high (NELCI: $9.32 vs $2.37)
**Fix:** Changed 4 deduction formulas to apply ONLY to K
**Backup:** `salary_rules_backup_20251110_192020`

#### Fix #3: Formula Not Matching Spreadsheet
**Problem:** Odoo NET showed $176.19 but spreadsheet showed $153.91
**Root Cause:** Spreadsheet uses: (Salary ÷ 2) - MONTHLY Deductions
**Fix:** DOUBLED deduction rates, removed cesta from bi-weekly
**Backup:** `payroll_rules_backup_20251110_194011`

**New Rates:**
- SSO: 2.25% → **4.5%**
- FAOV: 0.5% → **1%**
- Paro: 0.125% → **0.25%**
- ARI: 0.5% → **1%**
- Cesta: $20 → **$0** (excluded from bi-weekly)

#### Fix #4: Journal Entries Not Configured
**Problem:** NET posting directly to bank instead of liability account
**Impact:** No tracking of payable amounts
**Fix:** Configured VE_NET rule with correct Dr./Cr. accounts
**Backup:** `salary_rule_accounts_backup_20251110_200030`

**Journal Entry Configuration:**
- Debit: 5.1.01.10.001 (Nómina expense)
- Credit: 2.1.01.01.002 (Payable liability)

---

### 1.3 Module Deployment ✅

**Module:** ueipab_payroll_enhancements v17.0.1.0.0

**Features:**
- Payroll Batch Structure Selector wizard
- Smart detection of "Aguinaldos" batches
- Automatic structure pre-selection
- Backward compatible with existing workflows

**Dependencies:**
- hr_payroll_community
- ueipab_hr_contract

**Size:** 40KB (3 files)

---

## 2. Pre-Migration Requirements

### 2.1 Access Checklist

- [ ] SSH access to production server (10.124.0.3)
- [ ] Database credentials (user: odoo, password: [verify])
- [ ] Odoo admin credentials
- [ ] Google Sheets API credentials (for sync script)
- [ ] Sudo/root access for file operations

### 2.2 Production Environment Assessment

**Before starting, verify:**

```bash
# 1. Check Odoo version (must be 17.0)
docker exec odoo-production odoo --version

# 2. Check database name and connection
docker exec odoo-production-db psql -U odoo -l | grep testing

# 3. Verify addons path
docker exec odoo-production cat /etc/odoo/odoo.conf | grep addons_path

# 4. Check disk space (need at least 1GB free)
df -h /opt/odoo

# 5. Check current payroll structure
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT name, state FROM ir_module_module
WHERE name LIKE 'ueipab%' OR name LIKE '%payroll%';"

# 6. Verify no active payroll batches
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) FROM hr_payslip_run WHERE state = 'draft';"

# 7. Check for users currently logged in
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) FROM res_users
WHERE login_date > NOW() - INTERVAL '1 hour';"
```

### 2.3 Backup Requirements (MANDATORY)

**Create ALL backups before proceeding:**

```bash
# 1. Full database backup
docker exec odoo-production-db pg_dump -U odoo -Fc testing > \
    /backups/testing_pre_migration_$(date +%Y%m%d_%H%M%S).dump

# Verify backup size (should be > 50MB)
ls -lh /backups/testing_pre_migration_*.dump

# 2. Export current contracts (for verification)
docker exec odoo-production-db psql -U odoo -d testing -c "
COPY (
    SELECT
        e.name as employee,
        c.wage,
        c.ueipab_salary_base,
        c.ueipab_bonus_regular,
        c.ueipab_extra_bonus
    FROM hr_contract c
    JOIN hr_employee e ON e.id = c.employee_id
    WHERE c.state = 'open'
    ORDER BY e.name
) TO '/tmp/contracts_before_sync.csv' WITH CSV HEADER;"

# Copy to host
docker cp odoo-production-db:/tmp/contracts_before_sync.csv \
    /backups/contracts_before_sync_$(date +%Y%m%d).csv

# 3. Export current salary rules
docker exec odoo-production-db psql -U odoo -d testing -c "
COPY (
    SELECT code, name, amount_python_compute
    FROM hr_salary_rule
    WHERE code LIKE 'VE_%'
) TO '/tmp/salary_rules_before.csv' WITH CSV HEADER;"

docker cp odoo-production-db:/tmp/salary_rules_before.csv \
    /backups/salary_rules_before_$(date +%Y%m%d).csv

# 4. Backup addons directory
tar -czf /backups/addons_backup_$(date +%Y%m%d).tar.gz \
    /opt/odoo/addons/ueipab_*

# 5. Configuration backup
cp /opt/odoo/config/odoo.conf /backups/odoo.conf.$(date +%Y%m%d)
```

### 2.4 Required Files Transfer

**Copy scripts and module from development to production:**

```bash
# On development machine:
cd /opt/odoo-dev

# Create deployment package
tar -czf payroll_deployment_$(date +%Y%m%d).tar.gz \
    scripts/update-contracts-from-spreadsheet-FIXED.py \
    scripts/fix-deduction-rules.py \
    scripts/fix-payroll-to-match-spreadsheet.py \
    scripts/configure-payroll-journal-entries.py \
    addons/ueipab_payroll_enhancements/ \
    documentation/PAYROLL_SYSTEM_COMPLETE.md

# Transfer to production
scp payroll_deployment_*.tar.gz root@10.124.0.3:/tmp/

# On production server:
cd /tmp
tar -xzf payroll_deployment_*.tar.gz
```

---

## 3. Risk Assessment

### 3.1 Risk Matrix

| Risk | Probability | Impact | Mitigation | Severity |
|------|-------------|--------|------------|----------|
| **Contract sync errors** | LOW | HIGH | Tested on 43 employees, backups available | MEDIUM |
| **Payroll calculation errors** | LOW | CRITICAL | Formulas match spreadsheet exactly, verified | MEDIUM |
| **Journal entry posting errors** | LOW | HIGH | Accounts verified, tested in development | LOW |
| **Module conflicts** | VERY LOW | MEDIUM | No dependencies conflicts, clean install | LOW |
| **Data corruption** | VERY LOW | CRITICAL | Full backups, no destructive operations | LOW |
| **User disruption** | MEDIUM | LOW | Deploy during off-hours, communicate | LOW |

**Overall Risk Level:** **MEDIUM** ⚠️

**Risk Justification:**
- Changes affect payroll calculations directly
- All fixes tested thoroughly in development
- Complete rollback capability for all changes
- Zero past payslips affected (only future)

### 3.2 Impact Analysis

**Affected Systems:**
- ✅ HR Contracts (43 employees)
- ✅ Payroll Salary Rules (5 rules)
- ✅ Accounting Journal Entries (1 rule)
- ❌ Past Payslips (NOT affected - already finalized)
- ❌ Other modules (NO impact)

**Affected Users:**
- **Direct:** Payroll administrators (2-3 users)
- **Indirect:** All 43 employees (future payslips only)
- **Training Required:** 10-15 minutes

**Business Impact:**
- **Positive:** Payroll now matches spreadsheet exactly ($153.91 NET)
- **Positive:** Proper accounting with liability tracking
- **Positive:** Automated structure selection for Aguinaldos
- **Risk:** If calculations wrong, could over/underpay employees

### 3.3 Success Criteria

**Deployment is SUCCESSFUL if:**
1. ✅ All 43 contracts updated with correct values
2. ✅ Test payslip (NELCI) shows NET = $153.91
3. ✅ Deductions apply only to K component
4. ✅ Journal entries post to liability account
5. ✅ Module installed without errors
6. ✅ No errors in Odoo logs
7. ✅ All test payslips validate successfully

**Deployment FAILS if:**
1. ❌ Contract sync script errors
2. ❌ Payroll calculations incorrect
3. ❌ Journal entry posting fails
4. ❌ Critical errors in logs
5. ❌ Payslips don't match spreadsheet

---

## 4. Migration Steps

### 4.1 Phase 1: Database Employee Sync (30 min)

**Objective:** Update 43 employee contracts from Google Sheets

#### Step 1: Verify Google Sheets Access (5 min)

```bash
# On production server:
cd /tmp/scripts

# Test Google Sheets connection
python3 << 'EOF'
import gspread
from google.oauth2.service_account import Credentials

CREDENTIALS_FILE = '/var/www/dev/odoo_api_bridge/credentials/google_sheets_credentials.json'
SPREADSHEET_ID = '19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s'

scope = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet('31oct2025')
print(f"✓ Connected to: {spreadsheet.title}")
print(f"✓ Worksheet: {worksheet.title}")
print(f"✓ Rows: {worksheet.row_count}")
EOF
```

#### Step 2: Run Contract Sync (TEST MODE first) (10 min)

```bash
# Run in TEST mode (1 employee only)
cd /tmp/scripts
python3 update-contracts-from-spreadsheet-FIXED.py --test

# Review output:
# ✓ Should show ARCIDES ARZOLA update
# ✓ Verify wage, K, M, L values
# ✓ Check "Commit changes? (yes/no):" prompt

# Type "yes" to commit test update

# Verify test update in database
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    e.name,
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'ARCIDES ARZOLA';"

# ✓ VERIFY: Values match spreadsheet
```

#### Step 3: Run Contract Sync (PRODUCTION MODE) (15 min)

```bash
# Run in PRODUCTION mode (all 43 employees)
python3 update-contracts-from-spreadsheet-FIXED.py --production

# Review output:
# ✓ Should show all 43 employees
# ✓ Verify counts match
# ✓ Check for any mismatches

# Type "yes" to commit all updates

# Verify update counts
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) as updated_contracts
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE c.wage IS NOT NULL
  AND c.ueipab_salary_base IS NOT NULL
  AND c.state = 'open';"

# ✓ EXPECT: 43 contracts
```

---

### 4.2 Phase 2: Payroll Formula Fixes (30 min)

**Objective:** Apply 4 critical fixes to salary rules and accounts

#### Step 1: Fix Deduction Rules (Base = K only) (10 min)

```bash
cd /tmp/scripts

# Run fix script
python3 fix-deduction-rules.py

# Review changes:
# ✓ VE_SSO_DED: Apply to K only
# ✓ VE_FAOV_DED: Apply to K only
# ✓ VE_PARO_DED: Apply to K only
# ✓ VE_ARI_DED: Apply to K only (fixed rate: 0.5%)

# Type "yes" to commit changes

# Verify backup created
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) FROM salary_rules_backup_20251110_192020;"

# ✓ EXPECT: 4 rules backed up
```

#### Step 2: Match Spreadsheet Formula (10 min)

```bash
# Run formula tuning script
python3 fix-payroll-to-match-spreadsheet.py

# Review changes:
# ✓ SSO: 2.25% → 4.5% (DOUBLED)
# ✓ FAOV: 0.5% → 1% (DOUBLED)
# ✓ Paro: 0.125% → 0.25% (DOUBLED)
# ✓ ARI: 0.5% → 1% (DOUBLED)
# ✓ Cesta: $20 → $0 (REMOVED from bi-weekly)

# Review expected impact:
# NELCI BRITO (15 days):
#   Gross: $158.65
#   Deductions: $4.74
#   NET: $153.91 ✓ (matches spreadsheet!)

# Type "yes" to commit changes

# Verify backup created
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) FROM payroll_rules_backup_20251110_194011;"

# ✓ EXPECT: 5 rules backed up
```

#### Step 3: Configure Journal Entries (10 min)

```bash
# Run journal entry configuration script
printf "yes\n" | python3 configure-payroll-journal-entries.py

# Review configuration:
# ✓ VE_NET rule updated
# ✓ Debit: 5.1.01.10.001 (Nómina expense)
# ✓ Credit: 2.1.01.01.002 (Payable liability)

# Verify configuration
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    sr.code,
    sr.account_debit_id,
    sr.account_credit_id,
    d.code as debit_code,
    c.code as credit_code
FROM hr_salary_rule sr
LEFT JOIN account_account d ON d.id = sr.account_debit_id
LEFT JOIN account_account c ON c.id = sr.account_credit_id
WHERE sr.code = 'VE_NET';"

# ✓ EXPECT:
# VE_NET | 1009 | 1125 | 5.1.01.10.001 | 2.1.01.01.002
```

---

### 4.3 Phase 3: Module Deployment (30 min)

**Objective:** Install ueipab_payroll_enhancements module

#### Step 1: Extract Module (5 min)

```bash
# Copy module to addons directory
cd /opt/odoo/addons/
cp -r /tmp/addons/ueipab_payroll_enhancements ./

# Set permissions
chown -R odoo:odoo ueipab_payroll_enhancements/
chmod -R 755 ueipab_payroll_enhancements/

# Verify structure
ls -la ueipab_payroll_enhancements/
# ✓ EXPECT: __init__.py, __manifest__.py, models/, views/
```

#### Step 2: Update Module List (5 min)

```bash
# Update module list via Odoo shell
docker exec odoo-production odoo shell -d testing << 'EOF'
env['ir.module.module'].update_list()
print("✓ Module list updated")
env.cr.commit()
EOF

# Verify module appears
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';"

# ✓ EXPECT: ueipab_payroll_enhancements | uninstalled | 17.0.1.0.0
```

#### Step 3: Install Module (10 min)

```bash
# Install module via command line
docker exec odoo-production odoo -d testing \
    -i ueipab_payroll_enhancements \
    --stop-after-init

# Check installation status
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';"

# ✓ EXPECT: ueipab_payroll_enhancements | installed | 17.0.1.0.0

# Restart Odoo
docker restart odoo-production

# Wait for startup (30 seconds)
sleep 30

# Verify Odoo is running
docker logs odoo-production 2>&1 | tail -20 | grep -i "running\|ready"
```

#### Step 4: Clear Cache & Regenerate Assets (5 min)

```bash
# Via UI (recommended):
# 1. Login to Odoo as admin
# 2. Enable Developer Mode
# 3. Click bug icon (🐞)
# 4. Select "Regenerate Assets Bundles"

# Via command line (alternative):
docker exec odoo-production odoo -d testing \
    --stop-after-init \
    --update=ueipab_payroll_enhancements

# Restart again
docker restart odoo-production
sleep 30
```

---

### 4.4 Phase 4: Initial Validation (30 min)

**Objective:** Verify all changes before full testing

#### Step 1: Verify Contract Updates (5 min)

```bash
# Check NELCI BRITO contract
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    e.name,
    c.wage,
    c.ueipab_salary_base,
    c.ueipab_bonus_regular,
    c.ueipab_extra_bonus
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO'
  AND c.state = 'open';"

# ✓ EXPECT:
# NELCI BRITO | 317.29 | 140.36 | 176.94 | 0.00
```

#### Step 2: Verify Salary Rules (10 min)

```bash
# Check deduction formulas
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    code,
    amount_python_compute
FROM hr_salary_rule
WHERE code IN ('VE_SSO_DED', 'VE_FAOV_DED', 'VE_PARO_DED', 'VE_ARI_DED', 'VE_CESTA_TICKET')
ORDER BY code;"

# ✓ VERIFY each formula:
# - VE_SSO_DED: "salary_base * 0.045" (4.5%)
# - VE_FAOV_DED: "salary_base * 0.01" (1%)
# - VE_PARO_DED: "salary_base * 0.0025" (0.25%)
# - VE_ARI_DED: "salary_base * 0.01" (1%)
# - VE_CESTA_TICKET: "result = 0.0"
```

#### Step 3: Verify Journal Accounts (5 min)

```bash
# Check VE_NET rule accounts
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    sr.code,
    d.code as debit,
    c.code as credit
FROM hr_salary_rule sr
JOIN account_account d ON d.id = sr.account_debit_id
JOIN account_account c ON c.id = sr.account_credit_id
WHERE sr.code = 'VE_NET';"

# ✓ EXPECT:
# VE_NET | 5.1.01.10.001 | 2.1.01.01.002
```

#### Step 4: Verify Module Installation (10 min)

```bash
# Check module status
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT name, state, latest_version
FROM ir_module_module
WHERE name LIKE 'ueipab%'
ORDER BY name;"

# ✓ VERIFY:
# ueipab_payroll_enhancements | installed | 17.0.1.0.0

# Check for errors in logs
docker logs odoo-production 2>&1 | tail -100 | grep -i "error\|warning" | grep -i payroll

# ✓ EXPECT: No critical errors
```

---

## 5. Testing & Validation

### 5.1 Test Payslip: NELCI BRITO (Critical Test)

**This is the MOST IMPORTANT test - must match spreadsheet exactly!**

#### Step 1: Create Test Batch

```
1. Login to Odoo as admin or payroll user
2. Go to: Payroll → Batches
3. Click "Create"
4. Fill in:
   - Name: "TEST_NELCI_NOV_2025"
   - Date From: 2025-11-01
   - Date To: 2025-11-15
   - Payroll Journal: (select standard payroll journal)
5. Click "Save"
```

#### Step 2: Generate NELCI Payslip

```
1. Click "Generate Payslips" button
2. ✅ VERIFY: "Salary Structure" dropdown visible (new feature!)
3. Leave structure empty (use contract default)
4. Select only: NELCI BRITO
5. Click "Generate"
6. Click "Compute Sheet" on generated payslip
```

#### Step 3: Verify Payslip Amounts

```
Open NELCI BRITO payslip and verify:

Salary Details:
├─ VE_SALARY_70 (K × 50%):  $70.18  ✓
├─ VE_BONUS_25 (M × 50%):   $88.47  ✓
├─ VE_EXTRA_5 (L × 50%):    $0.00   ✓
├─ VE_CESTA_TICKET:         $0.00   ✓ (removed from bi-weekly)
└─ TOTAL GROSS:             $158.65 ✓

Deductions (on K only):
├─ VE_SSO_DED (4.5%):       $3.16   ✓ (70.18 × 0.045)
├─ VE_FAOV_DED (1%):        $0.70   ✓ (70.18 × 0.01)
├─ VE_PARO_DED (0.25%):     $0.18   ✓ (70.18 × 0.0025)
├─ VE_ARI_DED (1%):         $0.70   ✓ (70.18 × 0.01)
└─ TOTAL DEDUCTIONS:        $4.74   ✓

NET SALARY:                 $153.91 ✓✓✓

SPREADSHEET COLUMN Y:       $153.91 ✓✓✓
DIFFERENCE:                 $0.00   🎯 PERFECT MATCH!
```

**⚠️ CRITICAL: If NET ≠ $153.91, STOP and investigate!**

#### Step 4: Verify Journal Entry

```
1. Click "Create Draft Entry" or post the payslip
2. Go to: Accounting → Journal Entries
3. Find the entry for NELCI BRITO
4. Verify accounts:
   ✓ Debit:  5.1.01.10.001 (Nómina)      $153.91
   ✓ Credit: 2.1.01.01.002 (Payable)     $153.91
   ✓ NO direct bank posting
```

---

### 5.2 Mass Test: 5 Random Employees

**Test with diverse employee profiles:**

```
1. Create new batch: "MASS_TEST_NOV_2025"
2. Dates: 2025-11-01 to 2025-11-15
3. Generate payslips for:
   - ARCIDES ARZOLA (first employee)
   - NORKA VILLASMIL (mid-range)
   - NELCI BRITO (reference)
   - GABRIEL ESPAÑA (has Ñ character)
   - LUIS RODRIGUEZ (last employee)
4. Compute all 5 payslips
5. Compare each NET to spreadsheet Column Y
6. ✓ VERIFY: All match within $0.50 (rounding tolerance)
```

---

### 5.3 Module Feature Test

**Test new structure selector:**

```
1. Create batch: "AGUINALDOS_TEST_2025"
2. Click "Generate Payslips"
3. ✅ VERIFY: AGUINALDOS_2025 structure pre-selected automatically
4. ✅ VERIFY: Green alert shows "Structure Override Active"
5. ✅ VERIFY: Can manually change structure
6. ✅ VERIFY: Can clear structure (backward compatibility)
7. Cancel wizard (don't generate yet)
```

---

### 5.4 Accounting Integration Test

**Verify full payroll-to-payment flow:**

```
1. Generate 1-2 real payslips
2. Post payslips
3. Go to Accounting → Journal Entries
4. ✅ VERIFY: Entries show correct accounts
5. Check Balance Sheet:
   ✅ Liability 2.1.01.01.002 shows payable amount
   ✅ Bank 1.1.01.02.001 unchanged (not paid yet)
6. Create payment entry (optional):
   Dr. 2.1.01.01.002 (Payable)
   Cr. 1.1.01.02.001 (Bank)
7. ✅ VERIFY: Liability cleared, bank reduced
```

---

### 5.5 Acceptance Criteria

**Deployment is SUCCESSFUL if ALL are ✅:**

#### Contract Sync:
- [ ] All 43 contracts updated
- [ ] NELCI wage = $317.29
- [ ] All K, M, L values match spreadsheet
- [ ] No employees with NULL values

#### Payroll Formulas:
- [ ] NELCI NET = $153.91 (exact match)
- [ ] Deductions apply to K only
- [ ] Cesta = $0 in bi-weekly payslips
- [ ] All deduction rates doubled

#### Journal Entries:
- [ ] VE_NET posts to liability account
- [ ] Debit: 5.1.01.10.001
- [ ] Credit: 2.1.01.01.002
- [ ] No direct bank posting

#### Module:
- [ ] Module installed successfully
- [ ] Structure selector visible
- [ ] Aguinaldos auto-detection works
- [ ] Backward compatible (empty = default)

#### Testing:
- [ ] NELCI payslip validated
- [ ] 5 random employees validated
- [ ] All match spreadsheet
- [ ] No errors in logs

---

## 6. Rollback Procedures

### 6.1 Rollback Decision Criteria

**Trigger IMMEDIATE rollback if:**
- ❌ NELCI NET ≠ $153.91 (calculation error)
- ❌ Contract sync fails or corrupts data
- ❌ Journal entries post to wrong accounts
- ❌ Critical errors in Odoo logs
- ❌ Payslip validation fails
- ❌ Any data corruption detected

### 6.2 Rollback Steps (Execute in Order)

#### Step 1: Rollback Journal Entries (5 min)

```bash
docker exec odoo-production-db psql -U odoo -d testing << 'EOF'
-- Restore VE_NET accounts
UPDATE hr_salary_rule r SET
    account_debit_id = b.account_debit_id,
    account_credit_id = b.account_credit_id
FROM salary_rule_accounts_backup_20251110_200030 b
WHERE r.id = b.id;
EOF

# Verify rollback
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT code, account_debit_id, account_credit_id
FROM hr_salary_rule WHERE code = 'VE_NET';"
```

#### Step 2: Rollback Payroll Formulas (5 min)

```bash
docker exec odoo-production-db psql -U odoo -d testing << 'EOF'
-- Restore formula tuning
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
FROM payroll_rules_backup_20251110_194011 b
WHERE r.id = b.id;

-- Restore deduction base
UPDATE hr_salary_rule r SET
    amount_python_compute = b.amount_python_compute
FROM salary_rules_backup_20251110_192020 b
WHERE r.id = b.id;
EOF

# Verify rollback
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT code, amount_python_compute
FROM hr_salary_rule
WHERE code IN ('VE_SSO_DED', 'VE_CESTA_TICKET');"
```

#### Step 3: Rollback Contract Updates (10 min)

```bash
docker exec odoo-production-db psql -U odoo -d testing << 'EOF'
-- Restore contracts
UPDATE hr_contract c SET
    wage = b.wage,
    ueipab_salary_base = b.ueipab_salary_base,
    ueipab_bonus_regular = b.ueipab_bonus_regular,
    ueipab_extra_bonus = b.ueipab_extra_bonus
FROM contract_salary_backup_20251110_190655 b
WHERE c.id = b.id;
EOF

# Verify rollback
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT
    e.name, c.wage
FROM hr_contract c
JOIN hr_employee e ON e.id = c.employee_id
WHERE e.name = 'NELCI BRITO';"
```

#### Step 4: Uninstall Module (10 min)

```bash
# Uninstall via Odoo shell
docker exec odoo-production odoo shell -d testing << 'EOF'
module = env['ir.module.module'].search([
    ('name', '=', 'ueipab_payroll_enhancements')
])
if module:
    module.button_immediate_uninstall()
    env.cr.commit()
    print("✓ Module uninstalled")
else:
    print("⚠️ Module not found")
EOF

# Remove module files
rm -rf /opt/odoo/addons/ueipab_payroll_enhancements

# Restart Odoo
docker restart odoo-production
```

#### Step 5: Verify Rollback Complete (10 min)

```bash
# 1. Check contracts restored
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT COUNT(*) FROM contract_salary_backup_20251110_190655;"

# 2. Check salary rules restored
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT code, amount_python_compute
FROM hr_salary_rule WHERE code = 'VE_SSO_DED';"

# 3. Check module removed
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT name, state FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';"

# 4. Test payslip generation
# (Via UI - create test batch and verify old behavior)
```

### 6.3 Full Database Restore (EXTREME CASE)

**ONLY if above rollbacks fail:**

```bash
# 1. Stop Odoo
docker stop odoo-production

# 2. Drop database
docker exec odoo-production-db psql -U postgres << EOF
DROP DATABASE testing;
CREATE DATABASE testing;
\q
EOF

# 3. Restore from backup
docker exec -i odoo-production-db pg_restore -U odoo -d testing \
    < /backups/testing_pre_migration_*.dump

# 4. Restart Odoo
docker start odoo-production

# 5. Wait for startup
sleep 60

# 6. Verify restoration
docker logs odoo-production 2>&1 | tail -50
```

---

## 7. Post-Migration Actions

### 7.1 Immediate Actions (First Hour)

#### Monitoring

```bash
# Watch logs for errors
docker logs -f odoo-production 2>&1 | grep -i "error\|payroll"

# Check server resources
docker stats odoo-production

# Monitor database connections
docker exec odoo-production-db psql -U odoo -d testing -c "
SELECT count(*) FROM pg_stat_activity WHERE datname = 'testing';"
```

#### Verification

```bash
# Verify all fixes still in place
docker exec odoo-production-db psql -U odoo -d testing << 'EOF'
-- 1. Check contracts
SELECT COUNT(*) FROM hr_contract
WHERE wage IS NOT NULL AND state = 'open';

-- 2. Check salary rules
SELECT COUNT(*) FROM hr_salary_rule
WHERE code LIKE 'VE_%' AND amount_python_compute LIKE '%0.045%';

-- 3. Check journal accounts
SELECT code, account_debit_id, account_credit_id
FROM hr_salary_rule WHERE code = 'VE_NET';

-- 4. Check module
SELECT name, state FROM ir_module_module
WHERE name = 'ueipab_payroll_enhancements';
EOF
```

### 7.2 Communication

**Email to Payroll Team:**

```
Subject: Payroll System Updates Deployed - Action Required

Dear Payroll Team,

The following critical updates have been deployed to production:

1. Employee Contracts Updated (43 employees)
   - All salary components now match Google Sheets
   - Future payslips will use correct values

2. Payroll Formulas Fixed
   - NET salary now matches spreadsheet exactly
   - NELCI BRITO example: $153.91 bi-weekly ✓

3. Accounting Configuration
   - NET salary posts to liability account
   - Enables proper tracking before payment

4. New Feature: Structure Selector
   - Batch generation now has structure dropdown
   - Aguinaldos batches auto-select correct structure

IMPORTANT - Next Steps:
1. Do NOT generate new payslips until testing complete
2. Wait for confirmation email before proceeding
3. Training session scheduled: [Date/Time]

For questions or issues, contact: [Technical Support]

Status: All changes deployed successfully
Date: [Current Date]
```

### 7.3 Documentation

```bash
# Create deployment record
cat > /backups/deployment_log_$(date +%Y%m%d_%H%M%S).txt << EOF
===============================================
PRODUCTION DEPLOYMENT LOG
===============================================

Date: $(date)
Deployed By: [Your Name]
Server: 10.124.0.3
Database: testing

Components Deployed:
1. Database Employee Sync - 43 contracts
2. Payroll Formula Fixes - 4 critical bugs
3. Module Deployment - ueipab_payroll_enhancements

Status: SUCCESS

Verification:
- NELCI BRITO NET: $153.91 ✓
- Contracts synced: 43 ✓
- Module installed: ✓
- No errors in logs: ✓

Backups Created:
- Database: testing_pre_migration_YYYYMMDD_HHMMSS.dump
- Contracts: contract_salary_backup_20251110_190655
- Salary Rules: salary_rules_backup_20251110_192020
- Payroll Rules: payroll_rules_backup_20251110_194011
- Journal Accounts: salary_rule_accounts_backup_20251110_200030

Rollback Available: YES
Rollback Tested: YES

Notes:
[Any additional notes or observations]

===============================================
EOF
```

### 7.4 Monitoring Schedule

**First 24 Hours:**
- [ ] Hour 1: Check logs every 15 minutes
- [ ] Hour 2-4: Check logs hourly
- [ ] Hour 5-24: Check logs every 4 hours

**First Week:**
- [ ] Daily log review
- [ ] Daily test payslip generation
- [ ] Monitor user feedback
- [ ] Check performance metrics

**First Month:**
- [ ] Weekly verification
- [ ] Monthly payroll run monitoring
- [ ] User satisfaction survey

---

## 8. Approval Checklist

### 8.1 Technical Approval

**Reviewed and Approved By:**

```
Name: _______________________
Title: Technical Lead
Date: _______________________
Signature: __________________

Verification:
[ ] All scripts tested in development
[ ] Backups verified and tested
[ ] Rollback procedures documented
[ ] Test results reviewed (NELCI = $153.91)
[ ] No conflicts with existing modules
```

### 8.2 Business Approval

**Reviewed and Approved By:**

```
Name: _______________________
Title: Payroll Manager / HR Director
Date: _______________________
Signature: __________________

Verification:
[ ] Payroll calculations verified
[ ] Spreadsheet formula match confirmed
[ ] User training plan approved
[ ] Communication plan approved
[ ] Migration timing acceptable
```

### 8.3 Final Approval

**Reviewed and Approved By:**

```
Name: _______________________
Title: IT Director / CTO
Date: _______________________
Signature: __________________

Verification:
[ ] Risk assessment reviewed
[ ] Backup strategy approved
[ ] Rollback plan verified
[ ] Business continuity ensured
[ ] Authorization granted
```

### 8.4 Go/No-Go Decision

**Deployment Authorization:**

**Date:** _______________________
**Decision:** ⬜ GO / ⬜ NO-GO

**If NO-GO:**
- Reason: _________________________________
- Issues to Resolve: _______________________
- Rescheduled Date: ________________________

**If GO:**
- Deployment Window: _______________________
- Technical Staff: __________________________
- Backup Verified: __________________________
- Communication Sent: _______________________

---

## 9. Appendices

### Appendix A: Quick Reference

**NELCI BRITO Expected Values:**
```
Contract:
- wage: $317.29
- K (ueipab_salary_base): $140.36
- M (ueipab_bonus_regular): $176.94
- L (ueipab_extra_bonus): $0.00

Bi-Weekly Payslip (15 days):
- Gross: $158.65
- Deductions: $4.74
- NET: $153.91 ✓ (must match!)

Journal Entry:
- Dr. 5.1.01.10.001: $153.91
- Cr. 2.1.01.01.002: $153.91
```

### Appendix B: Script Locations

**All scripts in:** `/tmp/scripts/`
- `update-contracts-from-spreadsheet-FIXED.py`
- `fix-deduction-rules.py`
- `fix-payroll-to-match-spreadsheet.py`
- `configure-payroll-journal-entries.py`

**Module location:** `/opt/odoo/addons/ueipab_payroll_enhancements/`

### Appendix C: Backup Locations

**All backups in:** `/backups/`
- `testing_pre_migration_YYYYMMDD_HHMMSS.dump`
- `contracts_before_sync_YYYYMMDD.csv`
- `salary_rules_before_YYYYMMDD.csv`
- `addons_backup_YYYYMMDD.tar.gz`
- `odoo.conf.YYYYMMDD`

**Database backup tables:**
- `contract_salary_backup_20251110_190655`
- `salary_rules_backup_20251110_192020`
- `payroll_rules_backup_20251110_194011`
- `salary_rule_accounts_backup_20251110_200030`

### Appendix D: Support Contacts

| Role | Name | Contact | Availability |
|------|------|---------|--------------|
| Technical Lead | [Name] | [Email/Phone] | 24/7 during deployment |
| Database Admin | [Name] | [Email/Phone] | On-call |
| Payroll Manager | [Name] | [Email/Phone] | Business hours |
| HR Director | [Name] | [Email/Phone] | Emergency only |

### Appendix E: Reference Documentation

**Created Documentation:**
- `PAYROLL_SYSTEM_COMPLETE.md` - Master reference
- `FINAL_PAYROLL_FIX.md` - Formula fix details
- `JOURNAL_ENTRIES_CONFIGURED.md` - Accounting setup
- `CONTRACT_UPDATE_COMPLETED.md` - Sync details
- `PAYROLL_FIXES_COMPLETE.md` - All fixes summary

**External References:**
- Odoo 17 Payroll Documentation
- Google Sheets API Documentation
- PostgreSQL Backup/Restore Guide

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-09 | Technical Team | Initial draft (Aguinaldos only) |
| 2.0 | 2025-11-10 | Technical Team | Added contract sync |
| **3.0** | **2025-11-10** | **Technical Team** | **Complete migration: sync + fixes + module** |

---

## Summary Checklist

**Before Deployment:**
- [ ] Production environment assessed
- [ ] All backups created and verified
- [ ] Scripts and module transferred
- [ ] Google Sheets access verified
- [ ] All approvals obtained

**During Deployment:**
- [ ] Phase 1: Database sync (43 contracts)
- [ ] Phase 2: Payroll fixes (4 bugs)
- [ ] Phase 3: Module deployment
- [ ] Phase 4: Initial validation

**After Deployment:**
- [ ] NELCI payslip = $153.91 ✓
- [ ] 5 random employees tested ✓
- [ ] Module features tested ✓
- [ ] No errors in logs ✓
- [ ] Payroll team notified ✓

**If Issues:**
- [ ] Rollback procedures ready
- [ ] Backups accessible
- [ ] Support team available

---

**STATUS:** 🟢 READY FOR DEPLOYMENT

**Recommended Deployment Window:**
- **Date:** [Select date]
- **Time:** Evening or weekend (off-peak)
- **Duration:** 2-3 hours (includes testing)
- **Technical Staff:** On-site or on-call

---

**END OF DOCUMENT**
