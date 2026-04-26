# HR Salary Advance / Loan System

**Status:** Testing | **Version:** 17.0.1.63.9 | **Module:** `ueipab_payroll_enhancements` (+ `ohrms_loan` + `ohrms_loan_accounting`)

Tracks employee salary advances granted outside of Odoo and recovers them automatically via payslip deductions — either via regular bi-weekly batches (`NOMINA_VE_V2`) or at termination via liquidation (`LIQUID_VE_V2`). Includes employee notification email, digital acknowledgment portal, and confirmation email to HR.

---

## Business Context

**Phase 1 (current):** Accounting recovery flow. HR records an advance already paid outside Odoo; the system deducts the balance from the designated payslip batch and notifies the employee.

**Phase 2 (future):** Full request-approval flow. Employee submits a request, manager approves, disbursement is recorded in Odoo, then same recovery + notification logic applies.

---

## Architecture

| Layer | Component | Purpose |
|---|---|---|
| Data model | `hr.loan` (Cybrosys `ohrms_loan`) | Loan record, installment schedule, approval workflow |
| Extension | `hr_loan_extension.py` | `recovery_type`, Bs fields, journal link, ack fields, defaults |
| Salary rules | `VE_LOAN_DED_V2`, `LIQUID_LOAN_DED_V2` | Deduction rules in each V2 structure |
| Payslip hook | `get_inputs()` override | Guards `LO` injection by `recovery_type` vs structure code |
| Journal entry | `_create_advance_journal_entry()` | DR 1.1.06.01.001 / CR bank — posted at approval |
| Reports | Disbursement Detail, Relación de Liquidación | Dedicated loan column / deduction line |
| Email notify | `action_send_advance_notification()` | Sends "Adelanto de Salario" template via `send_mail()` |
| Ack portal | `/loan/acknowledge/<id>/<token>` | Employee confirms receipt; confirmation email sent to employee + CC HR |
| Email templates | Employee Delivery, Adelanto Prestaciones, Adelanto Salario | Conditional loan notice / rate box / ack button |

---

## Recovery Types

| `recovery_type` | Salary Structure | When it deducts |
|---|---|---|
| `quincena` | `VE_PAYROLL_V2` (id=9) | Payslip whose `date_from–date_to` window contains the installment date |
| `liquidacion` | `LIQUID_VE_V2` (id=10) | Only from termination liquidation payslip |

For **quincena**: set installment date inside the target quincena window (Q1 = 1–15, Q2 = 16–end of month).
For **liquidacion**: set installment date inside the employee's final payslip period.

---

## Salary Rules

| Code | Structure | Seq | Debit | Credit | Formula |
|---|---|---|---|---|---|
| `VE_LOAN_DED_V2` | `VE_PAYROLL_V2` | 106 | `1.1.06.01.001` | `1.1.01.02.001` | `result = -(inputs.LO.amount) if inputs.LO else 0` |
| `LIQUID_LOAN_DED_V2` | `LIQUID_VE_V2` | 196 | `1.1.06.01.001` | `5.1.01.10.010` | `result = -(inputs.LO.amount) if inputs.LO else 0` |

**NET formulas updated:**
- `VE_TOTAL_DED_V2` — includes `VE_LOAN_DED_V2` (try/except block)
- `LIQUID_NET_V2` — includes `LIQUID_LOAN_DED_V2` (try/except block)

> **Rules created via shell** (not XML data) because `hr.salary.rule` has no `struct_id` field in this version — link via `structure.rule_ids` Many2many instead.

---

## Accounting Configuration

| Account | Name | Role |
|---|---|---|
| `1.1.06.01.001` | Cuentas por cobrar empleados m.nac.corri | Employee advance receivable (asset) |
| `1.1.01.02.001` | Banco Venezuela | Disbursement bank |
| `5.1.01.10.010` | Prestaciones sociales (PD) | Liquidation expense |

### Approval journal entry (auto-posted when `treasury_account_id` + `journal_id` set)

```
DR 1.1.06.01.001  Cuentas por cobrar empleados   $loan_amount
   CR treasury_account_id                         $loan_amount
```

Partner on both lines: `employee.work_contact_id` (NOT `address_id` — that resolves to the company).

### Quincena payslip recovery journal (NOMINA_VE_V2)

```
DR 5.1.01.10.001  Nómina (Docentes)    $850
   CR 1.1.01.02.001 Banco Venezuela     $800   ← actual cash to employee
   CR 1.1.06.01.001 Emp. Receivable      $50   ← advance partially cleared
```

### Liquidation payslip recovery journal (LIQUID_VE_V2)

```
DR 5.1.01.10.010  Prestaciones Sociales  $5,000
   CR 2.1.01.10.005 Provisión             $4,500
   CR 1.1.06.01.001 Emp. Receivable        $500
```

---

## Loan Form Fields

### Accounting auto-defaults (on new loan / employee selected)

