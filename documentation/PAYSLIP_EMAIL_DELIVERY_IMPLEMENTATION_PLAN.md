# Payslip Email Delivery - Implementation Plan

**Date:** 2025-11-21
**Status:** 📋 DESIGN PHASE
**Module:** `ueipab_payroll_enhancements`

## Overview

Implement bulk and single payslip email delivery functionality in the **Reporting** menu, allowing HR staff to send payslip notifications to employees via email with professional HTML templates and PDF attachments.

---

## Executive Summary

### Current State

**✅ Assets Available:**
- HTML email template: `/var/www/dev/odoo_api_bridge/mass_email/templates/payslip_builtin.html`
- Python email sender: `/var/www/dev/odoo_api_bridge/mass_email/email_sender.py`
- Test script: `/var/www/dev/odoo_api_bridge/test_single_payslip_email.py`
- Working SMTP config for `recursoshumanos@ueipab.edu.ve`

**🎯 Goal:**
Integrate email delivery directly into Odoo's **Payroll > Reporting** menu with:
1. **Single Send:** Send one payslip via email wizard
2. **Bulk Send:** Send multiple payslips in batches with progress tracking
3. **Template Support:** Use existing HTML template with Odoo QWeb integration
4. **PDF Attachments:** Attach PDF payslip reports automatically
5. **Error Handling:** Track success/failure with detailed logs

---

## Architecture Design

### Option A: Native Odoo Implementation (RECOMMENDED) ⭐

**Approach:** Fully integrate email functionality using Odoo's built-in mail system

**Advantages:**
- Native Odoo mail tracking and logging
- Uses existing `mail.template` infrastructure
- Proper access control and security
- Integrated with Odoo's queue system
- Professional UI/UX with wizards

**Components:**
1. **Email Template (QWeb):** Odoo `mail.template` with HTML body
2. **Wizard Model:** TransientModel for single/bulk sending
3. **Server Actions:** Optional scheduled/automated sending
4. **Menu Items:** Add to Reporting menu

**Implementation Complexity:** Medium
**Maintenance:** Low (uses standard Odoo patterns)
**User Experience:** Excellent (native Odoo UI)

### Option B: Hybrid Approach (External SMTP Bridge)

**Approach:** Keep external email sender, call from Odoo via RPC/API

**Advantages:**
- Reuse existing `/var/www/dev/odoo_api_bridge` infrastructure
- Keep existing SMTP configuration and tracking
- Faster initial development

**Disadvantages:**
- Requires external service dependency
- More complex error handling
- Harder to maintain and debug
- Non-standard Odoo pattern

**Recommendation:** ❌ Not recommended - adds unnecessary complexity

---

## Recommended Implementation: Option A (Native Odoo)

### Phase 1: Email Template Integration

**Objective:** Convert existing HTML template to Odoo `mail.template`

#### 1.1 Convert HTML Template to QWeb

