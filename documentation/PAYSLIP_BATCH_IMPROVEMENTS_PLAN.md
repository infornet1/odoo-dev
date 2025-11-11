# Payslip Batch Improvements - Implementation Plan
**Date:** 2025-11-11
**Module:** ueipab_payroll_enhancements (existing) ✅
**Author:** UEIPAB
**Model:** hr.payslip.run
**Odoo Version:** 17.0 Community

---

## Executive Summary

Three critical improvements to payslip batch (hr.payslip.run) list/form view:

1. **Total Net Balance Field** - Show sum of all employee net pay in batch
2. **Print Disbursement List** - PDF report for finance staff (ICF compliance)
3. **Cancel Button** - Cancel batches instead of forcing deletion (audit trail)

**Odoo Best Practices Applied:**
- ✅ Computed fields with @api.depends
- ✅ QWeb PDF reports
- ✅ State-based workflow with cancel action
- ✅ No new modules (use existing ueipab_payslip_reports)

---

## Odoo 17 Documentation Review

### Computed Fields (Official Documentation)
**Source:** https://www.odoo.com/documentation/17.0/developer/tutorials/server_framework_101/08_compute_onchange.html

**Key Best Practices:**
- Use `@api.depends()` decorator to specify dependencies
- Computed fields are read-only by default (good for totals)
- For relational fields, use paths: `@api.depends('slip_ids')`
- Never use onchange for business logic - always use computed fields
- Store computed fields if expensive to calculate: `store=True`

**Example Pattern:**
```python
@api.depends('payslip_ids.total')
def _compute_total_net(self):
    for batch in self:
        batch.total_net_amount = sum(batch.payslip_ids.mapped('total'))
```

### QWeb Reports (Official Documentation)
**Source:** https://www.odoo.com/documentation/17.0/developer/tutorials/pdf_reports.html

**Key Best Practices:**
- Reports declared using `ir.actions.report` model
- Link reports to buttons for conditional access
- Use `report_type="qweb-pdf"` for PDF generation
- Template receives recordset, can handle multiple records
- Use `paperformat_id` for custom paper sizes

**Example Report Action:**
```xml
<record id="action_report_disbursement" model="ir.actions.report">
    <field name="name">Payroll Disbursement List</field>
    <field name="model">hr.payslip.run</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">module.template_disbursement</field>
    <field name="print_report_name">'Disbursement_%s' % object.name</field>
</record>
```

### State Workflows (Community Patterns)
**Common Pattern:**
- Selection field for state: `state = fields.Selection([...])`
- Action methods: `action_draft()`, `action_confirm()`, `action_cancel()`
- State-based button visibility: `attrs="{'invisible': [('state', '!=', 'draft')]}"`
- Cancel should preserve data (not delete)

---

## Current Module Structure

**Module:** ueipab_payroll_enhancements
**Author:** UEIPAB ✅
**Location:** `/opt/odoo-dev/addons/ueipab_payroll_enhancements/`

**Existing Structure:**
```
ueipab_payroll_enhancements/
├── __init__.py
├── __manifest__.py
├── models/
│   └── (wizard models)
├── security/
│   └── (access rights)
└── views/
    └── hr_payslip_employees_views.xml
```

**Dependencies:**
- hr_payroll_community ✅
- ueipab_hr_contract ✅

---

## Implementation Plan

### Enhancement 1: Total Net Balance Field

**Objective:** Show total net pay for all employees in batch

**Technical Approach:**
- Add computed field to hr.payslip.run model
- Calculate sum of all payslip net amounts
- Display in tree view (list) and form view
- Update on payslip changes

**Files to Create/Modify:**

1. **models/hr_payslip_run.py** (NEW)
```python
from odoo import models, fields, api

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    total_net_amount = fields.Monetary(
        string='Total Net Payable',
        compute='_compute_total_net_amount',
        store=True,
        currency_field='currency_id',
        help='Sum of all employee net payments in this batch'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    @api.depends('slip_ids', 'slip_ids.state')
    def _compute_total_net_amount(self):
        """Calculate total net payable for all payslips in batch.

        Only includes payslips in 'done' or 'paid' state to reflect
        actual disbursement amount.
        """
        for batch in self:
            # Get all completed payslips
            valid_slips = batch.slip_ids.filtered(
                lambda s: s.state in ('done', 'paid')
            )

            # Sum the NET line from each payslip
            total = 0.0
            for slip in valid_slips:
                net_line = slip.line_ids.filtered(
                    lambda l: l.salary_rule_id.code == 'VE_NET'
                )
                if net_line:
                    total += net_line.total

            batch.total_net_amount = total
```

