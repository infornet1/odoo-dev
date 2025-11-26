# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-26 03:35 UTC

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

**V2 Antigüedad Validation Fix (2025-11-21):** 🔴 CRITICAL
- **Bug Fixed:** Invalid `previous_liquidation_date` causing overpayments
- **Problem:** Dates before contract start created negative "already paid" periods
- **Example:** SLIP/853 paid $195.08 instead of $100.40 ($94.68 overpayment - 94% error!)
- **Fix:** Added validation `if previous_liquidation and previous_liquidation >= contract.date_start:`
- **Impact:** Prevents 20.7% overpayment on affected liquidations
- **Compliance:** LOTTT Article 142(b) - no antiguedad for fictional periods

**V2 Vacation/Bono Fix (2025-11-17):**
- Fixed double deduction bug where NET was incorrectly $0.00
- New field: `ueipab_vacation_prepaid_amount` for actual prepaid amounts
- Formulas simplified: Calculate FULL period, deduct actual prepaid amount
- School year: Sep 1 - Aug 31; Aug 1 payments cover PAST year (Aug X-1 to Jul X)

📖 **[V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)**
📖 **[V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)**
📖 **[V2 Implementation Details](documentation/LIQUIDATION_V2_IMPLEMENTATION.md)** ⭐
📖 **[V2 Antigüedad Bug Analysis](documentation/LIQUIDATION_V2_FORMULA_BUGS_2025-11-21.md)** 🔴
📖 **[SLIP/854 Validation Report](documentation/SLIP854_VALIDATION_REPORT.md)** ✅
📖 **[V2 Vacation/Bono Fix Plan](documentation/VACATION_BONO_FIX_IMPLEMENTATION_PLAN.md)** ⭐

---

### 3. Prestaciones Sociales Interest Report
**Status:** ✅ PRODUCTION READY - Accrual Calculation | **Module:** `ueipab_payroll_enhancements` v1.22.0

**Key Features:**
- Month-by-month breakdown of prestaciones and interest (13% annual)
- V1 and V2 liquidation structure support
- Currency selection (USD/VEB) with historical exchange rates
- Single-page Portrait Letter layout

**✅ Accrual-Based Interest Calculation (v1.20.0 - 2025-11-18):**
- **CRITICAL FIX:** Corrected VEB interest calculation to use proper accrual accounting
- **Old (WRONG):** Re-converted accumulated USD total each month (Bs. 10,641.29 for SLIP/802)
- **New (CORRECT):** Sum of monthly interest conversions (Bs. 4,224.84 for SLIP/802)
- **Accounting Impact:** NONE - Company uses USD functional currency, ledger stays $86.58
- **Report Impact:** VEB display now economically accurate, matches Relación report

**✅ Exchange Rate Consistency Fix (v1.22.0 - 2025-11-18):**
- **CRITICAL FIX:** Ensured Prestaciones and Relación reports use IDENTICAL exchange rates
- **Old (WRONG):** Used Odoo's `_convert_currency()` which reads `rate` field (Bs. 4,160.85)
- **New (CORRECT):** Direct multiplication with `company_rate` field (Bs. 4,224.84)
- **Root Cause:** Odoo's `rate` field (1/0.0282 = 35.47) ≠ `company_rate` field (36.14)
- **Result:** PERFECT MATCH between both reports - zero employee confusion!

**Technical Details:**
- Each month's interest converted at that month's historical rate
- VEB amounts accumulate properly (not re-converting same USD)
- USD display unchanged: always shows payslip total ($86.58)
- Always uses accrual calculation (NO exchange rate override)
- Both reports use identical `_get_exchange_rate()` method with `company_rate`
- Consistent with Relación de Liquidación report

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
- **IVSS (SSO):** 4.5% monthly (prorated by days/30) - applies to Vacaciones, Bono Vacacional, Utilidades
- **FAOV:** 1.0% monthly (prorated by days/30) - applies to Vacaciones, Bono Vacacional, Utilidades
- **INCES (PARO):** 0.5% monthly (prorated by days/30) - **applies ONLY to Utilidades** ✅
- **ARI:** Variable % (from contract field, prorated by days/30) - applies to Vacaciones, Bono Vacacional, Utilidades
- **INCES (Payroll):** 0.25% monthly (prorated by days/30) - ⏸️ **DISABLED** pending legal confirmation

