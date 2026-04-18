# Adelanto de Prestaciones Sociales — Payment Receipt Acknowledgment

**Status:** Deferred — keep as-is  
**Created:** 2026-04-18  
**Module:** `ueipab_payroll_enhancements`  
**Structure:** `LIQUID_VE_V2` only

---

## Business Issue

The Adelanto de Prestaciones Sociales is a sensitive termination-adjacent payment that
ideally requires two distinct confirmations:

| Event | When | What it proves |
|---|---|---|
| **Ack #1 — Consent** | Before/after payment | Employee reviewed document and agrees to receive the advance |
| **Ack #2 — Receipt** | After bank transfer confirmed | Employee confirms funds arrived in their bank account |

Currently only Ack #1 is tracked via `is_acknowledged` on `hr.payslip`.

---

## Current Implementation (as-is)

- HR computes LIQUID_VE_V2 payslip
- HR sends email via batch wizard (template id=50 prod / id=71 testing)
- Employee receives email with legal clauses (PRIMERO–CUARTO) and VEB amounts
- Employee clicks **"Enviar conformidad digital para recibir mi pago"**
- Landing page shows payslip details — employee clicks **"Confirmar Recepción Digital para recibir mi pago"**
- `is_acknowledged = True` + `acknowledged_date` + `acknowledged_ip` recorded on payslip

---

## Why a Second Ack Was Not Built (Yet)

Payment confirmation currently exists **only at banking level** — HR receives a payment
advice from the bank after the transfer is processed. There is no Odoo-side payment
trigger or bank integration.

Without an automated banking trigger, a second ack would require:
1. HR manually clicks "Notificar pago enviado" in Odoo after receiving bank advice
2. Second email auto-sent to employee
3. Employee clicks receipt confirmation link
4. `is_payment_received = True` recorded

This adds two manual touchpoints with no automated enforcement — process overhead
without proportional legal value, since the bank payment advice already proves funds
were sent at the institutional level.

---

## Recommended Workflow (interim — no code change)

Redefine timing of when HR sends the email:

```
Instead of: compute → send email → employee acks → bank transfer
Use:         compute → bank transfer → receive bank advice → send email → employee acks
```

With this sequence, the existing `is_acknowledged` becomes a genuine **payment receipt
confirmation** rather than pre-payment consent, without any code changes.

---

## Future Implementation Plan (when banking integration exists)

If a bank feed or payment advice import is added to Odoo, the full two-phase flow
becomes viable:

### Phase 1 — Pre-payment consent (existing)
- Email sent → employee reviews → clicks ack → `is_acknowledged = True`
- HR uses this as green light to proceed with bank transfer

### Phase 2 — Post-payment receipt (future)
- HR imports or pastes bank payment advice in Odoo
- System auto-sends second email: "Confirme recepción de fondos en su cuenta"
- Employee clicks → `is_payment_received = True` + timestamp + IP recorded
- Payslip fully closed only when both flags are True

### Fields to add (future)
| Field | Model | Type | Purpose |
|---|---|---|---|
| `is_payment_received` | `hr.payslip` | Boolean | Second ack flag |
| `payment_received_date` | `hr.payslip` | Datetime | Timestamp of receipt confirmation |
| `payment_received_ip` | `hr.payslip` | Char | IP at receipt confirmation |
| `bank_payment_reference` | `hr.payslip` | Char | Bank advice reference number |

### Controller change (future)
- New route: `/payslip/payment-received/{id}/{token}/confirm`
- Only accessible after `is_acknowledged = True`
- Different landing page text: "Confirme que ha recibido los fondos en su cuenta bancaria"

### Trigger options (future)
- **Manual button** on payslip/batch: "Marcar pago enviado" — HR clicks after bank advice, triggers second email
- **Automated** (ideal): bank feed integration sets `bank_payment_reference` → cron sends second email automatically

---

## Related Files

| File | Purpose |
|---|---|
| `addons/ueipab_payroll_enhancements/models/hr_payslip.py` | `is_acknowledged`, helper methods |
| `addons/ueipab_payroll_enhancements/controllers/payslip_acknowledgment.py` | Landing page, LIQUID_VE_V2 branching |
| `addons/ueipab_payroll_enhancements/data/mail_template_payslip.xml` | Template skeleton |
| `documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md` | Full ack system documentation |
| `documentation/CHANGELOG.md` | v1.62.2 deployment notes |
