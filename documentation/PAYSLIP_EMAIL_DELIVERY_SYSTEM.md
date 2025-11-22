# Payslip Email Delivery System

> ⚠️ **DEPRECATED - 2025-11-22**
>
> This custom email delivery system has been **DECOMMISSIONED** and replaced by the professional **hr_payslip_monthly_report** module (Cybrosys).
>
> **Migration:** Use hr_payslip_monthly_report for automatic email sending on payslip confirmation and mass payslip operations.
>
> **Archive:** Git tag `v1.28.0-phase2-final` preserves this implementation.
>
> **Decommission Plan:** See [PHASE2_EMAIL_DECOMMISSION_PLAN.md](PHASE2_EMAIL_DECOMMISSION_PLAN.md)

---

**Status:** 🔴 DECOMMISSIONED (v1.28.0 → v1.29.0)
**Module:** `ueipab_payroll_enhancements` (removed in v1.29.0)
**Last Updated:** 2025-11-22

## Overview

Automated email delivery system for sending payslips to employees via email with professional PDF attachments. Supports both regular payslips and AGUINALDOS (Christmas bonus) with batch processing capabilities.

---

## Features

### 1. Batch Email Wizard
- **Location:** Payroll > Reporting > Send by Email
- Select multiple payslips for batch processing
- Template type selector (Regular Payslip / AGUINALDOS)
- Real-time progress tracking
- Detailed success/failure logging

### 2. Professional PDF Reports

**Regular Payslip Template:**
- Employee information header
- Credits section (Salary Base, Bonos, Otros Bonos)
- Deductions breakdown (IVSS, FAOV, INCES, ARI)
- Total calculation with exchange rate display
- Company branding with purple gradient theme

**AGUINALDOS Template:**
- Christmas-themed design (red gradient)
- Employee information header
- Aguinaldos amount (2 months salary, paid in 2 installments)
- Note: No deductions for aguinaldos
- Total calculation with exchange rate display

### 3. Email Templates

**Regular Payslip Email:**
- Template: "Payslip Email - Employee Delivery"
- Subject: `Comprobante de Pago - {{ object.number }}`
- Auto-attaches PDF via `report_template_ids` field

**AGUINALDOS Email:**
- Template: "Aguinaldos Email - Christmas Bonus Delivery"
- Subject: `🎄 Aguinaldos (Bono Navideño) - {{ object.number }}`
- Auto-attaches PDF via `report_template_ids` field

---

## Technical Architecture

### Report Model Pattern (Pre-Formatting Approach)

**Critical Discovery:** QWeb PDF templates cannot execute Python methods like `.format()` or `.strftime()`. All formatting must be done in the report model's `_get_report_values()` method.

```python
class AguinaldosEmailReport(models.AbstractModel):
    _name = 'report.ueipab_payroll_enhancements.report_aguinaldos_email_document'

    def _get_report_values(self, docids, data=None):
        payslips = self.env['hr.payslip'].browse(docids)
        formatted_data = {}

        for payslip in payslips:
            # Get exchange rate
            exchange_rate = getattr(payslip, 'exchange_rate_used', None) or 241.5780

            # Get aguinaldos line
            aguinaldos_line = payslip.line_ids.filtered(lambda l: l.code == 'AGUINALDOS')
            aguinaldos_total = aguinaldos_line.total if aguinaldos_line else 0.0

            # PRE-FORMAT dates (cannot use strftime in QWeb)
            date_from_str = payslip.date_from.strftime('%d/%m/%Y') if payslip.date_from else 'N/A'
            date_to_str = payslip.date_to.strftime('%d/%m/%Y') if payslip.date_to else 'N/A'

            # PRE-FORMAT amounts with thousand separators
            aguinaldos_veb = aguinaldos_total * exchange_rate

            formatted_data[payslip.id] = {
                'employee_name': payslip.employee_id.name or 'N/A',
                'period': f"{date_from_str} → {date_to_str}",
                'aguinaldos_veb': f"{aguinaldos_veb:,.2f}",  # Pre-formatted string
                'exchange_rate': f"{exchange_rate:,.4f}",
            }

        return {
            'doc_ids': docids,
            'doc_model': 'hr.payslip',
            'docs': payslips,
            'formatted_data': formatted_data,  # Pass pre-formatted dict
        }
```

### QWeb Template Usage (No Python Calls)

```xml
<template id="report_aguinaldos_email_document">
    <t t-call="web.basic_layout">
        <t t-foreach="docs" t-as="o">
            <!-- Set formatted data for this payslip -->
            <t t-set="fmt" t-value="formatted_data[o.id]"/>

            <div class="page">
                <!-- Employee name - NO Python calls, just variable access -->
                <td><t t-esc="fmt['employee_name']"/></td>

                <!-- Period - Already formatted as string -->
                <td><t t-esc="fmt['period']"/></td>

                <!-- Amount - Already formatted with thousand separators -->
                <td>Bs. <t t-esc="fmt['aguinaldos_veb']"/></td>
            </div>
        </t>
    </t>
</template>
```

### Wizard Email Sending (Odoo Standard Pattern)

```python
class PayslipEmailWizard(models.TransientModel):
    _name = 'payslip.email.wizard'

    def action_send_emails(self):
        for payslip in self.payslip_ids:
            # Get employee email
            email_to = payslip.employee_id.work_email

            # Use Odoo's standard send_mail() - automatically generates and attaches PDF
            self.template_id.send_mail(
                payslip.id,
                force_send=True,
                raise_exception=True
            )
```

