# Banco Plaza Employee Data Collection Campaign

**Status:** 🟢 LIVE — blast sent 2026-06-17, collecting responses  
**Module:** `ueipab_hr_employee` v17.0.1.4.0  
**Created:** 2026-06-16 | **Blast sent:** 2026-06-17 23:57 UTC

---

## Purpose

Banco Plaza requires 4 additional fields per employee to open mass payroll accounts:

| XLSX Col | Field | Format |
|----------|-------|--------|
| D | Segundo Nombre | Text (blank = no aplica) |
| F | Segundo Apellido | Text (blank = no aplica) |
| O | Operadora | 3-digit carrier code (412, 414, 416, 421, 422, 424, 426, etc.) |
| P | Número Telefónico | 7-digit number (without prefix) |

Source file: `/home/ftpuser/odoo-dev/Plantilla-Empleados-UEIPAB-FILLED(1).xlsx`  
Data rows: 8–51 (44 employees) | Headers: row 7 | Footer: row 54  

---

## Architecture

### Two-server design

| Server | Role |
|--------|------|
| `odoo.ueipab.edu.ve` (prod, `10.124.0.3`) | Hosts the public form + stores submissions in `ir.config_parameter` |
| `freescout.ueipab.edu.ve` (dev) | Hosts XLSX file + blast/sync scripts |

Submissions flow: employee fills form → stored in prod Odoo param → `sync_banco_plaza_xlsx.py` pulls via XML-RPC → writes XLSX.

### `ir.config_parameter` keys (prod Odoo, `DB_UEIPAB`)

| Key | Content |
|-----|---------|
| `banco_plaza.form_secret` | HMAC-SHA256 secret for token generation |
| `banco_plaza.employees` | JSON list of all 44 employees (set by blast script) |
| `banco_plaza.submissions` | JSON dict keyed by employee email, updated on each submit |
| `banco_plaza.campaign_open` | `'True'` / `'False'` — gates form access |
| `banco_plaza.dry_run` | `'True'` → all form ACK emails route to CEO inbox only |

---

## Public Form

**URL pattern:** `https://odoo.ueipab.edu.ve/banco-plaza-form/<token>`  
**Controller:** `addons/ueipab_hr_employee/controllers/banco_plaza_form.py`  
**Auth:** public (`auth='public'`)  
**Token:** `HMAC-SHA256(form_secret, employee_email.lower())[:24]`

### Features
- Pre-filled with XLSX data + any prior submission (re-editable)
- Client-side: digits-only JS filter on Operadora (max 3) and Número (max 7); auto-uppercase on name fields; disable-on-submit guard
- Server-side: name regex `[A-Za-záéíóúÁÉÍÓÚüÜñÑ'\s\-]+`; operadora `^\d{3}$`; número `^\d{7}$`; cross-validation (operadora ↔ número must both be present or both absent)
- Multi-edit: re-submittable until `campaign_open=False`
- On submit: saves to `banco_plaza.submissions` + sends 2 ACK emails

### ACK emails on submit

1. **Employee receipt** (`_send_ack_employee`): blast-style email to employee showing confirmed data, green rows for changed fields, "Actualizar mis datos" button. CC + Reply-To `recursoshumanos@ueipab.edu.ve`.
2. **HR diff notification** (`_send_notify_hr`): diff table (ANTERIOR vs NUEVO) to `recursoshumanos@ueipab.edu.ve`.

### Dry-run flag

When `banco_plaza.dry_run = 'True'` (set in `ir.config_parameter`):
- ACK email → `gustavo.perdomo@ueipab.edu.ve` (no CC)
- HR notify → `gustavo.perdomo@ueipab.edu.ve`
- Subject prefixed with `[DRY-RUN]`
- Submission data is **still saved normally** — dry-run only affects email routing

---

## Scripts

### `scripts/send_banco_plaza_data_blast.py` — Blast email sender

Reads XLSX, enriches phone data from prod Odoo, generates per-employee HMAC tokens, stores employee list + secret in prod Odoo params, sends personalized HTML emails.

```bash
# Test single employee (always → CEO inbox, no real employee email)
python3 scripts/send_banco_plaza_data_blast.py --test-employee ARCIDES

# Send to ALL 44 employees (live)
python3 scripts/send_banco_plaza_data_blast.py --live
```

**Email content:**
- Blue UEIPAB header + greeting
- Contingency plan intro paragraph
- Data table (red rows = PENDIENTE fields)
- Yellow CTA box with "Confirmar y/o Actualizar mis Datos →" button after the table
- HR contact footer

**Key constants:**
- `CEO_EMAIL = 'gustavo.perdomo@ueipab.edu.ve'`
- `CC_EMAIL = 'recursoshumanos@ueipab.edu.ve'`
- `REPLY_TO = 'recursoshumanos@ueipab.edu.ve'`
- `FORM_BASE = 'https://odoo.ueipab.edu.ve/banco-plaza-form'`

**`ODOO_NAME_OVERRIDE`** — 4-part name exceptions (confirmed):
- `gustavo.perdomo@` → ('JOSE', 'MATA')
- `alejandra.lopez@` → ('CRISTINA', 'SAYAGO')

### `scripts/sync_banco_plaza_xlsx.py` — XLSX sync

Pulls `banco_plaza.submissions` from prod Odoo via XML-RPC and writes changes to the local XLSX file.

```bash
# Preview only (no file write)
python3 scripts/sync_banco_plaza_xlsx.py

# Apply changes to XLSX
python3 scripts/sync_banco_plaza_xlsx.py --apply
```

