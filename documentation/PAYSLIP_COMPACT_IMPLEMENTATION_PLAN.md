# Payslip Details Report (Compact) - Implementation Plan

**Date:** 2025-11-22
**Status:** 📋 PLAN - Ready for User Approval
**Approved By:** Pending
**Module:** `ueipab_payroll_enhancements` v1.30.0

---

## Overview

Create a new single-page, compact payslip report inspired by "Relación de Liquidación" design with full currency conversion support (USD/VEB).

---

## User Requirements

✅ **Option 1: Complete Redesign** (Single-page compact layout)
✅ **Exchange Rate Display** - Show current exchange rate when VEB selected
✅ **Currency Selector** - Choose USD or VEB from `res.currency` model
✅ **Full Currency Conversion** - ALL amounts displayed in selected currency

---

## Design Specifications

### 1. Report Layout

**Name:** Comprobante de Pago (Compact)
**Template ID:** `report_payslip_compact`
**Pages:** 1 page (Portrait Letter)
**Layout:** `web.basic_layout` (no header/footer)
**Font Base:** 7pt
**Language:** Spanish (Venezuelan context)

**Structure:**
```
┌─────────────────────────────────────────────┐
│ COMPROBANTE DE PAGO - UEIPAB               │
│ Nro: SLIP/XXX │ Período: MM/YYYY           │
│ Moneda: [USD/VEB] │ Tasa: XX.XX VEB/USD   │ ← NEW: Currency info
├─────────────────────────────────────────────┤
│ INFORMACIÓN DEL EMPLEADO                   │
│ Nombre │ Cédula │ Cargo │ Departamento    │
│ Salario│ Ingreso│ Período│ Banco          │
├─────────────────────────────────────────────┤
│ 1. DEVENGOS (EARNINGS) [GREEN HEADER]      │
│ # │ Concepto │ Cantidad │ Monto [CURRENCY]│
│ 1 │ Salario Básico    │ 1.00 │ $XXX.XX   │
│ 2 │ Bono Regular      │ 1.00 │ $XXX.XX   │
│ 3 │ Cesta Ticket      │ 1.00 │ $XXX.XX   │
│ ... (all earnings)                         │
│ SUBTOTAL DEVENGOS: [CURRENCY] XXX.XX       │
├─────────────────────────────────────────────┤
│ 2. DEDUCCIONES (DEDUCTIONS) [RED HEADER]   │
│ # │ Concepto │ Tasa │ Monto [CURRENCY]    │
│ 1 │ SSO (4.5%)       │ 4.5% │ $XXX.XX    │
│ 2 │ FAOV (1.0%)      │ 1.0% │ $XXX.XX    │
│ 3 │ INCES (0.5%)     │ 0.5% │ $XXX.XX    │
│ ... (all deductions)                       │
│ TOTAL DEDUCCIONES: [CURRENCY] (XXX.XX)     │
├─────────────────────────────────────────────┤
│ [RESUMEN / SUMMARY BOX]                    │
│ TOTAL DEVENGOS:     [CURRENCY] XXX.XX      │
│ TOTAL DEDUCCIONES:  [CURRENCY] (XXX.XX)    │
│ ─────────────────────────────────────────  │
│ NETO A PAGAR:       [CURRENCY] XXX.XX      │ ← Highlighted
├─────────────────────────────────────────────┤
│ FIRMAS / SIGNATURES                        │
│ _______________          _______________   │
│ Empleado                 RRHH UEIPAB      │
└─────────────────────────────────────────────┘
```

### 2. Currency Selection System

**Based on:** Relación de Liquidación wizard pattern

**Wizard Model:** `payslip.compact.wizard`
**File:** `wizard/payslip_compact_wizard.py`

**Fields:**
```python
class PayslipCompactWizard(models.TransientModel):
    _name = 'payslip.compact.wizard'
    _description = 'Payslip Compact Report Wizard'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        domain=[('name', 'in', ['USD', 'VEB'])],
        help="Select currency for report display"
    )

    # Exchange rate override (same as Relación)
    use_custom_rate = fields.Boolean(
        string='Use Custom Exchange Rate',
        default=False
    )

    custom_exchange_rate = fields.Float(
        string='Custom Exchange Rate',
        digits=(12, 4),
        help='Custom VEB/USD exchange rate (e.g., 36.50)'
    )

    rate_date = fields.Date(
        string='Rate Date (Auto Lookup)',
        help='Automatically lookup exchange rate for this date'
    )

    exchange_rate_display = fields.Char(
        string='Exchange Rate Info',
        compute='_compute_exchange_rate_display',
        readonly=True
    )
```

**Wizard View Structure:**
```xml
<!-- Similar to liquidacion_breakdown_wizard_view.xml -->
<form>
    <group>
        <field name="payslip_id" invisible="1"/>
        <field name="currency_id" widget="radio"/>
    </group>

    <group string="Exchange Rate Options"
           invisible="currency_id.name != 'VEB'">
        <field name="use_custom_rate"/>
        <field name="custom_exchange_rate"
               invisible="not use_custom_rate"/>
        <field name="rate_date"
               invisible="use_custom_rate"/>
        <field name="exchange_rate_display"/>
    </group>

    <footer>
        <button name="action_generate_report"
                string="Generate Report"
                type="object"
                class="btn-primary"/>
        <button string="Cancel"
                special="cancel"
                class="btn-secondary"/>
    </footer>
</form>
```

