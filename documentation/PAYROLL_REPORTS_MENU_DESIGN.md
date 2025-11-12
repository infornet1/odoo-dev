# Payroll Reports Menu Design

**Date:** 2025-11-11
**Context:** Add custom reports submenu to Payroll main menu
**User Request:** Add 4 business-specific reports under Payroll > Reports

## User Requirements

### Requested Reports:

1. **Payroll Disbursement Detail**
   - Detailed breakdown of employee payments
   - Bank transfer details
   - Payment methods and amounts

2. **Payroll Taxes**
   - Tax withholdings by employee
   - Tax summary by period
   - ARI (income tax) calculations
   - Social security contributions

3. **Payroll Accounting**
   - Journal entry details for payslips
   - Account-wise breakdown
   - Debit/credit summary
   - Integration with accounting module

4. **Liquidation Forms**
   - Final settlement calculation when employee leaves
   - Severance pay calculation
   - Unused vacation days payout
   - End-of-service benefits
   - Legal compliance forms

## Current Payroll Menu Structure

Based on analysis of `hr_payroll_community` module:

```
Payroll (Root Menu)
├── Employee Payslips
├── Batches
└── Configuration
    ├── Salary Rules
    ├── Salary Rule Categories
    ├── Contribution Registers
    ├── Salary Structures
    ├── Contract Advantage Templates
    └── Settings
```

**Finding:** There is currently NO "Reports" submenu in the Payroll menu.

## Proposed Menu Structure

Add a new "Reports" submenu under Payroll root:

```
Payroll (Root Menu)
├── Employee Payslips
├── Batches
├── Reports (NEW)
│   ├── Payroll Disbursement Detail
│   ├── Payroll Taxes
│   ├── Payroll Accounting
│   └── Liquidation Forms
└── Configuration
    └── [existing items...]
```

## Technical Implementation Options

### Option 1: Traditional Reports (ir.actions.report - PDF)

**Type:** QWeb PDF reports
**Access:** Print button from payslip/batch
**Navigation:** No menu items needed (button-based)

**Pros:**
- ✅ Simple to implement
- ✅ Standard Odoo pattern
- ✅ Direct print from records

**Cons:**
- ❌ Not in main menu (user requested menu items)
- ❌ No filtering/search capabilities
- ❌ Must open record first

**Example (already exists in hr_payroll_community):**
```xml
<record id="hr_payslip_report_action" model="ir.actions.report">
    <field name="name">Payslip Details Report</field>
    <field name="model">hr.payslip</field>
    <field name="report_type">qweb-pdf</field>
    <field name="binding_model_id" ref="model_hr_payslip"/>
    <field name="report_name">hr_payroll_community.report_payslipdetails</field>
</record>
```

### Option 2: Report Wizards with Menu Items ✅ RECOMMENDED

**Type:** Wizard forms with parameter selection
**Access:** Main menu Payroll > Reports
**Result:** Generated PDF or screen view based on parameters

**Pros:**
- ✅ Appears in main menu (user requirement)
- ✅ Flexible date range selection
- ✅ Multi-employee/batch filtering
- ✅ Better UX for complex reports
- ✅ Can show preview before printing

**Cons:**
- ⚠️ More complex implementation
- ⚠️ Requires wizard models

**Implementation Pattern:**
```xml
<!-- 1. Define wizard model (Python) -->
class PayrollDisbursementWizard(models.TransientModel):
    _name = 'payroll.disbursement.wizard'
    date_from = fields.Date()
    date_to = fields.Date()
    employee_ids = fields.Many2many('hr.employee')

    def action_print_report(self):
        # Generate report

<!-- 2. Define wizard view (XML) -->
<record id="payroll_disbursement_wizard_view" model="ir.ui.view">
    <field name="model">payroll.disbursement.wizard</field>
    <field name="arch" type="xml">
        <form>
            <group>
                <field name="date_from"/>
                <field name="date_to"/>
                <field name="employee_ids"/>
            </group>
            <footer>
                <button name="action_print_report" type="object"
                        string="Print" class="btn-primary"/>
                <button special="cancel" string="Cancel"/>
            </footer>
        </form>
    </field>
</record>

<!-- 3. Define action to open wizard -->
<record id="action_payroll_disbursement_report" model="ir.actions.act_window">
    <field name="name">Payroll Disbursement Detail</field>
    <field name="res_model">payroll.disbursement.wizard</field>
    <field name="view_mode">form</field>
    <field name="target">new</field>
</record>

<!-- 4. Add menu item -->
<menuitem id="menu_payroll_reports"
          name="Reports"
          parent="hr_payroll_community.menu_hr_payroll_community_root"
          sequence="50"/>

<menuitem id="menu_payroll_disbursement_report"
          name="Payroll Disbursement Detail"
          parent="menu_payroll_reports"
          action="action_payroll_disbursement_report"
          sequence="10"
          groups="hr_payroll_community.group_hr_payroll_community_user"/>
```

### Option 3: Hybrid Approach (Menu + Direct Print)

Combine both approaches:
- Wizard for parameter selection (appears in menu)
- Direct print button on payslip/batch forms
- Best of both worlds

## Recommended Implementation Plan

### Phase 1: Create Reports Submenu Structure

**Files to create/modify:**
- `addons/ueipab_payroll_enhancements/views/payroll_reports_menu.xml`

**Actions:**
1. Create parent "Reports" menu under Payroll root
2. Add 4 submenu items (initially empty actions)
3. Define security groups (reuse hr_payroll groups)

### Phase 2: Implement Report #1 - Payroll Disbursement Detail

