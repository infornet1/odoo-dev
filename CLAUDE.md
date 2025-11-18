# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-17 02:55 UTC

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

---

## Active Features & Quick Reference

### 1. Payroll Disbursement Detail Report
**Status:** ✅ Production Ready | **Module:** `ueipab_payroll_enhancements`

**Key Features:**
- 70/30 Salary/Bonus split for accounting transparency
- Currency selector (USD/VEB) with exchange rates
- Individual deduction columns (ARI, SSO, FAOV, PARO)
- Excel export capability

📖 **[Complete Documentation](documentation/PAYROLL_DISBURSEMENT_REPORT.md)**

---

### 2. Venezuelan Liquidation System
**Status:** ✅ V1 & V2 PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` + `ueipab_hr_contract`

**Quick V1 vs V2:**

| Aspect | V1 (Legacy) | V2 (New) |
|--------|-------------|----------|
| **Structure Code** | LIQUID_VE | LIQUID_VE_V2 |
| **Salary Field** | `ueipab_deduction_base` | `ueipab_salary_v2` |
| **Accounting** | 5.1.01.10.002 | 5.1.01.10.010 |
| **Status** | Production (Active) | Production Ready (Tested) |

**Key Contract Fields:**
```python
# V2 Fields (New)
contract.ueipab_salary_v2              # Direct salary subject to deductions
contract.ueipab_original_hire_date     # Original hire date (for antiguedad)
contract.ueipab_previous_liquidation_date  # Last full liquidation
contract.ueipab_vacation_paid_until    # Last vacation payment date (tracking only)
contract.ueipab_vacation_prepaid_amount    # Total prepaid vacation/bono amount
```

**V2 Vacation/Bono Fix (2025-11-17):**
- Fixed double deduction bug where NET was incorrectly $0.00
- New field: `ueipab_vacation_prepaid_amount` for actual prepaid amounts
- Formulas simplified: Calculate FULL period, deduct actual prepaid amount
- School year: Sep 1 - Aug 31; Aug 1 payments cover PAST year (Aug X-1 to Jul X)

📖 **[V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)**
📖 **[V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)**
📖 **[V2 Implementation Details](documentation/LIQUIDATION_V2_IMPLEMENTATION.md)** ⭐
📖 **[V2 Vacation/Bono Fix Plan](documentation/VACATION_BONO_FIX_IMPLEMENTATION_PLAN.md)** ⭐

---

### 3. Prestaciones Sociales Interest Report
**Status:** ✅ Production Ready - V2 Support | **Module:** `ueipab_payroll_enhancements` v1.17.0

**Key Features:**
- Month-by-month breakdown of prestaciones and interest (13% annual)
- V1 and V2 liquidation structure support
- Currency selection (USD/VEB) with historical exchange rates
- Single-page Portrait Letter layout

📖 **[Complete Documentation](documentation/PRESTACIONES_INTEREST_REPORT.md)**
📖 **[Wizard-Based Report Pattern](documentation/WIZARD_BASED_REPORT_PATTERN.md)**

---

### 4. Venezuelan Payroll V2 Revision Plan
**Status:** ✅ PHASE 5 COMPLETE - PRODUCTION READY | **Type:** System Redesign

**Purpose:** Migrate from percentage-based V1 to direct-amount V2 model

**V2 Design (NO Percentages):**
```python
# Store direct HR-approved amounts in contract
contract.ueipab_salary_v2       = $119.21  # Subject to deductions
contract.ueipab_extrabonus_v2   = $42.58   # NOT subject to deductions
contract.ueipab_bonus_v2        = $198.83  # NOT subject to deductions
contract.cesta_ticket_usd       = $40.00   # Food allowance (existing field)
```

**Deduction Rates (Monthly with Proration):**
- **IVSS (SSO):** 4.5% monthly (prorated by days/30)
- **FAOV:** 1.0% monthly (prorated by days/30)
- **INCES (PARO):** 0.5% monthly (prorated by days/30)
- **ARI:** Variable % (from contract field, prorated by days/30)

**Implementation Status:**
- ✅ Phase 1: Analysis & Planning
- ✅ Phase 2: V2 Contract Fields (`ueipab_hr_contract` v1.4.0)
- ✅ Phase 3: V2 Salary Structure (VE_PAYROLL_V2, 11 rules)
- ✅ Phase 4: Bulk Contract Migration (44/44 employees)
- ✅ Phase 5: V2 Testing & Validation (97.7% accuracy)

📖 **[Complete V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)**
📖 **[V2 Implementation Reference](documentation/V2_PAYROLL_IMPLEMENTATION.md)** ⭐

---

### 5. Relación de Liquidación Report (Breakdown Report)
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.15.0

**Key Features:**
- Detailed breakdown of all 6 liquidation benefits with formulas
- Step-by-step deduction calculations
- Legal declaration and signature sections
- Single-page Portrait Letter layout
- V1 and V2 structure support

📖 **[Development Journey](documentation/RELACION_BREAKDOWN_REPORT.md)** ⭐

---

### 6. Acuerdo Finiquito Laboral (Labor Settlement Agreement)
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.18.2

**Key Features:**
- Formal legal settlement document (4 legal sections)
- PDF and DOCX export formats
- Dynamic placeholders (name, dates, amounts)
- Professional signature section
- V1 and V2 liquidation support

**Version History:**
- **v1.18.2:** Added DOCX export with python-docx library
- **v1.18.1:** Updated legal representative name
- **v1.18.0:** Initial release with PDF export

📖 **[Implementation Details](documentation/FINIQUITO_REPORT.md)** ⭐

---

## Key Technical Learnings

### Odoo safe_eval Restrictions (Salary Rules)
```python
# ❌ FORBIDDEN in safe_eval:
from datetime import timedelta  # NO import statements
hasattr(contract, 'field')      # NO hasattr()

