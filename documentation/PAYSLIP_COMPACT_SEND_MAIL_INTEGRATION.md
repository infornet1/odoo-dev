# Payslip Compact Report - Send Mail Integration Analysis

**Date:** 2025-11-22
**Status:** 📋 ANALYSIS - Integration Options
**Purpose:** Determine how "Send Mail" functionality will work with new custom report

---

## Current Send Mail System

### **How It Works Now** (hr_payslip_monthly_report module)

**Button Location:** hr.payslip form view (header)

**Workflow:**
```
1. User opens payslip (e.g., SLIP/854)
   ↓
2. Clicks "Send Mail" button
   ↓
3. action_payslip_send() method called
   ↓
4. Opens email compose wizard
   ↓
5. Email template loads:
   - Template: "Monthly Payslip Email"
   - Attachment: Standard payslip PDF report
   - Report used: hr_payroll_community.hr_payslip_report_action
   ↓
6. User sends email
   ↓
7. Employee receives email with PDF attachment
```

**Key Components:**
```python
# File: hr_payslip_monthly_report/models/hr_payslip.py
def action_payslip_send(self):
    """Opens email compose wizard"""
    self.ensure_one()
    self.write({'is_send_mail': True})

    # Get email template
    template = self.env.ref('hr_payslip_monthly_report.email_template_payslip')

    # Open composer
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'mail.compose.message',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_template_id': template.id,
            ...
        }
    }
```

**Email Template:**
```xml
<!-- File: hr_payslip_monthly_report/data/mail_template_data.xml -->
<record id="email_template_payslip" model="mail.template">
    <field name="name">Monthly Payslip Email</field>
    <field name="subject">Ref {{object.number}}</field>
    <field name="body_html">Hi, Here by attaching payslip details...</field>

    <!-- This is the key: which report PDF to attach -->
    <field name="report_template_ids" eval="[(4, ref('hr_payroll_community.hr_payslip_report_action'))]"/>
</record>
```

**Problem:** Email always uses the standard `hr_payroll_community` report PDF. It has no currency selection.

---

## Challenge with New Custom Report

### **Why Direct Integration is Complex**

**Standard Report (Current):**
```
hr.payslip → Print → PDF generated immediately
                   ↓
                Email attachment (ready)
```

**Custom Report (New):**
```
hr.payslip → Open wizard → Select currency → Generate PDF
                         ↓
                      Email attachment (needs extra step)
```

**Issue:** Our custom report requires a wizard (for currency selection) BEFORE generating PDF. The email template expects a direct report reference.

---

## Integration Options

### **Option 1: Separate "Send Compact Payslip" Button** ⭐ (Recommended)

**Approach:** Add new button alongside existing "Send Mail"

**Button Placement:**
```xml
<xpath expr='//button[@name="action_compute_sheet"]' position='after'>
    <!-- Existing "Send Mail" button -->
    <button string="Send Mail"
            name="action_payslip_send"
            type="object"
            class="oe_highlight"
            invisible="is_send_mail == True"/>

    <!-- NEW: Send Compact Payslip button -->
    <button string="Send Compact Payslip"
            name="action_send_compact_payslip"
            type="object"
            class="btn-primary"
            invisible="is_send_mail == True"/>
</xpath>
```

**Workflow:**
```
1. User opens payslip
   ↓
2. Clicks "Send Compact Payslip" button
   ↓
3. Opens currency selection wizard
   ├─ Select currency (USD/VEB)
   ├─ Select exchange rate option (if VEB)
   └─ Preview option (optional)
   ↓
4. User clicks "Send Email"
   ↓
5. Method generates PDF with selected currency
   ↓
6. Opens email compose wizard with:
   - Template: Custom compact payslip email
   - Attachment: Generated compact PDF
   - Subject: "[Compact] Comprobante de Pago - SLIP/XXX"
   ↓
7. User sends email
   ↓
8. Employee receives email with compact PDF
```

**Implementation:**
```python
# File: ueipab_payroll_enhancements/models/hr_payslip.py

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_send_compact_payslip(self):
        """
        Open wizard to send compact payslip via email
        User selects currency, then sends email
        """
        self.ensure_one()

        return {
            'name': 'Send Compact Payslip',
            'type': 'ir.actions.act_window',
            'res_model': 'payslip.compact.send.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_id': self.id,
            }
        }
```

