# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-14

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
**Last Updated:** 2025-11-12
**Module:** `ueipab_payroll_enhancements`

**Quick Summary:**
- Report showing employee payroll disbursement details with deduction breakdown
- Fixed ARI TAX and Social Security columns to use correct salary rule codes
- Added individual deduction columns: ARI, SSO 4%, FAOV 1%, PARO 0.5%
- 9% tax calculation on Net Payable (USD and VEB)
- Landscape Letter format with optimized layout

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

---

## Module Versions

- **ueipab_payroll_enhancements:** v1.7.0
- **ueipab_hr_contract:** v1.3.0

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
