# REVISED DEPLOYMENT PLAN - DUAL SYSTEM IMPLEMENTATION
## Following Proper Development Workflow

**CRITICAL PRINCIPLE:** Nothing gets deployed to 10.124.0.3 (production-acceptance) until 100% tested locally

---

## ENVIRONMENT OVERVIEW

### Environment 1: Local Development (/opt/odoo-dev)
- **Purpose:** Development and testing
- **Database:** localhost:5433 (odoo-dev-postgres container)
- **Database Name:** odoo17
- **Use Case:** All development, testing, validation, and debugging

### Environment 2: Production-Acceptance (10.124.0.3)
- **Purpose:** Production-acceptance testing
- **Database:** 10.124.0.3:5432 (ueipab17_postgres_1 container)
- **Database Name:** testing
- **Use Case:** Final deployment ONLY after 100% local validation

---

## PHASE 1: LOCAL DEVELOPMENT & TESTING
### **Status: NOT STARTED - Awaiting Approval**

### 1.1 Local Database Schema Changes
**Action:** Add dual system fields to local hr_contract table

```bash
# Connect to local database
docker exec -it odoo-dev-postgres psql -U odoo -d odoo17

# Run schema changes
\i /opt/odoo-dev/scripts/sql/add-monthly-salary-tracking-fields.sql
```

**Verification:**
```sql
-- Verify columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'hr_contract'
  AND column_name IN ('ueipab_monthly_salary', 'ueipab_salary_notes');
```

**Expected Result:** 2 new columns visible

---

### 1.2 Local Test Sync (1 Employee)
**Action:** Test sync script with single employee

```bash
cd /opt/odoo-dev/scripts
python3 sync-monthly-salary-from-spreadsheet.py --test
```

**Validation Checklist:**
- [ ] Script connects to Google Sheets successfully
- [ ] Exchange rate reads correctly from cell O2 (219.87)
- [ ] Employee data parsed correctly from Column K
- [ ] Enhanced notes format includes: sheet name, column, VEB amount, exchange rate
- [ ] Backup table created successfully
- [ ] Single employee contract updated
- [ ] Values match spreadsheet exactly
- [ ] No errors in transaction

**Example Expected Output:**
```
✓ ARCIDES ARZOLA                   $  285.44
  Notes: From payroll sheet 31oct2025, Column K (62,748.90 VEB) @ 219.87 VEB/USD
```

**Manual Verification Query:**
```sql
SELECT
    e.name,
    c.ueipab_monthly_salary,
    c.ueipab_salary_notes,
    c.ueipab_salary_base,  -- Existing field (should be UNCHANGED)
    c.ueipab_bonus_regular, -- Existing field (should be UNCHANGED)
    c.ueipab_extra_bonus    -- Existing field (should be UNCHANGED)
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
  AND c.ueipab_monthly_salary IS NOT NULL
LIMIT 3;
```

**Critical Validation:** Existing fields (ueipab_salary_base, ueipab_bonus_regular, ueipab_extra_bonus) must remain UNCHANGED

---

### 1.3 Local Full Sync (All 45 Employees)
**Action:** After successful test, sync all employees

```bash
python3 sync-monthly-salary-from-spreadsheet.py --production
# Script will prompt: Type 'YES' to confirm
```

**Validation Checklist:**
- [ ] All 45 employees processed successfully
- [ ] Total monthly salary = $12,753.41 (matches spreadsheet analysis)
- [ ] All notes have enhanced format
- [ ] No employees missing
- [ ] Backup table created
- [ ] Transaction committed successfully

**Verification Query:**
```sql
SELECT
    COUNT(*) as total_employees,
    SUM(ueipab_monthly_salary) as total_monthly,
    SUM(ueipab_monthly_salary) * 2 as total_aguinaldos
FROM hr_contract
WHERE state = 'open'
  AND ueipab_monthly_salary IS NOT NULL;
```

**Expected Result:**
- total_employees: 45
- total_monthly: $12,753.41
- total_aguinaldos: $25,506.82

---

### 1.4 Local Aguinaldos Salary Structure Creation
**Action:** Create Aguinaldos salary structure in local Odoo

#### Option A: Create via Odoo UI
1. Navigate to: Payroll → Configuration → Salary Structures
2. Create new structure:
   - **Name:** Aguinaldos Diciembre 2025
   - **Code:** AGUINALDOS_2025
   - **Type:** Worker
   - **Country:** Venezuela (if applicable)

