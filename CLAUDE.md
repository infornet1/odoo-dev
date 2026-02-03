# UEIPAB Odoo Development - Project Guidelines

**Last Updated:** 2026-02-03

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
| 11 | Payslip Acknowledgment | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 12 | Smart Invoice Script | Testing | Script | - |
| 13 | Recurring Invoicing | Planned | - | [Plan](documentation/RECURRING_INVOICING_IMPLEMENTATION_PLAN.md) |
| 14 | Duplicate Payslip Warning | Planned | `ueipab_payroll_enhancements` | See below |
| 15 | Batch Email Progress Wizard | Production | `ueipab_payroll_enhancements` | [Docs](documentation/BATCH_EMAIL_WIZARD.md) |
| 16 | HRMS Dashboard Ack Widget | Production | `ueipab_hrms_dashboard_ack` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 17 | Cybrosys Module Refactoring | Planned | Multiple | [Docs](documentation/CYBROSYS_MODULE_MODIFICATIONS.md) |
| 18 | Liquidacion Estimation Mode | Production | `ueipab_payroll_enhancements` | See below |
| 19 | Payslip Ack Reminder System | Production | `ueipab_payroll_enhancements` | [Docs](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md) |
| 20 | V2 Payroll Accounting Config | Production | Database config | See below |
| 21 | Invoice Currency Rate Bug | Documented | `tdv_multi_currency_account` | [Docs](documentation/INVOICE_CURRENCY_RATE_BUG.md) |
| 22 | Aguinaldos Disbursement Report | Production | `ueipab_payroll_enhancements` | See below |
| 23 | Advance Payment System (Pago Adelanto) | Production | `ueipab_payroll_enhancements` | See below |
| 24 | WebSocket/Nginx Fix (Email Marketing) | Production | Infrastructure | [Docs](documentation/WEBSOCKET_NGINX_FIX.md) |
| 25 | Email Bounce Processor | Planned | Script + `ueipab_bounce_log` | [Docs](documentation/BOUNCE_EMAIL_PROCESSOR.md) |

---

## Advance Payment System (Pago Adelanto)

**Status:** Production | **Version:** 17.0.1.52.1 | **Deployed:** 2026-01-14

Allows partial salary disbursement when company needs to pay employees in installments due to financial constraints.

### Business Use Case

When company cannot pay full salary at once:
1. **Advance Batch (e.g., 50%)**: Pay partial salary now
2. **Remainder Batch (e.g., 50%)**: Pay remaining balance later

Each batch:
- Computes payslips with multiplied earnings
- Deductions recalculate on reduced amounts
- Posts with its own exchange rate
- Clean, independent journal entries

### Batch Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_advance_payment` | Boolean | Checkbox "Es Pago Adelanto" |
| `advance_percentage` | Float | Percentage to pay (e.g., 50.0) |
| `advance_total_amount` | Computed | Total advance amount |
| `is_remainder_batch` | Boolean | Marks as remainder payment |
| `advance_batch_id` | Many2one | Link to original advance batch |

### Payslip Fields

| Field | Type | Description |
|-------|------|-------------|
| `advance_amount` | Computed | Individual advance amount |

### Salary Rules Behavior

When `is_advance_payment = True` OR `is_remainder_batch = True`:
```python
# Earnings multiplied by advance_percentage
VE_SALARY_V2 = contract.salary * (batch.advance_percentage / 100)
VE_EXTRABONUS_V2 = contract.extrabonus * (batch.advance_percentage / 100)
VE_BONUS_V2 = contract.bonus * (batch.advance_percentage / 100)
# Deductions auto-recalculate on reduced gross
```

### Email Templates (Synced to Production 2026-01-08)

| Template | Purpose | Prod ID |
|----------|---------|---------|
| Payslip Email - Advance Payment - Employee Delivery | Full detailed advance notification | 44 |
| Payslip Email - Remainder Payment - Reconciliation | Shows advance + remainder + total | 45 |

### Accounting Treatment

Each batch posts independently with its exchange rate:
```
Advance Batch (50% at rate 298):
  DR 5.1.01.10.001  Bs. 14,900
     CR 1.1.01.02.001  Bs. 14,900

Remainder Batch (50% at rate 310):
  DR 5.1.01.10.001  Bs. 15,500
     CR 1.1.01.02.001  Bs. 15,500
```

No provisions or exchange difference accounts needed.