### 3. Currency Conversion Logic

**Report Model:** `payslip.compact.report`
**File:** `reports/payslip_compact_report.py`

**Key Methods:**
```python
def _get_exchange_rate(self, payslip, currency_target, use_custom, custom_rate, rate_date):
    """
    Get exchange rate for currency conversion
    Priority: 1) Custom rate → 2) Rate date → 3) Payslip date

    Returns: (rate_value, rate_source_text)
    Example: (36.5014, "Tasa del 22/11/2025")
    """
    if use_custom and custom_rate:
        return custom_rate, "Tasa personalizada"

    if rate_date:
        date_to_use = rate_date
    else:
        date_to_use = payslip.date_to

    # Get rate from res.currency.rate using company_rate
    rate_obj = self.env['res.currency.rate'].search([
        ('currency_id', '=', currency_target.id),
        ('name', '<=', date_to_use)
    ], order='name desc', limit=1)

    if rate_obj and rate_obj.company_rate:
        rate_value = rate_obj.company_rate
        return rate_value, f"Tasa del {rate_obj.name.strftime('%d/%m/%Y')}"

    # Fallback: use standard Odoo conversion
    rate_value = currency_target._convert(
        1.0, self.env.company.currency_id,
        self.env.company, date_to_use
    )
    return rate_value, f"Tasa automática ({date_to_use.strftime('%d/%m/%Y')})"

def _convert_amount(self, amount_usd, currency_target, exchange_rate):
    """
    Convert USD amount to target currency

    Args:
        amount_usd: Amount in USD
        currency_target: Target res.currency record
        exchange_rate: Conversion rate (VEB per USD)

    Returns: Converted amount
    """
    if currency_target.name == 'USD':
        return amount_usd

    # VEB conversion: multiply by exchange rate
    return amount_usd * exchange_rate

def _format_amount(self, amount, currency):
    """
    Format amount with thousand separators and currency symbol

    Returns: String like "$1,234.56" or "Bs. 44,566.78"
    """
    formatted = "{:,.2f}".format(abs(amount))

    if currency.name == 'USD':
        return f"${formatted}"
    else:
        return f"Bs. {formatted}"
```

**Data Preparation:**
```python
def _prepare_report_data(self, payslip, currency_id, exchange_rate, rate_source):
    """
    Prepare all data for report template with currency conversion
    """
    # Get exchange rate info
    exchange_info = {
        'currency': currency_id,
        'rate_value': exchange_rate,
        'rate_source': rate_source,
        'display_rate': exchange_rate != 1.0  # Only show for VEB
    }

    # Employee info (no conversion needed)
    employee_info = {
        'name': payslip.employee_id.name,
        'identification_id': payslip.employee_id.identification_id,
        'job': payslip.employee_id.job_id.name,
        'department': payslip.employee_id.department_id.name,
        'bank': payslip.employee_id.bank_account_id.acc_number,
        'date_start': payslip.contract_id.date_start,
        'period': f"{payslip.date_from.strftime('%d/%m/%Y')} - {payslip.date_to.strftime('%d/%m/%Y')}"
    }

    # Salary (convert)
    salary_usd = payslip.contract_id.wage
    salary_converted = self._convert_amount(salary_usd, currency_id, exchange_rate)

    # Process earnings
    earnings = []
    earnings_total = 0.0

    earnings_categories = ['ALW', 'BASIC', 'GROSS', 'COMP']
    for line in payslip.line_ids.filtered(lambda l: l.category_id.code in earnings_categories):
        amount_usd = line.total
        amount_converted = self._convert_amount(amount_usd, currency_id, exchange_rate)

        earnings.append({
            'number': len(earnings) + 1,
            'name': line.name,
            'code': line.code,
            'quantity': line.quantity,
            'amount': amount_converted,
            'amount_formatted': self._format_amount(amount_converted, currency_id)
        })
        earnings_total += amount_converted

    # Process deductions
    deductions = []
    deductions_total = 0.0

    deduction_categories = ['DED', 'NET']
    for line in payslip.line_ids.filtered(lambda l: l.category_id.code in deduction_categories and l.total < 0):
        amount_usd = abs(line.total)
        amount_converted = self._convert_amount(amount_usd, currency_id, exchange_rate)

        # Get rate percentage if available
        rate_text = f"{line.rate:.1f}%" if line.rate else ""

        deductions.append({
            'number': len(deductions) + 1,
            'name': line.name,
            'code': line.code,
            'rate': rate_text,
            'amount': amount_converted,
            'amount_formatted': self._format_amount(amount_converted, currency_id)
        })
        deductions_total += amount_converted

    # Calculate net
    net_pay = earnings_total - deductions_total

    return {
        'payslip': payslip,
        'employee': employee_info,
        'exchange': exchange_info,
        'salary': salary_converted,
        'salary_formatted': self._format_amount(salary_converted, currency_id),
        'earnings': earnings,
        'earnings_total': earnings_total,
        'earnings_total_formatted': self._format_amount(earnings_total, currency_id),
        'deductions': deductions,
        'deductions_total': deductions_total,
        'deductions_total_formatted': self._format_amount(deductions_total, currency_id),
        'net_pay': net_pay,
        'net_pay_formatted': self._format_amount(net_pay, currency_id),
        'currency': currency_id
    }
```

