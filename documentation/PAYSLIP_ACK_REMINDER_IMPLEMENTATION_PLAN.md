# Payslip Acknowledgment Reminder System - Implementation Plan

**Created:** 2025-12-16
**Status:** Ready for Review
**Module:** `ueipab_payroll_enhancements`
**Priority:** High (based on current low acknowledgment rates)

---

## Problem Statement

Based on current data (2025-12-16):

| Batch | Total | Acknowledged | Pending | % Done |
|-------|-------|--------------|---------|--------|
| DICIEMBRE15 | 44 | 16 | 28 | 36.4% |
| NOVIEMBRE30 | 44 | 11 | 33 | 25.0% |

**61 payslips pending acknowledgment** - employees may have forgotten to click the confirmation button.

---

## Proposed Solution

### Component 1: Manual Reminder Button (Batch Form)

**Button:** "📧 Enviar Recordatorio a Pendientes" on batch form header

**Location:** Next to existing "Send Payslips by Email" button

**User Flow:**
```
1. Open Payslip Batch form (e.g., DICIEMBRE15)
2. Click "📧 Enviar Recordatorio a Pendientes"
3. Confirmation dialog: "Se enviará recordatorio a 28 empleados pendientes. ¿Continuar?"
4. System sends reminder emails
5. Notification: "✅ Recordatorio enviado a 28 empleados"
```

**Logic:**
```python
def action_send_ack_reminder(self):
    """Send reminder email to employees who haven't acknowledged."""
    self.ensure_one()

    pending = self.slip_ids.filtered(
        lambda s: not s.is_acknowledged
        and s.state in ['done', 'paid']
        and s.employee_id.work_email
    )

    if not pending:
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'No hay comprobantes pendientes de confirmación',
                'type': 'warning',
            }
        }

    template = self.env.ref('ueipab_payroll_enhancements.email_template_payslip_ack_reminder')

    sent_count = 0
    for payslip in pending:
        try:
            template.send_mail(payslip.id, force_send=True)
            payslip.ack_reminder_count += 1
            payslip.ack_reminder_last_date = fields.Datetime.now()
            sent_count += 1
        except Exception as e:
            _logger.error(f"Failed to send reminder to {payslip.employee_id.name}: {e}")

    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'message': f'✅ Recordatorio enviado a {sent_count} empleados',
            'type': 'success',
        }
    }
```

---

### Component 2: New Payslip Fields (Reminder Tracking)

**Fields to add to `hr.payslip`:**

| Field | Type | Description |
|-------|------|-------------|
| `ack_reminder_count` | Integer | Number of reminders sent |
| `ack_reminder_last_date` | Datetime | Last reminder sent date |

**View Enhancement:** Show reminder info in payslip form (readonly):
- "Recordatorios enviados: 2"
- "Último recordatorio: 2025-12-16 09:00"

---

### Component 3: Email Template (Nice Layout)

**Template ID:** `email_template_payslip_ack_reminder`

**Subject:** `⏰ Recordatorio: Confirmar recepción de comprobante │ {{ object.number }}`

**Email Template HTML:**

