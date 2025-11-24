# Employee Contract Migration Plan - Production Deployment

**Date:** November 24, 2025
**Status:** 🔴 CRITICAL - Contract Creation Required Before Payroll Operations
**Target:** DB_UEIPAB (Production Database)

---

## 🚨 Critical Situation

**Production Current State:**
- ✅ **50 employees** in system
- ❌ **48 employees WITHOUT contracts** (96% of workforce)
- ⚠️ **2 employees WITH contracts:**
  - 1 cancelled contract (YOSMARI DEL CARMEN GONZÁLEZ ROMERO)
  - 1 draft contract (ALEJANDRA LOPEZ)

**Testing Comparison:**
- ✅ **49 employees** in system
- ✅ **48 active contracts** (98% coverage)
- ✅ All V2 salary fields populated

**Impact:** **CANNOT RUN PAYROLL WITHOUT ACTIVE CONTRACTS**

---

## 📋 Executive Summary

**The Problem:**
Production has employees but no active contracts. Without contracts, the payroll system cannot:
- Generate payslips
- Calculate salaries
- Process deductions
- Create accounting entries

**The Solution:**
Create contracts for all 50 employees after module deployment, with two options:

1. **OPTION A: Manual Creation (RECOMMENDED for <10 employees)**
   - Time: 5-10 minutes per employee
   - Accuracy: High (manual verification)
   - Suitable for: Initial setup, executive team, test phase

2. **OPTION B: Bulk Import (RECOMMENDED for all 50 employees)**
   - Time: 2-3 hours preparation + 10 minutes import
   - Accuracy: Depends on source data quality
   - Suitable for: Full workforce deployment

**Recommended Approach:** **PHASED DEPLOYMENT**
- Phase 1: Manual creation for 5-10 test employees (validate system)
- Phase 2: Bulk import for remaining 40-45 employees (after validation)

---

## 🎯 Contract Data Required

### Essential Fields (Minimum Viable Contract)

```
Employee Information:
  - Employee: [Select from existing 50 employees]
  - Start Date: Contract start date (e.g., 2024-01-01)
  - Wage: Total monthly wage (for accounting, e.g., $500.00)

V2 Salary Breakdown (CRITICAL for V2 payroll):
  - ueipab_salary_v2: Base salary subject to deductions (e.g., $300.00)
  - ueipab_bonus_v2: Bonus NOT subject to deductions (e.g., $100.00)
  - ueipab_extrabonus_v2: Extra bonus NOT subject to deductions (e.g., $60.00)
  - cesta_ticket_usd: Food allowance (e.g., $40.00)

Payroll Configuration:
  - Salary Structure: VE_PAYROLL_V2 (regular payroll)
  - Working Schedule: Standard 40 hours/week (or custom)
```

### Optional But Recommended Fields

```
Department & Job:
  - Department: [Select from existing departments]
  - Job Position: [Select or create job position]

Contract Metadata:
  - Contract Type: Employee (standard)
  - End Date: Leave blank for indefinite contracts
  - Trial End Date: Only if applicable

Venezuelan Localization (if needed):
  - ARI Tax Rate: Variable % (from tax table)
  - Original Hire Date: For antiguedad calculations
  - Previous Liquidation Date: For liquidation tracking
```

### Validation Rules

**V2 Salary Fields Must Sum to Wage:**
```
ueipab_salary_v2 + ueipab_bonus_v2 + ueipab_extrabonus_v2 + cesta_ticket_usd = wage

Example:
  $300.00 + $100.00 + $60.00 + $40.00 = $500.00 ✅
```

**V2 Salary Field is Deduction Base:**
Only `ueipab_salary_v2` is subject to SSO, FAOV, PARO, ARI deductions.
Other fields (bonus, extrabonus, cesta) are NOT deducted.

---

## 📊 Data Collection Requirements

### Information to Gather from HR/Accounting

**For Each Employee, Collect:**

