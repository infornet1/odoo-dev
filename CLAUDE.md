# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2025-11-28 13:40 UTC

## Core Instructions

**CRITICAL RULES:**
- **ALWAYS work locally, NEVER in production environment**
- **NEVER TOUCH DB_UEIPAB without proper authorization**
- Development database: `testing`
- Production database: `DB_UEIPAB` (requires authorization)

---

## Active Features Summary

| # | Feature | Status | Module | Documentation |
|---|---------|--------|--------|---------------|
| 1 | Payroll Disbursement Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYROLL_DISBURSEMENT_REPORT.md) |
| 2 | Venezuelan Liquidation V1/V2 | Production | `ueipab_payroll_enhancements` | [V2 Impl](documentation/LIQUIDATION_V2_IMPLEMENTATION.md) |
| 3 | Prestaciones Interest Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PRESTACIONES_INTEREST_REPORT.md) |
| 4 | Venezuelan Payroll V2 | Production | `ueipab_payroll_enhancements` | [V2 Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md) |
| 5 | Relacion Liquidacion Report | Production | `ueipab_payroll_enhancements` | [Docs](documentation/RELACION_BREAKDOWN_REPORT.md) |
| 6 | Payslip Email Delivery | Production | `hr_payslip_monthly_report` | [Docs](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md) |
| 7 | Batch Email Template Selector | Production | `ueipab_payroll_enhancements` | - |
| 8 | Comprobante de Pago Compacto | Production | `ueipab_payroll_enhancements` | - |
| 9 | Acuerdo Finiquito Laboral | Production | `ueipab_payroll_enhancements` | [Docs](documentation/FINIQUITO_REPORT.md) |
| 10 | AR-I Portal | Testing | `ueipab_ari_portal` | - |
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | - |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](documentation/RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | See below |

---

## Planned: Duplicate Payslip Warning Enhancement

**Status:** 📋 PLANNED | **Priority:** Medium

**Problem:** Users can accidentally create duplicate payslips for the same employee/period when clicking "Generate Payslips" multiple times.

**Proposed Solution:** Warning wizard before generating payslips

**Duplicate Detection Criteria:**
- Same employee (`employee_id`)
- Overlapping date range (`date_from` ≤ batch.date_end AND `date_to` ≥ batch.date_start)
- Not cancelled (`state != 'cancel'`)

**User Flow:**
```
User clicks "Generate Payslips" → System checks for duplicates → If found:
┌─────────────────────────────────────────────────────┐
│  ⚠️ Duplicate Payslips Warning                      │
│                                                     │
│  The following employees already have payslips      │
│  for this period (Nov 16-30, 2025):                 │
│                                                     │
│  • JUAN PEREZ - SLIP/1001 (Draft)                  │
│  • MARIA LOPEZ - SLIP/1002 (Confirmed)             │
│                                                     │
│  [Skip Duplicates]  [Create All]  [Cancel]          │
└─────────────────────────────────────────────────────┘
```

**Button Actions:**
- **Skip Duplicates:** Only create for employees WITHOUT existing payslips
- **Create All:** Create all payslips (for intentional duplicates/corrections)
- **Cancel:** Abort operation

**Implementation:**
1. Create TransientModel: `hr.payslip.duplicate.warning`
2. Modify `hr.payslip.employees.action_compute_sheet()` to check duplicates
3. If duplicates found, open warning wizard instead of creating
4. Warning wizard buttons call back with `skip_duplicates` or `force_create` flag

**Files to Modify:**
- `models/hr_payslip_employees.py` - Add duplicate check logic
- `wizard/payslip_duplicate_warning.py` - New warning wizard (create)
- `wizard/payslip_duplicate_warning_view.xml` - Wizard form view (create)
- `security/ir.model.access.csv` - Add wizard access

---

## Venezuelan Liquidation System (V1 vs V2)

| Aspect | V1 (Legacy) | V2 (Current) |
|--------|-------------|--------------|
| Structure Code | LIQUID_VE | LIQUID_VE_V2 |
| Salary Field | `ueipab_deduction_base` | `ueipab_salary_v2` |
| Accounting | 5.1.01.10.002 | 5.1.01.10.010 |

**V2 Contract Fields:**
```python
contract.ueipab_salary_v2              # Direct salary subject to deductions
contract.ueipab_extrabonus_v2          # NOT subject to deductions
contract.ueipab_bonus_v2               # NOT subject to deductions
contract.ueipab_original_hire_date     # Original hire date (antiguedad)
contract.ueipab_previous_liquidation_date  # Last full liquidation
contract.ueipab_vacation_prepaid_amount    # Total prepaid vacation/bono
contract.ueipab_other_deductions       # Fixed USD for loans/advances
```

---

## Venezuelan Payroll V2 Deductions

| Deduction | Rate | Applies To |
|-----------|------|------------|
| SSO (IVSS) | 4% | Salary, Vacaciones, Bono Vac., Utilidades |
| FAOV | 1% | Salary, Vacaciones, Bono Vac., Utilidades |
| INCES (PARO) | 0.5% | **Utilidades ONLY** |
| ARI | Variable % | From contract field |
| Otras Deducciones | Fixed USD | From contract field |
| INCES (Payroll) | 0.25% | **DISABLED** - pending legal |

---

## Report Exchange Rate System

**3-Priority System for VEB Reports:**
1. Custom rate (wizard) → "Tasa personalizada"
2. Rate date lookup (wizard) → "Tasa del DD/MM/YYYY"
3. Latest available / Payslip rate → "Tasa automática"

**Disbursement Report Priority (2025-11-27):**
1. Batch `exchange_rate` field → "Batch (BATCH_NAME)"
2. Payslip `exchange_rate_used` → "Payslip (exchange_rate_used)"
3. Date-based currency lookup → "Date lookup (YYYY-MM-DD)"

**Interest Calculation:** Always uses accrual method (ignores override)

---

## Payslip Batch Features

**Date Sync to Payslips (2025-11-27):**
- Button: "Sync Dates to Payslips" on batch form
- Updates `date_from`/`date_to` on all **draft** payslips
- **Automatically recomputes** all updated payslips
- Skips non-draft payslips with warning
- Use case: Batch date range changed after payslips created

**Total Net Payable (2025-11-27):**
- Shows sum of NET amounts for all payslips in batch
- **Includes draft payslips** (critical for pre-validation)
- Supports both V1 (`VE_NET`) and V2 (`VE_NET_V2`) structures
- Only excludes cancelled payslips

**Exchange Rate Application:**
- Button: "Apply Rate to Payslips" on batch form
- Updates `exchange_rate_used` on all payslips in batch
- Works on any state (draft, done, paid, cancel)

**Batch Email Sending (2025-11-28):**
- Button: "Send Payslips by Email" on batch form
- Field: `email_template_id` - Select email template before sending
- Uses notification popup instead of chatter (model doesn't inherit mail.thread)
- Default template: **Payslip Email - Employee Delivery** (updated 2025-11-28)

**Generate Payslips Button Visibility (Updated 2025-11-28):**
- Requires `batch_exchange_rate > 0` (simplified - no confirmation step required)
- Exchange rate auto-populates from latest BCV rate in `res.currency.rate`
- Fallback: Uses most recent confirmed batch rate if no BCV rate available

**Exchange Rate Auto-Population (2025-11-28):**
- New batches automatically get latest BCV rate from `res.currency.rate`
- Lookup order: VEB/VES/VEF currency → latest `company_rate`
- Fallback: Most recent confirmed batch rate
- Also triggers on `date_start`/`date_end` change if rate is still 0

---

## Email Templates (Batch Sending)

| Template | Use Case |
|----------|----------|
| Payslip Compact Report | Regular payroll |
| Payslip Email - Employee Delivery | Monthly detailed view with acknowledgment **(DEFAULT)** |
| Aguinaldos Email | December Christmas bonuses |

**Syntax Rules:**
- Headers (subject): Jinja2 `{{object.field}}`
- Body (body_html): QWeb `t-out="object.field"`

**Payslip Email - Employee Delivery Template (2025-11-28):**
- **Subject:** `💰 Comprobante de Pago │ Nro.: {{ object.number }} │ Lote: {{ object.payslip_run_id.name if object.payslip_run_id else "N/A" }}`
- **Email From:** `"Recursos Humanos" <recursoshumanos@ueipab.edu.ve>`
- **Email To:** `{{ object.employee_id.work_email }}`
- **Email CC:** `recursoshumanos@ueipab.edu.ve`
- **Exchange Rate:** Uses `object.exchange_rate_used` dynamically (fixed 2025-11-28)
- Includes digital acknowledgment button
- Button text: "Enviar conformidad digital"
- Acknowledgment title: "Acuso conformidad y recepción digital de este comprobante"
- Records confirmation with date, time, and IP
- Deduction labels: IVSS 4%, FAOV 1%, Paro Forzoso 0.5%

**Email Template Exchange Rate Fix (2025-11-28):**
- **Problem:** Template had hardcoded rate `241.5780` in JSONB `body_html` field
- **Solution:** Changed to `object.exchange_rate_used or 1.0` for dynamic lookup
- **Affected:** Both `es_VE` and `en_US` locale versions
- **Template IDs:** Testing: 43, Production: 37

**Payslip Acknowledgment Landing Page (Updated 2025-11-28):**
- Amount displayed in **VES (Bs.)** using payslip exchange rate
- Title: "Confirmar Recepción Digital"
- Text: "Al hacer click en el botón, confirma que ha recibido y revisado este comprobante de pago de forma digital."
- Button: "Confirmar Recepción Digital"
- Audit trail: Records date, time, and IP address

---

## Module Versions

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | v17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | v1.46.0 | 2025-11-28 |
| ueipab_hr_contract | v17.0.2.1.0 | 2025-11-26 |
| ueipab_ari_portal | v17.0.1.0.0 | 2025-11-26 |

---

## Key Technical Patterns

### Odoo safe_eval (Salary Rules)
```python
# FORBIDDEN:
from datetime import timedelta  # NO imports
hasattr(contract, 'field')      # NO hasattr

# ALLOWED:
(date1 - date2).days            # Direct arithmetic
try:
    value = contract.field or False
except:
    value = False
```

### Odoo 17 View Syntax
```xml
<!-- OLD (Odoo 16) -->
<div attrs="{'invisible': [('field', '=', 0)]}">

<!-- NEW (Odoo 17) -->
<div invisible="field == 0">
```

### Public Routes & Database Selection (Odoo 17)
Routes with `auth='public'` require database session.

**Production Fix (2025-11-27):** Changed `dbfilter` from `^(DB_UEIPAB|testing)$` to `^DB_UEIPAB$`
- **Problem:** Password reset/invitation links returned 404 without active session
- **Root Cause:** Multiple databases in filter prevented auto-selection
- **Solution:** Single-database filter enables auto-session creation
- **File:** `/etc/odoo/odoo.conf` in `ueipab17` container

### Report Development
- Use `web.basic_layout` for UTF-8 support
- Model naming: `report.<module>.<template_id>` (exact match)
- TransientModel wizards need security access rules
- QWeb: Pass data structures only (no Python calls)

---

## Production Environment

```
Server: 10.124.0.3
Container: ueipab17
Database: DB_UEIPAB
```

**Contract Status:**
- Production: 44 contracts (V2 structure assigned)
- Testing: 46 contracts

---

## Quick Commands

```bash
# Run script in testing
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py

# Restart Odoo
docker restart odoo-dev-web

# Clear cache
Ctrl+Shift+R (browser hard reload)
```

---

## Environment Sync

**VEB Exchange Rate Sync:** `scripts/sync-veb-rates-from-production.sql`
- Source: `ueipab17_postgres_1` @ 10.124.0.3
- Production: 636 rates (2024-01-30 to 2025-11-27)
- Currency ID: 2 (VEB)

---

## Documentation Index

### Core Systems
- [V2 Implementation](documentation/LIQUIDATION_V2_IMPLEMENTATION.md)
- [V2 Revision Plan](documentation/VENEZUELAN_PAYROLL_V2_REVISION_PLAN.md)
- [V2 Payroll Implementation](documentation/V2_PAYROLL_IMPLEMENTATION.md)

### Reports
- [Payroll Disbursement](documentation/PAYROLL_DISBURSEMENT_REPORT.md)
- [Prestaciones Interest](documentation/PRESTACIONES_INTEREST_REPORT.md)
- [Relacion Breakdown](documentation/RELACION_BREAKDOWN_REPORT.md)
- [Finiquito Report](documentation/FINIQUITO_REPORT.md)
- [Exchange Rate Override](documentation/EXCHANGE_RATE_OVERRIDE_FEATURE.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)
- [V2 Formula Bugs](documentation/LIQUIDATION_V2_FORMULA_BUGS_2025-11-21.md)
- [Vacation/Bono Fix](documentation/VACATION_BONO_FIX_IMPLEMENTATION_PLAN.md)

### Email System
- [Send Mail Fix](documentation/SEND_MAIL_BUTTON_FIX_FINAL.md)
- [Phase 2 Decommission](documentation/PHASE2_EMAIL_DECOMMISSION_PLAN.md)

### Infrastructure
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [WebSocket Issue](documentation/WEBSOCKET_ISSUE_DIAGNOSIS.md)

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)
- [Liquidation Clarifications](documentation/LIQUIDATION_CLARIFICATIONS.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history and bug fixes.