```html
<div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f4f4f4;margin:0;padding:20px">
    <div style="max-width:800px;margin:0 auto;background-color:white;border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,0.1);overflow:hidden">

        <!-- Header with ORANGE gradient (reminder color) -->
        <div style="background:linear-gradient(135deg,#f39c12 0%,#e74c3c 100%);color:white;padding:30px;text-align:center">
            <h1 style="margin:0;font-size:28px;font-weight:600">⏰ Recordatorio</h1>
            <p style="margin:5px 0 0 0;font-size:16px;opacity:0.9">Confirmación de Comprobante Pendiente</p>
        </div>

        <!-- Content -->
        <div style="padding:30px">
            <t t-set="batch_name" t-value="object.payslip_run_id.name if object.payslip_run_id else 'N/A'"/>
            <t t-set="exchange_rate" t-value="object.exchange_rate_used or 1.0"/>

            <!-- Greeting -->
            <p style="font-size:16px;color:#333;margin-bottom:20px">
                Estimado(a) <strong><t t-out="object.employee_id.name"/></strong>,
            </p>

            <p style="font-size:15px;color:#555;margin-bottom:25px">
                Le recordamos que tiene pendiente la confirmación de recepción de su comprobante de pago.
                Por favor, revise los detalles a continuación y confirme haciendo clic en el botón.
            </p>

            <!-- Payslip Info Box -->
            <div style="background:#fff9e6;border:2px solid #f39c12;border-radius:8px;padding:20px;margin-bottom:25px">
                <div style="display:flex;justify-content:space-between;margin-bottom:10px;padding:8px 0;border-bottom:1px solid #f5e6c8">
                    <span style="font-weight:600;color:#856404;font-size:14px">📋 Nro. Comprobante:</span>
                    <span style="color:#333;font-size:14px"><t t-out="object.number"/> │ <t t-out="batch_name"/></span>
                </div>
                <div style="display:flex;justify-content:space-between;margin-bottom:10px;padding:8px 0;border-bottom:1px solid #f5e6c8">
                    <span style="font-weight:600;color:#856404;font-size:14px">📅 Período:</span>
                    <span style="color:#333;font-size:14px">
                        <t t-out="object.date_from" t-options='{"widget":"date","format":"dd/MM/yyyy"}'/> →
                        <t t-out="object.date_to" t-options='{"widget":"date","format":"dd/MM/yyyy"}'/>
                    </span>
                </div>
                <div style="display:flex;justify-content:space-between;padding:8px 0">
                    <span style="font-weight:600;color:#856404;font-size:14px">💵 Monto Neto:</span>
                    <span style="color:#333;font-size:16px;font-weight:bold">
                        Bs. <t t-esc="'{:,.2f}'.format((object.net_wage or 0.0) * exchange_rate)"/>
                    </span>
                </div>
            </div>

            <!-- Reminder Count (if > 1) -->
            <t t-if="object.ack_reminder_count and object.ack_reminder_count > 1">
                <p style="font-size:13px;color:#e74c3c;text-align:center;margin-bottom:20px">
                    ⚠️ Este es el recordatorio #<t t-out="object.ack_reminder_count"/>
                </p>
            </t>
        </div>

        <!-- Acknowledgment Button (GREEN) -->
        <div style="background:linear-gradient(135deg,#28a745 0%,#20c997 100%);padding:25px 30px;text-align:center">
            <p style="margin:0 0 15px 0;color:white;font-size:16px;font-weight:600">✅ Confirmar Recepción del Comprobante</p>
            <p style="margin:0 0 20px 0;color:rgba(255,255,255,0.9);font-size:14px">
                Al hacer clic, confirma que ha recibido y revisado este comprobante de pago.
            </p>
            <a t-att-href="object._get_acknowledgment_url()"
               style="display:inline-block;background:white;color:#28a745;padding:15px 40px;font-size:16px;font-weight:bold;text-decoration:none;border-radius:8px;box-shadow:0 4px 15px rgba(0,0,0,0.2)">
                Confirmar Recepción
            </a>
            <p style="margin:15px 0 0 0;color:rgba(255,255,255,0.8);font-size:12px">
                Su confirmación quedará registrada con fecha, hora e IP
            </p>
        </div>

        <!-- Footer -->
        <div style="background:#f8f9fa;padding:20px 30px;border-top:1px solid #e0e0e0;text-align:center;font-size:13px;color:#666;line-height:1.6">
            <p style="margin:5px 0"><strong style="color:#f39c12">📧 ¿Dudas o consultas?</strong></p>
            <p style="margin:5px 0">Escribir al correo <strong style="color:#f39c12">recursoshumanos@ueipab.edu.ve</strong></p>
            <p style="margin-top:15px;color:#999;font-size:12px">
                Este es un recordatorio automático. Si ya confirmó su comprobante, por favor ignore este mensaje.
            </p>
        </div>
    </div>
</div>
```

**Template Design Notes:**
- **Header:** Orange/red gradient (⚠️ reminder urgency) vs purple for original payslip
- **Info Box:** Yellow background with payslip summary (not full breakdown)
- **Shows:** Payslip number, period, and net amount only (simplified)
- **Reminder Count:** Shows "Este es el recordatorio #2" if sent multiple times
- **Same acknowledgment button** as original email (green, same URL)

---

### Component 4: Optional - Automatic Cron Job

**Status:** Optional (can implement later if needed)

**Cron:** `ir.cron` - Run daily at 9:00 AM Venezuela time

