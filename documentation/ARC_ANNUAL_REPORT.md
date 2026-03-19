# ARC Annual Withholding Certificate (Comprobante ARC)

**Status:** Production-ready (testing)
**Module:** `ueipab_payroll_enhancements` v17.0.1.56.x
**Menus:** Payroll → Reports → Comprobante ARC | Estado ARC

---

## Overview

Generates and distributes the SENIAT-mandated **Comprobante de Retenciones de Impuesto Sobre la Renta (ARC)** — the annual ISLR withholding certificate required by Decreto 1808. One PDF per employee, batch-emailed with an acknowledgment receipt portal link.

---

## Features

- **Two-stage workflow** — Stage 1: notice email without PDF; Stage 2: signed PDF after employee confirms
- **PDF per employee** — portrait Letter, company logo centered at top, dark-blue header, monthly detail table (Bs. only)
- **Employer signature/seal in PDF** — `firma_sello_gp.jpg` embedded in left signature column (base64 data URI, no HTTP request required)
- **Digital ack block in PDF** — right column shows employee name, cédula, confirmation timestamp (VET GMT−4), IP when confirmed
- **Batch email wizard** — select fiscal year + optional employee filter; sends Stage 1 notice emails
- **Simulation** — months without confirmed payslips are estimated using contract ARI % × historical BCV rate
- **Contract date windowing** — respects `date_start` / `date_end`; no rows before hire date
- **CC to HR** — every ARC email (Stage 1 and Stage 2) copies `recursoshumanos@ueipab.edu.ve`
- **One-time portal guard** — "Ya Confirmado" page shown if employee clicks again after first confirmation
- **Stage 2 auto-PDF** — on confirm: cert model calls `action_send_final_pdf()` → generates signed PDF → emails via `email_template_arc_final_pdf`
- **Ack confirmation email** — secondary notice email sent to employee (CC: HR); template `email_template_arc_ack_confirmation`
- **Ack status tracker** — Payroll → Reports → Estado ARC; tree view with state badge (Pendiente / Notificado / Confirmado)
- **Acknowledgment reset** — HR manager can reset via `action_reset_acknowledgment()` (clears ack data + resets state to `pending`)

---

## Architecture

### Models

| Model | Type | Description |
|-------|------|-------------|
| `report.ueipab_payroll_enhancements.arc_annual_report` | AbstractModel | Report values provider; fetches cert ack_info per employee for PDF signature block |
| `arc.employee.certificate` | Model (permanent) | One record per employee+year; tracks state (`pending`/`notified`/`acknowledged`) + ack audit trail |
| `arc.report.wizard` | TransientModel | Stage 1 wizard: year, employee filter, email template |
| `arc.report.wizard.result` | TransientModel | Per-employee send status row |

### Two-Stage Workflow

```
Stage 1 — Wizard (HR action)
  HR opens wizard → selects year + employees + template
  For each employee:
    1. arc.employee.certificate created/updated → state = notified
    2. Notice email sent (NO PDF) with portal confirm link
    3. Wizard shows sent/error per employee

Stage 2 — Portal (Employee action)
  Employee clicks link in email → /arc/ack/init/ → /arc/acknowledge/
  Employee clicks "Confirmar" → POST /arc/acknowledge/.../confirm
    1. cert.write(is_acknowledged=True, acknowledged_date, ip, ua, state=acknowledged)
    2. cert.action_send_final_pdf() → PDF regenerated (now includes employer seal
       left column + digital ack block right column) → emailed via email_template_arc_final_pdf
    3. email_template_arc_ack_confirmation also sent (plain text confirmation receipt)
```

### Controllers

Both live in `controllers/payslip_acknowledgment.py`:

| Route | Auth | Purpose |
|-------|------|---------|
| `GET /arc/ack/init/<id>/<token>` | `none` | **Session-setter**: reads `?db=` → `ensure_db()` → redirects to the real page |
| `GET /arc/acknowledge/<id>/<token>` | `public` | Shows confirmation form (one-time guard: shows "Ya Confirmado" if already acked) |
| `POST /arc/acknowledge/<id>/<token>/confirm` | `public` | Records acknowledgment; triggers Stage 2 PDF generation + delivery |

#### Multi-database session design

`/arc/acknowledge/` uses `auth='public'` which requires an active Odoo session. In a multi-database environment (testing + DB_UEIPAB + openeducat_demo) with no session cookie, Odoo can't auto-select the database and returns 404.