---

## Aguinaldos Disbursement Report

**Status:** Production | **Deployed:** 2025-12-19 | **Version:** v1.49.1

Generate disbursement report for Aguinaldos (Christmas Bonus) payslips with PDF/Excel export, currency selection (USD/VEB), and batch filtering.

**Access:** Payroll -> Reports -> Aguinaldos Disbursement Report

---

## Planned: Duplicate Payslip Warning

**Status:** Planned | **Priority:** Medium

Warning wizard before generating payslips to detect duplicates (same employee/overlapping period). Options: Skip Duplicates, Create All, Cancel.

---

## Liquidacion Estimation Mode

**Status:** Production | **Version:** 17.0.1.46.0

Adds "Modo Estimacion" to Relacion de Liquidacion wizard (VEB only). Applies configurable % reduction with projection watermark, hidden signatures.

---

## Venezuelan Liquidation System (V1 vs V2)

| Aspect | V1 (Legacy) | V2 (Current) |
|--------|-------------|--------------|
| Structure Code | LIQUID_VE | LIQUID_VE_V2 |
| Salary Field | `ueipab_deduction_base` | `ueipab_salary_v2` |
| Accounting | 5.1.01.10.002 | 5.1.01.10.010 |

**V2 Contract Fields:** `ueipab_salary_v2`, `ueipab_extrabonus_v2`, `ueipab_bonus_v2`, `ueipab_original_hire_date`, `ueipab_previous_liquidation_date`, `ueipab_vacation_prepaid_amount`, `ueipab_other_deductions`

---

## Venezuelan Payroll V2 Deductions

| Deduction | Rate | Applies To |
|-----------|------|------------|
| SSO (IVSS) | 4% | Salary, Vacaciones, Bono Vac., Utilidades |
| FAOV | 1% | Salary, Vacaciones, Bono Vac., Utilidades |
| INCES (PARO) | 0.5% | Utilidades ONLY |
| ARI | Variable % | From contract field |
| Otras Deducciones | Fixed USD | From contract field |

---

## V2 Payroll Accounting Configuration

**Status:** Production | **Updated:** 2026-01-10

| Purpose | Debit Account | Credit Account |
|---------|---------------|----------------|
| V2 Payroll (NOMINA_VE_V2) | 5.1.01.10.001 (Nomina) | 1.1.01.02.001 (Banco Venezuela) |
| V2 Liquidation (LIQUID_VE_V2) | 5.1.01.10.010 (Prestaciones) | 2.1.01.10.005 (Provision Prestaciones) |
| AGUINALDOS | 5.1.01.10.001 (Nomina) | 1.1.01.02.001 (Banco Venezuela) |

**Design Pattern:** Only deductions and NET create journal entries. Earnings rules do NOT post to accounting.

**Important:** At minimum, the `*_NET_*` rule in each structure MUST have both debit and credit accounts configured, otherwise payslips cannot be confirmed (error: "choose Debit and Credit account for at least one salary rule").

---

## Report Exchange Rate System

**3-Priority System for VEB Reports:**
1. Custom rate (wizard) -> "Tasa personalizada"
2. Rate date lookup (wizard) -> "Tasa del DD/MM/YYYY"
3. Latest available / Payslip rate -> "Tasa automatica"

**Interest Calculation:** Always uses accrual method (ignores override)

---

## Payslip Batch Features

| Feature | Description |
|---------|-------------|
| Date Sync | Syncs batch dates to draft payslips, auto-recomputes |
| Total Net Payable | Includes draft payslips, supports V1/V2/Aguinaldos |
| Exchange Rate Application | Applies rate to all payslips in batch |
| Email Sending | Template selector, notification popup |
| Exchange Rate Auto-Population | From latest BCV rate or last batch |
| Advance Payment | Partial salary disbursement with % multiplier |
| Remainder Payment | Linked to original advance batch for reconciliation |

---

## Module Versions

### Testing Environment

| Module | Version | Last Update |
|--------|---------|-------------|
| hr_payroll_community | 17.0.1.0.0 | 2025-11-28 |
| ueipab_payroll_enhancements | 17.0.1.52.1 | 2026-01-08 |
| ueipab_hr_contract | 17.0.2.0.0 | 2025-11-26 |
| hrms_dashboard | 17.0.1.0.2 | 2025-12-01 |

### Production Environment