### 4. Report Template Structure

**File:** `reports/payslip_compact_report.xml`

**Key Template Sections:**
```xml
<template id="report_payslip_compact">
    <t t-call="web.html_container">
        <t t-foreach="reports" t-as="report">
            <t t-call="web.basic_layout">
                <div class="page" style="font-size: 7pt;">

                    <!-- TITLE + CURRENCY INFO -->
                    <div style="text-align: center; margin-bottom: 10px;">
                        <h3 style="font-size: 11pt;">COMPROBANTE DE PAGO</h3>
                        <p style="font-size: 7pt;">
                            Nro: <t t-esc="report['payslip'].number"/> │
                            Período: <t t-esc="report['payslip'].date_from.strftime('%B %Y')"/>
                        </p>
                        <!-- NEW: Exchange rate display -->
                        <t t-if="report.get('exchange').get('display_rate')">
                            <p style="font-size: 6.5pt; color: #666;">
                                <t t-esc="report['exchange']['rate_source']"/>:
                                <strong><t t-esc="'%.4f' % report['exchange']['rate_value']"/> VEB/USD</strong>
                            </p>
                        </t>
                    </div>

                    <!-- EMPLOYEE INFO -->
                    <table class="table table-sm table-bordered" style="margin-bottom: 8px;">
                        <!-- 2x4 grid layout -->
                        <tr>
                            <td style="width: 25%; background-color: #f8f9fa;"><strong>Empleado:</strong></td>
                            <td style="width: 25%;"><t t-esc="report['employee']['name']"/></td>
                            <td style="width: 25%; background-color: #f8f9fa;"><strong>Cédula:</strong></td>
                            <td style="width: 25%;"><t t-esc="report['employee']['identification_id']"/></td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8f9fa;"><strong>Cargo:</strong></td>
                            <td><t t-esc="report['employee']['job']"/></td>
                            <td style="background-color: #f8f9fa;"><strong>Departamento:</strong></td>
                            <td><t t-esc="report['employee']['department']"/></td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8f9fa;"><strong>Salario:</strong></td>
                            <td><t t-esc="report['salary_formatted']"/></td>
                            <td style="background-color: #f8f9fa;"><strong>Ingreso:</strong></td>
                            <td><t t-esc="report['employee']['date_start']"/></td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8f9fa;"><strong>Período:</strong></td>
                            <td><t t-esc="report['employee']['period']"/></td>
                            <td style="background-color: #f8f9fa;"><strong>Banco:</strong></td>
                            <td><t t-esc="report['employee']['bank']"/></td>
                        </tr>
                    </table>

                    <!-- SECTION 1: DEVENGOS (GREEN) -->
                    <div style="margin-bottom: 8px;">
                        <h5 style="background-color: #4CAF50; color: white; padding: 3px 8px; font-size: 8pt;">
                            1. DEVENGOS (INGRESOS)
                        </h5>
                        <table class="table table-sm table-bordered" style="font-size: 6.5pt;">
                            <thead style="background-color: #e8f5e9;">
                                <tr>
                                    <th style="width: 5%;">#</th>
                                    <th style="width: 55%;">Concepto</th>
                                    <th style="width: 15%; text-align: center;">Cantidad</th>
                                    <th style="width: 25%; text-align: right;">Monto</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="report['earnings']" t-as="earning">
                                    <tr>
                                        <td><t t-esc="earning['number']"/></td>
                                        <td><strong><t t-esc="earning['name']"/></strong></td>
                                        <td style="text-align: center;"><t t-esc="'%.2f' % earning['quantity']"/></td>
                                        <td style="text-align: right;"><t t-esc="earning['amount_formatted']"/></td>
                                    </tr>
                                </t>
                                <tr style="background-color: #e8f5e9; font-weight: bold;">
                                    <td colspan="3" style="text-align: right;">SUBTOTAL DEVENGOS:</td>
                                    <td style="text-align: right;"><t t-esc="report['earnings_total_formatted']"/></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- SECTION 2: DEDUCCIONES (RED) -->
                    <div style="margin-bottom: 8px;">
                        <h5 style="background-color: #f44336; color: white; padding: 3px 8px; font-size: 8pt;">
                            2. DEDUCCIONES
                        </h5>
                        <table class="table table-sm table-bordered" style="font-size: 6.5pt;">
                            <thead style="background-color: #ffebee;">
                                <tr>
                                    <th style="width: 5%;">#</th>
                                    <th style="width: 55%;">Concepto</th>
                                    <th style="width: 15%; text-align: center;">Tasa</th>
                                    <th style="width: 25%; text-align: right;">Monto</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="report['deductions']" t-as="deduction">
                                    <tr>
                                        <td><t t-esc="deduction['number']"/></td>
                                        <td><strong><t t-esc="deduction['name']"/></strong></td>
                                        <td style="text-align: center;"><t t-esc="deduction['rate']"/></td>
                                        <td style="text-align: right;"><t t-esc="deduction['amount_formatted']"/></td>
                                    </tr>
                                </t>
                                <tr style="background-color: #ffebee; font-weight: bold;">
                                    <td colspan="3" style="text-align: right;">TOTAL DEDUCCIONES:</td>
                                    <td style="text-align: right;">(<t t-esc="report['deductions_total_formatted']"/>)</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- FINAL SUMMARY BOX -->
                    <div style="margin-top: 10px; border: 2px solid #333; padding: 8px; background-color: #f8f9fa;">
                        <table style="width: 100%; font-size: 8pt;">
                            <tr>
                                <td style="width: 70%; text-align: right;"><strong>TOTAL DEVENGOS:</strong></td>
                                <td style="width: 30%; text-align: right;"><t t-esc="report['earnings_total_formatted']"/></td>
                            </tr>
                            <tr>
                                <td style="text-align: right;"><strong>TOTAL DEDUCCIONES:</strong></td>
                                <td style="text-align: right;">(<t t-esc="report['deductions_total_formatted']"/>)</td>
                            </tr>
                            <tr style="border-top: 2px solid #333;">
                                <td style="text-align: right; font-size: 9pt;"><strong>NETO A PAGAR:</strong></td>
                                <td style="text-align: right; font-size: 10pt; font-weight: bold;">
                                    <t t-esc="report['net_pay_formatted']"/>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- SIGNATURES -->
                    <div class="row" style="margin-top: 20px;">
                        <div class="col-6 text-center">
                            <div style="border-top: 1px solid #000; margin-top: 40px; padding-top: 5px;">
                                <strong>Firma del Empleado</strong><br/>
                                <small>Fecha: ____/____/______</small>
                            </div>
                        </div>
                        <div class="col-6 text-center">
                            <div style="border-top: 1px solid #000; margin-top: 40px; padding-top: 5px;">
                                <strong>Recursos Humanos UEIPAB</strong><br/>
                                <small>Firma Autorizada</small>
                            </div>
                        </div>
                    </div>

                </div>
            </t>
        </t>
    </t>
</template>
```