```python
# File: ueipab_payroll_enhancements/wizard/payslip_compact_send_wizard.py

class PayslipCompactSendWizard(models.TransientModel):
    _name = 'payslip.compact.send.wizard'
    _description = 'Send Compact Payslip Wizard'

    payslip_id = fields.Many2one('hr.payslip', required=True)

    # Currency selection
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)

    # Exchange rate options (if VEB)
    use_custom_rate = fields.Boolean(default=False)
    custom_exchange_rate = fields.Float(digits=(12, 4))
    rate_date = fields.Date()

    def action_send_email(self):
        """
        Generate compact PDF and send via email
        """
        self.ensure_one()

        # 1. Generate PDF report with selected currency
        report = self.env.ref('ueipab_payroll_enhancements.action_report_payslip_compact')
        pdf_content, _ = report._render_qweb_pdf(
            self.payslip_id.ids,
            data={
                'currency_id': self.currency_id.id,
                'use_custom_rate': self.use_custom_rate,
                'custom_exchange_rate': self.custom_exchange_rate,
                'rate_date': self.rate_date,
            }
        )

        # 2. Create attachment
        filename = f"Comprobante_Pago_{self.payslip_id.number.replace('/', '_')}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'mimetype': 'application/pdf'
        })

        # 3. Get email template
        template = self.env.ref('ueipab_payroll_enhancements.email_template_compact_payslip')

        # 4. Mark as sent
        self.payslip_id.write({'is_send_mail': True})

        # 5. Open email composer with attachment
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'hr.payslip',
                'default_res_ids': self.payslip_id.ids,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'default_attachment_ids': [(4, attachment.id)],
                'force_email': True,
            }
        }
```

**Email Template:**
```xml
<record id="email_template_compact_payslip" model="mail.template">
    <field name="name">Compact Payslip Email</field>
    <field name="model_id" ref="hr_payroll_community.model_hr_payslip"/>
    <field name="subject">[Comprobante] Pago {{object.number}} - {{object.date_from.strftime('%B %Y')}}</field>
    <field name="email_to">{{object.employee_id.private_email}}</field>
    <field name="body_html"><![CDATA[
        <p>Estimado(a) {{object.employee_id.name}},</p>
        <p>Adjunto encontrará su comprobante de pago correspondiente al período {{object.date_from.strftime('%B %Y')}}.</p>
        <p><strong>Referencia:</strong> {{object.number}}</p>
        <p>Saludos cordiales,<br/>
        Recursos Humanos UEIPAB</p>
    ]]></field>
</record>
```

**Pros:**
- ✅ **Simple for users** - Clear separation (two distinct buttons)
- ✅ **Flexible** - Currency selection before sending
- ✅ **No conflicts** - Original "Send Mail" unchanged
- ✅ **Easy to maintain** - All logic in new code

**Cons:**
- ⚠️ Two buttons might be confusing initially (need user training)
- ⚠️ Extra button in header (minor UI clutter)

---

### **Option 2: Enhance Existing "Send Mail" Button**

**Approach:** Modify existing button to offer report choice

**Workflow:**
```
1. User clicks "Send Mail" button
   ↓
2. Opens enhanced wizard with:
   ├─ Report type: [○ Standard  ○ Compact]
   ├─ If compact: Currency selection
   └─ If compact: Exchange rate options
   ↓
3. User clicks "Send Email"
   ↓
4. Generates appropriate PDF
   ↓
5. Opens email composer with PDF attached
```

**Implementation:**
```python
# Override existing method
def action_payslip_send(self):
    """Enhanced: Choose report type before sending"""
    self.ensure_one()

    return {
        'name': 'Send Payslip',
        'type': 'ir.actions.act_window',
        'res_model': 'payslip.send.wizard',  # Enhanced wizard
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_payslip_id': self.id,
        }
    }
```

