# Compact Payslip Report - Blank PDF Diagnosis

**Date:** 2025-11-22
**Issue:** PDF generates blank despite all fixes applied
**Status:** Awaiting user review before changes

---

## CONFIRMED WORKING ✅

### 1. Wizard Data Preparation
**File:** `wizard/payslip_compact_wizard.py:103-122`

```python
def action_generate_report(self):
    # Prepares data dict
    data = {
        'payslip_ids': self.payslip_ids.ids,  # ✅ PLURAL - correct
        'currency_id': self.currency_id.id,
        'use_custom_rate': self.use_custom_rate,
        'custom_exchange_rate': self.custom_exchange_rate,
        'rate_date': self.rate_date.isoformat() if self.rate_date else False,
    }

    # Returns report action
    report = self.env.ref('ueipab_payroll_enhancements.action_report_payslip_compact')
    return report.report_action(docids=self.payslip_ids.ids, data=data)  # ✅ Uses docids= parameter
```

**Status:** ✅ CORRECT - Matches working Liquidación pattern exactly

---

### 2. Report Model Data Reception
**File:** `models/payslip_compact_report.py:19-35`

```python
@api.model
def _get_report_values(self, docids, data=None):
    # Get payslip IDs from data dict (matching Liquidación pattern)
    payslip_ids = data.get('payslip_ids', []) if data else []  # ✅ PLURAL - correct

    if not payslip_ids and docids:
        payslip_ids = docids

    payslips = self.env['hr.payslip'].browse(payslip_ids)
```

**Status:** ✅ CORRECT - Now matches Liquidación pattern (was broken, fixed)

---

### 3. Report Data Generation
**Test Output:**
```
=== REPORT RESULT ===
Keys in result: ['doc_ids', 'doc_model', 'docs', 'data', 'currency', 'reports']

doc_ids: [2]
doc_model: hr.payslip
docs: hr.payslip(2,)
currency: res.currency(1,)

Number of reports: 1

=== FIRST REPORT STRUCTURE ===
Report keys: ['payslip', 'employee', 'exchange', 'salary', 'salary_formatted',
              'earnings', 'earnings_total', 'earnings_total_formatted',
              'deductions', 'deductions_total', 'deductions_total_formatted',
              'net_pay', 'net_pay_formatted', 'currency']

payslip: hr.payslip(2,)
employee: {'name': 'Gustavo Perdomo', 'identification_id': 'V12345678',
           'job': '', 'department': 'Soporte', ...}
salary_formatted: $389.37
earnings count: 1
deductions count: 0

=== FIRST EARNING ===
{
  "number": 1,
  "name": "Aguinaldos (Christmas Bonus)",
  "code": "AGUINALDOS",
  "quantity": 1.0,
  "amount": 146.19,
  "amount_formatted": "$146.19"
}

✓ Report data generated successfully!
```

**Status:** ✅ CORRECT - All data present and properly formatted

---

## CONFIGURATION COMPARISON

### Liquidación (WORKING) vs Compact (ISSUE)

| Component | Liquidación | Compact |
|-----------|-------------|---------|
| **Report Action** | | |
| - report_name | `ueipab_payroll_enhancements.liquidacion_breakdown_report` | `ueipab_payroll_enhancements.report_payslip_compact` |
| - model | `hr.payslip` | `hr.payslip` ✅ |
| - report_type | `qweb-pdf` | `qweb-pdf` ✅ |
| **Template** | | |
| - Template ID | `liquidacion_breakdown_report` | `report_payslip_compact` |
| - Iteration | `<t t-foreach="reports">` | `<t t-foreach="docs">` ⚠️ |
| **Report Model** | | |
| - _name | `report.ueipab_payroll_enhancements.liquidacion_breakdown_report` | `report.ueipab_payroll_enhancements.report_payslip_compact` ✅ |
| - Returns docs | ✅ Yes | ✅ Yes |
| - Returns reports | ✅ Yes | ✅ Yes |

---

## KEY DIFFERENCE IDENTIFIED ⚠️

### Template Iteration Pattern

**Liquidación (WORKING):**
```xml
<template id="liquidacion_breakdown_report">
    <t t-call="web.html_container">
        <t t-foreach="reports" t-as="report">  ← Direct iteration
            <t t-call="web.basic_layout">
                <div class="page">
                    <t t-esc="report['payslip'].number"/>
                    <t t-esc="report['employee']['name']"/>
                    <!-- ... uses report dict directly ... -->
                </div>
            </t>
        </t>
    </t>
</template>
```