2. **views/hr_payslip_run_view.xml** (NEW)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Extend tree view to add Total Net Payable -->
    <record id="hr_payslip_run_tree_total_net" model="ir.ui.view">
        <field name="name">hr.payslip.run.tree.total.net</field>
        <field name="model">hr.payslip.run</field>
        <field name="inherit_id" ref="hr_payroll_community.hr_payslip_run_tree"/>
        <field name="arch" type="xml">
            <!-- Add after Credit Note field -->
            <field name="credit_note" position="after">
                <field name="total_net_amount" sum="Total Net Payable"/>
            </field>
        </field>
    </record>

    <!-- Extend form view to add Total Net Payable -->
    <record id="hr_payslip_run_form_total_net" model="ir.ui.view">
        <field name="name">hr.payslip.run.form.total.net</field>
        <field name="model">hr.payslip.run</field>
        <field name="inherit_id" ref="hr_payroll_community.hr_payslip_run_form"/>
        <field name="arch" type="xml">
            <!-- Add in header area, next to Credit Note -->
            <field name="credit_note" position="after">
                <field name="total_net_amount" widget="monetary"/>
            </field>
        </field>
    </record>
</odoo>
```

3. **models/__init__.py** (MODIFY)
```python
from . import hr_payslip
from . import hr_payslip_run  # ADD THIS LINE
```

4. **__manifest__.py** (MODIFY)
```python
'data': [
    'views/hr_payslip_view.xml',
    'views/hr_payslip_run_view.xml',  # ADD THIS LINE
    'report/payslip_report_views.xml',
    'report/payslip_templates.xml',
]
```

---

### Enhancement 2: Print Disbursement List Report

**Objective:** Generate professional PDF report for finance staff showing pending disbursements

**Report Requirements:**
- Title: "Pending Payroll Disbursement List"
- Batch details (name, period, date, total)
- Employee list with net amounts
- Grouped by payment method (if applicable)
- Footer with prepared by, approved by signatures
- ICF (Internal Control Framework) compliant

**Files to Create/Modify:**

1. **report/disbursement_report_action.xml** (NEW)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Report Action -->
    <record id="action_report_payroll_disbursement" model="ir.actions.report">
        <field name="name">Payroll Disbursement List</field>
        <field name="model">hr.payslip.run</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">ueipab_payroll_enhancements.report_payroll_disbursement</field>
        <field name="report_file">ueipab_payroll_enhancements.report_payroll_disbursement</field>
        <field name="print_report_name">'Disbursement_%s_%s' % (object.name, object.date_start.strftime('%Y%m%d'))</field>
        <field name="binding_model_id" ref="hr_payroll_community.model_hr_payslip_run"/>
        <field name="binding_type">report</field>
    </record>
</odoo>
```