---

## File Structure

```
ueipab_payroll_enhancements/
├── models/
│   ├── hr_payslip.py (add action_send_compact_payslip method) ← UPDATED
│   └── __init__.py (add payslip_compact_report import)
├── wizard/
│   ├── __init__.py (add wizard imports)
│   ├── payslip_compact_wizard.py (NEW - Report generation wizard)
│   ├── payslip_compact_wizard_view.xml (NEW)
│   ├── payslip_compact_send_wizard.py (NEW - Individual email send wizard)
│   ├── payslip_compact_send_wizard_view.xml (NEW)
│   ├── payslip_mass_send_compact_wizard.py (NEW - Batch email send wizard) ← PHASE 8
│   └── payslip_mass_send_compact_wizard_view.xml (NEW) ← PHASE 8
├── reports/
│   ├── __init__.py (add payslip_compact_report import)
│   ├── payslip_compact_report.py (NEW)
│   ├── payslip_compact_report.xml (NEW)
│   └── report_actions.xml (add new report action)
├── views/
│   ├── hr_payslip_view.xml (add "Send Compact Payslip" button)
│   └── payroll_reports_menu.xml (add menu item)
├── data/
│   ├── email_template_compact_payslip.xml (NEW)
│   └── payslip_actions.xml (NEW - Mass send server action) ← PHASE 8
└── __manifest__.py (update data files list, version 1.30.0)
```

---

## Implementation Steps

### Phase 1: Wizard Setup (Report Generation - Currency Selection)
1. ✅ Create `payslip_compact_wizard.py` model
2. ✅ Create `payslip_compact_wizard_view.xml` form
3. ✅ Add wizard to `__init__.py`
4. ✅ Test wizard opens and currency selection works

### Phase 2: Report Model (Data Preparation)
1. ✅ Create `payslip_compact_report.py` model
2. ✅ Implement `_get_exchange_rate()` method
3. ✅ Implement `_convert_amount()` method
4. ✅ Implement `_format_amount()` method
5. ✅ Implement `_prepare_report_data()` method
6. ✅ Add to `__init__.py`

### Phase 3: Report Template (Layout)
1. ✅ Create `payslip_compact_report.xml` template
2. ✅ Add title + currency info section
3. ✅ Add employee info table (2x4 grid)
4. ✅ Add earnings section (green, with conversion)
5. ✅ Add deductions section (red, with conversion)
6. ✅ Add final summary box
7. ✅ Add signatures section

### Phase 4: Report Action & Menu
1. ✅ Add report action to `report_actions.xml`
2. ✅ Add menu item to `payroll_reports_menu.xml`
3. ✅ Update `__manifest__.py` data files

### Phase 5: Core Report Testing
1. ✅ Test with USD currency (default)
2. ✅ Test with VEB currency (automatic rate)
3. ✅ Test with VEB currency (custom rate)
4. ✅ Test with VEB currency (rate date lookup)
5. ✅ Verify all amounts convert correctly
6. ✅ Verify exchange rate displays correctly
7. ✅ Verify single-page layout
8. ✅ Test with various payslip types

