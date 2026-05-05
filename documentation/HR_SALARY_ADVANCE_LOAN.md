# HR Salary Advance / Loan System

**Status:** Production | **Version:** 17.0.1.66.5 | **Module:** `ueipab_payroll_enhancements` (+ `ohrms_loan` + `ohrms_loan_accounting`)

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
| Payslip hook | `get_inputs()` override | One LO input per active loan; date ≤ payslip end; HR can zero to skip |
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
| `VE_LOAN_DED_V2` | `VE_PAYROLL_V2` | 106 | `1.1.06.01.001` | `1.1.01.02.001` | `slip = payslip.dict; result = -sum(l.amount for l in slip.input_line_ids if l.code == 'LO')` |
| `LIQUID_LOAN_DED_V2` | `LIQUID_VE_V2` | 196 | `1.1.06.01.001` | `5.1.01.10.010` | `slip = payslip.dict; result = -sum(l.amount for l in slip.input_line_ids if l.code == 'LO')` |

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
| `date` | Until approved | Actual disbursement date. Defaults to today. Override to backdate historical advances. Used as the journal entry date on approval. |
| `advance_bs_amount` | Until approved | Bs amount paid to employee. Onchange → recalculates `loan_amount` = bs ÷ rate. |
| `advance_exchange_rate` | Until approved | Auto-populated from latest VEB `company_rate`. When `date` is changed, the field is automatically updated to the BCV rate on or before that date (`_onchange_date_rate`). Editable to override manually. |
| `loan_amount` | Always | USD obligation. Onchange → recalculates `advance_bs_amount` = usd × rate. Both directions work. |

### Smart buttons

| Button | Visible when | Action |
|---|---|---|
| **Asiento** (fa-book) | `move_id` is set | Opens disbursement journal entry |
| **Comprobante(s)** (fa-file-text-o) | `clearing_payslip_count > 0` | Opens payslip(s) that cleared the loan |
| **Pendiente** (orange, fa-hourglass-start) | Approved + `recovery_status='pending'` | Non-navigable status indicator |
| **En Recuperación** (blue, fa-spinner) | `recovery_status='recovering'` | Non-navigable status indicator |
| **Saldado** (green, fa-check-circle) | `recovery_status='cleared'` | Non-navigable status indicator |
| **Pendiente conformidad** (orange, fa-clock-o) | Approved + not acknowledged | Opens send wizard |
| **Confirmado conformidad** (green, fa-check-circle) | `loan_is_acknowledged` | Opens send wizard |

### Recovery status field

`loan_recovery_status` (computed, not stored) on `hr.loan`:

| Value | Condition | Badge colour |
|---|---|---|
| `pending` | state ≠ approve OR balance = loan_amount (no payment yet) | Orange |
| `recovering` | 0 < balance < loan_amount (partial recovery) | Blue |
| `cleared` | balance ≤ 0 (fully recovered) | Green |

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
     → action_payslip_done() hook writes payslip_id back onto the loan line
     → "Comprobante(s)" smart button appears on loan form
     → "Saldado" recovery status button shows when balance = 0
     → When balance = 0 → ohrms_loan constraint lifted → new loan can be created
