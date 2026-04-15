# Requisición Preliminar de Nómina — Estimation Report

**Created:** 2026-04-15
**Status:** 🟢 Production
**Module:** `ueipab_payroll_enhancements`
**Based on:** Payroll Disbursement Detail Report

---

## Purpose

Allows Finance to generate a **preliminary payroll cost estimate** before HR creates or confirms any payslip. Reads directly from active contracts (`hr.contract`) using V2 salary fields — no payslip records required.

Use cases:
- Budget approval requests before payroll is processed
- Bank transfer requisitions (USD amount needed)
- Accounting provision entries (VEB amount needed)
- Cross-check against confirmed disbursement report after payroll closes

---

## Design Decisions

### Currency — Single Currency Per Run

User selects **one currency** (USD or VEB) per report generation. The entire PDF/XLSX renders in that currency. Running twice (once per currency) is the intended workflow.

- Consistent with existing disbursement wizard (`currency_id` field)
- Avoids overcrowded landscape columns
- Cleaner separation of bank requisition (USD) vs. accounting entry (VEB)

### Exchange Rate — Auto-Population

When VEB is selected, the rate field **auto-populates** from the latest `res.currency.rate` record using `company_rate` (Odoo's computed inverse rate, VEB per 1 USD). User can override manually.

| Scenario | Behavior |
|---|---|
| VEB selected | Rate field visible, pre-filled with latest `company_rate`, shows rate date |
| USD selected | Rate field hidden (rate = 1.0 implicitly) |
| User edits rate | Labeled "Tasa personalizada" in report header |
| No VEB rate found | Field shows 0.0 + warning "No se encontró tasa disponible" |

Uses same `res.currency.rate` query as priority-3 fallback in existing disbursement wizard — proven in production.

### Estimation Source — Active Contracts Only

Calculates from `hr.contract` V2 fields directly. No dependency on payslip state.

| Contract Field | Maps To |
|---|---|
| `ueipab_salary_v2` | Salary (base) |
| `ueipab_extrabonus_v2` + `ueipab_bonus_v2` + `cesta_ticket_usd` | Bonus |
| `ueipab_ari_percentage` | ARI deduction rate |

Deduction rates applied (V2 standard):
- SSO: 4% of salary
- FAOV: 1% of salary
- PARO (INCES): 0.5% — Utilidades only, not applied in quincena estimation
- ARI: variable % from contract field

### Period Logic — Quincena Fixed Split

| Quincena | Days | Proration |
|---|---|---|
| Quincena 1 (1–15) | 15 | `monthly / 2.0` |
| Quincena 2 (16–end) | 15 | `monthly / 2.0` |

Fixed `monthly / 2.0` — consistent with the quincena fix applied 2026-02-25 across all V2 salary rules. Does NOT use `period_days / 30.0`.

### Report Header

Clearly labeled `[ESTIMADO]` to distinguish from confirmed disbursement reports. Exchange rate line shows rate value + date + whether auto or manual:

```
REQUISICIÓN PRELIMINAR DE NÓMINA — QUINCENA 1 MAYO 2026   [ESTIMADO]
Tasa de Cambio: 98.45 VEB/USD — BCV al 14/04/2026
```

---

## Wizard Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `period_type` | Selection | Yes | `q1` = Quincena 1 (1–15), `q2` = Quincena 2 (16–end) |
| `period_month` | Date | Yes | First day of target month (month/year selector) |
| `currency_id` | Many2one `res.currency` | Yes | USD or VEB |
| `exchange_rate` | Float | If VEB | Auto-filled from latest `res.currency.rate.company_rate` |
| `exchange_rate_date` | Date | Display only | Date of the auto-filled rate record |
| `advance_percentage` | Float | No | Optional advance % (e.g. 50 for adelanto). Default 100 |
| `allowed_tag_ids` | Many2many `res.partner.category` | No | Contact tags to include. Default: Empleado, Personal Administrativo, Profesor. Leave empty = no tag filter |
| `employee_ids` | Many2many `hr.employee` | No | Leave empty = all active employees |
| `department_ids` | Many2many `hr.department` | No | Leave empty = all departments |
| `output_format` | Selection | Yes | `pdf` or `excel` |
| `employee_count` | Integer (computed) | — | Preview: active contracts matching filters |

---

## Report Columns

| # | Column | Source |
|---|---|---|
| 1 | Employee Name | `hr.employee.name` |
| 2 | Tax ID | `hr.employee.identification_id` |
| 3 | Salary | `contract.ueipab_salary_v2 / 2.0` |
| 4 | Bonus | `(extrabonus + bonus + cesta) / 2.0` |
| 5 | Gross | Salary + Bonus |
| 6 | ARI | Gross × ARI% |
| 7 | SSO 4% | Salary × 4% |
| 8 | FAOV 1% | Salary × 1% |
| 9 | Total Deductions | ARI + SSO + FAOV |
| 10 | Net Payable | Gross − Total Deductions |
| 11 | Advance Amount | Net × advance_percentage% (if < 100%) |

If VEB: all monetary values × exchange_rate.
If advance_percentage < 100: column 11 shown, otherwise omitted.

**Summary box (bottom of report):**
- Total Gross
- Total Deductions
- Total Net Payable
- 9% Tax on Net (informational)
- Exchange rate used + date

---

## Implementation Plan

### Files to Create

| File | Description |
|---|---|
| `models/payroll_requisition_wizard.py` | Wizard model + calculation logic |
| `wizard/payroll_requisition_wizard_view.xml` | Wizard form view |
| `reports/payroll_requisition_report.xml` | QWeb PDF template |

### Files to Modify

| File | Change |
|---|---|
| `models/__init__.py` | Import new wizard model |
| `wizard/__init__.py` | Import new wizard view |
| `views/hr_payslip_run_view.xml` | Add menu item under Payroll → Reporting |
| `security/ir.model.access.csv` | Add access rule for new wizard model |
| `__manifest__.py` | Register new files |

### Reuse from Existing Disbursement Wizard

- Contract V2 field reading logic (`ueipab_salary_v2`, bonus fields)
- Exchange rate priority lookup (priority-3 fallback → `res.currency.rate`)
- Excel export skeleton (`xlsxwriter` workbook/worksheet setup, formats)
- QWeb layout structure (`web.basic_layout`, landscape Letter paper format)
- `_action_export_pdf()` / `_action_export_excel()` pattern

---

## Changelog

| Date | Version | Change |
|---|---|---|
| 2026-04-15 | — | Initial design doc created. Status: Planned |
| 2026-04-15 | v1.62.0 | Built and deployed to testing. Model, wizard view, QWeb PDF, Excel export, menu item. Smoke test passed: 47 active contracts, VEB rate 477.1488 @ 2026-04-13. |
| 2026-04-15 | v1.62.1 | Fix: exchange rate source label blank in Excel/PDF output. Root cause: Odoo 17 web_save drops invisible fields from payload; `exchange_rate_source` is invisible when USD is selected at form open, so onchange value is never persisted. Fix: re-derive label at export time via `_get_rate_source_label()` which uses `exchange_rate_date` if available, otherwise re-queries `res.currency.rate`. |
| 2026-04-15 | v1.62.1 | Deployed to production (DB_UEIPAB). Module upgrade clean, container restarted. |
| 2026-04-15 | v1.62.2 | Feat: configurable partner tag filter (`allowed_tag_ids`) added to wizard. Pre-filled with Empleado/Personal Administrativo/Profesor by default. Empty = no filter. Field path: `employee_id.work_contact_id.category_id`. Deployed to testing. |
| 2026-04-15 | v1.62.2 | **Known data gap:** As of 2026-04-15, only 5 of 46 active employees in production have an allowed tag on their contact (Daniel Bongianni, Giovanni Vezza, Lorena Reyes, MAIRELSY MOTTA, RAFAEL ANGEL PÉREZ ARÉVALO). The remaining 41 employees need `Empleado`, `Personal Administrativo`, or `Profesor` tagged on their Odoo contact record for the filter to include them. Until then, leave `allowed_tag_ids` empty to run unfiltered. |

---

## Related Documentation

- [Payroll Disbursement Report](PAYROLL_DISBURSEMENT_REPORT.md) — existing confirmed report this is based on
- [V2 Payroll Implementation](V2_PAYROLL_IMPLEMENTATION.md) — V2 salary rule structure and contract fields
- [Advance Payment System](ADVANCE_PAYMENT_SYSTEM.md) — advance % logic reference