**⏸️ VE_INCES_DED_V2 Rule (2025-11-25) - PENDING LEGAL CONFIRMATION:**
- **Created in Testing:** Rule for 0.25% INCES deduction on `ueipab_salary_v2`
- **Formula:** `-(salary × 0.0025 × days/30)`
- **Status:** DISABLED - awaiting legal labor law confirmation
- **Example:** $285.39 salary × 0.25% × (15/30) = -$0.36
- **Action Required:** Confirm with legal before enabling in production

**✅ INCES Deduction Scope Fix (2025-11-18):**
- **Accounting Observation:** INCES should only apply to Utilidades (profit sharing)
- **Fix Applied:** Updated LIQUID_INCES_V2 formula to exclude Vacaciones and Bono Vacacional
- **Impact:** Employees were previously over-deducted by 0.5% on vacation benefits
- **Formula:** `deduction_base = (LIQUID_UTILIDADES_V2 or 0)` (removed vacation components)
- **Report Template:** Updated Relación de Liquidación report to show "INCES 0.5% sobre (Utilidades)"
- **Display:** Removed "/ PARO FORZOSO" suffix, simplified calculation formula

**Implementation Status:**
- ✅ Phase 1: Analysis & Planning
- ✅ Phase 2: V2 Contract Fields (`ueipab_hr_contract` v1.4.0)
- ✅ Phase 3: V2 Salary Structure (VE_PAYROLL_V2, 11 rules)
- ✅ Phase 4: Bulk Contract Migration (44/44 employees)
- ✅ Phase 5: V2 Testing & Validation (97.7% accuracy)
- ✅ AGUINALDOS V2 Migration (2025-11-21): Updated formula to use `ueipab_salary_v2`

📖 **[Complete V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)**
📖 **[V2 Implementation Reference](documentation/V2_PAYROLL_IMPLEMENTATION.md)** ⭐
📖 **[AGUINALDOS V2 Migration](documentation/AGUINALDOS_V2_MIGRATION.md)** ✅

---

### 5. Relación de Liquidación Report (Breakdown Report)
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.25.4

**📋 Enhancement In Review:** Hide Vacaciones/Bono when fully prepaid - see [Plan](documentation/HIDE_PREPAID_VACATION_ENHANCEMENT.md)

**Key Features:**
- Detailed breakdown of all 6 liquidation benefits with formulas
- Step-by-step deduction calculations
- Legal declaration and signature sections
- Single-page Portrait Letter layout
- V1 and V2 structure support

**✅ Exchange Rate Override (v1.19.0 - 2025-11-17, Enhanced v1.26.0 - 2025-11-21):**
- **Automatic Latest Rate (NEW - v1.26.0):** VEB reports now default to latest available exchange rate in system (not payslip date)
- **3-Priority System:** (1) Custom rate → (2) Custom date → (3) Latest available (auto)
- **Example Impact:** SLIP/854 payslip date Oct 28 (218.17) vs latest Nov 21 (241.58) = +10.73%
- **Unified Footer:** All scenarios display "Tasa de cambio: XXX VEB/USD (Tasa del DD/MM/YYYY)"
- Custom rate entry (e.g., 300.00 for manual override)
- Rate date selector for automatic lookup (e.g., Nov 17 → 236.4601)
- Supports cash flow delays (compute Jul 31 @ 124.51, pay Nov 17 @ 236.46)
- **Tested:** All 3 priority scenarios validated with SLIP/854 ✅

**✅ Number Formatting (v1.19.1-1.19.2 - 2025-11-17):**
- Thousand separators for all amounts (33,560.78 instead of 33560.78)
- Applied to benefits, deductions, totals, declaration, and notes sections
- Improved readability for large VEB amounts (e.g., Bs. 283,972.03) ✅

**✅ Formula Currency Display (v1.19.3 - 2025-11-17):**
- Calculation formulas now show amounts in selected currency
- Example: `(23.30/12) × 15 días × $4.87` becomes `(23.30/12) × 15 días × Bs.1,151.56` when VEB selected
- Applied to all benefit calculations, deduction bases, and detail columns
- Daily salaries converted: $4.87 → Bs.1,151.56 (at 236.46 rate) ✅