| Field | Source | Example | Notes |
|-------|--------|---------|-------|
| **Employee Name** | Already in system | ALEJANDRA LOPEZ | No action needed |
| **Start Date** | HR records | 2024-01-01 | Contract effective date |
| **Base Salary (V2)** | Payroll records | $300.00 | Subject to deductions |
| **Bonus** | Payroll records | $100.00 | NOT subject to deductions |
| **Extra Bonus** | Payroll records | $60.00 | NOT subject to deductions |
| **Cesta Ticket** | Payroll records | $40.00 | Food allowance (standard) |
| **Total Wage** | Sum of above | $500.00 | For accounting |
| **Department** | HR records | Administración | Existing or new |
| **Job Position** | HR records | Teacher | Existing or new |

### Data Collection Template (Excel/CSV)

```csv
employee_id,employee_name,start_date,ueipab_salary_v2,ueipab_bonus_v2,ueipab_extrabonus_v2,cesta_ticket_usd,wage,department,job_position,ari_rate
570,ALEJANDRA LOPEZ,2024-01-01,300.00,100.00,60.00,40.00,500.00,Administración,Teacher,2.0
571,ANDRES MORALES,2024-01-01,350.00,120.00,80.00,40.00,590.00,Docencia,Professor,3.0
572,ARCIDES ARZOLA,2024-01-01,280.00,90.00,50.00,40.00,460.00,Coordinación,Coordinator,2.5
...
```

**Where to Get Data:**
1. **From Existing System:** If currently using another payroll system/spreadsheet
2. **From HR Records:** Employee personnel files
3. **From Accounting:** Current payroll registers
4. **From Testing Database:** If testing data is representative (can export)

---

## 🔄 Contract Creation Strategies

### OPTION A: Manual Creation via UI (Recommended for Initial Testing)

**When to Use:**
- Testing the system (5-10 employees)
- Executive/administrative team first
- High-accuracy requirements
- Learning the system

**Pros:**
- ✅ Full control and verification
- ✅ Easy to correct errors
- ✅ Learn system interface
- ✅ No import file preparation

**Cons:**
- ❌ Time-consuming (5-10 min per employee)
- ❌ Not scalable for 50 employees (4+ hours)
- ❌ Prone to manual entry errors at scale

**Steps:**

1. Login to production as admin
2. Navigate: **Employees → Contracts → Create**
3. Fill in required fields:
   ```
   Employee: [Select employee]
   Start Date: [Contract start date]
   Wage: [Total monthly wage]
   ```
4. Switch to **"💼 Salary Breakdown - V2"** tab
5. Fill V2 salary fields:
   ```
   ueipab_salary_v2: [Base salary]
   ueipab_bonus_v2: [Bonus amount]
   ueipab_extrabonus_v2: [Extra bonus]
   cesta_ticket_usd: [Food allowance]
   ```
6. Verify sum equals wage
7. Select **Salary Structure:** VE_PAYROLL_V2
8. Set **State:** Running (if ready to use)
9. **Save**

**Repeat for each employee**

---

### OPTION B: Bulk Import via CSV (Recommended for Full Deployment)

**When to Use:**
- Deploying for all 50 employees
- Data already exists in spreadsheet/system
- Time efficiency critical
- After successful testing phase

**Pros:**
- ✅ Fast (10 minutes to import 50 contracts)
- ✅ Scalable
- ✅ Repeatable (can re-import if errors)
- ✅ Version controlled (CSV file)

**Cons:**
- ❌ Requires data preparation (2-3 hours)
- ❌ Import errors can be confusing
- ❌ Requires understanding of Odoo import format
- ❌ External IDs needed for relationships

**Steps:**

**1. Prepare CSV File (template below)**

**2. Navigate to Import Screen:**
   - Employees → Contracts
   - Click **☰** (hamburger menu)
   - Select **Import records**

**3. Upload CSV File:**
   - Click **Load File**
   - Select your prepared CSV
   - **Encoding:** UTF-8
   - **Separator:** Comma

**4. Map Columns:**
   - Odoo will auto-detect columns
   - Verify mappings are correct
   - Pay attention to:
     - `employee_id/id` (External ID format)
     - `state` (must be "open" for active)
     - Date fields (YYYY-MM-DD format)

**5. Test Import:**
   - Click **Test** (bottom right)
   - Review any errors
   - Fix data and retry

**6. Execute Import:**
   - Click **Import** (after test succeeds)
   - Wait for completion
   - Verify contracts created

**7. Verify:**
   - Check a few contracts manually
   - Verify V2 fields populated correctly
   - Confirm state is "open"

---