```

---

## Key Technical Notes

### `action_payslip_done()` override
Runs after `ohrms_loan`'s override (MRO chain). After `super()` marks installments `paid=True`, searches for `hr.loan.line` records that:
- Belong to the payslip's employee
- Are `paid=True` and `payslip_id` is unset (just cleared)
- Have `date` within `date_from ≤ date ≤ date_to`

Then writes `payslip_id = payslip.id` on those lines. This powers the "Comprobante(s)" smart button and the installment lines table link.

**Backfill note:** For loans paid before this code existed, run `backfill_sql.py` (or equivalent) to set `payslip_id` retroactively.

### `get_inputs()` override
Runs after `ohrms_loan`'s override (MRO chain). Guards `LO` injection:
- `recovery_type='liquidacion'` + struct ≠ `LIQUID_VE_V2` → zero out LO
- `recovery_type='quincena'` + struct = `LIQUID_VE_V2` → zero out LO
- No double-deduction risk: `date_from ≤ installment_date ≤ date_to` check per quincena window

### `action_paid_amount()` override on `hr.loan.line`
`ohrms_loan_accounting.action_paid_amount(month)` is called during payslip confirmation for each loan input. It creates an `account.move` in the loan journal with name `'LOAN/ {employee}/{month-year}'`.

**Two problems with the original behaviour:**
1. **Naming conflict** — when the same employee has two loans cleared in the same calendar month (e.g., LO/0002 cleared by ABRIL30 and LO/0003 cleared by ABRIL30-1, both April 2026), `action_paid_amount('April-2026')` generates the same entry name twice → `Validation Error: Another entry with the same name already exists`.
2. **Double accounting** — `VE_LOAN_DED_V2` / `LIQUID_LOAN_DED_V2` salary rules already post DR `1.1.06.01.001` / CR `1.1.01.02.001` inside the main PAY1 payroll entry. The `action_paid_amount()` entry posts the exact same DR/CR a second time.

**Fix (v1.64.6):** Override `action_paid_amount()` to return `True` immediately. The salary rule accounting in the PAY1 payroll entry is sufficient and correct.

### Recovery type messaging (v1.64.9)

All three employee-facing surfaces adapt their language based on `recovery_type`:

| Surface | `quincena` | `liquidacion` |
|---|---|---|
| Notification email — badge | Blue: *🗓️ Recuperación por Nómina Quincenal* | Amber: *📋 Recuperación por Liquidación Laboral* + warning note |
| Notification email — table header | *📅 Plan de Cuotas Quincenales* | *📋 Descuento en Liquidación Laboral* |
| Notification email — legal declaration | "…descontado de su nómina quincenal…" | "…descontado íntegramente de su liquidación laboral…, sin afectar su nómina regular." |
| Ack landing page | Modalidad row + blue badge + quincenal legal text | Modalidad row + amber badge + liquidación legal text |
| POST confirm page | Modalidad + quincenal recovery note | Modalidad + liquidación recovery note |
| Ack confirmation email | 🔄 Modalidad row + quincenal green note | 🔄 Modalidad row + "Su nómina regular no será afectada." |

Helper methods on `LoanAcknowledgmentController`:
- `_recovery_label(loan)` → human-readable label string
- `_recovery_note(loan)` → context-appropriate recovery sentence

This is especially important for `liquidacion` loans: the employee must understand that **no deductions will appear on their regular payslips** — the balance is cleared only via the termination liquidation payment.

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

### `ohrms_loan` one-loan constraint — REMOVED (v1.66.0)
`ohrms_loan` originally blocked creating a new loan when the employee already had an approved loan with `balance_amount > 0`. **This constraint is bypassed** in v1.66.0 via MRO in `HrLoan.create()` — unlimited concurrent loans per employee (Option A). See [Multiple Loans](MULTIPLE_LOANS_PER_EMPLOYEE.md).

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
| Payslip Email - Employee Delivery | Loan recovery row in ❌ Deducciones table (Bs) | Only if `VE_LOAN_DED_V2` ≠ 0 |
| Pago Adelanto | Amount in Bs (× exchange_rate_used) | Standard |
| Adelanto de Prestaciones Sociales | Loan deduction row; exchange rate box retained | Only if `LIQUID_LOAN_DED_V2` ≠ 0 |
| **Adelanto de Salario** (new) | Full loan details, Bs amounts, rate box, ack button | Per loan |

---

## Production Deployment Notes

**Scripts prepared (2026-05-04):**
- `scripts/setup_loan_rules.py` — idempotent, creates both rules + patches NET formulas. Run via Odoo shell.
- `scripts/deploy_loan_templates_prod.py` — standalone Python script (psycopg2). Creates template 75 + patches templates 37 and 50.

**Production template IDs (confirmed):**
| Template | Testing id | Production id |
|---|---|---|
| Payslip Email - Employee Delivery | 43 | **37** |
| Adelanto de Prestaciones Sociales | 71 | **50** |
| Adelanto de Salario – Notificación | 75 | **TBD** (created by script) |

**Deployment sequence:**
1. Backup `DB_UEIPAB`
2. Copy `ohrms_loan` + `ohrms_loan_accounting` to `/home/vision/ueipab17/addons/`
3. Copy `ueipab_payroll_enhancements` **v1.66.5** to production (backup old first)
4. Install modules: `docker exec -i ueipab17 /usr/bin/odoo -d DB_UEIPAB -i ohrms_loan,ohrms_loan_accounting --stop-after-init --http-port=18069`
5. Upgrade: `docker exec -i ueipab17 /usr/bin/odoo -d DB_UEIPAB -u ueipab_payroll_enhancements --stop-after-init --http-port=18069`
6. Run salary rules: `docker exec -i ueipab17 /usr/bin/odoo shell -d DB_UEIPAB --no-http < setup_loan_rules.py`
7. Run template script: `python3 deploy_loan_templates_prod.py`
8. Restart: `docker restart ueipab17`
9. Verify: PAY1 clean, rules exist, loan form accessible, existing payslips unaffected

**Other notes:**
- PAY1 sequence check: already confirmed clean (no `LOAN/` entries) as of 2026-05-04
- `ohrms_loan` one-loan constraint is global — document for HR team
- LIQUID_VE_V2 payslips for loan employees must be created individually (not via batch)

---

## Known Issues / Post-Install Cleanup

### ~~Liquidation payslip created via batch does not pick up LO input~~ — FIXED v1.66.0

`get_inputs()` was fully rewritten in v1.66.0. It now checks `self.struct_id.code` directly on the payslip and searches active loans by `recovery_type`, bypassing `contracts.get_all_structures()` entirely. Batch-created payslips with struct_id set will correctly auto-populate LO inputs.

### PAY1 Sequence Contamination (testing env — fixed 2026-04-27)

`ohrms_loan_accounting.action_paid_amount()` created entries in the PAY1 journal with **explicit custom names** in format `LOAN/ {employee}/April-YYYY`. In Odoo 17, `account.move` naming works by prefix-continuation: the next unnamed entry in a journal inherits the prefix of the most recent posted entry. Once a `LOAN/ EMPLOYEE/April-` entry was the latest in PAY1, every subsequent unnamed PAY1 move (payroll accounting entries AND advance disbursements) got a `LOAN/` name with an incrementing counter instead of the correct `PAY1/YYYY/MM/NNNN` format.

**Affected entries in testing (IDs 2435, 2437, 2438, 2442)** — corrected via direct SQL on 2026-04-27:

```sql
-- Run only if LOAN/ entries exist in PAY1 journal for the affected period
-- Adjust IDs and sequence numbers to match your environment
UPDATE account_move SET name='PAY1/2026/04/0003', sequence_prefix='PAY1/2026/04/', sequence_number=3  WHERE id=2435;
UPDATE account_move SET name='PAY1/2026/04/0004', sequence_prefix='PAY1/2026/04/', sequence_number=4  WHERE id=2437;
UPDATE account_move SET name='PAY1/2026/04/0005', sequence_prefix='PAY1/2026/04/', sequence_number=5  WHERE id=2438;
UPDATE account_move SET name='PAY1/2026/04/0006', sequence_prefix='PAY1/2026/04/', sequence_number=6  WHERE id=2442;
```

**Note:** Entries 2434 (`LOAN/ GLADYS.../April-2026`, ref=LO/0001) and 2436 (`LOAN/ GUSTAVO.../April-2026`, ref=LO/0002) were created intentionally by `action_paid_amount()` and represent **double-accounting** of the loan recovery deduction (same DR/CR as `VE_LOAN_DED_V2` salary rule in the payroll entry). These should be reversed/cancelled in a future cleanup, but do not affect PAY1 sequence going forward since their prefix is distinct from `PAY1/YYYY/MM/`.

**Production:** If `ohrms_loan_accounting` is installed in production and any payslips with loan deductions have been confirmed, run the equivalent query to find and fix contaminated entries before or shortly after deploying v1.64.6.

---

## Phase 2 Plan (Future)

1. Configure portal access for `hr.loan` (employee self-service requests)
2. Re-enable `ohrms_loan_accounting` journal entry OR use our `_create_advance_journal_entry()` for the actual disbursement
3. ~~Override `create()` with per-`recovery_type` constraint (Option C)~~ — resolved in v1.66.0 (Option A: no constraint)
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
| 17.0.1.64.0 | 2026-04-27 | Payroll Disbursement Detail Excel: added "Loan Rec." column (K), shifted Total Ded→L, Net→M. |
| 17.0.1.64.1 | 2026-04-27 | Payslip Email (id=43): loan deduction block added. Initial patch to template. |
| 17.0.1.64.2 | 2026-04-27 | Payslip Email: loan notice also patched on template id=43 (id=59 was wrong target). |
| 17.0.1.64.3 | 2026-04-27 | Payslip Email: loan row moved into ❌ Deducciones table. Removed standalone yellow box. |
| 17.0.1.64.4 | 2026-04-27 | Payslip Email: fixed `es_VE` key sync (ORM uses es_VE; old yellow box was still in that key). Switched from `<tr t-if>` to `<t t-set>/<t t-if><tr>` pattern — `<tr t-if>` not processed by Odoo mail renderer. |
| 17.0.1.64.5 | 2026-04-27 | Loan form UI enhancements: `loan_recovery_status` badge (Pendiente/En Recuperación/Saldado), "Comprobante(s)" smart button, installment lines table: `payslip_id` column + row colour, `action_payslip_done()` hook writes `payslip_id` back onto cleared loan lines. |
| 17.0.1.64.6 | 2026-04-27 | Override `hr.loan.line.action_paid_amount()` to no-op: eliminates "Another entry with the same name" conflict when same employee has two loans cleared in the same month, and removes double-accounting (salary rules already handle DR/CR in PAY1 payroll entry). |
| DB-only fix | 2026-04-27 | PAY1 journal sequence restored: renamed contaminated entries 2435, 2437, 2438, 2442 from `LOAN/ EMPLOYEE/April-NNNN` to proper `PAY1/2026/04/000N` names + updated `sequence_prefix`/`sequence_number`. Next PAY1/2026/04/ entry = 0007. |
| 17.0.1.64.7 | 2026-04-27 | `hr.loan.date` editable until approved (override ohrms_loan's unconditional `readonly=True`). `_create_advance_journal_entry()` now uses `self.date or today` so the journal entry date matches the actual disbursement date. Enables correct backdating for historical advances. |
| 17.0.1.64.8 | 2026-04-28 | `_get_veb_rate(for_date)` now accepts a date parameter: fetches last BCV rate on or before that date. New `@api.onchange('date')` auto-populates `advance_exchange_rate` when the loan date is changed — required for historical advances to get the correct period rate. |
| 17.0.1.64.9 | 2026-04-28 | Recovery type messaging across all 3 surfaces: notification email, ack landing page, and ack confirmation email all display recovery-type-specific badge, table title, legal declaration, and confirmation note for `quincena` (blue) vs `liquidacion` (amber). Prevents confusion for liquidacion employees who see no quincena deductions. |
| 17.0.1.65.0 | 2026-05-04 | `total_net_amount` on `hr.payslip.run` now includes `LIQUID_NET_V2` code — batch totals were showing 0 for liquidation-only batches. Relación de Liquidación: loan deduction `amount_formatted` sign fix — was using `abs()` causing positive display inconsistent with other deductions. |
| 17.0.1.66.0 | 2026-05-04 | **Multiple loans per employee (Option A).** `HrLoan.create()` bypasses ohrms_loan one-loan constraint via MRO. `get_inputs()` rewritten: one LO input per active loan (date ≤ payslip end — handles skipped periods), removes last-wins bug. `action_payslip_done()` rewritten: uses `loan_line_id` directly, reverts paid=True for LO inputs HR zeroed out (skip). Salary rules `VE_LOAN_DED_V2`/`LIQUID_LOAN_DED_V2` updated to `sum all LO inputs` via `payslip.dict.input_line_ids`. Relación de Liquidación: removed `limit=1`, shows all active liquidación loans. |