**✅ Salary Header Display (v1.19.4 - 2025-11-17):**
- Employee header now shows "Salario:" field (ueipab_salary_v2)
- Automatically converts to selected currency
- Example: $146.19 → Bs. 34,568.10 (at 236.46 rate)
- Formatted with thousand separators ✅

**✅ Header Layout Optimization (v1.19.5-1.19.8 - 2025-11-17):**
- Moved "Fecha Liquidación" to report title area (more prominent)
- All employee header rows now perfectly aligned (4 columns @ 25% each)
- Row 1: Empleado | Cédula
- Row 2: Salario | Fecha Ingreso
- Row 3: Período Servicio | Antigüedad Total
- Title shows: "RELACIÓN DE LIQUIDACIÓN / Fecha Liquidación: 31/07/2025"
- Consistent structure, professional appearance ✅

**✅ Payslip Number in Header (v1.24.0 - 2025-11-18):**
- Added payslip number to report header for easy reference
- Format: "Nro: SLIP/802 │ Fecha Liquidación: 31/07/2025"
- Benefits: Easy traceability, professional appearance, links to system record
- Employee can quickly cite the payslip number when needed

**✅ Accrual-Based Interest Calculation (v1.20.0 - 2025-11-18):**
- **CRITICAL FIX:** "Intereses sobre Prestaciones" now uses accrual-based calculation
- **Matches Prestaciones Interest Report:** Both reports show same VEB amount
- **Calculation:** Sum of monthly interest conversions (not single-rate conversion)
- **Example (SLIP/802):** Bs. 4,224.84 (accrual) vs Bs. 10,780.09 (old single-rate)
- **Exchange Rate Override Behavior:** Interest IGNORES override (always uses accrual)
- **Rationale:** Interest accumulated over 23 months, different from other benefits
- **Zero Employee Confusion:** Both reports ALWAYS consistent regardless of override

**✅ Interest Formula Display Improvement (v1.21.0 - 2025-11-18):**
- **Problem Fixed:** Misleading calculation formula removed (showed Bs.162,206.90 × 50% × 13% × (23.30/12) implying Bs. 20,471.86, but actual was Bs. 4,224.84)
- **New Calculation Display:** "Acumulación mensual (23 meses) - Ver reporte 'Prestaciones Soc. Intereses'"
- **New Detail Column:** "Ver reporte 'Prestaciones Soc. Intereses'" (directs employee to detailed breakdown)
- **Employee Experience:** Clear reference to supporting documentation, no confusing arithmetic
- **Professional:** Shows complete documentation approach, verifiable by employee

**✅ XLSX Export Exchange Rate Bug Fix (v1.25.2 - 2025-11-19):**
- **CRITICAL FIX:** XLSX export now correctly uses wizard's exchange rate parameters
- **Bug:** XLSX was using payslip date rate (124.51) instead of wizard's rate_date (236.46)
- **Impact:** XLSX showed Bs. 114,497.09 vs PDF Bs. 217,443.98 (1.90x discrepancy)
- **Root Cause:** Controller wasn't passing `data` dict with `rate_date`, `use_custom_rate`, `custom_exchange_rate`
- **Fix:** Updated `/controllers/liquidacion_breakdown_xlsx.py:115-129` to pass wizard parameters
- **Result:** Perfect parity - both PDF and XLSX now show identical amounts
- **Technical:** Fixed permissions (755) on controllers directory for proper module loading

**✅ Antigüedad Display Fix (v1.25.3 - 2025-11-20):**
- **BUG FIX:** "Antigüedad Total" now displays for ALL employees, not just re-hires
- **Problem:** Field was hidden when `original_hire_date` = `contract.date_start` (e.g., SLIP/801)
- **Old Logic:** Only showed antiguedad if employee had different hire dates (indicating re-hire)
- **New Logic:** Always shows "Antigüedad Total" if `original_hire_date` exists
- **Enhancement:** Parenthetical note "(desde [date])" only shows if dates differ
- **Result:** Consistent display - all liquidation reports now show employee seniority
- **Example:** SLIP/801 now shows "Antigüedad Total: 1.03 años" (was blank before)