**Use existing disbursement report:**
- We already have `disbursement_list_report.xml` in ueipab_payroll_enhancements
- Currently prints from batch form
- Create wizard to select batch or date range
- Add menu item to access wizard

**New files:**
- `models/payroll_disbursement_wizard.py`
- `wizard/payroll_disbursement_wizard_view.xml`

### Phase 3: Implement Report #2 - Payroll Taxes

**Business Logic:**
- Show ARI withholdings per employee
- Social security contributions
- Tax summary by period
- Exportable for tax filing

**New files:**
- `models/payroll_taxes_wizard.py`
- `wizard/payroll_taxes_wizard_view.xml`
- `reports/payroll_taxes_report.xml`

### Phase 4: Implement Report #3 - Payroll Accounting

**Business Logic:**
- Show journal entries generated from payslips
- Account-wise breakdown (debits/credits)
- Integration with account moves
- Reconciliation status

**Dependencies:**
- Requires `hr_payroll_account_community` module
- Access to `account.move` and `account.move.line`

**New files:**
- `models/payroll_accounting_wizard.py`
- `wizard/payroll_accounting_wizard_view.xml`
- `reports/payroll_accounting_report.xml`

### Phase 5: Implement Report #4 - Liquidation Forms

**Business Logic:**
- Calculate final settlement on employee departure
- Severance pay (based on Venezuelan labor law)
- Unused vacation days
- Proportional Aguinaldos
- Other end-of-service benefits

**Complexity:** HIGH - requires understanding Venezuelan labor law

**New files:**
- `models/liquidation_wizard.py`
- `wizard/liquidation_wizard_view.xml`
- `reports/liquidation_form_report.xml`

## Menu Structure XML Template

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- ========================================
         Payroll Reports Menu Structure
         ======================================== -->

    <!-- Parent Reports Menu -->
    <menuitem id="menu_payroll_reports"
              name="Reports"
              parent="hr_payroll_community.menu_hr_payroll_community_root"
              sequence="50"
              groups="hr_payroll_community.group_hr_payroll_community_user"/>

    <!-- Report 1: Payroll Disbursement Detail -->
    <menuitem id="menu_payroll_disbursement_detail"
              name="Payroll Disbursement Detail"
              parent="menu_payroll_reports"
              action="action_payroll_disbursement_wizard"
              sequence="10"
              groups="hr_payroll_community.group_hr_payroll_community_user"/>

    <!-- Report 2: Payroll Taxes -->
    <menuitem id="menu_payroll_taxes"
              name="Payroll Taxes"
              parent="menu_payroll_reports"
              action="action_payroll_taxes_wizard"
              sequence="20"
              groups="hr_payroll_community.group_hr_payroll_community_user"/>

    <!-- Report 3: Payroll Accounting -->
    <menuitem id="menu_payroll_accounting"
              name="Payroll Accounting"
              parent="menu_payroll_reports"
              action="action_payroll_accounting_wizard"
              sequence="30"
              groups="hr_payroll_community.group_hr_payroll_community_manager"/>

    <!-- Report 4: Liquidation Forms -->
    <menuitem id="menu_liquidation_forms"
              name="Liquidation Forms"
              parent="menu_payroll_reports"
              action="action_liquidation_wizard"
              sequence="40"
              groups="hr_payroll_community.group_hr_payroll_community_manager"/>

</odoo>
```

## Security Considerations

**Access Groups:**
- `hr_payroll_community.group_hr_payroll_community_user` - Regular payroll users
- `hr_payroll_community.group_hr_payroll_community_manager` - Payroll managers

**Menu Visibility:**
- Disbursement reports: All payroll users
- Tax reports: All payroll users
- Accounting reports: Payroll managers only (sensitive financial data)
- Liquidation forms: Payroll managers only (employee departure)

## Benefits of This Approach

**For Users:**
- ✅ Easy access to reports from main menu
- ✅ Flexible filtering and parameter selection
- ✅ No need to navigate to specific records first
- ✅ Batch reporting across multiple employees/periods

**For Business:**
- ✅ Standardized reporting templates
- ✅ Audit trail of report generation
- ✅ Compliance with Venezuelan labor/tax laws
- ✅ Integration with accounting system

**For Developers:**
- ✅ Clean separation of concerns (wizard + report)
- ✅ Reusable wizard patterns
- ✅ Easy to extend with new reports
- ✅ Follows Odoo best practices

## Next Steps

1. **Get User Confirmation:**
   - Confirm wizard-based approach vs simple PDF reports
   - Prioritize which report to implement first
   - Clarify specific requirements for each report

2. **Start with Phase 1:**
   - Create Reports submenu structure
   - Add placeholder menu items
   - Test menu visibility and access

3. **Implement Reports Incrementally:**
   - Start with Disbursement Detail (easiest - we have template)
   - Then Taxes (important for compliance)
   - Then Accounting (requires understanding journal entries)
   - Finally Liquidation (most complex - legal requirements)

## Questions for User

1. **Report Priority:** Which report should we implement first?
2. **Wizard vs Direct Print:** Do you want parameter selection wizards or direct print buttons?
3. **Date Range:** All reports should support custom date ranges?
4. **Export Formats:** PDF only, or also Excel/CSV export?
5. **Liquidation Logic:** Do you have specific Venezuelan labor law formulas for severance calculations?

## References

- Odoo Reporting Framework: QWeb Reports
- Existing Report: `disbursement_list_report.xml` (already implemented)
- Wizard Pattern: `hr_payslips_employees_views.xml` (batch generation wizard)
- Menu Structure: `hr_payroll_community/views/hr_contract_views.xml`

**Version:** To be implemented in 17.0.1.6.0