**Wizard:**
```python
class PayslipSendWizard(models.TransientModel):
    _name = 'payslip.send.wizard'

    payslip_id = fields.Many2one('hr.payslip', required=True)
    report_type = fields.Selection([
        ('standard', 'Standard Payslip'),
        ('compact', 'Compact Payslip')
    ], required=True, default='standard')

    # Currency fields (shown only if compact selected)
    currency_id = fields.Many2one('res.currency')
    use_custom_rate = fields.Boolean()
    custom_exchange_rate = fields.Float()

    @api.onchange('report_type')
    def _onchange_report_type(self):
        if self.report_type == 'standard':
            self.currency_id = False
```

**Pros:**
- ✅ **Single entry point** - One button for all email sends
- ✅ **Centralized** - All email logic in one place
- ✅ **User choice** - Flexible report selection

**Cons:**
- ❌ **Modifies existing** - Changes working functionality (risky)
- ❌ **More complex wizard** - Conditional fields
- ❌ **Backwards compatibility** - Must maintain original behavior

---

### **Option 3: Configuration Setting**

**Approach:** Let admin choose default report in settings

**Settings:**
```
Payroll Settings:
  [ ] Use Compact Payslip for Emails
  If checked:
    Default Currency: [USD ▼]
    Exchange Rate: [○ Auto  ○ Latest  ○ Custom]
```

**Pros:**
- ✅ **Admin controlled** - Set once, applies to all
- ✅ **Consistent** - Everyone uses same report

**Cons:**
- ❌ **Inflexible** - Can't choose per-payslip
- ❌ **Currency locked** - No per-send currency selection
- ❌ **Not suitable** - Users NEED to choose currency each time

---

### **Option 4: Manual Process (No Integration)**

**Approach:** Users generate report manually, then email separately

**Workflow:**
```
1. User generates compact report manually (with wizard)
2. Downloads PDF
3. Composes email manually
4. Attaches PDF
5. Sends
```

**Pros:**
- ✅ **Simple implementation** - No email integration needed
- ✅ **Maximum flexibility** - User full control

**Cons:**
- ❌ **Poor UX** - Too many manual steps
- ❌ **No tracking** - Can't tell if payslip was emailed
- ❌ **Inconsistent** - Users might forget to send

---

## Recommendation: Option 1 (Separate Button)

### **Why Option 1 is Best**

**1. Clear User Intent**
```
"Send Mail" button = Standard report (existing, familiar)
"Send Compact Payslip" button = New compact report (with currency)
```

**2. No Breaking Changes**
- Original functionality 100% unchanged
- hr_payslip_monthly_report module untouched
- No risk to working email system

**3. Follows Existing Pattern**
Your reports already use wizards:
- Relación de Liquidación → Wizard → Generate
- Prestaciones Interest → Wizard → Generate
- Finiquito → Wizard → Generate
- **Compact Payslip → Wizard → Send Email** (same pattern!)

**4. Easy to Implement**
All new code in `ueipab_payroll_enhancements`:
- New wizard model
- New method on hr.payslip
- New button in view
- New email template

**5. User Training**
Simple message:
> "We added a new button 'Send Compact Payslip' that lets you choose USD or VEB before sending. The old 'Send Mail' button still works the same."

---

## Implementation Details (Option 1)

### **File Structure**
```
ueipab_payroll_enhancements/
├── models/
│   ├── hr_payslip.py (add action_send_compact_payslip method)
│   └── __init__.py
├── wizard/
│   ├── payslip_compact_send_wizard.py (NEW)
│   ├── payslip_compact_send_wizard_view.xml (NEW)
│   └── __init__.py
├── views/
│   └── hr_payslip_view.xml (add "Send Compact Payslip" button)
├── data/
│   └── email_template_compact_payslip.xml (NEW)
└── __manifest__.py
```

### **Button View**
```xml
<!-- File: views/hr_payslip_view.xml -->
<record id="view_hr_payslip_form_send_compact" model="ir.ui.view">
    <field name="name">hr.payslip.form.send.compact</field>
    <field name="model">hr.payslip</field>
    <field name="inherit_id" ref="hr_payroll_community.hr_payslip_view_form"/>
    <field name="arch" type="xml">
        <button name="action_payslip_send" position="after">
            <!-- NEW BUTTON -->
            <button string="Send Compact Payslip"
                    name="action_send_compact_payslip"
                    type="object"
                    icon="fa-envelope"
                    class="btn-primary"
                    invisible="is_send_mail == True"
                    help="Send compact payslip with currency selection"/>
        </button>
    </field>
</record>
```

