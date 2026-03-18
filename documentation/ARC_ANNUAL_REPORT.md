# ARC Annual Withholding Certificate (Comprobante ARC)

**Status:** Production-ready (testing)
**Module:** `ueipab_payroll_enhancements` v17.0.1.56.x
**Menus:** Payroll → Reports → Comprobante ARC | Estado ARC

---

## Overview

Generates and distributes the SENIAT-mandated **Comprobante de Retenciones de Impuesto Sobre la Renta (ARC)** — the annual ISLR withholding certificate required by Decreto 1808. One PDF per employee, batch-emailed with an acknowledgment receipt portal link.

---

## Features

- **PDF per employee** — portrait Letter, dark-blue header, monthly detail table (Bs. only)
- **Batch email wizard** — select fiscal year + optional employee filter; sends with `mail.mail`
- **Simulation** — months without confirmed payslips are estimated using contract ARI % × historical BCV rate
- **Contract date windowing** — respects `date_start` / `date_end`; no rows before hire date
- **CC to HR** — every ARC email copies `recursoshumanos@ueipab.edu.ve`
- **Acknowledgment portal** — employee clicks link in email → confirms receipt → IP + timestamp recorded
- **Ack confirmation email** — auto-sent to employee (CC: HR) when they confirm; template `email_template_arc_ack_confirmation`
- **Ack status tracker** — Payroll → Reports → Estado ARC; tree view grouped by fiscal year showing sent/pending/confirmed per employee
- **Acknowledgment reset** — HR manager can reset via `action_reset_acknowledgment()`

---

## Architecture

### Models

| Model | Type | Description |
|-------|------|-------------|
| `report.ueipab_payroll_enhancements.arc_annual_report` | AbstractModel | Report values provider |
| `arc.employee.certificate` | Model (permanent) | One record per employee+year; stores ack state |
| `arc.report.wizard` | TransientModel | Wizard: year, employee filter, email template |
| `arc.report.wizard.result` | TransientModel | Per-employee send status row |

### Controllers

Both live in `controllers/payslip_acknowledgment.py`:

| Route | Auth | Purpose |
|-------|------|---------|
| `GET /arc/ack/init/<id>/<token>` | `none` | **Session-setter**: reads `?db=` → `ensure_db()` → redirects to the real page |
| `GET /arc/acknowledge/<id>/<token>` | `public` | Shows confirmation form |
| `POST /arc/acknowledge/<id>/<token>/confirm` | `public` | Records acknowledgment |

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

| Template ID | Model | Purpose |
|-------------|-------|---------|
| `email_template_arc_annual` | `hr.employee` | Outbound ARC delivery (wizard renders + injects ack button via `Markup`) |
| `email_template_arc_ack_confirmation` | `arc.employee.certificate` | Confirmation receipt sent automatically when employee acknowledges; CC to HR |

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
- Green rows = confirmed; grey rows = pending
- Filters: Confirmados / Pendientes
- Group-by: Ejercicio Fiscal, Empleado
- Hidden column `acknowledged_ip` available via column selector

---

## SENIAT Compliance Notes

- **Decreto 1808** — ARC is mandatory for any compensation paid during the fiscal year
- No minimum months required; even 1 month of employment requires an ARC
- Employees hired mid-year receive only their worked months
- 0% ARI still requires ARC

---

## Wizard Usage

1. Go to **Payroll → Reports → Comprobante ARC**
2. Set **Ejercicio Fiscal** (default: previous year)
3. Optionally filter by specific employees (leave blank = all with active contracts)
4. Click **Vista Previa PDF** to generate a multi-page preview
5. Select an email template and click **Enviar por Email**
6. Watch progress; results shown per employee with status icons

---

## Changelog

| Version | Change |
|---------|--------|
| 17.0.1.55.0 | Initial release: PDF, batch email, ack portal |
| 17.0.1.55.1 | Fix: multi-database session (auth=none init route + server_wide_modules); nginx arc proxy; web.base.url = IP:8019 for testing |
| 17.0.1.56.0 | CC to HR on outbound emails; ack confirmation email to employee+HR; Estado ARC tracking list view |
