# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-16

## Core Instructions

⚠️ **CRITICAL RULES:**
- **ALWAYS work locally, NEVER in production environment**
- **NEVER TOUCH DB_UEIPAB without proper authorization from user**
- Development database: `testing`
- Production database: `DB_UEIPAB` (requires authorization)

## Environment Synchronization

**VEB Exchange Rate Sync Script:** `scripts/sync-veb-rates-from-production.sql`
- Syncs VEB rates from production to testing database
- **Production Source:** `ueipab17_postgres_1` container @ 10.124.0.3, DB: DB_UEIPAB
- **Last Sync:** 2025-11-14 (added 3 rates: 2025-11-12 to 2025-11-14)
- **Current Status:** 622 VEB rates synchronized (2024-01-30 to 2025-11-14)
- Always verify before executing
- Alternative execution: Use `scripts/run_veb_sync.py` via Odoo shell

---

## Features & Documentation Quick Reference

### 1. Payroll Disbursement Detail Report

**Status:** ✅ Production Ready
**Last Updated:** 2025-11-14
**Module:** `ueipab_payroll_enhancements`

**Quick Summary:**
- Report showing employee payroll disbursement details with deduction breakdown
- **NEW: 70/30 Salary/Bonus split** for accounting transparency
- Currency selector (USD/VEB) with automatic conversion
- Exchange rate display for VEB reports
- Fixed ARI TAX and Social Security columns to use correct salary rule codes
- Added individual deduction columns: ARI, SSO 4%, FAOV 1%, PARO 0.5%
- 9% tax calculation on Net Payable (USD and VEB)
- Landscape Letter format with optimized layout

**70/30 Salary/Bonus Split (2025-11-14):**
The report now splits the GROSS column into two columns using a 70/30 formula:

**Formula:**
```python
Salary = deduction_base × 70%
Bonus = (deduction_base × 30%) + (wage - deduction_base)
Total = Salary + Bonus = wage
```

**Rationale:**
- `deduction_base` represents the portion of wage subject to social security and tax (~42% of total wage)
- The 70/30 split provides accounting transparency:
  - **Salary (70%)**: Reportable salary for accounting purposes
  - **Bonus (30%)**: Remaining deduction_base portion + all other benefits/bonuses
- VE_NET values are UNCHANGED (formula only affects report column display)

**Example (Rafael Perez):**
- **Before:** Salary $170.30 (100% of deduction_base), Bonus $230.32
- **After:** Salary $119.21 (70% of deduction_base), Bonus $281.41 (30% + other benefits)
- **Wage:** $400.62 (unchanged)
- **VE_NET:** $193.72 (unchanged)

**Verification (NOVIEMBRE15-2 Batch):**
- ✅ All NOVIEMBRE15-2 payslips verified against Google Spreadsheet
- ✅ 86% exact match rate (38/44 payslips)
- ✅ 4 minor mismatches (differences $0.69 - $2.86, under 1.1%)
- ✅ Formula mathematically verified for all employees
- 📖 **[Verification Report](documentation/NOVIEMBRE15-2_VERIFICATION_SUMMARY.md)**

**Currency Selector Enhancement:**
- Wizard includes currency selection field (USD or VEB)
- Default currency: USD
- VEB conversion uses historical exchange rates from payslip period end date
- Exchange rate display: "@ 234.87 VEB/USD" when VEB selected
- Display-time multiplication only (no database modifications)
- Dynamic currency symbols and names throughout report