**Compact (CURRENT):**
```xml
<template id="report_payslip_compact">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="o">  ← Iterates over docs
            <t t-set="report" t-value="reports[o_index]"/>  ← Gets report by index
            <t t-call="web.basic_layout">
                <div class="page">
                    <t t-esc="report['payslip'].number"/>
                    <t t-esc="report['employee']['name']"/>
                    <!-- ... uses report dict from index ... -->
                </div>
            </t>
        </t>
    </t>
</template>
```

**Analysis:**
- Both patterns are VALID in Odoo
- Liquidación iterates directly over `reports` list
- Compact iterates over `docs` recordset and uses `reports[o_index]`
- Both should work IF reports list has same length as docs recordset

---

## POSSIBLE ROOT CAUSES

### 1. Browser Cache (MOST LIKELY)
- User may not have performed hard refresh (Ctrl+Shift+R)
- Old cached version of blank template may still be loading
- **ACTION:** Ask user to clear browser cache and hard reload

### 2. Template Iteration Mismatch
- If `docs` recordset has different length than `reports` list
- `o_index` might be out of bounds
- **CHECK:** Diagnostic shows both have length 1, so this is NOT the issue

### 3. Odoo Asset Cache
- Web assets may be cached in Odoo
- **ACTION:** Restart Odoo container to clear all caches

### 4. wkhtmltopdf Rendering Issue
- Template might have syntax that wkhtmltopdf can't render
- But diagnostic shows HTML renders correctly (12,573 bytes in earlier test)

---

## RECOMMENDATIONS (IN ORDER)

### Option 1: Clear All Caches (NO CODE CHANGES)
1. User performs hard browser refresh: `Ctrl+Shift+R`
2. Restart Odoo container: `docker restart odoo-dev-web`
3. Clear Odoo web assets via UI: Settings > Technical > Clear Assets Cache
4. Test again with SLIP/953

### Option 2: Align Template Pattern with Liquidación
Change template to iterate directly over `reports` instead of `docs`:

**FROM:**
```xml
<t t-foreach="docs" t-as="o">
    <t t-set="report" t-value="reports[o_index]"/>
```

**TO:**
```xml
<t t-foreach="reports" t-as="report">
```

This would make it EXACTLY match the working Liquidación pattern.

### Option 3: Add Debug Output to Template
Add visible text to verify template is rendering:

```xml
<div class="page">
    <p style="color: red; font-size: 20pt;">DEBUG: Template is rendering!</p>
    <p>Docs count: <t t-esc="len(docs)"/></p>
    <p>Reports count: <t t-esc="len(reports)"/></p>
    <!-- ... rest of template ... -->
</div>
```

---

## FILES INVOLVED

### Source Files (git tracked)
- `/opt/odoo-dev/addons/ueipab_payroll_enhancements/wizard/payslip_compact_wizard.py`
- `/opt/odoo-dev/addons/ueipab_payroll_enhancements/models/payslip_compact_report.py`
- `/opt/odoo-dev/addons/ueipab_payroll_enhancements/reports/payslip_compact_report.xml`
- `/opt/odoo-dev/addons/ueipab_payroll_enhancements/reports/report_actions.xml`

### Deployed Files (Odoo loads from here)
- `/mnt/extra-addons/ueipab_payroll_enhancements/wizard/payslip_compact_wizard.py`
- `/mnt/extra-addons/ueipab_payroll_enhancements/models/payslip_compact_report.py`
- `/mnt/extra-addons/ueipab_payroll_enhancements/reports/payslip_compact_report.xml`
- `/mnt/extra-addons/ueipab_payroll_enhancements/reports/report_actions.xml`

**Status:** All files synced ✅

---

## LATEST TEST RESULTS (2025-11-22 - Evening Session)

### Debug Output Test - CRITICAL FINDING 🔴

**Test:** Added prominent yellow debug box with red border at top of template
**Expected:** Debug text should appear even if rest of template fails
**Result:** **NOTHING - PDF still completely blank**

**Conclusion:** Template is NOT being rendered at all by wkhtmltopdf/Odoo