### Phase 6: Email Integration ⭐ NEW
1. ✅ Create `payslip_compact_send_wizard.py` model (email send wizard)
2. ✅ Create `payslip_compact_send_wizard_view.xml` form
3. ✅ Add method `action_send_compact_payslip()` to `models/hr_payslip.py`
4. ✅ Create `views/hr_payslip_view.xml` with "Send Compact Payslip" button
5. ✅ Create `data/email_template_compact_payslip.xml` email template
6. ✅ Update `__manifest__.py` with new data files

### Phase 7: Email Integration Testing
1. ✅ Test button appears on payslip form
2. ✅ Test send wizard opens correctly
3. ✅ Test email send with USD
4. ✅ Test email send with VEB (automatic rate)
5. ✅ Test email send with VEB (custom rate)
6. ✅ Test email send with VEB (rate date lookup)
7. ✅ Verify PDF attachment generated correctly
8. ✅ Verify email template renders correctly
9. ✅ Verify employee receives email with correct PDF
10. ✅ Test "Reset Send Status" button still works after sending

### Phase 8: Mass Send Functionality ⭐ NEW (Batch Email Sending)
1. ✅ Create `payslip_mass_send_compact_wizard.py` model
2. ✅ Create `payslip_mass_send_compact_wizard_view.xml` form
3. ✅ Create server action for list view (Actions dropdown)
4. ✅ Implement bulk email sending logic
5. ✅ Add error handling and progress notifications
6. ✅ Update `__manifest__.py` with new files

### Phase 9: Mass Send Testing
1. ✅ Test mass send wizard opens from list view
2. ✅ Test with multiple payslips (e.g., 5-10)
3. ✅ Test with full batch (e.g., 44 payslips)
4. ✅ Test with USD currency (all sent in USD)
5. ✅ Test with VEB currency (all sent in VEB)
6. ✅ Test error handling (payslips without email)
7. ✅ Verify success/failure notifications
8. ✅ Verify all employees receive correct PDFs
9. ✅ Verify performance with large batches

---

## Technical Details

### Currency Conversion Formula

**USD → VEB:**
```
VEB Amount = USD Amount × Exchange Rate
Example: $100.00 × 36.50 = Bs. 3,650.00
```

### Exchange Rate Priority
1. **Custom Rate** (user enters manually)
2. **Rate Date** (user selects date, system looks up rate)
3. **Payslip Date** (use rate from payslip date_to)

### Exchange Rate Source
- **Model:** `res.currency.rate`
- **Field:** `company_rate` (VEB per USD)
- **Lookup:** Most recent rate ≤ target date

Example:
```python
rate_record = env['res.currency.rate'].search([
    ('currency_id.name', '=', 'VEB'),
    ('name', '<=', date_to_use)
], order='name desc', limit=1)

if rate_record:
    exchange_rate = rate_record.company_rate  # e.g., 36.5014
```

### Report Action Configuration

```xml
<record id="action_report_payslip_compact" model="ir.actions.report">
    <field name="name">Comprobante de Pago (Compacto)</field>
    <field name="model">hr.payslip</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">ueipab_payroll_enhancements.report_payslip_compact</field>
    <field name="report_file">ueipab_payroll_enhancements.report_payslip_compact</field>
    <field name="print_report_name">'Payslip - %s' % (object.number)</field>
    <field name="binding_model_id" ref="hr_payroll_community.model_hr_payslip"/>
    <field name="binding_type">report</field>
</record>
```

**Note:** Report will be available via wizard, not direct print button.

---

## Expected Behavior

### USD Currency (Default)
1. User opens payslip
2. Clicks "Comprobante de Pago (Compacto)"
3. Wizard opens with USD selected
4. Click "Generate Report"
5. Report shows all amounts in USD
6. No exchange rate displayed
7. Example: "$146.19"

### VEB Currency (Automatic Rate)
1. User opens payslip
2. Clicks "Comprobante de Pago (Compacto)"
3. Wizard opens, user selects VEB
4. System shows latest exchange rate
5. Click "Generate Report"
6. Report shows exchange rate info at top
7. All amounts converted to VEB
8. Example: "Bs. 5,310.48" (at rate 36.50)

### VEB Currency (Custom Rate)
1. User selects VEB
2. Checks "Use Custom Exchange Rate"
3. Enters rate: 40.00
4. Click "Generate Report"
5. Report shows "Tasa personalizada: 40.0000 VEB/USD"
6. All amounts use custom rate
7. Example: "Bs. 5,847.60" (at rate 40.00)

### VEB Currency (Rate Date Lookup)
1. User selects VEB
2. Selects rate date: 2025-11-17
3. System looks up rate for that date
4. Click "Generate Report"
5. Report shows "Tasa del 17/11/2025: 36.1450 VEB/USD"
6. All amounts use looked-up rate

---

## Validation Checklist