2. **report/disbursement_templates.xml** (NEW)
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="report_payroll_disbursement">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="batch">
                <t t-call="web.external_layout">
                    <div class="page">
                        <!-- Header -->
                        <div class="text-center">
                            <h2>PENDING PAYROLL DISBURSEMENT LIST</h2>
                            <h4><t t-esc="batch.name"/></h4>
                            <p>
                                Period: <strong><t t-esc="batch.date_start"/> to <t t-esc="batch.date_end"/></strong>
                                <br/>
                                Date Prepared: <strong><t t-esc="context_timestamp(datetime.datetime.now()).strftime('%Y-%m-%d %H:%M')"/></strong>
                            </p>
                        </div>

                        <!-- Summary Box -->
                        <div class="row mt-4 mb-4" style="border: 2px solid #000; padding: 10px;">
                            <div class="col-6">
                                <strong>Total Employees:</strong> <t t-esc="len(batch.slip_ids)"/>
                            </div>
                            <div class="col-6 text-right">
                                <strong>Total Net Payable:</strong>
                                <span style="font-size: 18px;">
                                    <t t-esc="batch.total_net_amount" t-options="{'widget': 'monetary', 'display_currency': batch.currency_id}"/>
                                </span>
                            </div>
                        </div>

                        <!-- Employee List Table -->
                        <table class="table table-sm table-bordered">
                            <thead style="background-color: #875A7B; color: white;">
                                <tr>
                                    <th class="text-center">#</th>
                                    <th>Employee ID</th>
                                    <th>Employee Name</th>
                                    <th>Job Position</th>
                                    <th class="text-right">Net Amount</th>
                                    <th class="text-center">Signature</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-set="counter" t-value="1"/>
                                <t t-foreach="batch.slip_ids.sorted(key=lambda s: s.employee_id.name)" t-as="slip">
                                    <t t-set="net_line" t-value="slip.line_ids.filtered(lambda l: l.salary_rule_id.code == 'VE_NET')"/>
                                    <tr>
                                        <td class="text-center"><t t-esc="counter"/></td>
                                        <td><t t-esc="slip.employee_id.employee_id or 'N/A'"/></td>
                                        <td><strong><t t-esc="slip.employee_id.name"/></strong></td>
                                        <td><t t-esc="slip.employee_id.job_id.name or 'N/A'"/></td>
                                        <td class="text-right">
                                            <t t-esc="net_line.total if net_line else 0.0" t-options="{'widget': 'monetary', 'display_currency': batch.currency_id}"/>
                                        </td>
                                        <td style="height: 30px;"> </td>
                                    </tr>
                                    <t t-set="counter" t-value="counter + 1"/>
                                </t>
                            </tbody>
                            <tfoot>
                                <tr style="background-color: #f0f0f0; font-weight: bold;">
                                    <td colspan="4" class="text-right">TOTAL:</td>
                                    <td class="text-right">
                                        <t t-esc="batch.total_net_amount" t-options="{'widget': 'monetary', 'display_currency': batch.currency_id}"/>
                                    </td>
                                    <td></td>
                                </tr>
                            </tfoot>
                        </table>

                        <!-- ICF Signatures -->
                        <div class="row mt-5">
                            <div class="col-6 text-center">
                                <p style="border-top: 1px solid #000; display: inline-block; padding-top: 5px; width: 200px;">
                                    Prepared By
                                </p>
                                <br/>
                                <small>HR Department</small>
                            </div>
                            <div class="col-6 text-center">
                                <p style="border-top: 1px solid #000; display: inline-block; padding-top: 5px; width: 200px;">
                                    Approved By
                                </p>
                                <br/>
                                <small>Finance Manager</small>
                            </div>
                        </div>

                        <!-- Footer Note -->
                        <div class="row mt-4">
                            <div class="col-12 text-center">
                                <p style="font-size: 10px; color: #666;">
                                    <strong>Internal Control Framework (ICF) Document</strong><br/>
                                    This document serves as authorization for payroll disbursement and must be retained for audit purposes.
                                </p>
                            </div>
                        </div>
                    </div>
                </t>
            </t>
        </t>
    </template>
</odoo>
```

3. **views/hr_payslip_run_view.xml** (MODIFY - add button)
```xml
<!-- Add Print button to form view header -->
<record id="hr_payslip_run_form_print_button" model="ir.ui.view">
    <field name="name">hr.payslip.run.form.print.button</field>
    <field name="model">hr.payslip.run</field>
    <field name="inherit_id" ref="hr_payroll_community.hr_payslip_run_form"/>
    <field name="arch" type="xml">
        <xpath expr="//form/header" position="inside">
            <button name="%(action_report_payroll_disbursement)d"
                    string="Print Disbursement List"
                    type="action"
                    class="oe_highlight"
                    attrs="{'invisible': [('slip_ids', '=', [])]}"
                    icon="fa-print"/>
        </xpath>
    </field>