3. Add Salary Rule:
   - **Name:** Aguinaldos (Christmas Bonus)
   - **Code:** AGUINALDOS
   - **Category:** Gross (or create new "Bonuses" category)
   - **Amount Type:** Python Code
   - **Python Code:**
   ```python
   # Calculate 2x monthly salary from spreadsheet
   result = contract.ueipab_monthly_salary * 2 if contract.ueipab_monthly_salary else 0
   ```
   - **Condition:** Always True
   ```python
   result = True
   ```

#### Option B: Create via SQL (faster for testing)
```sql
-- Insert salary structure
INSERT INTO hr_payroll_structure (name, code, country_id, type_id, active, create_date, write_date)
VALUES ('Aguinaldos Diciembre 2025', 'AGUINALDOS_2025', NULL,
        (SELECT id FROM hr_payroll_structure_type WHERE code = 'worker' LIMIT 1),
        TRUE, NOW(), NOW())
RETURNING id;
-- Note the returned ID

-- Insert salary rule (replace <structure_id> with actual ID)
INSERT INTO hr_salary_rule (
    name, code, sequence, category_id, struct_id,
    active, amount_select, amount_python_compute, condition_select, condition_python,
    create_date, write_date
)
VALUES (
    'Aguinaldos (Christmas Bonus)',
    'AGUINALDOS',
    100,
    (SELECT id FROM hr_salary_rule_category WHERE code = 'GROSS' LIMIT 1),
    <structure_id>,  -- Replace with actual structure ID
    TRUE,
    'code',
    'result = contract.ueipab_monthly_salary * 2 if contract.ueipab_monthly_salary else 0',
    'python',
    'result = True',
    NOW(),
    NOW()
);
```

**Validation:** Verify structure appears in Odoo UI

---

### 1.5 Local Test Payslip Generation
**Action:** Generate test payslip for sample employee

**Steps:**
1. Navigate to: Payroll → Payslips
2. Create new payslip:
   - **Employee:** Select test employee (e.g., ARCIDES ARZOLA)
   - **Structure:** Aguinaldos Diciembre 2025
   - **Period:** December 2025
   - **Date From:** 2025-12-01
   - **Date To:** 2025-12-31

3. Click "Compute Sheet"

**Expected Result for ARCIDES ARZOLA:**
- Contract: ueipab_monthly_salary = $285.44
- Rule AGUINALDOS: $285.44 × 2 = **$570.88**

**Validation Checklist:**
- [ ] Payslip computes without errors
- [ ] AGUINALDOS rule appears in slip
- [ ] Amount = ueipab_monthly_salary × 2
- [ ] Amount matches spreadsheet (Column K × 2)
- [ ] No other salary rules interfere
- [ ] Gross total = Aguinaldos amount

**Manual Calculation Verification:**
```sql
SELECT
    e.name,
    c.ueipab_monthly_salary as monthly_salary,
    c.ueipab_monthly_salary * 2 as expected_aguinaldos,
    c.ueipab_salary_notes as source_notes
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE e.name = 'ARCIDES ARZOLA'
  AND c.state = 'open';
```

---

### 1.6 Local Full Validation
**Action:** Generate payslips for multiple employees and validate

**Test Sample (5-10 employees):**
- Generate payslips for diverse salary ranges
- Verify calculations match spreadsheet
- Check for any edge cases or errors

**Validation Queries:**
```sql
-- Summary of expected Aguinaldos by employee
SELECT
    e.name,
    c.ueipab_monthly_salary as monthly,
    c.ueipab_monthly_salary * 2 as aguinaldos,
    c.ueipab_salary_notes as source
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
  AND c.ueipab_monthly_salary IS NOT NULL
ORDER BY c.ueipab_monthly_salary DESC
LIMIT 10;

-- Total Aguinaldos across all employees
SELECT
    COUNT(*) as total_employees,
    SUM(ueipab_monthly_salary * 2) as total_aguinaldos,
    MIN(ueipab_monthly_salary * 2) as min_aguinaldos,
    MAX(ueipab_monthly_salary * 2) as max_aguinaldos,
    AVG(ueipab_monthly_salary * 2) as avg_aguinaldos
FROM hr_contract
WHERE state = 'open'
  AND ueipab_monthly_salary IS NOT NULL;
```

**Expected Totals:**
- Total employees: 45
- Total Aguinaldos: $25,506.82
- Min: ~$264 (lowest salary × 2)
- Max: ~$800 (highest salary × 2)

---

### 1.7 Local Regression Testing
**Action:** Verify existing payroll structures still work correctly

**Critical Test:** Generate regular bi-monthly payslip to ensure no interference

**Steps:**
1. Create new payslip with existing UEIPAB Venezuelan Payroll structure
2. Select October period (or current period)
3. Compute sheet