### CSV Import Template

**File: `employee_contracts_production.csv`**

```csv
id,employee_id/id,name,state,date_start,wage,structure_type_id/id,ueipab_salary_v2,ueipab_bonus_v2,ueipab_extrabonus_v2,cesta_ticket_usd
contract_570,hr.hr_employee_570,Standard Contract,open,2024-01-01,500.00,hr_contract.structure_type_employee,300.00,100.00,60.00,40.00
contract_571,hr.hr_employee_571,Standard Contract,open,2024-01-01,590.00,hr_contract.structure_type_employee,350.00,120.00,80.00,40.00
contract_572,hr.hr_employee_572,Standard Contract,open,2024-01-01,460.00,hr_contract.structure_type_employee,280.00,90.00,50.00,40.00
```

**Field Explanations:**

| Column | Format | Example | Notes |
|--------|--------|---------|-------|
| `id` | Unique identifier | `contract_570` | External ID for this contract |
| `employee_id/id` | External ID reference | `hr.hr_employee_570` | Links to employee (use employee ID from system) |
| `name` | Text | `Standard Contract` | Contract title (can be same for all) |
| `state` | Selection | `open` | Contract state (use "open" for active) |
| `date_start` | Date (YYYY-MM-DD) | `2024-01-01` | Contract start date |
| `wage` | Decimal | `500.00` | Total monthly wage |
| `structure_type_id/id` | External ID | `hr_contract.structure_type_employee` | Contract type (standard) |
| `ueipab_salary_v2` | Decimal | `300.00` | V2 base salary (deductible) |
| `ueipab_bonus_v2` | Decimal | `100.00` | V2 bonus (non-deductible) |
| `ueipab_extrabonus_v2` | Decimal | `60.00` | V2 extra bonus (non-deductible) |
| `cesta_ticket_usd` | Decimal | `40.00` | Food allowance |

**How to Get Employee External IDs:**

```bash
# Export employee list with IDs:
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
employees = env['hr.employee'].search([])
print("employee_id,employee_name,external_id")
for emp in employees:
    # Try to get external ID
    ext_id = env['ir.model.data'].search([
        ('model', '=', 'hr.employee'),
        ('res_id', '=', emp.id)
    ], limit=1)
    if ext_id:
        print(f"{emp.id},{emp.name},{ext_id.complete_name}")
    else:
        # Create format: hr.hr_employee_[ID]
        print(f"{emp.id},{emp.name},hr.hr_employee_{emp.id}")
EOF
```

---

### OPTION C: Copy from Testing Database (NOT RECOMMENDED)

**When to Use:**
- Testing database has representative data
- Need exact copy of testing contracts

**Why NOT Recommended:**
1. ❌ Testing has 49 employees, production has 50 (mismatch)
2. ❌ Employee IDs won't match (ID collision risk)
3. ❌ Testing data may not be production-accurate
4. ❌ Complex process (requires pg_dump/pg_restore with ID mapping)

**Alternative:** Export testing data to CSV, then import to production (uses Option B process)

---

## 📅 Recommended Deployment Timeline

### Phase 1: Module Deployment (Day 1)
**Duration:** 2-3 hours
**Goal:** Install all payroll modules

- Install base payroll modules
- Install ueipab_payroll_enhancements
- Create 3 salary structures manually
- Configure accounting (run script)
- Create payroll journal

**NO CONTRACT CREATION YET** - System not ready for contracts

---

### Phase 2: Test Contract Creation (Day 1-2)
**Duration:** 1-2 hours
**Goal:** Validate contract creation process

**2.1 Select Test Employees (5-10 people)**
- Administrative staff (easier to coordinate)
- Different departments (test variety)
- Include 1-2 executives (high visibility)

**2.2 Manual Contract Creation**
- Create contracts via UI for test group
- Verify V2 fields populate correctly
- Test contract in different states (draft → open)

**2.3 Generate Test Payslips**
- Create test batch for current month (1-15)
- Generate payslips for test employees
- Verify calculations correct
- Check accounting entries balanced

**2.4 Validate Reports**
- Print disbursement report
- Generate compact payslip PDF
- Test email delivery

**Checkpoint:** System fully functional for test group ✅

---