| Module | Version | Status |
|--------|---------|--------|
| ueipab_payroll_enhancements | 17.0.1.52.1 | Current (synced 2026-01-19) |
| ueipab_hr_contract | 17.0.2.0.0 | Current |
| hrms_dashboard | 17.0.1.0.2 | Installed (2025-12-21) |
| ueipab_hrms_dashboard_ack | 17.0.1.0.0 | Installed (2025-12-21) |

---

## Key Technical Patterns

### Odoo safe_eval (Salary Rules)
```python
# FORBIDDEN: imports, hasattr
# ALLOWED: Direct arithmetic, try/except
```

### Odoo 17 View Syntax
```xml
<!-- OLD --> <div attrs="{'invisible': [('field', '=', 0)]}">
<!-- NEW --> <div invisible="field == 0">
```

### Report Development
- Use `web.basic_layout` for UTF-8 support
- Model naming: `report.<module>.<template_id>` (exact match)
- TransientModel wizards need security access rules

---

## Production Environment

See [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md) for full details.

**Quick Reference:**
- Server: `10.124.0.3`
- Container: `0ef7d03db702_ueipab17`
- Database: `DB_UEIPAB`
- Module Path: `/home/vision/ueipab17/addons`

---

## Quick Commands

```bash
# Run script in testing
docker exec -i odoo-dev-web /usr/bin/odoo shell -d testing --no-http \
  < /opt/odoo-dev/scripts/[script-name].py

# Restart Odoo
docker restart odoo-dev-web
```

---

## Email Bounce Processor

**Status:** Planned | **Type:** Phase 1 (Script) + Phase 2 (Odoo Module)

Automated detection and cleanup of bounced emails from Freescout (READ-ONLY source). Freescout database is never modified.

### Phase 1 - Standalone Script (Current Priority)

- **Script:** `scripts/daily_bounce_processor.py` (cron daily)
- **Source:** Freescout MySQL (read-only) for bounce detection
- **Target:** Production Odoo via XML-RPC (`res.partner` + `mailing.contact`)
- **Notify:** HTML report to `soporte@ueipab.edu.ve`
- **Log:** `scripts/bounce_logs/bounce_log.csv` (queryable history)
- **State:** `scripts/bounce_state.json` (tracks last processed ID)

**Multi-email handling:** Contacts with multiple emails separated by `;` are handled surgically -- only the bounced email is removed, the rest are preserved.

### Phase 2 - Odoo Module (Future, with WhatsApp Agent)

- **Module:** `ueipab_bounce_log` (extends Contacts app, not a standalone app)
- **Menu:** `Contacts > Bounce Log` (direct submenu)
- **Model:** `mail.bounce.log` with resolution workflow
- **Resolution:** Two actions per bounce record:
  - "Restaurar Email Original" -- re-enable old email (temporary issue fixed)
  - "Aplicar Nuevo Email" -- apply customer's new email
- **WhatsApp Integration:** Agent queries pending bounces, contacts customer via WhatsApp, updates record on reply

See [Full Documentation](documentation/BOUNCE_EMAIL_PROCESSOR.md) for complete details.

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

### Features
- [Payslip Acknowledgment System](documentation/PAYSLIP_ACKNOWLEDGMENT_SYSTEM.md)
- [Batch Email Wizard](documentation/BATCH_EMAIL_WIZARD.md)
- [Email Templates](documentation/EMAIL_TEMPLATES.md)
- [Cybrosys Module Modifications](documentation/CYBROSYS_MODULE_MODIFICATIONS.md)

### Infrastructure
- [Production Environment](documentation/PRODUCTION_ENVIRONMENT.md)
- [Combined Fix Procedure](documentation/COMBINED_FIX_PROCEDURE.md)
- [Email Bounce Processor](documentation/BOUNCE_EMAIL_PROCESSOR.md)

### Liquidation
- [V1 Complete Guide](documentation/LIQUIDATION_COMPLETE_GUIDE.md)
- [V2 Migration Plan](documentation/LIQUIDACION_V2_MIGRATION_PLAN.md)

### Known Issues
- [Invoice Currency Rate Bug](documentation/INVOICE_CURRENCY_RATE_BUG.md)

### Legal
- [LOTTT Research](documentation/LOTTT_LAW_RESEARCH_2025-11-13.md)

---

## Changelog

See [CHANGELOG.md](documentation/CHANGELOG.md) for detailed version history.