| Field | Default | Source |
|---|---|---|
| `employee_account_id` | `1.1.06.01.001` | Hard-coded lookup |
| `treasury_account_id` | `1.1.01.02.001` | Hard-coded lookup |
| `journal_id` | `Nomina y Salarios, Bonos y Prestaciones Sociales` | Search by name |

**"Completar Datos Contables"** button: visible in header when any accounting field is empty and loan is not yet approved.

### Bs helper fields

| Field | Editable | Behaviour |
|---|---|---|
| `advance_bs_amount` | Until approved | Bs amount paid to employee. Onchange → recalculates `loan_amount` = bs ÷ rate. |
| `advance_exchange_rate` | Until approved | Auto-populated from latest VEB `company_rate`. Editable to match actual disbursement rate. |
| `loan_amount` | Always | USD obligation. Onchange → recalculates `advance_bs_amount` = usd × rate. Both directions work. |

### Smart buttons

| Button | Visible when | Action |
|---|---|---|
| **Asiento** (fa-book) | `move_id` is set | Opens journal entry |
| **Pendiente** (orange, fa-clock-o) | Approved + not acknowledged | Opens send wizard |
| **Confirmado** (green, fa-check-circle) | `loan_is_acknowledged` | Opens send wizard |

### Acknowledgment section

Appears on form after first email send (`loan_ack_token` is set):

| Field | Description |
|---|---|
| `loan_is_acknowledged` | Toggle (readonly) |
| `loan_acknowledged_date` | Timestamp of confirmation |
| `loan_acknowledged_ip` | IP address of confirmation |
| `loan_ack_url` | Portal URL (shown while pending) |

---

## Full Workflow: Phase 1

```
1. HR pays advance outside Odoo
2. HR creates hr.loan:
     - Employee, Monto Adelanto (Bs.) → loan_amount auto-calculates
     - recovery_type: quincena / liquidacion
     - Installment date inside target payslip window
3. Compute Installment → Submit → Approve
     → Journal entry posted: DR 1.1.06.01.001 / CR Banco
     → Asiento smart button appears
4. "📧 Enviar Notificación al Empleado"
     → token generated, send_mail() fires
     → Employee receives "Adelanto de Salario" email:
         - Monto in Bs, exchange rate box, repayment table in Bs
         - Legal declaration, green "Confirmar Recepción" button
5. Employee clicks ack link → landing page (Bs amounts, rate reference)
     → Clicks "Confirmar Recepción del Adelanto"
     → loan_is_acknowledged = True + date + IP
     → Confirmation email sent to employee + CC recursoshumanos@ueipab.edu.ve
     → Smart button turns green "Confirmado"
6. Next quincena batch computed for employee
     → get_inputs() injects LO = $loan_amount into payslip
     → VE_LOAN_DED_V2 fires → deducts from NET
7. Payslip confirmed
     → installment.paid = True
     → hr.loan.balance_amount decrements
     → When balance = 0 → loan fully recovered
```

---

## Key Technical Notes

### `get_inputs()` override
Runs after `ohrms_loan`'s override (MRO chain). Guards `LO` injection:
- `recovery_type='liquidacion'` + struct ≠ `LIQUID_VE_V2` → zero out LO
- `recovery_type='quincena'` + struct = `LIQUID_VE_V2` → zero out LO
- No double-deduction risk: `date_from ≤ installment_date ≤ date_to` check per quincena window

### Email templates — SQL management
All `mail.template.body_html` fields containing QWeb `<t>` tags **must be managed via direct SQL**. Odoo's `Html` field ORM sanitizer strips `<t t-esc>`, `<t t-if>`, etc. on every ORM write. Use `json.dumps` + `UPDATE mail_template SET body_html = %s::jsonb`.

| Template | DB id (testing) | DB id (production) | Managed via |
|---|---|---|---|
| Adelanto de Prestaciones Sociales | 71 | 50 | Direct SQL |
| Adelanto de Salario – Notificación | 75 | TBD | Direct SQL |
| Payslip Email - Employee Delivery | (noupdate=1) | — | ORM (no QWeb methods) |
| Pago Adelanto | (noupdate=1) | — | ORM (no QWeb methods) |

### Email amounts — local currency only
All employee-facing email templates show amounts in **Bs only** (no USD).
Exchange rate shown as informational reference box (`Tasa de Cambio Aplicada: Bs. X.XXXX`).

### `ohrms_loan` one-loan constraint
`ohrms_loan` blocks creating a new loan when the employee already has an approved loan with `balance_amount > 0`. This is a global constraint (not per `recovery_type`).

**Current behaviour:** HR must use a different employee OR wait until the existing loan balance reaches 0 before creating a new loan of any type.

**Future Option C:** Override `create()` to apply a per-`recovery_type` constraint — allows an employee to have both a `quincena` AND a `liquidacion` loan simultaneously. Not yet implemented; use a different employee for testing.

