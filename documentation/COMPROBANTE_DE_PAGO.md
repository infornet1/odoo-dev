# Comprobante de Pago Compacto

**Status:** Production | **Version:** 17.0.1.52.2 | **Updated:** 2026-02-13

Payslip receipt sent to employees by email with earnings breakdown, deductions, net pay, exchange rate, and digital acknowledgment button.

## Two Rendering Paths

| Path | Template | Storage | How It Works |
|------|----------|---------|-------------|
| PDF Report | `report_payslip_compact` | Code (`payslip_compact_report.py` + `.xml`) | QWeb PDF attached to email |
| Email Body | "Payslip Email - Employee Delivery" | Database (`mail.template` ID=37 prod, 43 test) | Inline QWeb in `body_html` |

The **Email Body** path is the primary one used for employee delivery (batches default to this template). It renders earnings directly using `object.get_line_amount('CODE')` calls.

## Cesta Ticket Fix (v1.52.2, 2026-02-13)

**Bug:** Cesta Ticket ($40/month) was invisible to employees in both rendering paths:
- PDF Report: consolidated into "Bonos" line via code
- Email Body: simply omitted (no row for `VE_CESTA_TICKET_V2`)

Employees saw 3 visible earnings lines that didn't add up to Total Asignaciones, causing confusion.

**Fix (both paths):**
- `payslip_compact_report.py`: Separated `VE_CESTA_TICKET_V2` from `VE_BONUS_V2` consolidation, added as its own "Cesta Ticket" display line
- `mail.template` (DB): Added Cesta Ticket row between "Otros Bonos" and "Total Asignaciones" via direct SQL (ORM sanitizes QWeb tags)

**Important:** The "Employee Delivery" template lives in the database only (not in XML data files). Updates require SQL or Odoo shell -- the ORM's HTML sanitizer strips QWeb `<t>` tags from `body_html`.

## Earnings Lines (Current)

| # | Concepto | Source Code |
|---|----------|-------------|
| 1 | Salario Base / Salario quincenal (Deducible) | `VE_SALARY_V2` |
| 2 | Bonos | `VE_BONUS_V2` |
| 3 | Otros Bonos | `VE_EXTRABONUS_V2` |
| 4 | Cesta Ticket | `VE_CESTA_TICKET_V2` |
| | **Total Asignaciones** | `VE_GROSS_V2` |