**File:** `addons/ueipab_payroll_enhancements/data/email_templates/payslip_email_template.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="email_template_payslip_delivery" model="mail.template">
        <field name="name">Payslip Email - Employee Delivery</field>
        <field name="model_id" ref="hr_payroll_community.model_hr_payslip"/>
        <field name="subject">💰 Comprobante de Pago - ${object.employee_id.name} (${object.date_from.strftime('%B %Y')})</field>
        <field name="email_from">recursoshumanos@ueipab.edu.ve</field>
        <field name="email_to">${object.employee_id.work_email or object.employee_id.address_home_id.email}</field>
        <field name="auto_delete" eval="True"/>

        <!-- Attach PDF payslip report (optional) -->
        <field name="report_template" ref="hr_payroll_community.action_report_payslip"/>
        <field name="report_name">Comprobante_${object.employee_id.name}_${object.date_from.strftime('%Y%m%d')}</field>

        <field name="body_html" type="html">
<![CDATA[
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        .payslip-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }
        .header p {
            margin: 5px 0 0 0;
            font-size: 16px;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #e0e0e0;
        }
        .info-label {
            font-weight: 600;
            color: #555;
            font-size: 14px;
        }
        .info-value {
            color: #333;
            font-size: 14px;
        }
        .section-title {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 20px;
            margin: 25px -30px 15px -30px;
            font-size: 18px;
            font-weight: 600;
        }
        .amount-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .amount-table td {
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }
        .amount-table .label-col {
            color: #555;
            font-weight: 500;
            width: 60%;
        }
        .amount-table .amount-col {
            text-align: right;
            color: #333;
            font-weight: 600;
            font-size: 15px;
        }
        .total-section {
            background: #f8f9fa;
            padding: 20px;
            margin: 25px -30px;
            border-top: 3px solid #667eea;
            border-bottom: 3px solid #667eea;
        }
        .total-row.final {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
            display: flex;
            justify-content: space-between;
        }
        .bcv-section {
            background: #fff9e6;
            border: 2px dashed #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
        }
        .bcv-section .bcv-label {
            font-size: 14px;
            color: #856404;
            margin-bottom: 5px;
        }
        .bcv-section .bcv-rate {
            font-size: 24px;
            font-weight: bold;
            color: #d39e00;
        }
        .footer {
            background: #f8f9fa;
            padding: 20px 30px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }
        .footer strong {
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="payslip-container">
        <div class="header">
            <h1>💰 Comprobante de Pago</h1>
            <p>Instituto Privado Andrés Bello, CA</p>
        </div>

        <div class="content">
            <!-- Employee Information -->
            <div class="info-row">
                <span class="info-label">📋 Nro. Comprobante:</span>
                <span class="info-value">${object.number} │ ${object.payslip_run_id.name if object.payslip_run_id else 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">📅 Período:</span>
                <span class="info-value">${object.date_from.strftime('%d/%m/%Y')} → ${object.date_to.strftime('%d/%m/%Y')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">👤 Nombre y Apellido:</span>
                <span class="info-value">${object.employee_id.name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">🆔 Cédula:</span>
                <span class="info-value">${object.employee_id.identification_id or 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">💳 Cuenta:</span>
                <span class="info-value">${object.employee_id.bank_account_id.acc_number if object.employee_id.bank_account_id else 'N/A'}</span>
            </div>

            <!-- Credits Section -->
            <div class="section-title">✅ Salario + Bonos</div>
            <table class="amount-table">
                <%
                    salary_v2 = object.line_ids.filtered(lambda l: l.code == 'VE_SALARY_V2')
                    bonus_v2 = object.line_ids.filtered(lambda l: l.code == 'VE_BONUS_V2')
                    extrabonus_v2 = object.line_ids.filtered(lambda l: l.code == 'VE_EXTRABONUS_V2')
                    gross_v2 = object.line_ids.filtered(lambda l: l.code == 'VE_GROSS_V2')

                    # Get exchange rate from payslip
                    exchange_rate = object.exchange_rate_used or 241.5780
                %>
                <tr>
                    <td class="label-col">Salario Base</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format((salary_v2.total if salary_v2 else 0.0) * exchange_rate)}</td>
                </tr>
                <tr>
                    <td class="label-col">Bonos</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format((bonus_v2.total if bonus_v2 else 0.0) * exchange_rate)}</td>
                </tr>
                <tr>
                    <td class="label-col">Otros Bonos</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format((extrabonus_v2.total if extrabonus_v2 else 0.0) * exchange_rate)}</td>
                </tr>
                <tr style="border-top: 2px solid #667eea; font-weight: bold;">
                    <td class="label-col">Total Asignaciones</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format((gross_v2.total if gross_v2 else 0.0) * exchange_rate)}</td>
                </tr>
            </table>

            <!-- Deductions Section -->
            <div class="section-title">❌ Deducciones</div>
            <table class="amount-table">
                <%
                    sso = object.line_ids.filtered(lambda l: l.code == 'VE_SSO_DED_V2')
                    faov = object.line_ids.filtered(lambda l: l.code == 'VE_FAOV_DED_V2')
                    paro = object.line_ids.filtered(lambda l: l.code == 'VE_PARO_DED_V2')
                    ari = object.line_ids.filtered(lambda l: l.code == 'VE_ARI_DED_V2')
                    total_ded = object.line_ids.filtered(lambda l: l.code == 'VE_TOTAL_DED_V2')
                %>
                <tr>
                    <td class="label-col">IVSS (Instituto Venezolano de los Seguros Sociales)</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format(abs(sso.total if sso else 0.0) * exchange_rate)}</td>
                </tr>
                <tr>
                    <td class="label-col">FAOV (Fondo de Ahorro Obligatorio para la Vivienda)</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format(abs(faov.total if faov else 0.0) * exchange_rate)}</td>
                </tr>
                <tr>
                    <td class="label-col">INCES (Instituto Nacional de Capacitación y Educación)</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format(abs(paro.total if paro else 0.0) * exchange_rate)}</td>
                </tr>
                <tr>
                    <td class="label-col">Otras Deducciones</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format(abs(ari.total if ari else 0.0) * exchange_rate)}</td>
                </tr>
                <tr style="border-top: 2px solid #667eea; font-weight: bold;">
                    <td class="label-col">Total Deducciones</td>
                    <td class="amount-col">Bs. ${'{:,.2f}'.format(abs(total_ded.total if total_ded else 0.0) * exchange_rate)}</td>
                </tr>
            </table>

            <!-- Total Section -->
            <div class="total-section">
                <div class="total-row final">
                    <span>💵 Total a Recibir:</span>
                    <span>Bs. ${'{:,.2f}'.format(object.net_wage * exchange_rate)}</span>
                </div>
            </div>

            <!-- Exchange Rate -->
            <div class="bcv-section">
                <div class="bcv-label">Tasa de Cambio (Referencia)</div>
                <div class="bcv-rate">Bs. ${'{:,.4f}'.format(exchange_rate)}</div>
            </div>
        </div>

        <div class="footer">
            <p><strong>📧 ¿Dudas o consultas?</strong></p>
            <p>Si usted tiene alguna duda por favor escribir inmediatamente al correo <strong>recursoshumanos@ueipab.edu.ve</strong></p>
            <p style="margin-top: 15px; color: #999; font-size: 12px;">
                Este es un documento generado automáticamente. Por favor, responda directamente a este correo si tiene dudas.
            </p>
        </div>
    </div>
</body>
</html>
]]>
        </field>
    </record>
</odoo>
```