This rules out:
- ❌ Template content issues (debug box should show regardless)
- ❌ Data availability issues (proven working in diagnostic script)
- ❌ Browser cache (hard refresh attempted multiple times)

This points to:
- ⚠️ Report action not calling the template correctly
- ⚠️ Template not registered/loaded in Odoo
- ⚠️ QWeb rendering pipeline issue

---

## NEXT DEBUGGING STEPS (When Resuming)

### Step 1: Verify Template Registration in Database
Check if template exists in Odoo database:

```python
# Script to check template registration
env['ir.ui.view'].search([('key', 'like', 'payslip_compact')])
env['ir.ui.view'].search([('name', 'like', 'compact')])
```

### Step 2: Compare Report Action Records
Check actual database records:

```python
# Compare both report actions
liquidacion = env['ir.actions.report'].search([('report_name', '=', 'ueipab_payroll_enhancements.liquidacion_breakdown_report')])
compact = env['ir.actions.report'].search([('report_name', '=', 'ueipab_payroll_enhancements.report_payslip_compact')])

print(f"Liquidación ID: {liquidacion.id}, Model: {liquidacion.model}")
print(f"Compact ID: {compact.id}, Model: {compact.model}")
```

### Step 3: Test Direct Template Call
Try calling template directly:

```python
# Bypass wizard, call report directly
payslip = env['hr.payslip'].browse(2)  # SLIP/953
report = env['ir.actions.report'].search([('report_name', '=', 'ueipab_payroll_enhancements.report_payslip_compact')])
pdf_data, _ = report._render_qweb_pdf([payslip.id])
print(f"PDF size: {len(pdf_data)} bytes")
```

### Step 4: Check Odoo Logs During Generation
Monitor Odoo logs while generating report:

```bash
docker logs -f odoo-dev-web 2>&1 | grep -E "report|qweb|payslip_compact|error|warning"
```

Look for:
- Template not found errors
- QWeb compilation errors
- Missing report action warnings

### Step 5: Nuclear Option - Recreate from Scratch
If all else fails, create minimal test report:

1. Create simplest possible template
2. Create minimal report action
3. Test if it renders
4. Gradually add complexity until it breaks

---

## POSSIBLE ROOT CAUSES (Updated)

### Most Likely (After Debug Test):

1. **Template XML Syntax Error** (90% confidence)
   - XML not well-formed
   - QWeb can't compile template
   - Silent failure in Odoo

2. **Report Action Misconfiguration** (70% confidence)
   - `report_name` doesn't match template `id`
   - Model name incorrect
   - Report type wrong

3. **Template Not Loaded into Database** (50% confidence)
   - Module upgrade didn't load template
   - XML file not in manifest data list
   - Template has duplicate ID

### Less Likely:

4. **wkhtmltopdf Issue** (10% confidence)
   - Working Liquidación proves wkhtmltopdf functional
   - Debug box should show even if rendering fails

---

## FILES TO REVIEW (Priority Order)

### 1. Template XML Syntax
**File:** `reports/payslip_compact_report.xml`
**Check for:**
- Proper XML closing tags
- t-esc vs t-raw usage
- Nested t-if/t-foreach properly closed
- QWeb expression syntax errors

### 2. Report Action Configuration
**File:** `reports/report_actions.xml:133-141`
**Verify:**
- `report_name` matches template `id` exactly
- Model is `hr.payslip` (not `payslip.compact.wizard`)
- `report_type` is `qweb-pdf`
- Template `id` is unique

### 3. Manifest Data Loading Order
**File:** `__manifest__.py`
**Ensure:**
- `reports/report_actions.xml` before `reports/payslip_compact_report.xml`
- OR both templates after actions
- No circular dependencies

---

## CONCLUSION (UPDATED)

**Data Layer:** ✅ WORKING - Report model generates all correct data (proven)
**Template Layer:** 🔴 NOT RENDERING - Even debug output doesn't show
**Root Cause:** Template is not being called/rendered by QWeb pipeline

**Critical Next Step:** Verify template exists in database and is linked to report action

**Session Status:** User taking break - resume debugging when returned

---

## SESSION NOTES

- **Duration:** Extended debugging session (multiple hours)
- **Fixes Applied:**
  - ✅ Wizard `docids=` parameter
  - ✅ Report model `payslip_ids` (plural)
  - ✅ Debug output added
- **Outcome:** Template fundamentally not rendering
- **User Action:** Break - will resume later