### Layout Validation
- [ ] Report fits on single Letter page (Portrait)
- [ ] All text is readable (minimum 6.5pt)
- [ ] Spanish characters display correctly (á, é, í, ó, ú, ñ)
- [ ] Color coding clear (Green earnings, Red deductions)
- [ ] Sections well-organized and logical flow
- [ ] No overlapping elements
- [ ] Signatures section has adequate space

### Currency Validation (USD)
- [ ] All amounts display in USD
- [ ] Dollar sign ($) appears correctly
- [ ] Amounts formatted with comma separators
- [ ] No exchange rate shown
- [ ] Totals calculate correctly

### Currency Validation (VEB)
- [ ] All amounts display in VEB
- [ ] "Bs." symbol appears correctly
- [ ] Exchange rate displays at top
- [ ] Rate source text correct
- [ ] All amounts converted consistently
- [ ] Totals calculate correctly in VEB

### Functional Validation
- [ ] Wizard opens from payslip form
- [ ] Currency selection works (radio buttons)
- [ ] Exchange rate options show/hide correctly
- [ ] Custom rate field accepts decimal values
- [ ] Rate date picker works
- [ ] "Generate Report" button works
- [ ] PDF generates without errors
- [ ] Can generate multiple times with different currencies

### Data Validation
- [ ] Employee info displays correctly
- [ ] Payslip number and period correct
- [ ] Salary amount correct
- [ ] All earnings lines included
- [ ] All deduction lines included
- [ ] Earnings total = sum of earnings
- [ ] Deductions total = sum of deductions
- [ ] Net pay = earnings - deductions
- [ ] Bank account info correct

---

## Module Version Update

**Current Version:** `ueipab_payroll_enhancements` v1.29.0
**New Version:** v1.30.0

**__manifest__.py Changes:**
```python
{
    'version': '1.30.0',
    'data': [
        # ... existing files ...
        'wizard/payslip_compact_wizard_view.xml',  # NEW
        'reports/payslip_compact_report.xml',      # NEW
        # ... rest of files ...
    ],
}
```

---

## Documentation

### User Guide (to be created)
**File:** `/opt/odoo-dev/documentation/PAYSLIP_COMPACT_USER_GUIDE.md`

**Contents:**
- How to generate compact payslip report
- How to select currency
- How to use custom exchange rates
- How to interpret the report
- Troubleshooting common issues

### Technical Reference (to be created)
**File:** `/opt/odoo-dev/documentation/PAYSLIP_COMPACT_TECHNICAL.md`

**Contents:**
- Architecture overview
- Currency conversion algorithms
- Exchange rate lookup logic
- Template structure
- Extension points
- Performance considerations

---

## Timeline Estimate

| Phase | Tasks | Time Estimate |
|-------|-------|---------------|
| **Phase 1** | Report wizard setup | 30 minutes |
| **Phase 2** | Report model | 45 minutes |
| **Phase 3** | Report template | 60 minutes |
| **Phase 4** | Actions & menu | 15 minutes |
| **Phase 5** | Core report testing | 45 minutes |
| **Phase 6** | Individual email integration | 90 minutes |
| **Phase 7** | Individual email testing | 30 minutes |
| **Phase 8** | Mass send functionality ⭐ | 90 minutes |
| **Phase 9** | Mass send testing | 30 minutes |
| **Total** | | **~6.5 hours** |

**Note:**
- Email integration (Phases 6-7) adds 2 hours to original 2.5 hour estimate
- Mass send functionality (Phases 8-9) adds additional 2 hours
- **Total with all features:** 6.5 hours

---

## Success Criteria

✅ **Single-page report** - Fits on 1 Portrait Letter page
✅ **Currency selection** - USD and VEB options work
✅ **Exchange rate display** - Shows rate when VEB selected
✅ **Full conversion** - ALL amounts in selected currency
✅ **Consistent formatting** - Thousand separators, proper symbols
✅ **Clean layout** - Professional appearance, easy to read
✅ **Spanish labels** - Venezuelan terminology
✅ **No errors** - Generates PDF without issues
✅ **UTF-8 support** - Spanish characters display correctly
✅ **Reusable wizard** - Can generate multiple times

---

## Questions / Clarifications Needed

### Resolved (from user input):
- ✅ Option 1 (complete redesign) approved
- ✅ Exchange rate display required
- ✅ Currency selector required (USD/VEB from res.currency)
- ✅ Full currency conversion required

### Outstanding:
1. **Earnings Categories** - Which salary rule categories should be included in "DEVENGOS"?
   - Current assumption: ALW, BASIC, GROSS, COMP
   - Should we include others?

2. **Deductions Categories** - Which categories for "DEDUCCIONES"?
   - Current assumption: DED, NET (with total < 0)
   - Should we include others?

3. **Bank Account Display** - Should we show full account or last 4 digits?
   - Current: Full account number

4. **Report Availability** - Should this replace the original "Payslip Details" or coexist?
   - Current plan: Coexist (new report, keep original)

5. **Exchange Rate Override** - All 3 options needed? (Custom / Date / Default)
   - Current plan: Yes, all 3 (matching Relación pattern)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Single page too cramped** | Medium | Tested with 7pt font, proven in Relación |