**Key Features:**
- Uses existing HTML template design
- QWeb expressions for dynamic data (`${object.field}`)
- Automatic exchange rate from payslip
- V2 payroll rule support (VE_SALARY_V2, VE_BONUS_V2, etc.)
- Professional styling (gradient header, responsive layout)

#### 1.2 Create AGUINALDOS-Specific Template

**File:** `addons/ueipab_payroll_enhancements/data/email_templates/aguinaldos_email_template.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="email_template_aguinaldos_delivery" model="mail.template">
        <field name="name">Aguinaldos Email - Employee Delivery</field>
        <field name="model_id" ref="hr_payroll_community.model_hr_payslip"/>
        <field name="subject">🎄 Aguinaldos (Bono Navideño) - ${object.employee_id.name}</field>
        <field name="email_from">recursoshumanos@ueipab.edu.ve</field>
        <field name="email_to">${object.employee_id.work_email or object.employee_id.address_home_id.email}</field>
        <field name="auto_delete" eval="True"/>

        <field name="report_template" ref="hr_payroll_community.action_report_payslip"/>
        <field name="report_name">Aguinaldos_${object.employee_id.name}_${object.date_from.strftime('%Y%m%d')}</field>

        <field name="body_html" type="html">
<![CDATA[
<!-- Similar structure but themed for Christmas bonus -->
<div class="header" style="background: linear-gradient(135deg, #c94b4b 0%, #4b134f 100%);">
    <h1>🎄 Aguinaldos (Bono Navideño)</h1>
    <p>Instituto Privado Andrés Bello, CA</p>
</div>
<!-- ... rest of template with AGUINALDOS rule mapping ... -->
]]>
        </field>
    </record>
</odoo>
```

**Mapping Logic:**
- Check if `payslip_run_id.name` contains "AGUINALDOS"
- Map `AGUINALDOS` line to "Salario Base" display
- Hide deductions section (AGUINALDOS has no deductions)
- Show Christmas-themed styling

---

### Phase 2: Payslip Email Wizard

**Objective:** Create wizard for single/bulk email sending

#### 2.1 Wizard Model