# ✅ ALLOWED in safe_eval:
(date1 - date2).days            # Direct date arithmetic
try:                            # Try/except for optional fields
    value = contract.field or False
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

### Report Development Patterns
- Use `web.basic_layout` for reports without headers/footers (UTF-8 support)
- Report model naming: `report.<module>.<template_id>` (exact match required)
- TransientModel wizards require explicit security access rules
- QWeb templates: Pass data structures only (NO Python function calls)

### Form View UX - Notebook Pages
**Best Practice:** Organize complex forms with logical notebook pages

```xml
<page name="information" position="after">
    <page string="💼 Category Name" name="category_slug">
        <group string="Section Title">
            <group>
                <field name="field1"/>
                <field name="field2"/>
            </group>
        </group>
    </page>
</page>
```

**Contract Form Example:**
- 💼 Salary Breakdown - V2 compensation fields
- 💰 Salary Tax Breakdown - Tax withholding
- 📋 Salary Liquidation - Historical tracking
- ⚙️ Salary Parameters - Payroll schedule

---

## Module Versions

- **ueipab_payroll_enhancements:** v1.18.2 (Finiquito DOCX export - 2025-11-17)
- **ueipab_hr_contract:** v1.5.0 (V2 vacation prepaid amount field - 2025-11-17)

---

## Additional Documentation

### Legal & Compliance
- [LOTTT Law Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)
- [Liquidation Clarifications](documentation/LIQUIDATION_CLARIFICATIONS.md)

### Technical Analysis
- [Liquidation Approach Analysis](documentation/LIQUIDATION_APPROACH_ANALYSIS.md)
- [Monica Mosqueda Analysis](documentation/MONICA_MOSQUEDA_ANALYSIS_2025-11-13.md)
- [Liquidation Validation Summary](documentation/LIQUIDATION_VALIDATION_SUMMARY_2025-11-13.md)

---

## Quick Commands Reference

### Test Scripts in Testing Database
```bash
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py
```

### Restart Odoo (after module changes)
```bash
docker restart odoo-dev-web
```

### Clear Web Assets Cache
User must hard-reload browser: `Ctrl+Shift+R`

---

## Support & Feedback

For detailed information, refer to:
1. Documentation files in `/opt/odoo-dev/documentation/`
2. Investigation scripts in `/opt/odoo-dev/scripts/`
3. Module code in `/mnt/extra-addons/ueipab_payroll_enhancements/`

---

**Document Size:** ~6.5k characters (was 47.5k - 86% reduction)
**Performance:** ✅ Optimized for fast loading
