# Custom Contract Fields & Views - Availability Timeline

**Question:** When will the custom contract fields (V2 fields) and views be available in production?

**Answer:** **Immediately after Phase 1, Step 4 (ueipab_hr_contract update)**

---

## 📅 Exact Timeline

### Phase 1: Module Deployment (Day 1)

**Step 1-3: Base Payroll Modules (30 min)**
- Install `hr_payroll_community`
- Install `hr_payroll_account_community`
- ❌ **V2 fields NOT yet available**

**Step 4: Update ueipab_hr_contract v1.0.0 → v1.5.0 (15 min)** ⭐
```bash
docker exec -it ueipab17 odoo -d DB_UEIPAB \
    -u ueipab_hr_contract \
    --stop-after-init \
    --log-level=info
```
- ✅ **V2 fields NOW AVAILABLE in database**
- ✅ **Custom views NOW VISIBLE in UI**
- ✅ **Can immediately create contracts with V2 data**

**Step 5-8: Custom Payroll Modules (45 min)**
- Install `ueipab_payroll_enhancements`
- Install `hr_payslip_monthly_report`
- Restart Odoo
- Clear assets

---

## 🔑 What Gets Added in Step 4

### Database Fields (Added to `hr_contract` table)

**V2 Compensation Fields:**
```python
ueipab_salary_v2       # Base salary (deductible)
ueipab_bonus_v2        # Bonus (non-deductible)
ueipab_extrabonus_v2   # Extra bonus (non-deductible)
cesta_ticket_usd       # Food allowance (already exists in v1.0.0)
```

**V2 Liquidation Historical Tracking:**
```python
ueipab_original_hire_date         # For antiguedad continuity
ueipab_previous_liquidation_date  # For rehires
ueipab_vacation_paid_until        # Vacation accrual tracking
ueipab_vacation_prepaid_amount    # Prepaid vacation/bono amount
```

**V1 Fields (Already in production v1.0.0):**
```python
ueipab_salary_base      # V1: 70% salary
ueipab_bonus_regular    # V1: 25% bonus
ueipab_extra_bonus      # V1: 5% extra bonus
ueipab_deduction_base   # V1: K+L deduction base
wage_ves                # Venezuelan Bolivars wage
ueipab_ari_rate         # ARI tax rate
```

### UI Views (Added to Contract Form)

**New Notebook Pages:**

**Page 1: "💼 Salary Breakdown" (V2 Fields)**
```
Fields visible:
  - Salary V2 (Deductible)      [ueipab_salary_v2]
  - Extra Bonus V2              [ueipab_extrabonus_v2]
  - Bonus V2                    [ueipab_bonus_v2]
  - Cesta Ticket (USD)          [cesta_ticket_usd]
  - Total Wage (auto-calculated) [wage]

Plus deduction rules explanation and proration formula
```

**Page 2: "💰 Salary Tax Breakdown" (ARI Tax)**
```
Fields visible:
  - ARI Withholding Rate (%)    [ueipab_ari_rate]
  - Last ARI Update Date        [ueipab_ari_last_update]

Plus tax bracket information and update tracking
```

**Page 3: "📋 Salary Liquidation" (Historical Tracking)**
```
Fields visible:
  - Original Hire Date          [ueipab_original_hire_date]
  - Previous Liquidation Date   [ueipab_previous_liquidation_date]
  - Vacation Paid Until         [ueipab_vacation_paid_until]
  - Vacation Prepaid Amount     [ueipab_vacation_prepaid_amount]

Plus liquidation tracking explanations
```

**Page 4: "⚙️ Salary Parameters" (Payroll Schedule)**
```
Fields visible:
  - Payroll Schedule            [ueipab_payroll_schedule]
  - Payment Day                 [ueipab_payment_day]

Plus bi-monthly payroll configuration
```

---

## ✅ Verification After Step 4

**How to Verify Fields Are Available:**

1. **Via Odoo Shell:**
```bash
docker exec -it ueipab17 odoo shell -d DB_UEIPAB << 'EOF'
# Check if V2 fields exist
Contract = env['hr.contract']
if hasattr(Contract, 'ueipab_salary_v2'):
    print("✅ V2 salary fields are available!")
else:
    print("❌ V2 fields not found")

# List all V2 fields
v2_fields = ['ueipab_salary_v2', 'ueipab_bonus_v2', 'ueipab_extrabonus_v2',
             'ueipab_original_hire_date', 'ueipab_vacation_prepaid_amount']
for field_name in v2_fields:
    if hasattr(Contract, field_name):
        print(f"  ✅ {field_name}")
    else:
        print(f"  ❌ {field_name} MISSING")
EOF
```

2. **Via UI:**
```
Navigate: Employees → Contracts → Create (or open existing)

Check for new notebook pages:
  ✅ "💼 Salary Breakdown" tab visible?
  ✅ "💰 Salary Tax Breakdown" tab visible?
  ✅ "📋 Salary Liquidation" tab visible?
  ✅ "⚙️ Salary Parameters" tab visible?

If YES to all → V2 fields and views are active!
```