**File:** `addons/ueipab_payroll_enhancements/models/payslip_email_wizard.py`

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PayslipEmailWizard(models.TransientModel):
    """Wizard for sending payslips via email (single or bulk)."""

    _name = 'payslip.email.wizard'
    _description = 'Send Payslips by Email'

    # ========================================
    # FIELDS
    # ========================================

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Payslips to Send',
        required=True,
        help='Select one or more payslips to email'
    )

    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        required=True,
        domain="[('model_id.model', '=', 'hr.payslip')]",
        default=lambda self: self._default_template(),
        help='Email template to use'
    )

    include_pdf = fields.Boolean(
        string='Attach PDF Payslip',
        default=True,
        help='Attach PDF version of payslip'
    )

    send_mode = fields.Selection([
        ('now', 'Send Immediately'),
        ('queue', 'Queue for Later'),
    ], string='Send Mode', default='now', required=True)

    # Progress Tracking
    state = fields.Selection([
        ('draft', 'Ready'),
        ('sending', 'Sending...'),
        ('done', 'Complete'),
    ], default='draft', readonly=True)

    send_log = fields.Html(
        string='Sending Log',
        readonly=True,
        help='Detailed log of email sending results'
    )

    success_count = fields.Integer(
        string='Successfully Sent',
        readonly=True
    )

    error_count = fields.Integer(
        string='Failed',
        readonly=True
    )

    # ========================================
    # DEFAULTS
    # ========================================

    @api.model
    def _default_template(self):
        """Get default template based on payslip type."""
        # Try to get regular payslip template
        template = self.env.ref(
            'ueipab_payroll_enhancements.email_template_payslip_delivery',
            raise_if_not_found=False
        )
        return template.id if template else False

    # ========================================
    # BUSINESS METHODS
    # ========================================

    def action_send_emails(self):
        """Send emails to selected payslips."""
        self.ensure_one()

        if not self.payslip_ids:
            raise UserError(_('No payslips selected'))

        if not self.template_id:
            raise UserError(_('Please select an email template'))

        # Update state
        self.state = 'sending'

        log_lines = []
        success = 0
        error = 0

        for payslip in self.payslip_ids:
            try:
                # Validate recipient
                recipient = self._get_recipient_email(payslip)
                if not recipient:
                    raise ValidationError(
                        _('No email found for employee: %s') % payslip.employee_id.name
                    )

                # Send email
                self._send_payslip_email(payslip, recipient)

                success += 1
                log_lines.append(
                    f'<p style="color: green;">✅ {payslip.number} - '
                    f'{payslip.employee_id.name} → {recipient}</p>'
                )

            except Exception as e:
                error += 1
                log_lines.append(
                    f'<p style="color: red;">❌ {payslip.number} - '
                    f'{payslip.employee_id.name}: {str(e)}</p>'
                )
                _logger.exception(f'Error sending payslip email: {e}')

        # Update results
        self.success_count = success
        self.error_count = error
        self.send_log = '<h4>Email Sending Results</h4>' + ''.join(log_lines)
        self.state = 'done'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Emails Sent'),
                'message': _(
                    f'✅ Sent: {success}/{len(self.payslip_ids)}\n'
                    f'❌ Failed: {error}'
                ),
                'type': 'success' if error == 0 else 'warning',
                'sticky': False,
            }
        }

    def _get_recipient_email(self, payslip):
        """Get employee email address."""
        return (
            payslip.employee_id.work_email or
            payslip.employee_id.address_home_id.email or
            None
        )

    def _send_payslip_email(self, payslip, recipient):
        """Send email for single payslip using template."""

        # Check template type (auto-select AGUINALDOS template if needed)
        if payslip.payslip_run_id and 'AGUINALDOS' in payslip.payslip_run_id.name.upper():
            aguinaldos_template = self.env.ref(
                'ueipab_payroll_enhancements.email_template_aguinaldos_delivery',
                raise_if_not_found=False
            )
            if aguinaldos_template:
                template = aguinaldos_template
            else:
                template = self.template_id
        else:
            template = self.template_id

        # Send via template
        template.send_mail(
            payslip.id,
            force_send=(self.send_mode == 'now'),
            email_values={
                'email_to': recipient,
            }
        )

        _logger.info(f'Payslip {payslip.number} emailed to {recipient}')

    def action_preview_payslips(self):
        """Open tree view of payslips to be sent."""
        return {
            'name': _('Payslips to Email'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.payslip_ids.ids)],
            'context': {'create': False, 'edit': False},
        }