**✅ XLSX Layout Consistency Fix (v1.25.4 - 2025-11-20):**
- **BUG FIX:** XLSX export now matches PDF layout exactly
- **Missing Fields Added:**
  - **Salario:** Now shown in employee header (Row 2)
  - **Antigüedad Total:** Now shown with same logic as PDF (Row 3)
  - **Payslip Number:** Added to report title (Nro: SLIP/XXX)
  - **Rate Source:** Exchange rate note now shows source (Personalizada/Automática/Tasa del DD/MM/YYYY)
- **Layout Changes:**
  - Converted employee info from vertical list to 2x4 grid (matching PDF)
  - Row 1: Empleado | Cédula
  - Row 2: Salario | Fecha Ingreso
  - Row 3: Período Servicio | Antigüedad Total
- **Result:** Perfect PDF/XLSX parity - both reports show identical information
- **Files Changed:** `controllers/liquidacion_breakdown_xlsx.py` (lines 143-180, 289)

📖 **[Development Journey](documentation/RELACION_BREAKDOWN_REPORT.md)** ⭐
📖 **[Exchange Rate Override Design](documentation/EXCHANGE_RATE_OVERRIDE_FEATURE.md)** ✅

---

### 6. Payslip Email Delivery System
**Status:** ✅ PRODUCTION READY | **Module:** `hr_payslip_monthly_report` v17.0.1.2 (Cybrosys + Custom Fix)

**Migration:** Custom Phase 2 email system decommissioned (v1.28.0 → v1.29.0) and replaced with professional Cybrosys module.

**✅ Send Mail Button Fix (v17.0.1.2 - 2025-11-22):**
- **Bug Fixed:** "Send Mail" button disappeared permanently if user cancelled email wizard
- **Solution:** Added "Reset Send Status" button for easy recovery
- **Impact:** Users can now retry sending emails after cancelling wizard
- **Technical:** Avoided complex mail composer overrides that caused transaction errors

**Key Features:**
- **Automatic Email on Confirmation:** Sends payslip PDF via email when payslip is confirmed
- **Manual Send Button:** "Send Email" button on payslip form for manual sending
- **Mass Confirm Wizard:** Bulk confirm multiple payslips (with auto-email if enabled)
- **Email Template:** Professional template with payslip PDF attachment

**Configuration:**
1. Navigate to **Settings > Payroll**
2. Enable **"Automatic Send Payslip By Mail"** checkbox
3. Save settings

**Usage:**

**Automatic Send (Recommended):**
1. Enable auto-send in Payroll settings
2. Confirm payslip normally via "Confirm" button
3. Email automatically sent to `employee.private_email`
4. Payslip marked with `is_send_mail = True`

**Manual Send:**
1. Open any payslip (draft or confirmed)
2. Click "Send Mail" button
3. Compose email window opens with template pre-loaded
4. Modify message if needed, click "Send"
5. If you cancel: Click "Reset Send Status" button to show "Send Mail" again

**Mass Confirm:**
1. Navigate to **Payroll > Payslips**
2. Select multiple payslips in list view (checkboxes)
3. Click **Actions > Mass Confirm Payslip**
4. All selected payslips confirmed (emails sent if auto-send enabled)

**Email Details:**
- **Template:** "Monthly Payslip Email"
- **Subject:** `Ref SLIP/XXX` (e.g., "Ref SLIP/944")
- **Body:** Simple message with PDF attachment
- **Attachment:** Standard Odoo payslip report PDF
- **Recipient:** Employee's `private_email` field

**⚠️ Important Notes:**
- Ensure employees have `private_email` set in their employee records
- SMTP must be configured (Settings > Technical > Outgoing Mail Servers)
- Auto-send is currently **ENABLED** in testing database
- Email sending requires valid email configuration

**Archive (Custom Phase 2 System):**
- Git tag: `v1.28.0-phase2-final` (preserves Phase 2 custom implementation)
- Documentation: [Decommission Plan](documentation/PHASE2_EMAIL_DECOMMISSION_PLAN.md)
- Technical guide: [Email Delivery System](documentation/PAYSLIP_EMAIL_DELIVERY_SYSTEM.md) (archived)

📖 **[Send Mail Button Fix - Final Solution](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md)** ⭐
📖 **[Bug Diagnosis](documentation/SEND_MAIL_BUTTON_BUG_DIAGNOSIS.md)**