**Logic:**
```python
def _cron_payslip_ack_reminder(self):
    """Auto-send reminder after 3 days if not acknowledged."""
    threshold = fields.Date.today() - timedelta(days=3)

    pending = self.env['hr.payslip'].search([
        ('is_acknowledged', '=', False),
        ('state', 'in', ['done', 'paid']),
        ('create_date', '<=', threshold),
        ('ack_reminder_count', '<', 2),  # Max 2 automatic reminders
    ])

    template = self.env.ref('ueipab_payroll_enhancements.email_template_payslip_ack_reminder')
    for payslip in pending:
        if payslip.employee_id.work_email:
            template.send_mail(payslip.id, force_send=True)
            payslip.ack_reminder_count += 1
            payslip.ack_reminder_last_date = fields.Datetime.now()
```

**Recommendation:** Start with manual button only. Add cron later if needed.

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `models/hr_payslip.py` | Modify | Add `ack_reminder_count`, `ack_reminder_last_date` fields |
| `models/hr_payslip_run.py` | Modify | Add `action_send_ack_reminder()` method |
| `views/hr_payslip_run_view.xml` | Modify | Add reminder button to batch form |
| `views/hr_payslip_view.xml` | Modify | Show reminder info in payslip form |
| `data/email_template_ack_reminder.xml` | Create | Reminder email template |
| `data/ir_cron_ack_reminder.xml` | Create (Optional) | Automatic daily cron |
| `security/ir.model.access.csv` | Verify | Ensure access rules are correct |
| `__manifest__.py` | Modify | Add new XML files, bump version |

---

## Implementation Steps

### Step 1: Add Fields to hr.payslip
```python
# In models/hr_payslip.py
ack_reminder_count = fields.Integer(
    string="Reminder Count",
    default=0,
    readonly=True
)
ack_reminder_last_date = fields.Datetime(
    string="Last Reminder Date",
    readonly=True
)
```

### Step 2: Create Email Template XML
```xml
<!-- data/email_template_ack_reminder.xml -->
<odoo>
    <record id="email_template_payslip_ack_reminder" model="mail.template">
        <field name="name">Payslip Acknowledgment Reminder</field>
        <field name="model_id" ref="hr_payroll_community.model_hr_payslip"/>
        <field name="subject">⏰ Recordatorio: Confirmar recepción │ {{ object.number }}</field>
        <field name="email_from">"Recursos Humanos" &lt;recursoshumanos@ueipab.edu.ve&gt;</field>
        <field name="email_to">{{ object.employee_id.work_email }}</field>
        <field name="email_cc">recursoshumanos@ueipab.edu.ve</field>
        <field name="body_html" type="html">
            <!-- Template HTML from above -->
        </field>
        <field name="auto_delete" eval="True"/>
    </record>
</odoo>
```

### Step 3: Add Button to Batch Form
```xml
<!-- In views/hr_payslip_run_view.xml -->
<button name="action_send_ack_reminder"
        type="object"
        string="📧 Recordatorio Pendientes"
        class="btn-warning"
        confirm="Se enviará recordatorio a los empleados que no han confirmado. ¿Continuar?"
        invisible="state != 'close'"/>
```

### Step 4: Add Method to hr.payslip.run
```python
# In models/hr_payslip_run.py
def action_send_ack_reminder(self):
    # Implementation from above
    pass
```

### Step 5: Update Manifest
```python
# In __manifest__.py
'version': '17.0.1.48.0',
'data': [
    # ... existing files ...
    'data/email_template_ack_reminder.xml',
],
```

---

## Testing Plan

1. **Unit Test:** Create batch, generate payslips, mark some as acknowledged
2. **Button Test:** Click reminder button, verify only pending employees receive email
3. **Email Test:** Verify email renders correctly with all fields
4. **Tracking Test:** Verify `ack_reminder_count` increments
5. **Edge Cases:**
   - Empty batch (no pending)
   - All acknowledged (button shows warning)
   - Employee without email (skipped)

---

## Rollout Plan

1. **Phase 1:** Deploy to Testing environment
2. **Phase 2:** Manual testing with test batch
3. **Phase 3:** Deploy to Production
4. **Phase 4:** Send reminders for NOVIEMBRE30 and DICIEMBRE15 pending

---

## Questions for Review

1. **Button visibility:** Show button always or only when batch is closed/confirmed?
2. **Max reminders:** Limit to 2 reminders per payslip? Or unlimited manual?
3. **Cron job:** Implement automatic reminders now or later?
4. **CC email:** Should reminders also CC recursoshumanos@ueipab.edu.ve?

---

## Approval

- [ ] Plan reviewed and approved
- [ ] Ready to implement

**Estimated Implementation Time:** 2-3 hours