```

#### 2.2 Wizard View

**File:** `addons/ueipab_payroll_enhancements/wizard/payslip_email_wizard_view.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Payslip Email Wizard Form -->
    <record id="payslip_email_wizard_form" model="ir.ui.view">
        <field name="name">payslip.email.wizard.form</field>
        <field name="model">payslip.email.wizard</field>
        <field name="arch" type="xml">
            <form string="Send Payslips by Email">
                <!-- Header Alert -->
                <div class="alert alert-info" role="alert" invisible="state != 'draft'">
                    <p>
                        <i class="fa fa-envelope"></i>
                        Send payslip notifications to employees via email with professional HTML formatting and optional PDF attachments.
                    </p>
                </div>

                <!-- Results Section (shown after sending) -->
                <div class="alert alert-success" role="alert" invisible="state != 'done' or error_count > 0">
                    <h4><i class="fa fa-check-circle"></i> Emails Sent Successfully</h4>
                    <p>All <field name="success_count"/> payslips have been emailed to employees.</p>
                </div>

                <div class="alert alert-warning" role="alert" invisible="state != 'done' or error_count == 0">
                    <h4><i class="fa fa-exclamation-triangle"></i> Partial Success</h4>
                    <p>
                        <strong><field name="success_count"/></strong> sent successfully,
                        <strong><field name="error_count"/></strong> failed. See log below.
                    </p>
                </div>

                <group invisible="state != 'draft'">
                    <!-- Payslip Selection -->
                    <group string="📋 Payslips to Send" colspan="2">
                        <field name="payslip_ids" nolabel="1" colspan="2"
                               widget="many2many_tags"
                               domain="[('state', 'in', ['done', 'paid'])]"/>
                    </group>

                    <!-- Email Configuration -->
                    <group string="✉️ Email Settings">
                        <field name="template_id" required="1"/>
                        <field name="include_pdf"/>
                    </group>

                    <!-- Sending Options -->
                    <group string="⚙️ Send Options">
                        <field name="send_mode" widget="radio"/>
                    </group>
                </group>

                <!-- Log Section (shown after sending) -->
                <group invisible="state != 'done'">
                    <field name="send_log" nolabel="1" colspan="2"/>
                </group>

                <footer>
                    <button name="action_send_emails"
                            string="📤 Send Emails"
                            type="object"
                            class="btn-primary"
                            invisible="state != 'draft'"/>

                    <button name="action_preview_payslips"
                            string="👁️ Preview Payslips"
                            type="object"
                            class="btn-secondary"
                            invisible="state != 'draft'"/>

                    <button string="Close"
                            special="cancel"
                            class="btn-secondary"/>
                </footer>
            </form>
        </field>
    </record>

    <!-- Wizard Action -->
    <record id="action_payslip_email_wizard" model="ir.actions.act_window">
        <field name="name">Send Payslips by Email</field>
        <field name="res_model">payslip.email.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
        <field name="view_id" ref="payslip_email_wizard_form"/>
    </record>

    <!-- Menu Item (under Payroll > Reporting) -->
    <menuitem
        id="menu_payslip_email_delivery"
        name="📧 Send by Email"
        action="action_payslip_email_wizard"
        parent="hr_payroll_community.menu_hr_payroll_reports"
        sequence="25"/>

</odoo>
```

---

### Phase 3: Bulk Email with Batch Processing

**Objective:** Add batch selection and server action support

#### 3.1 Enhanced Wizard for Batch Selection

**Additional Fields:**

```python
# In payslip_email_wizard.py

    batch_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        help='Select all payslips from a batch'
    )

    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        """Auto-populate payslips from selected batch."""
        if self.batch_id:
            payslips = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', self.batch_id.id),
                ('state', 'in', ['done', 'paid']),
            ])
            self.payslip_ids = [(6, 0, payslips.ids)]
```

#### 3.2 Server Action for Batch Context

**File:** `addons/ueipab_payroll_enhancements/data/server_actions.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Server Action: Send Batch Emails -->
    <record id="server_action_send_batch_emails" model="ir.actions.server">
        <field name="name">Send Payslips by Email</field>
        <field name="model_id" ref="hr_payroll_community.model_hr_payslip_run"/>
        <field name="binding_model_id" ref="hr_payroll_community.model_hr_payslip_run"/>
        <field name="binding_view_types">form,list</field>
        <field name="state">code</field>
        <field name="code">