**Key Pattern:** Email template's `report_template_ids` field links to PDF report. Calling `template.send_mail()` automatically:
1. Generates PDF using linked report
2. Attaches PDF to email
3. Sends email via SMTP

---

## Key Technical Learnings

### 1. QWeb PDF Rendering Limitations

**Problem:** QWeb PDF templates use a restricted Python environment where method calls like `.format()`, `.strftime()`, and even `hasattr()` fail with "TypeError: 'NoneType' object is not callable".

**Solution:** Pre-format ALL values in the report model's `_get_report_values()` method:
- Dates → strings using `strftime('%d/%m/%Y')`
- Numbers → formatted strings using f-strings with `:,.2f` format
- Complex calculations → computed in Python, passed as simple values

### 2. Net Amount Field Discovery

**Problem:** `hr.payslip` model has no `net_wage` field.

**Solution:** Get net amount from payslip lines:
```python
net_line = payslip.line_ids.filtered(lambda l: l.code == 'VE_NET_V2')
if not net_line:
    net_line = payslip.line_ids.filtered(lambda l: l.code == 'VE_NET')
net_amount = net_line.total if net_line else 0.0
```

### 3. QWeb Template Caching

**Problem:** Template changes not reflecting even after module restart.

**Solution:** Force module upgrade to reload cached templates:
```python
# Via Odoo shell
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
module.button_immediate_upgrade()
```

Or update module version in `__manifest__.py` to trigger automatic upgrade.

### 4. Odoo Standard Email + PDF Pattern

**Discovery:** Don't manually generate PDFs in wizard code. Instead:
1. Create QWeb PDF report with `report_type='qweb-pdf'`
2. Create email template
3. Link email template to report via `report_template_ids` (many2many field)
4. Call `template.send_mail(record_id)` - PDF auto-attached!

This is the **standard Odoo pattern** used across all core modules.

---

## File Structure

```
ueipab_payroll_enhancements/
├── models/
│   └── payslip_email_report.py          # Report models with pre-formatting logic
├── wizard/
│   ├── payslip_email_wizard.py          # Batch email wizard TransientModel
│   └── payslip_email_wizard_view.xml    # Wizard UI (3 states: draft/sending/done)
├── reports/
│   ├── payslip_email_report.xml         # Regular payslip QWeb template
│   └── aguinaldos_email_report.xml      # AGUINALDOS QWeb template
├── data/
│   └── email_templates/
│       ├── payslip_email_template.xml   # Regular payslip email
│       └── aguinaldos_email_template.xml # AGUINALDOS email
└── views/
    └── payroll_reports_menu.xml         # Menu: "Send by Email"
```

---

## Usage

### Send Payslips via Email

1. Navigate to **Payroll > Reporting > Send by Email**
2. Select one or more payslips
3. Choose template type:
   - **Regular Payslip** - For normal biweekly/monthly payslips
   - **AGUINALDOS (Christmas Bonus)** - For December Christmas bonus
4. Click **Send Emails**
5. Review detailed log showing success/failure for each payslip

### Email Configuration

Ensure SMTP is configured in Odoo:
- **Settings > Technical > Outgoing Mail Servers**
- Default: smtp.gmail.com (port 587, TLS)
- Sender: configured email account

### Testing

**Test Payslip:** SLIP/943
- Employee: Gustavo Perdomo
- Email: gustavo.perdomo@ueipab.edu.ve
- Period: 2025-12-01 → 2025-12-15
- Template: AGUINALDOS

**Expected PDF Size:** ~42KB

---

## Troubleshooting

### Email Not Received

1. Check wizard log for errors
2. Verify employee has `work_email` set
3. Check spam/junk folder
4. Verify SMTP configuration: **Settings > Technical > Outgoing Mail Servers**
5. Check Odoo mail queue: **Settings > Technical > Emails**

### PDF Generation Errors

**Symptom:** "TypeError: 'NoneType' object is not callable" in QWeb template

**Cause:** Python method calls (`.format()`, `.strftime()`, etc.) in QWeb PDF templates

**Fix:** Move all formatting to report model's `_get_report_values()` method

### Template Changes Not Applying

**Symptom:** Changes to XML templates not visible in generated PDF

**Cause:** QWeb templates heavily cached in database

**Fix:**
```bash
# Option 1: Force module upgrade via shell
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http <<EOF
module = env['ir.module.module'].search([('name', '=', 'ueipab_payroll_enhancements')])
module.button_immediate_upgrade()
EOF

# Option 2: Update module version in __manifest__.py and restart
```

---

## Version History

- **v1.28.0** (2025-11-22): Phase 2 complete - PDF generation working with pre-formatting approach
- **v1.27.0** (2025-11-22): Initial email delivery system implementation

---

## Future Enhancements (Phase 3)

- [ ] Server action for right-click "Send Email" on payslip tree/form view
- [ ] Email preview before sending
- [ ] CC/BCC options for HR department
- [ ] Attachment of additional documents (contratos, liquidaciones)
- [ ] Email delivery status tracking
- [ ] Retry failed emails
- [ ] Schedule email sending (e.g., every Friday at 5 PM)

---

**Report Issues:** Contact HR or technical support at recursoshumanos@ueipab.edu.ve