### **Wizard View**
```xml
<!-- File: wizard/payslip_compact_send_wizard_view.xml -->
<record id="view_payslip_compact_send_wizard_form" model="ir.ui.view">
    <field name="name">payslip.compact.send.wizard.form</field>
    <field name="model">payslip.compact.send.wizard</field>
    <field name="arch" type="xml">
        <form string="Send Compact Payslip">
            <group>
                <field name="payslip_id" invisible="1"/>

                <separator string="Currency Selection"/>
                <field name="currency_id" widget="radio"
                       options="{'horizontal': true}"/>
            </group>

            <group string="Exchange Rate Options"
                   invisible="currency_id.name != 'VEB'">
                <field name="use_custom_rate"/>
                <field name="custom_exchange_rate"
                       invisible="not use_custom_rate"/>
                <field name="rate_date"
                       invisible="use_custom_rate"/>
            </group>

            <footer>
                <button name="action_send_email"
                        string="Send Email"
                        type="object"
                        class="btn-primary"/>
                <button string="Cancel"
                        special="cancel"
                        class="btn-secondary"/>
            </footer>
        </form>
    </field>
</record>
```

### **Key Methods**

**1. Button Action (hr.payslip model)**
```python
def action_send_compact_payslip(self):
    """Open wizard to send compact payslip"""
    self.ensure_one()
    return {
        'name': 'Send Compact Payslip',
        'type': 'ir.actions.act_window',
        'res_model': 'payslip.compact.send.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {'default_payslip_id': self.id}
    }
```

**2. Send Email (wizard model)**
```python
def action_send_email(self):
    """Generate PDF and send email"""
    # 1. Prepare report data with currency
    report_data = {
        'currency_id': self.currency_id.id,
        'use_custom_rate': self.use_custom_rate,
        'custom_exchange_rate': self.custom_exchange_rate,
        'rate_date': self.rate_date,
    }

    # 2. Generate PDF
    report = self.env.ref('ueipab_payroll_enhancements.action_report_payslip_compact')
    pdf, _ = report._render_qweb_pdf(self.payslip_id.ids, data=report_data)

    # 3. Create attachment
    attachment = self.env['ir.attachment'].create({
        'name': f"Comprobante_{self.payslip_id.number.replace('/', '_')}.pdf",
        'datas': base64.b64encode(pdf),
        'res_model': 'hr.payslip',
        'res_id': self.payslip_id.id,
    })

    # 4. Mark as sent
    self.payslip_id.is_send_mail = True

    # 5. Open email composer
    template = self.env.ref('ueipab_payroll_enhancements.email_template_compact_payslip')
    return {
        'type': 'ir.actions.act_window',
        'res_model': 'mail.compose.message',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_template_id': template.id,
            'default_attachment_ids': [(4, attachment.id)],
            ...
        }
    }
```

---

## User Experience

### **Scenario 1: Send with USD**
```
1. User: Opens SLIP/854
2. User: Clicks "Send Compact Payslip"
3. System: Opens wizard, USD selected by default
4. User: Clicks "Send Email"
5. System: Generates PDF in USD, opens email composer
6. User: Reviews email, clicks "Send"
7. Employee: Receives email with USD payslip PDF
```

### **Scenario 2: Send with VEB**
```
1. User: Opens SLIP/854
2. User: Clicks "Send Compact Payslip"
3. System: Opens wizard
4. User: Selects VEB currency
5. User: Selects rate date or enters custom rate
6. User: Clicks "Send Email"
7. System: Generates PDF in VEB with exchange rate shown, opens email composer
8. User: Reviews email (attachment name shows VEB amounts), clicks "Send"
9. Employee: Receives email with VEB payslip PDF
```

### **Scenario 3: Standard Report**
```
1. User: Opens SLIP/854
2. User: Clicks "Send Mail" (existing button)
3. System: Opens email composer directly (no wizard)
4. System: Attaches standard multi-page report PDF
5. User: Clicks "Send"
6. Employee: Receives email with standard payslip PDF
```

