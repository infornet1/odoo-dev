# UEIPAB Odoo Development - Changelog

This file contains detailed version history, bug fixes, and deployment notes moved from CLAUDE.md.

---

## Production Deployments

### 2026-04-07 - PAY1 Sequence Conflict — Permanent Auto-fix (`ueipab_payroll_enhancements` v1.61.2)

**Implemented two-layer permanent prevention of PAY1 sequence/date mismatch errors.**

| Item | Details |
|------|---------|
| **Problem** | When the PAY1 journal sequence advances into a new month (e.g. April), payslips with `date_to` still in the prior month (e.g. March 31) fail validation: `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/xxxx"` |
| **Layer 1 — Early Warning** | `_collect_date_issues()` (Check 5) detects the sequence/date mismatch before the user clicks Validate. The date check wizard displays an **"Auto-fix Accounting Dates"** button that sets `slip.date` on all draft payslips to the first day of the sequence month. |
| **Layer 2 — Safety Net** | `action_validate_payslips()` override auto-detects any remaining conflict just before confirming payslips and silently sets `slip.date` if needed. Logs the adjustment via Python logger. No popup shown. |
| **Detection method** | Queries `account_move` for the latest posted entry in the payslip journal; extracts year/month from name pattern `PAY1/YYYY/MM/NNNN`. Compares against batch `date_end`. |
| **Files** | `models/hr_payslip_run.py` (+3 methods), `wizard/payslip_batch_date_check_wizard.py` (+`seq_fix_date` field, +`action_fix_accounting_dates`), `wizard/payslip_batch_date_check_wizard_view.xml` (info banner + button) |
| **Version** | `17.0.1.61.2` |

---

### 2026-04-07 - MARZO31-G3 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of DAVID HERNANDEZ payslip in MARZO31-G3 (batch id=43).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number PAY1/2026/04/0025"` |
| **Root Cause** | Same pattern as MARZO31-15 (2026-04-06): PAY1 sequence locked in April 2026, payslip `date=NULL` falls back to `date_to=2026-03-31` → sequence mismatch |
| **Fix** | Permanent fix (v1.61.2) handles this automatically at validate time |

---

### 2026-04-06 - MARZO31-15 Batch Validation Fix — PAY1 Sequence/Date Mismatch (Production operational fix)

**Fixed validation error preventing confirmation of payslip batch MARZO31-15 (id=42, 19 employees).**

| Item | Details |
|------|---------|
| **Error** | `"The Date (03/31/2026) doesn't match the sequence number of the related Journal Entry (PAY1/2026/04/0006)"` |
| **Root Cause** | PAY1 journal sequence had already advanced to April (`04`) because a prior April-period payslip (ISMARY ARCILA `PAY1/2026/04/0001`) was posted with a March 31 accounting date, pushing the sequence counter into April. All subsequent entries get `PAY1/2026/04/*` sequence numbers. Odoo 17 validates that the entry date month matches the sequence month — March 31 vs April sequence = rejected. |
| **Fix** | Set `date` (accounting date) field to `2026-04-01` on all 19 draft payslips via Odoo shell. `hr_payroll_account_community` uses `slip.date or slip.date_to` for the journal entry date — with `date=NULL` it fell back to `date_to` (2026-03-31). |
| **Action** | `env['hr.payslip'].browse([batch_42_slip_ids]).write({'date': date(2026, 4, 1)})` |

**Result:** 19 journal entries posted as `PAY1/2026/04/0006` → `PAY1/2026/04/0024`, all dated 2026-04-01. Batch closed successfully.

**Accounting Impact:**

| Account | Debit | Credit |
|---------|-------|--------|
| `5.1.01.10.001` Nómina (Docentes) | 3,013.85 | 29.20 |
| `1.1.01.02.001` Banco Venezuela | 29.20 | 3,013.85 |
| **Net payroll expense / bank outflow** | **2,984.65** | **2,984.65** |

**Period note:** These 19 entries (payroll period 2026-03-16→31) post to **April's accounting period** (date=2026-04-01), not March. All other MARZO31 batches posted on 2026-03-31. Finance team informed: March P&L understated by USD 2,984.65; April overstated by same amount. No system correction needed unless March books require restatement.