</record>
```

4. **__manifest__.py** (MODIFY)
```python
'data': [
    'views/hr_payslip_view.xml',
    'views/hr_payslip_run_view.xml',
    'report/payslip_report_views.xml',
    'report/payslip_templates.xml',
    'report/disbursement_report_action.xml',  # ADD THIS LINE
    'report/disbursement_templates.xml',       # ADD THIS LINE
]
```

---

### Enhancement 3: Cancel Button (No Deletion)

**Objective:** Add cancel workflow to batch, preserving audit trail

**Business Policy:**
- Never delete batches (audit trail requirement)
- Cancel button sets state to 'cancel'
- Cancels all associated payslips
- Preserves all data for history

**Files to Create/Modify:**

1. **models/hr_payslip_run.py** (MODIFY - add state and cancel method)
```python
class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('close', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    total_net_amount = fields.Monetary(...)  # from Enhancement 1
    currency_id = fields.Many2one(...)       # from Enhancement 1

    @api.depends('slip_ids', 'slip_ids.state')
    def _compute_total_net_amount(self):
        """Only include non-cancelled payslips in total"""
        for batch in self:
            valid_slips = batch.slip_ids.filtered(
                lambda s: s.state not in ('cancel',) and s.state in ('done', 'paid')
            )

            total = 0.0
            for slip in valid_slips:
                net_line = slip.line_ids.filtered(
                    lambda l: l.salary_rule_id.code == 'VE_NET'
                )
                if net_line:
                    total += net_line.total

            batch.total_net_amount = total

    def action_cancel(self):
        """Cancel payslip batch and all associated payslips.

        BUSINESS POLICY:
        - Does NOT delete batch or payslips
        - Sets state to 'cancel' for audit trail
        - Cancels all payslips and their journal entries
        - Preserves complete history
        """
        for batch in self:
            # Cancel all payslips in batch
            batch.slip_ids.filtered(
                lambda s: s.state != 'cancel'
            ).action_payslip_cancel()

            # Set batch to cancelled
            batch.state = 'cancel'

        return True

    def action_draft(self):
        """Reset batch to draft state"""
        for batch in self:
            batch.state = 'draft'
            # Reset payslips to draft if possible
            batch.slip_ids.filtered(
                lambda s: s.state == 'cancel'
            ).action_payslip_draft()
        return True
```

2. **views/hr_payslip_run_view.xml** (MODIFY - add cancel button)
```xml
<!-- Add Cancel button to form view header -->
<record id="hr_payslip_run_form_cancel_button" model="ir.ui.view">
    <field name="name">hr.payslip.run.form.cancel.button</field>
    <field name="model">hr.payslip.run</field>
    <field name="inherit_id" ref="hr_payroll_community.hr_payslip_run_form"/>
    <field name="arch" type="xml">
        <xpath expr="//form/header" position="inside">
            <!-- Cancel Button -->
            <button name="action_cancel"
                    string="Cancel Batch"
                    type="object"
                    confirm="Are you sure you want to cancel this batch? All payslips will be cancelled but preserved for audit trail."
                    attrs="{'invisible': [('state', 'in', ['cancel'])]}"
                    icon="fa-times-circle"/>

            <!-- Reset to Draft Button -->
            <button name="action_draft"
                    string="Reset to Draft"
                    type="object"
                    attrs="{'invisible': [('state', '!=', 'cancel')]}"
                    icon="fa-undo"/>

            <!-- State field (visible in header) -->
            <field name="state" widget="statusbar" statusbar_visible="draft,confirm,close"/>
        </xpath>
    </field>
</record>

<!-- Add state to tree view -->
<record id="hr_payslip_run_tree_state" model="ir.ui.view">
    <field name="name">hr.payslip.run.tree.state</field>
    <field name="model">hr.payslip.run</field>
    <field name="inherit_id" ref="hr_payroll_community.hr_payslip_run_tree"/>
    <field name="arch" type="xml">
        <field name="total_net_amount" position="after">
            <field name="state" decoration-danger="state=='cancel'" decoration-success="state=='close'"/>
        </field>
    </field>
</record>
```

---

## File Summary

### New Files to Create:
1. `models/hr_payslip_run.py` - Model extensions
2. `views/hr_payslip_run_view.xml` - UI enhancements
3. `report/disbursement_report_action.xml` - Report action
4. `report/disbursement_templates.xml` - Report template

### Files to Modify:
1. `models/__init__.py` - Add hr_payslip_run import
2. `__manifest__.py` - Add new data files

### No New Modules Created ✅
All enhancements in existing: `ueipab_payroll_enhancements` (UEIPAB author)

---

## Testing Plan

### Test 1: Total Net Balance Field
1. Create payslip batch with 5 employees
2. Generate payslips (state = draft)
3. Verify total_net_amount = 0 (only counts done/paid)
4. Confirm payslips (state = done)
5. Verify total_net_amount shows correct sum
6. Check tree view shows sum at bottom
7. Check form view shows amount next to Credit Note

### Test 2: Print Disbursement List
1. Create confirmed batch with payslips
2. Click "Print Disbursement List" button
3. Verify PDF generates successfully
4. Check PDF content:
   - Header with batch name/period
   - Summary box with total
   - Employee table with net amounts
   - Signature lines for ICF
   - Footer note
5. Test with multiple batches (batch print)

### Test 3: Cancel Button
1. Create batch with payslips
2. Confirm and post payslips (journal entries created)
3. Click "Cancel Batch" button
4. Verify:
   - Batch state = 'cancel'
   - All payslips state = 'cancel'
   - Journal entries state = 'cancel'
   - NO records deleted
   - Can see cancelled batch in list (with filter)
5. Click "Reset to Draft"
6. Verify batch and payslips back to draft

---

## Deployment Steps

1. **Backup Database**
```bash
docker exec odoo-dev-postgres pg_dump -U odoo testing > backup_before_enhancements.sql
```

2. **Update Module Code**
- Add all new files
- Modify existing files
- Git commit

3. **Upgrade Module in Odoo**
```bash
docker exec odoo-dev-web python3 /usr/bin/odoo -u ueipab_payroll_enhancements -d testing --stop-after-init
```

4. **Restart Odoo**
```bash
docker restart odoo-dev-web
```

5. **Test Each Enhancement**
- Follow testing plan
- Verify all functionality
- Check for errors in logs

6. **Git Commit and Push**
```bash
git add -A
git commit -m "Add payslip batch enhancements: total net, disbursement report, cancel button"
git push origin main
```

---

## Odoo Best Practices Applied

✅ **Computed Fields**
- Using @api.depends with proper dependencies
- Store=True for performance
- Read-only (no inverse needed)

✅ **Reports**
- QWeb PDF with professional template
- Linked to button (conditional access)
- Descriptive print_report_name
- ICF compliance

✅ **State Workflow**
- Selection field with tracking
- Action methods (action_cancel, action_draft)
- State-based button visibility
- No deletion (audit trail preserved)

✅ **Module Structure**
- No new modules created
- Proper file organization
- Manifest dependencies correct
- View inheritance (no duplication)

---

## Expected Results

### Enhancement 1: Total Net Balance
- Tree view shows sum of all batch net amounts at bottom
- Form view shows total next to Credit Note field
- Updates automatically when payslips change
- Only counts confirmed payslips

### Enhancement 2: Print Report
- Professional PDF report for finance
- Clear disbursement list format
- ICF compliant with signatures
- Print button visible when batch has payslips

### Enhancement 3: Cancel Button
- Cancel button available (not just delete)
- Preserves audit trail (no deletion)
- Cancels batch and all payslips
- Can reset to draft if needed

---

## Maintenance Notes

### Total Net Field
- Recomputes automatically via depends
- No manual maintenance needed
- Performance: Uses store=True

### Disbursement Report
- Template can be customized per requirements
- Easy to add more fields/sections
- Paperformat can be changed

### Cancel Workflow
- Follows same business policy as journal entries
- Complete audit trail maintained
- Can add more states if needed (e.g., 'pending_approval')

---

**Prepared by:** Claude Code AI Assistant
**Plan Date:** 2025-11-11
**Status:** ✅ READY FOR IMPLEMENTATION
**Module:** ueipab_payroll_enhancements (existing) - UEIPAB author ✅
**Odoo Version:** 17.0 Community Edition