---

## Comparison Summary

| Feature | Option 1 (Separate Button) | Option 2 (Enhanced Button) | Option 3 (Config) | Option 4 (Manual) |
|---------|---------------------------|---------------------------|-------------------|-------------------|
| **User chooses currency** | ✅ Per send | ✅ Per send | ❌ Admin only | ✅ Manual |
| **Backwards compatible** | ✅ Yes | ⚠️ Modifies existing | ✅ Yes | ✅ Yes |
| **Easy to implement** | ✅ Yes | ⚠️ Complex | ✅ Medium | ✅ Simple |
| **Flexibility** | ✅ High | ✅ High | ❌ Low | ✅ Highest |
| **User training needed** | ⚠️ Minimal | ⚠️ Moderate | ✅ None | ❌ Significant |
| **Code maintenance** | ✅ Easy (isolated) | ❌ Complex (shared) | ✅ Medium | ✅ Minimal |
| **Recommended** | ⭐ **YES** | Maybe | No | No |

---

## Updated Implementation Plan

### **Phase 1: Core Report (Already Planned)**
1. ✅ Create wizard for report generation
2. ✅ Create report model with currency conversion
3. ✅ Create compact template
4. ✅ Add report action

### **Phase 2: Email Integration (NEW)**
1. ✅ Create send wizard model (`payslip_compact_send_wizard.py`)
2. ✅ Create send wizard view (XML)
3. ✅ Add button to hr.payslip form view
4. ✅ Add method `action_send_compact_payslip()` to hr.payslip
5. ✅ Create email template (compact version)
6. ✅ Update __manifest__.py

### **Phase 3: Testing**
1. ✅ Test report generation (manual)
2. ✅ Test email send with USD
3. ✅ Test email send with VEB (auto rate)
4. ✅ Test email send with VEB (custom rate)
5. ✅ Test email send with VEB (rate date)
6. ✅ Verify PDF attachment correct
7. ✅ Verify email template rendering
8. ✅ Test "Reset Send Status" button still works

---

## Timeline Update

| Phase | Tasks | Original Estimate | With Email | Total |
|-------|-------|-------------------|------------|-------|
| Phase 1 | Core report | 2.5 hours | - | 2.5 hours |
| Phase 2 | Email integration | - | +1.5 hours | 1.5 hours |
| Phase 3 | Testing | 45 min | +30 min | 75 min |
| **Total** | | **2.5 hours** | **+2 hours** | **~4.5 hours** |

---

## Questions for User

1. **Approve Option 1** (separate "Send Compact Payslip" button)?
   - ✅ Recommended approach
   - Clear separation from existing functionality
   - Currency selection before send

2. **Button Label** - What should it say?
   - "Send Compact Payslip"
   - "Enviar Comprobante Compacto"
   - "Send with Currency Selection"
   - Other?

3. **Email Subject** - Format preference?
   - `[Comprobante] Pago SLIP/854 - Octubre 2025`
   - `Comprobante de Pago - SLIP/854 - Oct 2025`
   - Other?

4. **Keep both buttons?** (Send Mail + Send Compact)
   - Recommended: YES (both available)
   - Alternative: Replace "Send Mail" entirely?

5. **Default currency** in wizard?
   - USD (current company currency)
   - VEB (most recent used)
   - Last used per user?

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Users confused by 2 buttons** | Medium | Clear labels, tooltips, training |
| **Email template issues** | Low | Test with various payslip types |
| **PDF generation fails** | Medium | Error handling, fallback to manual |
| **Attachment too large** | Low | Compact report is smaller than original |
| **Currency conversion errors** | Medium | Reuse proven Relación code |

---

## Next Steps (If Approved)

1. ✅ Implement core compact report (Phases 1-5 from original plan)
2. ✅ Add email integration (send wizard + button)
3. ✅ Test thoroughly
4. ✅ Deploy to testing database
5. ✅ User acceptance testing
6. ✅ Document usage
7. ✅ Production deployment

---

**Status:** 📋 READY FOR APPROVAL

Please confirm:
- ✅ Option 1 (Separate button) acceptable?
- ✅ Button label preference?
- ✅ Ready to proceed with implementation?

---