---

### 7. Payslip Batch Email Template Selector
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.33.0 (2025-11-24)

**Smart template selector** for batch payslip emails with 3 beautiful HTML templates.

**Key Features:**
- **Template dropdown** on batch form view
- **Auto-default** to "Payslip Compact Report"
- **QWeb syntax** for proper email rendering
- **Inline styles** for email client compatibility
- **Sent count tracking** in batch message log

**Available Templates:**

1. **Payslip Compact Report** (Default)
   - Simple professional text email
   - PDF attachment with full details
   - Purple/blue color scheme
   - Best for: Regular payroll with archiving

2. **Payslip Email - Employee Delivery**
   - Beautiful HTML with gradient headers
   - Full salary + deductions breakdown tables
   - Purple gradient design
   - Exchange rate display
   - Best for: Monthly detailed employee view

3. **Aguinaldos Email - Christmas Bonus Delivery** 🎄
   - Christmas-themed (red/green gradient)
   - Aguinaldos explanation box
   - Shows only bonus amount (no deductions)
   - "¡Felices Fiestas!" footer
   - Best for: December Christmas bonuses

**Usage:**
1. Open payslip batch form
2. Select template from **"Email Template"** dropdown
3. Click **"Send Payslips by Email"** button
4. All employees receive emails using selected template

**Technical Implementation:**
- Field: `email_template_id` (Many2one to mail.template)
- Domain: `[('model', '=', 'hr.payslip')]`
- Method: `action_send_batch_emails()` uses selected template
- Syntax: Jinja2 for headers, QWeb for body_html

**Email Syntax Rules (Critical):**
```python
# Headers (subject, email_from, email_to, email_cc)
subject = "💰 Comprobante │ {{object.number}}"  # Jinja2

# Body (body_html)
<div>
    <p>Estimado/a <strong t-out="object.employee_id.name"/>,</p>  # QWeb
</div>
```

**Version History:**
- **v1.34.0:** Fixed batch fields display (2025-11-24) - see below
- **v1.33.0:** Added template selector with 3 templates (2025-11-24)
- Fixed "Payslip Compact Report" QWeb syntax
- Fixed "Aguinaldos Email" with Christmas theme
- Removed deductions section from Aguinaldos (not applicable)

**✅ Batch Fields Fix (v1.34.0 - 2025-11-24):**
- **Bug Fixed:** `total_net_amount` and `exchange_rate` not displaying on batch form
- **Root Cause 1:** `total_net_amount` computed field only looked for `code == 'NET'`, but V2 payslips use `VE_NET_V2`
- **Root Cause 2:** `exchange_rate` was a simple field with default 1.0, not auto-populated from VEB rates
- **Fix 1:** Updated filter to `l.code in ('NET', 'VE_NET_V2')` to support both V1 and V2 payroll
- **Fix 2:** Changed `exchange_rate` to computed field that auto-populates from latest VEB rate for batch end date
- **Result:** Batch 120 now shows $7,340.09 total and 243.1105 VEB/USD exchange rate
- **Note:** Existing batches required one-time recomputation; new batches auto-populate

---

### 8. Comprobante de Pago (Compacto) Report
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.41.0

**Key Features:**
- Single-page compact payslip with currency conversion
- VEB/USD currency selector with exchange rate options
- Consolidated earnings display (Salary + Bonos)
- Professional deduction breakdown with friendly names

**✅ ARI Deduction Display Enhancement (v1.41.0 - 2025-11-26):**
- **Before:** `VE_ARI_DED_V2 - ARI Variable %`
- **After:** `Retención impuestos AR-I X%` (shows actual rate from contract)
- **Source:** Reads `ueipab_ari_withholding_rate` from employee's contract
- **Example:** Employee with 3% ARI → `Retención impuestos AR-I 3%`

**Deduction Display Names:**
| Code | Display Name |
|------|--------------|
| VE_SSO_DED_V2 | Seguro Social Obligatorio 4.5% |
| VE_FAOV_DED_V2 | Política Habiltacional BANAVIH 1% |
| VE_PARO_DED_V2 | Seguro Social Paro Forzoso 0.5% |
| VE_ARI_DED_V2 | Retención impuestos AR-I X% |