**Validation Checklist:**
- [ ] Existing salary rules still work (VE_SALARY_70, VE_BONUS_25, VE_EXTRA_5)
- [ ] Rules still use existing custom fields (NOT new ueipab_monthly_salary)
- [ ] Calculations match previous payslips
- [ ] No errors or warnings
- [ ] New fields don't interfere with existing rules

**Verification Query:**
```sql
-- Compare existing field usage
SELECT
    e.name,
    c.ueipab_salary_base as base_70_field,
    c.ueipab_bonus_regular as bonus_25_field,
    c.ueipab_extra_bonus as extra_5_field,
    (c.ueipab_salary_base + c.ueipab_bonus_regular + c.ueipab_extra_bonus) as total_existing,
    c.ueipab_monthly_salary as new_tracking_field
FROM hr_contract c
JOIN hr_employee e ON c.employee_id = e.id
WHERE c.state = 'open'
LIMIT 5;
```

---

### PHASE 1 GATE: 100% Validation Required
**Before proceeding to Phase 2, ALL of the following must be TRUE:**

- [x] Database schema changes applied successfully locally
- [x] Test sync (1 employee) completed with correct values
- [x] Full sync (45 employees) completed successfully
- [x] Total monthly salary = $12,753.41 exactly
- [x] All enhanced notes formatted correctly with exchange rate
- [x] Aguinaldos salary structure created in local Odoo
- [x] Test payslips generate correctly with 2x multiplier
- [x] Sample calculations match spreadsheet exactly
- [x] Existing payroll structures still work (regression test passed)
- [x] No errors, no data corruption, no interference
- [x] Backup tables created for all operations
- [x] All documentation updated with any findings

**Sign-off Required:** User must explicitly approve before Phase 2

---

## PHASE 2: PRODUCTION-ACCEPTANCE DEPLOYMENT
### **Status: NOT STARTED - Requires Phase 1 Completion**

### 2.1 Production-Acceptance Database Schema
**Action:** Apply schema changes to 10.124.0.3

**Connection:**
```bash
sshpass -p 'g)9nE>?rq-#v3Hn' ssh root@10.124.0.3
docker exec -it ueipab17_postgres_1 psql -U odoo -d testing
```

**Execute:**
```sql
-- Copy-paste contents of add-monthly-salary-tracking-fields.sql
-- OR transfer file and run \i command
```

**Verification:**
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'hr_contract'
  AND column_name IN ('ueipab_monthly_salary', 'ueipab_salary_notes');
```

---

### 2.2 Production-Acceptance Test Sync
**Action:** Run sync script against production database (test mode)

**Update Script Configuration:**
Before running, verify `sync-monthly-salary-from-spreadsheet.py` has correct db_config:
```python
self.db_config = {
    'host': '10.124.0.3',
    'port': 5432,
    'database': 'testing',
    'user': 'odoo',
    'password': 'odoo'
}
```

**Execute:**
```bash
python3 sync-monthly-salary-from-spreadsheet.py --test
```

**Validation:** Same checklist as 1.2, verify results match local environment

---

### 2.3 Production-Acceptance Full Sync
**Action:** Sync all 45 employees

```bash
python3 sync-monthly-salary-from-spreadsheet.py --production
# Type 'YES' to confirm
```

**Validation:** Same checklist as 1.3, verify totals match exactly

---

### 2.4 Production-Acceptance Salary Structure
**Action:** Create Aguinaldos structure in production Odoo

**Access Production Odoo:**
- URL: http://10.124.0.3:8069 (or actual production URL)
- Follow same steps as 1.4

**Validation:** Structure visible and configured identically to local

---

### 2.5 Production-Acceptance Test Payslips
**Action:** Generate test payslips for validation

**Steps:**
1. Generate payslip for same test employee used locally
2. Verify amount matches local test exactly
3. Generate 2-3 additional samples
4. Compare all results to local environment

**Critical:** Results must be IDENTICAL to local testing

---

### 2.6 Production-Acceptance Final Validation
**Action:** Full system check before live deployment

**Validation Checklist:**
- [ ] All 45 employees have ueipab_monthly_salary populated
- [ ] Total = $12,753.41 (matches spreadsheet and local)
- [ ] All notes have enhanced format with exchange rate
- [ ] Test payslips match local results exactly
- [ ] Existing payroll structures unaffected (regression test)
- [ ] No errors in logs
- [ ] Backup tables exist for rollback if needed

**Final Verification Query:**
```sql
SELECT
    'Deployment Validation Summary' as check_type,
    COUNT(*) as total_employees,
    SUM(ueipab_monthly_salary) as total_monthly,
    SUM(ueipab_monthly_salary) * 2 as total_aguinaldos,
    MIN(ueipab_monthly_salary) as min_salary,
    MAX(ueipab_monthly_salary) as max_salary