### Phase 3: Data Collection (Day 2-3)
**Duration:** 4-8 hours (depends on data availability)
**Goal:** Gather salary data for all 50 employees

**3.1 Collect Data from HR/Accounting**
- Base salary (V2) for each employee
- Bonus amounts
- Extra bonus amounts
- Cesta ticket (standard $40 or custom)
- Contract start dates
- Department assignments

**3.2 Build CSV Import File**
- Use template provided above
- Fill in data for all 50 employees
- Validate sums (V2 fields = wage)
- Review for accuracy

**3.3 Stakeholder Review**
- HR reviews employee assignments
- Accounting reviews salary amounts
- Management approves deployment

**Checkpoint:** Data collected and validated ✅

---

### Phase 4: Bulk Contract Import (Day 3-4)
**Duration:** 1-2 hours
**Goal:** Create contracts for all employees

**4.1 Test Import (Staging or with 5 employees)**
- Import small subset first
- Verify mappings correct
- Fix any errors

**4.2 Full Import**
- Import all 50 employee contracts
- Monitor for errors
- Verify import success

**4.3 Manual Verification**
- Spot-check 10-15 contracts
- Verify V2 fields correct
- Confirm all contracts in "open" state

**Checkpoint:** All employees have active contracts ✅

---

### Phase 5: Full Payroll Test (Day 4-5)
**Duration:** 2-3 hours
**Goal:** Generate payroll for entire workforce

**5.1 Create Production Batch**
- Batch name: "Test Run - [Current Month]"
- Date range: Current month
- Select all 50 employees

**5.2 Generate Payslips**
- Use VE_PAYROLL_V2 structure
- Let system compute all payslips
- Review for errors

**5.3 Validate Calculations**
- Spot-check 10-15 payslips
- Verify deductions correct
- Check net amounts reasonable

**5.4 Generate Reports**
- Disbursement report (PDF/Excel)
- Compact payslips for all employees
- Review totals

**5.5 Confirm Batch**
- Validate batch (if no errors)
- Check accounting entries
- Verify journal balanced

**Checkpoint:** Payroll system operational for all 50 employees ✅

---

### Phase 6: Go-Live (Day 5+)
**Duration:** Ongoing
**Goal:** Regular payroll operations

**6.1 User Training**
- Train payroll team (1 hour)
- Demonstrate contract management
- Show payslip generation workflow

**6.2 First Real Payroll**
- Process first official payroll
- Monitor closely for issues
- Be available for support

**6.3 Ongoing Operations**
- Monthly payroll cycles
- Contract updates as needed
- New employee onboarding

---

## 🔍 Contract Verification Checklist

After creating contracts (manual or bulk), verify:

**Per Contract:**
- [ ] Employee assigned correctly
- [ ] Start date appropriate
- [ ] State is "open" (active)
- [ ] Wage field populated
- [ ] V2 salary fields filled:
  - [ ] ueipab_salary_v2 > 0
  - [ ] ueipab_bonus_v2 >= 0
  - [ ] ueipab_extrabonus_v2 >= 0
  - [ ] cesta_ticket_usd >= 0
- [ ] Sum of V2 fields = wage
- [ ] Salary structure assigned (VE_PAYROLL_V2)
- [ ] Department assigned (if applicable)

**System-Wide:**
- [ ] All 50 employees have contracts
- [ ] All contracts in "open" state
- [ ] No duplicate contracts per employee
- [ ] Salary structures assigned correctly
- [ ] Working schedules configured

**Test Generation:**
- [ ] Can generate test payslip successfully
- [ ] Payslip lines calculated correctly
- [ ] Deductions computed accurately
- [ ] Net amount reasonable
- [ ] Accounting entry balanced

---

## 🚨 Common Issues & Solutions

### Issue 1: "Validation Error: Wage must equal sum of V2 fields"

**Cause:** V2 salary fields don't add up to wage field

**Solution:**
```
Recalculate:
  wage = ueipab_salary_v2 + ueipab_bonus_v2 + ueipab_extrabonus_v2 + cesta_ticket_usd

Example:
  $300 + $100 + $60 + $40 = $500 ✅
```

### Issue 2: "No salary structure assigned"

**Cause:** Forgot to assign VE_PAYROLL_V2 structure

**Solution:**
- Edit contract
- Salary Structure field → Select "VE_PAYROLL_V2"
- Save