**✅ Payslip Exchange Rate Priority (v1.40.0 - 2025-11-25):**
- **NEW DEFAULT:** When VEB is selected, report now uses payslip's `exchange_rate_used` field
- **Priority Order:**
  1. Custom rate (wizard) → "Tasa personalizada"
  2. Rate date lookup (wizard) → "Tasa del DD/MM/YYYY"
  3. **Payslip's `exchange_rate_used`** → "Tasa de nómina (DD/MM/YYYY)"
  4. Latest available rate (fallback) → "Tasa automática"
- **Benefit:** Report shows same rate used when payslip was generated
- **Use Case:** Employee receives report with exact rate from their batch

---

### 9. Acuerdo Finiquito Laboral (Labor Settlement Agreement)
**Status:** ✅ PRODUCTION READY | **Module:** `ueipab_payroll_enhancements` v1.25.1

**Key Features:**
- Formal legal settlement document (4 legal sections)
- PDF and DOCX export formats
- Dynamic placeholders (name, dates, amounts)
- Professional signature section
- V1 and V2 liquidation support
- Exchange rate override support (matches Relación report)

**✅ Rate Date Fix (v1.25.1 - 2025-11-18 TESTED):**
- **BUG FIX:** Report model now correctly handles `rate_date` parameter
- **Problem:** v1.25.0 added wizard UI fields but report ignored `rate_date`
- **Symptom:** Selecting "Rate Date (Auto Lookup)" as 11/17/2025 still showed old rate (Bs. 158,294.80)
- **Solution:** Added date conversion logic and lookup in report model `finiquito_report.py`
- **Test Result:** SLIP/803 with rate_date=11/17/2025 now shows Bs. 300,621.18 ✅
- **Behavior:** If `rate_date` provided, uses that date for automatic rate lookup instead of payslip date

**✅ Exchange Rate Override UI (v1.25.0 - 2025-11-18):**
- Added exchange rate override fields to wizard UI
- 3 fields: `use_custom_rate`, `custom_exchange_rate`, `rate_date`
- UI matches Relación wizard (Exchange Rate Options section with alert)
- Perfect consistency across all 3 liquidation reports

**Version History:**
- **v1.25.1:** Fixed rate_date parameter handling in report model (2025-11-18) ✅
- **v1.25.0:** Added exchange rate override wizard UI fields (2025-11-18)
- **v1.23.0:** Added exchange rate override report support (2025-11-18)
- **v1.18.2:** Added DOCX export with python-docx library
- **v1.18.1:** Updated legal representative name
- **v1.18.0:** Initial release with PDF export

📖 **[Implementation Details](documentation/FINIQUITO_REPORT.md)** ⭐

---

### 10. AR-I Portal (Employee Self-Service)
**Status:** ✅ INSTALLED IN TESTING | **Module:** `ueipab_ari_portal` v17.0.1.0.0 (2025-11-26)

**Purpose:** Employee self-service portal for AR-I (Agente de Retención - Impuesto sobre la Renta) tax withholding declarations as required by Venezuelan law (SENIAT Decreto 1.808).

**Key Features:**
- **Employee Portal:** Self-service AR-I declaration submission at `/my/ari`
- **Tax Calculation:** Automatic ISLR progressive rate calculation (6% to 34%)
- **Desgravamen Options:** Único (774 UT fixed) or Detallado (itemized)
- **Family Dependents:** Cargas familiares (spouse, children, parents)
- **Excel Export:** Official SENIAT template filled via openpyxl
- **HR Approval Workflow:** Draft → Submitted → Approved/Rejected
- **Email Notifications:** Deadline reminders, submission alerts, approval/rejection
- **Quarterly Deadlines:** Jan 15, Mar 15, Jun 15, Sep 15, Dec 15

**Tax Calculation Example (ARI/2025/0001):**
```
Annual Income: 50,000.00 (5,555.56 UT @ 9.00 Bs/UT)
Desgravamen Único: 774.00 UT
Taxable Income: 4,781.56 UT
Estimated Tax: 811.65 UT
Personal Rebate: 10.00 UT
Tax to Withhold: 801.65 UT
★ Withholding %: 14.43%
```