# Get payslips from selected batch
if record:
    action = {
        'name': 'Send Payslips by Email',
        'type': 'ir.actions.act_window',
        'res_model': 'payslip.email.wizard',
        'view_mode': 'form',
        'target': 'new',
        'context': {
            'default_batch_id': record.id,
            'default_payslip_ids': [(6, 0, record.slip_ids.filtered(lambda s: s.state in ['done', 'paid']).ids)],
        }
    }
        </field>
    </record>
</odoo>
```

**Usage:** Right-click on payslip batch → "Send Payslips by Email"

---

### Phase 4: Security & Access Control

#### 4.1 Access Rights

**File:** `addons/ueipab_payroll_enhancements/security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink

# Payslip Email Wizard
access_payslip_email_wizard_user,payslip.email.wizard.user,model_payslip_email_wizard,hr_payroll_community.group_hr_payroll_community_user,1,1,1,1
access_payslip_email_wizard_manager,payslip.email.wizard.manager,model_payslip_email_wizard,hr_payroll_community.group_hr_payroll_community_manager,1,1,1,1
```

#### 4.2 SMTP Configuration

**Odoo Settings > Technical > Email > Outgoing Mail Servers:**

```
Server: smtp.gmail.com
Port: 587
Security: TLS
Username: recursoshumanos@ueipab.edu.ve
Password: naxx shwn eyyv adnk (App Password)
```

**Test:** Settings > Technical > Email > Outgoing Mail Servers → "Test Connection"

---

### Phase 5: Testing & Validation

#### 5.1 Unit Tests

**File:** `addons/ueipab_payroll_enhancements/tests/test_payslip_email.py`

```python
# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install', 'payslip_email')
class TestPayslipEmail(TransactionCase):
    """Test payslip email sending functionality."""

    def setUp(self):
        super().setUp()

        # Create test employee with email
        self.employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': '[email protected]',
        })

        # Create test payslip
        self.payslip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'date_from': '2025-11-01',
            'date_to': '2025-11-15',
            'state': 'done',
        })

        # Get email template
        self.template = self.env.ref(
            'ueipab_payroll_enhancements.email_template_payslip_delivery'
        )

    def test_wizard_creation(self):
        """Test wizard creation with defaults."""
        wizard = self.env['payslip.email.wizard'].create({
            'payslip_ids': [(6, 0, [self.payslip.id])],
        })

        self.assertTrue(wizard.template_id)
        self.assertEqual(wizard.state, 'draft')

    def test_email_sending(self):
        """Test email sending via wizard."""
        wizard = self.env['payslip.email.wizard'].create({
            'payslip_ids': [(6, 0, [self.payslip.id])],
            'send_mode': 'queue',  # Don't actually send in test
        })

        result = wizard.action_send_emails()

        self.assertEqual(wizard.success_count, 1)
        self.assertEqual(wizard.error_count, 0)
        self.assertEqual(wizard.state, 'done')

    def test_no_email_error(self):
        """Test error handling when employee has no email."""
        employee_no_email = self.env['hr.employee'].create({
            'name': 'No Email Employee',
        })

        payslip_no_email = self.env['hr.payslip'].create({
            'employee_id': employee_no_email.id,
            'date_from': '2025-11-01',
            'date_to': '2025-11-15',
            'state': 'done',
        })

        wizard = self.env['payslip.email.wizard'].create({
            'payslip_ids': [(6, 0, [payslip_no_email.id])],
        })

        wizard.action_send_emails()

        self.assertEqual(wizard.error_count, 1)
        self.assertIn('No email found', wizard.send_log)

    def test_template_rendering(self):
        """Test that template renders correctly."""
        body = self.template._render_template(
            self.template.body_html,
            'hr.payslip',
            self.payslip.id
        )

        self.assertIn(self.employee.name, body)
        self.assertIn('Comprobante de Pago', body)