---

## 📋 Contract Creation Timeline

### Phase 1: Module Deployment (FIRST)
```
Step 4: Update ueipab_hr_contract v1.0.0 → v1.5.0
  ↓
✅ V2 fields available in database
✅ Custom views visible in UI
✅ READY to create contracts with V2 data
```

### Phase 2: Test Contract Creation (AFTER Phase 1)
```
Can NOW create test contracts because:
  ✅ V2 fields exist in database
  ✅ Custom form views available
  ✅ Can fill ueipab_salary_v2, bonus_v2, etc.
```

### Phase 3-4: Data Collection & Bulk Import (AFTER Phase 2)
```
Can prepare CSV with V2 fields because:
  ✅ Fields already exist in database
  ✅ Import tool recognizes V2 columns
  ✅ Can import all 50 contracts with V2 data
```

---

## 🚨 Important Notes

### 1. Fields Available ≠ Contracts Created

**After Step 4:**
- ✅ Fields exist in database schema
- ✅ Views show the fields in UI
- ❌ NO contracts created yet (still 48 employees without contracts)

**You still need to CREATE the contracts** (Phase 2-4)

### 2. Production Already Has v1.0.0

**Current production state:**
```
ueipab_hr_contract: v1.0.0 (OUTDATED)
  - Has V1 fields only
  - Missing V2 fields
  - Missing liquidation tracking fields
```

**After update to v1.5.0:**
```
ueipab_hr_contract: v1.5.0 (CURRENT)
  - Has V1 fields (backward compatible)
  - Has V2 fields (NEW)
  - Has liquidation tracking fields (NEW)
```

**Benefit:** V1 and V2 coexist, so if any V1 contracts exist, they won't break.

### 3. Module Update is NON-DESTRUCTIVE

**What happens during update:**
- ✅ New fields ADDED to database
- ✅ New views ADDED to UI
- ✅ Existing data PRESERVED (if any V1 contracts exist)
- ❌ NO data deleted
- ❌ NO contracts modified

**Safe to run:** Zero risk of data loss

---

## 📊 Visual Timeline

```
Module Deployment Timeline:
================================================================================

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
│   └── ✅ V2 fields still available (no changes)
│
└── ✅ Phase 1 Complete: Ready to create contracts with V2 data

Phase 2 - Test Contract Creation (Day 1-2)
├── Manual creation of 5-10 test contracts
│   └── Uses V2 fields (available from Phase 1)
│
└── ✅ System validated with real contract data

Phase 3 - Data Collection (Day 2-3)
├── Gather V2 salary data for all 50 employees
└── Build CSV with V2 columns

Phase 4 - Bulk Import (Day 3-4)
├── Import all 50 contracts with V2 data
└── ✅ All employees have contracts with V2 fields
```

---

## 🎯 Key Takeaways

1. **V2 fields available IMMEDIATELY after Phase 1, Step 4** (ueipab_hr_contract update)

2. **Can create contracts with V2 data starting in Phase 2** (right after module deployment)

3. **No separate "field installation" step needed** - fields are part of module update

4. **Custom views automatically visible** - no configuration required

5. **Timeline is sequential** - Must complete Phase 1 before creating contracts in Phase 2

---

## 🔄 Migration Plan Impact

**CONTRACT_MIGRATION_PLAN.md should be updated to clarify:**

**Phase 1: Module Deployment**
```
✅ Deploy all modules (including ueipab_hr_contract v1.5.0)
✅ V2 contract fields become available
✅ Custom form views visible
→ READY for contract creation
```

**Phase 2: Test Contract Creation**
```
✅ V2 fields already available (from Phase 1)
✅ Create 5-10 test contracts manually
✅ Use "💼 Salary Breakdown" tab to fill V2 fields
→ Validate V2 data entry workflow
```

**Phase 3-4: Data Collection & Bulk Import**
```
✅ V2 fields available for import
✅ CSV can include V2 columns
✅ Import all 50 contracts with V2 data
→ Full workforce has V2 contracts
```

---

## ✅ Answer Summary

**Your Question:** "In what part of the plan will be implemented contract custom fields and views?"

**Answer:**
**Phase 1, Step 4** - When we update `ueipab_hr_contract` from v1.0.0 to v1.5.0 (takes 15 minutes)

**After this step:**
- ✅ All V2 fields exist in database
- ✅ All custom views visible in UI
- ✅ Ready to create contracts with V2 data
- ✅ No additional steps needed

**Impact on contract creation:**
- Phase 2 (test contracts): Can use V2 fields
- Phase 4 (bulk import): Can import V2 data
- No delay - fields ready when you need them

---

**Document Version:** 1.0
**Date:** November 24, 2025
**Status:** ✅ COMPLETE