**Portal Access:**
- **URL:** `/my/ari` (employee self-service)
- **Requirement:** User must have linked employee record (`employee.user_id`)
- **Backend:** Payroll → AR-I Declarations (HR management)

**Security Groups:**
- **AR-I Manager:** Full access to all declarations
- **AR-I User:** Access to own declarations only
- **HR Manager:** Full read/write access
- **HR User:** Read-only access

**Module Structure:**
```
ueipab_ari_portal/
├── models/
│   ├── hr_employee_ari.py    # Main AR-I model (81 fields)
│   ├── ari_excel_generator.py # SENIAT template filler
│   └── hr_contract.py        # Contract extension
├── controllers/
│   └── portal.py             # Portal routes
├── views/
│   ├── hr_employee_ari_views.xml
│   ├── portal_templates.xml
│   └── portal_menu.xml
├── wizard/
│   └── ari_reject_wizard.py
├── security/
│   ├── ari_security.xml
│   └── ir.model.access.csv
├── data/
│   ├── ari_cron.xml          # Deadline reminder cron
│   └── mail_templates.xml    # 4 email templates
└── static/
    └── templates/ARI SENIAT FORMATO.xlsx
```

**Dependencies:**
- `hr`, `hr_contract`, `portal`, `mail`, `ueipab_hr_contract`
- `openpyxl` (pip install in container for Excel generation)

**⚠️ Important Notes:**
- Employee must be linked to portal user (`hr.employee.user_id`)
- `openpyxl` must be installed in Docker container
- Portal card appears in "Common" section alongside "Connection & Security"

---

## Key Technical Learnings

### Accrual-Based Currency Conversion (2025-11-18)
**Problem:** Converting accumulated amounts month-by-month causes incorrect results
```python
# ❌ WRONG - Re-converts total accumulated USD each month
accumulated_usd = 0.0
for month in months:
    accumulated_usd += month_amount_usd
    accumulated_veb = convert(accumulated_usd, month_rate)  # WRONG!
# Result: Earlier months get converted multiple times with different rates

# ✅ CORRECT - Convert each month's amount once, accumulate VEB
accumulated_veb = 0.0
for month in months:
    month_veb = convert(month_amount_usd, month_rate)
    accumulated_veb += month_veb  # Proper accrual accounting
# Result: Each month's amount converted once at its own rate
```

**Impact:** SLIP/802 interest changed from Bs. 10,641.29 (wrong) to Bs. 4,160.85 (correct)

### Exchange Rate Override for Interest (2025-11-18)
**Decision:** Interest calculation should IGNORE exchange rate override

**Rationale:**
- Interest accumulated over 23 months at historical rates
- Different from other benefits (computed once at liquidation)
- Prestaciones Interest Report shows detailed monthly breakdown
- Both reports must match for employee understanding

```python
# ❌ WRONG - Interest uses override rate
if use_custom and custom_rate:
    return intereses_total * custom_rate  # Simple conversion

# ✅ CORRECT - Interest always uses accrual (ignores override)
# Always calculate month-by-month regardless of override
for month in service_period:
    month_interest_veb = convert(month_interest_usd, month_historical_rate)
    accumulated_veb += month_interest_veb
return accumulated_veb  # Accrual-based, consistent with Prestaciones report
```

**Impact:** Ensures report consistency even when override rate is used for other benefits

### Container Issues & Fixes (2025-11-19)

**Issue 1: Empty Database Log Pollution**
```
Problem: Database "ueipab" exists but not initialized
Symptom: ERROR every 60s - "relation ir_module_module does not exist"
Impact:  ~60 log errors per hour (cosmetic, no functional issues)
Fix:     DROP DATABASE ueipab;
```

**Issue 2: WebSocket Port Mismatch**
```
Problem: Config uses deprecated longpolling_port = 8078, Docker maps 8072
Symptom: RuntimeError every 30s - "Couldn't bind websocket on port 8078"
Impact:  Real-time features broken (chat, notifications), ~120 errors/hour
Fix:     Update config: longpolling_port = 8078 → gevent_port = 8072
```

**Root Causes:**
1. **Empty DB**: Orphaned database created but never initialized with Odoo
2. **WebSocket**: Using deprecated parameter + port not mapped in Docker

