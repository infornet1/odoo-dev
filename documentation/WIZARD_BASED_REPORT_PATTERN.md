# Wizard-Based Custom QWeb Report Pattern - Complete Guide

**Last Updated:** 2025-11-14
**Odoo Version:** 17.0 Community Edition
**Status:** ✅ Production-Ready Pattern

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Checklist](#implementation-checklist)
4. [Step-by-Step Implementation](#step-by-step-implementation)
5. [Critical Patterns](#critical-patterns)
6. [Common Pitfalls](#common-pitfalls)
7. [Debugging Guide](#debugging-guide)
8. [Working Examples](#working-examples)

---

## Overview

### What is a Wizard-Based Report?

A wizard-based report in Odoo allows users to:
- Select records dynamically through a wizard UI
- Choose report parameters (date ranges, currencies, filters, etc.)
- Generate customized PDF reports with processed data

### When to Use This Pattern

- ✅ Reports requiring user input before generation
- ✅ Multi-record selection with filtering
- ✅ Complex data processing/aggregation needed
- ✅ Reports with optional parameters
- ✅ Cross-model data combination

---

## Architecture

### Component Structure

```
Module
├── models/
│   ├── {report_name}_wizard.py          # TransientModel - User interface
│   └── {report_name}_report.py          # AbstractModel - Data processing
├── wizard/
│   └── {report_name}_wizard_view.xml    # Wizard form view
├── reports/
│   ├── report_actions.xml               # Report action + paper format
│   └── {report_name}_report.xml         # QWeb template
└── views/
    └── menu.xml                          # Menu integration
```

### Data Flow

```
User Interface (Wizard)
    ↓ (user selects records + parameters)
action_print_report()
    ↓ (calls report_action with data)
Report Action (ir.actions.report)
    ↓ (triggers report engine)
AbstractModel._get_report_values()
    ↓ (processes data, returns context)
QWeb Template
    ↓ (renders PDF)
wkhtmltopdf
    ↓
PDF Output
```

---

## Implementation Checklist

### Phase 1: Planning
- [ ] Define report requirements
- [ ] Identify source model(s)
- [ ] List wizard parameters needed
- [ ] Sketch report layout (columns, sections)
- [ ] Choose paper format (Portrait/Landscape, Letter/A4)

### Phase 2: Backend Models
- [ ] Create TransientModel wizard (`models/{name}_wizard.py`)
- [ ] Create AbstractModel report parser (`models/{name}_report.py`)
- [ ] Register both in `models/__init__.py`

### Phase 3: UI Components
- [ ] Create wizard view XML (`wizard/{name}_wizard_view.xml`)
- [ ] Create report action XML (`reports/report_actions.xml`)
- [ ] Create QWeb template XML (`reports/{name}_report.xml`)
- [ ] Add menu item (`views/menu.xml`)

### Phase 4: Security
- [ ] Add wizard access rules to `security/ir.model.access.csv`
- [ ] Test with non-admin users

### Phase 5: Testing
- [ ] Test wizard opens correctly
- [ ] Test record selection works
- [ ] Test PDF generation (backend)
- [ ] Test PDF generation (UI)
- [ ] Test with multiple records
- [ ] Test with edge cases (empty selection, special characters)

---

## Step-by-Step Implementation

### Step 1: Create Wizard Model

**File:** `models/{report_name}_wizard.py`

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class YourReportWizard(models.TransientModel):
    """Wizard for generating Your Custom Report."""

    _name = 'your.report.wizard'
    _description = 'Your Report Wizard'

    # Record Selection
    record_ids = fields.Many2many(
        'your.source.model',
        string='Records',
        required=True,
        domain="[('state', '!=', 'cancel')]",  # Add your domain
        help='Select records to include in report'
    )

    # Parameters
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.ref('base.USD'),
    )

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    # Computed field for UI feedback
    record_count = fields.Integer(
        compute='_compute_record_count',
        string='Selected Records'
    )

    @api.depends('record_ids')
    def _compute_record_count(self):
        for wizard in self:
            wizard.record_count = len(wizard.record_ids)

    def action_print_report(self):
        """Generate and print the report.

        CRITICAL: This is the method that bridges wizard -> report!
        """
        self.ensure_one()

        # Validation
        if not self.record_ids:
            raise UserError(_('Please select at least one record.'))

        # Prepare data dictionary - THIS IS CRITICAL!
        data = {
            'wizard_id': self.id,
            'currency_id': self.currency_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'record_ids': self.record_ids.ids,  # ← CRITICAL: Pass IDs here!
        }

        # Get report action
        report = self.env.ref('your_module.action_report_your_report')

        # CRITICAL PATTERN: Use docids= with IDs list
        # This pattern matches Odoo's working disbursement report
        return report.report_action(docids=self.record_ids.ids, data=data)
```

**Key Points:**
- ✅ Use `TransientModel` (temporary records)
- ✅ Pass **IDs list** in `data` dict as `record_ids`
- ✅ Use `docids=` keyword with IDs list in `report_action()`
- ✅ Validate inputs before generating

---

### Step 2: Create Report Model (AbstractModel)

**File:** `models/{report_name}_report.py`

```python
# -*- coding: utf-8 -*-
from odoo import models, api

class YourReportParser(models.AbstractModel):
    """Report parser for Your Custom Report."""

    # CRITICAL: Name must match report template reference
    _name = 'report.your_module.your_report_template_id'
    _description = 'Your Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Build report data for QWeb template.

        CRITICAL: This method MUST read from data['record_ids']!

        Args:
            docids (list): List of record IDs (may be None/empty from wizard)
            data (dict): Data dictionary from wizard containing actual IDs

        Returns:
            dict: Context dictionary for QWeb template
        """
        # CRITICAL PATTERN: Read from data dict FIRST!
        # This is what the wizard passes - docids might be empty!
        record_ids = data.get('record_ids', []) if data else []

        # Fallback to docids if data doesn't have IDs
        if not record_ids and docids:
            record_ids = docids

        # Build recordset from IDs
        records = self.env['your.source.model'].browse(record_ids)

        # Get parameters from wizard data
        currency_id = data.get('currency_id') if data else self.env.ref('base.USD').id
        currency = self.env['res.currency'].browse(currency_id)

        # Process data (your custom logic here)
        processed_data = self._process_records(records, data)

        # CRITICAL: Return standard Odoo variables + your custom data
        return {
            'doc_ids': record_ids,        # IDs list
            'doc_model': 'your.source.model',  # Model name
            'docs': records,              # Recordset (standard Odoo variable)
            'data': data,                 # Pass through wizard data
            'currency': currency,
            'processed_data': processed_data,  # Your custom data
        }

    def _process_records(self, records, data):
        """Process records and return structured data.

        This is where you implement your business logic.
        """
        result = []
        for record in records:
            # Your processing logic here
            result.append({
                'record': record,
                'calculated_value': self._calculate_something(record),
                # ... more fields
            })
        return result

    def _calculate_something(self, record):
        """Example calculation method."""
        return 0.0  # Your calculation here
```

**Key Points:**
- ✅ Inherit from `AbstractModel`
- ✅ Name: `report.{module}.{template_id}`
- ✅ **CRITICAL:** Read from `data.get('record_ids')` NOT `docids`!
- ✅ Return standard Odoo variables: `doc_ids`, `doc_model`, `docs`
- ✅ Pass through wizard `data` dict

---

### Step 3: Create Wizard View

**File:** `wizard/{report_name}_wizard_view.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Wizard Form View -->
    <record id="view_your_report_wizard" model="ir.ui.view">
        <field name="name">your.report.wizard.form</field>
        <field name="model">your.report.wizard</field>
        <field name="arch" type="xml">
            <form string="Your Report">
                <group>
                    <field name="record_ids" widget="many2many_tags"/>
                    <field name="currency_id"/>
                    <field name="date_from"/>
                    <field name="date_to"/>
                </group>

                <!-- User feedback -->
                <div class="alert alert-success" invisible="record_count == 0">
                    <strong><field name="record_count"/> record(s) selected</strong>
                </div>

                <footer>
                    <button name="action_print_report"
                            string="Generate Report"
                            type="object"
                            class="btn-primary"
                            invisible="record_count == 0"/>
                    <button string="Cancel" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>

    <!-- Wizard Action -->
    <record id="action_your_report_wizard" model="ir.actions.act_window">
        <field name="name">Your Report</field>
        <field name="res_model">your.report.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
</odoo>
```

**Key Points (Odoo 17):**
- ✅ Use `invisible` attribute (NOT deprecated `attrs`)
- ✅ Show record count for user feedback
- ✅ Disable button when no records selected
- ✅ Use `target="new"` for popup wizard

---

### Step 4: Create Report Action

**File:** `reports/report_actions.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Paper Format -->
    <record id="paperformat_your_report" model="report.paperformat">
        <field name="name">Your Report Format</field>
        <field name="default" eval="False"/>
        <field name="format">Letter</field>
        <field name="orientation">Landscape</field>
        <field name="margin_top">40</field>
        <field name="margin_bottom">25</field>
        <field name="margin_left">7</field>
        <field name="margin_right">7</field>
        <field name="header_line" eval="False"/>
        <field name="header_spacing">35</field>
        <field name="dpi">90</field>
    </record>

    <!-- Report Action -->
    <record id="action_report_your_report" model="ir.actions.report">
        <field name="name">Your Report</field>
        <field name="model">your.source.model</field>
        <field name="report_type">qweb-pdf</field>

        <!-- CRITICAL: These must match exactly -->
        <field name="report_name">your_module.your_report_template_id</field>
        <field name="report_file">your_module.your_report_template_id</field>

        <field name="paperformat_id" ref="paperformat_your_report"/>
        <field name="print_report_name">'Your_Report_%s' % (object.name.replace(' ', '_'))</field>
    </record>
</odoo>
```

**Key Points:**
- ✅ `report_name` and `report_file` must match template ID
- ✅ Paper format is optional but recommended
- ✅ `model` should be the source model (what records are)

---

### Step 5: Create QWeb Template

**File:** `reports/{report_name}_report.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="your_report_template_id">
        <t t-call="web.html_container">
            <t t-call="web.external_layout">
                <div class="page">
                    <!-- Report Header -->
                    <div class="row">
                        <div class="col-12 text-center">
                            <h3><strong>YOUR REPORT TITLE</strong></h3>
                        </div>
                    </div>

                    <!-- Iterate over records using standard 'docs' variable -->
                    <t t-foreach="docs" t-as="record">
                        <div class="row">
                            <div class="col-6">
                                <strong>Record:</strong> <span t-esc="record.name"/>
                            </div>
                        </div>

                        <!-- Your report content here -->
                        <table class="table table-sm table-bordered">
                            <thead>
                                <tr>
                                    <th>Column 1</th>
                                    <th>Column 2</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- Your data rows -->
                            </tbody>
                        </table>
                    </t>

                    <!-- Access custom data from AbstractModel -->
                    <t t-if="processed_data">
                        <t t-foreach="processed_data" t-as="item">
                            <p><span t-esc="item.get('calculated_value')"/></p>
                        </t>
                    </t>
                </div>
            </t>
        </t>
    </template>
</odoo>
```

**Key Points:**
- ✅ Use standard `docs` variable (recordset from AbstractModel)
- ✅ Access custom data variables you returned from `_get_report_values()`
- ✅ Use `.get()` for safe dictionary access
- ✅ Use `web.external_layout` for header/footer

---

### Step 6: Security Access Rules

**File:** `security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_your_report_wizard_user,your.report.wizard.user,model_your_report_wizard,base.group_user,1,1,1,1
access_your_report_wizard_manager,your.report.wizard.manager,model_your_report_wizard,base.group_system,1,1,1,1
```

**Key Points:**
- ✅ TransientModel wizards NEED explicit access rules
- ✅ Without these, menu will be invisible to users
- ✅ AbstractModel reports don't need access rules

---

### Step 7: Menu Integration

**File:** `views/menu.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_your_report"
              name="Your Report"
              parent="parent_menu_id"
              action="action_your_report_wizard"
              sequence="10"
              groups="base.group_user"/>
</odoo>
```

---

### Step 8: Register in __manifest__.py

```python
{
    'name': 'Your Module',
    'version': '1.0.0',
    'depends': ['base', 'hr_payroll_community'],  # Your dependencies
    'data': [
        'security/ir.model.access.csv',
        'wizard/your_report_wizard_view.xml',
        'reports/report_actions.xml',
        'reports/your_report_template.xml',
        'views/menu.xml',
    ],
}
```

---

## Critical Patterns

### ✅ Pattern 1: Wizard Data Passing

**CORRECT:**
```python
# In wizard's action_print_report()
data = {
    'record_ids': self.record_ids.ids,  # Pass IDs in data dict
}
return report.report_action(docids=self.record_ids.ids, data=data)
```

**WRONG:**
```python
# DON'T pass recordset directly
return report.report_action(self.record_ids, data=data)  # ❌
```

---

### ✅ Pattern 2: AbstractModel Data Reading

**CORRECT:**
```python
# In _get_report_values()
record_ids = data.get('record_ids', []) if data else []
if not record_ids and docids:
    record_ids = docids
records = self.env['model'].browse(record_ids)
```

**WRONG:**
```python
# DON'T only read from docids
records = self.env['model'].browse(docids)  # ❌ Will be empty!
```

---

### ✅ Pattern 3: QWeb Template Variable Access

**CORRECT:**
```xml
<!-- Use standard 'docs' variable -->
<t t-foreach="docs" t-as="record">
    <span t-esc="record.name"/>
</t>

<!-- Access custom data safely -->
<span t-esc="custom_data.get('field', 'default')"/>
```

**WRONG:**
```xml
<!-- Don't use reserved names like 'report' -->
<t t-foreach="reports" t-as="report">  <!-- ❌ May conflict -->
```

---

## Common Pitfalls

### ❌ Pitfall 1: Blank PDF Output

**Symptoms:**
- Wizard works, PDF generated
- PDF file size normal (~100KB)
- But PDF shows blank pages

**Root Cause:**
```python
# In AbstractModel
def _get_report_values(self, docids, data=None):
    records = self.env['model'].browse(docids)  # ❌ docids is empty!
```

**Fix:**
```python
# Read from data dict FIRST
record_ids = data.get('record_ids', []) if data else []
if not record_ids and docids:
    record_ids = docids
records = self.env['model'].browse(record_ids)  # ✅
```

---

### ❌ Pitfall 2: Menu Not Visible

**Symptoms:**
- Module installed
- No errors in log
- Menu doesn't appear

**Root Cause:**
Missing security access rules for TransientModel wizard.

**Fix:**
Add to `security/ir.model.access.csv`:
```csv
access_wizard_user,wizard.user,model_wizard_name,base.group_user,1,1,1,1
```

---

### ❌ Pitfall 3: Template Not Found

**Symptoms:**
- Error: "External ID not found: module.template_id"

**Root Cause:**
Mismatch between:
- Report action `report_name` field
- AbstractModel `_name` attribute
- QWeb template `id` attribute

**Fix:**
Ensure all three match:
```python
# AbstractModel
_name = 'report.your_module.your_template_id'
```

```xml
<!-- Report Action -->
<field name="report_name">your_module.your_template_id</field>

<!-- QWeb Template -->
<template id="your_template_id">
```

---

### ❌ Pitfall 4: Python Code Not Reloading

**Symptoms:**
- Changed Python code
- Upgraded module
- Changes not taking effect

**Root Cause:**
Python bytecode cache not cleared.

**Fix:**
```bash
# Clear Python cache
find /path/to/module -type d -name "__pycache__" -exec rm -rf {} +

# Restart Odoo
docker restart odoo-container
```

---

### ❌ Pitfall 5: Odoo 17 View Syntax

**Symptoms:**
- Error: "A partir de 17.0 ya no se usan los atributos 'attrs' y 'states'"

**Root Cause:**
Using deprecated Odoo 16 syntax.

**Fix:**
```xml
<!-- OLD (Odoo 16) - ❌ -->
<div attrs="{'invisible': [('field', '=', False)]}">

<!-- NEW (Odoo 17) - ✅ -->
<div invisible="field == False">
```

---

## Debugging Guide

### Debug Step 1: Test Wizard Creation

```python
# Via Odoo shell
wizard = env['your.report.wizard'].create({
    'record_ids': [(6, 0, [1, 2, 3])],
})
print(f"Wizard: {wizard}")
print(f"Records: {wizard.record_ids}")
print(f"IDs: {wizard.record_ids.ids}")
```

### Debug Step 2: Test Wizard Action

```python
result = wizard.action_print_report()
print(f"Result: {result}")
print(f"Data: {result.get('data')}")
```

### Debug Step 3: Test AbstractModel

```python
report_model = env['report.your_module.your_template_id']
data = {'record_ids': [1, 2, 3]}
values = report_model._get_report_values(docids=None, data=data)
print(f"Values keys: {values.keys()}")
print(f"Docs: {values.get('docs')}")
```

### Debug Step 4: Test PDF Generation

```python
report = env.ref('your_module.action_report_your_report')
pdf_content, fmt = report._render_qweb_pdf(
    report_ref='your_module.your_template_id',
    res_ids=[1, 2, 3],
    data={'record_ids': [1, 2, 3]}
)
print(f"PDF size: {len(pdf_content)} bytes")
```

### Debug Step 5: QWeb Template Variables

Create a debug template:
```xml
<template id="debug_template">
    <t t-call="web.html_container">
        <t t-call="web.external_layout">
            <div class="page">
                <p>docs exists: <span t-if="docs">YES</span><span t-if="not docs">NO</span></p>
                <p>doc_ids: <span t-esc="doc_ids"/></p>
                <p>custom_data exists: <span t-if="custom_data">YES</span><span t-if="not custom_data">NO</span></p>
            </div>
        </t>
    </t>
</template>
```

---

## Working Examples

### Example 1: Payroll Disbursement Detail Report

**Files:**
- `models/payroll_disbursement_wizard.py` - Wizard with batch/date range selection
- `models/payroll_disbursement_report.py` - AbstractModel that reads from `data['payslip_ids']`
- `reports/payroll_disbursement_detail_report.xml` - Template using `docs` variable

**Key Pattern:**
```python
# Wizard
return report.report_action(docids=payslip_ids, data=data)

# AbstractModel
payslip_ids = data.get('payslip_ids', []) if data else []
payslips = self.env['hr.payslip'].browse(payslip_ids)
return {'docs': payslips, ...}

# Template
<t t-foreach="docs" t-as="payslip">
```

---

### Example 2: Prestaciones Interest Report

**Files:**
- `models/prestaciones_interest_wizard.py` - Wizard with multi-select + currency
- `models/prestaciones_interest_report.py` - AbstractModel with monthly breakdown calculation
- `reports/prestaciones_interest_report.xml` - Template with 11-column table

**Key Pattern:**
```python
# Wizard
data = {'payslip_ids': self.payslip_ids.ids, 'currency_id': self.currency_id.id}
return report.report_action(docids=self.payslip_ids.ids, data=data)

# AbstractModel
payslip_ids = data.get('payslip_ids', []) if data else []
payslips = self.env['hr.payslip'].browse(payslip_ids)
# Process each payslip...
return {'docs': payslips, 'reports': processed_data, ...}

# Template
<t t-foreach="reports" t-as="report_data">
    <span t-esc="report_data.get('employee').name"/>
</t>
```

---

## Quick Reference Checklist

### Before Implementation
- [ ] Read this guide completely
- [ ] Review working examples
- [ ] Plan data structure
- [ ] Choose similar existing report as template

### During Implementation
- [ ] Follow naming conventions
- [ ] Use `data.get('record_ids')` pattern in AbstractModel
- [ ] Use `docids=` keyword in wizard
- [ ] Return standard Odoo variables (`docs`, `doc_ids`, `doc_model`)
- [ ] Add security access rules
- [ ] Use Odoo 17 view syntax

### Testing
- [ ] Test backend (shell scripts)
- [ ] Test UI (actual user workflow)
- [ ] Test with multiple records
- [ ] Test with edge cases
- [ ] Verify PDF contains data (not blank)

### Debugging
- [ ] Check logs for errors
- [ ] Use debug template to verify variables
- [ ] Test each component individually
- [ ] Clear Python cache when updating code
- [ ] Hard-refresh browser for UI changes

---

## Conclusion

This pattern is **production-ready** and based on working implementations in the UEIPAB payroll system. Follow these patterns exactly to avoid the common pitfalls that cause blank PDFs and missing data.

**Key Takeaway:** The wizard passes data via the `data` dictionary - the AbstractModel MUST read from `data.get('record_ids')` first, not from `docids`!

---

**Document Version:** 1.0
**Created:** 2025-11-14
**Based on:** Prestaciones Interest Report troubleshooting session
**Validated:** Payroll Disbursement Detail + Prestaciones Interest reports