**Root cause pattern — how to avoid in future:**
> When posting April-period payslips with a March 31 accounting date, Odoo's PAY1 sequence advances to April. Any remaining March-dated payslips then fail with this mismatch. Solution: always post out-of-period payslips with an accounting date that matches the current sequence month, or confirm all March payslips before confirming any April-period ones.

---

### 2026-04-06 - Batch Email Wizard Confirm Step Filter Fix (`ueipab_payroll_enhancements` view patch)

**Fixed confirm step showing all employees instead of only selected ones.**

| Item | Details |
|------|---------|
| **Problem** | Step 2 "Selected Employees" section displayed all employees regardless of selection state |
| **Root Cause** | `domain` on One2many field in Odoo 17 form views does not filter displayed records — only restricts new record creation |
| **Fix** | Added computed `Many2many` field `selected_ids` filtered server-side; confirm block uses `selected_ids` instead of `selection_ids` with broken domain |
| **Files** | `wizard/batch_email_wizard.py` (+computed field), `wizard/batch_email_wizard_view.xml` (field swap) |
| **Deployed** | Both testing and production |

---

### 2026-04-06 - Batch Email Wizard `boolean_toggle` Fix (`ueipab_payroll_enhancements` v60.1 view patch)

**Fixed `RPC_ERROR` when unchecking individual employees in the Send Emails wizard.**

| Item | Details |
|------|---------|
| **Problem** | Clicking any individual checkbox in the employee selection list inside the "Send Emails (with Progress)" wizard threw a Validation Error: `wizard_id` missing on `hr.payslip.batch.email.selection` |
| **Root Cause** | `boolean_toggle` widget fires an immediate `webSave` on the child record, sending only the changed field — ORM rejected because `wizard_id` (`required=True`) was absent from the auto-save payload |
| **Fix** | Removed `widget="boolean_toggle"` from `selected` field in selection tree; standard checkbox saves on row blur / form submit, which includes full context |
| **File** | `wizard/batch_email_wizard_view.xml` — 1-line change |
| **Deployed** | View-only patch applied directly; production manifest version unchanged (60.1) |

**Workaround that worked before fix:** Use "Select All" / "Deselect All" / "Select With Email Only" bulk buttons.

---

### 2026-02-08 - Contact Data Sync Fix (Bounce Log + Partner Emails)

**Fixed cross-reference inconsistencies between Odoo, Freescout bounces, Customers sheet, and Akdemia.**

**Category A — 7 not-found bounce logs linked to correct partners:**
- Linked bounce logs #30, #32, #33, #46, #54, #56, #58 to their matching partners
- Updated `action_tier` from `not_found` to `flag` (temporary) or `clean` (permanent)
- Appended bounced emails to partner email fields (multi-email `;` pattern)
- Contacts: DAIRILYS CHAURAN, ANTONIO MARTINEZ, MARIA APONTE, DOALBERT NUÑEZ, FRANCIA LORETO, CASTO GONZALEZ, GLORIA MILLAN