---

## Dependencies

| Module | Required | Purpose |
|---|---|---|
| `ohrms_loan` | Yes | `hr.loan` model, installment schedule, `get_inputs()` chain |
| `ohrms_loan_accounting` | Yes | Accounting fields (`employee_account_id`, `treasury_account_id`, `journal_id`) + journal entry on approval |

---

## Installation Sequence

```bash
# 1. Install ohrms_loan + ohrms_loan_accounting
docker exec odoo-dev-web /usr/bin/odoo -d testing \
    -i ohrms_loan,ohrms_loan_accounting \
    --stop-after-init --http-port=18069

# 2. Upgrade ueipab_payroll_enhancements
docker exec odoo-dev-web /usr/bin/odoo -d testing \
    -u ueipab_payroll_enhancements \
    --stop-after-init --http-port=18069

# 3. Run salary rules setup (migration 63.0 — required once)
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
    < /opt/odoo-dev/scripts/setup_loan_rules.py

# 4. Inject rate box into email templates via SQL (templates 71, 75)
# See fix scripts in session history

# 5. Restart
docker restart odoo-dev-web
```

---

## Reports & Email Templates

| Artifact | Change | Conditional? |
|---|---|---|
| Payroll Disbursement Detail | Dedicated "Loan Rec." column, excluded from "Other Ded" | Shows 0.00 when no loan |
| Relación de Liquidación | Deduction line with loan name + amount | Only if `LIQUID_LOAN_DED_V2` ≠ 0 |
| Payslip Email - Employee Delivery | Yellow loan recovery notice (Bs) | Only if `VE_LOAN_DED_V2` ≠ 0 |
| Pago Adelanto | Amount in Bs (× exchange_rate_used) | Standard |
| Adelanto de Prestaciones Sociales | Loan deduction row; exchange rate box retained | Only if `LIQUID_LOAN_DED_V2` ≠ 0 |
| **Adelanto de Salario** (new) | Full loan details, Bs amounts, rate box, ack button | Per loan |

---

## Production Deployment Notes

- Install `ohrms_loan` + `ohrms_loan_accounting` in production **before** upgrading `ueipab_payroll_enhancements`
- Run salary rules setup script manually (migration already ran in testing at 63.0)
- Apply SQL body patches for templates 71 (id=50 in prod) and 75 (new)
- Migration script is idempotent — safe to re-run

---

## Phase 2 Plan (Future)

1. Configure portal access for `hr.loan` (employee self-service requests)
2. Re-enable `ohrms_loan_accounting` journal entry OR use our `_create_advance_journal_entry()` for the actual disbursement
3. Override `create()` with per-`recovery_type` constraint (Option C) to allow quincena + liquidacion loans simultaneously
4. No changes needed to deduction logic, reports, or email/ack flow

---

## Changelog

| Version | Date | Change |
|---|---|---|
| 17.0.1.63.0 | 2026-04-26 | Initial implementation — recovery_type field, salary rules, payslip get_inputs() guard, Path B accounting, Disbursement Detail loan column, Relación de Liquidación loan deduction, conditional loan blocks in email templates. |
| 17.0.1.63.1 | 2026-04-26 | Bs helper fields (`advance_bs_amount`, `advance_exchange_rate`); auto-defaults for accounting fields; "Completar Datos Contables" button; `action_approve()` posts journal entry. |
| 17.0.1.63.2 | 2026-04-26 | Accounting defaults auto-fill on create() + employee onchange. |
| 17.0.1.63.3 | 2026-04-26 | Journal smart button (`move_id`); "Adelanto de Salario" email template; ack portal `/loan/acknowledge/<id>/<token>`; ack fields on loan form; "📧 Enviar Notificación" button. |
| 17.0.1.63.4 | 2026-04-26 | Remove USD from all employee-facing email templates; amounts in Bs only; exchange rate shown as reference box. Exchange rate box in Adelanto de Prestaciones (id=71) restored. |
| 17.0.1.63.5 | 2026-04-26 | Partner fix: `work_contact_id` (employee) instead of `address_id` (company) on journal entry lines. LO/0001 patched retroactively. |
| 17.0.1.63.6 | 2026-04-26 | `_onchange_loan_amount`: reverse Bs calculation (USD → Bs). Email send changed from compose wizard to `template.send_mail()` matching payslip batch pattern — fixes QWeb rendering. |
| 17.0.1.63.7 | 2026-04-26 | Ack landing page: USD removed, Bs + rate reference box added. Loan advance email: rate box added. |
| 17.0.1.63.8 | 2026-04-26 | Rate box in template 75 injected via direct SQL (ORM sanitizer strips `<t>` tags); `noupdate=1` restored. |
| 17.0.1.63.9 | 2026-04-26 | Confirmation email on ack: `_send_ack_confirmation_email()` sends to employee + CC `recursoshumanos@ueipab.edu.ve` on first confirmation only. |