### Issue 3: "Cannot generate payslip - no active contract"

**Cause:** Contract state is "draft" or "close" instead of "open"

**Solution:**
- Edit contract
- State field → Change to "Running" (open)
- Save

### Issue 4: "Import fails with 'employee_id not found'"

**Cause:** Employee external ID format incorrect in CSV

**Solution:**
- Check employee IDs in production
- Use format: `hr.hr_employee_[ID]` or actual external ID
- Example: `hr.hr_employee_570` for employee ID 570

### Issue 5: "Deductions not calculating"

**Cause:** ueipab_salary_v2 field is $0.00 (deduction base is zero)

**Solution:**
- Edit contract
- Ensure ueipab_salary_v2 > 0 (e.g., $300.00)
- This is the base for SSO, FAOV, PARO, ARI deductions

---

## 📊 Progress Tracking Template

**Contract Creation Progress:**

| Phase | Status | Completion Date | Notes |
|-------|--------|-----------------|-------|
| Module Deployment | ⬜ Pending | - | Install all payroll modules |
| Test Employee Selection | ⬜ Pending | - | Select 5-10 test employees |
| Test Contract Creation | ⬜ Pending | - | Manual creation for test group |
| Test Payslip Generation | ⬜ Pending | - | Validate calculations |
| Data Collection | ⬜ Pending | - | Gather salary data for all 50 |
| CSV Preparation | ⬜ Pending | - | Build import file |
| Test Import | ⬜ Pending | - | Import 5-10 employees |
| Full Import | ⬜ Pending | - | Import all 50 employees |
| Contract Verification | ⬜ Pending | - | Spot-check contracts |
| Full Payroll Test | ⬜ Pending | - | Generate for all 50 employees |
| Go-Live Approval | ⬜ Pending | - | Stakeholder sign-off |

**Employees Processed:**
```
Test Group:      [0/10]  Progress: [          ] 0%
Remaining:       [0/40]  Progress: [          ] 0%
Total:           [0/50]  Progress: [          ] 0%
```

---

## 💡 Best Practices

**1. Start Small**
- Begin with 5-10 test employees
- Validate system completely before scaling
- Learn from initial mistakes

**2. Validate Data**
- Double-check salary amounts
- Verify sums (V2 fields = wage)
- Review with HR/accounting before import

**3. Keep Backups**
- Backup database before bulk import
- Keep CSV source files
- Document any manual corrections

**4. Communicate Early**
- Inform employees about new system
- Set expectations for first payroll
- Provide support contact info

**5. Monitor First Cycles**
- Watch first 2-3 payroll cycles closely
- Collect employee feedback
- Fix issues immediately

---

## 📞 Support & Escalation

**For Contract Issues:**
- **HR Team:** Employee assignments, start dates
- **Accounting:** Salary amounts, deduction rates
- **Technical:** Import errors, system issues

**For Payroll Issues:**
- **Payroll Team:** Batch generation, payslip validation
- **Accounting:** Journal entries, account mapping
- **Technical:** Calculation errors, report issues

---

## 🎯 Success Criteria

**Contract Creation Phase Complete When:**
- [ ] All 50 employees have active contracts
- [ ] All V2 salary fields populated correctly
- [ ] All contracts in "open" state
- [ ] Test payslips generated successfully
- [ ] Accounting entries balanced
- [ ] Reports generating correctly
- [ ] Email delivery working
- [ ] Stakeholders approve go-live

---

## 📝 Next Steps After Contract Creation

**Once contracts are created:**

1. **Generate First Real Payroll:**
   - Create official batch for current month
   - Generate payslips for all employees
   - Review and validate
   - Confirm batch

2. **Send Payslips to Employees:**
   - Use email delivery system
   - Select appropriate template
   - Send batch emails

3. **Generate Disbursement Report:**
   - Print report for finance approval
   - Export to Excel for accounting
   - Review totals

4. **Regular Operations:**
   - Monthly payroll cycles
   - Contract updates (raises, bonuses)
   - New employee onboarding
   - Liquidation processing

---

**Document Status:** ✅ COMPLETE - Ready for Implementation
**Version:** 1.0
**Date:** November 24, 2025
**Next Review:** After Phase 1 completion