**Combined Fix Applied (2025-11-19):**
- Dropped empty `ueipab` database
- Updated to `gevent_port = 8072` (Odoo 17 standard)
- Ensured `workers = 2` set (required for websocket)
- Single restart applied both fixes
- Result: ~180 fewer errors per hour + real-time features working

📖 **[Complete Diagnosis & Procedure](documentation/COMBINED_FIX_PROCEDURE.md)**

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

- **ueipab_payroll_enhancements:** v1.41.0 (Compact report ARI display enhancement - 2025-11-26)
- **ueipab_hr_contract:** v17.0.2.0.0 (V2 fields only - V1 fields removed - 2025-11-24)
- **ueipab_ari_portal:** v17.0.1.0.0 (NEW - Employee AR-I self-service portal - 2025-11-26)

---

## Production Migration Status (2025-11-25)

### ✅ Salary Structure Assignment Complete (2025-11-25)
- All 44 production contracts assigned to "Salarios Venezuela UEIPAB V2" (struct_id)
- All 46 testing contracts assigned to same structure
- View `hr_payroll_community.hr_contract_view_form` activated in testing (was inactive)

### ✅ ARI Rate Comparison (2025-11-25)
- Compared ARI rates between Google Spreadsheet (15nov2025 tab) and Odoo production
- **Result:** 43/44 employees match, 1 discrepancy found
- **Discrepancy:** ARCIDES ARZOLA (V8478634) - Spreadsheet: 3%, Odoo: 1%

### ✅ V1 to V2 Contract Field Migration Complete

**V1 Fields Removed (both environments):**
- `ueipab_salary_base`, `ueipab_bonus_regular`, `ueipab_extra_bonus`
- `ueipab_deduction_base`, `ueipab_monthly_salary`, `ueipab_salary_notes`

**V2 Fields Active (both environments):**
- `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `cesta_ticket_usd`
- `ueipab_ari_withholding_rate`, `ueipab_ari_last_update`
- `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`
- `ueipab_vacation_paid_until`, `ueipab_vacation_prepaid_amount`

### ✅ Contract Synchronization Complete

| Environment | Running Contracts |
|-------------|------------------|
| Testing | 46 |
| Production | 44 |

**Synced to Production:**
- 44 contracts with V2 fields synchronized
- All employees with `department_id` and valid VAT included
- Last sync: 2025-11-24

**Remaining Differences (2):**
- `V12345678` - Gustavo Perdomo (test VAT - needs real cédula)
- `V30597749` - MARIA JIMENEZ (no department_id set)

### ✅ User Permissions Cleanup (2025-11-24)

**47 users had the following rights REMOVED:**

| Category | Groups Removed |
|----------|----------------|
| **Payroll** | Manager, Officer |
| **Contratos** | Administrador, Gerente del empleado |
| **Ventas** | Administrador, Usuario (all levels) |
| **Sitio web** | Editor restringido, Editor y diseñador |
| **Empleados** | Administrador, Encargado |
| **Reclutamiento** | Administrador, Encargado, Entrevistador |
| **Marketing por correo** | Usuario |
| **Encuestas** | Administrador, Usuario |
| **Administración** | Ajustes, Permisos de acceso |

**Users affected:** All regular employees (teachers, admin staff) now have minimal access rights.

### Production Environment Details

```
Server: 10.124.0.3
Container: ueipab17
Database: DB_UEIPAB
SSH: root (password in secure docs)
```

---

## Additional Documentation

### Legal & Compliance
- [LOTTT Law Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)
- [Liquidation Clarifications](documentation/LIQUIDATION_CLARIFICATIONS.md)

### Technical Analysis
- [Liquidation Approach Analysis](documentation/LIQUIDATION_APPROACH_ANALYSIS.md)
- [Monica Mosqueda Analysis](documentation/MONICA_MOSQUEDA_ANALYSIS_2025-11-13.md)
- [Liquidation Validation Summary](documentation/LIQUIDATION_VALIDATION_SUMMARY_2025-11-13.md)

### Infrastructure & Troubleshooting (2025-11-19)
- [Empty Database Issue Diagnosis](documentation/UEIPAB_EMPTY_DATABASE_ISSUE_DIAGNOSIS.md)
- [WebSocket Configuration Issue](documentation/WEBSOCKET_ISSUE_DIAGNOSIS.md)
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md) ⭐

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