---

## Go-Live Checklist

- [x] Validate full flow with test employee (ARCIDES dry-run 2026-06-16)
- [x] Flip dry-run off (`banco_plaza.dry_run = 'False'`)
- [x] Blast sent to all 44 employees — 2026-06-17 23:57 UTC (mail ids 7725–7768)
  - ✅ OK (0 missing): 2 — ALEJANDRA LOPEZ, GUSTAVO PERDOMO
  - ⚠️ Missing 1 field: 2 — GLADYS BRITO, LUISA ABREU
  - ⚠️ Missing 2 fields: 26 employees
  - ⚠️ Missing 4 fields: 14 employees
- [~] Collect responses (monitor with `sync_banco_plaza_xlsx.py`) — **30/44 submitted as of 2026-06-18**
- [ ] Close campaign when done: `banco_plaza.campaign_open = 'False'`
- [ ] Sync XLSX and submit to Banco Plaza

---

## Monitoring & Closing the Campaign

### Check submission progress (safe, read-only, run anytime)

```bash
python3 scripts/sync_banco_plaza_xlsx.py
```

Shows count of submissions received, per-employee diff (what would change in XLSX), and timestamp + submit count per employee. The XLSX file is **not touched** until `--apply` is passed.

### Write submissions to XLSX

```bash
python3 scripts/sync_banco_plaza_xlsx.py --apply
```

Run this on-demand — no need to do it after every submission. Typically run once or twice toward the end of the campaign, or right before the Banco Plaza deadline.

### Close the campaign (disables form for all employees)

```python
# via XML-RPC from dev server
models.execute_kw(db, uid, key, 'ir.config_parameter', 'set_param',
    ['banco_plaza.campaign_open', 'False'])
```

Or via Odoo shell on prod:
```python
env['ir.config_parameter'].sudo().set_param('banco_plaza.campaign_open', 'False')
```

After closing: run `sync_banco_plaza_xlsx.py --apply` for the final write, then submit the XLSX to Banco Plaza.

---

## Phone Validation Notes

- `VALID_OPS` check removed — any 3-digit numeric code accepted (covers 422 and future carriers)
- Three employees had corrupt phone data in XLSX (operadora=41, numero=48321963 = backup WA number): LUIS RODRIGUEZ, MARIA FIGUERA, ROBERT QUIJADA — these are treated as PENDIENTE by the blast script

## Accent Normalization

Spanish accented characters are **not accepted by Banco Plaza** and must be replaced with plain ASCII equivalents before submission.

| Special | Replace |
|---------|---------|
| Á/á | A |
| É/é | E |
| Í/í | I |
| Ó/ó | O |
| Ú/ú, Ü/ü | U |
| Ñ/ñ | N |
| Ç/ç | C |

**`sync_banco_plaza_xlsx.py` normalizes automatically** — `_normalize()` is applied to `segundo_nombre` and `segundo_apellido` on every `--apply` run. Employees may type accented names in the form; they will always land in the XLSX as clean ASCII.

Manual normalization run 2026-06-18 cleaned 11 cells (GUZMÁN, VELÁSQUEZ, YÉPEZ, PADRÓN, RONDÓN, JOSÉ ×3, ARÉVALO, PATIÑO).

## Manual Name Entry (national ID copies)

When employees don't respond in time, HR can fill in Segundo Nombre + Segundo Apellido directly from scanned national ID copies and then resend a reminder so the employee still confirms their phone number.

**Workflow:**
1. Edit XLSX directly (openpyxl, col D = Segundo Nombre, col F = Segundo Apellido)
2. Run `--send-employee NAME` to refresh `banco_plaza.employees` param in prod Odoo and send reminder — employee sees names pre-filled, only needs to confirm/add phone

**Done 2026-06-18** — 12 employees filled from national ID copies + reminder emails sent (mail ids 7865–7877):

| Employee | Segundo Nombre | Segundo Apellido |
|---|---|---|
| ANDRES MORALES | JOSE | PERALES |
| AUDREY GARCIA | LUCIA | AREYAN |
| CAMILA ROSSATO | ISABEL | ROJAS |
| DANIEL BONGIANNI | OMAR | MOSQUEDA |
| ISMARY ARCILA | ANDREINA | SALAZAR |
| JOSE HERNANDEZ | GREGORIO | GARCIA |
| LEIDYMAR ARAY | DEL CARMEN | MENESES |
| MARIELA PRADO | JUDITH | MARTINEZ |
| NORKA LA ROSA | JOSEFINA | BLANCO |
| PABLO NAVARRO | ANTONIO | *(blank — no segundo apellido)* |
| YARITZA BRUCES | YOSELY | CASANOVA |
| ZARETH FARIAS | NOHEMI | HERNANDEZ |

**Cédula corrections:**
- RAFAEL PEREZ: XLSX had `28595198` → corrected to `37383811` (2026-06-18)
- MIGUEL ROMERO: XLSX had blank → filled `8263626` (2026-06-18)

---

## ARCIDES ARZOLA — Test Employee

- **Row:** 10 in XLSX
- **Token:** `44f1a3285e79b67968f3bf48`
- **Form URL:** `https://odoo.ueipab.edu.ve/banco-plaza-form/44f1a3285e79b67968f3bf48`
- **Dry-run submission:** 2026-06-16 19:53 (dummy values J/M/412/4840948) — **cleared** before live blast to avoid pre-filling ARCIDES's form with test data