**Fix**: `_get_ack_url()` generates `/arc/ack/init/<id>/<token>?db=<db>` instead of going directly to `/arc/acknowledge/`. The init route uses `auth='none'` (included in Odoo's nodb routing map because the module is in `server_wide_modules`) and calls `ensure_db()`, which sets `session.db` and redirects to the same URL. On the second pass, the session has a database → normal db routing → confirmation page loads.

**Required `odoo.conf` change** (already applied):
```
server_wide_modules = web,ueipab_payroll_enhancements
```

### nginx

`/arc/` prefix is proxied to Odoo port 8019 (same block as `/web/`, `/payslip/`, etc.) in `/etc/nginx/sites-enabled/dev.ueipab.edu.ve`:
```nginx
location ~ ^/(web|website|payslip|mail|report|arc)(/|$) {
    proxy_pass http://127.0.0.1:8019;
    ...
}
```

---

## Data Sources

### Real payslip months
Confirmed payslips (`state='done'`) in the fiscal year with codes:
- Earnings: `VE_SALARY_V2`, `VE_EXTRABONUS_V2`, `VE_BONUS_V2`
- Deductions: `VE_SSO_DED_V2`, `VE_FAOV_DED_V2`, `VE_PARO_DED_V2`, `VE_ARI_DED_V2`

All amounts converted to VES using the payslip batch `exchange_rate`.

### Simulated months (no payslip)
- `gross_ves = ueipab_salary_v2 × historical_BCV_rate`
- `ari_ves = gross_ves × (ueipab_ari_withholding_rate / 100)`
- Historical rate: latest `res.currency.rate` where `name <= last_day_of_month`

### Contract date windowing
```python
effective_start = max(date(year, 1, 1), contract.date_start)
effective_end   = min(date(year, 12, 31), contract.date_end or year_end, today)
```
Months outside this window render as empty dashes.

---

## Email Templates

| Template ID | Model | Stage | Purpose |
|-------------|-------|-------|---------|
| `email_template_arc_annual` | `hr.employee` | 1 | Notice email: wizard renders + injects ack button via `Markup`; **no PDF** |
| `email_template_arc_final_pdf` | `arc.employee.certificate` | 2 | Signed PDF delivery: auto-sent by `action_send_final_pdf()` after employee confirms |
| `email_template_arc_ack_confirmation` | `arc.employee.certificate` | 2 | Plain confirmation receipt; also sent on confirm; CC to HR |

### `web.base.url` note
In the testing environment (direct Odoo port, no SSL): `http://64.23.157.121:8019`. Using the domain (`dev.ueipab.edu.ve`) triggers browser HSTS and forces HTTPS on port 8019 which has no SSL. Set via:
```bash
docker exec odoo-dev-web /usr/bin/odoo shell -d testing --no-http
self.env['ir.config_parameter'].sudo().set_param('web.base.url', 'http://64.23.157.121:8019')
self.env.cr.commit()
```

## Acknowledgment Status Tracking

**Menu:** Payroll → Reports → Estado ARC

Tree view on `arc.employee.certificate`, pre-grouped by fiscal year:
- Green rows = `acknowledged`; blue rows = `notified`; grey rows = `pending`
- `state` badge column: Pendiente / Notificado / Confirmado
- Filters: Confirmados / Notificados / Pendientes
- Group-by: Ejercicio Fiscal, Empleado
- Hidden column `acknowledged_ip` available via column selector

---

## SENIAT Compliance Notes

- **Decreto 1808** — ARC is mandatory for any compensation paid during the fiscal year
- No minimum months required; even 1 month of employment requires an ARC
- Employees hired mid-year receive only their worked months
- 0% ARI still requires ARC

---

## Wizard Usage (Stage 1)

1. Go to **Payroll → Reports → Comprobante ARC**
2. Set **Ejercicio Fiscal** (default: previous year)
3. Optionally filter by specific employees (leave blank = all with active contracts)
4. Click **Vista Previa PDF** to preview the unsigned ARC (no employer seal — will appear after confirmation)
5. Select a notice email template (e.g. `ARC Anual - Comprobante de Retenciones ISLR`) and click **Enviar por Email**
6. Watch progress; results shown per employee with status icons
7. Cert state → `notified`; PDF will be auto-sent (Stage 2) after each employee confirms

**Stage 2 is fully automatic.** When the employee clicks the portal link and confirms:
- PDF is re-generated with employer seal (left column) + digital ack block (right column)
- Signed PDF emailed to employee + CC to HR
- Cert state → `acknowledged` (visible in Estado ARC)

---

## Changelog

| Version | Change |
|---------|--------|
| 17.0.1.55.0 | Initial release: PDF, batch email, ack portal |
| 17.0.1.55.1 | Fix: multi-database session (auth=none init route + server_wide_modules); nginx arc proxy; web.base.url = IP:8019 for testing |
| 17.0.1.56.0 | CC to HR on outbound emails; ack confirmation email to employee+HR; Estado ARC tracking list view |
| 17.0.1.57.0 | Two-stage workflow: Stage 1 notice email (no PDF); Stage 2 auto-signed PDF on confirm; employer seal image in PDF left column; digital ack block in PDF right column; `state` field on cert (pending/notified/acknowledged); `email_template_arc_final_pdf` new template |
| 17.0.1.58.0 | PDF enhancements: company logo centered at top; signature boxes restructured as inner tables (wkhtmltopdf-safe layout); ack timestamp converted to VET (UTC−4) labeled "Fecha (VET GMT-4)"; Stage 2 email fix: replaced `send_mail()` with direct `mail.mail.create()` to prevent `email_to=False` bug in Odoo 17 pipeline; employer seal `firma_sello_gp.jpg` permissions fixed to 644 |
| 17.0.1.59.0 | Stage 1 email: ARC summary table injected (monthly detail + totals + AR-I%); `AGUINALDOS_2025` excluded from payslip search so months with only aguinaldo payslip fall through to contract simulation; simulation fixes: ARI based on `ueipab_salary_v2` only (mirrors `VE_ARI_DED_V2` rule) |
| 17.0.1.60.1 | Fix simulation: PARO restored to `salary_v2 × 0.5%` — `VE_PARO_DED_V2` confirmed to run on regular nómina (`VE_PAYROLL_V2`), not Utilidades-only. Simulated months now match real payslip behaviour. Deployed to prod 2026-03-19; `notified` employees receive corrected PARO in Stage 2 PDF on confirm. |
| 17.0.1.60.0 | Certificate number field (`ARC-YYYY-NNNNN`) on cert model; shown in PDF header + digital ack block; shown in Stage 1 email summary header; company logo added to Stage 1 email summary; confirm button text updated; portal confirmation message updated to mention PDF email dispatch |