FROM hr_contract
WHERE state = 'open'
  AND ueipab_monthly_salary IS NOT NULL;
```

**Expected:**
- total_employees: 45
- total_monthly: 12753.41
- total_aguinaldos: 25506.82

---

## PHASE 3: DECEMBER PAYROLL EXECUTION
### **Status: NOT STARTED - Requires Phase 2 Completion**

### 3.1 Generate December Aguinaldos Payslips
**Action:** Create payslips for all 45 employees

**Recommended Approach:** Use Odoo batch processing
1. Navigate to: Payroll → Payslips → Create Batch
2. Configuration:
   - **Structure:** Aguinaldos Diciembre 2025
   - **Period:** December 2025 (01/12/2025 - 31/12/2025)
   - **Employees:** Select all 45 employees (or use employee tag filter)

3. Click "Generate Payslips"
4. Review all generated payslips
5. Click "Compute All"

**Validation Before Confirmation:**
- [ ] All 45 payslips generated
- [ ] Each payslip shows correct AGUINALDOS amount
- [ ] Total gross = $25,506.82
- [ ] No errors or warnings
- [ ] All employees accounted for

---

### 3.2 Review and Confirm
**Action:** Final review before marking payslips as "Done"

**Steps:**
1. Export payslip summary for review
2. Compare to spreadsheet one final time
3. Get user approval
4. Mark payslips as "Done"
5. Process payments according to company procedure

---

## ROLLBACK PROCEDURES

### If Issues Found in Phase 1 (Local)
**Action:** Simply rollback or debug locally
- Drop backup table when done
- No impact to production

### If Issues Found in Phase 2 (Production-Acceptance)
**Action:** Restore from backup table

```sql
-- Restore original values
UPDATE hr_contract c
SET
    ueipab_monthly_salary = b.ueipab_monthly_salary,
    ueipab_salary_notes = b.ueipab_salary_notes
FROM contract_monthly_salary_backup_YYYYMMDD_HHMMSS b
WHERE c.id = b.id;

-- Verify restoration
SELECT COUNT(*) FROM hr_contract
WHERE ueipab_monthly_salary IS NOT NULL;
```

### If Issues Found in Phase 3 (Payslips)
**Action:** Delete draft payslips, fix issue, regenerate

```sql
-- Only if payslips are in draft state
DELETE FROM hr_payslip
WHERE struct_id = (SELECT id FROM hr_payroll_structure WHERE code = 'AGUINALDOS_2025')
  AND state = 'draft';
```

**Note:** NEVER delete payslips in 'done' or 'paid' state

---

## TIMELINE ESTIMATE

### Phase 1 (Local Testing): 2-4 hours
- Schema changes: 15 min
- Test sync: 30 min
- Full sync: 15 min
- Structure creation: 30 min
- Test payslips: 1 hour
- Full validation: 1-2 hours

### Phase 2 (Production Deployment): 1-2 hours
- Schema changes: 15 min
- Test sync: 15 min
- Full sync: 15 min
- Structure creation: 15 min
- Test payslips: 30 min
- Validation: 30 min

### Phase 3 (Payroll Execution): 1 hour
- Batch generation: 15 min
- Review: 30 min
- Confirmation: 15 min

**Total Estimated Time:** 4-7 hours across all phases

---

## SUCCESS CRITERIA

### Phase 1 Success:
✓ All 45 employees synced locally
✓ Total = $12,753.41
✓ Test payslips calculate correctly
✓ No interference with existing payroll
✓ User approval obtained

### Phase 2 Success:
✓ Production data matches local exactly
✓ All validation checks pass
✓ Test payslips identical to local
✓ System stable and functional

### Phase 3 Success:
✓ All 45 Aguinaldos payslips generated
✓ Total = $25,506.82
✓ Payments processed successfully
✓ Employees receive correct bonuses

---

## NOTES

1. **Never skip Phase 1** - All testing must happen locally first
2. **Gate between phases** - User must explicitly approve moving from Phase 1 to Phase 2
3. **Backup everything** - Scripts create automatic backups, but verify they exist
4. **Document issues** - Any problems found during testing must be documented and resolved
5. **Compare results** - Production must match local results exactly
6. **Keep spreadsheet** - Original spreadsheet is source of truth for validation

---

**READY TO BEGIN PHASE 1 PENDING USER APPROVAL**