| **Currency conversion errors** | High | Reuse proven code from Relación report |
| **Exchange rate not found** | Medium | Fallback to Odoo standard conversion |
| **Missing payslip lines** | Medium | Clear category filtering logic |
| **UTF-8 encoding issues** | Low | Use web.basic_layout (proven) |
| **Wizard complexity** | Low | Copy from existing Relación wizard |

---

## Email Integration Details ⭐

### **Approach: Separate "Send Compact Payslip" Button** (Recommended)

**Why This Approach:**
- ✅ Clear user intent - Two distinct buttons for two distinct actions
- ✅ No breaking changes - Original "Send Mail" button unchanged
- ✅ Follows existing pattern - Same wizard pattern as Relación, Prestaciones, Finiquito
- ✅ Easy to maintain - All new code isolated in ueipab_payroll_enhancements

**User Workflow:**
```
1. User opens payslip
   ↓
2. Clicks "Send Compact Payslip" button (NEW)
   ↓
3. Send wizard opens:
   ├─ Currency selection (USD/VEB)
   ├─ Exchange rate options (if VEB selected)
   └─ Preview option (future enhancement)
   ↓
4. User clicks "Send Email"
   ↓
5. System generates compact PDF with selected currency
   ↓
6. Email composer opens with:
   - Template: "Compact Payslip Email"
   - Attachment: Generated compact PDF
   - Subject: "[Comprobante] Pago SLIP/XXX - [Month Year]"
   ↓
7. User reviews and sends email
   ↓
8. Employee receives compact payslip in selected currency
```

### **Email Send Wizard Structure**

**Model:** `payslip.compact.send.wizard`
**File:** `wizard/payslip_compact_send_wizard.py`

```python
class PayslipCompactSendWizard(models.TransientModel):
    _name = 'payslip.compact.send.wizard'
    _description = 'Send Compact Payslip via Email'

    payslip_id = fields.Many2one('hr.payslip', required=True)

    # Currency selection (same as report generation wizard)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        domain=[('name', 'in', ['USD', 'VEB'])]
    )

    # Exchange rate options (if VEB)
    use_custom_rate = fields.Boolean(default=False)
    custom_exchange_rate = fields.Float(digits=(12, 4))
    rate_date = fields.Date()

    def action_send_email(self):
        """Generate compact PDF and open email composer"""
        self.ensure_one()

        # 1. Prepare report data with selected currency
        report_data = {
            'currency_id': self.currency_id.id,
            'use_custom_rate': self.use_custom_rate,
            'custom_exchange_rate': self.custom_exchange_rate,
            'rate_date': self.rate_date,
        }

        # 2. Generate PDF report
        report = self.env.ref('ueipab_payroll_enhancements.action_report_payslip_compact')
        pdf_content, _ = report._render_qweb_pdf(
            self.payslip_id.ids,
            data=report_data
        )

        # 3. Create attachment
        filename = f"Comprobante_Pago_{self.payslip_id.number.replace('/', '_')}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'mimetype': 'application/pdf'
        })

        # 4. Mark payslip as sent
        self.payslip_id.write({'is_send_mail': True})

        # 5. Get email template
        template = self.env.ref('ueipab_payroll_enhancements.email_template_compact_payslip')

        # 6. Open email composer with attachment
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

### **Button Addition to hr.payslip Form**

**File:** `views/hr_payslip_view.xml`

```xml
<record id="view_hr_payslip_form_send_compact" model="ir.ui.view">
    <field name="name">hr.payslip.form.send.compact</field>
    <field name="model">hr.payslip</field>
    <field name="inherit_id" ref="hr_payroll_community.hr_payslip_view_form"/>
    <field name="arch" type="xml">
        <!-- Add button after existing "Send Mail" button -->
        <button name="action_payslip_send" position="after">
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

### **Email Template**

**File:** `data/email_template_compact_payslip.xml`

```xml
<odoo>
    <data noupdate="1">
        <record id="email_template_compact_payslip" model="mail.template">
            <field name="name">Compact Payslip Email</field>
            <field name="model_id" ref="hr_payroll_community.model_hr_payslip"/>
            <field name="subject">[Comprobante] Pago {{object.number}} - {{object.date_from.strftime('%B %Y')}}</field>
            <field name="email_to">{{object.employee_id.private_email}}</field>
            <field name="body_html"><![CDATA[
                <p>Estimado(a) <strong>{{object.employee_id.name}}</strong>,</p>

                <p>Adjunto encontrará su <strong>Comprobante de Pago</strong> correspondiente al período
                <strong>{{object.date_from.strftime('%B %Y')}}</strong>.</p>

                <p><strong>Referencia:</strong> {{object.number}}<br/>
                <strong>Período:</strong> {{object.date_from.strftime('%d/%m/%Y')}} - {{object.date_to.strftime('%d/%m/%Y')}}</p>

                <p>Si tiene alguna consulta sobre su comprobante de pago, por favor contacte al Departamento de Recursos Humanos.</p>

                <p>Saludos cordiales,<br/>
                <strong>Recursos Humanos</strong><br/>
                UEIPAB</p>
            ]]></field>
        </record>
    </data>
</odoo>
```

### **Method Addition to hr.payslip Model**