```

#### 5.2 Manual Testing Checklist

**Single Send Test:**
- [ ] Create test payslip (state = Done)
- [ ] Open wizard: Payroll > Reporting > Send by Email
- [ ] Select 1 payslip
- [ ] Click "Send Emails"
- [ ] Verify: Email received at employee email
- [ ] Verify: PDF attached (if enabled)
- [ ] Verify: HTML rendering correct
- [ ] Verify: Exchange rate displayed

**Bulk Send Test:**
- [ ] Create payslip batch with 5 employees
- [ ] Open wizard, select batch
- [ ] All 5 payslips auto-populated
- [ ] Click "Send Emails"
- [ ] Verify: All 5 emails sent
- [ ] Verify: Log shows 5 successes
- [ ] Check: Odoo mail log (Discuss > Mail)

**Error Handling Test:**
- [ ] Create payslip for employee WITHOUT email
- [ ] Try to send via wizard
- [ ] Verify: Error logged (not crash)
- [ ] Verify: Other payslips still sent

**AGUINALDOS Template Test:**
- [ ] Create AGUINALDOS batch
- [ ] Send emails via wizard
- [ ] Verify: Auto-selects AGUINALDOS template
- [ ] Verify: Christmas theme displayed
- [ ] Verify: No deductions section shown

---

## Implementation Timeline

### Week 1: Template Integration (3 days)
- **Day 1:** Convert HTML template to QWeb (Phase 1.1)
- **Day 2:** Create AGUINALDOS template (Phase 1.2)
- **Day 3:** Test template rendering with sample payslips

### Week 2: Wizard Development (4 days)
- **Day 1:** Create wizard model (Phase 2.1)
- **Day 2:** Create wizard view (Phase 2.2)
- **Day 3:** Add batch selection (Phase 3.1)
- **Day 4:** Create server action (Phase 3.2)

### Week 3: Security & Testing (3 days)
- **Day 1:** Configure access rights (Phase 4)
- **Day 2:** Write unit tests (Phase 5.1)
- **Day 3:** Manual testing and bug fixes (Phase 5.2)

**Total Estimated Time:** 10 days

---

## Success Metrics

1. **Functional:**
   - ✅ Single payslip email sent successfully
   - ✅ Bulk batch email sent successfully (10+ employees)
   - ✅ AGUINALDOS template auto-selects correctly
   - ✅ PDF attachment included
   - ✅ Error handling works (no crashes)

2. **Performance:**
   - ⏱️ Batch of 44 payslips sent in < 2 minutes
   - ⏱️ Wizard opens in < 1 second
   - ⏱️ Template renders in < 500ms

3. **User Experience:**
   - 📊 Clear progress indicators
   - 📋 Detailed success/error log
   - 🎯 Intuitive wizard interface
   - 📧 Professional email appearance

---

## Dependencies & Prerequisites

### Odoo Modules Required:
- `hr_payroll_community` (already installed)
- `ueipab_payroll_enhancements` (current module)
- `mail` (Odoo core, already available)

### External Services:
- **SMTP Server:** Gmail (recursoshumanos@ueipab.edu.ve)
  - Already configured
  - App password available
  - TLS enabled

### Python Libraries:
- No additional libraries needed (uses Odoo stdlib)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Gmail SMTP limits** | High - Email sending fails | Use Odoo's queue system, batch in groups of 50 |
| **Employee missing emails** | Medium - Some payslips not sent | Validate before sending, show clear error log |
| **Template rendering errors** | Medium - Broken HTML emails | Extensive testing with sample data |
| **PDF generation slow** | Low - User wait time | Async PDF generation, progress indicator |
| **Spam filters** | Medium - Emails not delivered | SPF/DKIM records, professional template |

---

## Future Enhancements (Post-MVP)

1. **Scheduled Sending:**
   - Cron job to auto-send on payslip confirmation
   - Schedule batch emails for specific date/time

2. **Email Tracking:**
   - Track email opens (tracking pixel)
   - Track link clicks
   - Dashboard with delivery stats

3. **Multi-Language Support:**
   - Spanish/English template variants
   - Employee language preference

4. **Advanced Attachments:**
   - Include liquidation reports
   - Include prestaciones breakdown
   - Include finiquito document

5. **Email Templates Library:**
   - Multiple template designs
   - User-customizable templates
   - Preview before sending

---

## Conclusion

**Recommended Approach:** Option A (Native Odoo Implementation)

**Rationale:**
1. **Maintainability:** Uses standard Odoo patterns, easier to maintain
2. **User Experience:** Native Odoo UI, familiar to HR staff
3. **Security:** Built-in access control and permissions
4. **Scalability:** Odoo queue system handles bulk sending
5. **Integration:** Seamless integration with existing reports

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 (Template Integration)
3. Iterate with user feedback
4. Deploy to production after Week 3

---

**Document Version:** 1.0
**Author:** Claude (AI Assistant)
**Last Updated:** 2025-11-21
**Status:** 📋 Ready for Review