**Critical Fixes Applied:**
1. **VE_GROSS Double-Counting:** Excluded VE_GROSS from bonus calculation (it's a sum line)
2. **Database Protection:** Confirmed report does NOT modify payslip data
3. **Exchange Rate Display:** Shows rate used for VEB conversions

**Implementation:**
- Wizard: `payroll_disbursement_wizard.py` - Currency selection field
- Report Model: `payroll_disbursement_report.py` - Exchange rate calculation (no DB modification)
- Template: `payroll_disbursement_detail_report.xml` - 70/30 formula + exchange rate display

**Test Results:**
- ✅ USD Report: NOVIEMBRE15-2, 44 payslips, Rafael Perez: Salary $119.21, Bonus $281.41
- ✅ VEB Report: Same batch, exchange rate @ 234.87 VEB/USD
- ✅ No database corruption after multiple report generations

**Location:** `addons/ueipab_payroll_enhancements/reports/payroll_disbursement_detail_report.xml`

📖 **[Complete Documentation](documentation/PAYROLL_DISBURSEMENT_REPORT.md)**

---

### 2. Venezuelan Liquidation System

**Status:** ✅ Production Ready (All 9 Phases Complete)
**Last Updated:** 2025-11-13
**Module:** `ueipab_payroll_enhancements` + `ueipab_hr_contract`

**Quick Summary:**
- Calculates employee severance and benefits per Venezuelan Labor Law (LOTTT)
- Fixed hardcoded formulas - now calculates dynamically based on contract data
- Added 3 historical tracking fields for complex employee scenarios
- Implements vacation prepaid deduction for Aug 1 annual payments
- All 13 salary rules updated and tested

**Key Contract Fields:**
```python
contract.ueipab_deduction_base         # Base salary for liquidation
contract.ueipab_original_hire_date     # Original hire date (for antiguedad)
contract.ueipab_previous_liquidation_date  # Last full liquidation date
contract.ueipab_vacation_paid_until    # Last vacation payment date (Aug 1)
```

**Production-Ready Scripts:**
- `/opt/odoo-dev/scripts/phase2_fix_liquidation_formulas_validated.py`
- `/opt/odoo-dev/scripts/phase3_fix_historical_tracking_tryexcept.py`
- `/opt/odoo-dev/scripts/phase4_add_vacation_prepaid_deduction.py`
- `/opt/odoo-dev/scripts/phase4_fix_net_safe.py`
- `/opt/odoo-dev/scripts/phase4_fix_sequence_order.py`

**Test Cases:**
- ✅ Gabriel España (simple case): $875.34 net
- ✅ Virginia Verde (complex rehire): $786.18 net
- ✅ Josefina Rodriguez (prepaid deduction): $1,177.00 net

📖 **[Complete Documentation](documentation/LIQUIDATION_COMPLETE_GUIDE.md)**

---

### 3. Prestaciones Sociales Interest Report

**Status:** ✅ Production Ready - All Issues Resolved!
**Last Updated:** 2025-11-14
**Module:** `ueipab_payroll_enhancements` v1.7.0

**Quick Summary:**
- Month-by-month breakdown of prestaciones and interest accumulation
- Uses simple interest on average balance (13% annual rate)
- Wizard-based report with currency selection (USD/VEB)
- 11-column landscape report format
- Shows quarterly prestaciones deposits and monthly interest accrual
- **Full VEB currency support with historical exchange rates**

**Interest Calculation Method:**
```python
# SIMPLE interest (not compound)
average_balance = prestaciones * 0.5
interest = average_balance * 0.13 * (service_months / 12.0)
```

**Test Case:** SLIP/568 (Josefina Rodriguez)
- 23 months of service (Sep 2023 - Jul 2025)
- **USD Report:** Prestaciones $605.85, Interest $83.76
- **VEB Report:** Prestaciones Bs.75,434.50, Interest Bs.10,428.66
- Exchange rates: 36.14 - 231.09 VEB/USD (varies by month)

**Issues Fixed (2025-11-14):**

1. **Blank PDF Issue:**
   - Root Cause: AbstractModel reading from `docids` instead of `data.get('payslip_ids')`
   - Fix Applied: Changed to read from wizard data first (same pattern as working Disbursement report)
   - Result: ✅ Report generates correctly with all 23 rows of data

2. **VEB Currency Support:**
   - Root Cause: Exchange rate lookup returning 1.0, values not converted, hardcoded "$" symbol
   - Fix Applied:
     - Implemented Odoo's `_convert()` method for currency conversion
     - Updated `_get_exchange_rate()` to use historical rates (fallback to earliest for old dates)
     - Changed template to use dynamic currency symbol
   - Result: ✅ Report displays correctly in both USD and VEB with proper exchange rates

📖 **[Complete Documentation](documentation/PRESTACIONES_INTEREST_REPORT.md)**
📖 **[Wizard-Based Report Pattern Guide](documentation/WIZARD_BASED_REPORT_PATTERN.md)** ⭐ NEW!

---

### 4. Venezuelan Payroll V2 Revision Plan

**Status:** ✅ PHASE 3 COMPLETE - READY FOR PHASE 4
**Created:** 2025-11-14
**Updated:** 2025-11-16
**Type:** System Redesign

**Purpose:**
Migrate from percentage-based V1 salary structure to direct-amount V2 model for improved clarity and maintainability.

**Root Cause (Why V2 is Needed):**

After verifying NOVIEMBRE15-2 payslips against Google Spreadsheet:
- ✅ 40/44 employees (91%) matched exactly
- ❌ 4/44 employees showed $0.69-$2.86 differences
- **Cause:** V1 design uses confusing percentage calculations (70%, 25%, 5% of deduction_base)
- **Result:** Deductions applied to 100% of deduction_base instead of Salary portion only

**This is NOT a legal compliance issue** - All Venezuelan labor regulations are followed correctly. This is a **MODEL DESIGN IMPROVEMENT** to eliminate confusion and simplify payroll administration.

**Current V1 Design (Confusing):**
```python
# Stored in contract
contract.ueipab_deduction_base = $170.30  # ~42% of wage

# Calculated via salary rules (percentages)
VE_SALARY_70 = deduction_base × 70%  # $119.21
VE_BONUS_25  = deduction_base × 25%  # $42.58
VE_EXTRA_5   = deduction_base × 5%   # $8.52

# Deductions applied to 100% of deduction_base
VE_SSO_DED = deduction_base × 2.25%  # Applied to $170.30
```

**Proposed V2 Design (Clear):**
```python
# Store direct amounts in contract (no percentages!)
contract.ueipab_salary_v2       = $119.21  # Subject to deductions
contract.ueipab_extrabonus_v2   = $42.58   # NOT subject to deductions
contract.ueipab_bonus_v2        = $198.83  # NOT subject to deductions
contract.ueipab_cesta_ticket_v2 = $40.00   # Food allowance (fixed ~$40 for all employees)
contract.wage = Salary + ExtraBonus + Bonus + Cesta = $400.62

# Deductions applied ONLY to Salary field
VE_SSO_DED = ueipab_salary_v2 × 2.25%  # Applied to $119.21
```

**Deduction Rates (Monthly Basis with Proration) - CEO CONFIRMED:**
1. **IVSS (SSO):** 4.0% monthly (prorated by actual payslip period days/30)
2. **FAOV:** 1.0% monthly (prorated by actual payslip period days/30)
3. **INCES (PARO):** 0.5% monthly (prorated by actual payslip period days/30)
4. **ARI:** Dynamic % (from `ueipab_ari_withholding_rate` field, prorated by days/30)

**Proration Formula:** `monthly_deduction × (period_days / 30.0)`
- Handles standard bi-weekly (15 days), terminations, partial periods automatically
- CEO approved Option A (True Semi-Monthly Division) approach

All deductions apply **ONLY to Salary V2 field** (NOT to ExtraBonus, Bonus, or Cesta Ticket).

**Systems Affected:**
1. **[VE] UEIPAB Venezuelan Payroll** - Regular bi-weekly payroll (44 employees, 24x/year)
2. **Liquidación Venezolana** - Employee termination settlements
3. **Aguinaldos Diciembre 2025** - Christmas bonus payments

**Migration Strategy:**
- 8-phase implementation plan with parallel V1/V2 operation
- Keep V1 operational during V2 testing and validation
- Eventually decommission V1 after full migration
- **New:** "SalaryStructureV2" spreadsheet tab for pre-calculation and validation
  - Spreadsheet: `19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s`
  - Pre-calculate all V2 field values for all 44 employees
  - HR/Accounting review before Odoo import
  - Can export to CSV for bulk import

**Implementation Status:**
- ✅ **Phase 1 COMPLETE:** Root cause analysis, impact analysis, V2 plan documented
- ✅ **Phase 1 COMPLETE:** Spreadsheet validation (100% accuracy - 44/44 employees)
- ✅ **Phase 1 COMPLETE:** Cesta Ticket decision (reuse existing field)
- ✅ **Phase 1 COMPLETE:** V2 design clarification (NO percentages, HR-approved values)
- ✅ **CEO APPROVED (2025-11-16):** Legal compliance confirmed, all blockers removed
- ✅ **CEO APPROVED (2025-11-16):** Option A deduction approach (proration by days/30)
- ✅ **CEO APPROVED (2025-11-16):** Bulk UPDATE strategy (V1 fields untouched)
- ✅ **Phase 2 COMPLETE (2025-11-16):** V2 contract fields added to `ueipab_hr_contract` v1.4.0
  - `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2` fields created
  - Database columns and indexes created
  - **Contract form view redesigned with 4 new dedicated notebook pages:**
    - 💼 **Salary Breakdown** - V2 compensation fields + Cesta Ticket + auto-calculated wage
    - 💰 **Salary Tax Breakdown** - ARI withholding rate and update tracking
    - 📋 **Salary Liquidation** - Historical tracking (hire date, previous liquidation, vacation)
    - ⚙️ **Salary Parameters** - Payroll schedule configuration (bi-monthly, payment days)
  - Auto-calculation onchange method implemented
  - Full Odoo conventions (tracking, copy, groups, index, comprehensive help text)
  - Improved UX: Fields logically organized, cleaner layout, helpful explanatory labels
- ✅ **Phase 3 COMPLETE (2025-11-16):** V2 Salary Structure created with 11 salary rules
  - **Structure:** "Salarios Venezuela UEIPAB V2" (Code: VE_PAYROLL_V2, ID: 9)
  - **Earnings Rules (5):** VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2, VE_CESTA_TICKET_V2, VE_GROSS_V2
  - **Deduction Rules (5):** VE_SSO_DED_V2 (4%), VE_FAOV_DED_V2 (1%), VE_PARO_DED_V2 (0.5%), VE_ARI_DED_V2 (variable%), VE_TOTAL_DED_V2
  - **Net Rule (1):** VE_NET_V2
  - All deductions apply ONLY to `ueipab_salary_v2` field (NOT to bonuses or cesta ticket)
  - All amounts prorated by actual payslip period: `monthly_amount × (period_days / 30.0)`
  - Proper sequence order: Earnings (1-5), Deductions (101-105), Net (200)
  - **Accounting:** Left blank for now (can copy from V1 structure later once V2 is tested)
  - **Script:** `/opt/odoo-dev/scripts/phase3_create_v2_salary_structure.py`
- ⏳ **Phases 4-8:** Pending (awaiting user approval to proceed)

**Spreadsheet Validation Results (2025-11-15):**
- ✅ **44/44 employees (100.0%)** - Perfect wage match! 🎯
- ⚠️ 0/44 employees (0.0%) - No mismatches
- Spreadsheet ID: `19Kbx42whU4lzFI4vcXDDjbz_auOjLUXe7okBhAFbi8s`, Tab: "15nov2025"
- Exchange Rate: 234.8715 VEB/USD
- **Conclusion:** Spreadsheet is **fully validated** and ready for V2 migration
- **Status:** Migration-ready with 100% data accuracy confirmed

**Cesta Ticket Design Decision (2025-11-15):**
- ✅ **REUSE existing field:** `cesta_ticket_usd` (already exists in V1)
- ❌ **NOT creating:** `ueipab_cesta_ticket_v2` (would duplicate existing field)
- **Rationale:** Cesta Ticket is legally distinct mandatory benefit requiring separate tracking
- **V2 Wage Formula:** `wage = ueipab_salary_v2 + ueipab_extrabonus_v2 + ueipab_bonus_v2 + cesta_ticket_usd`
- **Current Rule:** `VE_CESTA_TICKET` will continue working in V2 (no changes needed)

**V2 Design Clarification - NO Percentage Calculations (2025-11-15):**

**CRITICAL:** V2 eliminates ALL percentage calculations. Values are HR-approved actual dollar amounts.

**❌ WRONG (What V1 Does):**
```python
# V1 - Confusing percentage calculations
VE_SALARY_70 = ueipab_deduction_base × 70%  # Calculated percentage
VE_BONUS_25  = ueipab_deduction_base × 25%  # Calculated percentage
VE_EXTRA_5   = ueipab_deduction_base × 5%   # Calculated percentage
```

**✅ CORRECT (What V2 Does):**
```python
# V2 - Direct HR-approved dollar amounts (NO calculations!)
ueipab_salary_v2 = $119.21      # HR-approved actual value (stored in contract)
ueipab_bonus_v2 = $281.41       # HR-approved actual value (stored in contract)
ueipab_extrabonus_v2 = $0.00    # HR-approved actual value (stored in contract)
cesta_ticket_usd = $40.00       # Existing field (not migrated)
```

**Migration Approach:**
- ✅ HR fills "SalaryStructureV2" spreadsheet tab with **actual dollar values**
- ✅ HR reviews and approves all 44 employee breakdowns
- ✅ Migration script **imports** these values (NO calculation, NO percentages)
- ✅ 70/30 split is only a **suggestion** for HR (they can use any split they want)

**Why This Matters:**
The whole purpose of V2 is to eliminate confusing percentage logic and use transparent, direct dollar amounts that HR controls.

**Diagnostic Scripts Created:**
- `scripts/verify_70_percent_pattern.py` - Confirmed 40 employees use 100% base
- `scripts/detailed_comparison.py` - Component-by-component analysis
- `scripts/diagnose_4_mismatches.py` - Deep dive on 4 mismatched employees
- `scripts/analyze_spreadsheet_formulas.py` - Verified spreadsheet calculations
- `scripts/analyze_period_scaling.py` - Confirmed semi-monthly logic
- `scripts/check_deduction_formulas.py` - Validated formula percentages
- `scripts/validate_spreadsheet_wages_v2.py` - **NEW:** Validates Odoo wages vs spreadsheet (100% match ✅)

📖 **[Complete V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)** (840 lines)

**CEO Directives (2025-11-16):**
- ✅ **Phase 2 APPROVED:** Begin implementation of V2 contract fields
- ✅ **Strategy:** Bulk UPDATE (add V2 fields, keep V1 fields untouched)
- ✅ **Testing:** Validate against already-paid NOVIEMBRE15-2 batch
- ✅ **Timeline:** 6-day development cycle approved (Nov 18-23)
- ✅ **Legal:** CEO confirmed full Venezuelan labor law compliance

---

## Additional Documentation

### Legal & Compliance
- **LOTTT Law Research:** `documentation/LOTTT_LAW_RESEARCH_2025-11-13.md`
- **Liquidation Clarifications:** `documentation/LIQUIDATION_CLARIFICATIONS.md`

### Technical Analysis
- **Liquidation Approach Analysis:** `documentation/LIQUIDATION_APPROACH_ANALYSIS.md`
- **Monica Mosqueda Analysis:** `documentation/MONICA_MOSQUEDA_ANALYSIS_2025-11-13.md`
- **Liquidation Validation Summary:** `documentation/LIQUIDATION_VALIDATION_SUMMARY_2025-11-13.md`

### Historical Documentation
- **Original Formula Fix:** `documentation/LIQUIDATION_FORMULA_FIX_2025-11-12.md`

---

## Key Technical Learnings

### Odoo safe_eval Restrictions (Salary Rules)

```python
# ❌ FORBIDDEN in safe_eval:
from datetime import timedelta  # NO import statements
hasattr(contract, 'field')      # NO hasattr()
getattr(contract, 'field')      # NO direct getattr()

# ✅ ALLOWED in safe_eval:
(date1 - date2).days            # Direct date arithmetic
try:                            # Try/except for optional fields
    value = contract.field
    if not value:
        value = False
except:
    value = False
```

### Odoo 17 View Syntax

```xml
<!-- ❌ DEPRECATED (Odoo 16) -->
<div attrs="{'invisible': [('field', '=', 0)]}">

<!-- ✅ CURRENT (Odoo 17) -->
<div invisible="field == 0">
```

### Form View UX Design - Notebook Pages

**Best Practice:** Organize complex forms into logical notebook pages for better UX

**Pattern:** Add pages after existing notebook pages using XPath position
```xml
<page name="information" position="after">
    <page string="💼 Category Name" name="category_slug">
        <group string="Section Title">
            <group>
                <field name="field1"/>
                <field name="field2"/>
            </group>
            <group>
                <separator string="Help Section"/>
                <div class="o_form_label">Helpful explanation text</div>
            </group>
        </group>
    </page>
</page>
```

**View Validation Rules:**
- Labels without `for` attribute must use `class="o_form_label"`
- Use `<div class="o_form_label">` for explanatory text (not `<label>`)
- Each page needs unique `name` and descriptive `string` attributes
- Use emojis in page titles for visual clarity (💼 💰 📋 ⚙️)

**Contract Form Example (ueipab_hr_contract):**
- 💼 Salary Breakdown - V2 compensation fields
- 💰 Salary Tax Breakdown - Tax withholding configuration
- 📋 Salary Liquidation - Historical tracking fields
- ⚙️ Salary Parameters - Payroll schedule settings

**Benefits:**
- Clean, uncluttered UI
- Logical field grouping
- Easy navigation between categories
- Contextual help text in each section

### Report Development

- Report model naming: `report.<module>.<template_id>` (exact match required)
- TransientModel wizards require explicit security access rules
- QWeb templates cannot call Python functions - pass data structures only
- `report_action()` signature: Recordset as positional arg, NOT `docids=` keyword
- PostgreSQL table name limit: 63 characters

### Salary Rule Computation Order

- Rules execute in sequence order
- Rules referencing other rules MUST have higher sequence numbers
- Example: `LIQUID_NET` (seq 200) references `LIQUID_VACATION_PREPAID` (seq 195)
- Creating a rule doesn't automatically link it to structure - must be linked manually

### Module Upgrades and View Loading

**Problem:** Module upgrade doesn't always reload view changes from XML files
**Symptom:** New fields added to view XML file don't appear in UI after upgrade
**Diagnosis:**
- Check if view exists in database: `env.ref('module.view_id')` or search `ir.ui.view`
- Verify view arch_db contains your changes: `view.arch_db`
- If view exists but missing new fields → database view is stale

**Solution:** Force update view in database via Odoo shell
```python
# Update view arch_db directly
view = env['ir.ui.view'].browse(VIEW_ID)
correct_arch = '''<data>
    <!-- Your view inheritance XML here -->
</data>'''
view.write({'arch_db': correct_arch})
env.cr.commit()
```

**Important Notes:**
- View arch must have single root element (use `<data>` wrapper)
- Do NOT include XML declaration (`<?xml version...?>`)
- Must restart Odoo after updating: `docker restart odoo-dev-web`
- Users must hard-refresh browser: `Ctrl+Shift+R`

**Alternative:** Uninstall/reinstall module (more drastic, loses data)

---

## Module Versions

- **ueipab_payroll_enhancements:** v1.7.0
- **ueipab_hr_contract:** v1.4.0 (V2 contract fields added 2025-11-16)

---

## Git Status Reference

**Current Branch:** main
**Untracked Files:** Various test scripts in `/opt/odoo-dev/scripts/`

**Recent Commits:**
- Add Prestaciones Sociales Interest Report - Wizard and QWeb Implementation (v1.7.0)
- Liquidation Formula Complete Overhaul - Phases 2-4 + Interest Analysis
- Fix: Remove forbidden datetime imports from liquidation formulas
- Phase 9 COMPLETE: Final documentation - ALL 9 PHASES FINISHED! 🎉

---

## Quick Commands Reference

### Test Liquidation Formula in Testing Database
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py
```

### Restart Odoo (after module changes)
```bash
docker restart odoo-dev-web
```

### Clear Web Assets Cache (after view changes)
User must hard-reload browser: `Ctrl+Shift+R`

---

## Support & Feedback

For issues or questions about features documented here, refer to:
1. Detailed documentation files in `/opt/odoo-dev/documentation/`
2. Investigation scripts in `/opt/odoo-dev/scripts/`
3. Module code in `/mnt/extra-addons/ueipab_payroll_enhancements/`

---

**Document Size:** ~8.5k characters (reduced from 56.3k)
**Performance:** ✅ Optimized for fast loading