**File:** `models/hr_payslip.py`

```python
class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_send_compact_payslip(self):
        """
        Open wizard to send compact payslip via email
        User selects currency, then email composer opens with PDF attached
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

---

## Approval Status

**Plan Ready:** ✅ YES
**Email Integration:** ✅ Included (Option 1 - Separate Button)
**Awaiting Approval From:** User
**Ready to Implement:** ⏳ Pending user approval

**Please review and confirm:**
1. ✅ Overall design acceptable?
2. ✅ Currency conversion approach correct?
3. ✅ Exchange rate display sufficient?
4. ✅ Email integration approach acceptable? (Separate button)
5. ✅ Button label "Send Compact Payslip" acceptable? (or prefer Spanish?)
6. ✅ Email subject format acceptable?
7. ✅ Ready to proceed with implementation?

---

## Mass Send Functionality Details ⭐ PHASE 8

### **Batch Email Sending from Payslip List**

**Critical Gap Identified:** Current plan only supports sending individual payslips one at a time.

**Problem Scenario:**
```
October 2025 payroll batch:
- 44 payslips (one per employee)
- Current plan: Open each → Send → Select currency → Repeat 44 times
- Time required: ~22 minutes (30 seconds per payslip)
- Result: Tedious, error-prone, inconsistent rates
```

**Solution:** Mass Send Wizard (similar to existing Mass Confirm)

**User Workflow:**
```
1. Navigate to Payroll > Payslips (list view)
   ↓
2. Filter to desired batch (e.g., October 2025)
   ↓
3. Select multiple payslips via checkboxes (e.g., all 44)
   ↓
4. Actions dropdown > "Mass Send Compact Payslips" (NEW)
   ↓
5. Wizard opens:
   - Currency selection (USD/VEB) - applies to ALL
   - Exchange rate options (if VEB)
   - Preview: "44 payslips will be emailed"
   ↓
6. User clicks "Send Emails"
   ↓
7. System processes each payslip:
   - Generates compact PDF with selected currency
   - Creates email with attachment
   - Sends to employee.private_email
   - Marks is_send_mail = True
   ↓
8. Success notification: "44 compact payslips sent successfully"
   ↓
9. All employees receive compact payslips in selected currency
```

**Time Savings:** 21 minutes per batch (1 minute vs 22 minutes)

**Key Features:**
- ✅ Single currency selection for entire batch
- ✅ Error handling (skip payslips without email)
- ✅ Success/failure notifications
- ✅ Async email sending (queued, doesn't block)
- ✅ Same security as individual send

**Implementation Files:**
```
wizard/payslip_mass_send_compact_wizard.py     (NEW)
wizard/payslip_mass_send_compact_wizard_view.xml (NEW)
data/payslip_actions.xml                        (NEW - server action)
```

**Additional Time Required:** +2 hours (90 min implementation + 30 min testing)

---

## Open Questions

1. **Include Mass Send Functionality?** ⭐ CRITICAL
   - **Option A:** YES - Include Phase 8 (Mass Send) - **Recommended**
     - Total time: 6.5 hours
     - Supports efficient batch operations
     - Saves 21 minutes per payroll run
   - **Option B:** NO - Individual send only
     - Total time: 4.5 hours
     - Must send payslips one by one

2. **Button Label** - English or Spanish?
   - Option A: "Send Compact Payslip" (individual)
   - Option B: "Enviar Comprobante Compacto"
   - Current plan: English (matches existing "Send Mail" button)

3. **Mass Send Action Label** - If including Phase 8:
   - Option A: "Mass Send Compact Payslips"
   - Option B: "Enviar Comprobantes Compactos en Masa"
   - Current plan: English

4. **Email Subject Format** - Current proposal:
   - `[Comprobante] Pago SLIP/854 - Octubre 2025`
   - Alternative: `Comprobante de Pago - SLIP/854`

5. **Default Currency** - Which should be pre-selected?
   - Option A: USD (company currency) ← Current plan
   - Option B: VEB (most commonly used)

6. **Keep Both Buttons?**
   - Current plan: YES - Keep both "Send Mail" and "Send Compact Payslip"
   - Alternative: Replace "Send Mail" entirely?

---

**Status:** 📋 PLAN UPDATED WITH BATCH EMAIL ANALYSIS - READY FOR APPROVAL

**Estimates:**
- **Without Mass Send:** ~4.5 hours (Phases 1-7 only)
- **With Mass Send:** ~6.5 hours (Phases 1-9) ⭐ **Recommended**

**Recommendation:** Include Phase 8 (Mass Send) - Critical for efficient payroll operations with multiple employees.

---

**Related Documentation:**
- **Batch Email Analysis:** `/opt/odoo-dev/documentation/PAYSLIP_COMPACT_BATCH_EMAIL_ANALYSIS.md`
- **Email Integration Analysis:** `/opt/odoo-dev/documentation/PAYSLIP_COMPACT_SEND_MAIL_INTEGRATION.md`
- **Report Revision Analysis:** `/opt/odoo-dev/documentation/PAYSLIP_DETAILS_REPORT_REVISION.md`

Once approved, implementation can begin immediately.

---