**Category B — MIGUEL MARIN #3663:**
- Added `susanaquijada102@gmail.com` as secondary email in Odoo (mother's email from Akdemia)
- Updated Customers Google Sheet row 128 to include both emails

**Category C — SORELIS MAITA #3669:**
- Flagged for manual mobile lookup (no phone/mobile in any data source)
- Glenda cannot WhatsApp without mobile number

**Category D — Perdomo duplicates cleanup:**
- Deleted 3 irrelevant bounce logs (#27, #28, #29) — staff, not Representante
- Archived 2 duplicate partners (#3612 Alberto J Perdomo, #3676 Gustavo Perdomo)
- Added `perdomo.gustavo@gmail.com` as secondary email on real user #7

**Category E — 8 orphan bounces:** No action (no match in any data source)

**Verification:** 37 bounce logs total, 29 linked to partners, 8 orphans as expected.

**Scripts:** `scripts/contact_data_sync_fix.py`, `scripts/contact_sync_comparison.py`

---

### 2026-01-10 - LIQUID_VE_V2 Accounting Configuration Fix

**Fixed payslip confirmation error for Liquidación Venezolana V2:**

| Item | Details |
|------|---------|
| **Problem** | SLIP/313 (STEFANY ROMERO) could not be confirmed: "choose Debit and Credit account for at least one salary rule" |
| **Root Cause** | `LIQUID_VE_V2` structure had no accounting accounts configured on any salary rules |
| **Solution** | Configured `LIQUID_NET_V2` rule with debit/credit accounts |
| **Affected Structure** | LIQUID_VE_V2 (Liquidación Venezolana V2) |

**Accounts Configured:**

| Rule | Debit Account | Credit Account |
|------|---------------|----------------|
| LIQUID_NET_V2 | 5.1.01.10.010 (Prestaciones sociales) | 2.1.01.10.005 (Provisión Prestaciones Sociales) |

**Environment Comparison:**
- **Testing:** All 14 rules have accounting configured (more comprehensive)
- **Production:** Only NET rule configured (minimum required - follows design pattern)

**Note:** Per Odoo payroll accounting design, only NET/deduction rules need accounting. Earnings rules should NOT post to accounting.

---

### 2026-01-08 - Salary Rules & Email Template Fix for Remainder Batches

**Fixed salary rules not applying percentage to remainder batches:**

| Item | Details |
|------|---------|
| **Problem** | Remainder batches (is_remainder_batch=True) computed at 100% instead of 50% |
| **Root Cause** | Salary rules only checked `is_advance_payment`, not `is_remainder_batch` |
| **Solution** | Updated condition to check both flags |
| **Rules Fixed** | VE_SALARY_V2, VE_EXTRABONUS_V2, VE_BONUS_V2 |

**Salary Rule Fix:**
```python
# Before (only advance batches got percentage)
if payslip.payslip_run_id and payslip.payslip_run_id.is_advance_payment:

# After (both advance AND remainder batches get percentage)
if payslip.payslip_run_id and (payslip.payslip_run_id.is_advance_payment or payslip.payslip_run_id.is_remainder_batch):
```

**Email Template Updated (ID 45 prod / ID 66 testing):**
- Removed percentage multiplication (salary rules now handle it)
- Uses `net_wage` directly: `<t t-set="rest_usd" t-value="object.net_wage or 0.0"/>`
- Removed "Tasa de Cambio Actual" section

**Synced:** Both production and testing environments updated

### 2026-01-07 - Payslip Batch Delete Fix (NewId Sorting Error)

**Fixed TypeError when deleting payslips from batch UI:**

| Item | Details |
|------|---------|
| **Problem** | Deleting payslip from batch view caused `TypeError: '<' not supported between instances of 'NewId' and 'NewId'` |
| **Root Cause** | `_compute_exchange_rate` sorted payslips by `s.id`, but during onchange operations unsaved records have `NewId` objects that can't be compared |
| **Solution** | Filter to only saved records (with integer IDs) before sorting, with fallback for unsaved slips |
| **File Changed** | `hr_payslip_run.py` line 180 |
| **Version** | 17.0.1.51.2 |

**Fix Applied:**
```python
# Before (broken)
first_slip = batch.slip_ids.sorted(lambda s: s.id)[0]

# After (fixed)
real_slips = batch.slip_ids.filtered(lambda s: isinstance(s.id, int))
if real_slips:
    first_slip = real_slips.sorted(lambda s: s.id)[0]
else:
    first_slip = batch.slip_ids[0]  # Fallback for unsaved slips
```

### 2025-11-27 - Password Reset URL Fix (dbfilter)

**Fixed invitation/password reset email links returning 404:**

| Item | Details |
|------|---------|
| **Problem** | Users clicking password reset links got "Not Found" error |
| **Root Cause** | `dbfilter = ^(DB_UEIPAB\|testing)$` allowed multiple DBs, preventing auto-session |
| **Solution** | Changed to `dbfilter = ^DB_UEIPAB$` (single database) |
| **File Changed** | `/etc/odoo/odoo.conf` in `ueipab17` container |
| **Impact** | 30 pending invitation tokens now work directly |

**Diagnosis:**
- Route `/web/reset_password` uses `auth='public'` + `website=True`
- Without active session, Odoo couldn't determine which database to use
- Single-database filter enables automatic session creation

### 2025-11-27 - Payslip Acknowledgment System + Email Fix

**Payslip Acknowledgment System deployed to production:**

| Change | Details |
|--------|---------|
| ueipab_payroll_enhancements | Upgraded v1.41.0 → v1.43.0 |
| Acknowledgment Fields | access_token, is_acknowledged, acknowledged_date, acknowledged_ip |
| Portal Routes | /payslip/acknowledge/<id>/<token> for employee confirmation |
| Access Tokens | Generated for 49 existing payslips |
| Email Template | "Payslip Compact Report" subject Jinja2 conditional fixed |

**Email Subject Fix:**
- **Old (broken):** `{{ (' │ Lote: ' + object.payslip_run_id.name) if object.payslip_run_id else '' }}`
- **New (working):** `{{' │ Lote: ' + object.payslip_run_id.name if object.payslip_run_id else ''}}`

**Payslip Data Cleanup:**
- Cancelled 5 confirmed payslips (reversed accounting moves)
- Deleted 49 payslips via ORM unlink()
- Deleted 2 test batches
- Reset sequence to 1 (next = SLIP/001)

### 2025-11-26 - SSO Rate Change + Otras Deducciones

| Change | Details |
|--------|---------|
| VE_SSO_DED_V2 | Rate changed from 4.5% → 4% |
| VE_OTHER_DED_V2 | New salary rule created (seq 105) |
| VE_TOTAL_DED_V2 | Updated to include other deductions |
| Contract Field | `ueipab_other_deductions` added |
| Email Template | "Payslip Email - Employee Delivery" created |
| Compact Report | SSO label updated to 4% |

### 2025-11-25 - Production Migration Complete

- All 44 production contracts assigned to "Salarios Venezuela UEIPAB V2"
- ARI rates compared: 43/44 match, 1 discrepancy (ARCIDES ARZOLA)
- V1 fields removed, V2 fields active
- 47 users had excessive permissions removed

---

## Feature Version History

### Payslip Acknowledgment System (v1.42.0-v1.43.0)

**Purpose:** Token-based portal for employees to acknowledge payslip receipt.

**Fields Added:**
- `access_token` - UUID for secure portal access
- `is_acknowledged` - True when employee confirms
- `acknowledged_date` - When confirmation occurred
- `acknowledged_ip` - IP address of confirmation
- `acknowledged_user_agent` - Browser/device info

**Routes:**
- GET `/payslip/acknowledge/<id>/<token>` - Landing page
- POST `/payslip/acknowledge/<id>/<token>/confirm` - Process confirmation

**Session Requirement:** Routes use `auth='public'` which requires database session.

### Batch Email Template Selector (v1.33.0-v1.34.0)

**v1.34.0 (2025-11-24):**
- Fixed `total_net_amount` computed field to include `VE_NET_V2` code
- Changed `exchange_rate` to computed field auto-populated from VEB rates

**v1.33.0 (2025-11-24):**
- Added template selector with 3 templates
- Fixed "Payslip Compact Report" QWeb syntax
- Fixed "Aguinaldos Email" with Christmas theme

### Comprobante de Pago Compacto (v1.40.0-v1.41.0)

**v1.41.0 (2025-11-26):**
- ARI Deduction now shows actual rate from contract
- Before: `VE_ARI_DED_V2 - ARI Variable %`
- After: `Retención impuestos AR-I X%`

**v1.40.0 (2025-11-25):**
- Added payslip's `exchange_rate_used` as default for VEB display
- 4-priority system: Custom → Rate date → Payslip rate → Latest

### Relación de Liquidación Report (v1.19.0-v1.26.0)

**v1.26.0 (2025-11-21):** Auto-latest rate as default for VEB
**v1.25.4 (2025-11-20):** XLSX layout matches PDF exactly
**v1.25.3 (2025-11-20):** Antigüedad displays for ALL employees
**v1.25.2 (2025-11-19):** XLSX export uses wizard's exchange rate
**v1.24.0 (2025-11-18):** Added payslip number to header
**v1.21.0 (2025-11-18):** Improved interest formula display
**v1.20.0 (2025-11-18):** Accrual-based interest calculation
**v1.19.0-1.19.8 (2025-11-17):** Exchange rate override, formatting, layout

### Acuerdo Finiquito Laboral (v1.18.0-v1.25.1)

**v1.25.1 (2025-11-18):** Fixed rate_date parameter handling
**v1.25.0 (2025-11-18):** Added exchange rate override UI
**v1.23.0 (2025-11-18):** Exchange rate override support
**v1.18.2:** DOCX export with python-docx
**v1.18.0:** Initial release with PDF export

### Prestaciones Interest Report (v1.20.0-v1.22.0)

**v1.22.0 (2025-11-18):** Exchange rate consistency fix using `company_rate`
**v1.20.0 (2025-11-18):** Accrual-based interest calculation

### Payslip Email Delivery (hr_payslip_monthly_report v17.0.1.2)

**v17.0.1.2 (2025-11-22):**
- Fixed "Send Mail" button disappearing after cancel
- Added "Reset Send Status" button for recovery

---

## Bug Fixes & Critical Fixes

### V2 Antigüedad Validation Fix (2025-11-21)

**Bug:** Invalid `previous_liquidation_date` causing overpayments
- Dates before contract start created negative "already paid" periods
- Example: SLIP/853 paid $195.08 instead of $100.40 (94% error!)

**Fix:** Added validation `if previous_liquidation and previous_liquidation >= contract.date_start:`
**Impact:** Prevents 20.7% overpayment on affected liquidations

### V2 Vacation/Bono Fix (2025-11-17)

- Fixed double deduction bug where NET was incorrectly $0.00
- New field: `ueipab_vacation_prepaid_amount` for actual prepaid amounts
- School year: Sep 1 - Aug 31

### INCES Deduction Scope Fix (2025-11-18)

**Observation:** INCES should only apply to Utilidades (profit sharing)
**Fix:** Updated LIQUID_INCES_V2 formula to exclude Vacaciones and Bono Vacacional

### Container Issues (2025-11-19)

**Empty Database Pollution:**
- Problem: Database "ueipab" exists but not initialized
- Fix: `DROP DATABASE ueipab;`

**WebSocket Port Mismatch:**
- Problem: Config uses deprecated `longpolling_port = 8078`
- Fix: Update to `gevent_port = 8072`

---

## Technical Learnings

### Accrual-Based Currency Conversion (2025-11-18)

```python
# WRONG - Re-converts total accumulated USD each month
accumulated_usd = 0.0
for month in months:
    accumulated_usd += month_amount_usd
    accumulated_veb = convert(accumulated_usd, month_rate)  # WRONG!

# CORRECT - Convert each month's amount once, accumulate VEB
accumulated_veb = 0.0
for month in months:
    month_veb = convert(month_amount_usd, month_rate)
    accumulated_veb += month_veb  # Proper accrual
```

### Exchange Rate Override for Interest

**Decision:** Interest calculation should IGNORE exchange rate override

**Rationale:**
- Interest accumulated over months at historical rates
- Different from other benefits (computed once at liquidation)
- Both reports must match for employee understanding

---

## AR-I Portal (v17.0.1.0.0)

**Module Structure:**
```
ueipab_ari_portal/
├── models/
│   ├── hr_employee_ari.py    # Main AR-I model (81 fields)
│   ├── ari_excel_generator.py # SENIAT template filler
│   └── hr_contract.py        # Contract extension
├── controllers/portal.py     # Portal routes
├── views/                    # XML views
├── wizard/ari_reject_wizard.py
├── security/                 # Access rules
├── data/                     # Cron, email templates
└── static/templates/         # SENIAT Excel template
```

**Tax Calculation Example:**
```
Annual Income: 50,000.00 (5,555.56 UT @ 9.00 Bs/UT)
Desgravamen Único: 774.00 UT
Taxable Income: 4,781.56 UT
Estimated Tax: 811.65 UT
Personal Rebate: 10.00 UT
Tax to Withhold: 801.65 UT
Withholding %: 14.43%
```

---

## Smart Invoice Confirmation Script (2025-11-27)

**Business Rules:**
| Scenario | Unit Price | Credit Applied |
|----------|------------|----------------|
| Credit ≥ $34.99 | $162.39 (discount) | Yes |
| Credit < $34.99 | $197.38 (regular) | Yes |
| No credit | $197.38 (regular) | No |

**Usage:**
```bash
# Dry run
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/smart_invoice_confirmation.py
```

---

## V1 to V2 Migration

**V1 Fields Removed:**
- `ueipab_salary_base`, `ueipab_bonus_regular`, `ueipab_extra_bonus`
- `ueipab_deduction_base`, `ueipab_monthly_salary`, `ueipab_salary_notes`

**V2 Fields Active:**
- `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `cesta_ticket_usd`
- `ueipab_ari_withholding_rate`, `ueipab_ari_last_update`
- `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`
- `ueipab_vacation_paid_until`, `ueipab_vacation_prepaid_amount`
- `ueipab_other_deductions`

---

**Last Updated:** 2025-11-27
