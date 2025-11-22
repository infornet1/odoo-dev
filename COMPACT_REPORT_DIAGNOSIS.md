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

## CONCLUSION

**Data Layer:** ✅ WORKING - Report generates all correct data
**Template Layer:** ⚠️ UNKNOWN - Uses different iteration pattern than working Liquidación
**Most Likely Issue:** Browser/Odoo cache preventing new template from loading

**Recommendation:** Start with Option 1 (cache clearing), then try Option 2 (align template pattern) if issue persists.
